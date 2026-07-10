from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.manifest import (
    canonical_json,
    sha256_file,
    validate_interim_package,
)
from wellnessbox_rnd.interim.store import InterimStore


@dataclass(frozen=True)
class ImportSummary:
    proxy_cases: int
    pro_observations: int
    adverse_events: int
    connector_sessions: int
    evaluation_cases: int
    model_versions: int
    manifest_sha256: str


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_gzip_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any], str]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"jsonl_object_required:{path}:{line_number}")
            yield line_number, value, _sha256_text(canonical_json(value))


def _limited(
    rows: Iterable[tuple[int, dict[str, Any], str]],
    maximum: int | None,
) -> Iterator[tuple[int, dict[str, Any], str]]:
    for index, row in enumerate(rows):
        if maximum is not None and index >= maximum:
            break
        yield row


def import_interim_package(
    store: InterimStore,
    package_root: Path,
    *,
    max_records_per_split: int | None = None,
) -> ImportSummary:
    validation = validate_interim_package(package_root)
    if not validation.valid:
        raise ValueError(f"interim_package_invalid:{validation.failures}")
    if not store.is_migrated():
        raise RuntimeError("interim_store_not_migrated")

    artifact_root = validation.artifact_root
    now = datetime.now(UTC).isoformat()
    dataset_id = f"proxy-gold-{validation.manifest_sha256[:16]}"
    effective_counts = {
        split: min(count, max_records_per_split) if max_records_per_split is not None else count
        for split, count in validation.split_counts.items()
    }

    with store.transaction() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO dataset_snapshots(
              dataset_id, name, version, data_class, manifest_uri, manifest_sha256,
              record_count, split_counts_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                "wellnessbox_interim_proxy_gold",
                "2026-07-10",
                DataClass.PROXY_GOLD_SIMULATION,
                str(artifact_root / "evidence_manifest.json"),
                validation.manifest_sha256,
                sum(effective_counts.values()),
                canonical_json(effective_counts),
                now,
            ),
        )

        for split in ("train", "validation", "calibration", "blind_test"):
            source_path = artifact_root / "datasets" / f"proxy_cases.{split}.jsonl.gz"
            records = []
            for line_number, row, row_hash in _limited(
                _read_gzip_jsonl(source_path), max_records_per_split
            ):
                records.append(
                    (
                        str(row["case_id"]),
                        dataset_id,
                        split,
                        DataClass.PROXY_GOLD_SIMULATION,
                        str(row["teacher_session"]),
                        str(row["archetype_id"]),
                        str(source_path),
                        line_number,
                        row_hash,
                        canonical_json(row),
                    )
                )
                if len(records) >= 1_000:
                    _upsert_proxy_cases(connection, records)
                    records.clear()
            _upsert_proxy_cases(connection, records)

        _import_outcomes(
            connection,
            artifact_root / "datasets" / "outcomes.synthetic_proxy.jsonl.gz",
        )
        _import_adverse_events(
            connection, artifact_root / "datasets" / "adr.synthetic_proxy.jsonl.gz"
        )
        _import_connector_sessions(
            connection,
            artifact_root / "datasets" / "linkage_sessions.synthetic_proxy.jsonl.gz",
        )
        _import_evaluations(connection, artifact_root)
        _import_model(connection, artifact_root, dataset_id, now)

        counts = _current_counts(connection)
        import_key = f"{validation.manifest_sha256}:{max_records_per_split or 'all'}"
        connection.execute(
            """
            INSERT OR REPLACE INTO import_jobs(
              import_key, package_root, manifest_sha256, status, counts_json, completed_at
            ) VALUES (?, ?, ?, 'completed', ?, ?)
            """,
            (
                import_key,
                str(package_root.resolve()),
                validation.manifest_sha256,
                canonical_json(counts),
                now,
            ),
        )

    return ImportSummary(
        proxy_cases=counts["proxy_cases"],
        pro_observations=counts["pro_observations"],
        adverse_events=counts["adverse_events"],
        connector_sessions=counts["connector_sessions"],
        evaluation_cases=counts["evaluation_cases"],
        model_versions=counts["model_versions"],
        manifest_sha256=validation.manifest_sha256,
    )


def register_retrained_package(
    store: InterimStore,
    package_root: Path,
    *,
    code_commit: str,
    rollback_model_id: str | None,
) -> str:
    """Register a verified retrain without replacing frozen imported case lineage."""
    validation = validate_interim_package(package_root)
    if not validation.valid:
        raise ValueError(f"interim_package_invalid:{validation.failures}")
    artifact_root = validation.artifact_root
    artifact_path = artifact_root / "model" / "proxy_recommendation_model.joblib"
    artifact_hash = sha256_file(artifact_path)
    dataset_id = f"proxy-retrain-{validation.manifest_sha256[:16]}"
    model_id = f"proxy-recommendation-{artifact_hash[:16]}"
    now = datetime.now(UTC).isoformat()
    package_metrics = json.loads(
        (artifact_root / "model" / "metrics.json").read_text(encoding="utf-8")
    )
    registry_metadata = {
        "package_metrics": package_metrics,
        "dataset_manifest_sha256": validation.manifest_sha256,
        "feature_schema": "package_script_v1_sparse_binary_features",
        "training_config": "deterministic_seed_20260710_full_150000",
        "code_commit": code_commit,
        "rollback_model_id": rollback_model_id,
    }
    with store.transaction() as connection:
        connection.execute(
            """
            insert or replace into dataset_snapshots(
              dataset_id, name, version, data_class, manifest_uri, manifest_sha256,
              record_count, split_counts_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                "wellnessbox_interim_proxy_gold_retrained",
                "2026-07-10-retrained",
                DataClass.PROXY_GOLD_SIMULATION,
                str(artifact_root / "evidence_manifest.json"),
                validation.manifest_sha256,
                validation.total_records,
                canonical_json(validation.split_counts),
                now,
            ),
        )
        connection.execute(
            """
            insert or replace into model_versions(
              model_id, model_name, version, data_class, artifact_uri, artifact_sha256,
              dataset_id, metrics_json, status, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model_id,
                "proxy_recommendation_model",
                "2026-07-10-retrained",
                DataClass.PROXY_GOLD_SIMULATION,
                str(artifact_path),
                artifact_hash,
                dataset_id,
                canonical_json(registry_metadata),
                "proxy_approved_rollback_available",
                now,
            ),
        )
    return model_id


def _upsert_proxy_cases(connection: Any, records: list[tuple[Any, ...]]) -> None:
    if not records:
        return
    connection.executemany(
        """
        INSERT OR REPLACE INTO proxy_cases(
          case_id, dataset_id, split, data_class, teacher_session, archetype_id,
          source_file, source_line, row_sha256, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )


def _import_outcomes(connection: Any, path: Path) -> None:
    rows = []
    for _, row, row_hash in _read_gzip_jsonl(path):
        rows.append(
            (
                str(row["participant_id"]),
                None,
                str(row["data_class"]),
                int(row["timepoint_weeks"]),
                float(row["z_pre"]),
                float(row["z_post"]),
                float(row["percentile_point_change"]),
                float(row["adherence"]),
                row_hash,
                canonical_json(row),
            )
        )
    connection.executemany(
        """
        INSERT OR REPLACE INTO pro_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _import_adverse_events(connection: Any, path: Path) -> None:
    rows = []
    for _, row, row_hash in _read_gzip_jsonl(path):
        rows.append(
            (
                str(row["case_id"]),
                None,
                str(row["data_class"]),
                int(bool(row["related_to_recommendation"])),
                int(bool(row["serious"])),
                str(row["status"]),
                int(row["observation_month"]),
                row_hash,
                canonical_json(row),
            )
        )
    connection.executemany(
        "INSERT OR REPLACE INTO adverse_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def _import_connector_sessions(connection: Any, path: Path) -> None:
    rows = []
    for _, row, row_hash in _read_gzip_jsonl(path):
        rows.append(
            (
                str(row["session_id"]),
                None,
                str(row["source"]),
                str(row["environment"]),
                str(row["data_class"]),
                int(bool(row["success"])),
                int(bool(row["schema_valid"])),
                int(bool(row["unit_valid"])),
                int(bool(row["timezone_valid"])),
                int(bool(row["deduplicated"])),
                int(bool(row["provenance_saved"])),
                row_hash,
                canonical_json(row),
            )
        )
    connection.executemany(
        "INSERT OR REPLACE INTO connector_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def _import_evaluations(connection: Any, artifact_root: Path) -> None:
    specs = {
        "recommendation": artifact_root
        / "evals"
        / "recommendation_predictions.proxy_blind.jsonl.gz",
        "safety": artifact_root / "evals" / "safety_evaluation.proxy.jsonl.gz",
        "action": artifact_root / "evals" / "agent_action_evaluation.proxy.jsonl.gz",
        "answer": artifact_root / "evals" / "answer_evaluation.proxy.jsonl.gz",
    }
    for kind, path in specs.items():
        rows = []
        for line_number, row, row_hash in _read_gzip_jsonl(path):
            case_id = str(row.get("case_id") or row.get("scenario_id") or row.get("question_id"))
            rows.append(
                (
                    kind,
                    case_id,
                    str(row.get("label_class", DataClass.PROXY_GOLD_SIMULATION)),
                    str(path),
                    line_number,
                    row_hash,
                    canonical_json(row),
                )
            )
        connection.executemany(
            """
            INSERT OR REPLACE INTO evaluation_cases(
              evaluation_kind, case_id, data_class, source_file, source_line,
              row_sha256, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _import_model(connection: Any, artifact_root: Path, dataset_id: str, now: str) -> None:
    artifact_path = artifact_root / "model" / "proxy_recommendation_model.joblib"
    metrics = json.loads((artifact_root / "model" / "metrics.json").read_text(encoding="utf-8"))
    artifact_hash = sha256_file(artifact_path)
    connection.execute(
        """
        INSERT OR REPLACE INTO model_versions(
          model_id, model_name, version, data_class, artifact_uri, artifact_sha256,
          dataset_id, metrics_json, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"proxy-recommendation-{artifact_hash[:16]}",
            "proxy_recommendation_model",
            "2026-07-10",
            DataClass.PROXY_GOLD_SIMULATION,
            str(artifact_path),
            artifact_hash,
            dataset_id,
            canonical_json(metrics),
            "proxy_approved",
            now,
        ),
    )


def _current_counts(connection: Any) -> dict[str, int]:
    names = (
        "proxy_cases",
        "pro_observations",
        "adverse_events",
        "connector_sessions",
        "evaluation_cases",
        "model_versions",
    )
    return {
        name: int(connection.execute(f"select count(*) from {name}").fetchone()[0])
        for name in names
    }
