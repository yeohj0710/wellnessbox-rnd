import base64
import json
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.run_final_completion_audit import (
    SERVICE_ROOT,
    _audited_input_hashes,
    apply_answer_key_integrity_gate,
    assert_no_regression,
    audited_repository_commits,
    working_tree_status,
)
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


def test_answer_key_integrity_blocks_an_otherwise_ready_final_audit() -> None:
    audit = {"status": "READY", "goal_complete": True, "blockers": []}

    result = apply_answer_key_integrity_gate(
        audit,
        {"completion_status": "BLOCKED", "completion_blockers": ["KPI-1"]},
    )

    assert result["status"] == "BLOCKED"
    assert result["goal_complete"] is False
    assert "answer_key_integrity_failed" in result["blockers"]
    assert audit["status"] == "READY"


def test_answer_key_integrity_pass_preserves_final_audit_result() -> None:
    audit = {"status": "READY", "goal_complete": True, "blockers": []}

    result = apply_answer_key_integrity_gate(
        audit,
        {"completion_status": "READY", "completion_blockers": []},
    )

    assert result == audit


def test_fixed_cases_allow_monotonic_completion_progress() -> None:
    expected = {
        "requirement_inventory": {"requirement_count": 120},
        "claimed_inventory": {"claimed_requirement_count": 119},
        "required_stage_gaps": {"nonexternal_stage_gap_count": 43},
        "external_validation": {"external_validation_gap_ids": ["OP-039"]},
        "research_reports": {"report_count": 120, "missing_report_count": 0},
        "canonical_evidence": {"audit_passed": True},
        "completion_receipts": {"validation": False, "independent_review": False},
        "completion_decision": {"status": "BLOCKED", "goal_complete": False},
    }
    improved = {
        **expected,
        "completion_receipts": {"validation": True, "independent_review": True},
    }
    assert_no_regression(expected, improved)


def test_fixed_cases_still_reject_regression() -> None:
    expected = {
        "requirement_inventory": {"requirement_count": 120},
        "claimed_inventory": {"claimed_requirement_count": 119},
        "required_stage_gaps": {"nonexternal_stage_gap_count": 43},
        "external_validation": {"external_validation_gap_ids": ["OP-039"]},
        "research_reports": {"report_count": 120, "missing_report_count": 0},
        "canonical_evidence": {"audit_passed": True},
        "completion_receipts": {"validation": False, "independent_review": False},
        "completion_decision": {"status": "BLOCKED", "goal_complete": False},
    }
    regressed = {**expected, "claimed_inventory": {"claimed_requirement_count": 118}}
    try:
        assert_no_regression(expected, regressed)
    except AssertionError:
        return
    raise AssertionError("regression was accepted")
def test_audited_input_hashes_use_working_tree_and_record_heads() -> None:
    file_blobs = _audited_input_hashes()
    commits = audited_repository_commits(file_blobs)

    for reference, expected_blob in file_blobs.items():
        actual_blob = subprocess.check_output(
            [
                "git",
                "-C",
                str(SERVICE_ROOT if reference.startswith("wellnessbox/") else ROOT),
                "hash-object",
                reference.split("/", 1)[1],
            ],
            text=True,
        ).strip()
        assert actual_blob == expected_blob
    assert commits["wellnessbox"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=SERVICE_ROOT, text=True
    ).strip()
    assert commits["wellnessbox-rnd"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    status = working_tree_status(sorted(file_blobs))
    assert set(status["repository_heads"]) == {"wellnessbox-rnd", "wellnessbox"}
    assert isinstance(status["changed_paths"], list)


def test_current_repository_stays_blocked_without_separate_external_review() -> None:
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
    assert result.facts.external_validation_gap_ids == []
    assert result.blockers == [
        "validation_receipt_missing_or_invalid",
        "independent_review_receipt_missing_or_invalid",
    ]


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
