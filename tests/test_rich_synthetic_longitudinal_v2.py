from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import (
    REQUIRED_POLICY_ACTIONS,
    build_rich_policy_training_rows,
    generate_rich_synthetic_cohort,
    summarize_rich_policy_training_rows,
    summarize_rich_synthetic_cohort,
    validate_rich_policy_training_rows,
    validate_rich_synthetic_cohort,
)


def test_generate_rich_synthetic_cohort_is_deterministic() -> None:
    left = generate_rich_synthetic_cohort(seed=101, user_count=48)
    right = generate_rich_synthetic_cohort(seed=101, user_count=48)

    assert [record.model_dump(mode="json") for record in left] == [
        record.model_dump(mode="json") for record in right
    ]


def test_generate_rich_synthetic_cohort_covers_required_action_space() -> None:
    records = generate_rich_synthetic_cohort(seed=202, user_count=48)

    assert len(records) == 240
    assert validate_rich_synthetic_cohort(records) == []
    assert {record.trajectory_step for record in records} == {0, 1, 2, 3, 4}
    assert REQUIRED_POLICY_ACTIONS.issubset({record.labels.next_action.value for record in records})
    assert any(record.request.input_availability.cgm for record in records)
    assert any(record.request.input_availability.genetic for record in records)
    assert all(record.baseline_pro.domain_z for record in records)
    assert all(record.follow_up_pro.domain_z for record in records)
    assert all(record.regimen for record in records if record.trajectory_step > 0)


def test_rich_policy_training_rows_validate_and_summarize() -> None:
    records = generate_rich_synthetic_cohort(seed=303, user_count=48)
    rows = build_rich_policy_training_rows(records)

    assert len(rows) == 240
    assert validate_rich_policy_training_rows(rows) == []

    cohort_summary = summarize_rich_synthetic_cohort(records, seed=303)
    policy_summary = summarize_rich_policy_training_rows(rows)

    assert cohort_summary.record_count == 240
    assert cohort_summary.user_count == 48
    assert policy_summary.record_count == 240
    assert policy_summary.average_feature_count > 20
    assert REQUIRED_POLICY_ACTIONS.issubset(policy_summary.next_action_counts)
    assert "cgm" in cohort_summary.modality_counts
