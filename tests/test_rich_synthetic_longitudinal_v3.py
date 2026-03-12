from pathlib import Path

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.simulation import compare_batch_simulation_modes
from wellnessbox_rnd.synthetic.rich_longitudinal_v3 import (
    build_rich_policy_training_rows_v3,
    generate_rich_synthetic_cohort_v3,
    summarize_rich_policy_training_rows_v3,
    summarize_rich_synthetic_cohort_v3,
    validate_rich_policy_training_rows,
    validate_rich_synthetic_cohort,
    write_rich_synthetic_jsonl_v3,
)
from wellnessbox_rnd.training.effect_model_v1 import (
    fit_effect_model_v1,
    split_effect_records_by_user_v1,
)

POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1.json"


def test_generate_rich_synthetic_cohort_v3_has_low_risk_followups_and_near_ties() -> None:
    records = generate_rich_synthetic_cohort_v3(seed=501, user_count=72)
    rows = build_rich_policy_training_rows_v3(records)

    assert validate_rich_synthetic_cohort(records) == []
    assert validate_rich_policy_training_rows(rows) == []

    low_risk_followups = [
        record
        for record in records
        if record.labels.risk_tier == "low" and record.trajectory_step > 0
    ]
    assert low_risk_followups

    near_tie_records = []
    for record in low_risk_followups:
        response = recommend(record.request)
        if len(response.recommendations) < 2:
            continue
        gap = (
            response.recommendations[0].score_breakdown.total
            - response.recommendations[1].score_breakdown.total
        )
        if gap <= 1.0:
            near_tie_records.append(record.record_id)

    structured_dose_record_count = sum(
        1
        for record in records
        if any(supplement.dose for supplement in record.request.current_supplements)
    )

    cohort_summary = summarize_rich_synthetic_cohort_v3(records, seed=501)
    policy_summary = summarize_rich_policy_training_rows_v3(rows)

    assert near_tie_records
    assert structured_dose_record_count > 0
    assert cohort_summary.record_count == 360
    assert (
        cohort_summary.structured_current_supplement_dose_record_count
        == structured_dose_record_count
    )
    assert cohort_summary.risk_tier_counts["low"] > 72
    assert policy_summary.record_count == 360


def test_effect_v2_training_on_v3_creates_learned_effect_divergence(tmp_path: Path) -> None:
    records = generate_rich_synthetic_cohort_v3(seed=502, user_count=72)
    split = split_effect_records_by_user_v1(records, seed=502)
    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=502)
    artifact = artifact.model_copy(update={"model_name": "effect_model_v2"})

    dataset_path = tmp_path / "synthetic_longitudinal_v3.jsonl"
    artifact_path = tmp_path / "effect_model_v2.json"
    write_rich_synthetic_jsonl_v3(dataset_path, records)
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

    report = compare_batch_simulation_modes(
        dataset_path=dataset_path,
        max_cycles=5,
        max_users=72,
        model_artifact_path=artifact_path,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
    )

    low_risk_user_ids = {
        record.user_id
        for record in records
        if record.trajectory_step == 0 and record.labels.risk_tier == "low"
    }
    differing_policy_user_ids = set(
        report.differing_final_policy_user_ids["learned_effect_guarded"]
    )
    differing_state_user_ids = set(
        report.differing_final_state_user_ids["learned_effect_guarded"]
    )
    differing_trace_user_ids = set(
        report.differing_trace_user_ids["learned_effect_guarded"]
    )

    assert report.differing_ranking_user_ids["learned_effect_guarded"]
    assert (
        low_risk_user_ids & differing_policy_user_ids
        or low_risk_user_ids & differing_state_user_ids
        or low_risk_user_ids & differing_trace_user_ids
    )

    learned_effect_mode = next(
        mode for mode in report.compared_modes if mode.mode_name == "learned_effect_guarded"
    )
    assert learned_effect_mode.raw_ranking_disagreement_count > 0
    assert (
        learned_effect_mode.cohort_slice_metrics[
            "low_risk_users"
        ].deterministic_vs_learned_disagreement_count
        > 0
    )
