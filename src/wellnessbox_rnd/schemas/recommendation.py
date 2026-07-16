from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from unicodedata import normalize as normalize_unicode
from uuid import uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
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
WellnessBoxSourceName = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=1,
        max_length=200,
        pattern=r"(?s).*\S.*",
    ),
]
WellnessBoxSourceText = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"(?s).*\S.*",
    ),
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


class WellnessBoxChatUserProfileV1(_StrictRequestInput):
    """Versioned trace of the service-owned chat profile contract.

    Camel-case field names intentionally match ``wellnessbox/types/chat.ts`` so
    integration code can prove that no source property disappeared in transit.
    """

    name: WellnessBoxSourceName | None = None
    age: int | None = Field(default=None, ge=18, le=120)
    sex: Literal["male", "female", "other"] | None = None
    heightCm: StrictInt | StrictFloat | None = Field(default=None, gt=0, le=300)
    weightKg: StrictInt | StrictFloat | None = Field(default=None, gt=0, le=500)
    conditions: list[WellnessBoxSourceText] | None = Field(
        default=None, max_length=100
    )
    medications: list[WellnessBoxSourceText] | None = Field(
        default=None, max_length=100
    )
    allergies: list[WellnessBoxSourceText] | None = Field(
        default=None, max_length=100
    )
    goals: list[WellnessBoxSourceText] | None = Field(default=None, max_length=20)
    dietaryRestrictions: list[WellnessBoxSourceText] | None = Field(
        default=None, max_length=100
    )
    pregnantOrBreastfeeding: StrictBool | None = None
    caffeineSensitivity: StrictBool | None = None

    @field_validator("age", mode="before")
    @classmethod
    def require_numeric_integer_age(cls, value: object) -> object:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("age must be a numeric integer")
        return value


class SourceProfileInput(_StrictRequestInput):
    schema_version: Literal["wellnessbox.chat.UserProfile.v1"]
    subject_id: str | None = Field(
        default=None,
        pattern=r"^usr_[a-f0-9]{16,64}$",
    )
    profile: WellnessBoxChatUserProfileV1


class UserProfile(_StrictRequestInput):
    age: int = Field(ge=18, le=120)
    biological_sex: BiologicalSex
    pregnant: bool = False
    lactating: bool = Field(default=False, exclude_if=lambda value: value is False)
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


class NormalizedSensorGeneticSnapshot(_StrictHealthInput):
    wearable_available: StrictBool = False
    cgm_available: StrictBool = False
    genetic_available: StrictBool = False
    sleep_hours: float | None = Field(
        default=None, ge=0.0, le=24.0, allow_inf_nan=False
    )
    steps: int | None = Field(default=None, ge=0, le=200_000)
    resting_heart_rate: int | None = Field(default=None, ge=20, le=250)
    mean_glucose_mg_dl: float | None = Field(
        default=None, ge=20.0, le=600.0, allow_inf_nan=False
    )
    time_in_range_pct: float | None = Field(
        default=None, ge=0.0, le=100.0, allow_inf_nan=False
    )
    time_in_range_low_mg_dl: float | None = Field(
        default=None, ge=20.0, le=600.0, allow_inf_nan=False
    )
    time_in_range_high_mg_dl: float | None = Field(
        default=None, ge=20.0, le=600.0, allow_inf_nan=False
    )
    post_meal_spike_concern: StrictBool = False
    genetic_tags: list[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=1,
                max_length=128,
                pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$",
            ),
        ]
    ] = Field(default_factory=list)
    normalization_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_source_availability_for_values(self) -> "NormalizedSensorGeneticSnapshot":
        if not self.wearable_available and any(
            value is not None
            for value in (self.sleep_hours, self.steps, self.resting_heart_rate)
        ):
            raise ValueError("wearable values require wearable_available=true")
        if not self.cgm_available and (
            self.mean_glucose_mg_dl is not None
            or self.time_in_range_pct is not None
            or self.time_in_range_low_mg_dl is not None
            or self.time_in_range_high_mg_dl is not None
            or self.post_meal_spike_concern
        ):
            raise ValueError("CGM values require cgm_available=true")
        range_bounds = (
            self.time_in_range_low_mg_dl,
            self.time_in_range_high_mg_dl,
        )
        if (range_bounds[0] is None) != (range_bounds[1] is None):
            raise ValueError("CGM time-in-range bounds must be supplied together")
        if range_bounds[0] is not None:
            if self.time_in_range_pct is None:
                raise ValueError("CGM time-in-range bounds require time_in_range_pct")
            if range_bounds[0] >= range_bounds[1]:
                raise ValueError("CGM time-in-range lower bound must be below upper bound")
        if not self.genetic_available and self.genetic_tags:
            raise ValueError("genetic tags require genetic_available=true")
        if len(set(self.genetic_tags)) != len(self.genetic_tags):
            raise ValueError("genetic tags must be unique")
        return self


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
    source_profile: SourceProfileInput | None = Field(default=None, exclude=True)
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
    sensor_genetic_snapshot: NormalizedSensorGeneticSnapshot | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
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
    def require_declared_sensor_snapshot_sources(self) -> "RecommendationRequest":
        snapshot = self.sensor_genetic_snapshot
        if snapshot is None:
            return self
        if "data_source_consents" not in self.model_fields_set:
            raise ValueError(
                "sensor_genetic_snapshot requires explicit data_source_consents"
            )
        for source in ("wearable", "cgm", "genetic"):
            if getattr(snapshot, f"{source}_available") and not getattr(
                self.input_availability, source
            ):
                raise ValueError(
                    f"{source} snapshot values require input_availability.{source}=true"
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
    rule_version: int = Field(ge=1)
    application_reason: Literal[
        "dose_evidence_incomplete",
        "upper_limit_exceeded",
    ] | None = None
    message: str
    severity: Severity
    source: str = "master_context_v1"
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    citations: list[CitationReference] = Field(default_factory=list)


class IngredientDoseAggregate(BaseModel):
    ingredient_key: str
    product_count: int = Field(ge=1)
    product_names: list[str] = Field(min_length=1)
    duplicate_across_products: bool
    total_daily_amount: float | None = Field(default=None, ge=0)
    unit: str | None = None
    dose_input_count: int = Field(ge=0)
    dose_observation_count: int = Field(ge=0)
    dose_complete: bool


class SafetySummary(BaseModel):
    applied_at: AwareDatetime
    status: RecommendationStatus
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    rule_refs: list[RuleReference] = Field(default_factory=list)
    duplicate_ingredient_keys: list[str] = Field(default_factory=list)
    ingredient_dose_aggregates: list[IngredientDoseAggregate] = Field(default_factory=list)


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


class CandidateScoreSignal(BaseModel):
    source: Literal[
        "symptom",
        "laboratory",
        "lifestyle",
        "dietary_pattern",
        "wearable",
        "cgm",
        "genetic",
    ]
    code: str = Field(min_length=1)
    observed_value: float | str
    unit: str | None = None
    points: float = Field(ge=0.0, le=10.0, allow_inf_nan=False)
    rule_id: str = Field(min_length=1)
    scoring_version: str = Field(min_length=1)
    reference_ids: list[str] = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)
    limitation: str = Field(min_length=1)


class CandidateScoreBreakdown(BaseModel):
    goal_alignment: float
    symptom_alignment: float
    lifestyle_alignment: float
    laboratory_alignment: float = 0.0
    dietary_alignment: float = 0.0
    wearable_adjustment: float = 0.0
    cgm_adjustment: float = 0.0
    genetic_adjustment: float = 0.0
    evidence_readiness: float
    budget_adjustment: float
    safety_adjustment: float
    conservative_adjustment: float
    learned_effect_bonus: float = 0.0
    applied_signals: list[CandidateScoreSignal] = Field(default_factory=list)
    total: float


ReasonIdentifier = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
ReasonText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1000),
]


class RecommendationReasonInputSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal[
        "goal",
        "symptom",
        "laboratory",
        "lifestyle",
        "dietary_pattern",
        "wearable",
        "cgm",
        "genetic",
        "safety",
    ]
    code: StructuredHealthCode
    observed_value: float | str
    unit: LaboratoryUnit | None = None


class RecommendationReasonScoreTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: Literal[
        "catalog_priority",
        "goal_alignment",
        "symptom_alignment",
        "lifestyle_alignment",
        "laboratory_alignment",
        "dietary_alignment",
        "wearable_adjustment",
        "cgm_adjustment",
        "genetic_adjustment",
        "evidence_readiness",
        "budget_adjustment",
        "safety_adjustment",
        "conservative_adjustment",
        "learned_effect_bonus",
    ]
    points: float = Field(ge=-1000.0, le=1000.0, allow_inf_nan=False)
    rule_ids: list[ReasonIdentifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_rule_ids(self) -> "RecommendationReasonScoreTerm":
        if len(set(self.rule_ids)) != len(self.rule_ids):
            raise ValueError("score-term rule IDs must be unique")
        return self


class RecommendationReasonEvidenceLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_source: Literal["goal_prior", "input_signal", "safety_rule"]
    code: StructuredHealthCode
    rule_id: ReasonIdentifier | None = None
    reference_ids: list[ReasonIdentifier] = Field(default_factory=list)
    claim_ids: list[ReasonIdentifier] = Field(default_factory=list)
    limitations: list[ReasonText] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_evidence_ids(self) -> "RecommendationReasonEvidenceLink":
        for field_name in ("reference_ids", "claim_ids", "limitations"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"reason evidence {field_name} must be unique")
        if self.evidence_source in {"input_signal", "safety_rule"} and self.rule_id is None:
            raise ValueError("input and safety evidence links require a rule ID")
        if self.evidence_source != "safety_rule" and (
            not self.reference_ids or not self.claim_ids
        ):
            raise ValueError("goal and scored-input evidence links require evidence IDs")
        return self


class RecommendationReasonBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_signals: list[RecommendationReasonInputSignal] = Field(min_length=1)
    score_terms: list[RecommendationReasonScoreTerm] = Field(min_length=1)
    evidence_links: list[RecommendationReasonEvidenceLink] = Field(min_length=1)
    rule_ids: list[ReasonIdentifier] = Field(min_length=1)
    reference_ids: list[ReasonIdentifier] = Field(min_length=1)
    claim_ids: list[ReasonIdentifier] = Field(min_length=1)
    limitations: list[ReasonText] = Field(min_length=1)
    score_total: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_reason_partition(self) -> "RecommendationReasonBreakdown":
        expected_terms = {
            "catalog_priority",
            "goal_alignment",
            "symptom_alignment",
            "lifestyle_alignment",
            "laboratory_alignment",
            "dietary_alignment",
            "wearable_adjustment",
            "cgm_adjustment",
            "genetic_adjustment",
            "evidence_readiness",
            "budget_adjustment",
            "safety_adjustment",
            "conservative_adjustment",
            "learned_effect_bonus",
        }
        term_names = [item.term for item in self.score_terms]
        if len(set(term_names)) != len(term_names):
            raise ValueError("recommendation reason score terms must be unique")
        if set(term_names) != expected_terms:
            raise ValueError("recommendation reason must contain every score term")
        input_keys = [(item.source, item.code) for item in self.input_signals]
        if len(set(input_keys)) != len(input_keys):
            raise ValueError("recommendation reason input signals must be unique")
        evidence_link_keys = [
            (link.evidence_source, link.code, link.rule_id)
            for link in self.evidence_links
        ]
        if len(set(evidence_link_keys)) != len(evidence_link_keys):
            raise ValueError("recommendation reason evidence links must be unique")
        for field_name in ("rule_ids", "reference_ids", "claim_ids", "limitations"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"recommendation reason {field_name} must be unique")
        if abs(sum(item.points for item in self.score_terms) - self.score_total) > 1e-6:
            raise ValueError("recommendation reason score total mismatch")
        linked_reference_ids = {
            value for link in self.evidence_links for value in link.reference_ids
        }
        linked_claim_ids = {
            value for link in self.evidence_links for value in link.claim_ids
        }
        linked_limitations = {
            value for link in self.evidence_links for value in link.limitations
        }
        if linked_reference_ids != set(self.reference_ids):
            raise ValueError("recommendation reason reference IDs must match evidence links")
        if linked_claim_ids != set(self.claim_ids):
            raise ValueError("recommendation reason claim IDs must match evidence links")
        if linked_limitations != set(self.limitations):
            raise ValueError("recommendation reason limitations must match evidence links")
        goal_codes = {
            item.code for item in self.input_signals if item.source == "goal"
        }
        scored_signal_codes = {
            item.code
            for item in self.input_signals
            if item.source not in {"goal", "safety"}
        }
        safety_signal_codes = {
            item.code for item in self.input_signals if item.source == "safety"
        }
        linked_goal_codes = {
            link.code for link in self.evidence_links if link.evidence_source == "goal_prior"
        }
        linked_signal_codes = {
            link.code
            for link in self.evidence_links
            if link.evidence_source == "input_signal"
        }
        linked_safety_codes = {
            link.code
            for link in self.evidence_links
            if link.evidence_source == "safety_rule"
        }
        if linked_goal_codes != goal_codes:
            raise ValueError("goal input signals must match goal-prior evidence links")
        if linked_signal_codes != scored_signal_codes:
            raise ValueError("scored input signals must match input-signal evidence links")
        if linked_safety_codes != safety_signal_codes:
            raise ValueError("safety input signals must match safety-rule evidence links")
        linked_rule_ids = {
            link.rule_id for link in self.evidence_links if link.rule_id is not None
        }
        term_rule_ids = {
            rule_id for term in self.score_terms for rule_id in term.rule_ids
        }
        if linked_rule_ids | term_rule_ids != set(self.rule_ids):
            raise ValueError("recommendation reason rule IDs must match terms and evidence links")
        return self


class CandidatePoolItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_key: StructuredHealthCode
    display_name: ReasonText
    matched_goals: list[RecommendationGoal] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_matched_goals(self) -> "CandidatePoolItem":
        if len(set(self.matched_goals)) != len(self.matched_goals):
            raise ValueError("candidate matched goals must be unique")
        return self


class CandidatePoolExclusion(CandidatePoolItem):
    exclusion_reasons: list[
        Literal[
            "safety_summary_excluded",
            "user_avoidance",
            "current_regimen_overlap",
        ]
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_exclusion_reasons(self) -> "CandidatePoolExclusion":
        if len(set(self.exclusion_reasons)) != len(self.exclusion_reasons):
            raise ValueError("candidate exclusion reasons must be unique")
        return self


class CandidatePoolTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pre_safety_candidates: list[CandidatePoolItem]
    excluded_candidates: list[CandidatePoolExclusion]
    post_safety_candidates: list[CandidatePoolItem]
    selected_candidate_keys: list[StructuredHealthCode]
    applied_safety_rule_ids: list[ReasonIdentifier]
    global_blocked: bool

    @model_validator(mode="after")
    def validate_candidate_partition(self) -> "CandidatePoolTrace":
        pre_keys = [item.ingredient_key for item in self.pre_safety_candidates]
        excluded_keys = [item.ingredient_key for item in self.excluded_candidates]
        post_keys = [item.ingredient_key for item in self.post_safety_candidates]
        for label, values in (
            ("pre-safety", pre_keys),
            ("excluded", excluded_keys),
            ("post-safety", post_keys),
            ("selected", self.selected_candidate_keys),
            ("safety-rule", self.applied_safety_rule_ids),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} candidate trace values must be unique")
        if set(excluded_keys) & set(post_keys):
            raise ValueError("excluded and post-safety candidate sets must be disjoint")
        if set(pre_keys) != set(excluded_keys) | set(post_keys):
            raise ValueError("pre-safety candidates must partition into excluded and post-safety")
        pre_by_key = {
            item.ingredient_key: (item.display_name, tuple(item.matched_goals))
            for item in self.pre_safety_candidates
        }
        partition_by_key = {
            item.ingredient_key: (item.display_name, tuple(item.matched_goals))
            for item in [*self.excluded_candidates, *self.post_safety_candidates]
        }
        if pre_by_key != partition_by_key:
            raise ValueError("candidate identity must be preserved across the safety partition")
        if not set(self.selected_candidate_keys).issubset(post_keys):
            raise ValueError("selected candidates must be a subset of post-safety candidates")
        if self.global_blocked and self.selected_candidate_keys:
            raise ValueError("globally blocked candidate traces cannot contain selections")
        return self


class RecommendationCandidate(BaseModel):
    ingredient_key: str
    display_name: str
    rationale: str
    expected_support_goals: list[RecommendationGoal]
    rule_refs: list[str] = Field(default_factory=list)
    score_breakdown: CandidateScoreBreakdown
    reason_breakdown: RecommendationReasonBreakdown
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
    execution_id: str = Field(pattern=r"^exec_[a-f0-9]{32}$")
    request_id: str
    decision_id: str
    status: RecommendationStatus
    decision_summary: DecisionSummary
    normalized_focus_goals: list[RecommendationGoal]
    safety_summary: SafetySummary
    safety_flags: list[str] = Field(default_factory=list)
    safety_evidence: list[SafetyEvidenceItem] = Field(default_factory=list)
    recommendations: list[RecommendationCandidate]
    candidate_pool_trace: CandidatePoolTrace
    next_action: NextAction
    next_action_rationale: NextActionRationale
    follow_up_window_days: int = Field(ge=1, le=90)
    follow_up_questions: list[str] = Field(default_factory=list)
    missing_information: list[MissingInformationItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    limitation_details: list[LimitationItem] = Field(default_factory=list)
    metadata: EngineMetadata
