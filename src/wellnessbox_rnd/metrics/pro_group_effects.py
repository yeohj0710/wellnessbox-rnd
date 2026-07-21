from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.metrics.pro_followup import (
    PRO_FOLLOWUP_CHANGE_TOLERANCE_V1,
    PROFollowUpEffectInterpretationV1,
)
from wellnessbox_rnd.metrics.statistics import deterministic_bootstrap_mean_ci

PRO_GROUP_EFFECT_SUMMARY_SCHEMA_VERSION_V1 = "pro_group_effect_summary_v1"
PRO_GROUP_EFFECT_CONTRACT_VERSION_V1 = "2026-07-21.1"
DEFAULT_PRO_GROUP_EFFECT_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/contracts/pro_group_effect_summary_v1.json"
)

PROGroupObservedChangeStatusV1 = Literal["improved", "worsened", "no_material_change"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")


class PROGroupConfidenceIntervalContractV1(_StrictModel):
    confidence_level: float = Field(strict=True, gt=0.0, lt=1.0)
    method: str = Field(min_length=1)
    iterations: StrictInt = Field(ge=1)
    seed: StrictInt


class PROGroupEffectContractV1(_StrictModel):
    schema_version: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    personal_effect_schema_version: str = Field(min_length=1)
    group_summary_schema_version: str = Field(min_length=1)
    aggregation_unit: str = Field(min_length=1)
    group_mean_method: str = Field(min_length=1)
    minimum_group_sample_size: StrictInt = Field(ge=2)
    kpi_target_sample_size: StrictInt = Field(ge=2)
    confidence_interval: PROGroupConfidenceIntervalContractV1
    uncertainty_reason_priority: list[str] = Field(min_length=5, max_length=5)
    effect_claim_scope: str = Field(min_length=1)
    causal_effect_claim_allowed: bool
    source_refs: list[str] = Field(min_length=1)
    limitation: str = Field(min_length=1)


_EXPECTED_PRO_GROUP_EFFECT_CONTRACT_V1 = {
    "schema_version": "pro_group_effect_summary_contract_v1",
    "contract_version": PRO_GROUP_EFFECT_CONTRACT_VERSION_V1,
    "personal_effect_schema_version": "pro_followup_effect_interpretation_v1",
    "group_summary_schema_version": PRO_GROUP_EFFECT_SUMMARY_SCHEMA_VERSION_V1,
    "aggregation_unit": "plan_linked_baseline_followup_pair",
    "group_mean_method": "arithmetic_mean_of_personal_observed_changes",
    "minimum_group_sample_size": 2,
    "kpi_target_sample_size": 100,
    "confidence_interval": {
        "confidence_level": 0.95,
        "method": "deterministic_percentile_bootstrap_mean",
        "iterations": 3_000,
        "seed": 20_260_710,
    },
    "uncertainty_reason_priority": [
        "observational_association_not_causal",
        "non_real_world_outcome_data",
        "sample_size_below_100",
        "limited_personal_interpretations_present",
        "confidence_interval_not_entirely_above_zero",
    ],
    "effect_claim_scope": "group_observed_association_not_causal",
    "causal_effect_claim_allowed": False,
    "source_refs": [
        "data/original_plan/requirements_manifest_v1.json#OP-055",
        "data/original_plan/requirements_manifest_v1.json#OP-056",
        "docs/context/master_context.md#14.3",
        "docs/context/master_context.md#15.6",
        "docs/context/original_plan.pdf#page=26",
    ],
    "limitation": (
        "The summary reports observed personal changes and their group average "
        "separately. Its sample size and confidence intervals quantify the supplied "
        "cohort only and do not establish causal efficacy."
    ),
}


class PROGroupConfidenceIntervalV1(_StrictModel):
    confidence_level: Literal[0.95]
    method: Literal["deterministic_percentile_bootstrap_mean"]
    iterations: Literal[3000]
    seed: Literal[20260710]
    lower: float = Field(allow_inf_nan=False)
    upper: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_bounds(self) -> PROGroupConfidenceIntervalV1:
        if self.lower > self.upper:
            raise ValueError("confidence interval lower bound exceeds upper bound")
        return self


class PROGroupEstimateV1(_StrictModel):
    sample_size: StrictInt = Field(ge=2)
    fully_interpretable_sample_size: StrictInt = Field(ge=0)
    interpretation_status_counts: dict[str, StrictInt]
    mean_health_z_change: float = Field(allow_inf_nan=False)
    mean_health_z_change_ci95: PROGroupConfidenceIntervalV1
    mean_health_percentile_change: float = Field(allow_inf_nan=False)
    mean_health_percentile_change_ci95: PROGroupConfidenceIntervalV1
    observed_change_status: PROGroupObservedChangeStatusV1


class PROGroupEffectSummaryV1(_StrictModel):
    schema_version: Literal["pro_group_effect_summary_v1"]
    contract_version: Literal["2026-07-21.1"]
    cohort_id: str = Field(min_length=1, pattern=r".*\S.*")
    data_class: DataClass
    follow_up_timepoint: Literal["week_2", "week_4", "discontinuation"]
    personal_effects: list[PROFollowUpEffectInterpretationV1] = Field(min_length=2)
    group_estimate: PROGroupEstimateV1
    uncertainty_reason_codes: list[str]
    effect_claim_scope: Literal["group_observed_association_not_causal"]
    causal_effect_claim_allowed: Literal[False]

    @model_validator(mode="after")
    def validate_derived_summary(self) -> PROGroupEffectSummaryV1:
        contract = load_pro_group_effect_contract_v1()
        expected = _derive_summary_fields(self.personal_effects, contract)
        actual = {
            "data_class": self.data_class,
            "follow_up_timepoint": self.follow_up_timepoint,
            "personal_effects": self.personal_effects,
            "group_estimate": self.group_estimate,
            "uncertainty_reason_codes": self.uncertainty_reason_codes,
        }
        if actual != expected:
            raise ValueError("group effect summary does not match personal effects")
        return self


def load_pro_group_effect_contract_v1(
    path: str | Path = DEFAULT_PRO_GROUP_EFFECT_CONTRACT_PATH,
) -> PROGroupEffectContractV1:
    try:
        contract = PROGroupEffectContractV1.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_pro_group_effect_contract::{exc}") from exc
    if contract.model_dump(mode="json") != _EXPECTED_PRO_GROUP_EFFECT_CONTRACT_V1:
        raise ValueError("invalid_pro_group_effect_contract::policy_drift")
    return contract


def build_pro_group_effect_summary_v1(
    *,
    cohort_id: str,
    personal_effects: list[PROFollowUpEffectInterpretationV1 | dict[str, object]],
    contract_path: str | Path = DEFAULT_PRO_GROUP_EFFECT_CONTRACT_PATH,
) -> PROGroupEffectSummaryV1:
    contract = load_pro_group_effect_contract_v1(contract_path)
    validated = [
        PROFollowUpEffectInterpretationV1.model_validate(item)
        for item in personal_effects
    ]
    fields = _derive_summary_fields(validated, contract)
    return PROGroupEffectSummaryV1(
        schema_version=PRO_GROUP_EFFECT_SUMMARY_SCHEMA_VERSION_V1,
        contract_version=contract.contract_version,
        cohort_id=cohort_id,
        effect_claim_scope=contract.effect_claim_scope,
        causal_effect_claim_allowed=contract.causal_effect_claim_allowed,
        **fields,
    )


def _derive_summary_fields(
    personal_effects: list[PROFollowUpEffectInterpretationV1],
    contract: PROGroupEffectContractV1,
) -> dict[str, object]:
    if len(personal_effects) < contract.minimum_group_sample_size:
        raise ValueError("minimum group sample size not met")
    canonical_effects = sorted(
        personal_effects,
        key=lambda item: item.baseline_event.plan_id,
    )
    plan_ids = [item.baseline_event.plan_id for item in canonical_effects]
    if len(plan_ids) != len(set(plan_ids)):
        raise ValueError("duplicate plan in group effect summary")
    assessment_ids = [
        assessment_id
        for item in canonical_effects
        for assessment_id in (
            item.baseline_event.assessment_id,
            item.follow_up_event.assessment_id,
        )
    ]
    if len(assessment_ids) != len(set(assessment_ids)):
        raise ValueError("duplicate assessment in group effect summary")

    data_classes = {item.baseline_event.data_class for item in canonical_effects}
    if len(data_classes) != 1:
        raise ValueError("group effect data class mismatch")
    timepoints = {item.follow_up_event.timepoint for item in canonical_effects}
    if len(timepoints) != 1:
        raise ValueError("group effect follow-up timepoint mismatch")
    score_identities = {_score_identity(item) for item in canonical_effects}
    if len(score_identities) != 1:
        raise ValueError("group effect score identity mismatch")

    z_changes = sorted(item.mean_health_z_change for item in canonical_effects)
    percentile_changes = sorted(
        statistics.mean(
            change.health_percentile_change for change in item.instrument_changes
        )
        for item in canonical_effects
    )
    confidence = contract.confidence_interval
    z_ci = deterministic_bootstrap_mean_ci(
        z_changes,
        confidence_level=confidence.confidence_level,
        iterations=confidence.iterations,
        seed=confidence.seed,
    )
    percentile_ci = deterministic_bootstrap_mean_ci(
        percentile_changes,
        confidence_level=confidence.confidence_level,
        iterations=confidence.iterations,
        seed=confidence.seed,
    )
    mean_z_change = round(statistics.mean(z_changes), 6)
    mean_percentile_change = round(statistics.mean(percentile_changes), 6)
    if mean_z_change > PRO_FOLLOWUP_CHANGE_TOLERANCE_V1:
        observed_change_status = "improved"
    elif mean_z_change < -PRO_FOLLOWUP_CHANGE_TOLERANCE_V1:
        observed_change_status = "worsened"
    else:
        observed_change_status = "no_material_change"

    status_counts = Counter(item.interpretation_status for item in canonical_effects)
    fully_interpretable = sum(
        item.benefit_interpretation_allowed for item in canonical_effects
    )
    group_estimate = PROGroupEstimateV1(
        sample_size=len(canonical_effects),
        fully_interpretable_sample_size=fully_interpretable,
        interpretation_status_counts=dict(sorted(status_counts.items())),
        mean_health_z_change=mean_z_change,
        mean_health_z_change_ci95=_confidence_interval(z_ci, confidence),
        mean_health_percentile_change=mean_percentile_change,
        mean_health_percentile_change_ci95=_confidence_interval(
            percentile_ci,
            confidence,
        ),
        observed_change_status=observed_change_status,
    )
    data_class = next(iter(data_classes))
    active_reasons = {"observational_association_not_causal"}
    if data_class != DataClass.REAL_WORLD_OUTCOME:
        active_reasons.add("non_real_world_outcome_data")
    if len(canonical_effects) < contract.kpi_target_sample_size:
        active_reasons.add("sample_size_below_100")
    if fully_interpretable < len(canonical_effects):
        active_reasons.add("limited_personal_interpretations_present")
    if z_ci[0] <= 0.0 or percentile_ci[0] <= 0.0:
        active_reasons.add("confidence_interval_not_entirely_above_zero")
    return {
        "data_class": data_class,
        "follow_up_timepoint": next(iter(timepoints)),
        "personal_effects": canonical_effects,
        "group_estimate": group_estimate,
        "uncertainty_reason_codes": [
            reason
            for reason in contract.uncertainty_reason_priority
            if reason in active_reasons
        ],
    }


def _score_identity(
    effect: PROFollowUpEffectInterpretationV1,
) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        sorted(
            (
                item.instrument,
                item.contract_version,
                item.instrument_scoring_version,
                item.baseline_distribution.source_scores_sha256,
            )
            for item in effect.baseline_event.standardized_scores
        )
    )


def _confidence_interval(
    bounds: tuple[float, float],
    contract: PROGroupConfidenceIntervalContractV1,
) -> PROGroupConfidenceIntervalV1:
    return PROGroupConfidenceIntervalV1(
        confidence_level=contract.confidence_level,
        method=contract.method,
        iterations=contract.iterations,
        seed=contract.seed,
        lower=round(bounds[0], 6),
        upper=round(bounds[1], 6),
    )


__all__ = [
    "PRO_GROUP_EFFECT_CONTRACT_VERSION_V1",
    "PRO_GROUP_EFFECT_SUMMARY_SCHEMA_VERSION_V1",
    "PROGroupConfidenceIntervalV1",
    "PROGroupEffectContractV1",
    "PROGroupEffectSummaryV1",
    "PROGroupEstimateV1",
    "build_pro_group_effect_summary_v1",
    "load_pro_group_effect_contract_v1",
]
