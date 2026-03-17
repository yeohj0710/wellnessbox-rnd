import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_structured_safety_overlap_non_blocking_hold_regression() -> None:
    decision = _load_json("artifacts/reports/structured_safety_rule_overlap_decision_v1.json")
    audit = _load_json("artifacts/reports/weakest_slice_frozen_eval_audit_v1.json")

    assert (
        decision["decision_gate"]["decision"]
        == "partial_rule_overlap_not_blocking_current_kpi_interpretation"
    )
    assert decision["decision_gate"]["blocks_kpi_interpretation"] is False
    assert "workflow_branch_coverage_complete" in decision["decision_gate"]["reason_codes"]
    assert "structured_safety_rule_overlap_partial" in decision["decision_gate"]["reason_codes"]

    assert decision["evidence_summary"]["workflow_category_join"]["coverage_pct"] == 100.0
    assert decision["evidence_summary"]["safety_reference_metric"]["weakest_passed"] is True
    assert decision["evidence_summary"]["safety_reference_metric"]["overall_passed"] is True
    assert (
        decision["evidence_summary"]["structured_safety_rule_overlap"][
            "fixture_rule_overlap_pct_of_observed"
        ]
        == 20.0
    )

    safety_audit = audit["structured_safety_evidence_linkage_audit"]
    assert safety_audit["next_action_workflow_category_join"]["coverage_pct"] == 100.0
    assert safety_audit["frozen_eval_category_join"]["fixture_rule_overlap_count"] == 1
    assert (
        safety_audit["frozen_eval_category_join"][
            "workflow_contract_next_action_seen_in_family"
        ]
        is True
    )
    assert safety_audit["frozen_eval_category_join"]["fixture_next_action_seen_in_family"] is False
