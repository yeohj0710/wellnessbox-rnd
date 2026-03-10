from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.knowledge.runtime_db import (
    build_runtime_knowledge_db,
    find_triggered_interaction_rules,
    validate_runtime_knowledge_db,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    ActivityLevel,
    BiologicalSex,
    InputAvailability,
    LifestyleInput,
    MedicationInput,
    NextAction,
    RecommendationGoal,
    RecommendationPreferences,
    RecommendationRequest,
    RecommendationStatus,
    SupplementInput,
    UserProfile,
)


def test_runtime_knowledge_db_builds_required_tables() -> None:
    runtime_db = build_runtime_knowledge_db()

    assert validate_runtime_knowledge_db(runtime_db) == []
    assert runtime_db.ingredients
    assert runtime_db.ingredient_aliases
    assert runtime_db.medications
    assert runtime_db.conditions
    assert runtime_db.interaction_rules
    assert runtime_db.contraindication_rules
    assert isinstance(runtime_db.dose_limits, list)
    assert runtime_db.ingredient_domain_scores
    assert runtime_db.references
    assert runtime_db.reference_spans
    assert runtime_db.workflow_policies
    assert any(
        rule.rule_id == "KB-SAFETY-ANTICOAG-001" and rule.source_kind == "knowledge_artifact"
        for rule in runtime_db.interaction_rules
    )


def test_runtime_knowledge_query_matches_anticoagulant_interaction() -> None:
    runtime_db = build_runtime_knowledge_db()

    matches = find_triggered_interaction_rules(
        runtime_db,
        medication_keys={"warfarin"},
        ingredient_keys={"glucosamine"},
    )

    assert [rule.rule_id for rule in matches] == ["KB-SAFETY-ANTICOAG-001"]


def test_assess_safety_returns_citation_backed_structured_knowledge_rule() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=58,
            biological_sex=BiologicalSex.MALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.HEART_HEALTH],
        symptoms=["low_activity_tolerance"],
        medications=[MedicationInput(name="warfarin", dose="5mg")],
        current_supplements=[SupplementInput(name="glucosamine")],
        lifestyle=LifestyleInput(
            sleep_hours=7.0,
            stress_level=2,
            activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        ),
        input_availability=InputAvailability(
            survey=True,
            nhis=False,
            wearable=False,
            cgm=False,
            genetic=False,
        ),
        preferences=RecommendationPreferences(),
    )

    summary = assess_safety(normalize_request(request))

    assert summary.status == RecommendationStatus.BLOCKED
    assert "glucosamine" in summary.excluded_ingredients
    knowledge_rule = next(
        item for item in summary.rule_refs if item.rule_id == "KB-SAFETY-ANTICOAG-001"
    )
    assert knowledge_rule.reference_ids == ["REF-KNOWLEDGE-ANTICOAG-001"]
    assert knowledge_rule.claim_ids == ["CLM-KNOWLEDGE-ANTICOAG-001"]
    assert knowledge_rule.citations[0].reference_id == "REF-KNOWLEDGE-ANTICOAG-001"
    assert knowledge_rule.citations[0].claim_id == "CLM-KNOWLEDGE-ANTICOAG-001"

    response = recommend(request)

    assert response.next_action == NextAction.TRIGGER_SAFETY_RECHECK
    assert response.next_action_rationale.reason_code == "structured_safety_blocker"
