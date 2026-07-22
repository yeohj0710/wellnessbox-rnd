import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wellnessbox_rnd.governance.final_completion_audit import (
    CompletionReceiptV1,
    FinalCompletionFactsV1,
    FinalCompletionStatus,
    TrustedIssuerV1,
    _signature_valid,
    _valid_research_report,
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


def test_receipt_requires_allowlisted_valid_signature() -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    unsigned = {
        "schema_version": "final_validation_receipt_v1",
        "status": "PASS",
        "manifest_sha256": "1" * 64,
        "canonical_audit_sha256": "2" * 64,
        "source_commit": "3" * 40,
        "issuer_id": "external-auditor",
    }
    message = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    receipt = CompletionReceiptV1(
        **unsigned,
        signature_ed25519_base64=base64.b64encode(private_key.sign(message)).decode(),
    )
    issuer = TrustedIssuerV1(
        issuer_id="external-auditor",
        public_key_ed25519_base64=base64.b64encode(public_key).decode(),
    )
    assert _signature_valid(receipt, [issuer]) is True
    assert _signature_valid(receipt.model_copy(update={"status": "FAIL"}), [issuer]) is False
    assert _signature_valid(receipt, []) is False


def test_padded_report_without_required_semantics_is_rejected(tmp_path: Path) -> None:
    report = tmp_path / "OP-001.md"
    report.write_text(
        "# OP-001 filler\n\n## a\n" + "x" * 200 + "\n## b\n" + "y" * 200 + "\n## c\n" + "z" * 200,
        encoding="utf-8",
    )
    assert (
        _valid_research_report(
            report, "OP-001", ["wellnessbox-rnd/data/original_plan/evidence/op001.json"]
        )
        is False
    )
