from __future__ import annotations

import json
import statistics
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.run_pro_personal_group_uncertainty_smoke import SOURCE_PATHS
from wellnessbox_rnd.metrics.pro_followup import interpret_pro_followup_effect_v1
from wellnessbox_rnd.metrics.pro_group_effects import (
    PROGroupEffectSummaryV1,
    build_pro_group_effect_summary_v1,
    load_pro_group_effect_contract_v1,
)
from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineScoreObservationV1,
    build_pro_baseline_distribution_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)
from wellnessbox_rnd.metrics.statistics import deterministic_bootstrap_mean_ci

CONTRACT_PATH = Path("data/contracts/pro_group_effect_summary_v1.json")
SCHEDULED_DAYS = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": None,
}
ACTUAL_DAYS = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": 35,
}
OBSERVED_AT = {
    "pre_intake": "2026-01-01T00:00:00Z",
    "week_2": "2026-01-15T00:00:00Z",
    "week_4": "2026-01-29T00:00:00Z",
    "discontinuation": "2026-02-05T00:00:00Z",
}


def _psqi_score(raw_score: int):
    values = [0] * 7
    remaining = raw_score
    for index in range(7):
        values[index] = min(3, remaining)
        remaining -= values[index]
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": "PSQI",
            "item_scores": values,
        }
    )


def _distribution(*, cohort_id: str = "op052-psqi-baseline"):
    return build_pro_baseline_distribution_v1(
        [
            PROBaselineScoreObservationV1(
                schema_version="pro_baseline_score_observation_v1",
                observation_role="BASELINE",
                score=_psqi_score(raw_score),
            )
            for raw_score in (6, 9, 12)
        ],
        cohort_id=cohort_id,
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )


def _event_payload(
    member_index: int,
    timepoint: str,
    raw_score: int,
    *,
    plan_id: str | None = None,
    assessment_id: str | None = None,
    planned: int = 14,
    taken: int = 14,
    distribution_cohort_id: str = "op052-psqi-baseline",
    data_class: str = "SYNTHETIC_OUTCOME_PROXY",
) -> dict[str, object]:
    score = _psqi_score(raw_score)
    standardized = standardize_pro_instrument_score_v1(
        score,
        _distribution(cohort_id=distribution_cohort_id),
    )
    adherence = None
    if timepoint != "pre_intake":
        adherence = {
            "planned_dose_count": planned,
            "taken_dose_count": taken,
            "missed_dose_count": planned - taken,
            "adherence_rate": round(taken / planned, 6),
        }
    return {
        "schema_version": "versioned_pro_followup_event_v1",
        "assessment_id": assessment_id or f"assessment_{member_index:03d}_{timepoint}",
        "plan_id": plan_id or f"plan_{member_index:03d}",
        "data_class": data_class,
        "timepoint": timepoint,
        "scheduled_day_index": SCHEDULED_DAYS[timepoint],
        "actual_day_index": ACTUAL_DAYS[timepoint],
        "observed_at": OBSERVED_AT[timepoint],
        "instrument_scores": [score.model_dump(mode="json")],
        "standardized_scores": [standardized.model_dump(mode="json")],
        "adherence": adherence,
        "adverse_events": [],
        "discontinuation_reason": (
            "user_stopped_plan" if timepoint == "discontinuation" else None
        ),
    }


def _personal_effect(
    member_index: int,
    raw_score: int,
    *,
    timepoint: str = "week_2",
    plan_id: str | None = None,
    baseline_assessment_id: str | None = None,
    follow_up_assessment_id: str | None = None,
    planned: int = 14,
    taken: int = 14,
    distribution_cohort_id: str = "op052-psqi-baseline",
    data_class: str = "SYNTHETIC_OUTCOME_PROXY",
):
    return interpret_pro_followup_effect_v1(
        _event_payload(
            member_index,
            "pre_intake",
            10,
            plan_id=plan_id,
            assessment_id=baseline_assessment_id,
            distribution_cohort_id=distribution_cohort_id,
            data_class=data_class,
        ),
        _event_payload(
            member_index,
            timepoint,
            raw_score,
            plan_id=plan_id,
            assessment_id=follow_up_assessment_id,
            planned=planned,
            taken=taken,
            distribution_cohort_id=distribution_cohort_id,
            data_class=data_class,
        ),
    )


def test_deterministic_bootstrap_mean_ci_replays_exactly() -> None:
    values = [-0.2, 0.1, 0.4, 0.8]

    first = deterministic_bootstrap_mean_ci(values)
    second = deterministic_bootstrap_mean_ci(values)

    assert first == second
    assert first[0] <= statistics.mean(values) <= first[1]


@pytest.mark.parametrize(
    ("values", "error_match"),
    [
        ([], "values_required"),
        ([0.0, float("nan")], "finite"),
    ],
)
def test_deterministic_bootstrap_mean_ci_rejects_invalid_inputs(
    values: list[float],
    error_match: str,
) -> None:
    with pytest.raises(ValueError, match=error_match):
        deterministic_bootstrap_mean_ci(values)


def test_group_summary_separates_personal_effects_from_group_estimate() -> None:
    personal = [_personal_effect(index, raw_score) for index, raw_score in enumerate((9, 8, 7))]

    summary = build_pro_group_effect_summary_v1(
        cohort_id="cohort_sleep_week_2",
        personal_effects=personal,
    )

    assert summary.personal_effects == personal
    assert summary.group_estimate.sample_size == 3
    assert summary.group_estimate.mean_health_z_change == round(
        statistics.mean(item.mean_health_z_change for item in personal),
        6,
    )
    assert summary.group_estimate.mean_health_percentile_change == round(
        statistics.mean(
            statistics.mean(
                change.health_percentile_change for change in item.instrument_changes
            )
            for item in personal
        ),
        6,
    )
    assert summary.causal_effect_claim_allowed is False
    assert summary.effect_claim_scope == "group_observed_association_not_causal"


def test_group_summary_reports_sample_ci_and_uncertainty_reasons() -> None:
    personal = [_personal_effect(index, 7 + (index % 3)) for index in range(100)]

    summary = build_pro_group_effect_summary_v1(
        cohort_id="cohort_sleep_week_2_n100",
        personal_effects=personal,
    )

    estimate = summary.group_estimate
    assert estimate.sample_size == 100
    assert estimate.fully_interpretable_sample_size == 100
    assert estimate.interpretation_status_counts == {"observed_change_interpretable": 100}
    assert estimate.mean_health_z_change_ci95.lower > 0
    assert estimate.mean_health_percentile_change_ci95.lower > 0
    assert estimate.mean_health_z_change_ci95.method == (
        "deterministic_percentile_bootstrap_mean"
    )
    assert estimate.mean_health_z_change_ci95.iterations == 3000
    assert estimate.mean_health_z_change_ci95.seed == 20260710
    assert summary.uncertainty_reason_codes == [
        "observational_association_not_causal",
        "non_real_world_outcome_data",
    ]


def test_group_summary_reports_limited_and_zero_crossing_uncertainty() -> None:
    personal = [
        _personal_effect(0, 7),
        _personal_effect(1, 13, planned=14, taken=10),
    ]

    summary = build_pro_group_effect_summary_v1(
        cohort_id="cohort_mixed_observed_change",
        personal_effects=personal,
    )

    assert summary.group_estimate.fully_interpretable_sample_size == 1
    assert summary.group_estimate.interpretation_status_counts == {
        "limited_by_low_adherence": 1,
        "observed_change_interpretable": 1,
    }
    assert summary.uncertainty_reason_codes == [
        "observational_association_not_causal",
        "non_real_world_outcome_data",
        "sample_size_below_100",
        "limited_personal_interpretations_present",
        "confidence_interval_not_entirely_above_zero",
    ]


def test_group_summary_is_order_independent() -> None:
    personal = [_personal_effect(index, 7 + (index % 3)) for index in range(8)]

    forward = build_pro_group_effect_summary_v1(
        cohort_id="cohort_order_independent",
        personal_effects=personal,
    )
    reverse = build_pro_group_effect_summary_v1(
        cohort_id="cohort_order_independent",
        personal_effects=list(reversed(personal)),
    )

    assert forward.model_dump(mode="json") == reverse.model_dump(mode="json")


@pytest.mark.parametrize(
    ("personal", "error_match"),
    [
        (
            [
                _personal_effect(0, 7, plan_id="plan_same"),
                _personal_effect(1, 8, plan_id="plan_same"),
            ],
            "duplicate plan",
        ),
        (
            [_personal_effect(0, 7), _personal_effect(1, 8, timepoint="week_4")],
            "timepoint",
        ),
        (
            [
                _personal_effect(0, 7),
                _personal_effect(1, 8, distribution_cohort_id="different-baseline"),
            ],
            "score identity",
        ),
        (
            [_personal_effect(0, 7), _personal_effect(1, 8, data_class="REAL_WORLD_OUTCOME")],
            "data class",
        ),
        (
            [
                _personal_effect(0, 7, follow_up_assessment_id="assessment_shared_followup"),
                _personal_effect(1, 8, follow_up_assessment_id="assessment_shared_followup"),
            ],
            "duplicate assessment",
        ),
    ],
)
def test_group_summary_rejects_mixed_or_duplicate_cohort_members(
    personal: list[object],
    error_match: str,
) -> None:
    with pytest.raises(ValueError, match=error_match):
        build_pro_group_effect_summary_v1(
            cohort_id="cohort_invalid",
            personal_effects=personal,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["group_estimate"].update(
            {"mean_health_z_change": 999.0}
        ),
        lambda payload: payload.update({"uncertainty_reason_codes": []}),
        lambda payload: payload["group_estimate"]["mean_health_z_change_ci95"].update(
            {"lower": -999.0}
        ),
    ],
)
def test_group_summary_rejects_derived_output_mutation(mutate) -> None:
    summary = build_pro_group_effect_summary_v1(
        cohort_id="cohort_mutation",
        personal_effects=[_personal_effect(0, 7), _personal_effect(1, 8)],
    )
    payload = deepcopy(summary.model_dump(mode="json"))
    mutate(payload)

    with pytest.raises(ValidationError, match="group effect summary"):
        PROGroupEffectSummaryV1.model_validate(payload)


def test_group_effect_contract_rejects_policy_drift(tmp_path: Path) -> None:
    contract = load_pro_group_effect_contract_v1()

    assert contract.contract_version == "2026-07-21.1"
    assert contract.kpi_target_sample_size == 100
    assert contract.confidence_interval.iterations == 3000
    assert contract.causal_effect_claim_allowed is False

    changed = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    changed["kpi_target_sample_size"] = 2
    changed_path = tmp_path / "changed-group-contract.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="policy_drift"):
        load_pro_group_effect_contract_v1(changed_path)


def test_metrics_package_exports_group_effect_api() -> None:
    from wellnessbox_rnd import metrics

    assert metrics.PRO_GROUP_EFFECT_CONTRACT_VERSION_V1 == "2026-07-21.1"
    assert metrics.PROGroupEffectSummaryV1 is PROGroupEffectSummaryV1
    assert metrics.build_pro_group_effect_summary_v1 is build_pro_group_effect_summary_v1


def test_smoke_source_identity_includes_direct_contract_dependencies() -> None:
    assert "data/contracts/pro_group_effect_summary_v1.json" in SOURCE_PATHS
    assert "data/contracts/pro_followup_interpretation_v1.json" in SOURCE_PATHS
    assert "data/contracts/pro_instrument_scoring_v1.json" in SOURCE_PATHS
    assert "src/wellnessbox_rnd/interim/contracts.py" in SOURCE_PATHS
