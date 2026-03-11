from wellnessbox_rnd.models.effect_model_v1 import (
    EffectFeatureVectorizerV1,
    build_effect_feature_dict_v1,
    predict_aggregate_delta_v1,
    predict_domain_deltas_v1,
    predict_policy_effect_proxy_v1,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import generate_rich_synthetic_cohort
from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_feature_schema_v1,
    evaluate_effect_model_v1,
    fit_effect_model_v1,
    split_effect_records_by_user_v1,
)


def test_effect_feature_vectorizer_v1_is_deterministic() -> None:
    records = generate_rich_synthetic_cohort(seed=3101, user_count=16)
    rows = [build_effect_feature_dict_v1(record) for record in records[:8]]

    vectorizer = EffectFeatureVectorizerV1.fit(rows)

    assert vectorizer.feature_names == sorted(vectorizer.feature_names)
    assert vectorizer.transform(rows) == vectorizer.transform(rows)


def test_split_effect_records_by_user_v1_keeps_user_ids_disjoint() -> None:
    records = generate_rich_synthetic_cohort(seed=3102, user_count=24)

    split = split_effect_records_by_user_v1(records, seed=3102)

    train_users = {record.user_id for record in split.train}
    val_users = {record.user_id for record in split.val}
    test_users = {record.user_id for record in split.test}
    assert train_users.isdisjoint(val_users)
    assert train_users.isdisjoint(test_users)
    assert val_users.isdisjoint(test_users)


def test_effect_model_v1_beats_zero_baseline_on_rich_synthetic_test_split() -> None:
    records = generate_rich_synthetic_cohort(seed=3103, user_count=96)
    split = split_effect_records_by_user_v1(records, seed=3103)

    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=3103)
    metrics = evaluate_effect_model_v1(artifact, split.test)
    domain_prediction = predict_domain_deltas_v1(artifact, split.test[0])
    aggregate_prediction = predict_aggregate_delta_v1(artifact, split.test[0])
    feature_schema = build_effect_feature_schema_v1(artifact)

    assert artifact.feature_names
    assert set(domain_prediction) == set(artifact.output_names)
    assert isinstance(aggregate_prediction, float)
    assert metrics.aggregate_mae < metrics.zero_baseline_aggregate_mae
    assert metrics.mean_domain_mae < metrics.zero_baseline_mean_domain_mae
    assert feature_schema["feature_count"] == len(artifact.feature_names)


def test_effect_model_v1_calibrates_policy_proxy_better_than_raw_aggregate() -> None:
    records = generate_rich_synthetic_cohort(seed=3104, user_count=96)
    split = split_effect_records_by_user_v1(records, seed=3104)

    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=3104)
    calibrated_errors = [
        abs(predict_policy_effect_proxy_v1(artifact, record) - record.expected_effect_proxy)
        for record in split.test
    ]
    raw_errors = [
        abs(predict_aggregate_delta_v1(artifact, record) - record.expected_effect_proxy)
        for record in split.test
    ]

    assert artifact.policy_proxy_slope >= 0.0
    assert sum(calibrated_errors) / len(calibrated_errors) < sum(raw_errors) / len(raw_errors)
