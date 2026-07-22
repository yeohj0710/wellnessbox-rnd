from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from io import StringIO
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from wellnessbox_rnd.domain.sensor_parser import (
    normalize_cgm_summary_csv,
    normalize_sensor_genetic_payloads,
    normalize_wearable_csv,
    validate_cgm_summary_csv_schema,
    validate_gene_profile_json_schema,
    validate_wearable_summary_csv_schema,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.schemas.recommendation import DataSourceConsents

NORMALIZATION_VERSION = "sensor_file_normalization_v1"
MAX_FILE_BYTES = 2 * 1024 * 1024

FileIdentifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    ),
]


class SensorFileSource(StrEnum):
    WEARABLE = "wearable"
    CGM = "cgm"
    GENETIC = "genetic"


class SensorFileBatchStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class SensorFileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: FileIdentifier
    source: SensorFileSource
    content_base64: Annotated[
        str,
        StringConstraints(min_length=1, max_length=(MAX_FILE_BYTES * 4 // 3) + 8),
    ]


class SensorFileBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
    ]
    files: list[SensorFileInput] = Field(min_length=1, max_length=100)
    data_source_consents: DataSourceConsents

    @model_validator(mode="after")
    def file_ids_must_be_unique(self) -> SensorFileBatchRequest:
        file_ids = [item.file_id for item in self.files]
        if len(set(file_ids)) != len(file_ids):
            raise ValueError("sensor_file_ids_must_be_unique")
        return self


class SensorFileResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: FileIdentifier
    source: SensorFileSource
    status: SensorFileBatchStatus
    failure_types: list[str] = Field(default_factory=list)
    normalized_record_count: int = Field(ge=0)
    raw_file_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    normalized_payload_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    ingestion_id: str | None = Field(default=None, pattern=r"^sfi_[a-f0-9]{32}$")
    persisted: bool = False
    deduplicated: bool = False


class SensorFileBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "sensor_file_batch_response_v1"
    status: SensorFileBatchStatus
    total_file_count: int = Field(ge=1)
    success_file_count: int = Field(ge=0)
    failure_file_count: int = Field(ge=0)
    normalized_record_count: int = Field(ge=0)
    persisted_file_count: int = Field(ge=0)
    files: list[SensorFileResult]

    @model_validator(mode="after")
    def counts_must_match_files(self) -> SensorFileBatchResponse:
        success = sum(item.status == SensorFileBatchStatus.SUCCESS for item in self.files)
        failure = len(self.files) - success
        if (
            self.total_file_count != len(self.files)
            or self.success_file_count != success
            or self.failure_file_count != failure
            or self.normalized_record_count
            != sum(item.normalized_record_count for item in self.files)
            or self.persisted_file_count != sum(item.persisted for item in self.files)
        ):
            raise ValueError("sensor_file_batch_counts_mismatch")
        expected_status = (
            SensorFileBatchStatus.SUCCESS
            if failure == 0
            else SensorFileBatchStatus.FAILED
            if success == 0
            else SensorFileBatchStatus.PARTIAL_SUCCESS
        )
        if self.status != expected_status:
            raise ValueError("sensor_file_batch_status_mismatch")
        return self


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _decode_file(item: SensorFileInput) -> bytes:
    try:
        decoded = base64.b64decode(item.content_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("sensor_file_content_base64_invalid") from error
    if not decoded:
        raise ValueError("sensor_file_empty")
    if len(decoded) > MAX_FILE_BYTES:
        raise ValueError("sensor_file_too_large")
    return decoded


def _decode_utf8(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("sensor_file_utf8_required") from error


def _json_object_without_duplicate_keys(text: str) -> dict[str, Any]:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"gene_profile_duplicate_json_key::{key}")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=pairs_hook)
    except json.JSONDecodeError as error:
        raise ValueError("gene_profile_json_invalid") from error
    if not isinstance(value, dict):
        raise ValueError("gene_profile_json_object_required")
    return value


def _duplicate_csv_headers(text: str) -> list[str]:
    try:
        header = next(csv.reader(StringIO(text)))
    except (csv.Error, StopIteration):
        return []
    normalized = [item.strip() for item in header]
    return sorted({item for item in normalized if normalized.count(item) > 1})


def _normalize_file(
    source: SensorFileSource, raw: bytes
) -> tuple[dict[str, Any], list[str], list[str]]:
    text = _decode_utf8(raw)
    if source == SensorFileSource.GENETIC:
        payload = _json_object_without_duplicate_keys(text)
        validation = validate_gene_profile_json_schema(payload)
        if not validation.passed:
            return validation.model_dump(mode="json"), validation.failure_types, []
        snapshot = normalize_sensor_genetic_payloads(genetic_payload=payload)
        normalized = {
            "genetic_tags": snapshot.genetic_tags,
            "genetic_variants": [
                item.model_dump(mode="json") for item in snapshot.genetic_variants
            ],
        }
        return validation.model_dump(mode="json"), [], [normalized]

    duplicate_headers = _duplicate_csv_headers(text)
    validator = (
        validate_wearable_summary_csv_schema
        if source == SensorFileSource.WEARABLE
        else validate_cgm_summary_csv_schema
    )
    validation = validator(text)
    failures = list(validation.failure_types)
    failures.extend(f"duplicate_csv_header::{item}" for item in duplicate_headers)
    if failures:
        validation_payload = validation.model_dump(mode="json")
        validation_payload["passed"] = False
        validation_payload["failure_types"] = failures
        return validation_payload, failures, []
    normalizer = (
        normalize_wearable_csv if source == SensorFileSource.WEARABLE else normalize_cgm_summary_csv
    )
    records = [item.model_dump(mode="json") for item in normalizer(text)]
    return validation.model_dump(mode="json"), [], records


def _ingestion_id(profile_id: str, file_id: str, raw_file_sha256: str) -> str:
    identity = _canonical_json(
        {
            "profile_id": profile_id,
            "file_id": file_id,
            "raw_file_sha256": raw_file_sha256,
            "normalization_version": NORMALIZATION_VERSION,
        }
    )
    return f"sfi_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _persist_result(
    *,
    store: InterimStore,
    profile_id: str,
    item: SensorFileInput,
    raw_file_sha256: str,
    status: SensorFileBatchStatus,
    schema_validation: dict[str, Any],
    failures: list[str],
    normalized_records: list[dict[str, Any]],
) -> tuple[str, bool]:
    ingestion_id = _ingestion_id(profile_id, item.file_id, raw_file_sha256)
    normalized_payload = (
        {"records": normalized_records} if status == SensorFileBatchStatus.SUCCESS else None
    )
    normalized_payload_sha256 = (
        _sha256_json(normalized_payload) if normalized_payload is not None else None
    )
    expected = {
        "ingestion_id": ingestion_id,
        "profile_id": profile_id,
        "file_id": item.file_id,
        "source": item.source.value,
        "normalization_version": NORMALIZATION_VERSION,
        "raw_file_sha256": raw_file_sha256,
        "status": status.value,
        "schema_validation_json": _canonical_json(schema_validation),
        "failure_types_json": _canonical_json(failures),
        "normalized_record_count": len(normalized_records),
        "normalized_payload_json": (
            _canonical_json(normalized_payload) if normalized_payload is not None else None
        ),
        "normalized_payload_sha256": normalized_payload_sha256,
    }
    with store.transaction(immediate=True) as connection:
        existing = connection.execute(
            "select * from sensor_file_ingestions where ingestion_id=?",
            (ingestion_id,),
        ).fetchone()
        if existing is not None:
            if any(existing[key] != value for key, value in expected.items()):
                raise ValueError("sensor_file_ingestion_identity_conflict")
            return ingestion_id, True
        connection.execute(
            """
            insert into sensor_file_ingestions(
              ingestion_id, profile_id, file_id, source, normalization_version,
              raw_file_sha256, status, schema_validation_json, failure_types_json,
              normalized_record_count, normalized_payload_json,
              normalized_payload_sha256, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*expected.values(), datetime.now(UTC).isoformat()),
        )
    return ingestion_id, False


def ingest_sensor_file_batch(
    request: SensorFileBatchRequest,
    *,
    store: InterimStore,
) -> SensorFileBatchResponse:
    if not store.is_migrated():
        raise RuntimeError("interim_store_not_migrated")
    results: list[SensorFileResult] = []
    for item in request.files:
        raw: bytes | None = None
        consent = getattr(request.data_source_consents, item.source.value)
        if not consent.use_for_recommendation:
            results.append(
                SensorFileResult(
                    file_id=item.file_id,
                    source=item.source,
                    status=SensorFileBatchStatus.FAILED,
                    failure_types=["source_use_consent_required"],
                    normalized_record_count=0,
                )
            )
            continue
        try:
            raw = _decode_file(item)
            raw_file_sha256 = _sha256_bytes(raw)
            schema_validation, failures, normalized_records = _normalize_file(item.source, raw)
        except ValueError as error:
            raw_file_sha256 = _sha256_bytes(raw) if raw is not None else None
            schema_validation = {
                "format_name": item.source.value,
                "passed": False,
                "failure_types": [str(error)],
            }
            failures = [str(error)]
            normalized_records = []
        status = SensorFileBatchStatus.SUCCESS if not failures else SensorFileBatchStatus.FAILED
        ingestion_id: str | None = None
        deduplicated = False
        persisted = False
        normalized_payload_sha256 = (
            _sha256_json({"records": normalized_records}) if normalized_records else None
        )
        if consent.allow_persistent_storage and raw_file_sha256 is not None:
            ingestion_id, deduplicated = _persist_result(
                store=store,
                profile_id=request.profile_id,
                item=item,
                raw_file_sha256=raw_file_sha256,
                status=status,
                schema_validation=schema_validation,
                failures=failures,
                normalized_records=normalized_records,
            )
            persisted = True
        results.append(
            SensorFileResult(
                file_id=item.file_id,
                source=item.source,
                status=status,
                failure_types=failures,
                normalized_record_count=len(normalized_records),
                raw_file_sha256=raw_file_sha256,
                normalized_payload_sha256=normalized_payload_sha256,
                ingestion_id=ingestion_id,
                persisted=persisted,
                deduplicated=deduplicated,
            )
        )
    success = sum(item.status == SensorFileBatchStatus.SUCCESS for item in results)
    failure = len(results) - success
    batch_status = (
        SensorFileBatchStatus.SUCCESS
        if failure == 0
        else SensorFileBatchStatus.FAILED
        if success == 0
        else SensorFileBatchStatus.PARTIAL_SUCCESS
    )
    return SensorFileBatchResponse(
        status=batch_status,
        total_file_count=len(results),
        success_file_count=success,
        failure_file_count=failure,
        normalized_record_count=sum(item.normalized_record_count for item in results),
        persisted_file_count=sum(item.persisted for item in results),
        files=results,
    )


__all__ = [
    "NORMALIZATION_VERSION",
    "SensorFileBatchRequest",
    "SensorFileBatchResponse",
    "SensorFileBatchStatus",
    "SensorFileInput",
    "SensorFileResult",
    "SensorFileSource",
    "ingest_sensor_file_batch",
]
