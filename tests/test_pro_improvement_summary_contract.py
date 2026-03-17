from wellnessbox_rnd.metrics.calculators import percentile_improvement_pp
from wellnessbox_rnd.metrics.pro_scoring import (
    summarize_pro_improvement_from_event_v1,
    summarize_pro_improvement_summary_contract_v1,
    validate_pro_improvement_summary_from_event_v1,
)
from wellnessbox_rnd.schemas.pro_events import build_baseline_followup_pro_event_v1
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import generate_rich_synthetic_cohort_v4


def test_pro_improvement_summary_uses_same_normalized_baseline_follow_up_shape() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=701, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record)

    summary = summarize_pro_improvement_from_event_v1(event)

    assert set(event.baseline.model_dump(mode="json")) == {
        "timepoint",
        "aggregate_z",
        "domain_z",
        "aggregate_percentile",
        "domain_percentile",
    }
    assert set(event.baseline.model_dump(mode="json")) == set(
        event.follow_up.model_dump(mode="json")
    )
    assert summary.baseline_aggregate_z == event.baseline.aggregate_z
    assert summary.follow_up_aggregate_z == event.follow_up.aggregate_z
    assert summary.baseline_aggregate_percentile == event.baseline.aggregate_percentile
    assert summary.follow_up_aggregate_percentile == event.follow_up.aggregate_percentile
    assert summary.aggregate_delta_pp == round(
        percentile_improvement_pp(
            z_pre=event.baseline.aggregate_z,
            z_post=event.follow_up.aggregate_z,
        ),
        6,
    )
    assert summary.aggregate_delta_pp == round(
        event.follow_up.aggregate_percentile - event.baseline.aggregate_percentile,
        6,
    )


def test_validate_pro_improvement_summary_from_event_v1_flags_delta_pp_mismatch() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=702, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record)
    summary = summarize_pro_improvement_from_event_v1(event).model_copy(
        update={"aggregate_delta_pp": 999.0}
    )

    issues = validate_pro_improvement_summary_from_event_v1(
        event=event,
        summary=summary,
    )

    assert any(issue.startswith("aggregate_delta_pp_mismatch::") for issue in issues)


def test_summarize_pro_improvement_summary_contract_v1_proves_end_to_end_shared_path() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=703, user_count=24)

    report = summarize_pro_improvement_summary_contract_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )

    assert report["case_count"] == len(records)
    assert report["path_status"]["derived_directly_from_shared_event_contract"] is True
    assert report["path_status"]["baseline_follow_up_same_normalized_structure_case_count"] == len(
        records
    )
    assert report["path_status"]["frozen_eval_compatible"] is True
    assert report["consistency_checks"]["delta_pp_matches_percentile_diff_all_valid_cases"] is True
    assert report["path_status"]["event_to_summary_valid_case_count"] == len(records)
    assert report["path_status"]["event_to_summary_invalid_case_count"] == 0
