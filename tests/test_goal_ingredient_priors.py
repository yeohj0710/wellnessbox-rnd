from __future__ import annotations

from pathlib import Path

from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.efficacy.service import score_candidate
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.knowledge.goal_priors import (
    EvidenceDirection,
    EvidenceStrength,
    load_goal_prior_registry,
    validate_goal_prior_registry,
)
from wellnessbox_rnd.knowledge.runtime_db import (
    RuntimeKnowledgeDB,
    build_runtime_knowledge_db,
    validate_runtime_knowledge_db,
)
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)


def _artifact() -> KnowledgeBaseArtifact:
    return KnowledgeBaseArtifact.model_validate_json(
        Path("data/knowledge/reference_knowledge_base_v1.json").read_text(encoding="utf-8")
    )


def test_current_goal_prior_registry_is_evidence_linked_and_covers_every_goal() -> None:
    registry = load_goal_prior_registry()

    assert (
        validate_goal_prior_registry(
            registry,
            reference_artifact=_artifact(),
        )
        == []
    )
    assert {record.goal_key for record in registry.records} == set(RecommendationGoal)
    assert all(record.reference_ids for record in registry.records)
    assert all(record.claim_ids for record in registry.records)
    assert all(record.limitations for record in registry.records)


def test_goal_prior_validation_rejects_score_outside_versioned_policy() -> None:
    registry = load_goal_prior_registry().model_copy(deep=True)
    target = next(
        record
        for record in registry.records
        if record.evidence_strength == EvidenceStrength.INCONCLUSIVE
    )
    target.prior_score = 34.0

    assert any(
        issue.startswith("goal_prior_score_policy_mismatch:coq10:heart_health")
        for issue in validate_goal_prior_registry(
            registry,
            reference_artifact=_artifact(),
        )
    )


def test_goal_prior_validation_rejects_claim_from_another_reference() -> None:
    registry = load_goal_prior_registry().model_copy(deep=True)
    target = next(
        record
        for record in registry.records
        if record.ingredient_key == "omega3" and record.goal_key == RecommendationGoal.HEART_HEALTH
    )
    target.reference_ids = [
        "REF-MC-GOAL-PRIOR-001",
        "REF-NCCIH-COQ10-HEART-001",
    ]

    assert (
        "goal_prior_claim_reference_mismatch:omega3:heart_health:"
        "CLM-NIH-ODS-OMEGA3-HEART-001:REF-NIH-ODS-OMEGA3-HEART-001"
        in validate_goal_prior_registry(
            registry,
            reference_artifact=_artifact(),
        )
    )


def test_goal_prior_validation_rejects_clinical_strength_without_clinical_claim() -> None:
    registry = load_goal_prior_registry().model_copy(deep=True)
    target = next(
        record
        for record in registry.records
        if record.ingredient_key == "coq10" and record.goal_key == RecommendationGoal.ENERGY_SUPPORT
    )
    target.evidence_strength = EvidenceStrength.MODERATE
    target.evidence_direction = EvidenceDirection.SUPPORTS_CANDIDATE

    assert any(
        issue.startswith("goal_prior_evidence_contract_mismatch:coq10:energy_support")
        for issue in validate_goal_prior_registry(
            registry,
            reference_artifact=_artifact(),
        )
    )


def test_goal_prior_validation_rejects_forged_policy_claim_type() -> None:
    registry = load_goal_prior_registry().model_copy(deep=True)
    artifact = _artifact().model_copy(deep=True)
    claim = next(
        item for item in artifact.parsed_claims if item.claim_id == "CLM-NCCIH-COQ10-HEART-001"
    )
    claim.normalized_claim_type = "candidate_prior_policy"

    issues = validate_goal_prior_registry(registry, reference_artifact=artifact)

    assert any(
        issue.startswith(
            "unexpected_goal_prior_policy_claim:coq10:heart_health:CLM-NCCIH-COQ10-HEART-001"
        )
        for issue in issues
    )
    assert any(
        issue.startswith(
            "unsupported_goal_prior_claim_type:coq10:heart_health:CLM-NCCIH-COQ10-HEART-001"
        )
        for issue in issues
    )


def test_goal_prior_validation_rejects_reference_without_owned_claim() -> None:
    registry = load_goal_prior_registry().model_copy(deep=True)
    target = next(
        record
        for record in registry.records
        if record.ingredient_key == "omega3"
        and record.goal_key == RecommendationGoal.HEART_HEALTH
    )
    target.reference_ids.append("REF-NCCIH-COQ10-HEART-001")

    issues = validate_goal_prior_registry(registry, reference_artifact=_artifact())

    assert (
        "unclaimed_goal_prior_reference:omega3:heart_health:"
        "REF-NCCIH-COQ10-HEART-001" in issues
    )


def test_runtime_goal_prior_validation_rejects_reference_without_owned_claim() -> None:
    runtime_db = build_runtime_knowledge_db()
    target = next(
        record
        for record in runtime_db.goal_ingredient_priors
        if record.ingredient_key == "omega3"
        and record.goal_key == RecommendationGoal.HEART_HEALTH
    )
    target.reference_ids.append("REF-NCCIH-COQ10-HEART-001")

    issues = validate_runtime_knowledge_db(runtime_db)

    assert (
        "unclaimed_goal_prior_reference:omega3:heart_health:"
        "REF-NCCIH-COQ10-HEART-001" in issues
    )


def test_runtime_goal_priors_preserve_claim_scope_and_validate() -> None:
    runtime_db = build_runtime_knowledge_db()

    assert validate_runtime_knowledge_db(runtime_db) == []
    assert len(runtime_db.goal_ingredient_priors) == 24
    omega3 = next(
        record
        for record in runtime_db.goal_ingredient_priors
        if record.ingredient_key == "omega3" and record.goal_key == RecommendationGoal.HEART_HEALTH
    )
    assert omega3.goal_key == RecommendationGoal.HEART_HEALTH
    assert omega3.prior_score == 35.0
    assert omega3.reference_ids == [
        "REF-MC-GOAL-PRIOR-001",
        "REF-NIH-ODS-OMEGA3-HEART-001",
    ]


def test_stored_runtime_db_matches_fresh_builder() -> None:
    stored = RuntimeKnowledgeDB.model_validate_json(
        Path("data/knowledge/runtime_knowledge_db_v1.json").read_text(encoding="utf-8")
    )
    fresh = build_runtime_knowledge_db()
    repeated = build_runtime_knowledge_db()

    assert stored.model_dump(mode="json") == fresh.model_dump(mode="json")
    assert repeated.model_dump(mode="json") == fresh.model_dump(mode="json")


def test_candidate_goal_alignment_uses_registered_prior_scores() -> None:
    intake = normalize_request(
        RecommendationRequest(
            user_profile=UserProfile(
                age=41,
                biological_sex=BiologicalSex.MALE,
                pregnant=False,
            ),
            goals=[RecommendationGoal.HEART_HEALTH],
        )
    )
    catalog = get_catalog_index()

    omega3 = score_candidate(catalog["omega3"], intake, safety_review=False)
    coq10 = score_candidate(catalog["coq10"], intake, safety_review=False)

    assert omega3.goal_alignment == 35.0
    assert coq10.goal_alignment == 35.0


def test_weak_or_null_evidence_is_exploratory_only() -> None:
    registry = load_goal_prior_registry()
    weak_strengths = {
        EvidenceStrength.NULL_WITHOUT_DEFICIENCY,
        EvidenceStrength.INCONCLUSIVE,
        EvidenceStrength.MIXED,
    }

    assert all(
        record.evidence_direction == EvidenceDirection.EXPLORATORY_ONLY
        for record in registry.records
        if record.evidence_strength in weak_strengths
    )
    assert all(
        record.evidence_direction == EvidenceDirection.SELECTION_POLICY_ONLY
        for record in registry.records
        if record.evidence_strength == EvidenceStrength.POLICY_ONLY
    )
