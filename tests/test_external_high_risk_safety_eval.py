from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import wellnessbox_rnd.evals.external_high_risk_safety as external_eval
from wellnessbox_rnd.evals.external_high_risk_safety import (
    ExternalHighRiskEvalContractError,
    run_external_high_risk_safety_eval,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationResponse


def _urgent_request(case_id: str) -> dict[str, object]:
    return {
        "request_id": f"external-{case_id}",
        "user_profile": {"age": 52, "biological_sex": "male", "pregnant": False},
        "goals": ["heart_health"],
        "symptoms": [
            {"code": "chest_pressure", "severity": "critical", "duration_days": 0}
        ],
        "conditions": [],
        "risk_flags": [
            {
                "code": "red_flag_chest_pain",
                "present": True,
                "source": "self_report",
            }
        ],
        "medications": [],
        "current_supplements": [],
        "input_availability": {"survey": True},
    }


def _write_bundle(
    tmp_path: Path,
    *,
    case_count: int = 2,
    minimum_case_count: int | None = None,
    minimum_emergency_cases: int | None = None,
    dataset_sha256: str | None = None,
    source_kind: str = "independent_clinical_review",
    independent: bool = True,
    organization: str = "Independent Clinical Safety Board",
    approve_attestation: bool = True,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    dataset_path = tmp_path / "externally_labeled_high_risk.jsonl"
    rows = [
        {
            "schema_version": "external_high_risk_safety_case_v2",
            "case_id": f"ext-clinical-{index:03d}",
            "risk_tier": "high",
            "expected_final_disposition": "blocked",
            "hazard_stratum": "emergency_symptom",
            "expected_blocking_rule_ids": ["SAFETY-URGENT-SYMPTOM-001"],
            "label_basis": "Independent review requires an urgent final safety block.",
            "request": _urgent_request(f"case-{index:03d}"),
        }
        for index in range(1, case_count + 1)
    ]
    dataset_bytes = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")
    dataset_path.write_bytes(dataset_bytes)
    actual_dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

    attestation_path = tmp_path / "detached_attestation.json"
    attestation_path.write_text(
        json.dumps(
            {
                "schema_version": "external_high_risk_safety_attestation_v2",
                "attestation_id": "EXT-CLINICAL-ATTESTATION-2026-001",
                "dataset_id": "external-high-risk-safety-2026-001",
                "dataset_sha256": dataset_sha256 or actual_dataset_hash,
                "case_count": case_count,
                "source_kind": source_kind,
                "review_organization": organization,
                "reviewer_role": "licensed_pharmacist",
                "independent_of_implementation_team": independent,
                "labeling_protocol_reference": "EXT-SAFETY-LABEL-PROTOCOL-001",
                "attestation_reference": "EXT-CLINICAL-ATTESTATION-2026-001",
                "labeling_started_at": "2026-07-15T02:00:00+09:00",
                "attested_at": "2026-07-16T10:00:00+09:00",
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    attestation_hash = hashlib.sha256(attestation_path.read_bytes()).hexdigest()

    receipt_path = tmp_path / "verification_receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": "external_high_risk_safety_verification_receipt_v1",
                "attestation_sha256": attestation_hash,
                "verification_status": "verified",
                "verifier_organization": "Independent Research Integrity Office",
                "verifier_role": "external_evidence_auditor",
                "independent_of_implementation_team": True,
                "verification_method": "issuer identity and detached file integrity review",
                "verification_reference": "EXT-INTEGRITY-RECEIPT-2026-001",
                "verified_at": "2026-07-16T11:00:00+09:00",
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    receipt_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

    coverage_protocol_path = tmp_path / "frozen_coverage_protocol.json"
    coverage_protocol_path.write_text(
        json.dumps(
            {
                "schema_version": "external_high_risk_safety_coverage_protocol_v1",
                "protocol_id": "EXT-SAFETY-COVERAGE-PROTOCOL-2026-001",
                "frozen_at": "2026-07-15T00:00:00+09:00",
                "labeling_protocol_reference": "EXT-SAFETY-LABEL-PROTOCOL-001",
                "minimum_case_count": minimum_case_count or case_count,
                "minimum_cases_per_hazard_stratum": {
                    "emergency_symptom": minimum_emergency_cases or case_count
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    coverage_protocol_hash = hashlib.sha256(
        coverage_protocol_path.read_bytes()
    ).hexdigest()
    coverage_roots_path = tmp_path / "repository_coverage_trust_roots.json"
    coverage_roots_path.write_text(
        json.dumps(
            {
                "schema_version": "external_high_risk_safety_coverage_trust_roots_v1",
                "frozen_at": "2026-07-15T01:00:00+09:00",
                "approval_authority": "Independent Evidence Governance Board",
                "approved_coverage_protocols": [
                    {
                        "coverage_protocol_sha256": coverage_protocol_hash,
                        "approval_reference": "EXT-COVERAGE-APPROVAL-2026-001",
                    }
                ],
                "approval_record_references": ["EXT-COVERAGE-APPROVAL-2026-001"],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    attestation_roots_path = tmp_path / "repository_attestation_trust_roots.json"
    attestation_roots_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    "external_high_risk_safety_attestation_trust_roots_v1"
                ),
                "frozen_at": "2026-07-16T12:00:00+09:00",
                "approval_authority": "Independent Evidence Governance Board",
                "approved_attestations": [
                    {
                        "dataset_id": "external-high-risk-safety-2026-001",
                        "coverage_protocol_sha256": coverage_protocol_hash,
                        "labeling_protocol_reference": (
                            "EXT-SAFETY-LABEL-PROTOCOL-001"
                        ),
                        "approval_reference": (
                            "EXT-ATTESTATION-APPROVAL-2026-001"
                        ),
                        "attestation_sha256": (
                            attestation_hash if approve_attestation else "f" * 64
                        ),
                        "verification_receipt_sha256": receipt_hash,
                    }
                ],
                "approval_record_references": [
                    "EXT-ATTESTATION-APPROVAL-2026-001"
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return (
        dataset_path,
        attestation_path,
        receipt_path,
        coverage_protocol_path,
        coverage_roots_path,
        attestation_roots_path,
    )


def _run(paths, monkeypatch, **kwargs):
    (
        dataset,
        attestation,
        receipt,
        coverage_protocol,
        coverage_roots,
        attestation_roots,
    ) = paths
    monkeypatch.setattr(external_eval, "COVERAGE_TRUST_ROOTS_PATH", coverage_roots)
    monkeypatch.setattr(
        external_eval, "ATTESTATION_TRUST_ROOTS_PATH", attestation_roots
    )
    monkeypatch.setattr(
        external_eval,
        "_engine_git_identity",
        lambda: ("a" * 40, "b" * 40),
    )
    return run_external_high_risk_safety_eval(
        dataset_path=dataset,
        attestation_path=attestation,
        verification_receipt_path=receipt,
        coverage_protocol_path=coverage_protocol,
        **kwargs,
    )


def test_verified_external_eval_reports_zero_hard_false_negatives(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_bundle(tmp_path)
    output_path = tmp_path / "report.json"

    report = _run(paths, monkeypatch, output_path=output_path)

    assert report.status == "PASS"
    assert report.attestation_authenticity == "verified_by_frozen_trust_registry"
    assert report.case_count == 2
    assert report.cases_by_hazard_stratum == {"emergency_symptom": 2}
    assert report.hard_false_negative_count == 0
    assert report.rule_mismatch_case_ids == []
    assert report.matched_rule_versions["SAFETY-URGENT-SYMPTOM-001"]
    assert len(report.engine_code_commit) == 40
    assert report.engine_git_tree_sha1 == "b" * 40
    assert output_path.read_text(encoding="utf-8") == (
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def test_wrong_blocking_reason_is_a_hard_false_negative(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_bundle(tmp_path, case_count=1)

    def wrong_rule_recommendation(request) -> RecommendationResponse:
        response = recommend(request)
        return response.model_copy(
            update={
                "safety_summary": response.safety_summary.model_copy(
                    update={"rule_refs": []}
                )
            }
        )

    report = _run(paths, monkeypatch, recommend_fn=wrong_rule_recommendation)

    assert report.status == "FAIL"
    assert report.hard_false_negative_case_ids == ["ext-clinical-001"]
    assert report.rule_mismatch_case_ids == ["ext-clinical-001"]


def test_non_blocked_decision_is_a_hard_false_negative(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_bundle(tmp_path, case_count=1)

    def unsafe_recommendation(request) -> RecommendationResponse:
        response = recommend(request)
        payload = response.model_dump(mode="json")
        payload["status"] = "ok"
        payload["safety_summary"]["status"] = "ok"
        uncertainty = payload["decision_uncertainty"]
        uncertainty["components"].append(
            {
                "code": "candidate_availability:no_selection",
                "source": "candidate_availability",
                "points": 0.15,
                "basis_codes": ["no_selected_candidate"],
            }
        )
        uncertainty["raw_uncertainty_score"] = round(
            uncertainty["raw_uncertainty_score"] + 0.15,
            6,
        )
        uncertainty["uncertainty_score"] = min(
            1.0,
            uncertainty["raw_uncertainty_score"],
        )
        uncertainty["uncertainty_band"] = "moderate"
        return RecommendationResponse.model_validate(payload)

    report = _run(paths, monkeypatch, recommend_fn=unsafe_recommendation)

    assert report.status == "FAIL"
    assert report.hard_false_negative_case_ids == ["ext-clinical-001"]


def test_eval_rejects_unapproved_attestation(tmp_path: Path, monkeypatch) -> None:
    paths = _write_bundle(tmp_path, approve_attestation=False)
    with pytest.raises(ExternalHighRiskEvalContractError, match="not pinned"):
        _run(paths, monkeypatch)


def test_eval_rejects_coverage_protocol_not_pinned_by_repository(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _write_bundle(tmp_path)
    monkeypatch.setattr(
        external_eval,
        "COVERAGE_TRUST_ROOTS_PATH",
        external_eval.PROJECT_ROOT
        / "data"
        / "original_plan"
        / "contracts"
        / "op039_external_coverage_trust_roots_v1.json",
    )
    dataset, attestation, receipt, coverage_protocol, _coverage_roots, attestation_roots = paths
    monkeypatch.setattr(
        external_eval, "ATTESTATION_TRUST_ROOTS_PATH", attestation_roots
    )
    with pytest.raises(ExternalHighRiskEvalContractError, match="not pinned"):
        run_external_high_risk_safety_eval(
            dataset_path=dataset,
            attestation_path=attestation,
            verification_receipt_path=receipt,
            coverage_protocol_path=coverage_protocol,
        )


def test_eval_rejects_coverage_protocol_frozen_after_attestation(
    tmp_path: Path, monkeypatch
) -> None:
    paths = list(_write_bundle(tmp_path))
    coverage_protocol_path = paths[3]
    coverage_protocol = json.loads(coverage_protocol_path.read_text(encoding="utf-8"))
    coverage_protocol["frozen_at"] = "2026-07-17T00:00:00+09:00"
    coverage_protocol_path.write_text(
        json.dumps(coverage_protocol, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    coverage_roots_path = paths[4]
    coverage_roots = json.loads(coverage_roots_path.read_text(encoding="utf-8"))
    coverage_roots["approved_coverage_protocols"] = [
        {
            "coverage_protocol_sha256": hashlib.sha256(
                coverage_protocol_path.read_bytes()
            ).hexdigest(),
            "approval_reference": "EXT-COVERAGE-APPROVAL-2026-001",
        }
    ]
    coverage_roots_path.write_text(
        json.dumps(coverage_roots, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    with pytest.raises(ExternalHighRiskEvalContractError, match="must precede"):
        _run(tuple(paths), monkeypatch)


def test_eval_rejects_frozen_coverage_shortfall(tmp_path: Path, monkeypatch) -> None:
    paths = _write_bundle(
        tmp_path,
        case_count=1,
        minimum_case_count=2,
        minimum_emergency_cases=2,
    )
    with pytest.raises(ExternalHighRiskEvalContractError, match="minimum_case_count"):
        _run(paths, monkeypatch)


def test_eval_rejects_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    paths = _write_bundle(tmp_path, dataset_sha256="0" * 64)
    with pytest.raises(ExternalHighRiskEvalContractError, match="dataset SHA-256"):
        _run(paths, monkeypatch)


@pytest.mark.parametrize(
    ("source_kind", "independent", "organization", "expected"),
    [
        ("internal_regression", True, "Independent Board", "source_kind"),
        (
            "independent_clinical_review",
            False,
            "Independent Board",
            "independent_of_implementation_team",
        ),
        (
            "independent_clinical_review",
            True,
            "synthetic test organization",
            "placeholder or internal provenance",
        ),
    ],
)
def test_eval_rejects_non_external_attestation(
    tmp_path: Path,
    monkeypatch,
    source_kind: str,
    independent: bool,
    organization: str,
    expected: str,
) -> None:
    paths = _write_bundle(
        tmp_path,
        source_kind=source_kind,
        independent=independent,
        organization=organization,
    )
    with pytest.raises(ExternalHighRiskEvalContractError, match=expected):
        _run(paths, monkeypatch)


def test_eval_rejects_repository_internal_dataset_path(
    tmp_path: Path, monkeypatch
) -> None:
    internal_root = tmp_path / "data" / "frozen_eval"
    internal_root.mkdir(parents=True)
    paths = _write_bundle(internal_root, case_count=1)
    with pytest.raises(ExternalHighRiskEvalContractError, match="internal or synthetic"):
        _run(paths, monkeypatch)
