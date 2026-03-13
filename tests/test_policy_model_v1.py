from wellnessbox_rnd.models.policy_model_v1 import (
    PolicyFeatureVectorizerV1,
    build_policy_feature_dict_v1,
    predict_policy_action_v1,
)
from wellnessbox_rnd.policy import (
    PolicyTrainingRowV1,
    apply_policy_guard,
    build_policy_feature_schema_v1,
    build_policy_prediction_slice_summaries_v1,
    build_policy_sample_weights_v1,
    build_policy_training_rows_v1,
    evaluate_policy_model_v1,
    fit_policy_model_v1,
    split_policy_records_by_user_v1,
    summarize_policy_sample_weights_v1,
)
from wellnessbox_rnd.schemas.recommendation import NextAction
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import (
    REQUIRED_POLICY_ACTIONS,
    generate_rich_synthetic_cohort,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import generate_rich_synthetic_cohort_v4


def test_policy_feature_vectorizer_v1_is_deterministic() -> None:
    records = generate_rich_synthetic_cohort(seed=2101, user_count=24)
    rows = [build_policy_feature_dict_v1(record) for record in records[:8]]

    vectorizer = PolicyFeatureVectorizerV1.fit(rows)

    assert vectorizer.feature_names == sorted(vectorizer.feature_names)
    assert vectorizer.transform(rows) == vectorizer.transform(rows)


def test_build_policy_training_rows_v1_keeps_richer_action_space() -> None:
    records = generate_rich_synthetic_cohort(seed=2102, user_count=48)

    rows = build_policy_training_rows_v1(records)

    assert len(rows) == len(records)
    assert REQUIRED_POLICY_ACTIONS.issubset({row.next_action for row in rows})
    assert all(isinstance(row, PolicyTrainingRowV1) for row in rows)
    assert any(row.next_action != row.deterministic_next_action for row in rows)


def test_apply_policy_guard_v1_blocks_more_permissive_prediction() -> None:
    guarded = apply_policy_guard(
        predicted_action=NextAction.CONTINUE_PLAN,
        deterministic_action=NextAction.TRIGGER_SAFETY_RECHECK,
    )

    assert guarded == NextAction.TRIGGER_SAFETY_RECHECK


def test_policy_model_v1_beats_majority_baseline_on_rich_synthetic_test_split() -> None:
    records = generate_rich_synthetic_cohort(seed=2103, user_count=96)
    split = split_policy_records_by_user_v1(records, seed=2103)

    artifact, _ = fit_policy_model_v1(split.train, split.val, seed=2103)
    metrics = evaluate_policy_model_v1(artifact, split.test)
    prediction = predict_policy_action_v1(artifact, split.test[0])
    feature_schema = build_policy_feature_schema_v1(artifact)

    assert artifact.feature_names
    assert prediction.value in REQUIRED_POLICY_ACTIONS
    assert metrics.raw_accuracy > metrics.majority_baseline_accuracy
    assert metrics.guarded_accuracy >= metrics.deterministic_accuracy
    assert feature_schema["feature_count"] == len(artifact.feature_names)


def test_policy_sample_weights_v1_boost_target_cgm_threshold_edge_slice() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=20260310, user_count=96)

    weights = build_policy_sample_weights_v1(records)
    summary = summarize_policy_sample_weights_v1(records)

    assert len(weights) == len(records)
    assert summary["boosted_record_count"] > 0
    assert summary["downweighted_record_count"] > 0
    assert summary["max_weight"] > 1.0
    assert summary["min_weight"] < 1.0
    assert summary["low_risk_cgm_threshold_edge_weight_totals"]["monitor_only"] > 0.0
    assert summary["low_risk_cgm_weight_totals"]["re_optimize"] > 0.0


def test_policy_prediction_slice_summaries_v1_cover_target_slices() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=20260310, user_count=96)
    split = split_policy_records_by_user_v1(records, seed=20260310)

    artifact, _ = fit_policy_model_v1(split.train, split.val, seed=20260310)
    summaries = build_policy_prediction_slice_summaries_v1(
        artifact,
        train_records=split.train,
        val_records=split.val,
        test_records=split.test,
    )

    assert summaries["train"]["low_risk_cgm"]["record_count"] > 0
    assert summaries["train"]["low_risk_cgm_threshold_edge"]["record_count"] > 0
    assert (
        summaries["train"]["low_risk_cgm_threshold_edge"]["actual_action_counts"]["re_optimize"]
        > 0
    )
    assert "guarded_predicted_action_counts" in summaries["val"]["low_risk_cgm"]
