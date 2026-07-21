from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    model_validator,
)

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.metrics.pro_scoring import (
    PROInstrumentScoreV1,
    PROStandardizedScoreV1,
)

PRO_FOLLOWUP_EVENT_SCHEMA_VERSION_V1 = "versioned_pro_followup_event_v1"
PRO_FOLLOWUP_EFFECT_INTERPRETATION_SCHEMA_VERSION_V1 = (
    "pro_followup_effect_interpretation_v1"
)
PRO_FOLLOWUP_INTERPRETATION_CONTRACT_VERSION_V1 = "2026-07-17.1"
PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1 = 0.8
PRO_FOLLOWUP_CHANGE_TOLERANCE_V1 = 1e-6

PROFollowUpTimepointV1 = Literal[
    "pre_intake",
    "week_2",
    "week_4",
    "discontinuation",
]
PROInstrumentIdV1 = Literal["PSQI", "ISI", "PSS10"]
PROInterpretationStatusV1 = Literal[
    "observed_change_interpretable",
    "limited_by_missed_doses",
    "limited_by_low_adherence",
    "safety_context_required",
    "safety_escalation_required",
]

_SCHEDULED_DAY_BY_TIMEPOINT: dict[str, int | None] = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": None,
}
_VERSIONED_PRO_PAYLOAD_DISCRIMINATORS = {
    "timepoint",
    "instrument_scores",
    "standardized_scores",
}
_PROScore = TypeVar("_PROScore", PROInstrumentScoreV1, PROStandardizedScoreV1)
DEFAULT_PRO_FOLLOWUP_INTERPRETATION_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/contracts/pro_followup_interpretation_v1.json"
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")


class PROFollowUpAdherenceContractV1(_StrictModel):
    minimum_interpretable_rate: float = Field(strict=True, ge=0.0, le=1.0)
    rate_precision_decimal_places: StrictInt = Field(ge=0)
    count_reconciliation: str = Field(min_length=1)


class PROFollowUpPersistenceContractV1(_StrictModel):
    table: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    versioned_payload_required_for_pro_claim: bool


class PROFollowUpInterpretationContractV1(_StrictModel):
    schema_version: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    event_schema_version: str = Field(min_length=1)
    policy_kind: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    limitation: str = Field(min_length=1)
    timepoint_order: list[str] = Field(min_length=4, max_length=4)
    scheduled_day_index_by_timepoint: dict[str, StrictInt | None]
    adherence: PROFollowUpAdherenceContractV1
    interpretation_priority: list[str] = Field(min_length=5, max_length=5)
    effect_claim_scope: str = Field(min_length=1)
    causal_effect_claim_allowed: bool
    persistence: PROFollowUpPersistenceContractV1


_EXPECTED_PRO_FOLLOWUP_INTERPRETATION_CONTRACT_V1 = {
    "schema_version": "pro_followup_interpretation_contract_v1",
    "contract_version": PRO_FOLLOWUP_INTERPRETATION_CONTRACT_VERSION_V1,
    "event_schema_version": PRO_FOLLOWUP_EVENT_SCHEMA_VERSION_V1,
    "policy_kind": "conservative_internal_interpretation_policy",
    "source_refs": [
        "data/original_plan/requirements_manifest_v1.json#OP-053",
        "data/original_plan/requirements_manifest_v1.json#OP-054",
        "docs/context/master_context.md#19.3",
        "docs/context/master_context.md#21.2",
    ],
    "limitation": (
        "The 0.8 threshold limits interpretation only. It is not a clinical cutoff "
        "and does not prove causal efficacy."
    ),
    "timepoint_order": ["pre_intake", "week_2", "week_4", "discontinuation"],
    "scheduled_day_index_by_timepoint": _SCHEDULED_DAY_BY_TIMEPOINT,
    "adherence": {
        "minimum_interpretable_rate": PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1,
        "rate_precision_decimal_places": 6,
        "count_reconciliation": (
            "planned_dose_count=taken_dose_count+missed_dose_count"
        ),
    },
    "interpretation_priority": [
        "serious_adverse_event_present",
        "adverse_event_present",
        "adherence_below_80_percent",
        "missed_doses_present",
        "observed_change_interpretable",
    ],
    "effect_claim_scope": "observed_association_not_causal",
    "causal_effect_claim_allowed": False,
    "persistence": {
        "table": "execution_events",
        "event_type": "followup_evaluation",
        "versioned_payload_required_for_pro_claim": True,
    },
}


class PROAdherenceWindowV1(_StrictModel):
    planned_dose_count: StrictInt = Field(ge=0)
    taken_dose_count: StrictInt = Field(ge=0)
    missed_dose_count: StrictInt = Field(ge=0)
    adherence_rate: float = Field(strict=True, ge=0.0, le=1.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_counts(self) -> PROAdherenceWindowV1:
        if self.taken_dose_count + self.missed_dose_count != self.planned_dose_count:
            raise ValueError("planned doses must equal taken plus missed doses")
        expected_rate = (
            0.0
            if self.planned_dose_count == 0
            else round(self.taken_dose_count / self.planned_dose_count, 6)
        )
        if abs(self.adherence_rate - expected_rate) > 1e-6:
            raise ValueError("adherence rate does not match reconciled dose counts")
        return self


class PROAdverseEventContextV1(_StrictModel):
    adverse_event_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]+$",
    )
    severity: Literal["mild", "moderate", "severe", "serious"]
    relatedness: Literal["not_related", "unlikely", "possible", "probable", "unknown"]
    ongoing: bool


class PROFollowUpEventV1(_StrictModel):
    schema_version: Literal["versioned_pro_followup_event_v1"]
    assessment_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]+$",
    )
    plan_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]+$",
    )
    data_class: DataClass
    timepoint: PROFollowUpTimepointV1
    scheduled_day_index: StrictInt | None
    actual_day_index: StrictInt = Field(ge=0)
    observed_at: datetime
    instrument_scores: list[PROInstrumentScoreV1] = Field(min_length=1, max_length=3)
    standardized_scores: list[PROStandardizedScoreV1] = Field(min_length=1, max_length=3)
    adherence: PROAdherenceWindowV1 | None = None
    adverse_events: list[PROAdverseEventContextV1] = Field(
        default_factory=list,
        max_length=20,
    )
    discontinuation_reason: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )

    @model_validator(mode="after")
    def validate_event(self) -> PROFollowUpEventV1:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        expected_scheduled_day = _SCHEDULED_DAY_BY_TIMEPOINT[self.timepoint]
        if self.scheduled_day_index != expected_scheduled_day:
            raise ValueError("scheduled day does not match the declared timepoint")
        if (
            expected_scheduled_day is not None
            and self.actual_day_index < expected_scheduled_day
        ):
            raise ValueError("actual day cannot precede the scheduled timepoint")
        if self.timepoint == "pre_intake":
            if self.actual_day_index != 0:
                raise ValueError("pre-intake actual day must be zero")
            if self.adherence is not None:
                raise ValueError("pre-intake event cannot contain an adherence window")
            if self.adverse_events:
                raise ValueError("pre-intake event cannot attribute adverse events to the plan")
        else:
            if self.adherence is None or self.adherence.planned_dose_count < 1:
                raise ValueError("post-intake event requires a positive adherence window")
        if self.timepoint == "discontinuation":
            if self.discontinuation_reason is None or not self.discontinuation_reason.strip():
                raise ValueError("discontinuation event requires a reason")
        elif self.discontinuation_reason is not None:
            raise ValueError("only discontinuation events may contain a discontinuation reason")

        scores_by_instrument = _unique_by_instrument(
            self.instrument_scores,
            value_name="instrument score",
        )
        standardized_by_instrument = _unique_by_instrument(
            self.standardized_scores,
            value_name="standardized score",
        )
        if set(scores_by_instrument) != set(standardized_by_instrument):
            raise ValueError("instrument and standardized score sets differ")
        for instrument, score in scores_by_instrument.items():
            standardized = standardized_by_instrument[instrument]
            if score.raw_score != standardized.raw_score:
                raise ValueError("instrument raw score does not match standardized score")
            if score.contract_version != standardized.contract_version:
                raise ValueError("instrument contract version does not match standardized score")
            if score.scoring_version != standardized.instrument_scoring_version:
                raise ValueError("instrument scoring version does not match standardized score")

        adverse_event_ids = [item.adverse_event_id for item in self.adverse_events]
        if len(adverse_event_ids) != len(set(adverse_event_ids)):
            raise ValueError("duplicate adverse event ID")
        return self


class PROInstrumentObservedChangeV1(_StrictModel):
    instrument: PROInstrumentIdV1
    baseline_raw_problem_score: StrictInt
    follow_up_raw_problem_score: StrictInt
    raw_problem_score_change: StrictInt
    baseline_health_z_score: float = Field(allow_inf_nan=False)
    follow_up_health_z_score: float = Field(allow_inf_nan=False)
    health_z_change: float = Field(allow_inf_nan=False)
    baseline_health_percentile: float = Field(ge=0.0, le=100.0, allow_inf_nan=False)
    follow_up_health_percentile: float = Field(ge=0.0, le=100.0, allow_inf_nan=False)
    health_percentile_change: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_change(self) -> PROInstrumentObservedChangeV1:
        if (
            self.raw_problem_score_change
            != self.follow_up_raw_problem_score - self.baseline_raw_problem_score
        ):
            raise ValueError("raw problem score change does not match source scores")
        expected_z_change = round(
            self.follow_up_health_z_score - self.baseline_health_z_score,
            6,
        )
        if abs(self.health_z_change - expected_z_change) > 1e-6:
            raise ValueError("health Z change does not match source scores")
        expected_percentile_change = round(
            self.follow_up_health_percentile - self.baseline_health_percentile,
            6,
        )
        if abs(self.health_percentile_change - expected_percentile_change) > 1e-6:
            raise ValueError("health percentile change does not match source scores")
        return self


class PROFollowUpEffectInterpretationV1(_StrictModel):
    schema_version: Literal["pro_followup_effect_interpretation_v1"]
    interpretation_policy_version: Literal["2026-07-17.1"]
    baseline_event: PROFollowUpEventV1
    follow_up_event: PROFollowUpEventV1
    instrument_changes: list[PROInstrumentObservedChangeV1] = Field(min_length=1)
    mean_health_z_change: float = Field(allow_inf_nan=False)
    observed_change_status: Literal["improved", "worsened", "no_material_change"]
    adherence_rate: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    missed_dose_count: StrictInt = Field(ge=0)
    adverse_event_count: StrictInt = Field(ge=0)
    serious_adverse_event_present: bool
    interpretation_status: PROInterpretationStatusV1
    interpretation_reason_codes: list[str]
    benefit_interpretation_allowed: bool
    causal_effect_claim_allowed: Literal[False]
    effect_claim_scope: Literal["observed_association_not_causal"]

    @model_validator(mode="after")
    def validate_interpretation(self) -> PROFollowUpEffectInterpretationV1:
        expected = _derive_interpretation_fields(
            self.baseline_event,
            self.follow_up_event,
        )
        actual = {
            "instrument_changes": self.instrument_changes,
            "mean_health_z_change": self.mean_health_z_change,
            "observed_change_status": self.observed_change_status,
            "adherence_rate": self.adherence_rate,
            "missed_dose_count": self.missed_dose_count,
            "adverse_event_count": self.adverse_event_count,
            "serious_adverse_event_present": self.serious_adverse_event_present,
            "interpretation_status": self.interpretation_status,
            "interpretation_reason_codes": self.interpretation_reason_codes,
            "benefit_interpretation_allowed": self.benefit_interpretation_allowed,
        }
        if actual != expected:
            raise ValueError("effect interpretation does not match source events")
        return self


def is_versioned_pro_followup_payload_v1(payload: object) -> bool:
    if isinstance(payload, PROFollowUpEventV1):
        return True
    if not isinstance(payload, dict):
        return False
    return (
        payload.get("schema_version") == PRO_FOLLOWUP_EVENT_SCHEMA_VERSION_V1
        or _VERSIONED_PRO_PAYLOAD_DISCRIMINATORS <= set(payload)
    )


def load_pro_followup_interpretation_contract_v1(
    path: str | Path = DEFAULT_PRO_FOLLOWUP_INTERPRETATION_CONTRACT_PATH,
) -> PROFollowUpInterpretationContractV1:
    try:
        contract = PROFollowUpInterpretationContractV1.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_pro_followup_interpretation_contract::{exc}") from exc
    if (
        contract.model_dump(mode="json")
        != _EXPECTED_PRO_FOLLOWUP_INTERPRETATION_CONTRACT_V1
    ):
        raise ValueError("invalid_pro_followup_interpretation_contract::policy_drift")
    return contract


def normalize_pro_followup_event_v1(
    event: PROFollowUpEventV1 | dict[str, object],
    *,
    contract_path: str | Path = DEFAULT_PRO_FOLLOWUP_INTERPRETATION_CONTRACT_PATH,
) -> PROFollowUpEventV1:
    load_pro_followup_interpretation_contract_v1(contract_path)
    return PROFollowUpEventV1.model_validate(event)


def validate_pro_followup_sequence_v1(
    existing_events: list[PROFollowUpEventV1 | dict[str, object]],
    candidate_event: PROFollowUpEventV1 | dict[str, object],
) -> list[str]:
    existing = [normalize_pro_followup_event_v1(item) for item in existing_events]
    candidate = normalize_pro_followup_event_v1(candidate_event)
    issues: list[str] = []
    if not existing:
        if candidate.timepoint != "pre_intake":
            issues.append("first_pro_followup_event_must_be_pre_intake")
        return issues

    if existing[0].timepoint != "pre_intake":
        issues.append("existing_pro_followup_sequence_missing_pre_intake")
    allowed_next = {
        "pre_intake": {"week_2", "discontinuation"},
        "week_2": {"week_4", "discontinuation"},
        "week_4": {"discontinuation"},
        "discontinuation": set(),
    }
    for previous, current in zip(existing, existing[1:], strict=False):
        if current.timepoint not in allowed_next[previous.timepoint]:
            issues.append(
                "invalid_existing_pro_followup_transition::"
                f"{previous.timepoint}::{current.timepoint}"
            )
        if current.actual_day_index <= previous.actual_day_index:
            issues.append("existing_pro_followup_actual_day_not_increasing")
        if current.observed_at <= previous.observed_at:
            issues.append("existing_pro_followup_observed_at_not_increasing")

    if any(item.plan_id != candidate.plan_id for item in existing):
        issues.append("pro_followup_plan_mismatch")
    if any(item.data_class != candidate.data_class for item in existing):
        issues.append("pro_followup_data_class_mismatch")
    prior_timepoints = [item.timepoint for item in existing]
    if candidate.timepoint in prior_timepoints:
        issues.append(f"duplicate_pro_followup_timepoint::{candidate.timepoint}")
    if any(item.assessment_id == candidate.assessment_id for item in existing):
        issues.append(f"duplicate_pro_followup_assessment_id::{candidate.assessment_id}")
    reference_identity = _longitudinal_score_identity(existing[0])
    if _longitudinal_score_identity(candidate) != reference_identity:
        issues.append("pro_followup_longitudinal_score_identity_mismatch")
    last = existing[-1]
    if last.timepoint == "discontinuation":
        issues.append("pro_followup_event_after_discontinuation")
    if candidate.timepoint not in allowed_next[last.timepoint]:
        issues.append(
            f"invalid_pro_followup_transition::{last.timepoint}::{candidate.timepoint}"
        )
    if candidate.actual_day_index <= last.actual_day_index:
        issues.append("pro_followup_actual_day_must_increase")
    if candidate.observed_at <= last.observed_at:
        issues.append("pro_followup_observed_at_must_increase")
    return issues


def interpret_pro_followup_effect_v1(
    baseline_event: PROFollowUpEventV1 | dict[str, object],
    follow_up_event: PROFollowUpEventV1 | dict[str, object],
    *,
    contract_path: str | Path = DEFAULT_PRO_FOLLOWUP_INTERPRETATION_CONTRACT_PATH,
) -> PROFollowUpEffectInterpretationV1:
    contract = load_pro_followup_interpretation_contract_v1(contract_path)
    baseline = normalize_pro_followup_event_v1(
        baseline_event,
        contract_path=contract_path,
    )
    follow_up = normalize_pro_followup_event_v1(
        follow_up_event,
        contract_path=contract_path,
    )
    fields = _derive_interpretation_fields(baseline, follow_up)
    return PROFollowUpEffectInterpretationV1(
        schema_version=PRO_FOLLOWUP_EFFECT_INTERPRETATION_SCHEMA_VERSION_V1,
        interpretation_policy_version=contract.contract_version,
        baseline_event=baseline,
        follow_up_event=follow_up,
        causal_effect_claim_allowed=False,
        effect_claim_scope="observed_association_not_causal",
        **fields,
    )


def _derive_interpretation_fields(
    baseline: PROFollowUpEventV1,
    follow_up: PROFollowUpEventV1,
) -> dict[str, object]:
    _validate_interpretation_pair(baseline, follow_up)
    baseline_by_instrument = {
        item.instrument: item for item in baseline.standardized_scores
    }
    follow_up_by_instrument = {
        item.instrument: item for item in follow_up.standardized_scores
    }
    changes = [
        PROInstrumentObservedChangeV1(
            instrument=instrument,
            baseline_raw_problem_score=baseline_by_instrument[instrument].raw_score,
            follow_up_raw_problem_score=follow_up_by_instrument[instrument].raw_score,
            raw_problem_score_change=(
                follow_up_by_instrument[instrument].raw_score
                - baseline_by_instrument[instrument].raw_score
            ),
            baseline_health_z_score=baseline_by_instrument[instrument].health_z_score,
            follow_up_health_z_score=follow_up_by_instrument[instrument].health_z_score,
            health_z_change=round(
                follow_up_by_instrument[instrument].health_z_score
                - baseline_by_instrument[instrument].health_z_score,
                6,
            ),
            baseline_health_percentile=(
                baseline_by_instrument[instrument].health_percentile
            ),
            follow_up_health_percentile=(
                follow_up_by_instrument[instrument].health_percentile
            ),
            health_percentile_change=round(
                follow_up_by_instrument[instrument].health_percentile
                - baseline_by_instrument[instrument].health_percentile,
                6,
            ),
        )
        for instrument in sorted(baseline_by_instrument)
    ]
    mean_health_z_change = round(
        sum(item.health_z_change for item in changes) / len(changes),
        6,
    )
    if mean_health_z_change > PRO_FOLLOWUP_CHANGE_TOLERANCE_V1:
        observed_change_status = "improved"
    elif mean_health_z_change < -PRO_FOLLOWUP_CHANGE_TOLERANCE_V1:
        observed_change_status = "worsened"
    else:
        observed_change_status = "no_material_change"

    adherence = follow_up.adherence
    if adherence is None:
        raise ValueError("follow-up interpretation requires adherence context")
    adverse_event_count = len(follow_up.adverse_events)
    serious_adverse_event_present = any(
        item.severity == "serious" for item in follow_up.adverse_events
    )
    reason_codes: list[str] = []
    if adherence.missed_dose_count:
        reason_codes.append("missed_doses_present")
    if adherence.adherence_rate < PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1:
        reason_codes.append("adherence_below_80_percent")
    if adverse_event_count:
        reason_codes.append("adverse_event_present")
    if serious_adverse_event_present:
        reason_codes.append("serious_adverse_event_present")

    if serious_adverse_event_present:
        interpretation_status = "safety_escalation_required"
    elif adverse_event_count:
        interpretation_status = "safety_context_required"
    elif adherence.adherence_rate < PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1:
        interpretation_status = "limited_by_low_adherence"
    elif adherence.missed_dose_count:
        interpretation_status = "limited_by_missed_doses"
    else:
        interpretation_status = "observed_change_interpretable"
    return {
        "instrument_changes": changes,
        "mean_health_z_change": mean_health_z_change,
        "observed_change_status": observed_change_status,
        "adherence_rate": adherence.adherence_rate,
        "missed_dose_count": adherence.missed_dose_count,
        "adverse_event_count": adverse_event_count,
        "serious_adverse_event_present": serious_adverse_event_present,
        "interpretation_status": interpretation_status,
        "interpretation_reason_codes": reason_codes,
        "benefit_interpretation_allowed": not reason_codes,
    }


def _validate_interpretation_pair(
    baseline: PROFollowUpEventV1,
    follow_up: PROFollowUpEventV1,
) -> None:
    if baseline.timepoint != "pre_intake":
        raise ValueError("baseline interpretation event must be pre_intake")
    if follow_up.timepoint == "pre_intake":
        raise ValueError("follow-up interpretation event cannot be pre_intake")
    if baseline.assessment_id == follow_up.assessment_id:
        raise ValueError("pro follow-up assessment ID must differ from baseline")
    if follow_up.actual_day_index <= baseline.actual_day_index:
        raise ValueError("follow-up actual day must be after baseline")
    if follow_up.observed_at <= baseline.observed_at:
        raise ValueError("follow-up observed_at must be after baseline")
    if baseline.plan_id != follow_up.plan_id:
        raise ValueError("pro follow-up plan mismatch")
    if baseline.data_class != follow_up.data_class:
        raise ValueError("pro follow-up data class mismatch")
    baseline_by_instrument = {
        item.instrument: item for item in baseline.standardized_scores
    }
    follow_up_by_instrument = {
        item.instrument: item for item in follow_up.standardized_scores
    }
    if set(baseline_by_instrument) != set(follow_up_by_instrument):
        raise ValueError("pro follow-up instrument set mismatch")
    for instrument, baseline_score in baseline_by_instrument.items():
        follow_up_score = follow_up_by_instrument[instrument]
        if (
            baseline_score.contract_version != follow_up_score.contract_version
            or baseline_score.instrument_scoring_version
            != follow_up_score.instrument_scoring_version
        ):
            raise ValueError("pro follow-up scoring version mismatch")
        if (
            baseline_score.baseline_distribution.source_scores_sha256
            != follow_up_score.baseline_distribution.source_scores_sha256
        ):
            raise ValueError("pro follow-up baseline distribution mismatch")


def _unique_by_instrument(
    values: list[_PROScore],
    *,
    value_name: str,
) -> dict[str, _PROScore]:
    result: dict[str, _PROScore] = {}
    for value in values:
        instrument = value.instrument
        if instrument in result:
            raise ValueError(f"duplicate {value_name} instrument::{instrument}")
        result[instrument] = value
    return result


def _longitudinal_score_identity(
    event: PROFollowUpEventV1,
) -> dict[str, tuple[str, str, str]]:
    return {
        item.instrument: (
            item.contract_version,
            item.instrument_scoring_version,
            item.baseline_distribution.source_scores_sha256,
        )
        for item in event.standardized_scores
    }


__all__ = [
    "PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1",
    "PRO_FOLLOWUP_EFFECT_INTERPRETATION_SCHEMA_VERSION_V1",
    "PRO_FOLLOWUP_EVENT_SCHEMA_VERSION_V1",
    "PRO_FOLLOWUP_INTERPRETATION_CONTRACT_VERSION_V1",
    "PROAdherenceWindowV1",
    "PROAdverseEventContextV1",
    "PROFollowUpEffectInterpretationV1",
    "PROFollowUpEventV1",
    "PROFollowUpInterpretationContractV1",
    "PROInstrumentObservedChangeV1",
    "interpret_pro_followup_effect_v1",
    "is_versioned_pro_followup_payload_v1",
    "load_pro_followup_interpretation_contract_v1",
    "normalize_pro_followup_event_v1",
    "validate_pro_followup_sequence_v1",
]
