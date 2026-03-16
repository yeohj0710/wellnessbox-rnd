from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas import (
    build_structured_safety_evidence_event_v1,
    validate_structured_safety_evidence_event_v1,
)
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest


def test_structured_safety_evidence_event_preserves_deterministic_dose_boundary() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {
                    "name": "Daily Bone Softgel",
                    "dose": "125 mcg",
                    "ingredients": ["Vitamin D3"],
                }
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )

    event = build_structured_safety_evidence_event_v1(recommend(request))

    dose_rule = next(item for item in event.rule_links if item.rule_id == "SAFETY-DOSE-VITD3-001")

    assert dose_rule.source == "deterministic_policy"
    assert dose_rule.reference_ids == []
    assert dose_rule.claim_ids == []
    assert dose_rule.citation_reference_ids == []
    assert dose_rule.citation_claim_ids == []
    assert validate_structured_safety_evidence_event_v1(event) == []


def test_structured_safety_evidence_event_preserves_knowledge_backed_rule_linkage() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 58,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity_tolerance"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [{"name": "glucosamine"}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )

    event = build_structured_safety_evidence_event_v1(recommend(request))

    knowledge_rule = next(
        item
        for item in event.rule_links
        if item.rule_id == "KB-SAFETY-ANTICOAG-001"
    )

    assert knowledge_rule.reference_ids == ["REF-KNOWLEDGE-ANTICOAG-001"]
    assert knowledge_rule.claim_ids == ["CLM-KNOWLEDGE-ANTICOAG-001"]
    assert knowledge_rule.citation_reference_ids == ["REF-KNOWLEDGE-ANTICOAG-001"]
    assert knowledge_rule.citation_claim_ids == ["CLM-KNOWLEDGE-ANTICOAG-001"]
    assert validate_structured_safety_evidence_event_v1(event) == []


def test_safety_event_validator_flags_missing_rule_evidence_and_reference_mismatch(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 58,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity_tolerance"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [{"name": "glucosamine"}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )

    event = build_structured_safety_evidence_event_v1(recommend(request)).model_dump(mode="json")
    event["evidence_items"] = [
        item for item in event["evidence_items"] if item["code"] != "KB-SAFETY-ANTICOAG-001"
    ]
    event["rule_links"][0]["reference_ids"] = ["REF-MISMATCH-001"]

    issues = validate_structured_safety_evidence_event_v1(event)

    assert "missing_rule_evidence::KB-SAFETY-ANTICOAG-001" in issues
    assert "citation_reference_mismatch::SAFETY-ANTICOAG-001" in issues
