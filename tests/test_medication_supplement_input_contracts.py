from __future__ import annotations

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.models.efficacy_model_v0 import (
    EfficacyFeatureVectorizer,
    build_runtime_efficacy_feature_dict,
)
from wellnessbox_rnd.models.policy_model_v0 import (
    PolicyFeatureVectorizer,
    build_runtime_policy_feature_dict,
)
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    DoseAmount,
    DoseUnit,
    MedicationInput,
    RecommendationGoal,
    RecommendationRequest,
    SupplementIngredientInput,
    SupplementInput,
    UserProfile,
)


def _request(
    *,
    medications: list[MedicationInput] | None = None,
    supplements: list[SupplementInput] | None = None,
) -> RecommendationRequest:
    return RecommendationRequest(
        user_profile=UserProfile(age=45, biological_sex="female"),
        goals=[RecommendationGoal.BONE_JOINT],
        medications=medications or [],
        current_supplements=supplements or [],
    )


def _dose_rule_ids(request: RecommendationRequest) -> set[str]:
    summary = assess_safety(normalize_request(request))
    return {reference.rule_id for reference in summary.rule_refs if "DOSE" in reference.rule_id}


def test_medication_classification_and_numeric_dose_are_normalized_without_loss() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {"age": 45, "biological_sex": "female"},
            "goals": ["bone_joint"],
            "medications": [
                {
                    "name": " Metformin ",
                    "classification": {
                        "code": " A10BA02 ",
                        "system": " ATC ",
                        "display_name": "Biguanides",
                    },
                    "dose": {"amount": 500, "unit": "mg"},
                }
            ],
        }
    )

    intake = normalize_request(request)
    normalized = intake.normalized_medications[0]

    assert intake.medication_set == {"metformin"}
    assert intake.medication_classification_set == {"atc::a10ba02"}
    assert normalized.name == "metformin"
    assert normalized.classification is not None
    assert normalized.classification.code == "a10ba02"
    assert normalized.classification.system == "atc"
    assert normalized.classification.display_name == "Biguanides"
    assert normalized.dose == DoseAmount(amount=500, unit=DoseUnit.MILLIGRAM)


def test_legacy_medication_and_supplement_dose_strings_remain_accepted() -> None:
    request = _request(
        medications=[MedicationInput(name="warfarin", dose=" 5mg ")],
        supplements=[
            SupplementInput(
                name="Daily Bone Softgel",
                dose=" 125 mcg ",
                ingredients=["Vitamin D3"],
            )
        ],
    )

    intake = normalize_request(request)

    assert intake.normalized_medications[0].dose == "5mg"
    assert intake.normalized_current_supplements[0].dose == "125 mcg"
    assert "SAFETY-DOSE-VITD3-001" in _dose_rule_ids(request)


@pytest.mark.parametrize(
    "supplement",
    [
        SupplementInput(
            name="Daily Bone Softgel",
            dose="125000 ng",
            ingredients=["Vitamin D3"],
        ),
        SupplementInput(
            name="Daily Bone Softgel",
            ingredients=["Vitamin D3 125000 ng"],
        ),
    ],
)
def test_legacy_nanogram_product_and_ingredient_doses_use_the_same_limit(
    supplement: SupplementInput,
) -> None:
    assert "SAFETY-DOSE-VITD3-001" in _dose_rule_ids(
        _request(supplements=[supplement])
    )


def test_structured_ingredient_daily_doses_are_summed_across_products() -> None:
    request = _request(
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
        ]
    )

    intake = normalize_request(request)

    assert intake.current_supplement_product_set == {"bone daily a", "bone daily b"}
    assert "vitamin_d3" in intake.current_ingredient_set
    assert (
        intake.normalized_current_supplements[0].ingredients[0].daily_dose
        == DoseAmount(amount=2400, unit=DoseUnit.INTERNATIONAL_UNIT)
    )
    summary = assess_safety(intake)
    vitamin_d = next(
        item for item in summary.ingredient_dose_aggregates if item.ingredient_key == "vitamin_d3"
    )

    assert "SAFETY-DOSE-VITD3-001" in {
        reference.rule_id for reference in summary.rule_refs
    }
    assert summary.duplicate_ingredient_keys == ["vitamin_d3"]
    assert vitamin_d.total_daily_amount == 4400
    assert vitamin_d.unit == "iu"
    assert vitamin_d.product_count == 2
    assert vitamin_d.product_names == ["bone daily a", "bone daily b"]
    assert vitamin_d.duplicate_across_products is True
    assert vitamin_d.dose_observation_count == 2
    assert vitamin_d.dose_complete is True


def test_duplicate_ingredients_without_doses_are_reported_without_inventing_a_total() -> None:
    request = _request(
        supplements=[
            SupplementInput(name="Gut Product A", ingredients=["Probiotics"]),
            SupplementInput(name="Gut Product B", ingredients=["Probiotics"]),
        ]
    )

    summary = assess_safety(normalize_request(request))
    probiotics = next(
        item for item in summary.ingredient_dose_aggregates if item.ingredient_key == "probiotics"
    )

    assert summary.duplicate_ingredient_keys == ["probiotics"]
    assert probiotics.product_count == 2
    assert probiotics.duplicate_across_products is True
    assert probiotics.total_daily_amount is None
    assert probiotics.unit is None
    assert probiotics.dose_observation_count == 0
    assert probiotics.dose_complete is False


def test_partial_cross_product_dose_is_marked_incomplete() -> None:
    request = _request(
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
        ]
    )

    summary = assess_safety(normalize_request(request))
    vitamin_d = next(
        item for item in summary.ingredient_dose_aggregates if item.ingredient_key == "vitamin_d3"
    )

    assert vitamin_d.total_daily_amount == 2000
    assert vitamin_d.product_count == 2
    assert vitamin_d.dose_observation_count == 1
    assert vitamin_d.duplicate_across_products is True
    assert vitamin_d.dose_complete is False


def test_multiple_same_ingredient_lines_in_one_product_are_not_cross_product_duplicates() -> None:
    request = _request(
        supplements=[
            SupplementInput(
                name="One Bone Product",
                ingredients=["Vitamin D3 1000 IU", "Vitamin D3 500 IU"],
            )
        ]
    )

    summary = assess_safety(normalize_request(request))
    vitamin_d = next(
        item for item in summary.ingredient_dose_aggregates if item.ingredient_key == "vitamin_d3"
    )

    assert summary.duplicate_ingredient_keys == []
    assert vitamin_d.total_daily_amount == 1500
    assert vitamin_d.product_count == 1
    assert vitamin_d.dose_observation_count == 2
    assert vitamin_d.duplicate_across_products is False
    assert vitamin_d.dose_complete is True


def test_structured_doses_are_summed_for_ingredients_without_a_dose_limit() -> None:
    request = _request(
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
        ]
    )

    summary = assess_safety(normalize_request(request))
    omega3 = next(
        item for item in summary.ingredient_dose_aggregates if item.ingredient_key == "omega3"
    )

    assert omega3.total_daily_amount == 1500
    assert omega3.unit == "mg"
    assert omega3.product_count == 2
    assert omega3.dose_observation_count == 2
    assert omega3.duplicate_across_products is True
    assert omega3.dose_complete is True


def test_undosed_duplicate_line_in_one_product_marks_the_total_incomplete() -> None:
    request = _request(
        supplements=[
            SupplementInput(
                name="Bone Product",
                ingredients=["Vitamin D3 1000 IU", "Vitamin D3"],
            )
        ]
    )

    summary = assess_safety(normalize_request(request))
    vitamin_d = next(
        item for item in summary.ingredient_dose_aggregates if item.ingredient_key == "vitamin_d3"
    )

    assert vitamin_d.total_daily_amount == 1000
    assert vitamin_d.dose_observation_count == 1
    assert vitamin_d.dose_complete is False


def test_warfarin_omega3_policy_returns_exact_reference_and_claim_ids() -> None:
    request = _request(
        medications=[MedicationInput(name="warfarin")],
        supplements=[SupplementInput(name="Fish Oil", ingredients=["Omega-3"])],
    )

    summary = assess_safety(normalize_request(request))
    rule = next(item for item in summary.rule_refs if item.rule_id == "SAFETY-ANTICOAG-001")

    assert rule.source == "evidence_linked_policy"
    assert rule.reference_ids == ["REF-NIH-ODS-OMEGA3-001"]
    assert rule.claim_ids == ["CLM-NIH-ODS-OMEGA3-WARFARIN-001"]
    assert [citation.reference_id for citation in rule.citations] == [
        "REF-NIH-ODS-OMEGA3-001"
    ]
    assert [citation.claim_id for citation in rule.citations] == [
        "CLM-NIH-ODS-OMEGA3-WARFARIN-001"
    ]


@pytest.mark.parametrize(
    ("amount", "unit"),
    [(0.125, "mg"), (125000, "ng"), (5000, "IU")],
)
def test_structured_daily_dose_units_are_converted_before_limit_comparison(
    amount: float,
    unit: str,
) -> None:
    request = _request(
        supplements=[
            SupplementInput(
                name="Vitamin D product",
                ingredients=[
                    SupplementIngredientInput(
                        name="Vitamin D3",
                        daily_dose=DoseAmount(amount=amount, unit=unit),
                    )
                ],
            )
        ]
    )

    assert "SAFETY-DOSE-VITD3-001" in _dose_rule_ids(request)


def test_product_daily_dose_is_not_assigned_to_multiple_ingredients() -> None:
    request = _request(
        supplements=[
            SupplementInput(
                name="Multi nutrient product",
                daily_dose=DoseAmount(amount=5000, unit="IU"),
                ingredients=["Vitamin D3", "Probiotics"],
            )
        ]
    )

    assert _dose_rule_ids(request) == set()


@pytest.mark.parametrize(
    "supplement",
    [
        SupplementInput(
            name="Multi nutrient product",
            daily_dose=DoseAmount(amount=5000, unit="IU"),
            ingredients=["Vitamin D3 + Probiotics"],
        ),
        SupplementInput(
            name="Vitamin D3 + Probiotics",
            daily_dose=DoseAmount(amount=5000, unit="IU"),
            ingredients=[],
        ),
        SupplementInput(
            name="Multi nutrient product",
            dose="5000 IU",
            ingredients=["Vitamin D3 and Zinc"],
        ),
    ],
)
def test_product_dose_is_not_assigned_from_compound_legacy_text(
    supplement: SupplementInput,
) -> None:
    assert _dose_rule_ids(_request(supplements=[supplement])) == set()


def test_structured_and_legacy_ingredient_lines_are_both_counted() -> None:
    request = _request(
        supplements=[
            SupplementInput(
                name="Mixed input product",
                ingredients=[
                    SupplementIngredientInput(
                        name="Vitamin D3",
                        daily_dose=DoseAmount(amount=2400, unit="IU"),
                    ),
                    "Vitamin D3 2400 IU",
                ],
            )
        ]
    )

    assert "SAFETY-DOSE-VITD3-001" in _dose_rule_ids(request)


def test_ambiguous_legacy_and_structured_product_dose_is_rejected() -> None:
    with pytest.raises(ValidationError, match="dose and daily_dose cannot both be provided"):
        SupplementInput(
            name="Vitamin D product",
            dose="5000 IU",
            daily_dose=DoseAmount(amount=5000, unit="IU"),
            ingredients=["Vitamin D3"],
        )

    with pytest.raises(ValidationError):
        MedicationInput(
            name="Metformin",
            dose=DoseAmount(amount=0, unit="mg"),
        )


def test_structured_names_and_classification_reach_existing_model_feature_paths() -> None:
    request = _request(
        medications=[
            MedicationInput.model_validate(
                {
                    "name": "Metformin",
                    "classification": {"code": "A10BA02", "system": "ATC"},
                    "dose": {"amount": 500, "unit": "mg"},
                }
            )
        ],
        supplements=[
            SupplementInput(
                name="Daily Bone Softgel",
                ingredients=[
                    SupplementIngredientInput(
                        name="Vitamin D3",
                        daily_dose=DoseAmount(amount=2000, unit="IU"),
                    )
                ],
            )
        ],
    )
    efficacy_features = build_runtime_efficacy_feature_dict(
        request=request,
        follow_up_step=0,
        day_index=0,
        baseline_recommendations=[],
        adherence_proxy=1.0,
    )
    policy_features = build_runtime_policy_feature_dict(
        request=request,
        follow_up_step=0,
        day_index=0,
        baseline_recommendations=[],
        expected_effect_proxy=0.0,
        adherence_proxy=1.0,
        risk_tier="low",
        adverse_event=False,
        closed_loop_state="baseline",
        safety_status="ok",
    )

    for features in (efficacy_features, policy_features):
        assert features["medication::metformin"] == 1.0
        assert features["medication_classification::atc::a10ba02"] == 1.0
        assert features["current_ingredient::vitamin_d3"] == 1.0
        assert all("SupplementIngredientInput" not in key for key in features)

    expected_feature_names = ["current_ingredient::vitamin_d3"]
    efficacy_vector = EfficacyFeatureVectorizer(expected_feature_names).transform(
        [efficacy_features]
    )[0]
    policy_vector = PolicyFeatureVectorizer(expected_feature_names).transform(
        [policy_features]
    )[0]

    assert efficacy_vector == [1.0]
    assert policy_vector == [1.0]


def test_medication_classification_system_prevents_cross_system_code_collisions() -> None:
    request = _request(
        medications=[
            MedicationInput.model_validate(
                {
                    "name": "Medication A",
                    "classification": {"code": "123", "system": "ATC"},
                }
            ),
            MedicationInput.model_validate(
                {
                    "name": "Medication B",
                    "classification": {"code": "123", "system": "RxNorm"},
                }
            ),
        ]
    )

    intake = normalize_request(request)
    features = build_runtime_efficacy_feature_dict(
        request=request,
        follow_up_step=0,
        day_index=0,
        baseline_recommendations=[],
        adherence_proxy=1.0,
    )

    assert intake.medication_classification_set == {"atc::123", "rxnorm::123"}
    assert features["medication_classification::atc::123"] == 1.0
    assert features["medication_classification::rxnorm::123"] == 1.0
