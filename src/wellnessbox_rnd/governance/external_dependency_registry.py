from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

REGISTRY_SCHEMA = "op119_external_dependency_registry_v1"


class ExternalDependencyRegistryError(ValueError):
    """Raised when the external dependency registry is incomplete or inflated."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountableOwnerV1(_StrictModel):
    role_id: str = Field(min_length=1, max_length=200)
    authority: str = Field(min_length=1, max_length=300)
    responsibility: str = Field(min_length=1, max_length=1000)


class RequiredExternalInputV1(_StrictModel):
    input_id: str = Field(min_length=1, max_length=200)
    supplier_role: str = Field(min_length=1, max_length=300)
    schema_version: str = Field(min_length=1, max_length=200)
    acceptance_contract: str = Field(min_length=1, max_length=500)
    provision_status: Literal["MISSING", "PROVIDED"]
    artifact_path: str | None = None
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ExternalInputDefinitionV1(_StrictModel):
    input_id: str = Field(min_length=1, max_length=200)
    supplier_role: str = Field(min_length=1, max_length=300)
    schema_version: str = Field(min_length=1, max_length=200)
    acceptance_contract: str = Field(min_length=1, max_length=500)


class ExternalInputContractV1(_StrictModel):
    schema_version: Literal["op039_external_input_contract_v1"]
    requirement_id: Literal["OP-039"]
    required_inputs: list[ExternalInputDefinitionV1] = Field(min_length=1)


class BlockingReasonV1(_StrictModel):
    code: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    source_path: str = Field(min_length=1, max_length=500)
    json_pointer: str = Field(pattern=r"^/[A-Za-z0-9_/-]+$")
    expected_observation: Literal["EMPTY_LIST"]


class ExternalDependencyEntryV1(_StrictModel):
    requirement_id: str = Field(pattern=r"^OP-[0-9]{3}$")
    accountable_owner: AccountableOwnerV1
    external_provider_role: str = Field(min_length=1, max_length=300)
    input_contract_path: str = Field(min_length=1, max_length=500)
    required_inputs: list[RequiredExternalInputV1] = Field(min_length=1)
    replacement_contracts: list[str] = Field(min_length=1)
    blocking_reasons: list[BlockingReasonV1]
    readiness: Literal["BLOCKED", "READY"]
    promotion_condition: str = Field(min_length=1, max_length=2000)


class ExternalDependencyRegistryV1(_StrictModel):
    schema_version: Literal[REGISTRY_SCHEMA]
    entries: list[ExternalDependencyEntryV1]


class ExternalDependencyRegistryAuditV1(_StrictModel):
    schema_version: Literal["op119_external_dependency_registry_audit_v1"] = (
        "op119_external_dependency_registry_audit_v1"
    )
    status: Literal["PASS"] = "PASS"
    external_requirement_ids: list[str]
    registry_requirement_ids: list[str]
    blocked_requirement_ids: list[str]
    required_input_count: int
    replacement_contract_count: int
    blocking_reason_count: int
    verified_observation_count: int


def audit_external_dependency_registry_v1(
    registry_path: str | Path,
    manifest_path: str | Path,
    repository_root: str | Path,
) -> ExternalDependencyRegistryAuditV1:
    root = Path(repository_root).resolve()
    try:
        registry = ExternalDependencyRegistryV1.model_validate_json(
            Path(registry_path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as error:
        raise ExternalDependencyRegistryError(f"invalid registry: {error}") from error
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    requirements = [
        requirement
        for group in manifest["groups"]
        for requirement in group["requirements"]
    ]
    external = {
        item["requirement_id"]: item
        for item in requirements
        if item.get("required_stage") == "EXTERNAL"
    }
    entries = {entry.requirement_id: entry for entry in registry.entries}
    if set(entries) != set(external) or len(entries) != len(registry.entries):
        raise ExternalDependencyRegistryError("external requirement set mismatch")

    verified_observations = 0
    for requirement_id, entry in entries.items():
        manifest_contracts = set(
            external[requirement_id].get("evidence", {}).get(
                "replacement_contracts", []
            )
        )
        if set(entry.replacement_contracts) != manifest_contracts:
            raise ExternalDependencyRegistryError(
                f"{requirement_id} replacement contracts do not match manifest"
            )
        for relative in entry.replacement_contracts:
            if not _resolve_repository_file(root, relative).is_file():
                raise ExternalDependencyRegistryError(
                    f"replacement contract file missing: {relative}"
                )
        input_contract_path = _resolve_repository_file(root, entry.input_contract_path)
        try:
            input_contract = ExternalInputContractV1.model_validate_json(
                input_contract_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as error:
            raise ExternalDependencyRegistryError(
                f"invalid external input contract: {error}"
            ) from error
        if input_contract.requirement_id != requirement_id:
            raise ExternalDependencyRegistryError("input contract requirement mismatch")
        registry_input_contract = [
            ExternalInputDefinitionV1.model_validate(
                item.model_dump(
                    exclude={"provision_status", "artifact_path", "artifact_sha256"}
                )
            )
            for item in entry.required_inputs
        ]
        if registry_input_contract != input_contract.required_inputs:
            raise ExternalDependencyRegistryError(
                f"{requirement_id} required inputs do not match input contract"
            )
        for definition in input_contract.required_inputs:
            if not _resolve_repository_file(
                root, definition.acceptance_contract
            ).is_file():
                raise ExternalDependencyRegistryError(
                    f"acceptance contract file missing: {definition.acceptance_contract}"
                )
        for item in entry.required_inputs:
            _validate_provisioned_input(root, item)
        input_ids = [item.input_id for item in entry.required_inputs]
        reason_codes = [reason.code for reason in entry.blocking_reasons]
        if len(input_ids) != len(set(input_ids)) or len(reason_codes) != len(
            set(reason_codes)
        ):
            raise ExternalDependencyRegistryError("registry identifiers must be unique")
        if entry.readiness == "READY" and (
            any(item.provision_status != "PROVIDED" for item in entry.required_inputs)
            or entry.blocking_reasons
        ):
            raise ExternalDependencyRegistryError(
                f"{requirement_id} cannot be READY with missing inputs or blockers"
            )
        if entry.readiness == "BLOCKED" and (
            not entry.blocking_reasons
            or not any(
                item.provision_status == "MISSING" for item in entry.required_inputs
            )
        ):
            raise ExternalDependencyRegistryError(
                f"{requirement_id} BLOCKED requires blockers and missing inputs"
            )
        for reason in entry.blocking_reasons:
            source = _resolve_repository_file(root, reason.source_path)
            try:
                value = _resolve_json_pointer(
                    json.loads(source.read_text(encoding="utf-8")),
                    reason.json_pointer,
                )
            except (OSError, KeyError, json.JSONDecodeError) as error:
                raise ExternalDependencyRegistryError(
                    f"unverified json pointer for {reason.code}: {error}"
                ) from error
            if reason.expected_observation == "EMPTY_LIST" and value != []:
                raise ExternalDependencyRegistryError(
                    f"blocking observation changed for {reason.code}"
                )
            verified_observations += 1

    return ExternalDependencyRegistryAuditV1(
        external_requirement_ids=sorted(external),
        registry_requirement_ids=sorted(entries),
        blocked_requirement_ids=sorted(
            entry.requirement_id
            for entry in entries.values()
            if entry.readiness == "BLOCKED"
        ),
        required_input_count=sum(len(entry.required_inputs) for entry in entries.values()),
        replacement_contract_count=sum(
            len(entry.replacement_contracts) for entry in entries.values()
        ),
        blocking_reason_count=sum(
            len(entry.blocking_reasons) for entry in entries.values()
        ),
        verified_observation_count=verified_observations,
    )


def _strip_repository_prefix(path: str) -> Path:
    prefix = "wellnessbox-rnd/"
    return Path(path[len(prefix) :] if path.startswith(prefix) else path)


def _resolve_repository_file(root: Path, path: str) -> Path:
    relative = _strip_repository_prefix(path)
    if relative.is_absolute():
        raise ExternalDependencyRegistryError(f"absolute repository path rejected: {path}")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ExternalDependencyRegistryError(f"repository path traversal rejected: {path}")
    return resolved


def _validate_provisioned_input(root: Path, item: RequiredExternalInputV1) -> None:
    if item.provision_status == "MISSING":
        if item.artifact_path is not None or item.artifact_sha256 is not None:
            raise ExternalDependencyRegistryError(
                f"missing input {item.input_id} cannot reference an artifact"
            )
        return
    if item.artifact_path is None or item.artifact_sha256 is None:
        raise ExternalDependencyRegistryError(
            f"provided input {item.input_id} requires artifact path and SHA-256"
        )
    artifact = _resolve_repository_file(root, item.artifact_path)
    if not artifact.is_file():
        raise ExternalDependencyRegistryError(
            f"provided input artifact missing: {item.artifact_path}"
        )
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != item.artifact_sha256:
        raise ExternalDependencyRegistryError(
            f"provided input artifact SHA-256 mismatch: {item.input_id}"
        )
    try:
        if item.schema_version == "external_high_risk_safety_case_v2":
            schemas = {
                json.loads(line)["schema_version"]
                for line in artifact.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            valid_schema = schemas == {item.schema_version}
        else:
            valid_schema = (
                json.loads(artifact.read_text(encoding="utf-8"))["schema_version"]
                == item.schema_version
            )
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise ExternalDependencyRegistryError(
            f"provided input artifact schema unreadable: {item.input_id}"
        ) from error
    if not valid_schema:
        raise ExternalDependencyRegistryError(
            f"provided input artifact schema mismatch: {item.input_id}"
        )


def _resolve_json_pointer(document: object, pointer: str) -> object:
    value = document
    for token in pointer.lstrip("/").split("/"):
        if not isinstance(value, dict) or token not in value:
            raise KeyError(pointer)
        value = value[token]
    return value
