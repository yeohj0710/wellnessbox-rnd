from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from unicodedata import normalize as normalize_unicode
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

StructuredHealthCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]
LegacyDoseText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]
LaboratoryUnit = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
]

_LABORATORY_UNIT_ALIASES = {
    "g/dl": "g/dL",
    "iu/l": "IU/L",
    "meq/l": "mEq/L",
    "mg/dl": "mg/dL",
    "miu/l": "mIU/L",
    "mmol/l": "mmol/L",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "u/l": "U/L",
    "umol/l": "umol/L",
    "ug/dl": "ug/dL",
    "ug/l": "ug/L",
    "ug/ml": "ug/mL",
}
_SUPPORTED_LABORATORY_UNITS = frozenset(
    {"%", *_LABORATORY_UNIT_ALIASES.values()}
)


def _reject_boolean_numeric(value: object) -> object:
    if isinstance(value, bool):
        raise ValueError("value must be numeric, not boolean")
    return value


class BiologicalSex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    UNDISCLOSED = "undisclosed"


class ConditionStatus(StrEnum):
    ACTIVE = "active"
    SUSPECTED = "suspected"
    HISTORY = "history"
    RESOLVED = "resolved"


class SymptomSeverity(StrEnum):
    UNSPECIFIED = "unspecified"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class RiskSignalSource(StrEnum):
    SELF_REPORT = "self_report"
    CLINICIAN = "clinician"
    DEVICE = "device"
    IMPORTED_RECORD = "imported_record"
    LEGACY = "legacy"


class DoseUnit(StrEnum):
    GRAM = "g"
    MILLIGRAM = "mg"
    MICROGRAM = "mcg"
    NANOGRAM = "ng"
    MILLILITER = "mL"
    INTERNATIONAL_UNIT = "IU"
    TABLET = "tablet"
    CAPSULE = "capsule"


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


class DataSource(StrEnum):
    SURVEY = "survey"
    NHIS = "nhis"
    WEARABLE = "wearable"
    CGM = "cgm"
    GENETIC = "genetic"


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


class _StrictRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserProfile(_StrictRequestInput):
    age: int = Field(ge=18, le=120)
    biological_sex: BiologicalSex
    pregnant: bool = False
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)


class _StrictHealthInput(_StrictRequestInput):
    pass


class ConditionInput(_StrictHealthInput):
    code: StructuredHealthCode
    status: ConditionStatus = ConditionStatus.ACTIVE
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class SymptomInput(_StrictHealthInput):
    code: StructuredHealthCode
    severity: SymptomSeverity
    duration_days: int | None = Field(default=None, ge=0, le=36500)


class UrgentRiskSignal(_StrictHealthInput):
    code: StructuredHealthCode
    present: bool = True
    source: RiskSignalSource = RiskSignalSource.SELF_REPORT


class DoseAmount(_StrictHealthInput):
    amount: float = Field(gt=0, le=1_000_000)
    unit: DoseUnit


class MedicationClassification(_StrictHealthInput):
    code: StructuredHealthCode
    system: StructuredHealthCode = "local"
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class MedicationInput(_StrictHealthInput):
    name: StructuredHealthCode
    classification: MedicationClassification | None = None
    dose: LegacyDoseText | DoseAmount | None = None


class SupplementIngredientInput(_StrictHealthInput):
    name: StructuredHealthCode
    daily_dose: DoseAmount | None = None


class SupplementInput(_StrictHealthInput):
    name: StructuredHealthCode
    dose: LegacyDoseText | None = None
    daily_dose: DoseAmount | None = None
    ingredients: list[LegacyDoseText | SupplementIngredientInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_ambiguous_product_dose(self) -> "SupplementInput":
        if self.dose is not None and self.daily_dose is not None:
            raise ValueError("dose and daily_dose cannot both be provided")
        return self


class DietaryPatternInput(_StrictHealthInput):
    code: StructuredHealthCode
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class LaboratoryReferenceRange(_StrictHealthInput):
    low: float | None = Field(default=None, allow_inf_nan=False)
    high: float | None = Field(default=None, allow_inf_nan=False)

    @field_validator("low", "high", mode="before")
    @classmethod
    def reject_boolean_bounds(cls, value: object) -> object:
        return _reject_boolean_numeric(value)

    @model_validator(mode="after")
    def validate_bounds(self) -> "LaboratoryReferenceRange":
        if self.low is None and self.high is None:
            raise ValueError("reference_range requires low or high")
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("reference_range low cannot exceed high")
        return self


class LaboratoryObservationInput(_StrictHealthInput):
    code: StructuredHealthCode
    value: float = Field(allow_inf_nan=False)
    unit: LaboratoryUnit
    reference_range: LaboratoryReferenceRange
    measured_at: datetime
    source: DataSource = DataSource.SURVEY

    @field_validator("value", mode="before")
    @classmethod
    def reject_boolean_value(cls, value: object) -> object:
        return _reject_boolean_numeric(value)

    @field_validator("unit")
    @classmethod
    def require_supported_unit(cls, value: str) -> str:
        if normalize_laboratory_unit(value) not in _SUPPORTED_LABORATORY_UNITS:
            raise ValueError("unsupported laboratory unit")
        return value

    @field_validator("measured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must include a timezone")
        return value.astimezone(UTC)


class LaboratoryRangeStatus(StrEnum):
    LOW = "low"
    WITHIN_RANGE = "within_range"
    HIGH = "high"


class LifestyleInput(_StrictRequestInput):
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    activity_level: ActivityLevel = ActivityLevel.SEDENTARY
    exercise_minutes_per_week: float | None = Field(default=None, ge=0, le=10_080)
    smoker: bool = False
    alcohol_per_week: int = Field(default=0, ge=0, le=50)
    caffeine_mg_per_day: float | None = Field(default=None, ge=0, le=5_000)

    @field_validator(
        "exercise_minutes_per_week",
        "caffeine_mg_per_day",
        mode="before",
    )
    @classmethod
    def reject_boolean_numeric_fields(cls, value: object) -> object:
        return _reject_boolean_numeric(value)


class InputAvailability(_StrictRequestInput):
    survey: bool = True
    nhis: bool = False
    wearable: bool = False
    cgm: bool = False
    genetic: bool = False


class DataSourceConsent(_StrictHealthInput):
    use_for_recommendation: StrictBool = False
    allow_persistent_storage: StrictBool = False


class DataSourceConsents(_StrictHealthInput):
    survey: DataSourceConsent = Field(default_factory=DataSourceConsent)
    nhis: DataSourceConsent = Field(default_factory=DataSourceConsent)
    wearable: DataSourceConsent = Field(default_factory=DataSourceConsent)
    cgm: DataSourceConsent = Field(default_factory=DataSourceConsent)
    genetic: DataSourceConsent = Field(default_factory=DataSourceConsent)


def _legacy_data_source_consents() -> DataSourceConsents:
    return DataSourceConsents(
        **{
            source.value: DataSourceConsent(use_for_recommendation=True)
            for source in DataSource
        }
    )


class RecommendationPreferences(_StrictRequestInput):
    budget_level: BudgetLevel = BudgetLevel.MEDIUM
    max_products: int = Field(default=2, ge=1, le=5)
    avoid_ingredients: list[str] = Field(default_factory=list)


def _normalize_contract_text(value: str) -> str:
    normalized = normalize_unicode("NFKC", value)
    return " ".join(normalized.strip().casefold().split())


def _dose_signature(
    value: LegacyDoseText | DoseAmount | None,
) -> tuple[object, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return ("legacy_text", _normalize_contract_text(value))
    return ("structured", value.amount, value.unit.value)


def _medication_signature(value: MedicationInput) -> tuple[object, ...]:
    classification_signature = None
    if value.classification is not None:
        classification_signature = (
            _normalize_contract_text(value.classification.system),
            _normalize_contract_text(value.classification.code),
        )
    return (classification_signature, _dose_signature(value.dose))


def _supplement_ingredient_signatures(
    value: SupplementInput,
) -> tuple[tuple[str, tuple[object, ...] | None], ...]:
    from wellnessbox_rnd.domain.catalog import canonicalize_exact_catalog_term

    signatures_by_name: dict[str, tuple[object, ...] | None] = {}
    entries: list[tuple[str, tuple[object, ...] | None]] = []
    for ingredient in value.ingredients:
        if isinstance(ingredient, str):
            normalized_name = _normalize_contract_text(ingredient)
            signature = None
        else:
            normalized_name = _normalize_contract_text(ingredient.name)
            signature = _dose_signature(ingredient.daily_dose)
        name = canonicalize_exact_catalog_term(normalized_name) or normalized_name
        if name in signatures_by_name and signatures_by_name[name] != signature:
            raise ValueError(
                "conflicting duplicate supplement ingredients for the same normalized name"
            )
        signatures_by_name[name] = signature
        entries.append((name, signature))
    return tuple(sorted(entries))


def _supplement_signature(value: SupplementInput) -> tuple[object, ...]:
    return (
        _dose_signature(value.dose),
        _dose_signature(value.daily_dose),
        _supplement_ingredient_signatures(value),
    )


class RecommendationRequest(_StrictRequestInput):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    user_profile: UserProfile
    goals: list[RecommendationGoal] = Field(min_length=1)
    symptoms: list[str | SymptomInput] = Field(default_factory=list)
    conditions: list[str | ConditionInput] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    risk_flags: list[str | UrgentRiskSignal] = Field(default_factory=list)
    medications: list[MedicationInput] = Field(default_factory=list)
    current_supplements: list[SupplementInput] = Field(default_factory=list)
    dietary_patterns: list[str | DietaryPatternInput] = Field(default_factory=list)
    laboratory_observations: list[LaboratoryObservationInput] = Field(
        default_factory=list
    )
    lifestyle: LifestyleInput = Field(default_factory=LifestyleInput)
    input_availability: InputAvailability = Field(default_factory=InputAvailability)
    data_source_consents: DataSourceConsents = Field(
        default_factory=_legacy_data_source_consents
    )
    preferences: RecommendationPreferences = Field(default_factory=RecommendationPreferences)

    @model_validator(mode="after")
    def require_survey_recommendation_consent(self) -> "RecommendationRequest":
        if not self.data_source_consents.survey.use_for_recommendation:
            raise ValueError(
                "survey use_for_recommendation consent is required for a recommendation request"
            )
        return self

    @model_validator(mode="after")
    def reject_conflicting_duplicate_medications(self) -> "RecommendationRequest":
        signatures_by_name: dict[str, tuple[object, ...]] = {}
        for medication in self.medications:
            name = _normalize_contract_text(medication.name)
            signature = _medication_signature(medication)
            if name in signatures_by_name and signatures_by_name[name] != signature:
                raise ValueError(
                    "conflicting duplicate medications for the same normalized name"
                )
            signatures_by_name[name] = signature
        return self

    @model_validator(mode="after")
    def reject_conflicting_duplicate_supplements(self) -> "RecommendationRequest":
        signatures_by_name: dict[str, tuple[object, ...]] = {}
        for supplement in self.current_supplements:
            name = _normalize_contract_text(supplement.name)
            signature = _supplement_signature(supplement)
            if name in signatures_by_name and signatures_by_name[name] != signature:
                raise ValueError(
                    "conflicting duplicate supplements for the same normalized name"
                )
            signatures_by_name[name] = signature
        return self

    @model_validator(mode="after")
    def reject_conflicting_laboratory_observations(self) -> "RecommendationRequest":
        signatures_by_identity: dict[tuple[str, datetime], tuple[object, ...]] = {}
        for observation in self.laboratory_observations:
            if not getattr(self.input_availability, observation.source.value) or not getattr(
                self.data_source_consents,
                observation.source.value,
            ).use_for_recommendation:
                continue
            identity = (
                normalize_laboratory_observation_code(observation),
                observation.measured_at,
            )
            signature = (
                observation.value,
                normalize_laboratory_unit(observation.unit),
                observation.reference_range.low,
                observation.reference_range.high,
            )
            existing = signatures_by_identity.get(identity)
            if existing is not None and existing != signature:
                raise ValueError(
                    "conflicting laboratory observations for the same code and measured_at"
                )
            signatures_by_identity[identity] = signature
        return self


def normalize_health_input_code(
    value: str | ConditionInput | SymptomInput | UrgentRiskSignal,
) -> str:
    raw_value = value if isinstance(value, str) else value.code
    return " ".join(raw_value.strip().lower().split())


def normalize_medication_classification_code(value: MedicationClassification) -> str:
    return " ".join(value.code.strip().lower().split())


def normalize_medication_classification_key(value: MedicationClassification) -> str:
    system = " ".join(value.system.strip().lower().split())
    code = normalize_medication_classification_code(value)
    return f"{system}::{code}"


def normalize_dietary_pattern_code(value: str | DietaryPatternInput) -> str:
    raw_value = value if isinstance(value, str) else value.code
    return " ".join(raw_value.strip().lower().split())


def normalize_laboratory_observation_code(value: LaboratoryObservationInput) -> str:
    return " ".join(value.code.strip().lower().split())


def normalize_laboratory_unit(value: str) -> str:
    compact = "".join(normalize_unicode("NFKC", value).strip().split())
    normalized_key = compact.casefold().replace("μ", "u").replace("µ", "u")
    if normalized_key.startswith("mcg"):
        normalized_key = f"ug{normalized_key[3:]}"
    return _LABORATORY_UNIT_ALIASES.get(normalized_key, compact)


def classify_laboratory_observation(
    value: LaboratoryObservationInput,
) -> LaboratoryRangeStatus:
    if value.reference_range.low is not None and value.value < value.reference_range.low:
        return LaboratoryRangeStatus.LOW
    if value.reference_range.high is not None and value.value > value.reference_range.high:
        return LaboratoryRangeStatus.HIGH
    return LaboratoryRangeStatus.WITHIN_RANGE


def normalize_supplement_ingredient_name(
    value: str | SupplementIngredientInput,
) -> str:
    raw_value = value if isinstance(value, str) else value.name
    return " ".join(raw_value.strip().lower().split())


def is_current_condition_input(value: str | ConditionInput) -> bool:
    return not isinstance(value, ConditionInput) or value.status != ConditionStatus.RESOLVED


def count_current_condition_inputs(values: list[str | ConditionInput]) -> int:
    return sum(is_current_condition_input(value) for value in values)


def has_current_condition_inputs(values: list[str | ConditionInput]) -> bool:
    return any(is_current_condition_input(value) for value in values)


class CitationReference(BaseModel):
    reference_id: str
    claim_id: str | None = None
    source_title: str
    source_type: str
    page_or_section: str
    excerpt: str
    reference_uri: str


class RuleReference(BaseModel):
    rule_id: str
    message: str
    severity: Severity
    source: str = "master_context_v1"
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    citations: list[CitationReference] = Field(default_factory=list)


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
    reference_ids: list[str] = Field(default_factory=list)


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
