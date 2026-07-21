import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.optimizer.constraints import (
    OptimizationCandidateFactsV1,
    OptimizationConstraintsV1,
    evaluate_optimization_candidate_v1,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data/contracts/optimization_constraints_v1.json"


def _constraints(**updates: object) -> OptimizationConstraintsV1:
    payload = {
        "schema_version": "optimization_constraints_v1",
        "policy_version": "2026-07-21.1",
        "minimum_effect_score": 5.0,
        "excluded_ingredient_keys": ["unsafe_ingredient"],
        "max_total_cost_krw": 50_000,
        "max_products": 2,
        "max_daily_units": 4,
        "preferred_formulations": ["capsule", "tablet"],
    }
    payload.update(updates)
    return OptimizationConstraintsV1.model_validate(payload)


def _candidate(**updates: object) -> OptimizationCandidateFactsV1:
    payload = {
        "schema_version": "optimization_candidate_facts_v1",
        "candidate_id": "candidate-safe",
        "ingredient_keys": ["magnesium_glycinate", "vitamin_d3"],
        "expected_effect_score": 7.5,
        "safety_status": "allowed",
        "total_cost_krw": 42_000,
        "product_count": 2,
        "daily_unit_count": 3,
        "formulations": ["capsule", "tablet"],
    }
    payload.update(updates)
    return OptimizationCandidateFactsV1.model_validate(payload)


def test_contract_file_is_the_canonical_default_policy() -> None:
    loaded = OptimizationConstraintsV1.model_validate_json(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )
    assert loaded == _constraints()


def test_feasible_candidate_records_all_five_constraint_dimensions() -> None:
    result = evaluate_optimization_candidate_v1(_candidate(), _constraints())

    assert result.feasible is True
    assert result.violations == ()
    assert result.checked_dimensions == (
        "efficacy",
        "safety",
        "cost",
        "daily_burden",
        "formulation",
    )


@pytest.mark.parametrize(
    ("candidate", "violation"),
    [
        (_candidate(expected_effect_score=4.99), "minimum_effect_score_not_met"),
        (_candidate(safety_status="blocked"), "safety_status_blocked"),
        (
            _candidate(ingredient_keys=["magnesium_glycinate", "unsafe_ingredient"]),
            "excluded_ingredient_present",
        ),
        (_candidate(total_cost_krw=50_001), "maximum_total_cost_exceeded"),
        (_candidate(product_count=3), "maximum_product_count_exceeded"),
        (_candidate(daily_unit_count=5), "maximum_daily_unit_count_exceeded"),
        (_candidate(formulations=["powder"]), "preferred_formulation_not_met"),
    ],
)
def test_each_constraint_violation_is_explicit(
    candidate: OptimizationCandidateFactsV1,
    violation: str,
) -> None:
    result = evaluate_optimization_candidate_v1(candidate, _constraints())

    assert result.feasible is False
    assert violation in result.violations


def test_evaluation_rejects_derived_output_mutation() -> None:
    result = evaluate_optimization_candidate_v1(_candidate(), _constraints())
    payload = result.model_dump(mode="json")
    payload["feasible"] = False

    with pytest.raises(ValidationError, match="does not match candidate and constraints"):
        type(result).model_validate(payload)


def test_validated_contract_and_evaluation_collections_are_immutable() -> None:
    constraints = _constraints()
    result = evaluate_optimization_candidate_v1(_candidate(), constraints)

    with pytest.raises(AttributeError):
        constraints.excluded_ingredient_keys.append("late_unsafe")  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        result.checked_dimensions.clear()  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "payload",
    [
        {"ingredient_keys": ["vitamin_d3", "vitamin_d3"]},
        {"expected_effect_score": float("nan")},
        {"formulations": ["capsule", "capsule"]},
    ],
)
def test_candidate_rejects_ambiguous_or_non_finite_input(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _candidate(**payload)


def test_contract_rejects_duplicate_exclusions_and_preferences() -> None:
    with pytest.raises(ValidationError):
        _constraints(excluded_ingredient_keys=["zinc", "zinc"])
    with pytest.raises(ValidationError):
        _constraints(preferred_formulations=["capsule", "capsule"])


def test_contract_json_has_no_unvalidated_extra_fields() -> None:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["untracked_weight"] = 1

    with pytest.raises(ValidationError):
        OptimizationConstraintsV1.model_validate(payload)
