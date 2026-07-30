"""Build a training dataset manifest that contains approved AI drafts only.

H-003 requires a verifiable chain from pharmacist-approved drafts to whatever a
candidate model is trained on. This module is the first link: it reads the AI
draft ledger, keeps only rows a human reviewer approved, and records why every
other row was excluded. Pending and rejected drafts never reach the manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "approved_draft_dataset_manifest_v1"
APPROVED_STATUSES = ("approved", "approved_with_edits")
OWNER_REVIEWER_IDS = ("여형준", "웰니스박스")

_SELECT_DRAFTS = (
    "select draft_id, record_type, review_status, reviewer_id, reviewed_at, "
    "model_identifier, prompt_version, content_json, created_at, row_sha256 "
    "from ai_drafts order by created_at, draft_id"
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _exclusion_reason(row: dict[str, Any], owner_reviewer_ids: frozenset[str]) -> str | None:
    status = str(row["review_status"])
    if status == "pending":
        return "pending_review"
    if status == "rejected":
        return "rejected_by_reviewer"
    if status not in APPROVED_STATUSES:
        return "unknown_review_status"
    reviewer = str(row["reviewer_id"] or "").strip()
    if not reviewer:
        return "reviewer_id_missing"
    if reviewer in owner_reviewer_ids:
        return "reviewed_by_owner_or_system_account"
    if not str(row["reviewed_at"] or "").strip():
        return "reviewed_at_missing"
    return None


def build_approved_draft_dataset_manifest_v1(
    rows: list[dict[str, Any]],
    *,
    database_path: str | Path,
    database_sha256: str,
    owner_reviewer_ids: tuple[str, ...] = OWNER_REVIEWER_IDS,
) -> dict[str, Any]:
    """Return a manifest holding only drafts a non-owner human approved."""
    excluded_accounts = frozenset(owner_reviewer_ids)
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in rows:
        reason = _exclusion_reason(row, excluded_accounts)
        if reason is not None:
            excluded.append({"draft_id": str(row["draft_id"]), "reason": reason})
            continue
        included.append(
            {
                "draft_id": str(row["draft_id"]),
                "record_type": str(row["record_type"]),
                "review_status": str(row["review_status"]),
                "reviewer_id": str(row["reviewer_id"]).strip(),
                "reviewed_at": str(row["reviewed_at"]),
                "model_identifier": str(row["model_identifier"]),
                "prompt_version": str(row["prompt_version"]),
                "content_sha256": _sha256_text(str(row["content_json"])),
                "row_sha256": str(row["row_sha256"]),
            }
        )

    leaked = [item for item in included if item["review_status"] not in APPROVED_STATUSES]
    if leaked:
        raise ValueError(f"unapproved_draft_in_training_manifest:{[i['draft_id'] for i in leaked]}")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "draft_ledger_path": str(Path(database_path).resolve()),
            "draft_ledger_sha256": database_sha256,
            "owner_reviewer_ids": sorted(owner_reviewer_ids),
        },
        "selection_rule": (
            "review_status in ('approved','approved_with_edits') and the reviewer is a named "
            "human other than the project owner or the system account"
        ),
        "counts": {
            "ledger_row_count": len(rows),
            "included_count": len(included),
            "excluded_count": len(excluded),
            "excluded_by_reason": _count_reasons(excluded),
        },
        "included_drafts": included,
        "excluded_drafts": excluded,
    }
    manifest["dataset_sha256"] = _sha256_text(_canonical(included))
    return manifest


def _count_reasons(excluded: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in excluded:
        counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    return dict(sorted(counts.items()))


def load_draft_rows(database_path: str | Path) -> tuple[list[dict[str, Any]], str]:
    """Read the AI draft ledger read-only and return its rows plus the file digest."""
    import sqlite3

    path = Path(database_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"draft_ledger_not_found:{path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(_SELECT_DRAFTS)]
    finally:
        connection.close()
    return rows, digest


def verify_manifest_is_approved_only(manifest: dict[str, Any]) -> dict[str, Any]:
    """Re-check a stored manifest without trusting the counts written into it."""
    included = manifest.get("included_drafts", [])
    violations = [
        item["draft_id"]
        for item in included
        if item.get("review_status") not in APPROVED_STATUSES
        or not str(item.get("reviewer_id", "")).strip()
        or str(item.get("reviewer_id", "")).strip() in set(manifest["source"]["owner_reviewer_ids"])
    ]
    recomputed = _sha256_text(_canonical(included))
    return {
        "schema_version": "approved_draft_dataset_manifest_check_v1",
        "status": "READY" if not violations and recomputed == manifest.get("dataset_sha256")
        else "BLOCKED",
        "included_count": len(included),
        "violation_draft_ids": violations,
        "dataset_sha256_matches": recomputed == manifest.get("dataset_sha256"),
        "recomputed_dataset_sha256": recomputed,
    }
