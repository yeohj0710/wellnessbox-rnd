from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.knowledge.runtime_db import build_runtime_knowledge_db
from wellnessbox_rnd.safety.rules import get_safety_rule_set
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    DoseAmount,
    RecommendationGoal,
    RecommendationRequest,
    SafetySummary,
    SupplementIngredientInput,
    SupplementInput,
    UserProfile,
)

FIXED_APPLIED_AT = datetime(2026, 7, 16, tzinfo=UTC)


def _request(case_id: str, supplements: list[SupplementInput]) -> RecommendationRequest:
    return RecommendationRequest(
        request_id=f"op037-op038-{case_id}",
        user_profile=UserProfile(age=45, biological_sex="female"),
        goals=[RecommendationGoal.GENERAL_WELLNESS],
        current_supplements=supplements,
    )


def _assess(case_id: str, supplements: list[SupplementInput]) -> SafetySummary:
    return assess_safety(
        normalize_request(_request(case_id, supplements)),
        applied_at=FIXED_APPLIED_AT,
    )


def _ingredient(
    name: str,
    amount: float,
    unit: str,
) -> SupplementIngredientInput:
    return SupplementIngredientInput(
        name=name,
        daily_dose=DoseAmount(amount=amount, unit=unit),
    )


def _case_result(
    summary: SafetySummary,
    *,
    ingredient_key: str,
    rule_id: str,
) -> dict[str, Any]:
    aggregate = next(
        item
        for item in summary.ingredient_dose_aggregates
        if item.ingredient_key == ingredient_key
    )
    dose_rule = next(
        (item for item in summary.rule_refs if item.rule_id == rule_id),
        None,
    )
    return {
        "applied_at": summary.applied_at.isoformat(),
        "status": summary.status.value,
        "excluded": ingredient_key in summary.excluded_ingredients,
        "aggregate": aggregate.model_dump(mode="json"),
        "dose_rule": dose_rule.model_dump(mode="json") if dose_rule else None,
    }


def build_evidence() -> dict[str, Any]:
    above = _assess(
        "complete-above",
        [
            SupplementInput(
                name="Vitamin C A",
                ingredients=[_ingredient("Vitamin C", 1.0, "g")],
            ),
            SupplementInput(
                name="Vitamin C B",
                ingredients=[_ingredient("Vitamin C", 1.2, "g")],
            ),
        ],
    )
    below = _assess(
        "complete-below",
        [
            SupplementInput(
                name="Vitamin C A",
                ingredients=[_ingredient("Vitamin C", 0.5, "g")],
            ),
            SupplementInput(
                name="Vitamin C B",
                ingredients=[_ingredient("Vitamin C", 1.0, "g")],
            ),
        ],
    )
    missing = _assess(
        "missing",
        [SupplementInput(name="Undosed vitamin D", ingredients=["Vitamin D3"])],
    )
    partial = _assess(
        "partial",
        [
            SupplementInput(
                name="Vitamin D A",
                ingredients=[_ingredient("Vitamin D3", 2000, "IU")],
            ),
            SupplementInput(name="Vitamin D B", ingredients=["Vitamin D3"]),
        ],
    )
    incompatible = _assess(
        "incompatible",
        [
            SupplementInput(
                name="Vitamin C wrong unit",
                ingredients=[_ingredient("Vitamin C", 500, "IU")],
            )
        ],
    )
    ambiguous_range = _assess(
        "ambiguous-range",
        [
            SupplementInput(
                name="Vitamin C range",
                ingredients=["Vitamin C 1000 mg - 2500 mg"],
            )
        ],
    )

    cases = {
        "complete_above_limit": _case_result(
            above,
            ingredient_key="vitamin_c",
            rule_id="SAFETY-DOSE-VITC-001",
        ),
        "complete_below_limit": _case_result(
            below,
            ingredient_key="vitamin_c",
            rule_id="SAFETY-DOSE-VITC-001",
        ),
        "missing_dose": _case_result(
            missing,
            ingredient_key="vitamin_d3",
            rule_id="SAFETY-DOSE-VITD3-001",
        ),
        "partial_dose": _case_result(
            partial,
            ingredient_key="vitamin_d3",
            rule_id="SAFETY-DOSE-VITD3-001",
        ),
        "incompatible_unit": _case_result(
            incompatible,
            ingredient_key="vitamin_c",
            rule_id="SAFETY-DOSE-VITC-001",
        ),
        "ambiguous_range": _case_result(
            ambiguous_range,
            ingredient_key="vitamin_c",
            rule_id="SAFETY-DOSE-VITC-001",
        ),
    }

    above_rule = cases["complete_above_limit"]["dose_rule"]
    if cases["complete_above_limit"]["aggregate"]["total_daily_amount"] != 2200:
        raise AssertionError("complete mass doses were not normalized to 2200 mg")
    if above_rule["application_reason"] != "upper_limit_exceeded":
        raise AssertionError("complete above-limit dose lost its application reason")
    if cases["complete_below_limit"]["dose_rule"] is not None:
        raise AssertionError("complete below-limit dose unexpectedly triggered the limit")
    if cases["missing_dose"]["dose_rule"] is not None:
        raise AssertionError("optional absent dose claimed an upper-limit evaluation")
    for case_name in ("partial_dose", "incompatible_unit", "ambiguous_range"):
        case = cases[case_name]
        if case["dose_rule"]["application_reason"] != "dose_evidence_incomplete":
            raise AssertionError(f"{case_name} did not fail closed")
        if case["status"] != "ok" or not case["excluded"]:
            raise AssertionError(
                f"{case_name} did not exclude the ingredient for review"
            )
    if {case["applied_at"] for case in cases.values()} != {
        FIXED_APPLIED_AT.isoformat()
    }:
        raise AssertionError("smoke cases did not preserve one fixed application time")

    runtime_db = build_runtime_knowledge_db()
    runtime_versions = [
        *(record.rule_version for record in runtime_db.interaction_rules),
        *(record.rule_version for record in runtime_db.contraindication_rules),
        *(record.rule_version for record in runtime_db.dose_limits),
    ]
    returned_versions = [
        rule["rule_version"]
        for case in cases.values()
        if (rule := case["dose_rule"]) is not None
    ]
    if not runtime_versions or not all(version >= 1 for version in runtime_versions):
        raise AssertionError("runtime safety rules are missing positive versions")
    if not returned_versions or not all(version >= 1 for version in returned_versions):
        raise AssertionError("returned safety rules are missing positive versions")
    raw_dose_versions = {
        rule.metadata.rule_id: rule.metadata.version
        for rule in get_safety_rule_set().dose_limits
    }
    runtime_dose_versions = {
        record.rule_id: record.rule_version for record in runtime_db.dose_limits
    }
    for case in cases.values():
        returned_rule = case["dose_rule"]
        if returned_rule is None:
            continue
        rule_id = returned_rule["rule_id"]
        if not (
            returned_rule["rule_version"]
            == runtime_dose_versions[rule_id]
            == raw_dose_versions[rule_id]
        ):
            raise AssertionError(f"rule version provenance diverged for {rule_id}")

    return {
        "schema_version": "op037_op038_dose_limit_rule_metadata_smoke_v1",
        "requirements": ["OP-037", "OP-038"],
        "contains_health_identifiers": False,
        "fixed_applied_at": FIXED_APPLIED_AT.isoformat(),
        "runtime_rule_version_count": len(runtime_versions),
        "minimum_runtime_rule_version": min(runtime_versions),
        "cases": cases,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_path = (
        root
        / "data"
        / "original_plan"
        / "evidence"
        / "op037_op038_dose_limit_rule_metadata_smoke_v1.json"
    )
    rendered = json.dumps(build_evidence(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rendered_bytes = rendered.encode("utf-8")
    output_path.write_bytes(rendered_bytes)
    digest = hashlib.sha256(rendered_bytes).hexdigest()
    if hashlib.sha256(output_path.read_bytes()).hexdigest() != digest:
        raise AssertionError("written evidence hash does not match rendered evidence")
    print(f"Evidence: {output_path}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
