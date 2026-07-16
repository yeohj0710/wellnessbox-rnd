from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.domain.loaders import load_ingredient_catalog, repo_root
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.schemas.recommendation import LaboratoryRangeStatus, RecommendationGoal

CANDIDATE_SIGNAL_SCHEMA_VERSION = "candidate_signal_scoring_rules_v1"
DEFAULT_CANDIDATE_SIGNAL_PATH = Path(
    "data/rules/candidate_signal_scoring_rules_v1.json"
)
CANDIDATE_SIGNAL_POLICY_REFERENCE_ID = "REF-MC-CANDIDATE-SIGNAL-001"
CANDIDATE_SIGNAL_POLICY_CLAIM_ID = "CLM-MC-CANDIDATE-SIGNAL-POLICY-001"
CANDIDATE_SIGNAL_POLICY_CLAIM_TYPE = "candidate_signal_policy"
CANDIDATE_SIGNAL_SCORING_VERSION = "2026-07-16.1"
CANDIDATE_SIGNAL_EFFECTIVE_AT = "2026-07-16T00:00:00Z"
CANDIDATE_SIGNAL_SCORE_MEANING = (
    "bounded deterministic candidate-ordering points, not diagnosis, dose advice, "
    "treatment target, efficacy probability, or individualized medical advice"
)
CANDIDATE_SIGNAL_SYMPTOM_RULE_ID = "CS-SYMPTOM-MATCH-001"
CANDIDATE_SIGNAL_LIFESTYLE_RULE_ID = "CS-LIFESTYLE-MATCH-001"
CANDIDATE_SIGNAL_ALLOWED_CLAIM_TYPES = {
    "candidate_signal_threshold",
    "dietary_pattern_candidate_signal",
    "genetic_candidate_signal_policy",
    "inconclusive_goal_evidence",
    "limited_goal_evidence",
    "mixed_goal_evidence",
    "moderate_goal_evidence",
    "null_goal_evidence_without_deficiency",
    "nutrient_adequacy_goal_evidence",
}
CANDIDATE_SIGNAL_RULE_CONTRACTS: dict[str, dict[str, object]] = {
    "CS-LAB-GLUCOSE-FIBER-001": {
        "ingredient_key": "soluble_fiber",
        "goal_keys": ["blood_glucose"],
        "observation_codes": ["fasting glucose", "hba1c"],
        "range_status": "high",
        "points": 4.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-CDC-SOLUBLE-FIBER-001",
        ],
    },
    "CS-LAB-GLUCOSE-BERBERINE-001": {
        "ingredient_key": "berberine",
        "goal_keys": ["blood_glucose"],
        "observation_codes": ["fasting glucose", "hba1c"],
        "range_status": "high",
        "points": 2.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-NCCIH-BERBERINE-GLUCOSE-001",
        ],
    },
    "CS-LAB-TRIGLYCERIDE-OMEGA3-001": {
        "ingredient_key": "omega3",
        "goal_keys": ["heart_health"],
        "observation_codes": ["triglyceride", "triglycerides"],
        "range_status": "high",
        "points": 4.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-NIH-ODS-OMEGA3-HEART-001",
        ],
    },
    "CS-DIET-VEGETARIAN-B12-001": {
        "ingredient_key": "vitamin_b_complex",
        "goal_keys": ["energy_support", "general_wellness"],
        "dietary_patterns": ["plant based", "strict vegetarian", "vegan", "vegetarian"],
        "points": 3.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-NIH-ODS-B12-VEGETARIAN-001",
        ],
    },
    "CS-WEARABLE-SLEEP-MAGNESIUM-001": {
        "ingredient_key": "magnesium_glycinate",
        "goal_keys": ["sleep_support"],
        "metric": "sleep_hours",
        "operator": "below",
        "threshold": 7.0,
        "points_per_unit": 2.0,
        "max_points": 6.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-CDC-ADULT-SLEEP-001",
            "CLM-NCCIH-MAGNESIUM-SLEEP-001",
        ],
    },
    "CS-WEARABLE-SLEEP-LTHEANINE-001": {
        "ingredient_key": "l_theanine",
        "goal_keys": ["sleep_support"],
        "metric": "sleep_hours",
        "operator": "below",
        "threshold": 7.0,
        "points_per_unit": 1.5,
        "max_points": 4.5,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-CDC-ADULT-SLEEP-001",
            "CLM-PUBMED-LTHEANINE-STRESS-SLEEP-001",
        ],
    },
    "CS-CGM-TIR-FIBER-001": {
        "ingredient_key": "soluble_fiber",
        "goal_keys": ["blood_glucose"],
        "condition_keys": ["diabetes", "type 1 diabetes", "type 2 diabetes"],
        "requires_nonpregnant": True,
        "range_low_mg_dl": 70.0,
        "range_high_mg_dl": 180.0,
        "metric": "time_in_range_pct",
        "operator": "below",
        "threshold": 70.0,
        "points_per_unit": 0.2,
        "max_points": 6.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-ADA-CGM-TIR-001",
            "CLM-CDC-SOLUBLE-FIBER-001",
        ],
    },
    "CS-CGM-TIR-BERBERINE-001": {
        "ingredient_key": "berberine",
        "goal_keys": ["blood_glucose"],
        "condition_keys": ["diabetes", "type 1 diabetes", "type 2 diabetes"],
        "requires_nonpregnant": True,
        "range_low_mg_dl": 70.0,
        "range_high_mg_dl": 180.0,
        "metric": "time_in_range_pct",
        "operator": "below",
        "threshold": 70.0,
        "points_per_unit": 0.1,
        "max_points": 3.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-ADA-CGM-TIR-001",
            "CLM-NCCIH-BERBERINE-GLUCOSE-001",
        ],
    },
    "CS-GENE-CYP1A2-LTHEANINE-001": {
        "ingredient_key": "l_theanine",
        "goal_keys": ["sleep_support", "stress_support"],
        "genetic_tags": ["cyp1a2_slow_metabolizer", "slow_caffeine_metabolism"],
        "points": 4.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-MC-CANDIDATE-SIGNAL-CYP1A2-001",
            "CLM-PUBMED-LTHEANINE-STRESS-SLEEP-001",
        ],
    },
    "CS-GENE-LPL-OMEGA3-001": {
        "ingredient_key": "omega3",
        "goal_keys": ["heart_health"],
        "genetic_tags": ["adverse_lpl_variant", "lpl_triglyceride_risk"],
        "points": 4.0,
        "claim_ids": [
            CANDIDATE_SIGNAL_POLICY_CLAIM_ID,
            "CLM-MC-CANDIDATE-SIGNAL-LPL-001",
            "CLM-NIH-ODS-OMEGA3-HEART-001",
        ],
    },
}
CANDIDATE_SIGNAL_RULE_LIMITATIONS = {
    "CS-LAB-GLUCOSE-FIBER-001": (
        "Uses the laboratory-provided reference range and does not diagnose "
        "dysglycemia or establish a product or dose."
    ),
    "CS-LAB-GLUCOSE-BERBERINE-001": (
        "Uses the laboratory-provided reference range; berberine evidence is "
        "limited and safety filtering remains authoritative."
    ),
    "CS-LAB-TRIGLYCERIDE-OMEGA3-001": (
        "Uses the laboratory-provided reference range and does not determine an "
        "omega-3 product or dose."
    ),
    "CS-DIET-VEGETARIAN-B12-001": (
        "Raises candidate priority for inadequacy risk only; it does not diagnose "
        "deficiency or establish whole B-complex efficacy."
    ),
    "CS-WEARABLE-SLEEP-MAGNESIUM-001": (
        "Short-sleep context is not a sleep-disorder diagnosis; magnesium sleep "
        "evidence is mixed."
    ),
    "CS-WEARABLE-SLEEP-LTHEANINE-001": (
        "Short-sleep context is not a sleep-disorder diagnosis; L-theanine evidence "
        "comes from a small short trial."
    ),
    "CS-CGM-TIR-FIBER-001": (
        "Only explicit diabetes context is eligible; this is candidate ordering and "
        "not an individualized CGM treatment target."
    ),
    "CS-CGM-TIR-BERBERINE-001": (
        "Only explicit diabetes context is eligible; berberine evidence is limited "
        "and safety filtering remains authoritative."
    ),
    "CS-GENE-CYP1A2-LTHEANINE-001": (
        "A declared tag changes prototype ordering only and is not independently "
        "reinterpreted as a genetic diagnosis."
    ),
    "CS-GENE-LPL-OMEGA3-001": (
        "A declared tag changes prototype ordering only and is not independently "
        "reinterpreted as a genetic diagnosis."
    ),
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateSignalRuleBase(_StrictModel):
    rule_id: str = Field(pattern=r"^CS-[A-Z0-9-]+-\d{3}$")
    ingredient_key: str = Field(min_length=1)
    goal_keys: list[RecommendationGoal] = Field(min_length=1)
    reference_ids: list[str] = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)
    limitation: str = Field(min_length=1)


class LaboratoryCandidateSignalRule(CandidateSignalRuleBase):
    observation_codes: list[str] = Field(min_length=1)
    range_status: LaboratoryRangeStatus
    points: float = Field(gt=0.0, le=10.0, allow_inf_nan=False)


class DietaryCandidateSignalRule(CandidateSignalRuleBase):
    dietary_patterns: list[str] = Field(min_length=1)
    points: float = Field(gt=0.0, le=10.0, allow_inf_nan=False)


class NumericCandidateSignalRule(CandidateSignalRuleBase):
    metric: Literal["sleep_hours", "time_in_range_pct"]
    operator: Literal["below"]
    threshold: float = Field(allow_inf_nan=False)
    points_per_unit: float = Field(gt=0.0, le=10.0, allow_inf_nan=False)
    max_points: float = Field(gt=0.0, le=10.0, allow_inf_nan=False)


class CgmCandidateSignalRule(NumericCandidateSignalRule):
    metric: Literal["time_in_range_pct"]
    condition_keys: list[str] = Field(min_length=1)
    requires_nonpregnant: Literal[True]
    range_low_mg_dl: float = Field(ge=20.0, le=600.0, allow_inf_nan=False)
    range_high_mg_dl: float = Field(ge=20.0, le=600.0, allow_inf_nan=False)


class GeneticCandidateSignalRule(CandidateSignalRuleBase):
    genetic_tags: list[str] = Field(min_length=1)
    points: float = Field(gt=0.0, le=10.0, allow_inf_nan=False)


class CandidateSignalScoringRegistry(_StrictModel):
    schema_version: str
    scoring_version: str = Field(min_length=1)
    effective_at: str = Field(min_length=1)
    score_meaning: str = Field(min_length=1)
    symptom_rule_id: str = Field(pattern=r"^CS-[A-Z0-9-]+-\d{3}$")
    symptom_points_per_match: float = Field(gt=0.0, le=10.0, allow_inf_nan=False)
    lifestyle_rule_id: str = Field(pattern=r"^CS-[A-Z0-9-]+-\d{3}$")
    lifestyle_signal_points_per_match: float = Field(
        gt=0.0, le=10.0, allow_inf_nan=False
    )
    policy_reference_id: str = Field(min_length=1)
    policy_claim_id: str = Field(min_length=1)
    laboratory_rules: list[LaboratoryCandidateSignalRule] = Field(default_factory=list)
    dietary_rules: list[DietaryCandidateSignalRule] = Field(default_factory=list)
    wearable_rules: list[NumericCandidateSignalRule] = Field(default_factory=list)
    cgm_rules: list[CgmCandidateSignalRule] = Field(default_factory=list)
    genetic_rules: list[GeneticCandidateSignalRule] = Field(default_factory=list)

    def all_rules(self) -> list[CandidateSignalRuleBase]:
        return [
            *self.laboratory_rules,
            *self.dietary_rules,
            *self.wearable_rules,
            *self.cgm_rules,
            *self.genetic_rules,
        ]


def load_candidate_signal_registry(
    path: str | Path | None = None,
) -> CandidateSignalScoringRegistry:
    resolved = (
        Path(path)
        if path is not None
        else repo_root() / DEFAULT_CANDIDATE_SIGNAL_PATH
    )
    return CandidateSignalScoringRegistry.model_validate_json(
        resolved.read_text(encoding="utf-8")
    )


def validate_candidate_signal_registry(
    registry: CandidateSignalScoringRegistry,
    *,
    reference_artifact: KnowledgeBaseArtifact,
) -> list[str]:
    issues: list[str] = []
    if registry.schema_version != CANDIDATE_SIGNAL_SCHEMA_VERSION:
        issues.append(f"unsupported_candidate_signal_schema:{registry.schema_version}")
    if registry.scoring_version != CANDIDATE_SIGNAL_SCORING_VERSION:
        issues.append("candidate_signal_scoring_version_mismatch")
    if registry.effective_at != CANDIDATE_SIGNAL_EFFECTIVE_AT:
        issues.append("candidate_signal_effective_at_mismatch")
    if registry.score_meaning != CANDIDATE_SIGNAL_SCORE_MEANING:
        issues.append("candidate_signal_score_meaning_mismatch")
    if registry.policy_reference_id != CANDIDATE_SIGNAL_POLICY_REFERENCE_ID:
        issues.append("candidate_signal_policy_reference_mismatch")
    if registry.policy_claim_id != CANDIDATE_SIGNAL_POLICY_CLAIM_ID:
        issues.append("candidate_signal_policy_claim_mismatch")
    if registry.symptom_points_per_match != 8.0:
        issues.append("candidate_signal_symptom_weight_mismatch")
    if registry.lifestyle_signal_points_per_match != 6.0:
        issues.append("candidate_signal_lifestyle_weight_mismatch")
    if registry.symptom_rule_id != CANDIDATE_SIGNAL_SYMPTOM_RULE_ID:
        issues.append("candidate_signal_symptom_rule_mismatch")
    if registry.lifestyle_rule_id != CANDIDATE_SIGNAL_LIFESTYLE_RULE_ID:
        issues.append("candidate_signal_lifestyle_rule_mismatch")

    catalog = {item.key: item for item in load_ingredient_catalog()}
    references = {item.reference_id for item in reference_artifact.references}
    claims = {item.claim_id: item for item in reference_artifact.parsed_claims}
    policy_claim = claims.get(CANDIDATE_SIGNAL_POLICY_CLAIM_ID)
    if (
        policy_claim is None
        or policy_claim.reference_id != CANDIDATE_SIGNAL_POLICY_REFERENCE_ID
        or policy_claim.normalized_claim_type != CANDIDATE_SIGNAL_POLICY_CLAIM_TYPE
        or policy_claim.ingredient_keys
        or policy_claim.domain_keys != [CANDIDATE_SIGNAL_POLICY_CLAIM_TYPE]
    ):
        issues.append("invalid_candidate_signal_policy_claim")

    rules = registry.all_rules()
    actual_rule_ids = {rule.rule_id for rule in rules}
    expected_rule_ids = set(CANDIDATE_SIGNAL_RULE_CONTRACTS)
    for rule_id in sorted(expected_rule_ids - actual_rule_ids):
        issues.append(f"missing_candidate_signal_rule:{rule_id}")
    for rule_id in sorted(actual_rule_ids - expected_rule_ids):
        issues.append(f"unknown_candidate_signal_rule:{rule_id}")
    rule_ids = [
        registry.symptom_rule_id,
        registry.lifestyle_rule_id,
        *(rule.rule_id for rule in rules),
    ]
    for rule_id in sorted({value for value in rule_ids if rule_ids.count(value) > 1}):
        issues.append(f"duplicate_candidate_signal_rule:{rule_id}")

    for rule in rules:
        label = rule.rule_id
        expected_contract = CANDIDATE_SIGNAL_RULE_CONTRACTS.get(label)
        if expected_contract is not None:
            actual_contract = rule.model_dump(
                mode="json",
                include=set(expected_contract),
            )
            if actual_contract != expected_contract:
                issues.append(f"candidate_signal_rule_contract_mismatch:{label}")
            if rule.limitation != CANDIDATE_SIGNAL_RULE_LIMITATIONS[label]:
                issues.append(f"candidate_signal_rule_limitation_mismatch:{label}")
        catalog_item = catalog.get(rule.ingredient_key)
        if catalog_item is None:
            issues.append(f"unknown_candidate_signal_ingredient:{label}:{rule.ingredient_key}")
        else:
            for goal in rule.goal_keys:
                if goal not in catalog_item.supported_goals:
                    issues.append(
                        f"candidate_signal_goal_out_of_catalog_scope:{label}:{goal.value}"
                    )
        if len(set(rule.goal_keys)) != len(rule.goal_keys):
            issues.append(f"duplicate_candidate_signal_goal:{label}")
        if len(set(rule.reference_ids)) != len(rule.reference_ids):
            issues.append(f"duplicate_candidate_signal_reference:{label}")
        if len(set(rule.claim_ids)) != len(rule.claim_ids):
            issues.append(f"duplicate_candidate_signal_claim:{label}")
        if CANDIDATE_SIGNAL_POLICY_REFERENCE_ID not in rule.reference_ids:
            issues.append(f"missing_candidate_signal_policy_reference:{label}")
        if CANDIDATE_SIGNAL_POLICY_CLAIM_ID not in rule.claim_ids:
            issues.append(f"missing_candidate_signal_policy_claim:{label}")

        declared_references = set(rule.reference_ids)
        claim_owned_references: set[str] = set()
        scoped_domains: set[str] = set()
        for reference_id in rule.reference_ids:
            if not reference_id.strip():
                issues.append(f"empty_candidate_signal_reference:{label}")
            elif reference_id not in references:
                issues.append(f"missing_candidate_signal_reference:{label}:{reference_id}")
        for claim_id in rule.claim_ids:
            if not claim_id.strip():
                issues.append(f"empty_candidate_signal_claim:{label}")
                continue
            claim = claims.get(claim_id)
            if claim is None:
                issues.append(f"missing_candidate_signal_claim:{label}:{claim_id}")
                continue
            claim_owned_references.add(claim.reference_id)
            if claim.reference_id not in declared_references:
                issues.append(
                    f"candidate_signal_claim_reference_mismatch:{label}:{claim_id}:"
                    f"{claim.reference_id}"
                )
            if claim_id == CANDIDATE_SIGNAL_POLICY_CLAIM_ID:
                continue
            scoped_domains.update(claim.domain_keys)
            if claim.normalized_claim_type == CANDIDATE_SIGNAL_POLICY_CLAIM_TYPE:
                issues.append(f"unexpected_candidate_signal_policy_claim:{label}:{claim_id}")
            if claim.normalized_claim_type not in CANDIDATE_SIGNAL_ALLOWED_CLAIM_TYPES:
                issues.append(
                    f"unsupported_candidate_signal_claim_type:{label}:{claim_id}:"
                    f"{claim.normalized_claim_type}"
                )
            elif claim.normalized_claim_type == "candidate_signal_threshold":
                if claim.ingredient_keys:
                    issues.append(
                        f"candidate_signal_threshold_has_ingredient_scope:{label}:{claim_id}"
                    )
            elif rule.ingredient_key not in claim.ingredient_keys:
                issues.append(
                    f"candidate_signal_claim_ingredient_mismatch:{label}:{claim_id}"
                )

        for reference_id in sorted(declared_references - claim_owned_references):
            issues.append(f"unclaimed_candidate_signal_reference:{label}:{reference_id}")
        for reference_id in sorted(claim_owned_references - declared_references):
            issues.append(f"undeclared_candidate_signal_reference:{label}:{reference_id}")
        for goal in rule.goal_keys:
            if goal.value not in scoped_domains:
                issues.append(f"candidate_signal_claim_domain_mismatch:{label}:{goal.value}")

        if isinstance(rule, LaboratoryCandidateSignalRule):
            if any(code != code.strip().casefold() for code in rule.observation_codes):
                issues.append(f"noncanonical_candidate_signal_lab_code:{label}")
        elif isinstance(rule, DietaryCandidateSignalRule):
            if any(value != value.strip().casefold() for value in rule.dietary_patterns):
                issues.append(f"noncanonical_candidate_signal_dietary_pattern:{label}")
        elif isinstance(rule, CgmCandidateSignalRule):
            if rule.threshold != 70.0:
                issues.append(f"candidate_signal_cgm_threshold_mismatch:{label}")
            if any(value != value.strip().casefold() for value in rule.condition_keys):
                issues.append(f"noncanonical_candidate_signal_condition:{label}")
        elif isinstance(rule, NumericCandidateSignalRule):
            if rule.metric == "sleep_hours" and rule.threshold != 7.0:
                issues.append(f"candidate_signal_sleep_threshold_mismatch:{label}")
        elif isinstance(rule, GeneticCandidateSignalRule):
            if any(value != value.strip().casefold() for value in rule.genetic_tags):
                issues.append(f"noncanonical_candidate_signal_genetic_tag:{label}")
    return issues


@lru_cache
def get_candidate_signal_registry() -> CandidateSignalScoringRegistry:
    registry = load_candidate_signal_registry()
    reference_artifact = KnowledgeBaseArtifact.model_validate_json(
        (repo_root() / "data/knowledge/reference_knowledge_base_v1.json").read_text(
            encoding="utf-8"
        )
    )
    issues = validate_candidate_signal_registry(
        registry,
        reference_artifact=reference_artifact,
    )
    if issues:
        raise ValueError(f"invalid_candidate_signal_registry:{','.join(issues)}")
    return registry
