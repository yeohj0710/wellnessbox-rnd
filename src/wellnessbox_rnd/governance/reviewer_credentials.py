"""Identity and qualification checks for the H-005 safety review.

2차년도인 지금 검토자는 아직 면허를 받지 않은 예비 약사다. 그래서 면허 번호나
자격 확인 방법을 받지 않는다. 받아도 존재하지 않는 값이기 때문이다. 대신 이름과
소속만 받고, 두 값을 과제 등록 정보와 대조한 뒤 검토를 "예비 약사 사전 검토"로
기록한다. 면허를 받는 3차년도에 같은 사람이 약사 자격으로 다시 검토해야 최종
근거가 된다.

이 모듈은 사례를 판정하지 않고 판정 값을 채우지도 않는다.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

REGISTRY_RELATIVE_PATH = "data/original_plan/contracts/op039_reviewer_identity_registry_v1.json"
PHARMACIST_CANDIDATE = "pharmacist_candidate"
LICENSED_PHARMACIST = "licensed_pharmacist"
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"))
IDENTITY_REFERENCE_PREFIX = "registry:op039:sha256:"


def reviewer_identity_reference(entry: dict[str, Any]) -> str:
    """Create a stable opaque reference to one registered project participant."""
    stable_record = {
        "name": str(entry.get("name", "")).strip(),
        "organization": str(entry.get("organization", "")).strip(),
        "role_in_project": str(entry.get("role_in_project", "")).strip(),
    }
    encoded = json.dumps(
        stable_record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return IDENTITY_REFERENCE_PREFIX + hashlib.sha256(encoded).hexdigest()


def registered_reviewer_identity_references(registry: dict[str, Any]) -> set[str]:
    """Return only references that resolve to the checked-in participant registry."""
    return {
        reviewer_identity_reference(entry)
        for entry in registry.get("registered_reviewers", [])
        if str(entry.get("name", "")).strip()
    }


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


def registered_reviewer(name: str, registry: dict[str, Any]) -> dict[str, Any] | None:
    """Find the reviewer in the project participant list."""
    candidate = normalize_identity(name)
    for entry in registry.get("registered_reviewers", []):
        if candidate == normalize_identity(entry["name"]):
            return entry
    return None


def organization_matches(declared: str, registered: dict[str, Any]) -> bool:
    """Compare the typed organization with the one on file for that participant."""
    return normalize_identity(declared) == normalize_identity(registered["organization"])


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
    """Check who the reviewer is and what they are qualified to claim right now."""
    name = str(reviewer.get("name", "")).strip()
    organization = str(reviewer.get("organization", "")).strip()
    stage_contract = registry.get("qualification_stage", {})
    problems: list[str] = []

    blocked = blocked_identity_match(name, registry)
    if blocked is not None:
        problems.append(f"reviewer_is_a_blocked_identity:{blocked}")

    if not name:
        problems.append("reviewer_name_missing")
    if not organization:
        problems.append("reviewer_organization_missing")

    entry = registered_reviewer(name, registry) if name else None
    if name and blocked is None:
        if entry is None:
            problems.append("reviewer_is_not_a_registered_project_participant")
        elif not entry.get("may_review_h005"):
            problems.append("registered_participant_may_not_review_h005")
        elif organization and not organization_matches(organization, entry):
            problems.append("reviewer_organization_does_not_match_the_project_record")

    conflict = ai_draft_reviewer_conflict(
        declared=reviewer.get("was_ai_draft_reviewer"),
        reviewer_name=name,
        draft_reviewer_ids=draft_reviewer_ids,
    )
    if conflict is not None:
        problems.append(conflict)

    declared_stage = str(reviewer.get("qualification_stage", "")).strip()
    current_stage = str(stage_contract.get("current_stage", PHARMACIST_CANDIDATE))
    if declared_stage and declared_stage != current_stage:
        problems.append(f"qualification_stage_must_be:{current_stage}")

    warnings: list[str] = []
    if reviewer.get("was_ai_draft_reviewer") is True:
        warnings.append("reviewer_also_reviewed_ai_drafts")
    if current_stage == PHARMACIST_CANDIDATE:
        warnings.append("review_performed_before_licensure_requires_year3_reconfirmation")

    return {
        "schema_version": "op039_reviewer_credential_audit_v1",
        "status": "BLOCKED" if problems else "READY",
        "problems": problems,
        "warnings": warnings,
        "qualification_stage": current_stage,
        "license_status": stage_contract.get("license_status", "not_yet_licensed"),
        "expected_licensure_period": stage_contract.get("expected_licensure_period"),
        "requires_licensed_reconfirmation": current_stage != LICENSED_PHARMACIST,
        "matched_participant": entry["name"] if entry else None,
        "checked_against_draft_reviewer_count": len(draft_reviewer_ids),
    }


def review_character_for(stage: str) -> str:
    """Name the evidence so a preliminary review is never read as a licensed one."""
    if stage == LICENSED_PHARMACIST:
        return "licensed_pharmacist_expert_safety_review"
    return "pharmacist_candidate_preliminary_safety_review"


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
