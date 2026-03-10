from wellnessbox_rnd.models.policy_model_v0 import (
    PolicyFeatureVectorizer,
    build_policy_feature_dict,
    predict_policy_action,
)
from wellnessbox_rnd.policy.model_v0 import (
    apply_policy_guard,
    build_policy_training_rows,
    evaluate_policy_model,
    fit_policy_model,
    split_policy_records_by_user,
)
from wellnessbox_rnd.schemas.recommendation import NextAction
from wellnessbox_rnd.synthetic.longitudinal import generate_synthetic_longitudinal_cohort


def test_policy_feature_vectorizer_is_deterministic() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=2001, user_count=8)
    rows = [build_policy_feature_dict(record) for record in records[:6]]

    vectorizer = PolicyFeatureVectorizer.fit(rows)

    assert vectorizer.feature_names == sorted(vectorizer.feature_names)
    assert vectorizer.transform(rows) == vectorizer.transform(rows)


def test_build_policy_training_rows_keeps_deterministic_labels_aligned() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=2002, user_count=6)

    rows = build_policy_training_rows(records)

    assert len(rows) == len(records)
    assert {row.next_action for row in rows} <= {
        "start_plan",
        "collect_more_input",
        "trigger_safety_recheck",
    }
    assert any(row.next_action == row.deterministic_next_action for row in rows)


def test_apply_policy_guard_blocks_more_permissive_prediction() -> None:
    guarded = apply_policy_guard(
        predicted_action=NextAction.START_PLAN,
        deterministic_action=NextAction.TRIGGER_SAFETY_RECHECK,
    )

    assert guarded == NextAction.TRIGGER_SAFETY_RECHECK


def test_policy_model_beats_majority_baseline_on_synthetic_test_split() -> None:
    records = generate_synthetic_longitudinal_cohort(seed=2003, user_count=36)
    split = split_policy_records_by_user(records, seed=2003)

    artifact, _ = fit_policy_model(split.train, split.val, seed=2003)
    metrics = evaluate_policy_model(artifact, split.test)
    prediction = predict_policy_action(artifact, split.test[0])

    assert artifact.feature_names
    assert prediction in {
        NextAction.START_PLAN,
        NextAction.COLLECT_MORE_INPUT,
        NextAction.TRIGGER_SAFETY_RECHECK,
    }
    assert metrics.raw_accuracy > metrics.majority_baseline_accuracy
