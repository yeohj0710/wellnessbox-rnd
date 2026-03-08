from typing import Literal

from pydantic import BaseModel, Field

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


class PregnancyRule(BaseModel):
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata


class ConditionExclusionRule(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
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
    pregnancy_rule: PregnancyRule | None = None
    condition_rules: list[ConditionExclusionRule] = Field(default_factory=list)
    duplicate_overlap_rule: DuplicateOverlapRule | None = None
    goal_context_rules: dict[str, GoalContextRule] = Field(default_factory=dict)
    duplicate_policy: str = "exclude"
