from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


TABLES = (
    "user_profiles", "profile_snapshots", "behavior_events",
    "recommendation_runs", "recommendation_items", "agent_runs", "agent_steps",
    "followups", "pro_observations", "adverse_events", "workflow_jobs",
    "review_tasks", "ai_drafts",
)


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def database_counts(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {table: 0 for table in TABLES}
    with closing(sqlite3.connect(path)) as connection:
        existing = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
        return {
            table: int(connection.execute(f"select count(*) from {table}").fetchone()[0])
            if table in existing else 0
            for table in TABLES
        }


def source_commits(root: Path) -> dict[str, str]:
    return {
        name: subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        for name, path in (("wellnessbox-rnd", root), ("wellnessbox", root.parent / "wellnessbox"))
    }


def begin_session(root: Path, database: Path, urls: dict[str, str]) -> dict[str, Any]:
    started_at = now()
    return {
        "schema_version": "local_operational_session_capture_v1",
        "data_class": "ACTUAL",
        "environment_id": "wellnessbox-local-research-pc",
        "session_id": "local-" + started_at.replace(":", "").replace("-", "").replace(".", ""),
        "started_at": started_at,
        "source_commits": source_commits(root),
        "urls": urls,
        "database_counts_before": database_counts(database),
    }


def finish_session(
    root: Path,
    database: Path,
    capture: dict[str, Any],
    output_directory: Path,
    *,
    key_path: Path | None,
    data_class: str = "ACTUAL",
) -> dict[str, Any]:
    mapping_path = root / "data/original_plan/operational_action_coverage_v1.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    before = capture["database_counts_before"]
    after = database_counts(database)
    delta = {table: after[table] - int(before.get(table, 0)) for table in TABLES}
    observed: list[str] = []
    for action, signals in mapping["signals"].items():
        if action != "completed_session" and any(delta.get(table, 0) > 0 for table in signals):
            observed.append(action)
    if observed:
        observed.append("completed_session")
    covered = sorted({op for action in observed for op in mapping["actions"][action]})
    payload = {
        "schema_version": "local_operational_session_receipt_v1",
        "data_class": data_class,
        "environment_id": capture["environment_id"],
        "session_id": capture["session_id"],
        "started_at": capture["started_at"],
        "ended_at": now(),
        "source_commits": capture["source_commits"],
        "executed_paths": [action for action in observed if action != "completed_session"],
        "database_count_delta": delta,
        "covered_requirement_ids": covered,
        "coverage_mapping_path": "data/original_plan/operational_action_coverage_v1.json",
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    receipt = {**payload, "payload_sha256": hashlib.sha256(canonical).hexdigest()}
    if key_path and key_path.is_file():
        private = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if not isinstance(private, Ed25519PrivateKey):
            raise ValueError("운영 영수증 키는 Ed25519여야 합니다.")
        receipt["signature_ed25519_base64"] = base64.b64encode(private.sign(canonical)).decode()
        receipt["issuer_id"] = "웰니스박스"
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / f"{capture['session_id']}.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**receipt, "receipt_path": str(path.resolve())}
