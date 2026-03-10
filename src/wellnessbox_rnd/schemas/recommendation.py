from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class BiologicalSex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    UNDISCLOSED = "undisclosed"


class RecommendationGoal(StrEnum):
    STRESS_SUPPORT = "stress_support"
    SLEEP_SUPPORT = "sleep_support"
    IMMUNITY_SUPPORT = "immunity_support"
    ENERGY_SUPPORT = "energy_support"
    GUT_HEALTH = "gut_health"
    BONE_JOINT = "bone_joint"
    HEART_HEALTH = "heart_health"
    BLOOD_GLUCOSE = "blood_glucose"
    GENERAL_WELLNESS = "general_wellness"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"


class BudgetLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationStatus(StrEnum):
    OK = "ok"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class NextAction(StrEnum):
    BLOCKED = "blocked"
    ASK_TARGETED_FOLLOWUP = "ask_targeted_followup"
    TRIGGER_SAFETY_RECHECK = "trigger_safety_recheck"
    START_PLAN = "start_plan"
    CONTINUE_PLAN = "continue_plan"
    RE_OPTIMIZE = "re_optimize"
    REDUCE_OR_STOP = "reduce_or_stop"
    MONITOR_ONLY = "monitor_only"
    COLLECT_MORE_INPUT = "collect_more_input"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class MissingInfoImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConfidenceBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserProfile(BaseModel):
    age: int = Field(ge=18, le=120)
    biological_sex: BiologicalSex
    pregnant: bool = False


class MedicationInput(BaseModel):
    name: str = Field(min_length=1)
    dose: str | None = None


class SupplementInput(BaseModel):
    name: str = Field(min_length=1)
    ingredients: list[str] = Field(default_factory=list)


class LifestyleInput(BaseModel):
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    activity_level: ActivityLevel = ActivityLevel.SEDENTARY
    smoker: bool = False
    alcohol_per_week: int = Field(default=0, ge=0, le=50)


class InputAvailability(BaseModel):
    survey: bool = True
    nhis: bool = False
    wearable: bool = False
    cgm: bool = False
    genetic: bool = False


class RecommendationPreferences(BaseModel):
    budget_level: BudgetLevel = BudgetLevel.MEDIUM
    max_products: int = Field(default=2, ge=1, le=5)
    avoid_ingredients: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    user_profile: UserProfile
    goals: list[RecommendationGoal] = Field(min_length=1)
    symptoms: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[MedicationInput] = Field(default_factory=list)
    current_supplements: list[SupplementInput] = Field(default_factory=list)
    lifestyle: LifestyleInput = Field(default_factory=LifestyleInput)
    input_availability: InputAvailability = Field(default_factory=InputAvailability)
    preferences: RecommendationPreferences = Field(default_factory=RecommendationPreferences)


class RuleReference(BaseModel):
    rule_id: str
    message: str
    severity: Severity
    source: str = "master_context_v1"


class SafetySummary(BaseModel):
    status: RecommendationStatus
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    rule_refs: list[RuleReference] = Field(default_factory=list)


class MissingInformationItem(BaseModel):
    code: str
    question: str
    reason: str
    importance: MissingInfoImportance


class NextActionRationale(BaseModel):
    reason_code: str
    summary: str
    supporting_codes: list[str] = Field(default_factory=list)


class SafetyEvidenceItem(BaseModel):
    evidence_type: Literal["rule", "excluded_ingredient", "user_preference"]
    code: str
    summary: str


class LimitationItem(BaseModel):
    code: str
    summary: str


class CandidateScoreBreakdown(BaseModel):
    goal_alignment: float
    symptom_alignment: float
    lifestyle_alignment: float
    evidence_readiness: float
    budget_adjustment: float
    safety_adjustment: float
    conservative_adjustment: float
    learned_effect_bonus: float = 0.0
    total: float


class RecommendationCandidate(BaseModel):
    ingredient_key: str
    display_name: str
    rationale: str
    expected_support_goals: list[RecommendationGoal]
    rule_refs: list[str] = Field(default_factory=list)
    score_breakdown: CandidateScoreBreakdown
    follow_up_focus: str


class DecisionSummary(BaseModel):
    headline: str
    summary: str
    confidence_band: ConfidenceBand


class EngineMetadata(BaseModel):
    engine_version: str = "0.1.0"
    mode: str = "mock_deterministic_v0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecommendationResponse(BaseModel):
    request_id: str
    decision_id: str
    status: RecommendationStatus
    decision_summary: DecisionSummary
    normalized_focus_goals: list[RecommendationGoal]
    safety_summary: SafetySummary
    safety_flags: list[str] = Field(default_factory=list)
    safety_evidence: list[SafetyEvidenceItem] = Field(default_factory=list)
    recommendations: list[RecommendationCandidate]
    next_action: NextAction
    next_action_rationale: NextActionRationale
    follow_up_window_days: int = Field(ge=1, le=90)
    follow_up_questions: list[str] = Field(default_factory=list)
    missing_information: list[MissingInformationItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    limitation_details: list[LimitationItem] = Field(default_factory=list)
    metadata: EngineMetadata
