import json
from pathlib import Path

from wellnessbox_rnd.governance.final_completion_audit import (
    FinalCompletionFactsV1,
    FinalCompletionStatus,
    audit_final_completion_v1,
    evaluate_final_completion_facts_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import RepositoryName

ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_is_fail_closed() -> None:
    result = audit_final_completion_v1(
        manifest_path=ROOT / "data/original_plan/requirements_manifest_v1.json",
        reports_dir=ROOT / "docs/original_plan/research_reports",
        policy_path=ROOT / "data/original_plan/op120_final_audit_policy_v1.json",
        repository_roots={
            RepositoryName.WELLNESSBOX_RND: ROOT,
            RepositoryName.WELLNESSBOX: ROOT.parent / "wellnessbox",
        },
    )
    assert result.status == FinalCompletionStatus.BLOCKED
    assert result.goal_complete is False
    assert result.facts.requirement_count == 120
    assert "OP-039" in result.facts.external_validation_gap_ids


def test_only_all_satisfied_facts_are_ready() -> None:
    facts = FinalCompletionFactsV1(
        requirement_count=120,
        claimed_requirement_count=120,
        report_count=120,
        canonical_evidence_audit_passed=True,
        validation_receipt_valid=True,
        independent_review_receipt_valid=True,
    )
    result = evaluate_final_completion_facts_v1(facts)
    assert result.status == FinalCompletionStatus.READY
    assert result.goal_complete is True


def test_each_completion_dimension_blocks_independently() -> None:
    base = dict(
        requirement_count=120,
        claimed_requirement_count=120,
        report_count=120,
        canonical_evidence_audit_passed=True,
        validation_receipt_valid=True,
        independent_review_receipt_valid=True,
    )
    variants = [
        {"claimed_requirement_count": 119},
        {"nonexternal_stage_gap_ids": ["OP-120"]},
        {"external_validation_gap_ids": ["OP-039"]},
        {"report_count": 119, "missing_report_ids": ["OP-001"]},
        {"canonical_evidence_audit_passed": False},
        {"validation_receipt_valid": False},
        {"independent_review_receipt_valid": False},
    ]
    for variant in variants:
        result = evaluate_final_completion_facts_v1(FinalCompletionFactsV1(**(base | variant)))
        assert result.status == FinalCompletionStatus.BLOCKED
        assert result.goal_complete is False


def test_untracked_arbitrary_receipts_cannot_unlock_completion(tmp_path: Path) -> None:
    receipt = tmp_path / "forged.json"
    receipt.write_text(
        json.dumps({"status": "PASS", "critical_count": 0, "important_count": 0}), encoding="utf-8"
    )
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": "op120_final_audit_policy_v1",
                "required_requirement_count": 120,
                "required_report_count": 120,
                "validation_receipt_path": str(receipt),
                "independent_review_receipt_path": str(receipt),
            }
        ),
        encoding="utf-8",
    )
    result = audit_final_completion_v1(
        manifest_path=ROOT / "data/original_plan/requirements_manifest_v1.json",
        reports_dir=ROOT / "docs/original_plan/research_reports",
        policy_path=policy,
        repository_roots={
            RepositoryName.WELLNESSBOX_RND: ROOT,
            RepositoryName.WELLNESSBOX: ROOT.parent / "wellnessbox",
        },
    )
    assert result.facts.validation_receipt_valid is False
    assert result.facts.independent_review_receipt_valid is False
