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

COHORT_VERSION = "synthetic_longitudinal_v1"
DEFAULT_SYNTHETIC_SEED = 20260310
DEFAULT_USER_COUNT = 48
FOLLOW_UP_STEPS = (0, 1, 2)


class SyntheticLabels(BaseModel):
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


class SyntheticCohortRecord(BaseModel):
    record_id: str
    user_id: str
    cohort_version: str = COHORT_VERSION
    rng_seed: int
    follow_up_step: int = Field(ge=0, le=2)
    day_index: int = Field(ge=0)
    request: RecommendationRequest
    expected_effect_proxy: float = Field(ge=-1.0, le=1.0)
    adherence_proxy: float = Field(ge=0.0, le=1.0)
    baseline_recommendations: list[str] = Field(default_factory=list)
    labels: SyntheticLabels


class SyntheticCohortSummary(BaseModel):
    cohort_version: str = COHORT_VERSION
    seed: int
    user_count: int
    record_count: int
    step_counts: dict[int, int]
    next_action_counts: dict[str, int]
    safety_status_counts: dict[str, int]
    risk_tier_counts: dict[str, int]
    state_counts: dict[str, int]
    goal_counts: dict[str, int]
    adverse_event_count: int
    average_effect_proxy: float
    average_adherence_proxy: float


class SyntheticStepSignals(BaseModel):
    fallback_effect_proxy: float = Field(ge=-1.0, le=1.0)
    adherence_proxy: float = Field(ge=0.0, le=1.0)
    risk_tier: Literal["low", "moderate", "high"]
    adverse_event: bool
    fallback_closed_loop_state: Literal[
        "baseline_questionnaire_due",
        "safety_review",
        "recommendation_ready",
        "intake_active",
        "followup_due",
        "re_evaluation",
        "adjust_plan",
        "stop_or_escalate",
    ]


@dataclass(frozen=True)
class CohortArchetype:
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
    smoker: bool = False
    alcohol_per_week: int = 0
    stress_level: int = 2
    sleep_hours: float | None = 7.0
    avoid_ingredients: tuple[str, ...] = ()
    current_supplements: tuple[tuple[str, tuple[str, ...]], ...] = ()


ARCHETYPES: tuple[CohortArchetype, ...] = (
    CohortArchetype(
        name="sleep_recovery",
        goals=(RecommendationGoal.SLEEP_SUPPORT,),
        symptoms=("difficulty_falling_asleep",),
        conditions=(),
        medications=(),
        wearable=True,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        stress_level=3,
        sleep_hours=5.6,
    ),
    CohortArchetype(
        name="general_micronutrient",
        goals=(RecommendationGoal.GENERAL_WELLNESS,),
        symptoms=("frequent_fatigue",),
        conditions=(),
        medications=(),
        wearable=True,
        genetic=True,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        stress_level=2,
        sleep_hours=6.9,
    ),
    CohortArchetype(
        name="glucose_cgm",
        goals=(RecommendationGoal.BLOOD_GLUCOSE,),
        symptoms=("post_meal_spike_concern",),
        conditions=(),
        medications=(),
        cgm=True,
        genetic=True,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        stress_level=2,
        sleep_hours=6.8,
    ),
    CohortArchetype(
        name="heart_anticoagulant",
        goals=(RecommendationGoal.HEART_HEALTH,),
        symptoms=(),
        conditions=(),
        medications=(("warfarin", "5mg"),),
        wearable=False,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        stress_level=2,
        sleep_hours=7.1,
    ),
    CohortArchetype(
        name="pregnancy_wellness",
        goals=(RecommendationGoal.GENERAL_WELLNESS, RecommendationGoal.BLOOD_GLUCOSE),
        symptoms=(),
        conditions=("kidney disease",),
        medications=(),
        pregnancy=True,
        wearable=True,
        cgm=True,
        genetic=True,
        activity_level=ActivityLevel.SEDENTARY,
        stress_level=2,
        sleep_hours=7.0,
    ),
    CohortArchetype(
        name="renal_sleep",
        goals=(RecommendationGoal.SLEEP_SUPPORT,),
        symptoms=("difficulty_falling_asleep",),
        conditions=("kidney disease",),
        medications=(),
        wearable=True,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        stress_level=3,
        sleep_hours=None,
    ),
    CohortArchetype(
        name="gut_support",
        goals=(RecommendationGoal.GUT_HEALTH,),
        symptoms=("bloating",),
        conditions=(),
        medications=(),
        genetic=True,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        stress_level=2,
        sleep_hours=7.0,
    ),
    CohortArchetype(
        name="sleep_stress_multigoal",
        goals=(RecommendationGoal.SLEEP_SUPPORT, RecommendationGoal.STRESS_SUPPORT),
        symptoms=(),
        conditions=(),
        medications=(),
        genetic=True,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        stress_level=3,
        sleep_hours=None,
    ),
)


DEFAULT_SYMPTOM_BY_GOAL: dict[RecommendationGoal, str] = {
    RecommendationGoal.SLEEP_SUPPORT: "difficulty_falling_asleep",
    RecommendationGoal.STRESS_SUPPORT: "high_stress",
    RecommendationGoal.IMMUNITY_SUPPORT: "frequent_fatigue",
    RecommendationGoal.ENERGY_SUPPORT: "fatigue",
    RecommendationGoal.GUT_HEALTH: "bloating",
    RecommendationGoal.BONE_JOINT: "low_sun_exposure",
    RecommendationGoal.HEART_HEALTH: "low_activity",
    RecommendationGoal.BLOOD_GLUCOSE: "post_meal_spike_concern",
    RecommendationGoal.GENERAL_WELLNESS: "frequent_fatigue",
}


def generate_synthetic_longitudinal_cohort(
    *,
    seed: int = DEFAULT_SYNTHETIC_SEED,
    user_count: int = DEFAULT_USER_COUNT,
) -> list[SyntheticCohortRecord]:
    records: list[SyntheticCohortRecord] = []
    master_rng = Random(seed)

    for user_index in range(user_count):
        user_seed = master_rng.randint(1, 10_000_000)
        user_rng = Random(user_seed)
        archetype = ARCHETYPES[user_index % len(ARCHETYPES)]
        request = _build_baseline_request(
            user_index=user_index,
            archetype=archetype,
            rng=user_rng,
        )

        for step in FOLLOW_UP_STEPS:
            if step > 0:
                previous_response = recommend(request)
                request = _advance_request_for_step(
                    request=request,
                    response=previous_response,
                    step=step,
                )
            response = recommend(request)
            expected_effect_proxy = _compute_effect_proxy(
                request=request,
                step=step,
                response=response,
            )
            adherence_proxy = _compute_adherence_proxy(
                request=request,
                step=step,
                response=response,
            )
            risk_tier = _risk_tier(request=request, response=response)
            adverse_event = _adverse_event_label(
                request=request,
                step=step,
                response=response,
                expected_effect_proxy=expected_effect_proxy,
                risk_tier=risk_tier,
            )
            closed_loop_state = _closed_loop_state(
                step=step,
                response=response,
                expected_effect_proxy=expected_effect_proxy,
                adverse_event=adverse_event,
            )
            records.append(
                SyntheticCohortRecord(
                    record_id=f"syn-{user_index:03d}-step-{step}",
                    user_id=f"syn-user-{user_index:03d}",
                    rng_seed=user_seed,
                    follow_up_step=step,
                    day_index=step * 14,
                    request=request,
                    expected_effect_proxy=expected_effect_proxy,
                    adherence_proxy=adherence_proxy,
                    baseline_recommendations=[
                        item.ingredient_key for item in response.recommendations
                    ],
                    labels=SyntheticLabels(
                        next_action=response.next_action,
                        reason_code=response.next_action_rationale.reason_code,
                        safety_status=response.status,
                        risk_tier=risk_tier,
                        adverse_event=adverse_event,
                        closed_loop_state=closed_loop_state,
                    ),
                )
            )

    return records


def advance_synthetic_request_for_step(
    *,
    request: RecommendationRequest,
    response,
    step: int,
) -> RecommendationRequest:
    return _advance_request_for_step(request=request, response=response, step=step)


def compute_synthetic_effect_proxy(
    *,
    request: RecommendationRequest,
    step: int,
    response,
) -> float:
    return _compute_effect_proxy(request=request, step=step, response=response)


def compute_synthetic_adherence_proxy(
    *,
    request: RecommendationRequest,
    step: int,
    response,
) -> float:
    return _compute_adherence_proxy(request=request, step=step, response=response)


def compute_synthetic_risk_tier(
    *,
    request: RecommendationRequest,
    response,
) -> Literal["low", "moderate", "high"]:
    return _risk_tier(request=request, response=response)


def compute_synthetic_adverse_event(
    *,
    request: RecommendationRequest,
    step: int,
    response,
    expected_effect_proxy: float,
    risk_tier: Literal["low", "moderate", "high"],
) -> bool:
    return _adverse_event_label(
        request=request,
        step=step,
        response=response,
        expected_effect_proxy=expected_effect_proxy,
        risk_tier=risk_tier,
    )


def build_synthetic_step_signals(
    *,
    request: RecommendationRequest,
    step: int,
    response,
) -> SyntheticStepSignals:
    fallback_effect_proxy = _compute_effect_proxy(
        request=request,
        step=step,
        response=response,
    )
    adherence_proxy = _compute_adherence_proxy(
        request=request,
        step=step,
        response=response,
    )
    risk_tier = _risk_tier(request=request, response=response)
    adverse_event = _adverse_event_label(
        request=request,
        step=step,
        response=response,
        expected_effect_proxy=fallback_effect_proxy,
        risk_tier=risk_tier,
    )
    fallback_closed_loop_state = _closed_loop_state(
        step=step,
        response=response,
        expected_effect_proxy=fallback_effect_proxy,
        adverse_event=adverse_event,
    )
    return SyntheticStepSignals(
        fallback_effect_proxy=fallback_effect_proxy,
        adherence_proxy=adherence_proxy,
        risk_tier=risk_tier,
        adverse_event=adverse_event,
        fallback_closed_loop_state=fallback_closed_loop_state,
    )


def validate_synthetic_cohort(records: list[SyntheticCohortRecord]) -> list[str]:
    issues: list[str] = []
    if not records:
        return ["synthetic cohort is empty"]

    seen_ids: set[str] = set()
    user_steps: defaultdict[str, list[int]] = defaultdict(list)

    for record in records:
        if record.record_id in seen_ids:
            issues.append(f"duplicate record_id: {record.record_id}")
        seen_ids.add(record.record_id)
        user_steps[record.user_id].append(record.follow_up_step)

        if record.follow_up_step == 0 and record.labels.adverse_event:
            issues.append(f"baseline step cannot mark adverse event: {record.record_id}")
        if (
            record.labels.closed_loop_state == "stop_or_escalate"
            and not record.labels.adverse_event
        ):
            issues.append(
                f"stop_or_escalate requires adverse_event label: {record.record_id}"
            )
        if (
            record.labels.next_action == NextAction.START_PLAN
            and not record.baseline_recommendations
            and "current_regimen_coverage" not in record.labels.reason_code
        ):
            issues.append(f"start_plan record has no recommendations: {record.record_id}")

    for user_id, steps in user_steps.items():
        if sorted(steps) != list(FOLLOW_UP_STEPS):
            issues.append(f"user {user_id} does not cover steps {FOLLOW_UP_STEPS}")

    return issues


def summarize_synthetic_cohort(
    records: list[SyntheticCohortRecord],
    *,
    seed: int,
) -> SyntheticCohortSummary:
    step_counts = Counter(record.follow_up_step for record in records)
    next_action_counts = Counter(record.labels.next_action.value for record in records)
    safety_status_counts = Counter(record.labels.safety_status.value for record in records)
    risk_tier_counts = Counter(record.labels.risk_tier for record in records)
    state_counts = Counter(record.labels.closed_loop_state for record in records)
    goal_counts = Counter(
        goal.value
        for record in records
        for goal in record.request.goals
    )
    adverse_event_count = sum(1 for record in records if record.labels.adverse_event)
    average_effect_proxy = round(
        sum(record.expected_effect_proxy for record in records) / len(records),
        4,
    )
    average_adherence_proxy = round(
        sum(record.adherence_proxy for record in records) / len(records),
        4,
    )

    return SyntheticCohortSummary(
        seed=seed,
        user_count=len({record.user_id for record in records}),
        record_count=len(records),
        step_counts=dict(sorted(step_counts.items())),
        next_action_counts=dict(sorted(next_action_counts.items())),
        safety_status_counts=dict(sorted(safety_status_counts.items())),
        risk_tier_counts=dict(sorted(risk_tier_counts.items())),
        state_counts=dict(sorted(state_counts.items())),
        goal_counts=dict(sorted(goal_counts.items())),
        adverse_event_count=adverse_event_count,
        average_effect_proxy=average_effect_proxy,
        average_adherence_proxy=average_adherence_proxy,
    )


def _build_baseline_request(
    *,
    user_index: int,
    archetype: CohortArchetype,
    rng: Random,
) -> RecommendationRequest:
    age = 25 + ((user_index * 7) % 43)
    biological_sex = BiologicalSex.FEMALE if user_index % 2 == 0 else BiologicalSex.MALE
    if archetype.pregnancy:
        biological_sex = BiologicalSex.FEMALE

    budget_cycle = (BudgetLevel.LOW, BudgetLevel.MEDIUM, BudgetLevel.HIGH)
    budget_level = budget_cycle[user_index % len(budget_cycle)]
    max_products = 1 if budget_level == BudgetLevel.LOW else archetype.max_products

    payload = {
        "request_id": f"syn-req-{user_index:03d}-step-0",
        "user_profile": {
            "age": age,
            "biological_sex": biological_sex.value,
            "pregnant": archetype.pregnancy,
        },
        "goals": [goal.value for goal in archetype.goals],
        "symptoms": list(archetype.symptoms),
        "conditions": list(archetype.conditions),
        "medications": [
            {"name": name, "dose": dose} for name, dose in archetype.medications
        ],
        "current_supplements": [
            {"name": name, "ingredients": list(ingredients)}
            for name, ingredients in archetype.current_supplements
        ],
        "lifestyle": {
            "sleep_hours": archetype.sleep_hours,
            "stress_level": archetype.stress_level,
            "activity_level": archetype.activity_level.value,
            "smoker": archetype.smoker,
            "alcohol_per_week": archetype.alcohol_per_week,
        },
        "input_availability": {
            "survey": True,
            "nhis": bool(user_index % 3),
            "wearable": archetype.wearable,
            "cgm": archetype.cgm,
            "genetic": archetype.genetic,
        },
        "preferences": {
            "budget_level": budget_level.value,
            "max_products": max_products,
            "avoid_ingredients": list(archetype.avoid_ingredients),
        },
    }

    if rng.random() < 0.2:
        payload["preferences"]["avoid_ingredients"] = payload["preferences"][
            "avoid_ingredients"
        ][:1]

    return RecommendationRequest.model_validate(payload)


def _advance_request_for_step(
    *,
    request: RecommendationRequest,
    response,
    step: int,
) -> RecommendationRequest:
    payload = request.model_dump(mode="json")
    payload["request_id"] = (
        f"{payload['request_id'].split('-step-')[0]}-step-{step}"
        if "-step-" in payload["request_id"]
        else f"{payload['request_id']}-step-{step}"
    )

    if response.next_action == NextAction.START_PLAN and response.recommendations:
        payload["current_supplements"] = [
            {
                "name": item.display_name,
                "ingredients": [item.ingredient_key],
            }
            for item in response.recommendations[: request.preferences.max_products]
        ]
        if payload["lifestyle"]["sleep_hours"] is not None:
            payload["lifestyle"]["sleep_hours"] = min(
                8.5,
                round(payload["lifestyle"]["sleep_hours"] + 0.3, 1),
            )
        if payload["lifestyle"]["stress_level"] is not None:
            payload["lifestyle"]["stress_level"] = max(
                1,
                payload["lifestyle"]["stress_level"] - 1,
            )
        if payload["symptoms"]:
            payload["symptoms"] = payload["symptoms"][1:]
    else:
        if not payload["symptoms"]:
            payload["symptoms"] = [_default_symptom_from_goals(request.goals)]
        elif step == 2 and not payload["current_supplements"] and response.recommendations:
            lead = response.recommendations[0]
            payload["current_supplements"] = [
                {"name": lead.display_name, "ingredients": [lead.ingredient_key]}
            ]

    return RecommendationRequest.model_validate(payload)


def _default_symptom_from_goals(goals: list[RecommendationGoal]) -> str:
    for goal in goals:
        if goal in DEFAULT_SYMPTOM_BY_GOAL:
            return DEFAULT_SYMPTOM_BY_GOAL[goal]
    return "frequent_fatigue"


def _compute_effect_proxy(*, request: RecommendationRequest, step: int, response) -> float:
    goal_bonus = 0.08 * len(request.goals)
    symptom_penalty = 0.07 * len(request.symptoms)
    condition_penalty = 0.12 * len(request.conditions)
    medication_penalty = 0.1 * len(request.medications)
    pregnancy_penalty = 0.18 if request.user_profile.pregnant else 0.0
    modality_bonus = 0.03 * sum(
        (
            request.input_availability.wearable,
            request.input_availability.cgm,
            request.input_availability.genetic,
        )
    )
    start_plan_bonus = 0.18 if response.next_action == NextAction.START_PLAN else -0.05
    safety_penalty = {
        RecommendationStatus.OK: 0.0,
        RecommendationStatus.NEEDS_REVIEW: 0.18,
        RecommendationStatus.BLOCKED: 0.3,
    }[response.status]
    follow_up_bonus = 0.06 * step
    sleep_bonus = 0.0
    if request.lifestyle.sleep_hours is not None and request.lifestyle.sleep_hours < 6.5:
        sleep_bonus -= 0.06
    if request.lifestyle.stress_level is not None and request.lifestyle.stress_level >= 4:
        sleep_bonus -= 0.05

    proxy = (
        goal_bonus
        + modality_bonus
        + start_plan_bonus
        + follow_up_bonus
        + sleep_bonus
        - symptom_penalty
        - condition_penalty
        - medication_penalty
        - pregnancy_penalty
        - safety_penalty
    )
    return round(max(-1.0, min(1.0, proxy)), 3)


def _compute_adherence_proxy(*, request: RecommendationRequest, step: int, response) -> float:
    base = 0.55
    if response.next_action == NextAction.START_PLAN:
        base += 0.18
    if request.preferences.budget_level == BudgetLevel.LOW:
        base += 0.05
    if request.preferences.max_products > 2:
        base -= 0.08
    if request.medications or request.conditions or request.user_profile.pregnant:
        base -= 0.1
    if step > 0 and request.current_supplements:
        base += 0.08
    return round(max(0.0, min(1.0, base)), 3)


def _risk_tier(*, request: RecommendationRequest, response) -> Literal["low", "moderate", "high"]:
    if response.status in {RecommendationStatus.BLOCKED, RecommendationStatus.NEEDS_REVIEW}:
        return "high"
    if request.user_profile.pregnant or request.conditions or request.medications:
        return "high"
    if response.safety_summary.rule_refs:
        return "moderate"
    return "low"


def _adverse_event_label(
    *,
    request: RecommendationRequest,
    step: int,
    response,
    expected_effect_proxy: float,
    risk_tier: Literal["low", "moderate", "high"],
) -> bool:
    if step == 0:
        return False
    if risk_tier == "high" and response.next_action != NextAction.START_PLAN:
        return True
    if expected_effect_proxy < -0.05 and (
        request.user_profile.pregnant or request.conditions or request.medications
    ):
        return True
    return False


def _closed_loop_state(
    *,
    step: int,
    response,
    expected_effect_proxy: float,
    adverse_event: bool,
) -> str:
    if step == 0:
        if response.next_action == NextAction.START_PLAN:
            return "recommendation_ready"
        if response.next_action == NextAction.COLLECT_MORE_INPUT:
            return "baseline_questionnaire_due"
        return "safety_review"

    if adverse_event:
        return "stop_or_escalate"
    if response.next_action == NextAction.TRIGGER_SAFETY_RECHECK:
        return "safety_review"
    if response.next_action == NextAction.COLLECT_MORE_INPUT:
        return "re_evaluation"
    if step == 1:
        return "intake_active"
    if expected_effect_proxy >= 0.1:
        return "followup_due"
    return "adjust_plan"
