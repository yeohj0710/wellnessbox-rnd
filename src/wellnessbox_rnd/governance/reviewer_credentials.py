"""Credential checks for the H-005 project pharmacist safety review.

The review screen collects a name, a licence number, how the credential was
verified, and whether the same person also reviewed H-003 drafts. None of those
answers were checked before: the owner block compared two exact strings, the
licence field accepted any non-empty text, the verification method was not read
at all, and the H-003 flag was believed on self-report. This module closes those
four gaps. It never decides a case and never fills a judgment in.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

REGISTRY_RELATIVE_PATH = "data/original_plan/contracts/op039_reviewer_identity_registry_v1.json"
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"))


def normalize_identity(value: str) -> str:
    """Fold a free-text person name down to something comparable."""
    folded = unicodedata.normalize("NFKC", str(value)).translate(_ZERO_WIDTH)
    return re.sub(r"\s+", "", folded).casefold()


def load_registry(root: Path) -> dict[str, Any]:
    path = Path(root) / REGISTRY_RELATIVE_PATH
    if not path.is_file():
        raise FileNotFoundError(f"reviewer_identity_registry_missing:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def blocked_identity_match(name: str, registry: dict[str, Any]) -> str | None:
    """Return the canonical blocked name when the reviewer is the owner or the system."""
    candidate = normalize_identity(name)
    if not candidate:
        return None
    for entry in registry.get("blocked_identities", []):
        names = [entry["canonical_name"], *entry.get("aliases", [])]
        if any(candidate == normalize_identity(item) for item in names):
            return str(entry["canonical_name"])
    return None


def license_id_problem(value: str, registry: dict[str, Any]) -> str | None:
    """Return why a licence number is unusable, or None when it looks real."""
    raw = str(value or "").strip()
    if not raw:
        return "license_id_missing"
    folded = normalize_identity(raw)
    placeholders = {
        normalize_identity(item) for item in registry.get("placeholder_license_ids", [])
    }
    if folded in placeholders:
        return "license_id_is_a_placeholder"
    minimum = int(registry.get("license_id_minimum_digits", 4))
    if sum(character.isdigit() for character in raw) < minimum:
        return f"license_id_needs_at_least_{minimum}_digits"
    return None


def credential_method_problem(value: str, registry: dict[str, Any]) -> str | None:
    """Return why the stated verification method is unusable, or None when it is specific."""
    raw = str(value or "").strip()
    if not raw:
        return "credential_verification_method_missing"
    folded = normalize_identity(raw)
    rejected = {
        normalize_identity(item) for item in registry.get("rejected_credential_methods", [])
    }
    if folded in rejected:
        return "credential_verification_method_is_self_or_owner_attestation"
    minimum = int(registry.get("credential_method_minimum_length", 8))
    if len(raw) < minimum:
        return f"credential_verification_method_needs_at_least_{minimum}_characters"
    return None


def ai_draft_reviewer_conflict(
    *, declared: Any, reviewer_name: str, draft_reviewer_ids: set[str]
) -> str | None:
    """Catch a reviewer who reviewed H-003 drafts but declared otherwise."""
    candidate = normalize_identity(reviewer_name)
    in_ledger = any(candidate == normalize_identity(item) for item in draft_reviewer_ids)
    if in_ledger and declared is not True:
        return "reviewer_appears_in_h003_draft_ledger_but_declared_otherwise"
    return None


def audit_reviewer_credentials(
    reviewer: dict[str, Any],
    *,
    registry: dict[str, Any],
    draft_reviewer_ids: set[str],
) -> dict[str, Any]:
    """Collect every credential problem at once so the reviewer sees them together."""
    name = str(reviewer.get("name", "")).strip()
    problems: list[str] = []

    blocked = blocked_identity_match(name, registry)
    if blocked is not None:
        problems.append(f"reviewer_is_a_blocked_identity:{blocked}")

    for problem in (
        license_id_problem(reviewer.get("pharmacist_license_id", ""), registry),
        credential_method_problem(reviewer.get("credential_verification_method", ""), registry),
        ai_draft_reviewer_conflict(
            declared=reviewer.get("was_ai_draft_reviewer"),
            reviewer_name=name,
            draft_reviewer_ids=draft_reviewer_ids,
        ),
    ):
        if problem is not None:
            problems.append(problem)

    warnings: list[str] = []
    if reviewer.get("was_ai_draft_reviewer") is True:
        warnings.append("reviewer_also_reviewed_ai_drafts")

    return {
        "schema_version": "op039_reviewer_credential_audit_v1",
        "status": "BLOCKED" if problems else "READY",
        "problems": problems,
        "warnings": warnings,
        "checked_against_draft_reviewer_count": len(draft_reviewer_ids),
    }


def load_draft_reviewer_ids(database_path: Path) -> set[str]:
    """Read the distinct H-003 reviewer names, tolerating a missing ledger."""
    import sqlite3

    path = Path(database_path)
    if not path.is_file():
        return set()
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "select distinct reviewer_id from ai_drafts where reviewer_id is not null"
        ).fetchall()
    except sqlite3.DatabaseError:
        return set()
    finally:
        connection.close()
    return {str(row[0]).strip() for row in rows if str(row[0] or "").strip()}
