from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.governance.original_plan_audit import (
    OriginalPlanAuditStatus,
    audit_original_plan_manifest_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    EvidenceStage,
    RepositoryName,
    load_original_plan_manifest_v1,
    materialize_original_plan_requirements_v1,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinalCompletionStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class FinalCompletionFactsV1(_StrictModel):
    requirement_count: int
    claimed_requirement_count: int
    nonexternal_stage_gap_ids: list[str] = Field(default_factory=list)
    external_validation_gap_ids: list[str] = Field(default_factory=list)
    report_count: int
    missing_report_ids: list[str] = Field(default_factory=list)
    canonical_evidence_audit_passed: bool
    validation_receipt_valid: bool
    independent_review_receipt_valid: bool


class FinalCompletionAuditV1(_StrictModel):
    status: FinalCompletionStatus
    goal_complete: bool
    facts: FinalCompletionFactsV1
    blockers: list[str] = Field(default_factory=list)


def evaluate_final_completion_facts_v1(
    facts: FinalCompletionFactsV1,
) -> FinalCompletionAuditV1:
    blockers: list[str] = []
    if facts.requirement_count != 120:
        blockers.append(f"requirement_count:{facts.requirement_count}!=120")
    if facts.claimed_requirement_count != 120:
        blockers.append(f"claimed_requirement_count:{facts.claimed_requirement_count}!=120")
    if facts.nonexternal_stage_gap_ids:
        blockers.append(f"nonexternal_stage_gaps:{len(facts.nonexternal_stage_gap_ids)}")
    if facts.external_validation_gap_ids:
        blockers.append(
            f"external_validation_gaps:{len(facts.external_validation_gap_ids)}"
        )
    if facts.report_count != 120 or facts.missing_report_ids:
        blockers.append(f"research_report_gaps:{len(facts.missing_report_ids)}")
    if not facts.canonical_evidence_audit_passed:
        blockers.append("canonical_evidence_audit_failed")
    if not facts.validation_receipt_valid:
        blockers.append("validation_receipt_missing_or_invalid")
    if not facts.independent_review_receipt_valid:
        blockers.append("independent_review_receipt_missing_or_invalid")
    status = FinalCompletionStatus.READY if not blockers else FinalCompletionStatus.BLOCKED
    return FinalCompletionAuditV1(
        status=status,
        goal_complete=status == FinalCompletionStatus.READY,
        facts=facts,
        blockers=blockers,
    )


def audit_final_completion_v1(
    *,
    manifest_path: str | Path,
    reports_dir: str | Path,
    policy_path: str | Path,
    repository_roots: dict[RepositoryName | str, str | Path],
) -> FinalCompletionAuditV1:
    manifest = load_original_plan_manifest_v1(manifest_path)
    requirements = materialize_original_plan_requirements_v1(manifest)
    canonical_audit = audit_original_plan_manifest_v1(
        manifest, repository_roots=repository_roots
    )
    stage_rank = {
        EvidenceStage.IMPLEMENTED: 1,
        EvidenceStage.INTEGRATED: 2,
        EvidenceStage.OPERATED: 3,
    }
    nonexternal_gaps = [
        item.requirement_id
        for item in requirements
        if item.required_stage != EvidenceStage.EXTERNAL
        and (
            item.claimed_stage not in stage_rank
            or stage_rank[item.claimed_stage] < stage_rank[item.required_stage]
        )
    ]
    external_gaps = [
        item.requirement_id
        for item in requirements
        if item.required_stage == EvidenceStage.EXTERNAL
        and item.claimed_stage != EvidenceStage.EXTERNAL
    ]
    report_root = Path(reports_dir)
    missing_reports = [
        item.requirement_id
        for item in requirements
        if not (report_root / f"{item.requirement_id}.md").is_file()
    ]
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    validation_receipt = policy.get("validation_receipt_path")
    review_receipt = policy.get("independent_review_receipt_path")
    facts = FinalCompletionFactsV1(
        requirement_count=len(requirements),
        claimed_requirement_count=sum(item.claimed_stage is not None for item in requirements),
        nonexternal_stage_gap_ids=nonexternal_gaps,
        external_validation_gap_ids=external_gaps,
        report_count=len(requirements) - len(missing_reports),
        missing_report_ids=missing_reports,
        canonical_evidence_audit_passed=canonical_audit.status
        == OriginalPlanAuditStatus.PASS,
        validation_receipt_valid=_receipt_valid(validation_receipt, "PASS"),
        independent_review_receipt_valid=_review_receipt_valid(review_receipt),
    )
    return evaluate_final_completion_facts_v1(facts)


def _receipt_valid(reference: object, expected_status: str) -> bool:
    if not isinstance(reference, str):
        return False
    path = Path(reference)
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return payload.get("status") == expected_status


def _review_receipt_valid(reference: object) -> bool:
    if not isinstance(reference, str):
        return False
    path = Path(reference)
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        payload.get("status") == "PASS"
        and payload.get("critical_count") == 0
        and payload.get("important_count") == 0
    )
