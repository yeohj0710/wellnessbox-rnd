import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_parser_case_id_mismatch_non_blocking_hold_regression() -> None:
    decision = _load_json("artifacts/reports/parser_case_id_mismatch_decision_v1.json")
    normalization_audit = _load_json(
        "artifacts/reports/sensor_genetic_normalization_audit_v1.json"
    )
    weakest_slice_summary = _load_json(
        "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
    )

    assert decision["decision_gate"]["blocks_kpi_interpretation"] is False
    assert (
        decision["decision_gate"]["decision"]
        == "mismatch_not_blocking_current_kpi_interpretation"
    )
    assert "weakest_metric_score_reproduced" in decision["decision_gate"]["reason_codes"]
    assert "direct_cgm_family_join_present" in decision["decision_gate"]["reason_codes"]
    assert (
        "fixture_case_ids_do_not_match_eval_case_ids"
        in decision["decision_gate"]["reason_codes"]
    )

    mismatch_summary = decision["evidence_summary"]["case_id_mismatch_summary"]
    assert mismatch_summary["parser_case_id_overlap_with_weakest_family"] == []
    assert mismatch_summary["parser_case_id_overlap_with_direct_cgm_family"] == []
    assert mismatch_summary["parser_case_ids_match_frozen_eval_case_ids_one_by_one"] is False

    assert (
        normalization_audit["frozen_eval_category_join"]["pooled_score_matches_weakest_metric"]
        is True
    )
    assert normalization_audit["direct_cgm_case_family_join"]["join_status"] == "connected"

    family_summary = next(
        item
        for item in weakest_slice_summary["case_family_summaries"]
        if item["family"] == "free_text_alias"
    )
    assert family_summary["coverage_status"] == "connected"
    assert family_summary["weakest_metrics"] == ["sensor_genetic_integration_rate_pct"]
    assert "parser_outputs" in family_summary["contracts_filled"]
    assert "cgm_slice_bridge_summary_v1" in family_summary["contracts_filled"]
