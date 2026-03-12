from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from random import Random
from typing import Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    ActivityLevel,
    BiologicalSex,
    BudgetLevel,
    NextAction,
    RecommendationGoal,
    RecommendationRequest,
    RecommendationStatus,
)

COHORT_VERSION = "synthetic_longitudinal_v2"
POLICY_DATASET_VERSION = "policy_training_v1"
DEFAULT_RICH_SYNTHETIC_SEED = 20260310
DEFAULT_RICH_USER_COUNT = 96
TRAJECTORY_STEPS: tuple[tuple[int, int], ...] = ((0, 0), (1, 7), (2, 14), (3, 30), (4, 45))
DOMAIN_KEYS = tuple(goal.value for goal in RecommendationGoal)
REQUIRED_POLICY_ACTIONS = {
    NextAction.CONTINUE_PLAN.value,
    NextAction.RE_OPTIMIZE.value,
    NextAction.REDUCE_OR_STOP.value,
    NextAction.MONITOR_ONLY.value,
    NextAction.ASK_TARGETED_FOLLOWUP.value,
    NextAction.TRIGGER_SAFETY_RECHECK.value,
}
TRAJECTORY_MODES = (
    "stable_continue",
    "monitor_plateau",
    "reoptimize_low_response",
    "reduce_side_effect",
    "targeted_followup_low_adherence",
    "safety_recheck_high_risk",
)
DOSE_TEMPLATES: dict[str, tuple[float, str, str]] = {
    "magnesium_glycinate": (240.0, "mg", "night"),
    "l_theanine": (200.0, "mg", "night"),
    "vitamin_d3": (2000.0, "IU", "morning"),
    "vitamin_c": (500.0, "mg", "morning"),
    "zinc": (15.0, "mg", "with_breakfast"),
    "omega3": (1000.0, "mg", "with_lunch"),
    "coq10": (150.0, "mg", "with_lunch"),
    "soluble_fiber": (5.0, "g", "before_dinner"),
    "berberine": (500.0, "mg", "before_dinner"),
    "probiotics": (10.0, "billion_cfu", "morning"),
    "vitamin_b_complex": (1.0, "capsule", "morning"),
    "calcium_citrate": (500.0, "mg", "with_dinner"),
    "glucosamine": (1200.0, "mg", "with_lunch"),
}
GOAL_FALLBACK_INGREDIENTS: dict[RecommendationGoal, tuple[str, ...]] = {
    RecommendationGoal.SLEEP_SUPPORT: ("magnesium_glycinate", "l_theanine"),
    RecommendationGoal.STRESS_SUPPORT: ("l_theanine", "magnesium_glycinate"),
    RecommendationGoal.IMMUNITY_SUPPORT: ("vitamin_c", "zinc"),
    RecommendationGoal.ENERGY_SUPPORT: ("vitamin_b_complex", "coq10"),
    RecommendationGoal.GUT_HEALTH: ("probiotics", "soluble_fiber"),
    RecommendationGoal.BONE_JOINT: ("vitamin_d3", "calcium_citrate"),
    RecommendationGoal.HEART_HEALTH: ("omega3", "coq10"),
    RecommendationGoal.BLOOD_GLUCOSE: ("soluble_fiber", "berberine"),
    RecommendationGoal.GENERAL_WELLNESS: ("vitamin_d3", "vitamin_b_complex"),
}
DEFAULT_SYMPTOM_BY_GOAL: dict[RecommendationGoal, str] = {
    RecommendationGoal.SLEEP_SUPPORT: "difficulty_falling_asleep",
    RecommendationGoal.STRESS_SUPPORT: "high_stress",
    RecommendationGoal.IMMUNITY_SUPPORT: "frequent_fatigue",
    RecommendationGoal.ENERGY_SUPPORT: "fatigue",
    RecommendationGoal.GUT_HEALTH: "bloating",
    RecommendationGoal.BONE_JOINT: "low_sun_exposure",
    RecommendationGoal.HEART_HEALTH: "low_activity_tolerance",
    RecommendationGoal.BLOOD_GLUCOSE: "post_meal_spike_concern",
    RecommendationGoal.GENERAL_WELLNESS: "frequent_fatigue",
}


class PROSnapshot(BaseModel):
    domain_z: dict[str, float] = Field(default_factory=dict)
    aggregate_z: float


class RichRegimenItem(BaseModel):
    ingredient_key: str
    display_name: str
    daily_dose: float = Field(ge=0.0)
    dose_unit: str
    schedule: str
    regimen_status: Literal["planned", "active", "reduced", "stopped"]


class RichSyntheticLabels(BaseModel):
    next_action: NextAction
    reason_code: str
    safety_status: RecommendationStatus
    risk_tier: Literal["low", "moderate", "high"]
    adverse_event: bool
    closed_loop_state: Literal[
        "baseline_questionnaire_due",
        "safety_review",
        "recommendation_ready",
        "intake_active",
        "followup_due",
        "re_evaluation",
        "adjust_plan",
        "stop_or_escalate",
    ]


class RichSyntheticCohortRecord(BaseModel):
    record_id: str
    user_id: str
    cohort_version: str = COHORT_VERSION
    rng_seed: int
    trajectory_mode: str
    trajectory_step: int = Field(ge=0)
    day_index: int = Field(ge=0)
    request: RecommendationRequest
    baseline_pro: PROSnapshot
    follow_up_pro: PROSnapshot
    delta_z_by_domain: dict[str, float] = Field(default_factory=dict)
    regimen: list[RichRegimenItem] = Field(default_factory=list)
    baseline_recommendations: list[str] = Field(default_factory=list)
    expected_effect_proxy: float = Field(ge=-1.0, le=1.0)
    adherence_proxy: float = Field(ge=0.0, le=1.0)
    side_effect_proxy: float = Field(ge=0.0, le=1.0)
    labels: RichSyntheticLabels


class RichSyntheticCohortSummary(BaseModel):
    cohort_version: str = COHORT_VERSION
    seed: int
    user_count: int
    record_count: int
    structured_current_supplement_dose_record_count: int = 0
    total_trajectory_steps: int
    step_counts: dict[int, int]
    next_action_counts: dict[str, int]
    safety_status_counts: dict[str, int]
    risk_tier_counts: dict[str, int]
    state_counts: dict[str, int]
    modality_counts: dict[str, int]
    goal_counts: dict[str, int]
    trajectory_mode_counts: dict[str, int]
    adverse_event_count: int
    average_effect_proxy: float
    average_adherence_proxy: float
    average_side_effect_proxy: float
    average_delta_aggregate_z: float


class RichPolicyTrainingRow(BaseModel):
    dataset_version: str = POLICY_DATASET_VERSION
    record_id: str
    user_id: str
    trajectory_step: int
    day_index: int
    next_action: str
    safety_status: str
    risk_tier: str
    closed_loop_state: str
    goals: list[str] = Field(default_factory=list)
    symptom_keys: list[str] = Field(default_factory=list)
    condition_keys: list[str] = Field(default_factory=list)
    medication_keys: list[str] = Field(default_factory=list)
    regimen_keys: list[str] = Field(default_factory=list)
    modality_flags: list[str] = Field(default_factory=list)
    feature_row: dict[str, float] = Field(default_factory=dict)


class RichPolicyTrainingSummary(BaseModel):
    dataset_version: str = POLICY_DATASET_VERSION
    record_count: int
    user_count: int
    next_action_counts: dict[str, int]
    risk_tier_counts: dict[str, int]
    state_counts: dict[str, int]
    modality_counts: dict[str, int]
    average_feature_count: float


@dataclass(frozen=True)
class RichArchetype:
    name: str
    goals: tuple[RecommendationGoal, ...]
    symptoms: tuple[str, ...]
    conditions: tuple[str, ...]
    medications: tuple[tuple[str, str], ...]
    pregnancy: bool = False
    wearable: bool = False
    cgm: bool = False
    genetic: bool = False
    budget_level: BudgetLevel = BudgetLevel.MEDIUM
    max_products: int = 2
    activity_level: ActivityLevel = ActivityLevel.LIGHTLY_ACTIVE
    stress_level: int = 2
    sleep_hours: float | None = 7.0
    avoid_ingredients: tuple[str, ...] = ()
    current_supplements: tuple[tuple[str, tuple[str, ...]], ...] = ()


ARCHETYPES: tuple[RichArchetype, ...] = (
    RichArchetype(
        "sleep_recovery",
        (RecommendationGoal.SLEEP_SUPPORT,),
        ("difficulty_falling_asleep",),
        (),
        (),
        wearable=True,
        stress_level=4,
        sleep_hours=5.4,
    ),
    RichArchetype(
        "stress_monitor",
        (RecommendationGoal.STRESS_SUPPORT, RecommendationGoal.SLEEP_SUPPORT),
        ("high_stress",),
        (),
        (),
        wearable=True,
        genetic=True,
        stress_level=4,
        sleep_hours=6.0,
    ),
    RichArchetype(
        "energy_low_adherence",
        (RecommendationGoal.ENERGY_SUPPORT,),
        ("fatigue",),
        (),
        (),
        wearable=True,
        budget_level=BudgetLevel.LOW,
        max_products=1,
    ),
    RichArchetype(
        "gut_support", (RecommendationGoal.GUT_HEALTH,), ("bloating",), (), (), genetic=True
    ),
    RichArchetype(
        "glucose_sensor",
        (RecommendationGoal.BLOOD_GLUCOSE,),
        ("post_meal_spike_concern",),
        (),
        (),
        cgm=True,
        genetic=True,
    ),
    RichArchetype(
        "heart_anticoagulant",
        (RecommendationGoal.HEART_HEALTH,),
        (),
        (),
        (("warfarin", "5mg"),),
        wearable=True,
    ),
    RichArchetype(
        "pregnancy_mixed",
        (RecommendationGoal.GENERAL_WELLNESS, RecommendationGoal.BLOOD_GLUCOSE),
        (),
        ("kidney disease",),
        (),
        pregnancy=True,
        wearable=True,
        cgm=True,
        genetic=True,
    ),
    RichArchetype(
        "bone_joint", (RecommendationGoal.BONE_JOINT,), ("low_sun_exposure",), (), (), genetic=True
    ),
    RichArchetype(
        "multi_goal_high_risk",
        (RecommendationGoal.HEART_HEALTH, RecommendationGoal.BLOOD_GLUCOSE),
        ("post_meal_spike_concern",),
        ("chronic kidney disease",),
        (("warfarin", "5mg"),),
        wearable=True,
        cgm=True,
        genetic=True,
        budget_level=BudgetLevel.HIGH,
    ),
)


def generate_rich_synthetic_cohort(
    *,
    seed: int = DEFAULT_RICH_SYNTHETIC_SEED,
    user_count: int = DEFAULT_RICH_USER_COUNT,
) -> list[RichSyntheticCohortRecord]:
    records: list[RichSyntheticCohortRecord] = []
    cohort_rng = Random(seed)
    for user_index in range(user_count):
        user_seed = cohort_rng.randint(1, 10_000_000)
        user_rng = Random(user_seed)
        archetype = ARCHETYPES[user_index % len(ARCHETYPES)]
        trajectory_mode = _choose_trajectory_mode(archetype, user_index)
        baseline_request = _build_request(user_index=user_index, archetype=archetype)
        baseline_pro = _build_baseline_pro(archetype=archetype, rng=user_rng)
        current_request = baseline_request
        current_regimen_keys: list[str] = []

        for step, day_index in TRAJECTORY_STEPS:
            response = recommend(current_request)
            baseline_recommendations = [
                item.ingredient_key
                for item in response.recommendations[: current_request.preferences.max_products]
            ]
            follow_up_pro = _build_follow_up_pro(
                baseline_pro=baseline_pro,
                request=current_request,
                step=step,
                trajectory_mode=trajectory_mode,
            )
            delta_z_by_domain = {
                domain_key: round(
                    follow_up_pro.domain_z[domain_key] - baseline_pro.domain_z[domain_key],
                    3,
                )
                for domain_key in DOMAIN_KEYS
            }
            expected_effect_proxy = _compute_effect_proxy(
                request=current_request,
                response=response,
                step=step,
                delta_z_by_domain=delta_z_by_domain,
            )
            adherence_proxy = _compute_adherence_proxy(
                step=step,
                trajectory_mode=trajectory_mode,
                request=current_request,
            )
            side_effect_proxy = _compute_side_effect_proxy(
                step=step,
                trajectory_mode=trajectory_mode,
                request=current_request,
                response=response,
            )
            risk_tier = _risk_tier(current_request, response)
            adverse_event = _is_adverse_event(
                risk_tier=risk_tier,
                step=step,
                side_effect_proxy=side_effect_proxy,
            )
            next_action, reason_code = _label_next_action(
                step=step,
                response=response,
                trajectory_mode=trajectory_mode,
                adherence_proxy=adherence_proxy,
                expected_effect_proxy=expected_effect_proxy,
                side_effect_proxy=side_effect_proxy,
                risk_tier=risk_tier,
                adverse_event=adverse_event,
            )
            closed_loop_state = _closed_loop_state(
                step=step,
                next_action=next_action,
                adverse_event=adverse_event,
            )
            regimen = _build_regimen(
                request=current_request,
                baseline_recommendations=baseline_recommendations,
                current_regimen_keys=current_regimen_keys,
                next_action=next_action,
            )
            current_regimen_keys = [
                item.ingredient_key
                for item in regimen
                if item.regimen_status in {"planned", "active", "reduced"}
            ]
            records.append(
                RichSyntheticCohortRecord(
                    record_id=f"syn-v2-{user_index:03d}-step-{step}",
                    user_id=f"syn-v2-user-{user_index:03d}",
                    rng_seed=user_seed,
                    trajectory_mode=trajectory_mode,
                    trajectory_step=step,
                    day_index=day_index,
                    request=current_request,
                    baseline_pro=baseline_pro,
                    follow_up_pro=follow_up_pro,
                    delta_z_by_domain=delta_z_by_domain,
                    regimen=regimen,
                    baseline_recommendations=baseline_recommendations,
                    expected_effect_proxy=expected_effect_proxy,
                    adherence_proxy=adherence_proxy,
                    side_effect_proxy=side_effect_proxy,
                    labels=RichSyntheticLabels(
                        next_action=next_action,
                        reason_code=reason_code,
                        safety_status=response.status,
                        risk_tier=risk_tier,
                        adverse_event=adverse_event,
                        closed_loop_state=closed_loop_state,
                    ),
                )
            )
            current_request = _advance_request(
                request=current_request,
                baseline_request=baseline_request,
                regimen=regimen,
                follow_up_pro=follow_up_pro,
                trajectory_mode=trajectory_mode,
                step=step,
            )
    return records


def build_rich_policy_training_rows(
    records: list[RichSyntheticCohortRecord],
) -> list[RichPolicyTrainingRow]:
    rows: list[RichPolicyTrainingRow] = []
    for record in records:
        modality_flags = sorted(
            flag
            for flag, enabled in {
                "wearable": record.request.input_availability.wearable,
                "cgm": record.request.input_availability.cgm,
                "genetic": record.request.input_availability.genetic,
            }.items()
            if enabled
        )
        rows.append(
            RichPolicyTrainingRow(
                record_id=record.record_id,
                user_id=record.user_id,
                trajectory_step=record.trajectory_step,
                day_index=record.day_index,
                next_action=record.labels.next_action.value,
                safety_status=record.labels.safety_status.value,
                risk_tier=record.labels.risk_tier,
                closed_loop_state=record.labels.closed_loop_state,
                goals=[goal.value for goal in record.request.goals],
                symptom_keys=sorted(record.request.symptoms),
                condition_keys=sorted(record.request.conditions),
                medication_keys=sorted(
                    medication.name.strip().lower() for medication in record.request.medications
                ),
                regimen_keys=sorted(item.ingredient_key for item in record.regimen),
                modality_flags=modality_flags,
                feature_row=_build_policy_feature_row(record),
            )
        )
    return rows


def validate_rich_synthetic_cohort(
    records: list[RichSyntheticCohortRecord],
) -> list[str]:
    issues: list[str] = []
    if len(records) < 200:
        issues.append("record_count_below_minimum_200")
    seen_ids: set[str] = set()
    user_steps: defaultdict[str, list[int]] = defaultdict(list)
    action_counts = Counter(record.labels.next_action.value for record in records)
    for record in records:
        if record.record_id in seen_ids:
            issues.append(f"duplicate_record_id:{record.record_id}")
        seen_ids.add(record.record_id)
        user_steps[record.user_id].append(record.trajectory_step)
        if not record.baseline_pro.domain_z:
            issues.append(f"missing_baseline_pro:{record.record_id}")
        if not record.follow_up_pro.domain_z:
            issues.append(f"missing_follow_up_pro:{record.record_id}")
        if record.trajectory_step > 0 and not record.regimen:
            issues.append(f"missing_regimen_after_step0:{record.record_id}")
        for regimen_item in record.regimen:
            if not regimen_item.schedule:
                issues.append(f"missing_regimen_schedule:{record.record_id}")
    expected_steps = [item[0] for item in TRAJECTORY_STEPS]
    for user_id, steps in user_steps.items():
        if sorted(steps) != expected_steps:
            issues.append(f"trajectory_steps_incomplete:{user_id}")
    missing_actions = REQUIRED_POLICY_ACTIONS - set(action_counts)
    if missing_actions:
        issues.append(f"missing_required_policy_actions:{sorted(missing_actions)}")
    return issues


def summarize_rich_synthetic_cohort(
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


def summarize_rich_policy_training_rows(
    rows: list[RichPolicyTrainingRow],
) -> RichPolicyTrainingSummary:
    modality_counts = Counter(modality for row in rows for modality in row.modality_flags)
    return RichPolicyTrainingSummary(
        record_count=len(rows),
        user_count=len({row.user_id for row in rows}),
        next_action_counts=dict(sorted(Counter(row.next_action for row in rows).items())),
        risk_tier_counts=dict(sorted(Counter(row.risk_tier for row in rows).items())),
        state_counts=dict(sorted(Counter(row.closed_loop_state for row in rows).items())),
        modality_counts=dict(sorted(modality_counts.items())),
        average_feature_count=round(sum(len(row.feature_row) for row in rows) / len(rows), 2),
    )


def validate_rich_policy_training_rows(rows: list[RichPolicyTrainingRow]) -> list[str]:
    if not rows:
        return ["policy_training_rows_empty"]
    missing_actions = REQUIRED_POLICY_ACTIONS - {row.next_action for row in rows}
    if missing_actions:
        return [f"policy_rows_missing_required_actions:{sorted(missing_actions)}"]
    return []


def _build_request(*, user_index: int, archetype: RichArchetype) -> RecommendationRequest:
    biological_sex = BiologicalSex.FEMALE if user_index % 2 == 0 else BiologicalSex.MALE
    if archetype.pregnancy:
        biological_sex = BiologicalSex.FEMALE
    payload = {
        "request_id": f"syn-v2-req-{user_index:03d}-step-0",
        "user_profile": {
            "age": 24 + ((user_index * 5) % 45),
            "biological_sex": biological_sex.value,
            "pregnant": archetype.pregnancy,
        },
        "goals": [goal.value for goal in archetype.goals],
        "symptoms": list(archetype.symptoms),
        "conditions": list(archetype.conditions),
        "medications": [{"name": name, "dose": dose} for name, dose in archetype.medications],
        "current_supplements": [
            {"name": name, "ingredients": list(ingredients)}
            for name, ingredients in archetype.current_supplements
        ],
        "lifestyle": {
            "sleep_hours": archetype.sleep_hours,
            "stress_level": archetype.stress_level,
            "activity_level": archetype.activity_level.value,
            "smoker": False,
            "alcohol_per_week": 1,
        },
        "input_availability": {
            "survey": True,
            "nhis": user_index % 3 != 0,
            "wearable": archetype.wearable,
            "cgm": archetype.cgm,
            "genetic": archetype.genetic,
        },
        "preferences": {
            "budget_level": archetype.budget_level.value,
            "max_products": archetype.max_products,
            "avoid_ingredients": list(archetype.avoid_ingredients),
        },
    }
    return RecommendationRequest.model_validate(payload)


def _choose_trajectory_mode(archetype: RichArchetype, user_index: int) -> str:
    if archetype.pregnancy or archetype.conditions or archetype.medications:
        return "safety_recheck_high_risk" if user_index % 2 == 0 else "reduce_side_effect"
    return TRAJECTORY_MODES[user_index % len(TRAJECTORY_MODES)]


def _build_baseline_pro(*, archetype: RichArchetype, rng: Random) -> PROSnapshot:
    goal_values = {goal.value for goal in archetype.goals}
    domain_z: dict[str, float] = {}
    for domain_key in DOMAIN_KEYS:
        if domain_key in goal_values:
            value = -1.6 + (rng.random() * 0.7)
        else:
            value = -0.2 + (rng.random() * 0.6)
        domain_z[domain_key] = round(max(-3.0, min(3.0, value)), 3)
    return PROSnapshot(
        domain_z=domain_z,
        aggregate_z=round(sum(domain_z.values()) / len(domain_z), 3),
    )


def _build_follow_up_pro(
    *,
    baseline_pro: PROSnapshot,
    request: RecommendationRequest,
    step: int,
    trajectory_mode: str,
) -> PROSnapshot:
    goal_values = {goal.value for goal in request.goals}
    progress_curve = {
        "stable_continue": (0.0, 0.28, 0.46, 0.58, 0.66),
        "monitor_plateau": (0.0, 0.12, 0.16, 0.18, 0.2),
        "reoptimize_low_response": (0.0, 0.04, -0.03, 0.18, 0.34),
        "reduce_side_effect": (0.0, -0.06, -0.12, -0.04, 0.08),
        "targeted_followup_low_adherence": (0.0, 0.05, 0.08, 0.21, 0.29),
        "safety_recheck_high_risk": (0.0, -0.12, -0.18, -0.08, 0.04),
    }[trajectory_mode]
    delta = progress_curve[step]
    domain_z = {}
    for domain_key, baseline_value in baseline_pro.domain_z.items():
        adjustment = delta if domain_key in goal_values else delta * 0.35
        domain_z[domain_key] = round(
            max(-3.0, min(3.0, baseline_value + adjustment)),
            3,
        )
    return PROSnapshot(
        domain_z=domain_z,
        aggregate_z=round(sum(domain_z.values()) / len(domain_z), 3),
    )


def _compute_effect_proxy(
    *,
    request: RecommendationRequest,
    response,
    step: int,
    delta_z_by_domain: dict[str, float],
) -> float:
    goal_delta = [
        delta_z_by_domain[goal.value] for goal in request.goals if goal.value in delta_z_by_domain
    ]
    mean_goal_delta = sum(goal_delta) / len(goal_delta) if goal_delta else 0.0
    modality_bonus = 0.03 * sum(
        (
            request.input_availability.wearable,
            request.input_availability.cgm,
            request.input_availability.genetic,
        )
    )
    status_penalty = {
        RecommendationStatus.OK: 0.0,
        RecommendationStatus.NEEDS_REVIEW: 0.12,
        RecommendationStatus.BLOCKED: 0.2,
    }[response.status]
    value = (mean_goal_delta * 0.55) + modality_bonus + (0.03 * step) - status_penalty
    return round(max(-1.0, min(1.0, value)), 3)


def _compute_adherence_proxy(
    *,
    step: int,
    trajectory_mode: str,
    request: RecommendationRequest,
) -> float:
    curve = {
        "stable_continue": (0.76, 0.81, 0.84, 0.86, 0.87),
        "monitor_plateau": (0.72, 0.74, 0.76, 0.75, 0.74),
        "reoptimize_low_response": (0.7, 0.65, 0.61, 0.71, 0.78),
        "reduce_side_effect": (0.69, 0.56, 0.38, 0.49, 0.63),
        "targeted_followup_low_adherence": (0.62, 0.48, 0.53, 0.69, 0.77),
        "safety_recheck_high_risk": (0.64, 0.45, 0.4, 0.47, 0.55),
    }[trajectory_mode][step]
    if request.preferences.budget_level == BudgetLevel.LOW:
        curve -= 0.04
    return round(max(0.0, min(1.0, curve)), 3)


def _compute_side_effect_proxy(
    *,
    step: int,
    trajectory_mode: str,
    request: RecommendationRequest,
    response,
) -> float:
    curve = {
        "stable_continue": (0.08, 0.1, 0.12, 0.11, 0.1),
        "monitor_plateau": (0.12, 0.14, 0.16, 0.16, 0.15),
        "reoptimize_low_response": (0.14, 0.2, 0.24, 0.17, 0.15),
        "reduce_side_effect": (0.18, 0.55, 0.76, 0.48, 0.26),
        "targeted_followup_low_adherence": (0.1, 0.14, 0.16, 0.12, 0.1),
        "safety_recheck_high_risk": (0.22, 0.62, 0.81, 0.58, 0.32),
    }[trajectory_mode][step]
    if request.user_profile.pregnant or request.conditions or request.medications:
        curve += 0.08
    if response.status == RecommendationStatus.BLOCKED:
        curve += 0.06
    return round(max(0.0, min(1.0, curve)), 3)


def _risk_tier(
    request: RecommendationRequest,
    response,
) -> Literal["low", "moderate", "high"]:
    if response.status in {
        RecommendationStatus.BLOCKED,
        RecommendationStatus.NEEDS_REVIEW,
    }:
        return "high"
    if request.user_profile.pregnant or request.conditions or request.medications:
        return "high"
    if (
        response.safety_summary.rule_refs
        or request.input_availability.cgm
        or request.input_availability.genetic
        or len(request.goals) > 1
    ):
        return "moderate"
    return "low"


def _is_adverse_event(
    *,
    risk_tier: Literal["low", "moderate", "high"],
    step: int,
    side_effect_proxy: float,
) -> bool:
    if step == 0:
        return False
    if side_effect_proxy >= 0.82:
        return True
    if risk_tier == "high" and side_effect_proxy >= 0.72:
        return True
    return step >= 2 and risk_tier != "low" and side_effect_proxy >= 0.68


def _label_next_action(
    *,
    step: int,
    response,
    trajectory_mode: str,
    adherence_proxy: float,
    expected_effect_proxy: float,
    side_effect_proxy: float,
    risk_tier: Literal["low", "moderate", "high"],
    adverse_event: bool,
) -> tuple[NextAction, str]:
    if response.status == RecommendationStatus.BLOCKED:
        return NextAction.TRIGGER_SAFETY_RECHECK, "structured_safety_block"
    if trajectory_mode == "safety_recheck_high_risk" and (
        step <= 2 or risk_tier == "high" or side_effect_proxy >= 0.58
    ):
        return NextAction.TRIGGER_SAFETY_RECHECK, "high_risk_structured_monitoring"
    if adverse_event or side_effect_proxy >= 0.72:
        return NextAction.REDUCE_OR_STOP, "side_effect_burden_requires_deescalation"
    if trajectory_mode == "reduce_side_effect" and step >= 1 and side_effect_proxy >= 0.45:
        return NextAction.REDUCE_OR_STOP, "tolerability_regimen_reduction"
    if (
        trajectory_mode == "targeted_followup_low_adherence"
        and adherence_proxy < 0.65
        and step <= 2
    ):
        return NextAction.ASK_TARGETED_FOLLOWUP, "adherence_gap_targeted_followup"
    if trajectory_mode == "reoptimize_low_response" and step >= 1 and expected_effect_proxy < 0.16:
        return NextAction.RE_OPTIMIZE, "insufficient_response_reoptimize"
    if trajectory_mode == "monitor_plateau" and step >= 1 and side_effect_proxy < 0.25:
        return NextAction.MONITOR_ONLY, "plateau_monitor_without_change"
    if step == 0 and trajectory_mode == "monitor_plateau":
        return NextAction.MONITOR_ONLY, "baseline_monitoring_window"
    return NextAction.CONTINUE_PLAN, "trajectory_supports_continue_plan"


def _closed_loop_state(
    *,
    step: int,
    next_action: NextAction,
    adverse_event: bool,
) -> Literal[
    "baseline_questionnaire_due",
    "safety_review",
    "recommendation_ready",
    "intake_active",
    "followup_due",
    "re_evaluation",
    "adjust_plan",
    "stop_or_escalate",
]:
    if adverse_event or next_action == NextAction.REDUCE_OR_STOP:
        return "stop_or_escalate"
    if next_action == NextAction.TRIGGER_SAFETY_RECHECK:
        return "safety_review"
    if next_action == NextAction.ASK_TARGETED_FOLLOWUP:
        return "baseline_questionnaire_due" if step == 0 else "re_evaluation"
    if next_action == NextAction.RE_OPTIMIZE:
        return "adjust_plan"
    if next_action == NextAction.MONITOR_ONLY:
        return "recommendation_ready" if step == 0 else "followup_due"
    if step == 0:
        return "recommendation_ready"
    return "intake_active" if step == 1 else "followup_due"


def _build_regimen(
    *,
    request: RecommendationRequest,
    baseline_recommendations: list[str],
    current_regimen_keys: list[str],
    next_action: NextAction,
) -> list[RichRegimenItem]:
    regimen_keys = list(dict.fromkeys(current_regimen_keys or baseline_recommendations))
    if not regimen_keys:
        regimen_keys = _fallback_ingredients(request.goals)
    if next_action == NextAction.RE_OPTIMIZE:
        candidate_keys = _fallback_ingredients(request.goals)
        for ingredient_key in candidate_keys:
            if ingredient_key not in regimen_keys:
                if len(regimen_keys) >= request.preferences.max_products:
                    regimen_keys = regimen_keys[:-1] + [ingredient_key]
                else:
                    regimen_keys.append(ingredient_key)
                break
    regimen_keys = regimen_keys[: request.preferences.max_products]

    regimen: list[RichRegimenItem] = []
    for index, ingredient_key in enumerate(regimen_keys):
        base_dose, dose_unit, schedule = DOSE_TEMPLATES.get(
            ingredient_key,
            (1.0, "serving", "morning"),
        )
        if next_action == NextAction.REDUCE_OR_STOP:
            regimen_status = "stopped" if index == 0 else "reduced"
        elif next_action == NextAction.TRIGGER_SAFETY_RECHECK:
            regimen_status = "reduced" if current_regimen_keys else "planned"
        elif next_action == NextAction.ASK_TARGETED_FOLLOWUP:
            regimen_status = "planned" if not current_regimen_keys else "active"
        elif next_action == NextAction.RE_OPTIMIZE and ingredient_key not in current_regimen_keys:
            regimen_status = "planned"
        else:
            regimen_status = "active" if current_regimen_keys else "planned"

        adjusted_dose = base_dose
        if regimen_status == "reduced":
            adjusted_dose = round(base_dose * 0.65, 3)
        elif regimen_status == "stopped":
            adjusted_dose = 0.0

        regimen.append(
            RichRegimenItem(
                ingredient_key=ingredient_key,
                display_name=ingredient_key.replace("_", " ").title(),
                daily_dose=round(adjusted_dose, 3),
                dose_unit=dose_unit,
                schedule=schedule,
                regimen_status=regimen_status,
            )
        )
    return regimen


def _advance_request(
    *,
    request: RecommendationRequest,
    baseline_request: RecommendationRequest,
    regimen: list[RichRegimenItem],
    follow_up_pro: PROSnapshot,
    trajectory_mode: str,
    step: int,
) -> RecommendationRequest:
    payload = request.model_dump(mode="json")
    payload["request_id"] = (
        f"{payload['request_id'].split('-step-')[0]}-step-{step + 1}"
        if "-step-" in payload["request_id"]
        else f"{payload['request_id']}-step-{step + 1}"
    )
    payload["current_supplements"] = [
        {
            "name": item.display_name,
            "ingredients": [item.ingredient_key],
        }
        for item in regimen
        if item.regimen_status in {"planned", "active", "reduced"}
    ]
    payload["lifestyle"]["sleep_hours"] = _sleep_adjustment(
        payload["lifestyle"].get("sleep_hours"),
        follow_up_pro.aggregate_z,
        trajectory_mode,
    )
    stress_level = payload["lifestyle"].get("stress_level")
    if stress_level is not None:
        if follow_up_pro.aggregate_z >= -0.15:
            stress_level = max(1, stress_level - 1)
        elif trajectory_mode in {
            "reduce_side_effect",
            "safety_recheck_high_risk",
            "targeted_followup_low_adherence",
        }:
            stress_level = min(5, stress_level + 1)
        payload["lifestyle"]["stress_level"] = stress_level

    symptoms = list(payload["symptoms"])
    if (
        trajectory_mode in {"stable_continue", "monitor_plateau"}
        and follow_up_pro.aggregate_z >= -0.2
    ):
        payload["symptoms"] = symptoms[:1]
    elif trajectory_mode == "reoptimize_low_response":
        payload["symptoms"] = symptoms or [_default_symptom_from_goals(request.goals)]
    elif trajectory_mode == "targeted_followup_low_adherence" and step <= 2:
        payload["symptoms"] = symptoms or [_default_symptom_from_goals(request.goals)]
    elif trajectory_mode in {"reduce_side_effect", "safety_recheck_high_risk"}:
        payload["symptoms"] = list(
            dict.fromkeys(symptoms + [_default_symptom_from_goals(request.goals)])
        )
    else:
        payload["symptoms"] = symptoms

    if step >= 2 and not payload["current_supplements"]:
        payload["current_supplements"] = [
            {
                "name": item.display_name,
                "ingredients": [item.ingredient_key],
            }
            for item in _build_regimen(
                request=baseline_request,
                baseline_recommendations=_fallback_ingredients(baseline_request.goals),
                current_regimen_keys=[],
                next_action=NextAction.MONITOR_ONLY,
            )
        ]

    return RecommendationRequest.model_validate(payload)


def _fallback_ingredients(goals: list[RecommendationGoal]) -> list[str]:
    ingredients: list[str] = []
    for goal in goals:
        ingredients.extend(GOAL_FALLBACK_INGREDIENTS.get(goal, ()))
    return list(dict.fromkeys(ingredients))


def _default_symptom_from_goals(goals: list[RecommendationGoal]) -> str:
    for goal in goals:
        if goal in DEFAULT_SYMPTOM_BY_GOAL:
            return DEFAULT_SYMPTOM_BY_GOAL[goal]
    return "frequent_fatigue"


def _sleep_adjustment(
    current_sleep_hours: float | None,
    aggregate_z: float,
    trajectory_mode: str,
) -> float | None:
    if current_sleep_hours is None:
        return None
    delta = 0.0
    if trajectory_mode == "stable_continue":
        delta = 0.25
    elif trajectory_mode == "monitor_plateau":
        delta = 0.1
    elif trajectory_mode == "reoptimize_low_response":
        delta = -0.05 if aggregate_z < -0.35 else 0.1
    elif trajectory_mode == "reduce_side_effect":
        delta = -0.2 if aggregate_z < -0.4 else 0.05
    elif trajectory_mode == "targeted_followup_low_adherence":
        delta = -0.1 if aggregate_z < -0.3 else 0.1
    elif trajectory_mode == "safety_recheck_high_risk":
        delta = -0.15 if aggregate_z < -0.3 else 0.05
    return round(max(4.0, min(9.0, current_sleep_hours + delta)), 1)


def _build_policy_feature_row(record: RichSyntheticCohortRecord) -> dict[str, float]:
    feature_row = {
        "age": float(record.request.user_profile.age),
        "pregnant": float(record.request.user_profile.pregnant),
        "goal_count": float(len(record.request.goals)),
        "symptom_count": float(len(record.request.symptoms)),
        "condition_count": float(len(record.request.conditions)),
        "medication_count": float(len(record.request.medications)),
        "current_supplement_count": float(len(record.request.current_supplements)),
        "max_products": float(record.request.preferences.max_products),
        "sleep_hours": float(record.request.lifestyle.sleep_hours or 0.0),
        "stress_level": float(record.request.lifestyle.stress_level or 0.0),
        "wearable_available": float(record.request.input_availability.wearable),
        "cgm_available": float(record.request.input_availability.cgm),
        "genetic_available": float(record.request.input_availability.genetic),
        "trajectory_step": float(record.trajectory_step),
        "day_index": float(record.day_index),
        "baseline_aggregate_z": float(record.baseline_pro.aggregate_z),
        "follow_up_aggregate_z": float(record.follow_up_pro.aggregate_z),
        "delta_aggregate_z": float(
            round(record.follow_up_pro.aggregate_z - record.baseline_pro.aggregate_z, 3)
        ),
        "expected_effect_proxy": float(record.expected_effect_proxy),
        "adherence_proxy": float(record.adherence_proxy),
        "side_effect_proxy": float(record.side_effect_proxy),
        "regimen_count": float(len(record.regimen)),
        "regimen_reduced_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "reduced")
        ),
        "regimen_stopped_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "stopped")
        ),
        "risk_tier_low": float(record.labels.risk_tier == "low"),
        "risk_tier_moderate": float(record.labels.risk_tier == "moderate"),
        "risk_tier_high": float(record.labels.risk_tier == "high"),
        "safety_status_ok": float(record.labels.safety_status == RecommendationStatus.OK),
        "safety_status_needs_review": float(
            record.labels.safety_status == RecommendationStatus.NEEDS_REVIEW
        ),
        "safety_status_blocked": float(record.labels.safety_status == RecommendationStatus.BLOCKED),
    }
    for goal in RecommendationGoal:
        feature_row[f"goal::{goal.value}"] = float(goal in record.request.goals)
        feature_row[f"baseline::{goal.value}"] = float(
            record.baseline_pro.domain_z.get(goal.value, 0.0)
        )
        feature_row[f"follow_up::{goal.value}"] = float(
            record.follow_up_pro.domain_z.get(goal.value, 0.0)
        )
        feature_row[f"delta::{goal.value}"] = float(record.delta_z_by_domain.get(goal.value, 0.0))
    return feature_row
