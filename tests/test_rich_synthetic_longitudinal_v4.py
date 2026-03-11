from pathlib import Path

from wellnessbox_rnd.models.effect_model_v1 import predict_policy_effect_proxy_v1
from wellnessbox_rnd.simulation import compare_batch_simulation_modes
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import (
    build_rich_policy_training_rows_v4,
    generate_rich_synthetic_cohort_v4,
    summarize_rich_policy_training_rows_v4,
    summarize_rich_synthetic_cohort_v4,
    validate_rich_policy_training_rows,
    validate_rich_synthetic_cohort,
    write_rich_synthetic_jsonl_v4,
)
from wellnessbox_rnd.training.effect_model_v1 import (
    evaluate_effect_model_v1,
    fit_effect_model_v1,
    split_effect_records_by_user_v1,
)

POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1.json"


def test_generate_rich_synthetic_cohort_v4_has_modality_enabled_low_risk_edges() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=601, user_count=72)
    rows = build_rich_policy_training_rows_v4(records)

    assert validate_rich_synthetic_cohort(records) == []
    assert validate_rich_policy_training_rows(rows) == []

    low_risk_step_zero = [
        record
        for record in records
        if record.labels.risk_tier == "low" and record.trajectory_step == 0
    ]
    assert low_risk_step_zero
    assert any(record.request.input_availability.genetic for record in low_risk_step_zero)
    assert any(record.request.input_availability.wearable for record in low_risk_step_zero)

    low_risk_actions = {
        record.labels.next_action.value
        for record in records
        if record.labels.risk_tier == "low"
    }
    assert {"continue_plan", "monitor_only", "re_optimize"} <= low_risk_actions

    cohort_summary = summarize_rich_synthetic_cohort_v4(records, seed=601)
    policy_summary = summarize_rich_policy_training_rows_v4(rows)

    assert cohort_summary.record_count == 360
    assert cohort_summary.modality_counts["genetic"] > 0
    assert policy_summary.record_count == 360


def test_effect_v3_training_on_v4_keeps_divergence_without_low_risk_collapse(
    tmp_path: Path,
) -> None:
    records = generate_rich_synthetic_cohort_v4(seed=602, user_count=72)
    split = split_effect_records_by_user_v1(records, seed=602)
    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=602)
    artifact = artifact.model_copy(update={"model_name": "effect_model_v3"})
    metrics = evaluate_effect_model_v1(artifact, split.test)

    dataset_path = tmp_path / "synthetic_longitudinal_v4.jsonl"
    artifact_path = tmp_path / "effect_model_v3.json"
    write_rich_synthetic_jsonl_v4(dataset_path, records)
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

    report = compare_batch_simulation_modes(
        dataset_path=dataset_path,
        max_cycles=5,
        max_users=72,
        model_artifact_path=artifact_path,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
    )

    learned_effect_mode = next(
        mode for mode in report.compared_modes if mode.mode_name == "learned_effect_guarded"
    )
    low_risk_slice = learned_effect_mode.cohort_slice_metrics["low_risk_users"]

    assert metrics.policy_proxy_mae < metrics.zero_baseline_policy_proxy_mae
    assert report.differing_ranking_user_ids["learned_effect_guarded"]
    assert low_risk_slice.deterministic_vs_learned_disagreement_count > 0
    assert len(low_risk_slice.final_action_distribution) >= 2
    assert "continue_plan" in low_risk_slice.final_action_distribution

    low_risk_test_records = [
        record for record in split.test if record.labels.risk_tier == "low"
    ]
    proxy_values = [
        predict_policy_effect_proxy_v1(artifact, record)
        for record in low_risk_test_records
    ]
    assert max(proxy_values) > 0.24
    assert min(proxy_values) < 0.24
