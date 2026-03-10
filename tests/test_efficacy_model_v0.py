from wellnessbox_rnd.models.efficacy_model_v0 import (
    EfficacyFeatureVectorizer,
    build_efficacy_feature_dict,
)
from wellnessbox_rnd.synthetic.longitudinal import generate_synthetic_longitudinal_cohort
from wellnessbox_rnd.training.efficacy_model_v0 import (
    evaluate_efficacy_model,
    fit_efficacy_model,
    split_records_by_user,
)


def test_split_records_by_user_keeps_user_ids_disjoint() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=1001, user_count=18)

    split = split_records_by_user(records, seed=1001)

    train_users = {record.user_id for record in split.train}
    val_users = {record.user_id for record in split.val}
    test_users = {record.user_id for record in split.test}
    assert train_users.isdisjoint(val_users)
    assert train_users.isdisjoint(test_users)
    assert val_users.isdisjoint(test_users)


def test_efficacy_feature_vectorizer_is_deterministic() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=1002, user_count=4)
    rows = [build_efficacy_feature_dict(record) for record in records[:4]]

    vectorizer = EfficacyFeatureVectorizer.fit(rows)
    matrix_left = vectorizer.transform(rows)
    matrix_right = vectorizer.transform(rows)

    assert matrix_left == matrix_right
    assert vectorizer.feature_names == sorted(vectorizer.feature_names)


def test_fit_efficacy_model_beats_mean_baseline_on_synthetic_test_split() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=1003, user_count=36)
    split = split_records_by_user(records, seed=1003)

    artifact, _ = fit_efficacy_model(split.train, split.val, seed=1003)
    metrics = evaluate_efficacy_model(artifact, split.test)

    assert artifact.feature_names
    assert metrics.mae < metrics.baseline_mae
