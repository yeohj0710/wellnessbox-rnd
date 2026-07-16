from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wellnessbox_rnd.schemas.recommendation import (
    BudgetLevel,
    MissingInfoImportance,
    RecommendationGoal,
    Severity,
)


class IngredientCatalogItem(BaseModel):
    key: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    supported_goals: list[RecommendationGoal]
    supported_symptoms: list[str] = Field(default_factory=list)
    preferred_signals: list[str] = Field(default_factory=list)
    budget_tier: BudgetLevel
    default_priority: float = 0.0
    follow_up_focus: str
    explanation_tags: list[str] = Field(default_factory=list)
    conservative_profile: Literal["baseline", "standard", "interaction_sensitive"] = (
        "standard"
    )


class SafetyRuleMetadata(BaseModel):
    rule_id: str
    message: str
    severity: Severity
    warning_text: str


class InputRequirementRule(BaseModel):
    input_key: str
    metadata: SafetyRuleMetadata
    blocked_reason: str


class MedicationInteractionRule(BaseModel):
    medications: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata


class SpecialPopulationRule(BaseModel):
    statuses: list[Literal["pregnant", "lactating"]] = Field(min_length=1)
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata


class ConditionSafetyRule(BaseModel):
    conditions: list[str] = Field(min_length=1)
    effect: Literal["contraindication", "review_required"]
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata

    @model_validator(mode="after")
    def require_contraindication_ingredients(self) -> "ConditionSafetyRule":
        if self.effect == "contraindication" and not self.excluded_ingredients:
            raise ValueError("contraindication rules require excluded_ingredients")
        return self


class AllergyRule(BaseModel):
    allergies: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata


class RiskFlagRule(BaseModel):
    risk_flags: list[str] = Field(default_factory=list)
    blocked_reason: str
    metadata: SafetyRuleMetadata


class DoseLimitRule(BaseModel):
    ingredient_key: str
    max_daily_amount: float | None = None
    unit: str | None = None
    allowed_evidence_sources: list[
        Literal["structured_dose", "ingredient_line", "title"]
    ] = Field(default_factory=lambda: ["structured_dose", "ingredient_line", "title"])
    metadata: SafetyRuleMetadata


class DuplicateOverlapRule(BaseModel):
    metadata: SafetyRuleMetadata


class GoalContextRule(BaseModel):
    question: str
    reason: str
    importance: MissingInfoImportance


class SafetyRuleSet(BaseModel):
    input_requirements: list[InputRequirementRule] = Field(default_factory=list)
    medication_rules: list[MedicationInteractionRule] = Field(default_factory=list)
    special_population_rules: list[SpecialPopulationRule] = Field(default_factory=list)
    condition_rules: list[ConditionSafetyRule] = Field(default_factory=list)
    allergy_rules: list[AllergyRule] = Field(default_factory=list)
    risk_flag_rules: list[RiskFlagRule] = Field(default_factory=list)
    dose_limits: list[DoseLimitRule] = Field(default_factory=list)
    duplicate_overlap_rule: DuplicateOverlapRule | None = None
    goal_context_rules: dict[str, GoalContextRule] = Field(default_factory=dict)
    duplicate_policy: str = "exclude"
