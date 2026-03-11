from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
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
    build_rich_policy_training_rows,
    generate_rich_synthetic_cohort,
    summarize_rich_policy_training_rows,
    validate_rich_policy_training_rows,
    validate_rich_synthetic_cohort,
)

COHORT_VERSION = "synthetic_longitudinal_v3"
POLICY_DATASET_VERSION = "policy_training_v1_from_v3"

LOW_RISK_EFFECT_MODES: tuple[str, ...] = (
    "near_tie_secondary_win",
    "near_tie_primary_win",
    "near_tie_delayed_flip",
    "near_tie_adherence_sensitive",
)

TARGET_EFFECT_ACTIONS = {
    NextAction.CONTINUE_PLAN,
    NextAction.MONITOR_ONLY,
    NextAction.RE_OPTIMIZE,
}


@dataclass(frozen=True)
class EffectRichFamily:
    goal: RecommendationGoal
    preferred_sleep_hours: float
    preferred_stress: int
    wearer_share: bool


FAMILY_CONFIGS: tuple[EffectRichFamily, ...] = (
    EffectRichFamily(
        goal=RecommendationGoal.STRESS_SUPPORT,
        preferred_sleep_hours=7.0,
        preferred_stress=3,
        wearer_share=False,
    ),
    EffectRichFamily(
        goal=RecommendationGoal.SLEEP_SUPPORT,
        preferred_sleep_hours=7.0,
        preferred_stress=2,
        wearer_share=False,
    ),
    EffectRichFamily(
        goal=RecommendationGoal.GUT_HEALTH,
        preferred_sleep_hours=7.0,
        preferred_stress=2,
        wearer_share=True,
    ),
    EffectRichFamily(
        goal=RecommendationGoal.IMMUNITY_SUPPORT,
        preferred_sleep_hours=7.0,
        preferred_stress=2,
        wearer_share=True,
    ),
)


def generate_rich_synthetic_cohort_v3(
    *,
    seed: int = DEFAULT_RICH_SYNTHETIC_SEED + 1,
    user_count: int = DEFAULT_RICH_USER_COUNT,
) -> list[RichSyntheticCohortRecord]:
    base_records = generate_rich_synthetic_cohort(seed=seed, user_count=user_count)
    base_by_user: dict[str, list[RichSyntheticCohortRecord]] = {}
    for record in base_records:
        base_by_user.setdefault(record.user_id, []).append(record)

    records: list[RichSyntheticCohortRecord] = []
    for user_index, user_id in enumerate(sorted(base_by_user)):
        base_user_records = sorted(base_by_user[user_id], key=lambda item: item.trajectory_step)
        baseline_record = base_user_records[0]
        if _is_effect_enrichment_target(baseline_record):
            records.extend(
                _build_effect_rich_user_records(
                    user_index=user_index,
                    user_seed=baseline_record.rng_seed,
                    base_user_records=base_user_records,
                )
            )
            continue

        for base_record in base_user_records:
            request_payload = base_record.request.model_dump(mode="json")
            request_payload["request_id"] = (
                f"syn-v3-req-{user_index:03d}-step-{base_record.trajectory_step}"
            )
            record = base_record.model_copy(
                update={
                    "record_id": f"syn-v3-{user_index:03d}-step-{base_record.trajectory_step}",
                    "user_id": f"syn-v3-user-{user_index:03d}",
                    "cohort_version": COHORT_VERSION,
                    "request": RecommendationRequest.model_validate(request_payload),
                }
            )
            records.append(record)
    return records


def summarize_rich_synthetic_cohort_v3(
    records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
) -> RichSyntheticCohortSummary:
    modality_counts = Counter()
    for record in records:
        if record.request.input_availability.wearable:
            modality_counts["wearable"] += 1
        if record.request.input_availability.cgm:
            modality_counts["cgm"] += 1
        if record.request.input_availability.genetic:
            modality_counts["genetic"] += 1
    return RichSyntheticCohortSummary(
        cohort_version=COHORT_VERSION,
        seed=seed,
        user_count=len({record.user_id for record in records}),
        record_count=len(records),
        total_trajectory_steps=sum(record.trajectory_step for record in records),
        step_counts=dict(sorted(Counter(record.trajectory_step for record in records).items())),
        next_action_counts=dict(
            sorted(Counter(record.labels.next_action.value for record in records).items())
        ),
        safety_status_counts=dict(
            sorted(Counter(record.labels.safety_status.value for record in records).items())
        ),
        risk_tier_counts=dict(
            sorted(Counter(record.labels.risk_tier for record in records).items())
        ),
        state_counts=dict(
            sorted(Counter(record.labels.closed_loop_state for record in records).items())
        ),
        modality_counts=dict(sorted(modality_counts.items())),
        goal_counts=dict(
            sorted(
                Counter(goal.value for record in records for goal in record.request.goals).items()
            )
        ),
        trajectory_mode_counts=dict(
            sorted(Counter(record.trajectory_mode for record in records).items())
        ),
        adverse_event_count=sum(1 for record in records if record.labels.adverse_event),
        average_effect_proxy=round(
            sum(record.expected_effect_proxy for record in records) / len(records), 4
        ),
        average_adherence_proxy=round(
            sum(record.adherence_proxy for record in records) / len(records), 4
        ),
        average_side_effect_proxy=round(
            sum(record.side_effect_proxy for record in records) / len(records), 4
        ),
        average_delta_aggregate_z=round(
            sum(
                record.follow_up_pro.aggregate_z - record.baseline_pro.aggregate_z
                for record in records
            )
            / len(records),
            4,
        ),
    )


def build_rich_policy_training_rows_v3(
    records: list[RichSyntheticCohortRecord],
) -> list[RichPolicyTrainingRow]:
    rows = build_rich_policy_training_rows(records)
    return [
        row.model_copy(update={"dataset_version": POLICY_DATASET_VERSION})
        for row in rows
    ]


def summarize_rich_policy_training_rows_v3(
    rows: list[RichPolicyTrainingRow],
) -> RichPolicyTrainingSummary:
    summary = summarize_rich_policy_training_rows(rows)
    return summary.model_copy(update={"dataset_version": POLICY_DATASET_VERSION})


def _is_effect_enrichment_target(record: RichSyntheticCohortRecord) -> bool:
    request = record.request
    return (
        not request.user_profile.pregnant
        and not request.conditions
        and not request.medications
        and not request.input_availability.cgm
    )


def _build_effect_rich_user_records(
    *,
    user_index: int,
    user_seed: int,
    base_user_records: list[RichSyntheticCohortRecord],
) -> list[RichSyntheticCohortRecord]:
    baseline_record = base_user_records[0]
    rng = Random(user_seed)
    family = FAMILY_CONFIGS[user_index % len(FAMILY_CONFIGS)]
    mode = LOW_RISK_EFFECT_MODES[user_index % len(LOW_RISK_EFFECT_MODES)]
    user_id = f"syn-v3-user-{user_index:03d}"
    baseline_pro = _build_effect_rich_baseline(
        goal=family.goal,
        rng=rng,
    )
    records: list[RichSyntheticCohortRecord] = []

    for step, day_index in TRAJECTORY_STEPS:
        request = _build_effect_rich_request(
            baseline_record=baseline_record,
            user_index=user_index,
            step=step,
            family=family,
            mode=mode,
        )
        response = recommend(request)
        recommendation_keys = [item.ingredient_key for item in response.recommendations[:2]]
        if len(recommendation_keys) < 2 or response.status != RecommendationStatus.OK:
            return _clone_base_user_records(
                user_index=user_index,
                base_user_records=base_user_records,
            )

        active_candidate = _choose_active_candidate(
            recommendation_keys=recommendation_keys,
            request=request,
            step=step,
            mode=mode,
        )
        regimen = _build_effect_rich_regimen(
            recommendation_keys=recommendation_keys,
            active_candidate=active_candidate,
            step=step,
            mode=mode,
        )
        adherence_proxy = _compute_effect_rich_adherence(
            request=request,
            step=step,
            mode=mode,
        )
        side_effect_proxy = _compute_effect_rich_side_effect(
            request=request,
            step=step,
            mode=mode,
        )
        follow_up_pro, delta_z_by_domain, expected_effect_proxy = _build_effect_rich_follow_up(
            baseline_pro=baseline_pro,
            request=request,
            regimen=regimen,
            step=step,
            adherence_proxy=adherence_proxy,
            side_effect_proxy=side_effect_proxy,
        )
        next_action = _label_effect_rich_action(
            step=step,
            expected_effect_proxy=expected_effect_proxy,
            adherence_proxy=adherence_proxy,
            side_effect_proxy=side_effect_proxy,
        )
        adverse_event = side_effect_proxy >= 0.62
        records.append(
            RichSyntheticCohortRecord(
                record_id=f"syn-v3-{user_index:03d}-step-{step}",
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
                    reason_code=_reason_code(next_action),
                    safety_status=response.status,
                    risk_tier="low",
                    adverse_event=adverse_event,
                    closed_loop_state=_closed_loop_state_v3(
                        step=step,
                        next_action=next_action,
                        adverse_event=adverse_event,
                    ),
                ),
            )
        )
    return records


def _clone_base_user_records(
    *,
    user_index: int,
    base_user_records: list[RichSyntheticCohortRecord],
) -> list[RichSyntheticCohortRecord]:
    cloned: list[RichSyntheticCohortRecord] = []
    for base_record in base_user_records:
        payload = base_record.request.model_dump(mode="json")
        payload["request_id"] = f"syn-v3-req-{user_index:03d}-step-{base_record.trajectory_step}"
        cloned.append(
            base_record.model_copy(
                update={
                    "record_id": f"syn-v3-{user_index:03d}-step-{base_record.trajectory_step}",
                    "user_id": f"syn-v3-user-{user_index:03d}",
                    "cohort_version": COHORT_VERSION,
                    "request": RecommendationRequest.model_validate(payload),
                }
            )
        )
    return cloned


def _build_effect_rich_request(
    *,
    baseline_record: RichSyntheticCohortRecord,
    user_index: int,
    step: int,
    family: EffectRichFamily,
    mode: str,
) -> RecommendationRequest:
    payload = baseline_record.request.model_dump(mode="json")
    payload["request_id"] = f"syn-v3-req-{user_index:03d}-step-{step}"
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
    payload["input_availability"]["genetic"] = False
    payload["input_availability"]["wearable"] = family.wearer_share
    payload["preferences"]["max_products"] = 2
    payload["lifestyle"]["sleep_hours"] = round(
        family.preferred_sleep_hours + ((user_index % 3) - 1) * 0.1,
        1,
    )
    payload["lifestyle"]["stress_level"] = min(
        5,
        max(
            1,
            family.preferred_stress + ((user_index + step) % 2),
        ),
    )
    if mode == "near_tie_adherence_sensitive":
        payload["preferences"]["budget_level"] = "low"
    else:
        payload["preferences"]["budget_level"] = "medium"
    return RecommendationRequest.model_validate(payload)


def _build_effect_rich_baseline(
    *,
    goal: RecommendationGoal,
    rng: Random,
) -> PROSnapshot:
    domain_z: dict[str, float] = {}
    for domain_key in DOMAIN_KEYS:
        if domain_key == goal.value:
            value = -1.45 + (rng.random() * 0.35)
        else:
            value = -0.3 + (rng.random() * 0.45)
        domain_z[domain_key] = round(max(-3.0, min(3.0, value)), 3)
    return PROSnapshot(
        domain_z=domain_z,
        aggregate_z=round(sum(domain_z.values()) / len(domain_z), 3),
    )


def _choose_active_candidate(
    *,
    recommendation_keys: list[str],
    request: RecommendationRequest,
    step: int,
    mode: str,
) -> str:
    top_key, second_key = recommendation_keys[:2]
    if mode == "near_tie_secondary_win":
        return second_key
    if mode == "near_tie_primary_win":
        return top_key
    if mode == "near_tie_delayed_flip":
        return second_key if step <= 1 else top_key
    if mode == "near_tie_adherence_sensitive":
        return second_key if (request.lifestyle.stress_level or 0) >= 4 else top_key
    return top_key


def _build_effect_rich_regimen(
    *,
    recommendation_keys: list[str],
    active_candidate: str,
    step: int,
    mode: str,
) -> list[RichRegimenItem]:
    regimen: list[RichRegimenItem] = []
    for position, candidate_key in enumerate(recommendation_keys[:2]):
        base_dose, dose_unit, _ = {
            "magnesium_glycinate": (240.0, "mg", "night"),
            "l_theanine": (200.0, "mg", "split_evening"),
            "soluble_fiber": (5.0, "g", "split_premeal"),
            "probiotics": (10.0, "billion_cfu", "morning"),
            "vitamin_d3": (2000.0, "IU", "weekly_split"),
            "vitamin_c": (500.0, "mg", "midday_split"),
        }.get(candidate_key, (1.0, "serving", "morning"))
        if candidate_key == active_candidate:
            regimen_status = "active"
            dose_multiplier = 0.92 + (0.07 * step)
        else:
            regimen_status = "planned"
            dose_multiplier = 0.58 if mode == "near_tie_adherence_sensitive" else 0.72
        if mode == "near_tie_delayed_flip" and candidate_key != active_candidate and step >= 2:
            regimen_status = "active" if position == 0 else "planned"
            dose_multiplier = 0.88 if position == 0 else 0.5
        regimen.append(
            RichRegimenItem(
                ingredient_key=candidate_key,
                display_name=candidate_key.replace("_", " ").title(),
                daily_dose=round(base_dose * dose_multiplier, 3),
                dose_unit=dose_unit,
                schedule=_schedule_for_candidate(
                    candidate_key=candidate_key,
                    step=step,
                    active=(candidate_key == active_candidate),
                ),
                regimen_status=regimen_status,
            )
        )
    return regimen


def _schedule_for_candidate(
    *,
    candidate_key: str,
    step: int,
    active: bool,
) -> str:
    if candidate_key == "magnesium_glycinate":
        return "night_split" if active and step >= 2 else "night"
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


def _compute_effect_rich_adherence(
    *,
    request: RecommendationRequest,
    step: int,
    mode: str,
) -> float:
    base = {
        "near_tie_secondary_win": (0.72, 0.75, 0.79, 0.82, 0.84),
        "near_tie_primary_win": (0.74, 0.78, 0.83, 0.85, 0.87),
        "near_tie_delayed_flip": (0.7, 0.72, 0.77, 0.81, 0.84),
        "near_tie_adherence_sensitive": (0.62, 0.58, 0.64, 0.71, 0.77),
    }[mode][step]
    if request.preferences.budget_level.value == "low":
        base -= 0.05
    return round(max(0.0, min(1.0, base)), 3)


def _compute_effect_rich_side_effect(
    *,
    request: RecommendationRequest,
    step: int,
    mode: str,
) -> float:
    base = {
        "near_tie_secondary_win": (0.08, 0.11, 0.14, 0.12, 0.1),
        "near_tie_primary_win": (0.09, 0.12, 0.13, 0.12, 0.11),
        "near_tie_delayed_flip": (0.1, 0.14, 0.18, 0.14, 0.12),
        "near_tie_adherence_sensitive": (0.12, 0.18, 0.22, 0.19, 0.16),
    }[mode][step]
    if (request.lifestyle.stress_level or 0) >= 4:
        base += 0.02
    return round(max(0.0, min(1.0, base)), 3)


def _build_effect_rich_follow_up(
    *,
    baseline_pro: PROSnapshot,
    request: RecommendationRequest,
    regimen: list[RichRegimenItem],
    step: int,
    adherence_proxy: float,
    side_effect_proxy: float,
) -> tuple[PROSnapshot, dict[str, float], float]:
    goal_key = request.goals[0].value
    domain_z: dict[str, float] = {}
    active_items = [item for item in regimen if item.regimen_status == "active"]
    active_item = active_items[0] if active_items else regimen[0]
    goal_delta = _candidate_goal_delta(
        candidate_key=active_item.ingredient_key,
        request=request,
        step=step,
        daily_dose=active_item.daily_dose,
        schedule=active_item.schedule,
        adherence_proxy=adherence_proxy,
        side_effect_proxy=side_effect_proxy,
    )
    for domain_key, baseline_value in baseline_pro.domain_z.items():
        if domain_key == goal_key:
            delta = goal_delta
        else:
            delta = max(0.01, goal_delta * 0.18)
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
                (goal_delta * 0.78)
                + (0.08 * adherence_proxy)
                - (0.12 * side_effect_proxy)
                - 0.03,
            ),
        ),
        3,
    )
    return follow_up_pro, delta_z_by_domain, expected_effect_proxy


def _candidate_goal_delta(
    *,
    candidate_key: str,
    request: RecommendationRequest,
    step: int,
    daily_dose: float,
    schedule: str,
    adherence_proxy: float,
    side_effect_proxy: float,
) -> float:
    sleep_hours = request.lifestyle.sleep_hours or 7.0
    stress_level = request.lifestyle.stress_level or 2
    goal = request.goals[0]
    step_curve = (0.02, 0.09, 0.14, 0.18, 0.21)[step]
    schedule_bonus = 0.03 if "split" in schedule else 0.0
    if goal == RecommendationGoal.SLEEP_SUPPORT:
        magnesium_bias = 0.08 + max(0.0, 6.4 - sleep_hours) * 0.035
        theanine_bias = 0.05 + max(0.0, stress_level - 3) * 0.04
        ingredient_bias = (
            magnesium_bias if candidate_key == "magnesium_glycinate" else theanine_bias
        )
    elif goal == RecommendationGoal.STRESS_SUPPORT:
        theanine_bias = 0.08 + max(0.0, stress_level - 3) * 0.04
        magnesium_bias = 0.06 + max(0.0, 6.3 - sleep_hours) * 0.03
        ingredient_bias = theanine_bias if candidate_key == "l_theanine" else magnesium_bias
    elif goal == RecommendationGoal.GUT_HEALTH:
        ingredient_bias = 0.08 if candidate_key == "soluble_fiber" else 0.075
        ingredient_bias += 0.025 if "split" in schedule else 0.0
        ingredient_bias += 0.015 if stress_level <= 2 and candidate_key == "probiotics" else 0.0
    else:
        ingredient_bias = 0.08 if candidate_key == "vitamin_d3" else 0.074
        ingredient_bias += (
            0.015
            if request.input_availability.wearable and candidate_key == "vitamin_c"
            else 0.0
        )
        ingredient_bias += 0.02 if step >= 2 and candidate_key == "vitamin_d3" else 0.0

    dose_bonus = min(0.06, max(0.0, daily_dose) / 6000.0)
    adherence_term = adherence_proxy * 0.12
    side_effect_penalty = side_effect_proxy * 0.08
    delta = (
        step_curve
        + ingredient_bias
        + schedule_bonus
        + dose_bonus
        + adherence_term
        - side_effect_penalty
    )
    return round(max(0.04, min(0.44, delta)), 3)


def _label_effect_rich_action(
    *,
    step: int,
    expected_effect_proxy: float,
    adherence_proxy: float,
    side_effect_proxy: float,
) -> NextAction:
    if side_effect_proxy >= 0.62:
        return NextAction.REDUCE_OR_STOP
    if adherence_proxy < 0.57 and step <= 2:
        return NextAction.ASK_TARGETED_FOLLOWUP
    if expected_effect_proxy < 0.18:
        return NextAction.RE_OPTIMIZE
    if expected_effect_proxy < 0.24:
        return NextAction.MONITOR_ONLY
    return NextAction.CONTINUE_PLAN


def _reason_code(next_action: NextAction) -> str:
    mapping = {
        NextAction.CONTINUE_PLAN: "effect_rich_continue_plan",
        NextAction.MONITOR_ONLY: "effect_rich_monitor_plateau",
        NextAction.RE_OPTIMIZE: "effect_rich_reoptimize_near_tie_gap",
        NextAction.ASK_TARGETED_FOLLOWUP: "effect_rich_adherence_followup",
        NextAction.REDUCE_OR_STOP: "effect_rich_tolerability_reduction",
    }
    return mapping.get(next_action, "effect_rich_fallback")


def _closed_loop_state_v3(
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
    if next_action == NextAction.MONITOR_ONLY:
        return "recommendation_ready" if step == 0 else "followup_due"
    return "recommendation_ready" if step == 0 else "followup_due"


def write_rich_synthetic_jsonl_v3(
    path: str | Path,
    records: list[RichSyntheticCohortRecord],
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(record.model_dump_json() for record in records) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "COHORT_VERSION",
    "POLICY_DATASET_VERSION",
    "TARGET_EFFECT_ACTIONS",
    "build_rich_policy_training_rows_v3",
    "generate_rich_synthetic_cohort_v3",
    "summarize_rich_policy_training_rows_v3",
    "summarize_rich_synthetic_cohort_v3",
    "validate_rich_policy_training_rows",
    "validate_rich_synthetic_cohort",
    "write_rich_synthetic_jsonl_v3",
]
