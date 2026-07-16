from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.domain.loaders import load_ingredient_catalog, repo_root
from wellnessbox_rnd.ingestion.reference_ingestion import (
    CitationSpan,
    KnowledgeBaseArtifact,
    ParsedReferenceClaim,
    ReferenceMetadata,
    validate_knowledge_artifact,
)
from wellnessbox_rnd.knowledge.candidate_signals import (
    CandidateSignalScoringRegistry,
    load_candidate_signal_registry,
    validate_candidate_signal_registry,
)
from wellnessbox_rnd.knowledge.goal_priors import (
    GOAL_PRIOR_CLINICAL_CLAIM_CONTRACTS,
    GOAL_PRIOR_POLICY_CLAIM_ID,
    GOAL_PRIOR_POLICY_CLAIM_TYPE,
    GOAL_PRIOR_POLICY_REFERENCE_ID,
    EvidenceDirection,
    EvidenceStrength,
    GoalIngredientPriorRecord,
    load_goal_prior_registry,
    validate_goal_prior_registry,
)
from wellnessbox_rnd.schemas.recommendation import (
    CitationReference,
    RecommendationGoal,
    Severity,
)


class IngredientRecord(BaseModel):
    ingredient_key: str
    display_name: str


class IngredientAliasRecord(BaseModel):
    ingredient_key: str
    alias: str
    source_kind: str


class MedicationRecord(BaseModel):
    medication_key: str


class ConditionRecord(BaseModel):
    condition_key: str


class InteractionRuleRecord(BaseModel):
    rule_id: str
    rule_version: int = Field(ge=1)
    source_kind: Literal["knowledge_artifact", "evidence_linked_policy"]
    severity: Severity
    medication_keys: list[str] = Field(default_factory=list)
    ingredient_keys: list[str] = Field(default_factory=list)
    message: str
    warning_text: str
    reason_code: str | None = None
    next_action: str | None = None
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class ContraindicationRuleRecord(BaseModel):
    rule_id: str
    rule_version: int = Field(ge=1)
    source_kind: str
    severity: Severity
    effect: Literal["contraindication", "review_required"] = "contraindication"
    condition_keys: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    message: str
    warning_text: str
    applies_when_pregnant: bool = False
    applies_when_lactating: bool = False
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class DoseLimitRecord(BaseModel):
    rule_id: str
    rule_version: int = Field(ge=1)
    source_kind: str
    severity: Severity
    ingredient_key: str
    max_daily_amount: float | None = None
    unit: str | None = None
    allowed_evidence_sources: list[str] = Field(
        default_factory=lambda: ["structured_dose", "ingredient_line", "title"]
    )
    message: str
    warning_text: str
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class IngredientDomainScoreRecord(BaseModel):
    ingredient_key: str
    domain_key: str
    support_score: float
    medication_keys: list[str] = Field(default_factory=list)
    normalized_claim_types: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class KnowledgeReferenceRecord(BaseModel):
    reference_id: str
    source_title: str
    source_type: str
    page_or_section: str
    reference_uri: str
    parsed_source_uri: str
    license_status: str
    effective_at: str
    retired_at: str | None = None


class ReferenceSpanRecord(BaseModel):
    span_id: str
    reference_id: str
    claim_id: str
    line_start: int
    line_end: int
    excerpt: str
    claim_text: str
    normalized_claim_type: str
    ingredient_keys: list[str] = Field(default_factory=list)
    domain_keys: list[str] = Field(default_factory=list)


class WorkflowPolicyRecord(BaseModel):
    rule_id: str
    source_kind: str
    severity: Severity
    policy_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    message: str
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class RuntimeKnowledgeDB(BaseModel):
    artifact_version: str = "runtime_knowledge_db_v1"
    source_reference_artifact_version: str
    ingredients: list[IngredientRecord] = Field(default_factory=list)
    ingredient_aliases: list[IngredientAliasRecord] = Field(default_factory=list)
    medications: list[MedicationRecord] = Field(default_factory=list)
    conditions: list[ConditionRecord] = Field(default_factory=list)
    interaction_rules: list[InteractionRuleRecord] = Field(default_factory=list)
    contraindication_rules: list[ContraindicationRuleRecord] = Field(default_factory=list)
    dose_limits: list[DoseLimitRecord] = Field(default_factory=list)
    ingredient_domain_scores: list[IngredientDomainScoreRecord] = Field(default_factory=list)
    goal_ingredient_priors: list[GoalIngredientPriorRecord] = Field(default_factory=list)
    candidate_signal_scoring: CandidateSignalScoringRegistry | None = None
    references: list[KnowledgeReferenceRecord] = Field(default_factory=list)
    reference_spans: list[ReferenceSpanRecord] = Field(default_factory=list)
    workflow_policies: list[WorkflowPolicyRecord] = Field(default_factory=list)


def build_runtime_knowledge_db(
    reference_artifact_path: str | Path | None = None,
) -> RuntimeKnowledgeDB:
    artifact = _load_reference_artifact(reference_artifact_path)
    rules_payload = _load_raw_safety_rules()
    knowledge_rule_version = _version_from_artifact_version(artifact.artifact_version)
    claim_by_id = {claim.claim_id: claim for claim in artifact.parsed_claims}
    goal_prior_registry = load_goal_prior_registry()
    goal_prior_issues = validate_goal_prior_registry(
        goal_prior_registry,
        reference_artifact=artifact,
        catalog=load_ingredient_catalog(),
    )
    if goal_prior_issues:
        raise ValueError(f"invalid_goal_prior_registry:{','.join(goal_prior_issues)}")
    candidate_signal_registry = load_candidate_signal_registry()
    candidate_signal_issues = validate_candidate_signal_registry(
        candidate_signal_registry,
        reference_artifact=artifact,
    )
    if candidate_signal_issues:
        raise ValueError(
            f"invalid_candidate_signal_registry:{','.join(candidate_signal_issues)}"
        )

    ingredient_map: dict[str, IngredientRecord] = {}
    alias_keys: set[tuple[str, str, str]] = set()
    ingredient_aliases: list[IngredientAliasRecord] = []
    for item in load_ingredient_catalog():
        ingredient_map[item.key] = IngredientRecord(
            ingredient_key=item.key,
            display_name=item.display_name,
        )
        _append_alias(
            ingredient_aliases,
            alias_keys,
            IngredientAliasRecord(
                ingredient_key=item.key,
                alias=item.key,
                source_kind="catalog",
            ),
        )
        for alias in item.aliases:
            _append_alias(
                ingredient_aliases,
                alias_keys,
                IngredientAliasRecord(
                    ingredient_key=item.key,
                    alias=alias,
                    source_kind="catalog",
                ),
            )

    medication_keys: set[str] = set()
    condition_keys: set[str] = set()
    interaction_rules: list[InteractionRuleRecord] = []
    contraindication_rules: list[ContraindicationRuleRecord] = []
    dose_limits: list[DoseLimitRecord] = []

    for raw_rule in rules_payload.get("medication_rules", []):
        medications = sorted(set(raw_rule.get("medications", [])))
        excluded_ingredients = sorted(set(raw_rule.get("excluded_ingredients", [])))
        metadata = raw_rule["metadata"]
        interaction_rules.append(
            InteractionRuleRecord(
                rule_id=metadata["rule_id"],
                rule_version=metadata["version"],
                source_kind="evidence_linked_policy",
                severity=Severity(metadata["severity"]),
                medication_keys=medications,
                ingredient_keys=excluded_ingredients,
                message=metadata["message"],
                warning_text=metadata["warning_text"],
                reference_ids=sorted(set(raw_rule.get("reference_ids", []))),
                claim_ids=sorted(set(raw_rule.get("claim_ids", []))),
            )
        )
        medication_keys.update(medications)
        _register_ingredients(
            ingredient_map,
            ingredient_aliases,
            alias_keys,
            excluded_ingredients,
            source_kind="deterministic_policy",
        )

    special_population_condition_keys = {
        "pregnant": "pregnancy",
        "lactating": "lactation",
    }
    for special_population_rule in rules_payload.get("special_population_rules", []):
        metadata = special_population_rule["metadata"]
        statuses = sorted(set(special_population_rule.get("statuses", [])))
        conditions = [special_population_condition_keys[status] for status in statuses]
        excluded_ingredients = sorted(set(special_population_rule.get("excluded_ingredients", [])))
        contraindication_rules.append(
            ContraindicationRuleRecord(
                rule_id=metadata["rule_id"],
                rule_version=metadata["version"],
                source_kind="deterministic_policy",
                severity=Severity(metadata["severity"]),
                effect="contraindication",
                condition_keys=conditions,
                excluded_ingredients=excluded_ingredients,
                message=metadata["message"],
                warning_text=metadata["warning_text"],
                applies_when_pregnant="pregnant" in statuses,
                applies_when_lactating="lactating" in statuses,
            )
        )
        condition_keys.update(conditions)
        _register_ingredients(
            ingredient_map,
            ingredient_aliases,
            alias_keys,
            excluded_ingredients,
            source_kind="deterministic_policy",
        )

    for raw_rule in rules_payload.get("condition_rules", []):
        metadata = raw_rule["metadata"]
        conditions = sorted(set(raw_rule.get("conditions", [])))
        excluded_ingredients = sorted(set(raw_rule.get("excluded_ingredients", [])))
        contraindication_rules.append(
            ContraindicationRuleRecord(
                rule_id=metadata["rule_id"],
                rule_version=metadata["version"],
                source_kind="deterministic_policy",
                severity=Severity(metadata["severity"]),
                effect=raw_rule["effect"],
                condition_keys=conditions,
                excluded_ingredients=excluded_ingredients,
                message=metadata["message"],
                warning_text=metadata["warning_text"],
            )
        )
        condition_keys.update(conditions)
        _register_ingredients(
            ingredient_map,
            ingredient_aliases,
            alias_keys,
            excluded_ingredients,
            source_kind="deterministic_policy",
        )

    for raw_rule in rules_payload.get("dose_limits", []):
        metadata = raw_rule["metadata"]
        ingredient_key = raw_rule["ingredient_key"]
        dose_limits.append(
            DoseLimitRecord(
                rule_id=metadata["rule_id"],
                rule_version=metadata["version"],
                source_kind="deterministic_policy",
                severity=Severity(metadata["severity"]),
                ingredient_key=ingredient_key,
                max_daily_amount=raw_rule.get("max_daily_amount"),
                unit=_optional_string(raw_rule.get("unit")),
                allowed_evidence_sources=_validated_dose_evidence_sources(
                    raw_rule.get("allowed_evidence_sources")
                ),
                message=metadata["message"],
                warning_text=metadata["warning_text"],
            )
        )
        _register_ingredients(
            ingredient_map,
            ingredient_aliases,
            alias_keys,
            [ingredient_key],
            source_kind="deterministic_policy",
        )

    for candidate in artifact.rule_candidates:
        claim = claim_by_id[candidate.claim_id]
        if candidate.rule_type == "block_anticoagulant_interaction":
            medications = _sorted_string_list(candidate.if_clause.get("any_medications", []))
            ingredients = _sorted_string_list(candidate.if_clause.get("any_ingredients", []))
            interaction_rules.append(
                InteractionRuleRecord(
                    rule_id=candidate.rule_id,
                    rule_version=knowledge_rule_version,
                    source_kind="knowledge_artifact",
                    severity=Severity(candidate.severity),
                    medication_keys=medications,
                    ingredient_keys=ingredients,
                    message=claim.claim_text,
                    warning_text=claim.claim_text,
                    reason_code=_optional_string(candidate.then_clause.get("reason_code")),
                    next_action=_optional_string(candidate.then_clause.get("next_action")),
                    reference_ids=[candidate.reference_id],
                    claim_ids=[candidate.claim_id],
                )
            )
            medication_keys.update(medications)
            _register_ingredients(
                ingredient_map,
                ingredient_aliases,
                alias_keys,
                ingredients,
                source_kind="knowledge_artifact",
            )

    ingredient_domain_scores = [
        IngredientDomainScoreRecord(
            ingredient_key=edge.ingredient_key,
            domain_key=edge.domain_key,
            support_score=float(len(edge.claim_ids)),
            medication_keys=edge.medication_keys,
            normalized_claim_types=edge.normalized_claim_types,
            reference_ids=edge.reference_ids,
            claim_ids=edge.claim_ids,
        )
        for edge in artifact.ingredient_domain_evidence
    ]
    _register_ingredients(
        ingredient_map,
        ingredient_aliases,
        alias_keys,
        [edge.ingredient_key for edge in artifact.ingredient_domain_evidence],
        source_kind="knowledge_artifact",
    )
    medication_keys.update(
        medication_key
        for edge in artifact.ingredient_domain_evidence
        for medication_key in edge.medication_keys
    )

    references = [
        KnowledgeReferenceRecord.model_validate(reference.model_dump())
        for reference in artifact.references
    ]
    reference_spans = [
        ReferenceSpanRecord(
            span_id=f"SPAN-{claim.claim_id}",
            reference_id=claim.reference_id,
            claim_id=claim.claim_id,
            line_start=claim.citation_span.line_start,
            line_end=claim.citation_span.line_end,
            excerpt=claim.citation_span.excerpt,
            claim_text=claim.claim_text,
            normalized_claim_type=claim.normalized_claim_type,
            ingredient_keys=claim.ingredient_keys,
            domain_keys=claim.domain_keys,
        )
        for claim in artifact.parsed_claims
    ]
    workflow_policies = [
        WorkflowPolicyRecord(
            rule_id=candidate.rule_id,
            source_kind="knowledge_artifact",
            severity=Severity(candidate.severity),
            policy_type=candidate.rule_type,
            payload=candidate.then_clause,
            message=claim_by_id[candidate.claim_id].claim_text,
            reference_ids=[candidate.reference_id],
            claim_ids=[candidate.claim_id],
        )
        for candidate in artifact.rule_candidates
        if candidate.rule_type
        in {
            "enforce_system_owned_actions",
            "map_high_risk_to_safety_recheck",
            "require_reference_ids",
            "enforce_citation_schema",
        }
    ]

    runtime_db = RuntimeKnowledgeDB(
        source_reference_artifact_version=artifact.artifact_version,
        ingredients=sorted(ingredient_map.values(), key=lambda item: item.ingredient_key),
        ingredient_aliases=sorted(
            ingredient_aliases,
            key=lambda item: (item.ingredient_key, item.alias, item.source_kind),
        ),
        medications=[MedicationRecord(medication_key=item) for item in sorted(medication_keys)],
        conditions=[ConditionRecord(condition_key=item) for item in sorted(condition_keys)],
        interaction_rules=interaction_rules,
        contraindication_rules=contraindication_rules,
        dose_limits=dose_limits,
        ingredient_domain_scores=ingredient_domain_scores,
        goal_ingredient_priors=goal_prior_registry.records,
        candidate_signal_scoring=candidate_signal_registry,
        references=references,
        reference_spans=reference_spans,
        workflow_policies=workflow_policies,
    )
    issues = validate_runtime_knowledge_db(runtime_db)
    if issues:
        raise ValueError(f"invalid_runtime_knowledge_db:{','.join(issues)}")
    return runtime_db


@lru_cache
def load_runtime_knowledge_db() -> RuntimeKnowledgeDB:
    path = repo_root() / "data" / "knowledge" / "runtime_knowledge_db_v1.json"
    if path.exists():
        runtime_db = RuntimeKnowledgeDB.model_validate_json(path.read_text(encoding="utf-8"))
    else:
        runtime_db = build_runtime_knowledge_db()
    issues = validate_runtime_knowledge_db(runtime_db)
    if issues:
        raise ValueError(f"invalid_runtime_knowledge_db:{','.join(issues)}")
    return runtime_db


def validate_runtime_knowledge_db(runtime_db: RuntimeKnowledgeDB) -> list[str]:
    issues: list[str] = []
    issues.extend(_validate_unique_keys("ingredient", runtime_db.ingredients, "ingredient_key"))
    issues.extend(_validate_unique_keys("medication", runtime_db.medications, "medication_key"))
    issues.extend(_validate_unique_keys("condition", runtime_db.conditions, "condition_key"))
    issues.extend(
        _validate_unique_keys(
            "interaction_rule",
            runtime_db.interaction_rules,
            "rule_id",
        )
    )
    issues.extend(
        _validate_unique_keys("contraindication_rule", runtime_db.contraindication_rules, "rule_id")
    )
    issues.extend(_validate_unique_keys("dose_limit", runtime_db.dose_limits, "rule_id"))
    issues.extend(_validate_unique_keys("reference", runtime_db.references, "reference_id"))
    issues.extend(_validate_unique_keys("reference_span", runtime_db.reference_spans, "span_id"))
    issues.extend(_validate_unique_keys("reference_claim", runtime_db.reference_spans, "claim_id"))
    issues.extend(_validate_unique_keys("workflow_policy", runtime_db.workflow_policies, "rule_id"))

    required_tables = (
        "ingredients",
        "ingredient_aliases",
        "medications",
        "conditions",
        "interaction_rules",
        "contraindication_rules",
        "dose_limits",
        "ingredient_domain_scores",
        "goal_ingredient_priors",
        "references",
        "reference_spans",
        "workflow_policies",
    )
    for table_name in required_tables:
        if getattr(runtime_db, table_name, None) is None:
            issues.append(f"missing_table:{table_name}")

    reference_ids = {reference.reference_id for reference in runtime_db.references}
    claim_reference_ids = {span.claim_id: span.reference_id for span in runtime_db.reference_spans}
    ingredient_keys = {record.ingredient_key for record in runtime_db.ingredients}
    spans_by_claim_id = {span.claim_id: span for span in runtime_db.reference_spans}
    if runtime_db.candidate_signal_scoring is None:
        issues.append("missing_candidate_signal_scoring_registry")
    else:
        issues.extend(
            validate_candidate_signal_registry(
                runtime_db.candidate_signal_scoring,
                reference_artifact=_runtime_reference_artifact(runtime_db),
            )
        )
    for rule in runtime_db.interaction_rules:
        if rule.source_kind not in {"knowledge_artifact", "evidence_linked_policy"}:
            issues.append(f"invalid_interaction_source_kind:{rule.rule_id}:{rule.source_kind}")
        issues.extend(
            _validate_referenced_ids(
                rule,
                reference_ids,
                claim_reference_ids,
                require_evidence=True,
            )
        )
    for rule in runtime_db.contraindication_rules:
        issues.extend(_validate_referenced_ids(rule, reference_ids, claim_reference_ids))
    for record in runtime_db.dose_limits:
        issues.extend(_validate_referenced_ids(record, reference_ids, claim_reference_ids))
        if record.ingredient_key not in ingredient_keys:
            issues.append(f"missing_ingredient:dose_limit:{record.ingredient_key}")
        if record.max_daily_amount is None or record.max_daily_amount <= 0:
            issues.append(f"invalid_dose_limit_amount:{record.rule_id}")
        if not record.unit:
            issues.append(f"missing_dose_limit_unit:{record.rule_id}")
        if not record.allowed_evidence_sources:
            issues.append(f"missing_dose_limit_evidence_sources:{record.rule_id}")
        invalid_sources = {
            source
            for source in record.allowed_evidence_sources
            if source not in {"structured_dose", "ingredient_line", "title"}
        }
        for source in sorted(invalid_sources):
            issues.append(f"invalid_dose_limit_evidence_source:{record.rule_id}:{source}")
    for record in runtime_db.ingredient_domain_scores:
        issues.extend(_validate_referenced_ids(record, reference_ids, claim_reference_ids))
    seen_goal_priors: set[tuple[str, str]] = set()
    covered_goals: set[str] = set()
    for record in runtime_db.goal_ingredient_priors:
        label = f"{record.ingredient_key}:{record.goal_key.value}"
        pair = (record.ingredient_key, record.goal_key.value)
        if pair in seen_goal_priors:
            issues.append(f"duplicate_goal_prior:{label}")
        seen_goal_priors.add(pair)
        covered_goals.add(record.goal_key.value)
        issues.extend(_validate_referenced_ids(record, reference_ids, claim_reference_ids))
        if len(set(record.reference_ids)) != len(record.reference_ids):
            issues.append(f"duplicate_goal_prior_reference:{label}")
        if len(set(record.claim_ids)) != len(record.claim_ids):
            issues.append(f"duplicate_goal_prior_claim:{label}")
        if record.ingredient_key not in ingredient_keys:
            issues.append(f"unknown_goal_prior_ingredient:{record.ingredient_key}")
        expected_score = 18.0 if record.goal_key == RecommendationGoal.GENERAL_WELLNESS else 35.0
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
        if GOAL_PRIOR_POLICY_REFERENCE_ID not in record.reference_ids:
            issues.append(f"missing_goal_prior_policy_reference:{label}")
        if GOAL_PRIOR_POLICY_CLAIM_ID not in record.claim_ids:
            issues.append(f"missing_goal_prior_policy_claim:{label}")
        clinical_contracts: set[tuple[EvidenceStrength, EvidenceDirection]] = set()
        claim_owned_references: set[str] = set()
        for claim_id in record.claim_ids:
            span = spans_by_claim_id.get(claim_id)
            if span is None:
                continue
            claim_owned_references.add(span.reference_id)
            if claim_id == GOAL_PRIOR_POLICY_CLAIM_ID:
                if (
                    span.reference_id != GOAL_PRIOR_POLICY_REFERENCE_ID
                    or span.normalized_claim_type != GOAL_PRIOR_POLICY_CLAIM_TYPE
                    or span.ingredient_keys
                    or span.domain_keys != [GOAL_PRIOR_POLICY_CLAIM_TYPE]
                ):
                    issues.append(f"invalid_goal_prior_policy_claim:{label}:{claim_id}")
                continue
            if span.normalized_claim_type == GOAL_PRIOR_POLICY_CLAIM_TYPE:
                issues.append(f"unexpected_goal_prior_policy_claim:{label}:{claim_id}")
            if record.ingredient_key not in span.ingredient_keys:
                issues.append(f"goal_prior_claim_ingredient_mismatch:{label}:{claim_id}")
            if record.goal_key.value not in span.domain_keys:
                issues.append(f"goal_prior_claim_domain_mismatch:{label}:{claim_id}")
            contract = GOAL_PRIOR_CLINICAL_CLAIM_CONTRACTS.get(span.normalized_claim_type)
            if contract is None:
                issues.append(
                    f"unsupported_goal_prior_claim_type:{label}:{claim_id}:"
                    f"{span.normalized_claim_type}"
                )
            else:
                clinical_contracts.add(contract)
        declared_references = set(record.reference_ids)
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
        if goal.value not in covered_goals:
            issues.append(f"goal_prior_goal_uncovered:{goal.value}")
    expected_goal_priors = {
        (item.key, goal.value)
        for item in load_ingredient_catalog()
        for goal in item.supported_goals
    }
    for ingredient_key, goal_key in sorted(expected_goal_priors - seen_goal_priors):
        issues.append(f"goal_prior_catalog_pair_uncovered:{ingredient_key}:{goal_key}")
    for ingredient_key, goal_key in sorted(seen_goal_priors - expected_goal_priors):
        issues.append(f"goal_prior_catalog_pair_unknown:{ingredient_key}:{goal_key}")
    for policy in runtime_db.workflow_policies:
        issues.extend(_validate_referenced_ids(policy, reference_ids, claim_reference_ids))

    return issues


def _runtime_reference_artifact(runtime_db: RuntimeKnowledgeDB) -> KnowledgeBaseArtifact:
    references_by_id = {
        reference.reference_id: reference for reference in runtime_db.references
    }
    return KnowledgeBaseArtifact(
        references=[
            ReferenceMetadata.model_validate(reference.model_dump(mode="json"))
            for reference in runtime_db.references
        ],
        parsed_claims=[
            ParsedReferenceClaim(
                reference_id=span.reference_id,
                source_title=references_by_id[span.reference_id].source_title,
                source_type=references_by_id[span.reference_id].source_type,
                page_or_section=references_by_id[span.reference_id].page_or_section,
                reference_uri=references_by_id[span.reference_id].reference_uri,
                claim_id=span.claim_id,
                claim_text=span.claim_text,
                normalized_claim_type=span.normalized_claim_type,
                citation_span=CitationSpan(
                    line_start=span.line_start,
                    line_end=span.line_end,
                    excerpt=span.excerpt,
                ),
                ingredient_keys=span.ingredient_keys,
                domain_keys=span.domain_keys,
            )
            for span in runtime_db.reference_spans
            if span.reference_id in references_by_id
        ],
        rule_candidates=[],
        ingredient_domain_evidence=[],
    )


def find_triggered_interaction_rules(
    runtime_db: RuntimeKnowledgeDB,
    *,
    medication_keys: set[str],
    ingredient_keys: set[str],
) -> list[InteractionRuleRecord]:
    matches: list[InteractionRuleRecord] = []
    for rule in runtime_db.interaction_rules:
        if rule.source_kind != "knowledge_artifact":
            continue
        if not set(rule.medication_keys).intersection(medication_keys):
            continue
        if not set(rule.ingredient_keys).intersection(ingredient_keys):
            continue
        matches.append(rule)
    return matches


def build_citations_for_rule(
    runtime_db: RuntimeKnowledgeDB,
    *,
    reference_ids: list[str],
    claim_ids: list[str],
) -> list[CitationReference]:
    references_by_id = {reference.reference_id: reference for reference in runtime_db.references}
    spans_by_claim_id = {span.claim_id: span for span in runtime_db.reference_spans}
    citations: list[CitationReference] = []
    seen_keys: set[tuple[str, str | None]] = set()
    declared_reference_ids = set(reference_ids)
    for claim_id in claim_ids:
        span = spans_by_claim_id.get(claim_id)
        if span is None:
            continue
        if span.reference_id not in declared_reference_ids:
            continue
        reference = references_by_id.get(span.reference_id)
        if reference is None:
            continue
        key = (reference.reference_id, claim_id)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        citations.append(
            CitationReference(
                reference_id=reference.reference_id,
                claim_id=claim_id,
                source_title=reference.source_title,
                source_type=reference.source_type,
                page_or_section=reference.page_or_section,
                excerpt=span.excerpt,
                reference_uri=reference.reference_uri,
            )
        )
    for reference_id in reference_ids:
        key = (reference_id, None)
        if key in seen_keys:
            continue
        if any(existing_key[0] == reference_id for existing_key in seen_keys):
            continue
        reference = references_by_id.get(reference_id)
        if reference is None:
            continue
        seen_keys.add(key)
        citations.append(
            CitationReference(
                reference_id=reference.reference_id,
                source_title=reference.source_title,
                source_type=reference.source_type,
                page_or_section=reference.page_or_section,
                excerpt="Structured runtime knowledge reference.",
                reference_uri=reference.reference_uri,
            )
        )
    return citations


def _load_reference_artifact(
    reference_artifact_path: str | Path | None,
) -> KnowledgeBaseArtifact:
    path = (
        Path(reference_artifact_path)
        if reference_artifact_path
        else (repo_root() / "data" / "knowledge" / "reference_knowledge_base_v1.json")
    )
    artifact = KnowledgeBaseArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    issues = validate_knowledge_artifact(artifact)
    if issues:
        raise ValueError(f"invalid_reference_knowledge_artifact:{','.join(issues)}")
    return artifact


def _load_raw_safety_rules() -> dict[str, Any]:
    path = repo_root() / "data" / "rules" / "safety_rules.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _version_from_artifact_version(artifact_version: str) -> int:
    match = re.fullmatch(r".*_v(?P<version>[1-9]\d*)", artifact_version)
    if match is None:
        raise ValueError("knowledge artifact version must end in _v<positive integer>")
    return int(match.group("version"))


def _validate_unique_keys(
    label: str,
    items: list[Any],
    field_name: str,
) -> list[str]:
    issues: list[str] = []
    seen_keys: set[Any] = set()
    for item in items:
        key = getattr(item, field_name)
        if key in seen_keys:
            issues.append(f"duplicate_{label}:{key}")
            continue
        seen_keys.add(key)
    return issues


def _validate_referenced_ids(
    item: Any,
    reference_ids: set[str],
    claim_reference_ids: dict[str, str],
    *,
    require_evidence: bool = False,
) -> list[str]:
    issues: list[str] = []
    source_kind = getattr(item, "source_kind", "deterministic_policy")
    item_id = getattr(item, "rule_id", getattr(item, "ingredient_key", "unknown"))
    item_reference_ids = getattr(item, "reference_ids", [])
    item_claim_ids = getattr(item, "claim_ids", [])
    if require_evidence or source_kind in {"knowledge_artifact", "evidence_linked_policy"}:
        if not item_reference_ids:
            issues.append(f"evidence_item_missing_reference:{item_id}")
        if not item_claim_ids:
            issues.append(f"evidence_item_missing_claim:{item_id}")
    for reference_id in item_reference_ids:
        if reference_id not in reference_ids:
            issues.append(f"missing_reference:{item_id}:{reference_id}")
    for claim_id in item_claim_ids:
        claim_reference_id = claim_reference_ids.get(claim_id)
        if claim_reference_id is None:
            issues.append(f"missing_claim:{item_id}:{claim_id}")
        elif claim_reference_id not in item_reference_ids:
            issues.append(f"claim_reference_mismatch:{item_id}:{claim_id}:{claim_reference_id}")
    return issues


def _register_ingredients(
    ingredient_map: dict[str, IngredientRecord],
    ingredient_aliases: list[IngredientAliasRecord],
    alias_keys: set[tuple[str, str, str]],
    ingredient_keys: list[str],
    *,
    source_kind: str,
) -> None:
    for ingredient_key in ingredient_keys:
        if ingredient_key not in ingredient_map:
            ingredient_map[ingredient_key] = IngredientRecord(
                ingredient_key=ingredient_key,
                display_name=_humanize_key(ingredient_key),
            )
        _append_alias(
            ingredient_aliases,
            alias_keys,
            IngredientAliasRecord(
                ingredient_key=ingredient_key,
                alias=ingredient_key,
                source_kind=source_kind,
            ),
        )


def _append_alias(
    aliases: list[IngredientAliasRecord],
    alias_keys: set[tuple[str, str, str]],
    alias: IngredientAliasRecord,
) -> None:
    key = (alias.ingredient_key, alias.alias, alias.source_kind)
    if key in alias_keys:
        return
    alias_keys.add(key)
    aliases.append(alias)


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _sorted_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({value for value in values if isinstance(value, str) and value})


def _validated_dose_evidence_sources(values: Any) -> list[str]:
    default_sources = ["structured_dose", "ingredient_line", "title"]
    if not isinstance(values, list):
        return default_sources

    allowed_values = {"structured_dose", "ingredient_line", "title"}
    normalized_sources = [
        value for value in values if isinstance(value, str) and value in allowed_values
    ]
    if not normalized_sources:
        return default_sources
    return list(dict.fromkeys(normalized_sources))


def _humanize_key(value: str) -> str:
    return value.replace("_", " ").title()
