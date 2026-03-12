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
    assert runtime_db.dose_limits
    assert runtime_db.ingredient_domain_scores
    assert runtime_db.references
    assert runtime_db.reference_spans
    assert runtime_db.workflow_policies
    assert any(
        rule.rule_id == "KB-SAFETY-ANTICOAG-001" and rule.source_kind == "knowledge_artifact"
        for rule in runtime_db.interaction_rules
    )


def test_runtime_knowledge_db_builds_structured_dose_limits() -> None:
    runtime_db = build_runtime_knowledge_db()

    assert [record.rule_id for record in runtime_db.dose_limits] == [
        "SAFETY-DOSE-VITD3-001",
        "SAFETY-DOSE-VITC-001",
        "SAFETY-DOSE-ZINC-001",
        "SAFETY-DOSE-MAG-001",
        "SAFETY-DOSE-CAL-001",
    ]
    vitamin_d3_limit = next(
        record for record in runtime_db.dose_limits if record.ingredient_key == "vitamin_d3"
    )
    assert vitamin_d3_limit.max_daily_amount == 4000
    assert vitamin_d3_limit.unit == "iu"
    assert vitamin_d3_limit.severity.value == "blocker"
    magnesium_limit = next(
        record
        for record in runtime_db.dose_limits
        if record.ingredient_key == "magnesium_glycinate"
    )
    assert magnesium_limit.max_daily_amount == 350
    assert magnesium_limit.allowed_evidence_sources == ["structured_dose", "ingredient_line"]
    calcium_limit = next(
        record for record in runtime_db.dose_limits if record.ingredient_key == "calcium_citrate"
    )
    assert calcium_limit.max_daily_amount == 2000
    assert calcium_limit.allowed_evidence_sources == ["structured_dose", "ingredient_line"]


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


def test_assess_safety_blocks_current_regimen_when_structured_dose_limit_is_exceeded() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=41,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.BONE_JOINT],
        symptoms=["low_sun_exposure"],
        medications=[],
        current_supplements=[SupplementInput(name="Vitamin D3 5000 IU")],
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
    assert "vitamin_d3" in summary.excluded_ingredients
    assert any("5000 iu" in warning.lower() for warning in summary.warnings)
    dose_rule = next(item for item in summary.rule_refs if item.rule_id == "SAFETY-DOSE-VITD3-001")
    assert dose_rule.severity.value == "blocker"

    response = recommend(request)

    assert response.next_action == NextAction.TRIGGER_SAFETY_RECHECK
    assert response.next_action_rationale.reason_code == "structured_safety_blocker"


def test_assess_safety_blocks_vitamin_d3_when_ingredient_line_uses_mcg() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=41,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.BONE_JOINT],
        symptoms=["low_sun_exposure"],
        medications=[],
        current_supplements=[
            SupplementInput(
                name="Daily Bone Softgel",
                ingredients=["Vitamin D3 125 mcg"],
            )
        ],
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
    assert "vitamin_d3" in summary.excluded_ingredients
    assert any("5000 iu" in warning.lower() for warning in summary.warnings)

    response = recommend(request)

    assert response.next_action == NextAction.TRIGGER_SAFETY_RECHECK
    assert response.next_action_rationale.reason_code == "structured_safety_blocker"


def test_assess_safety_blocks_zinc_when_title_uses_mcg_mass_units() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=37,
            biological_sex=BiologicalSex.MALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.IMMUNITY_SUPPORT],
        symptoms=["frequent_colds"],
        medications=[],
        current_supplements=[SupplementInput(name="Zinc 50000 mcg", ingredients=[])],
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
    assert "zinc" in summary.excluded_ingredients
    assert any("50 mg" in warning.lower() for warning in summary.warnings)


def test_assess_safety_blocks_magnesium_when_ingredient_line_exceeds_structured_limit() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=34,
            biological_sex=BiologicalSex.MALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.SLEEP_SUPPORT],
        symptoms=["difficulty_falling_asleep"],
        medications=[],
        current_supplements=[
            SupplementInput(
                name="Night Mineral",
                ingredients=["Magnesium Glycinate 400 mg"],
            )
        ],
        lifestyle=LifestyleInput(
            sleep_hours=6.0,
            stress_level=3,
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
    assert "magnesium_glycinate" in summary.excluded_ingredients
    assert any("400 mg" in warning.lower() for warning in summary.warnings)
    assert any(rule.rule_id == "SAFETY-DOSE-MAG-001" for rule in summary.rule_refs)

    response = recommend(request)

    assert response.next_action == NextAction.TRIGGER_SAFETY_RECHECK
    assert response.next_action_rationale.reason_code == "structured_safety_blocker"


def test_assess_safety_skips_title_only_magnesium_dose_limit_when_rule_requires_stronger_evidence(
) -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=34,
            biological_sex=BiologicalSex.MALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.SLEEP_SUPPORT],
        symptoms=["difficulty_falling_asleep"],
        medications=[],
        current_supplements=[SupplementInput(name="Magnesium Glycinate 400 mg", ingredients=[])],
        lifestyle=LifestyleInput(
            sleep_hours=6.0,
            stress_level=3,
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

    assert summary.status == RecommendationStatus.OK
    assert "magnesium_glycinate" in summary.excluded_ingredients
    assert [rule.rule_id for rule in summary.rule_refs] == ["SAFETY-DUP-001"]
    assert not any(rule.rule_id == "SAFETY-DOSE-MAG-001" for rule in summary.rule_refs)


def test_assess_safety_blocks_calcium_when_structured_dose_exceeds_limit() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=52,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.BONE_JOINT],
        symptoms=["low_sun_exposure"],
        medications=[],
        current_supplements=[
            SupplementInput(
                name="Bone Support",
                dose="2100 mg",
                ingredients=["Calcium Citrate"],
            )
        ],
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
    assert "calcium_citrate" in summary.excluded_ingredients
    assert any("2100 mg" in warning.lower() for warning in summary.warnings)
    assert any(rule.rule_id == "SAFETY-DOSE-CAL-001" for rule in summary.rule_refs)

    response = recommend(request)

    assert response.next_action == NextAction.TRIGGER_SAFETY_RECHECK
    assert response.next_action_rationale.reason_code == "structured_safety_blocker"


def test_assess_safety_blocks_when_structured_supplement_dose_is_explicit() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=45,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.BONE_JOINT],
        symptoms=["low_sun_exposure"],
        medications=[],
        current_supplements=[
            SupplementInput(
                name="Daily Bone Softgel",
                dose="125 mcg",
                ingredients=["Vitamin D3"],
            )
        ],
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
    assert "vitamin_d3" in summary.excluded_ingredients
    assert any("5000 iu" in warning.lower() for warning in summary.warnings)

    response = recommend(request)

    assert response.next_action == NextAction.TRIGGER_SAFETY_RECHECK
    assert response.next_action_rationale.reason_code == "structured_safety_blocker"


def test_structured_supplement_dose_skips_ambiguous_ingredient_mapping() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=39,
            biological_sex=BiologicalSex.MALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.IMMUNITY_SUPPORT],
        symptoms=["frequent_colds"],
        medications=[],
        current_supplements=[
            SupplementInput(
                name="Immune Combo",
                dose="5000 mg",
                ingredients=["Vitamin C", "Zinc"],
            )
        ],
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

    assert summary.status == RecommendationStatus.OK
    assert "vitamin_c" in summary.excluded_ingredients
    assert "zinc" in summary.excluded_ingredients
    assert [rule.rule_id for rule in summary.rule_refs] == ["SAFETY-DUP-001"]
    assert not any(rule.rule_id.startswith("SAFETY-DOSE-") for rule in summary.rule_refs)
