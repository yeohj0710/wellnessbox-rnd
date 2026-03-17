import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_bone_joint_empty_anchor_hold_regression() -> None:
    decision = _load_json("artifacts/reports/bone_joint_weakest_family_decision_v1.json")
    weakest_slice_summary = _load_json(
        "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
    )

    assert decision["decision_gate"]["keep_explicit_empty_anchor"] is True
    assert decision["decision_gate"]["decision"] == "keep_explicit_empty_anchor"
    assert "single_case_anchor" in decision["decision_gate"]["reason_codes"]
    assert "family_metrics_all_passing" in decision["decision_gate"]["reason_codes"]
    assert "higher_roi_training_blockers_elsewhere" in decision["decision_gate"]["reason_codes"]

    family_summary = weakest_slice_summary["case_family_summaries"][0]
    assert family_summary["family"] == "bone_joint"
    assert family_summary["case_count"] == 1
    assert family_summary["coverage_status"] == "empty"
    assert family_summary["contracts_filled"] == []
    assert family_summary["weakest_metrics"] == [
        "adverse_event_count_yearly",
        "recommendation_coverage_pct",
    ]

    metric_anchor = weakest_slice_summary["frozen_eval_anchor"]["weakest_category_by_metric"]
    assert metric_anchor["recommendation_coverage_pct"]["category"] == "bone_joint"
    assert metric_anchor["recommendation_coverage_pct"]["passed"] is True
    assert metric_anchor["adverse_event_count_yearly"]["category"] == "bone_joint"
    assert metric_anchor["adverse_event_count_yearly"]["passed"] is True
