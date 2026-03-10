from wellnessbox_rnd.synthetic.longitudinal import (
    generate_synthetic_longitudinal_cohort,
    summarize_synthetic_cohort,
    validate_synthetic_cohort,
)


def test_generate_synthetic_longitudinal_cohort_is_deterministic() -> None:
    left = generate_synthetic_longitudinal_cohort(seed=101, user_count=8)
    right = generate_synthetic_longitudinal_cohort(seed=101, user_count=8)

    assert [record.model_dump(mode="json") for record in left] == [
        record.model_dump(mode="json") for record in right
    ]


def test_generate_synthetic_longitudinal_cohort_validates_expected_shape() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=202, user_count=12)

    assert len(records) == 36
    assert validate_synthetic_cohort(records) == []
    assert {record.follow_up_step for record in records} == {0, 1, 2}
    assert any(record.labels.next_action.value == "start_plan" for record in records)
    assert any(
        record.labels.next_action.value == "collect_more_input" for record in records
    )


def test_synthetic_cohort_summary_reports_closed_loop_states() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=303, user_count=16)

    summary = summarize_synthetic_cohort(records, seed=303)

    assert summary.user_count == 16
    assert summary.record_count == 48
    assert summary.step_counts == {0: 16, 1: 16, 2: 16}
    assert "recommendation_ready" in summary.state_counts
    assert "baseline_questionnaire_due" in summary.state_counts
    assert summary.average_adherence_proxy > 0.0
