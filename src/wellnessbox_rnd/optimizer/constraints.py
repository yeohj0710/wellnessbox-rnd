from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

FormulationV1 = Literal["capsule", "tablet", "powder", "liquid", "gummy", "other"]
ConstraintDimensionV1 = Literal[
    "efficacy",
    "safety",
    "cost",
    "daily_burden",
    "formulation",
]
ConstraintViolationV1 = Literal[
    "minimum_effect_score_not_met",
    "safety_status_blocked",
    "excluded_ingredient_present",
    "maximum_total_cost_exceeded",
    "maximum_product_count_exceeded",
    "maximum_daily_unit_count_exceeded",
    "preferred_formulation_not_met",
]

CHECKED_DIMENSIONS: tuple[ConstraintDimensionV1, ...] = (
    "efficacy",
    "safety",
    "cost",
    "daily_burden",
    "formulation",
)


class OptimizationConstraintsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["optimization_constraints_v1"]
    policy_version: Literal["2026-07-21.1"]
    minimum_effect_score: float = Field(ge=-1000.0, le=1000.0, allow_inf_nan=False)
    excluded_ingredient_keys: tuple[str, ...] = ()
    max_total_cost_krw: StrictInt = Field(ge=0)
    max_products: StrictInt = Field(ge=1, le=20)
    max_daily_units: StrictInt = Field(ge=1, le=100)
    preferred_formulations: tuple[FormulationV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_values(self) -> OptimizationConstraintsV1:
        _require_unique(self.excluded_ingredient_keys, "excluded ingredient keys")
        _require_unique(self.preferred_formulations, "preferred formulations")
        return self


class OptimizationCandidateFactsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["optimization_candidate_facts_v1"]
    candidate_id: str = Field(min_length=1, max_length=128)
    ingredient_keys: tuple[str, ...] = Field(min_length=1)
    expected_effect_score: float = Field(
        ge=-1000.0,
        le=1000.0,
        allow_inf_nan=False,
    )
    safety_status: Literal["allowed", "blocked"]
    total_cost_krw: StrictInt = Field(ge=0)
    product_count: StrictInt = Field(ge=1, le=100)
    daily_unit_count: StrictInt = Field(ge=1, le=1000)
    formulations: tuple[FormulationV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_values(self) -> OptimizationCandidateFactsV1:
        _require_unique(self.ingredient_keys, "candidate ingredient keys")
        _require_unique(self.formulations, "candidate formulations")
        return self


class OptimizationConstraintEvaluationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["optimization_constraint_evaluation_v1"]
    candidate: OptimizationCandidateFactsV1
    constraints: OptimizationConstraintsV1
    checked_dimensions: tuple[ConstraintDimensionV1, ...]
    violations: tuple[ConstraintViolationV1, ...]
    feasible: bool

    @model_validator(mode="after")
    def validate_derived_output(self) -> OptimizationConstraintEvaluationV1:
        expected_violations = _derive_violations(self.candidate, self.constraints)
        if (
            self.checked_dimensions != CHECKED_DIMENSIONS
            or self.violations != expected_violations
            or self.feasible is not (not expected_violations)
        ):
            raise ValueError("evaluation does not match candidate and constraints")
        return self


def evaluate_optimization_candidate_v1(
    candidate: OptimizationCandidateFactsV1,
    constraints: OptimizationConstraintsV1,
) -> OptimizationConstraintEvaluationV1:
    violations = _derive_violations(candidate, constraints)
    return OptimizationConstraintEvaluationV1(
        schema_version="optimization_constraint_evaluation_v1",
        candidate=candidate,
        constraints=constraints,
        checked_dimensions=CHECKED_DIMENSIONS,
        violations=violations,
        feasible=not violations,
    )


def _derive_violations(
    candidate: OptimizationCandidateFactsV1,
    constraints: OptimizationConstraintsV1,
) -> tuple[ConstraintViolationV1, ...]:
    violations: list[ConstraintViolationV1] = []
    if candidate.expected_effect_score < constraints.minimum_effect_score:
        violations.append("minimum_effect_score_not_met")
    if candidate.safety_status == "blocked":
        violations.append("safety_status_blocked")
    if set(candidate.ingredient_keys) & set(constraints.excluded_ingredient_keys):
        violations.append("excluded_ingredient_present")
    if candidate.total_cost_krw > constraints.max_total_cost_krw:
        violations.append("maximum_total_cost_exceeded")
    if candidate.product_count > constraints.max_products:
        violations.append("maximum_product_count_exceeded")
    if candidate.daily_unit_count > constraints.max_daily_units:
        violations.append("maximum_daily_unit_count_exceeded")
    if not set(candidate.formulations).issubset(constraints.preferred_formulations):
        violations.append("preferred_formulation_not_met")
    return tuple(violations)


def _require_unique(values: Sequence[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must be unique")


__all__ = [
    "ConstraintDimensionV1",
    "ConstraintViolationV1",
    "FormulationV1",
    "OptimizationCandidateFactsV1",
    "OptimizationConstraintEvaluationV1",
    "OptimizationConstraintsV1",
    "evaluate_optimization_candidate_v1",
]
