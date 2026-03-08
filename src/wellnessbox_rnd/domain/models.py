from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import BudgetLevel, RecommendationGoal


class IngredientCatalogItem(BaseModel):
    key: str
    display_name: str
    supported_goals: list[RecommendationGoal]
    supported_symptoms: list[str] = Field(default_factory=list)
    preferred_signals: list[str] = Field(default_factory=list)
    budget_tier: BudgetLevel
    default_priority: float = 0.0
    follow_up_focus: str
    explanation_tags: list[str] = Field(default_factory=list)


class SafetyRuleSet(BaseModel):
    minimum_required_inputs: list[str] = Field(default_factory=list)
    medication_interactions: dict[str, list[str]] = Field(default_factory=dict)
    pregnancy_exclusions: list[str] = Field(default_factory=list)
    condition_exclusions: dict[str, list[str]] = Field(default_factory=dict)
    condition_review_flags: dict[str, str] = Field(default_factory=dict)
    goal_data_questions: dict[str, str] = Field(default_factory=dict)
    duplicate_policy: str = "exclude"

