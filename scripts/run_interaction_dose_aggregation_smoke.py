from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.interim.safety import evaluate_safety
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    DoseAmount,
    MedicationInput,
    RecommendationGoal,
    RecommendationRequest,
    SupplementIngredientInput,
    SupplementInput,
    UserProfile,
)


def _request(
    case_id: str,
    *,
    medications: list[MedicationInput] | None = None,
    supplements: list[SupplementInput] | None = None,
) -> RecommendationRequest:
    return RecommendationRequest(
        request_id=f"op035-op036-{case_id}",
        user_profile=UserProfile(age=45, biological_sex="female"),
        goals=[RecommendationGoal.GENERAL_WELLNESS],
        medications=medications or [],
        current_supplements=supplements or [],
    )


def _rule_result(summary, rule_id: str) -> dict[str, Any]:
    rule = next(item for item in summary.rule_refs if item.rule_id == rule_id)
    return rule.model_dump(mode="json")


def _aggregate_result(summary, ingredient_key: str) -> dict[str, Any]:
    aggregate = next(
        item
        for item in summary.ingredient_dose_aggregates
        if item.ingredient_key == ingredient_key
    )
    return aggregate.model_dump(mode="json")


def build_evidence() -> dict[str, Any]:
    omega3_summary = assess_safety(
        normalize_request(
            _request(
                "warfarin-omega3",
                medications=[MedicationInput(name="warfarin")],
                supplements=[SupplementInput(name="Fish Oil", ingredients=["Omega-3"])],
            )
        )
    )
    omega3_rule = _rule_result(omega3_summary, "SAFETY-ANTICOAG-001")
    if omega3_rule["reference_ids"] != ["REF-NIH-ODS-OMEGA3-001"]:
        raise AssertionError("warfarin-omega3 policy is missing its exact reference ID")
    if omega3_rule["claim_ids"] != ["CLM-NIH-ODS-OMEGA3-WARFARIN-001"]:
        raise AssertionError("warfarin-omega3 policy is missing its exact claim ID")

    glucosamine_summary = assess_safety(
        normalize_request(
            _request(
                "warfarin-glucosamine",
                medications=[MedicationInput(name="warfarin")],
                supplements=[SupplementInput(name="glucosamine")],
            )
        )
    )
    glucosamine_rule = _rule_result(
        glucosamine_summary,
        "KB-SAFETY-ANTICOAG-001",
    )
    if glucosamine_rule["reference_ids"] != ["REF-KNOWLEDGE-ANTICOAG-001"]:
        raise AssertionError("knowledge interaction is missing its exact reference ID")

    complete_summary = assess_safety(
        normalize_request(
            _request(
                "complete-dose-total",
                supplements=[
                    SupplementInput(
                        name="Bone Daily A",
                        ingredients=[
                            SupplementIngredientInput(
                                name="Vitamin D3",
                                daily_dose=DoseAmount(amount=2400, unit="IU"),
                            )
                        ],
                    ),
                    SupplementInput(
                        name="Bone Daily B",
                        ingredients=[
                            SupplementIngredientInput(
                                name="Vitamin D3",
                                daily_dose=DoseAmount(amount=2000, unit="IU"),
                            )
                        ],
                    ),
                ],
            )
        )
    )
    complete_aggregate = _aggregate_result(complete_summary, "vitamin_d3")
    if complete_aggregate["total_daily_amount"] != 4400:
        raise AssertionError("cross-product vitamin D total must equal 4400 IU")
    if not complete_aggregate["dose_complete"]:
        raise AssertionError("fully observed cross-product dose must be complete")

    general_summary = assess_safety(
        normalize_request(
            _request(
                "general-ingredient-total",
                supplements=[
                    SupplementInput(
                        name="Fish Oil A",
                        ingredients=[
                            SupplementIngredientInput(
                                name="Omega-3",
                                daily_dose=DoseAmount(amount=1000, unit="mg"),
                            )
                        ],
                    ),
                    SupplementInput(
                        name="Fish Oil B",
                        ingredients=[
                            SupplementIngredientInput(
                                name="Omega-3",
                                daily_dose=DoseAmount(amount=500, unit="mg"),
                            )
                        ],
                    ),
                ],
            )
        )
    )
    general_aggregate = _aggregate_result(general_summary, "omega3")
    if general_aggregate["total_daily_amount"] != 1500:
        raise AssertionError("ingredients without dose limits must still be aggregated")
    if general_aggregate["unit"] != "mg" or not general_aggregate["dose_complete"]:
        raise AssertionError("compatible general ingredient doses must be complete")

    unknown_summary = assess_safety(
        normalize_request(
            _request(
                "duplicate-unknown-dose",
                supplements=[
                    SupplementInput(name="Gut Product A", ingredients=["Probiotics"]),
                    SupplementInput(name="Gut Product B", ingredients=["Probiotics"]),
                ],
            )
        )
    )
    unknown_aggregate = _aggregate_result(unknown_summary, "probiotics")
    if unknown_aggregate["total_daily_amount"] is not None:
        raise AssertionError("unknown product doses must not produce an invented total")

    partial_summary = assess_safety(
        normalize_request(
            _request(
                "partial-dose-total",
                supplements=[
                    SupplementInput(
                        name="Bone Product A",
                        ingredients=[
                            SupplementIngredientInput(
                                name="Vitamin D3",
                                daily_dose=DoseAmount(amount=2000, unit="IU"),
                            )
                        ],
                    ),
                    SupplementInput(name="Bone Product B", ingredients=["Vitamin D3"]),
                ],
            )
        )
    )
    partial_aggregate = _aggregate_result(partial_summary, "vitamin_d3")
    if partial_aggregate["dose_complete"]:
        raise AssertionError("partial cross-product dose must remain explicitly incomplete")

    partial_line_summary = assess_safety(
        normalize_request(
            _request(
                "partial-same-product-lines",
                supplements=[
                    SupplementInput(
                        name="Bone Product",
                        ingredients=["Vitamin D3 1000 IU", "Vitamin D3"],
                    )
                ],
            )
        )
    )
    partial_line_aggregate = _aggregate_result(partial_line_summary, "vitamin_d3")
    if partial_line_aggregate["dose_complete"]:
        raise AssertionError("an undosed ingredient line must keep the total incomplete")

    replay = evaluate_safety(
        {"medications": ["warfarin"], "ingredients": ["omega3"]}
    )
    replay_finding = next(
        item for item in replay.findings if item.rule_id == "SAFE-DDI-001"
    )
    if replay_finding.reference_ids != ("REF-NIH-ODS-OMEGA3-001",):
        raise AssertionError("replay interaction finding lost its evidence ID")
    coumadin_replay = evaluate_safety(
        {"medications": ["Coumadin"], "ingredients": ["omega3"]}
    )
    coumadin_finding = next(
        item for item in coumadin_replay.findings if item.rule_id == "SAFE-DDI-001"
    )
    if coumadin_finding.reference_ids != ("REF-NIH-ODS-OMEGA3-001",):
        raise AssertionError("Coumadin replay alias lost the warfarin evidence ID")
    unsupported_replay = evaluate_safety(
        {"medications": ["apixaban"], "ingredients": ["ginkgo"]}
    )
    if any(
        finding.rule_id == "SAFE-DDI-001" for finding in unsupported_replay.findings
    ):
        raise AssertionError("warfarin-omega3 evidence was reused for another pair")

    return {
        "schema_version": "op035_op036_interaction_dose_aggregation_smoke_v1",
        "requirements": ["OP-035", "OP-036"],
        "contains_health_identifiers": False,
        "source_scope": {
            "reference_id": "REF-NIH-ODS-OMEGA3-001",
            "claim_id": "CLM-NIH-ODS-OMEGA3-WARFARIN-001",
            "url": "https://ods.od.nih.gov/factsheets/Omega3FattyAcids-HealthProfessional/",
            "source_supports": (
                "Possible fish-oil/warfarin INR effect; most research at 3–6 g/day "
                "found no significant anticoagulant-status change; FDA-approved "
                "omega-3 pharmaceutical package inserts state periodic INR monitoring "
                "for those products with anticoagulants."
            ),
            "policy_addition": (
                "The deterministic candidate policy excludes omega-3 conservatively "
                "when warfarin is present."
            ),
        },
        "interaction_cases": {
            "warfarin_omega3": {
                "status": omega3_summary.status.value,
                "excluded_ingredients": omega3_summary.excluded_ingredients,
                "rule": omega3_rule,
            },
            "warfarin_glucosamine": {
                "status": glucosamine_summary.status.value,
                "rule": glucosamine_rule,
            },
            "interim_replay": {
                "action": replay.action,
                "finding": {
                    "rule_id": replay_finding.rule_id,
                    "reference_ids": list(replay_finding.reference_ids),
                    "claim_ids": list(replay_finding.claim_ids),
                },
            },
            "coumadin_interim_replay": {
                "action": coumadin_replay.action,
                "finding": {
                    "rule_id": coumadin_finding.rule_id,
                    "reference_ids": list(coumadin_finding.reference_ids),
                    "claim_ids": list(coumadin_finding.claim_ids),
                },
            },
            "unsupported_pair_has_warfarin_omega3_finding": False,
        },
        "dose_aggregation_cases": {
            "complete_cross_product_total": complete_aggregate,
            "general_ingredient_total": general_aggregate,
            "duplicate_unknown_total": unknown_aggregate,
            "partial_cross_product_total": partial_aggregate,
            "partial_same_product_lines": partial_line_aggregate,
        },
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_path = (
        root
        / "data"
        / "original_plan"
        / "evidence"
        / "op035_op036_interaction_dose_aggregation_smoke_v1.json"
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
