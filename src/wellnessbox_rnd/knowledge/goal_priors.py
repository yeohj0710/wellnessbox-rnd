from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.domain.loaders import load_ingredient_catalog, repo_root
from wellnessbox_rnd.domain.models import IngredientCatalogItem
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.schemas.recommendation import RecommendationGoal

GOAL_PRIOR_SCHEMA_VERSION = "goal_ingredient_priors_v1"
DEFAULT_GOAL_PRIOR_PATH = Path("data/knowledge/goal_ingredient_priors_v1.json")
GOAL_PRIOR_POLICY_REFERENCE_ID = "REF-MC-GOAL-PRIOR-001"
GOAL_PRIOR_POLICY_CLAIM_ID = "CLM-MC-GOAL-PRIOR-POLICY-001"
GOAL_PRIOR_POLICY_CLAIM_TYPE = "candidate_prior_policy"


class EvidenceStrength(StrEnum):
    POLICY_ONLY = "policy_only"
    NULL_WITHOUT_DEFICIENCY = "null_without_deficiency"
    INCONCLUSIVE = "inconclusive"
    MIXED = "mixed"
    LIMITED = "limited"
    NUTRIENT_ADEQUACY = "nutrient_adequacy"
    MODERATE = "moderate"


class EvidenceDirection(StrEnum):
    SUPPORTS_CANDIDATE = "supports_candidate"
    EXPLORATORY_ONLY = "exploratory_only"
    SELECTION_POLICY_ONLY = "selection_policy_only"


GOAL_PRIOR_CLINICAL_CLAIM_CONTRACTS: dict[str, tuple[EvidenceStrength, EvidenceDirection]] = {
    "null_goal_evidence_without_deficiency": (
        EvidenceStrength.NULL_WITHOUT_DEFICIENCY,
        EvidenceDirection.EXPLORATORY_ONLY,
    ),
    "inconclusive_goal_evidence": (
        EvidenceStrength.INCONCLUSIVE,
        EvidenceDirection.EXPLORATORY_ONLY,
    ),
    "mixed_goal_evidence": (
        EvidenceStrength.MIXED,
        EvidenceDirection.EXPLORATORY_ONLY,
    ),
    "limited_goal_evidence": (
        EvidenceStrength.LIMITED,
        EvidenceDirection.SUPPORTS_CANDIDATE,
    ),
    "nutrient_adequacy_goal_evidence": (
        EvidenceStrength.NUTRIENT_ADEQUACY,
        EvidenceDirection.SUPPORTS_CANDIDATE,
    ),
    "moderate_goal_evidence": (
        EvidenceStrength.MODERATE,
        EvidenceDirection.SUPPORTS_CANDIDATE,
    ),
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoalPriorScoreScale(_StrictModel):
    minimum: float = 0.0
    maximum: float = 35.0
    standard_goal_prior: float = 35.0
    general_wellness_prior: float = 18.0
    meaning: str = Field(min_length=1)


class GoalIngredientPriorRecord(_StrictModel):
    ingredient_key: str = Field(min_length=1)
    goal_key: RecommendationGoal
    prior_score: float = Field(ge=0.0, le=35.0)
    evidence_strength: EvidenceStrength
    evidence_direction: EvidenceDirection
    reference_ids: list[str] = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


class GoalIngredientPriorRegistry(_StrictModel):
    schema_version: str
    prior_version: str = Field(min_length=1)
    effective_at: str = Field(min_length=1)
    score_scale: GoalPriorScoreScale
    records: list[GoalIngredientPriorRecord] = Field(min_length=1)


def load_goal_prior_registry(
    path: str | Path | None = None,
) -> GoalIngredientPriorRegistry:
    resolved = Path(path) if path is not None else repo_root() / DEFAULT_GOAL_PRIOR_PATH
    return GoalIngredientPriorRegistry.model_validate_json(resolved.read_text(encoding="utf-8"))


def validate_goal_prior_registry(
    registry: GoalIngredientPriorRegistry,
    *,
    reference_artifact: KnowledgeBaseArtifact,
    catalog: list[IngredientCatalogItem] | None = None,
) -> list[str]:
    issues: list[str] = []
    if registry.schema_version != GOAL_PRIOR_SCHEMA_VERSION:
        issues.append(f"unsupported_goal_prior_schema:{registry.schema_version}")
    if (
        registry.score_scale.minimum != 0.0
        or registry.score_scale.maximum != 35.0
        or registry.score_scale.standard_goal_prior != 35.0
        or registry.score_scale.general_wellness_prior != 18.0
    ):
        issues.append("goal_prior_score_scale_policy_mismatch")

    catalog_by_key = {
        item.key: item for item in (catalog if catalog is not None else load_ingredient_catalog())
    }
    references = {item.reference_id for item in reference_artifact.references}
    claims = {item.claim_id: item for item in reference_artifact.parsed_claims}
    seen_pairs: set[tuple[str, RecommendationGoal]] = set()
    covered_goals: set[RecommendationGoal] = set()
    expected_pairs = {
        (item.key, goal) for item in catalog_by_key.values() for goal in item.supported_goals
    }

    for record in registry.records:
        pair = (record.ingredient_key, record.goal_key)
        label = f"{record.ingredient_key}:{record.goal_key.value}"
        if pair in seen_pairs:
            issues.append(f"duplicate_goal_prior:{label}")
        seen_pairs.add(pair)
        covered_goals.add(record.goal_key)

        catalog_item = catalog_by_key.get(record.ingredient_key)
        if catalog_item is None:
            issues.append(f"unknown_goal_prior_ingredient:{record.ingredient_key}")
        elif record.goal_key not in catalog_item.supported_goals:
            issues.append(f"goal_prior_not_in_catalog_scope:{label}")

        expected_score = (
            registry.score_scale.general_wellness_prior
            if record.goal_key == RecommendationGoal.GENERAL_WELLNESS
            else registry.score_scale.standard_goal_prior
        )
        if record.prior_score != expected_score:
            issues.append(
                f"goal_prior_score_policy_mismatch:{label}:{record.prior_score}!={expected_score}"
            )
        if (
            record.evidence_strength
            in {
                EvidenceStrength.NULL_WITHOUT_DEFICIENCY,
                EvidenceStrength.INCONCLUSIVE,
                EvidenceStrength.MIXED,
            }
            and record.evidence_direction != EvidenceDirection.EXPLORATORY_ONLY
        ):
            issues.append(f"weak_goal_prior_must_be_exploratory:{label}")
        if (
            record.evidence_strength == EvidenceStrength.POLICY_ONLY
            and record.evidence_direction != EvidenceDirection.SELECTION_POLICY_ONLY
        ):
            issues.append(f"policy_goal_prior_direction_mismatch:{label}")

        declared_references = set(record.reference_ids)
        if len(declared_references) != len(record.reference_ids):
            issues.append(f"duplicate_goal_prior_reference:{label}")
        if len(set(record.claim_ids)) != len(record.claim_ids):
            issues.append(f"duplicate_goal_prior_claim:{label}")
        if GOAL_PRIOR_POLICY_REFERENCE_ID not in declared_references:
            issues.append(f"missing_goal_prior_policy_reference:{label}")
        if GOAL_PRIOR_POLICY_CLAIM_ID not in record.claim_ids:
            issues.append(f"missing_goal_prior_policy_claim:{label}")
        for reference_id in record.reference_ids:
            if not reference_id.strip():
                issues.append(f"empty_goal_prior_reference:{label}")
            elif reference_id not in references:
                issues.append(f"missing_goal_prior_reference:{label}:{reference_id}")
        clinical_contracts: set[tuple[EvidenceStrength, EvidenceDirection]] = set()
        claim_owned_references: set[str] = set()
        for claim_id in record.claim_ids:
            if not claim_id.strip():
                issues.append(f"empty_goal_prior_claim:{label}")
                continue
            claim = claims.get(claim_id)
            if claim is None:
                issues.append(f"missing_goal_prior_claim:{label}:{claim_id}")
                continue
            claim_owned_references.add(claim.reference_id)
            if claim.reference_id not in declared_references:
                issues.append(
                    f"goal_prior_claim_reference_mismatch:{label}:{claim_id}:{claim.reference_id}"
                )
            if claim_id == GOAL_PRIOR_POLICY_CLAIM_ID:
                if (
                    claim.reference_id != GOAL_PRIOR_POLICY_REFERENCE_ID
                    or claim.normalized_claim_type != GOAL_PRIOR_POLICY_CLAIM_TYPE
                    or claim.ingredient_keys
                    or claim.domain_keys != [GOAL_PRIOR_POLICY_CLAIM_TYPE]
                ):
                    issues.append(f"invalid_goal_prior_policy_claim:{label}:{claim_id}")
                continue
            if claim.normalized_claim_type == GOAL_PRIOR_POLICY_CLAIM_TYPE:
                issues.append(f"unexpected_goal_prior_policy_claim:{label}:{claim_id}")
            if record.ingredient_key not in claim.ingredient_keys:
                issues.append(f"goal_prior_claim_ingredient_mismatch:{label}:{claim_id}")
            if record.goal_key.value not in claim.domain_keys:
                issues.append(f"goal_prior_claim_domain_mismatch:{label}:{claim_id}")
            contract = GOAL_PRIOR_CLINICAL_CLAIM_CONTRACTS.get(claim.normalized_claim_type)
            if contract is None:
                issues.append(
                    f"unsupported_goal_prior_claim_type:{label}:{claim_id}:"
                    f"{claim.normalized_claim_type}"
                )
            else:
                clinical_contracts.add(contract)

        for reference_id in sorted(declared_references - claim_owned_references):
            issues.append(f"unclaimed_goal_prior_reference:{label}:{reference_id}")
        for reference_id in sorted(claim_owned_references - declared_references):
            issues.append(f"undeclared_goal_prior_claim_reference:{label}:{reference_id}")

        expected_contract = (
            (EvidenceStrength.POLICY_ONLY, EvidenceDirection.SELECTION_POLICY_ONLY)
            if not clinical_contracts
            else next(iter(clinical_contracts))
            if len(clinical_contracts) == 1
            else None
        )
        if expected_contract is None:
            issues.append(f"conflicting_goal_prior_evidence_claims:{label}")
        elif (
            record.evidence_strength,
            record.evidence_direction,
        ) != expected_contract:
            issues.append(
                f"goal_prior_evidence_contract_mismatch:{label}:"
                f"{record.evidence_strength.value}:{record.evidence_direction.value}!="
                f"{expected_contract[0].value}:{expected_contract[1].value}"
            )

    for goal in RecommendationGoal:
        if goal not in covered_goals:
            issues.append(f"goal_prior_goal_uncovered:{goal.value}")
    for ingredient_key, goal in sorted(
        expected_pairs - seen_pairs,
        key=lambda pair: (pair[0], pair[1].value),
    ):
        issues.append(f"goal_prior_catalog_pair_uncovered:{ingredient_key}:{goal.value}")
    for ingredient_key, goal in sorted(
        seen_pairs - expected_pairs,
        key=lambda pair: (pair[0], pair[1].value),
    ):
        issues.append(f"goal_prior_catalog_pair_unknown:{ingredient_key}:{goal.value}")
    return issues


@lru_cache
def get_goal_prior_index() -> dict[tuple[str, RecommendationGoal], GoalIngredientPriorRecord]:
    registry = load_goal_prior_registry()
    artifact_path = repo_root() / "data" / "knowledge" / "reference_knowledge_base_v1.json"
    artifact = KnowledgeBaseArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
    issues = validate_goal_prior_registry(registry, reference_artifact=artifact)
    if issues:
        raise ValueError(f"invalid_goal_prior_registry:{','.join(issues)}")
    return {(record.ingredient_key, record.goal_key): record for record in registry.records}
