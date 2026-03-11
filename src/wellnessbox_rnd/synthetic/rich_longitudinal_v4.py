from __future__ import annotations

from pathlib import Path
from random import Random

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationGoal,
    RecommendationRequest,
    RecommendationStatus,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import (
    DEFAULT_RICH_SYNTHETIC_SEED,
    DEFAULT_RICH_USER_COUNT,
    DOMAIN_KEYS,
    TRAJECTORY_STEPS,
    PROSnapshot,
    RichPolicyTrainingRow,
    RichPolicyTrainingSummary,
    RichRegimenItem,
    RichSyntheticCohortRecord,
    RichSyntheticCohortSummary,
    RichSyntheticLabels,
    validate_rich_policy_training_rows,
    validate_rich_synthetic_cohort,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v3 import (
    FAMILY_CONFIGS,
    EffectRichFamily,
    build_rich_policy_training_rows_v3,
    generate_rich_synthetic_cohort_v3,
    summarize_rich_policy_training_rows_v3,
    summarize_rich_synthetic_cohort_v3,
)

COHORT_VERSION = "synthetic_longitudinal_v4"
POLICY_DATASET_VERSION = "policy_training_v1_from_v4"

LOW_RISK_EFFECT_MODES: tuple[str, ...] = (
    "threshold_continue_primary",
    "threshold_monitor_secondary",
    "threshold_reopt_edge",
    "threshold_delayed_flip",
    "threshold_duration_sensitive",
    "threshold_adherence_recovery",
)


def generate_rich_synthetic_cohort_v4(
    *,
    seed: int = DEFAULT_RICH_SYNTHETIC_SEED + 2,
    user_count: int = DEFAULT_RICH_USER_COUNT,
) -> list[RichSyntheticCohortRecord]:
    base_records = generate_rich_synthetic_cohort_v3(seed=seed, user_count=user_count)
    base_by_user: dict[str, list[RichSyntheticCohortRecord]] = {}
    for record in base_records:
        base_by_user.setdefault(record.user_id, []).append(record)

    records: list[RichSyntheticCohortRecord] = []
    for user_index, user_id in enumerate(sorted(base_by_user)):
        base_user_records = sorted(base_by_user[user_id], key=lambda item: item.trajectory_step)
        baseline_record = base_user_records[0]
        if _is_effect_enrichment_target(baseline_record):
            records.extend(
                _build_effect_rich_user_records_v4(
                    user_index=user_index,
                    user_seed=baseline_record.rng_seed,
                    base_user_records=base_user_records,
                )
            )
            continue
        records.extend(
            _clone_base_user_records_v4(
                user_index=user_index,
                base_user_records=base_user_records,
            )
        )
    return records


def summarize_rich_synthetic_cohort_v4(
    records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
) -> RichSyntheticCohortSummary:
    summary = summarize_rich_synthetic_cohort_v3(records, seed=seed)
    return summary.model_copy(update={"cohort_version": COHORT_VERSION, "seed": seed})


def build_rich_policy_training_rows_v4(
    records: list[RichSyntheticCohortRecord],
) -> list[RichPolicyTrainingRow]:
    rows = build_rich_policy_training_rows_v3(records)
    return [
        row.model_copy(update={"dataset_version": POLICY_DATASET_VERSION})
        for row in rows
    ]


def summarize_rich_policy_training_rows_v4(
    rows: list[RichPolicyTrainingRow],
) -> RichPolicyTrainingSummary:
    summary = summarize_rich_policy_training_rows_v3(rows)
    return summary.model_copy(update={"dataset_version": POLICY_DATASET_VERSION})


def write_rich_synthetic_jsonl_v4(
    path: str | Path,
    records: list[RichSyntheticCohortRecord],
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(record.model_dump_json() for record in records) + "\n",
        encoding="utf-8",
    )


def _is_effect_enrichment_target(record: RichSyntheticCohortRecord) -> bool:
    request = record.request
    return (
        not request.user_profile.pregnant
        and not request.conditions
        and not request.medications
        and len(request.goals) == 1
    )


def _build_effect_rich_user_records_v4(
    *,
    user_index: int,
    user_seed: int,
    base_user_records: list[RichSyntheticCohortRecord],
) -> list[RichSyntheticCohortRecord]:
    baseline_record = base_user_records[0]
    rng = Random(user_seed)
    family = FAMILY_CONFIGS[user_index % len(FAMILY_CONFIGS)]
    mode = LOW_RISK_EFFECT_MODES[user_index % len(LOW_RISK_EFFECT_MODES)]
    user_id = f"syn-v4-user-{user_index:03d}"
    baseline_pro = _build_effect_rich_baseline(goal=family.goal, rng=rng)
    records: list[RichSyntheticCohortRecord] = []

    for step, day_index in TRAJECTORY_STEPS:
        request = _build_effect_rich_request_v4(
            baseline_record=baseline_record,
            user_index=user_index,
            step=step,
            family=family,
            mode=mode,
        )
        response = recommend(request)
        recommendation_keys = [item.ingredient_key for item in response.recommendations[:2]]
        if len(recommendation_keys) < 2 or response.status != RecommendationStatus.OK:
            return _clone_base_user_records_v4(
                user_index=user_index,
                base_user_records=base_user_records,
            )

        active_candidate = _choose_active_candidate_v4(
            recommendation_keys=recommendation_keys,
            request=request,
            step=step,
            mode=mode,
        )
        regimen = _build_effect_rich_regimen_v4(
            recommendation_keys=recommendation_keys,
            active_candidate=active_candidate,
            step=step,
            mode=mode,
        )
        adherence_proxy = _compute_effect_rich_adherence_v4(
            request=request,
            step=step,
            mode=mode,
        )
        side_effect_proxy = _compute_effect_rich_side_effect_v4(
            request=request,
            step=step,
            mode=mode,
        )
        follow_up_pro, delta_z_by_domain, expected_effect_proxy = _build_effect_rich_follow_up_v4(
            baseline_pro=baseline_pro,
            request=request,
            regimen=regimen,
            step=step,
            adherence_proxy=adherence_proxy,
            side_effect_proxy=side_effect_proxy,
            mode=mode,
        )
        next_action = _label_effect_rich_action_v4(
            step=step,
            expected_effect_proxy=expected_effect_proxy,
            adherence_proxy=adherence_proxy,
            side_effect_proxy=side_effect_proxy,
        )
        adverse_event = side_effect_proxy >= 0.62
        records.append(
            RichSyntheticCohortRecord(
                record_id=f"syn-v4-{user_index:03d}-step-{step}",
                user_id=user_id,
                cohort_version=COHORT_VERSION,
                rng_seed=user_seed,
                trajectory_mode=mode,
                trajectory_step=step,
                day_index=day_index,
                request=request,
                baseline_pro=baseline_pro,
                follow_up_pro=follow_up_pro,
                delta_z_by_domain=delta_z_by_domain,
                regimen=regimen,
                baseline_recommendations=recommendation_keys,
                expected_effect_proxy=expected_effect_proxy,
                adherence_proxy=adherence_proxy,
                side_effect_proxy=side_effect_proxy,
                labels=RichSyntheticLabels(
                    next_action=next_action,
                    reason_code=_reason_code_v4(next_action),
                    safety_status=response.status,
                    risk_tier="low",
                    adverse_event=adverse_event,
                    closed_loop_state=_closed_loop_state_v4(
                        step=step,
                        next_action=next_action,
                        adverse_event=adverse_event,
                    ),
                ),
            )
        )
    return records


def _clone_base_user_records_v4(
    *,
    user_index: int,
    base_user_records: list[RichSyntheticCohortRecord],
) -> list[RichSyntheticCohortRecord]:
    cloned: list[RichSyntheticCohortRecord] = []
    for base_record in base_user_records:
        payload = base_record.request.model_dump(mode="json")
        payload["request_id"] = f"syn-v4-req-{user_index:03d}-step-{base_record.trajectory_step}"
        cloned.append(
            base_record.model_copy(
                update={
                    "record_id": f"syn-v4-{user_index:03d}-step-{base_record.trajectory_step}",
                    "user_id": f"syn-v4-user-{user_index:03d}",
                    "cohort_version": COHORT_VERSION,
                    "request": RecommendationRequest.model_validate(payload),
                }
            )
        )
    return cloned


def _build_effect_rich_request_v4(
    *,
    baseline_record: RichSyntheticCohortRecord,
    user_index: int,
    step: int,
    family: EffectRichFamily,
    mode: str,
) -> RecommendationRequest:
    payload = baseline_record.request.model_dump(mode="json")
    payload["request_id"] = f"syn-v4-req-{user_index:03d}-step-{step}"
    payload["goals"] = [family.goal.value]
    payload["symptoms"] = []
    payload["conditions"] = []
    payload["medications"] = []
    payload["current_supplements"] = [
        {
            "name": "Baseline Multi",
            "ingredients": ["vitamin_b_complex"],
        }
    ]
    payload["user_profile"]["pregnant"] = False
    payload["input_availability"]["cgm"] = False
    payload["input_availability"]["genetic"] = user_index % 2 == 0
    payload["input_availability"]["wearable"] = family.wearer_share or user_index % 3 != 0
    payload["preferences"]["max_products"] = 2
    payload["preferences"]["budget_level"] = (
        "low"
        if mode in {"threshold_reopt_edge", "threshold_adherence_recovery"}
        else "medium"
    )
    sleep_offset = {
        "threshold_continue_primary": 0.1,
        "threshold_monitor_secondary": -0.2,
        "threshold_reopt_edge": -0.6,
        "threshold_delayed_flip": -0.4 if step < 2 else -0.1,
        "threshold_duration_sensitive": -0.3,
        "threshold_adherence_recovery": -0.5 if step < 2 else 0.0,
    }[mode]
    stress_offset = {
        "threshold_continue_primary": 0,
        "threshold_monitor_secondary": 1,
        "threshold_reopt_edge": 2,
        "threshold_delayed_flip": 2 if step < 2 else 1,
        "threshold_duration_sensitive": 1,
        "threshold_adherence_recovery": 2 if step < 3 else 1,
    }[mode]
    payload["lifestyle"]["sleep_hours"] = round(
        family.preferred_sleep_hours + sleep_offset + ((user_index % 3) - 1) * 0.1,
        1,
    )
    payload["lifestyle"]["stress_level"] = min(
        5,
        max(
            1,
            family.preferred_stress + stress_offset,
        ),
    )
    return RecommendationRequest.model_validate(payload)


def _build_effect_rich_baseline(
    *,
    goal: RecommendationGoal,
    rng: Random,
) -> PROSnapshot:
    domain_z: dict[str, float] = {}
    for domain_key in DOMAIN_KEYS:
        if domain_key == goal.value:
            value = -1.4 + (rng.random() * 0.4)
        else:
            value = -0.28 + (rng.random() * 0.42)
        domain_z[domain_key] = round(max(-3.0, min(3.0, value)), 3)
    return PROSnapshot(
        domain_z=domain_z,
        aggregate_z=round(sum(domain_z.values()) / len(domain_z), 3),
    )


def _choose_active_candidate_v4(
    *,
    recommendation_keys: list[str],
    request: RecommendationRequest,
    step: int,
    mode: str,
) -> str:
    top_key, second_key = recommendation_keys[:2]
    if mode == "threshold_continue_primary":
        return top_key
    if mode == "threshold_monitor_secondary":
        return second_key
    if mode == "threshold_reopt_edge":
        return second_key if step <= 2 else top_key
    if mode == "threshold_delayed_flip":
        return second_key if step <= 1 else top_key
    if mode == "threshold_duration_sensitive":
        return second_key if step >= 3 else top_key
    if mode == "threshold_adherence_recovery":
        return (
            second_key
            if request.preferences.budget_level.value == "low" and step <= 2
            else top_key
        )
    return top_key


def _build_effect_rich_regimen_v4(
    *,
    recommendation_keys: list[str],
    active_candidate: str,
    step: int,
    mode: str,
) -> list[RichRegimenItem]:
    regimen: list[RichRegimenItem] = []
    for position, candidate_key in enumerate(recommendation_keys[:2]):
        base_dose, dose_unit, _ = {
            "magnesium_glycinate": (220.0, "mg", "night"),
            "l_theanine": (180.0, "mg", "split_evening"),
            "soluble_fiber": (4.5, "g", "split_premeal"),
            "probiotics": (9.0, "billion_cfu", "morning"),
            "vitamin_d3": (1800.0, "IU", "weekly_split"),
            "vitamin_c": (450.0, "mg", "midday_split"),
        }.get(candidate_key, (1.0, "serving", "morning"))
        if candidate_key == active_candidate:
            regimen_status = "active"
            dose_multiplier = {
                "threshold_continue_primary": (0.95, 1.0, 1.04, 1.08, 1.1),
                "threshold_monitor_secondary": (0.86, 0.88, 0.9, 0.93, 0.95),
                "threshold_reopt_edge": (0.76, 0.78, 0.8, 0.86, 0.9),
                "threshold_delayed_flip": (0.78, 0.8, 0.92, 1.0, 1.04),
                "threshold_duration_sensitive": (0.82, 0.84, 0.86, 0.98, 1.02),
                "threshold_adherence_recovery": (0.72, 0.74, 0.82, 0.92, 0.98),
            }[mode][step]
        else:
            regimen_status = "planned"
            dose_multiplier = 0.6 if position == 1 else 0.68
        regimen.append(
            RichRegimenItem(
                ingredient_key=candidate_key,
                display_name=candidate_key.replace("_", " ").title(),
                daily_dose=round(base_dose * dose_multiplier, 3),
                dose_unit=dose_unit,
                schedule=_schedule_for_candidate_v4(
                    candidate_key=candidate_key,
                    step=step,
                    active=(candidate_key == active_candidate),
                    mode=mode,
                ),
                regimen_status=regimen_status,
            )
        )
    return regimen


def _schedule_for_candidate_v4(
    *,
    candidate_key: str,
    step: int,
    active: bool,
    mode: str,
) -> str:
    if candidate_key == "magnesium_glycinate":
        if mode == "threshold_duration_sensitive" and active and step >= 3:
            return "night_split"
        return "night" if active else "midday"
    if candidate_key == "l_theanine":
        return "split_evening" if active else "midday"
    if candidate_key == "soluble_fiber":
        return "split_premeal" if active else "before_dinner"
    if candidate_key == "probiotics":
        return "morning" if active else "morning_alt_day"
    if candidate_key == "vitamin_d3":
        return "weekly_split" if active else "morning"
    if candidate_key == "vitamin_c":
        return "midday_split" if active else "morning"
    return "morning"


def _compute_effect_rich_adherence_v4(
    *,
    request: RecommendationRequest,
    step: int,
    mode: str,
) -> float:
    base = {
        "threshold_continue_primary": (0.79, 0.82, 0.84, 0.86, 0.88),
        "threshold_monitor_secondary": (0.71, 0.74, 0.76, 0.78, 0.8),
        "threshold_reopt_edge": (0.63, 0.61, 0.64, 0.66, 0.69),
        "threshold_delayed_flip": (0.68, 0.7, 0.76, 0.81, 0.84),
        "threshold_duration_sensitive": (0.72, 0.73, 0.75, 0.79, 0.82),
        "threshold_adherence_recovery": (0.56, 0.53, 0.6, 0.71, 0.78),
    }[mode][step]
    if request.preferences.budget_level.value == "low":
        base -= 0.03
    return round(max(0.0, min(1.0, base)), 3)


def _compute_effect_rich_side_effect_v4(
    *,
    request: RecommendationRequest,
    step: int,
    mode: str,
) -> float:
    base = {
        "threshold_continue_primary": (0.07, 0.08, 0.09, 0.09, 0.08),
        "threshold_monitor_secondary": (0.09, 0.11, 0.12, 0.11, 0.1),
        "threshold_reopt_edge": (0.13, 0.16, 0.18, 0.17, 0.15),
        "threshold_delayed_flip": (0.1, 0.12, 0.14, 0.12, 0.11),
        "threshold_duration_sensitive": (0.09, 0.1, 0.11, 0.12, 0.11),
        "threshold_adherence_recovery": (0.11, 0.15, 0.17, 0.14, 0.12),
    }[mode][step]
    if (request.lifestyle.stress_level or 0) >= 4:
        base += 0.02
    return round(max(0.0, min(1.0, base)), 3)


def _build_effect_rich_follow_up_v4(
    *,
    baseline_pro: PROSnapshot,
    request: RecommendationRequest,
    regimen: list[RichRegimenItem],
    step: int,
    adherence_proxy: float,
    side_effect_proxy: float,
    mode: str,
) -> tuple[PROSnapshot, dict[str, float], float]:
    goal_key = request.goals[0].value
    active_items = [item for item in regimen if item.regimen_status == "active"]
    active_item = active_items[0] if active_items else regimen[0]
    goal_delta = _candidate_goal_delta_v4(
        candidate_key=active_item.ingredient_key,
        request=request,
        step=step,
        daily_dose=active_item.daily_dose,
        schedule=active_item.schedule,
        adherence_proxy=adherence_proxy,
        side_effect_proxy=side_effect_proxy,
        mode=mode,
    )
    spillover_ratio = 0.11 + (0.015 * step)
    domain_z: dict[str, float] = {}
    for domain_key, baseline_value in baseline_pro.domain_z.items():
        delta = goal_delta if domain_key == goal_key else max(0.01, goal_delta * spillover_ratio)
        domain_z[domain_key] = round(max(-3.0, min(3.0, baseline_value + delta)), 3)
    follow_up_pro = PROSnapshot(
        domain_z=domain_z,
        aggregate_z=round(sum(domain_z.values()) / len(domain_z), 3),
    )
    delta_z_by_domain = {
        domain_key: round(follow_up_pro.domain_z[domain_key] - baseline_pro.domain_z[domain_key], 3)
        for domain_key in DOMAIN_KEYS
    }
    expected_effect_proxy = round(
        max(
            -1.0,
            min(
                1.0,
                (goal_delta * 0.84)
                + (0.11 * adherence_proxy)
                - (0.14 * side_effect_proxy)
                + (0.012 * step)
                - 0.018,
            ),
        ),
        3,
    )
    return follow_up_pro, delta_z_by_domain, expected_effect_proxy


def _candidate_goal_delta_v4(
    *,
    candidate_key: str,
    request: RecommendationRequest,
    step: int,
    daily_dose: float,
    schedule: str,
    adherence_proxy: float,
    side_effect_proxy: float,
    mode: str,
) -> float:
    sleep_hours = request.lifestyle.sleep_hours or 7.0
    stress_level = request.lifestyle.stress_level or 2
    goal = request.goals[0]
    step_curve = {
        "threshold_continue_primary": (0.12, 0.16, 0.19, 0.22, 0.24),
        "threshold_monitor_secondary": (0.09, 0.12, 0.14, 0.16, 0.18),
        "threshold_reopt_edge": (0.07, 0.09, 0.11, 0.12, 0.14),
        "threshold_delayed_flip": (0.08, 0.1, 0.15, 0.19, 0.22),
        "threshold_duration_sensitive": (0.09, 0.11, 0.13, 0.18, 0.21),
        "threshold_adherence_recovery": (0.06, 0.07, 0.1, 0.15, 0.18),
    }[mode][step]
    schedule_bonus = 0.018 if "split" in schedule else 0.0
    if goal == RecommendationGoal.SLEEP_SUPPORT:
        magnesium_bias = 0.044 + max(0.0, 6.5 - sleep_hours) * 0.03
        theanine_bias = 0.03 + max(0.0, stress_level - 3) * 0.03
        ingredient_bias = (
            magnesium_bias
            if candidate_key == "magnesium_glycinate"
            else theanine_bias
        )
    elif goal == RecommendationGoal.STRESS_SUPPORT:
        theanine_bias = 0.043 + max(0.0, stress_level - 3) * 0.03
        magnesium_bias = 0.032 + max(0.0, 6.4 - sleep_hours) * 0.025
        ingredient_bias = theanine_bias if candidate_key == "l_theanine" else magnesium_bias
    elif goal == RecommendationGoal.GUT_HEALTH:
        ingredient_bias = 0.042 if candidate_key == "soluble_fiber" else 0.036
        ingredient_bias += 0.014 if "split" in schedule else 0.0
    else:
        ingredient_bias = 0.041 if candidate_key == "vitamin_d3" else 0.034
        ingredient_bias += (
            0.012
            if request.input_availability.genetic and candidate_key == "vitamin_d3"
            else 0.0
        )
        ingredient_bias += (
            0.01
            if request.input_availability.wearable and candidate_key == "vitamin_c"
            else 0.0
        )
    dose_bonus = min(0.045, max(0.0, daily_dose) / 7000.0)
    duration_bonus = 0.02 if mode == "threshold_duration_sensitive" and step >= 3 else 0.0
    delayed_bonus = 0.015 if mode == "threshold_delayed_flip" and step >= 2 else 0.0
    recovery_bonus = 0.012 if mode == "threshold_adherence_recovery" and step >= 3 else 0.0
    delta = (
        step_curve
        + ingredient_bias
        + schedule_bonus
        + dose_bonus
        + duration_bonus
        + delayed_bonus
        + recovery_bonus
        + (adherence_proxy * 0.06)
        - (side_effect_proxy * 0.05)
    )
    return round(max(0.035, min(0.34, delta)), 3)


def _label_effect_rich_action_v4(
    *,
    step: int,
    expected_effect_proxy: float,
    adherence_proxy: float,
    side_effect_proxy: float,
) -> NextAction:
    if side_effect_proxy >= 0.62:
        return NextAction.REDUCE_OR_STOP
    if adherence_proxy < 0.54 and step <= 2:
        return NextAction.ASK_TARGETED_FOLLOWUP
    if expected_effect_proxy < 0.16:
        return NextAction.RE_OPTIMIZE
    if expected_effect_proxy < 0.25:
        return NextAction.MONITOR_ONLY
    return NextAction.CONTINUE_PLAN


def _reason_code_v4(next_action: NextAction) -> str:
    mapping = {
        NextAction.CONTINUE_PLAN: "effect_calibrated_continue_plan",
        NextAction.MONITOR_ONLY: "effect_calibrated_monitor_plateau",
        NextAction.RE_OPTIMIZE: "effect_calibrated_near_tie_gap",
        NextAction.ASK_TARGETED_FOLLOWUP: "effect_calibrated_adherence_followup",
        NextAction.REDUCE_OR_STOP: "effect_calibrated_tolerability_reduction",
    }
    return mapping.get(next_action, "effect_calibrated_fallback")


def _closed_loop_state_v4(
    *,
    step: int,
    next_action: NextAction,
    adverse_event: bool,
) -> str:
    if adverse_event or next_action == NextAction.REDUCE_OR_STOP:
        return "stop_or_escalate"
    if next_action == NextAction.ASK_TARGETED_FOLLOWUP:
        return "baseline_questionnaire_due" if step == 0 else "re_evaluation"
    if next_action == NextAction.RE_OPTIMIZE:
        return "adjust_plan"
    return "recommendation_ready" if step == 0 else "followup_due"


__all__ = [
    "COHORT_VERSION",
    "POLICY_DATASET_VERSION",
    "build_rich_policy_training_rows_v4",
    "generate_rich_synthetic_cohort_v4",
    "summarize_rich_policy_training_rows_v4",
    "summarize_rich_synthetic_cohort_v4",
    "validate_rich_policy_training_rows",
    "validate_rich_synthetic_cohort",
    "write_rich_synthetic_jsonl_v4",
]
