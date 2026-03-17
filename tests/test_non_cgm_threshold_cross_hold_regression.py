import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_non_cgm_threshold_cross_hold_regression() -> None:
    diagnostic = _load_json(
        "artifacts/reports/"
        "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
        "non_cgm_threshold_cross_diagnostic_v1.json"
    )
    reject_decision = _load_json(
        "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
    )

    target_family = diagnostic["target_family"]
    workflow_summary = diagnostic["workflow_summary"]
    case_summary = diagnostic["case_summary"]
    feature_summary = diagnostic["feature_summary"]
    interpretation = diagnostic["interpretation"]
    dominant_low_risk = reject_decision["regression_slices"]["dominant_low_risk_slice"]
    hold_context = reject_decision["hold_context"]

    assert target_family["name"] == "non_cgm_continue_to_monitor_threshold_cross"
    assert target_family["expected_case_count_from_compare"] == 26
    assert target_family["observed_case_count"] == 26
    assert target_family["transition"] == "continue_plan->monitor_only"
    assert target_family["non_cgm_only"] is True

    assert case_summary["all_cases_non_cgm"] is True
    assert case_summary["all_transitions_match_target"] is True
    assert case_summary["all_band_crosses_match_target"] is True
    assert case_summary["reference_continue_margin_summary"]["mean"] == 0.053676
    assert case_summary["proxy_drop_summary"]["mean"] == 0.080658

    assert workflow_summary["reference_continue_margin_bucket_counts"] == {
        "comfortable_margin": 7,
        "mid_margin": 19,
    }
    assert workflow_summary["proxy_drop_bucket_counts"] == {
        "large_drop": 9,
        "medium_drop": 9,
        "small_drop": 8,
    }
    assert workflow_summary["trajectory_mode_counts"]["threshold_duration_sensitive"] == 10
    assert workflow_summary["trajectory_mode_counts"]["threshold_monitor_secondary"] == 7
    assert workflow_summary["trajectory_mode_counts"]["threshold_reopt_edge"] == 4

    top_absolute_family = feature_summary["feature_family_delta_summary"][
        "top_absolute_families"
    ][0]
    top_negative_family = feature_summary["feature_family_delta_summary"][
        "top_negative_signed_families"
    ][0]
    top_absolute_feature = feature_summary["top_absolute_features"][0]
    reference_only_feature = feature_summary["reference_only_structural_top_features"][0]

    assert top_absolute_family["family"] == "intercept"
    assert top_absolute_family["value"] == 3.37753
    assert top_negative_family["family"] == "intercept"
    assert top_negative_family["value"] == -3.37753
    assert top_absolute_feature["feature"] == "__intercept__"
    assert reference_only_feature["feature"] == "sleep_hours"

    assert interpretation["threshold_edge_only_story_supported"] is False
    assert interpretation["near_edge_case_count"] == 0
    assert interpretation["non_edge_case_count"] == 26
    assert interpretation["dominant_feature_family"] == "intercept"
    assert interpretation["dominant_feature"] == "__intercept__"
    assert interpretation["reference_only_structural_delta_present"] is True

    assert dominant_low_risk["decision_family"] == "non_cgm_continue_to_monitor_threshold_cross"
    assert dominant_low_risk["observed_case_count"] == 26
    assert dominant_low_risk["dominant_feature_family"] == "intercept"
    assert hold_context["dominant_replay_regression_family"] == (
        "non_cgm_continue_to_monitor_threshold_cross"
    )
