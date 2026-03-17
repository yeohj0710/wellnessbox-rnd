from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np
from pydantic import BaseModel, Field

from wellnessbox_rnd.models.effect_model_v1 import (
    EffectFeatureVectorizerV1,
    EffectModelV1Artifact,
    predict_aggregate_delta_v1,
    predict_domain_deltas_v1,
    predict_policy_effect_proxy_v1,
)
from wellnessbox_rnd.schemas.recommendation import RecommendationGoal

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord


class EffectEvaluationMetricsV1(BaseModel):
    mean_domain_mae: float
    mean_domain_rmse: float
    aggregate_mae: float
    aggregate_rmse: float
    aggregate_r2: float
    policy_proxy_mae: float
    policy_proxy_rmse: float
    zero_baseline_mean_domain_mae: float
    zero_baseline_aggregate_mae: float
    zero_baseline_policy_proxy_mae: float
    domain_mae: dict[str, float]


@dataclass(frozen=True)
class EffectSplitResultV1:
    train: list[RichSyntheticCohortRecord]
    val: list[RichSyntheticCohortRecord]
    test: list[RichSyntheticCohortRecord]


class EffectDatasetSnapshotV1(BaseModel):
    domain_z: dict[str, float] = Field(default_factory=dict)
    aggregate_z: float


class EffectDatasetRecommendedItemV1(BaseModel):
    ingredient_key: str
    daily_dose: float = Field(ge=0.0)
    dose_unit: str
    schedule: str
    regimen_status: Literal["planned", "active", "reduced", "stopped"]


class EffectDatasetPeriodV1(BaseModel):
    trajectory_step: int = Field(ge=0)
    start_day_index: int = Field(ge=0)
    end_day_index: int = Field(ge=0)
    days_from_baseline: int = Field(ge=0)


class EffectDatasetInputFlagsV1(BaseModel):
    survey: bool
    nhis: bool
    wearable: bool
    cgm: bool
    genetic: bool


class EffectDatasetProvenanceV1(BaseModel):
    source_request_id: str
    rng_seed: int
    trajectory_mode: str


class EffectDatasetResponseProfileV1(BaseModel):
    trajectory_mode: str
    response_family: str
    response_strength_band: Literal["weak", "moderate", "strong"]
    adherence_band: Literal["low", "moderate", "high"]
    tolerability_band: Literal["low", "moderate", "elevated"]
    modality_signature: str


class EffectDatasetPairRowV1(BaseModel):
    pair_id: str
    source_record_id: str
    user_id: str
    cohort_version: str
    goal: str
    baseline: EffectDatasetSnapshotV1
    follow_up: EffectDatasetSnapshotV1
    recommended_set: list[EffectDatasetRecommendedItemV1] = Field(default_factory=list)
    period: EffectDatasetPeriodV1
    adverse_event: bool
    expected_effect_proxy: float = Field(ge=-1.0, le=1.0)
    adherence_proxy: float = Field(ge=0.0, le=1.0)
    side_effect_proxy: float = Field(ge=0.0, le=1.0)
    next_action: str
    risk_tier: str
    input_flags: EffectDatasetInputFlagsV1
    provenance: EffectDatasetProvenanceV1
    response_profile: EffectDatasetResponseProfileV1


EFFECT_DATASET_PAIR_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "pair_id",
    "source_record_id",
    "user_id",
    "cohort_version",
    "goal",
    "baseline",
    "follow_up",
    "recommended_set",
    "period",
    "adverse_event",
    "expected_effect_proxy",
    "adherence_proxy",
    "side_effect_proxy",
    "next_action",
    "risk_tier",
    "input_flags",
    "provenance",
    "response_profile",
)

EFFECT_TRAINING_VIEW_FORBIDDEN_FEATURE_NAMES: tuple[str, ...] = (
    "adherence_proxy",
    "side_effect_proxy",
    "risk_tier_high",
    "risk_tier_moderate",
    "risk_tier_low",
)

EFFECT_TRAINING_ALLOWED_SOURCE_FIELDS_V1: tuple[str, ...] = (
    "goal",
    "baseline",
    "input_flags",
    "recommended_set",
    "period",
)

EFFECT_TRAINING_FORBIDDEN_LEAKAGE_FAMILY_PATTERNS_V1: dict[str, tuple[str, ...]] = {
    "follow_up": ("follow_up::", "follow_up_aggregate_z"),
    "adverse_event": ("adverse_event",),
    "expected_effect_proxy": ("expected_effect_proxy",),
    "adherence_proxy": ("adherence_proxy",),
    "side_effect_proxy": ("side_effect_proxy",),
    "next_action": ("next_action::", "next_action_"),
    "risk_tier": ("risk_tier_",),
    "response_profile": (
        "response_profile::",
        "response_family::",
        "response_strength_band::",
        "adherence_band::",
        "tolerability_band::",
        "modality_signature::",
    ),
}

DEFAULT_EFFECT_VALIDATION_SELECTION_PROFILE_V1 = "aggregate_mae_v1"


def build_effect_dataset_training_view_contract_v1() -> dict[str, object]:
    metadata_fields = [
        "pair_id",
        "source_record_id",
        "user_id",
        "cohort_version",
        "provenance",
    ]
    baseline_fact_fields = [
        "goal",
        "baseline",
        "input_flags",
    ]
    intervention_assignment_fields = [
        "recommended_set",
        "period",
    ]
    follow_up_outcome_fields = [
        "follow_up",
        "adverse_event",
        "expected_effect_proxy",
        "adherence_proxy",
        "side_effect_proxy",
        "next_action",
        "risk_tier",
        "response_profile",
    ]
    training_input_allowed_fields = (
        baseline_fact_fields + intervention_assignment_fields
    )
    training_input_forbidden_fields = follow_up_outcome_fields.copy()
    return {
        "contract_version": "dataset_f_effect_training_view_v1",
        "metadata_fields": metadata_fields,
        "baseline_fact_fields": baseline_fact_fields,
        "intervention_assignment_fields": intervention_assignment_fields,
        "follow_up_outcome_fields": follow_up_outcome_fields,
        "training_input_allowed_fields": training_input_allowed_fields,
        "training_input_forbidden_fields": training_input_forbidden_fields,
    }


def load_rich_effect_records(
    path: str | Path,
) -> list[RichSyntheticCohortRecord]:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord

    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(RichSyntheticCohortRecord.model_validate_json(line))
    return rows


def build_effect_dataset_pair_row_v1(
    record: RichSyntheticCohortRecord,
) -> EffectDatasetPairRowV1:
    goal = record.request.goals[0].value if record.request.goals else "unknown"
    return EffectDatasetPairRowV1(
        pair_id=record.record_id,
        source_record_id=record.record_id,
        user_id=record.user_id,
        cohort_version=record.cohort_version,
        goal=goal,
        baseline=EffectDatasetSnapshotV1.model_validate(
            record.baseline_pro.model_dump(mode="json")
        ),
        follow_up=EffectDatasetSnapshotV1.model_validate(
            record.follow_up_pro.model_dump(mode="json")
        ),
        recommended_set=[
            EffectDatasetRecommendedItemV1(
                ingredient_key=item.ingredient_key,
                daily_dose=item.daily_dose,
                dose_unit=item.dose_unit,
                schedule=item.schedule,
                regimen_status=item.regimen_status,
            )
            for item in record.regimen
        ],
        period=EffectDatasetPeriodV1(
            trajectory_step=record.trajectory_step,
            start_day_index=0,
            end_day_index=record.day_index,
            days_from_baseline=record.day_index,
        ),
        adverse_event=record.labels.adverse_event,
        expected_effect_proxy=record.expected_effect_proxy,
        adherence_proxy=record.adherence_proxy,
        side_effect_proxy=record.side_effect_proxy,
        next_action=record.labels.next_action.value,
        risk_tier=record.labels.risk_tier,
        input_flags=EffectDatasetInputFlagsV1.model_validate(
            record.request.input_availability.model_dump(mode="json")
        ),
        provenance=EffectDatasetProvenanceV1(
            source_request_id=record.request.request_id,
            rng_seed=record.rng_seed,
            trajectory_mode=record.trajectory_mode,
        ),
        response_profile=build_effect_dataset_response_profile_v1(record),
    )


def build_effect_dataset_pairs_v1(
    records: list[RichSyntheticCohortRecord],
) -> list[EffectDatasetPairRowV1]:
    return [build_effect_dataset_pair_row_v1(record) for record in records]


def load_effect_dataset_pairs_v1(
    path: str | Path,
) -> list[EffectDatasetPairRowV1]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(EffectDatasetPairRowV1.model_validate_json(line))
    return rows


def validate_effect_dataset_pairs_v1(
    rows: list[EffectDatasetPairRowV1],
) -> list[str]:
    issues: list[str] = []
    pair_ids = [row.pair_id for row in rows]
    if pair_ids != sorted(pair_ids):
        issues.append("pair ordering is not sorted by pair_id")
    if len(pair_ids) != len(set(pair_ids)):
        issues.append("duplicate pair_id values detected")
    for row in rows:
        if not row.baseline.domain_z:
            issues.append(f"baseline domain_z missing: {row.pair_id}")
        if not row.follow_up.domain_z:
            issues.append(f"follow_up domain_z missing: {row.pair_id}")
        if not row.recommended_set:
            issues.append(f"recommended_set missing: {row.pair_id}")
        if row.period.end_day_index < row.period.start_day_index:
            issues.append(f"period day indices invalid: {row.pair_id}")
        expected_days = row.period.end_day_index - row.period.start_day_index
        if row.period.days_from_baseline != expected_days:
            issues.append(f"period days_from_baseline mismatch: {row.pair_id}")
        if not row.provenance.source_request_id:
            issues.append(f"provenance source_request_id missing: {row.pair_id}")
        if row.provenance.rng_seed < 0:
            issues.append(f"provenance rng_seed invalid: {row.pair_id}")
        if not row.provenance.trajectory_mode:
            issues.append(f"provenance trajectory_mode missing: {row.pair_id}")
        if row.response_profile.trajectory_mode != row.provenance.trajectory_mode:
            issues.append(f"response_profile trajectory_mode mismatch: {row.pair_id}")
        if not row.response_profile.response_family:
            issues.append(f"response_profile response_family missing: {row.pair_id}")
        if (
            row.response_profile.modality_signature
            != _build_effect_dataset_modality_signature_v1(row.input_flags)
        ):
            issues.append(f"response_profile modality_signature mismatch: {row.pair_id}")
        if not row.input_flags.survey:
            issues.append(f"survey input flag must remain true: {row.pair_id}")
    return issues


def validate_effect_dataset_training_view_contract_v1(
    rows: list[EffectDatasetPairRowV1],
) -> list[str]:
    contract = build_effect_dataset_training_view_contract_v1()
    issues: list[str] = []
    grouped_fields = (
        contract["metadata_fields"]
        + contract["baseline_fact_fields"]
        + contract["intervention_assignment_fields"]
        + contract["follow_up_outcome_fields"]
    )
    grouped_field_set = set(grouped_fields)
    expected_field_set = set(EFFECT_DATASET_PAIR_TOP_LEVEL_FIELDS)
    if grouped_field_set != expected_field_set:
        issues.append("training-view contract does not cover the full pair-row field set")
    if len(grouped_fields) != len(grouped_field_set):
        issues.append("training-view contract assigns some fields to multiple stages")

    allowed_fields = set(contract["training_input_allowed_fields"])
    forbidden_fields = set(contract["training_input_forbidden_fields"])
    overlap = sorted(allowed_fields & forbidden_fields)
    if overlap:
        issues.append(
            "training-view contract overlaps allowed and forbidden fields: "
            + ", ".join(overlap)
        )

    for field_name in sorted(grouped_field_set):
        if not rows:
            break
        if field_name not in rows[0].model_dump(mode="json"):
            issues.append(f"training-view contract field missing from pair row: {field_name}")
    return issues


def build_effect_dataset_response_profile_v1(
    record: RichSyntheticCohortRecord,
) -> EffectDatasetResponseProfileV1:
    return EffectDatasetResponseProfileV1(
        trajectory_mode=record.trajectory_mode,
        response_family=_effect_dataset_response_family_v1(record.trajectory_mode),
        response_strength_band=_effect_dataset_response_strength_band_v1(
            record.expected_effect_proxy
        ),
        adherence_band=_effect_dataset_adherence_band_v1(record.adherence_proxy),
        tolerability_band=_effect_dataset_tolerability_band_v1(record.side_effect_proxy),
        modality_signature=_build_effect_dataset_modality_signature_v1(
            EffectDatasetInputFlagsV1.model_validate(
                record.request.input_availability.model_dump(mode="json")
            )
        ),
    )


def _effect_dataset_response_family_v1(trajectory_mode: str) -> str:
    return {
        "reduce_side_effect": "tolerability_limited",
        "safety_recheck_high_risk": "safety_blocked",
        "threshold_continue_primary": "stable_responder",
        "threshold_monitor_secondary": "monitor_plateau",
        "threshold_reopt_edge": "low_response_edge",
        "threshold_cgm_balance": "cgm_threshold_sensitive",
        "threshold_delayed_flip": "delayed_response",
        "threshold_duration_sensitive": "duration_sensitive",
        "threshold_adherence_recovery": "adherence_limited_recovery",
    }.get(trajectory_mode, "other")


def _effect_dataset_response_strength_band_v1(
    expected_effect_proxy: float,
) -> Literal["weak", "moderate", "strong"]:
    if expected_effect_proxy >= 0.33:
        return "strong"
    if expected_effect_proxy >= 0.18:
        return "moderate"
    return "weak"


def _effect_dataset_adherence_band_v1(
    adherence_proxy: float,
) -> Literal["low", "moderate", "high"]:
    if adherence_proxy >= 0.75:
        return "high"
    if adherence_proxy >= 0.6:
        return "moderate"
    return "low"


def _effect_dataset_tolerability_band_v1(
    side_effect_proxy: float,
) -> Literal["low", "moderate", "elevated"]:
    if side_effect_proxy >= 0.45:
        return "elevated"
    if side_effect_proxy >= 0.2:
        return "moderate"
    return "low"


def _build_effect_dataset_modality_signature_v1(
    input_flags: EffectDatasetInputFlagsV1,
) -> str:
    enabled_modalities = [
        name
        for name in ("survey", "nhis", "wearable", "cgm", "genetic")
        if getattr(input_flags, name)
    ]
    return "+".join(enabled_modalities)


def split_effect_records_by_user_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
) -> EffectSplitResultV1:
    grouped: dict[str, list[RichSyntheticCohortRecord]] = {}
    for record in records:
        grouped.setdefault(record.user_id, []).append(record)

    buckets: dict[str, list[RichSyntheticCohortRecord]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    for user_id in sorted(grouped):
        digest = hashlib.sha256(f"{seed}:{user_id}".encode()).digest()[0]
        ratio = digest / 255.0
        split_name = "train" if ratio < 0.6 else "val" if ratio < 0.8 else "test"
        buckets[split_name].extend(grouped[user_id])

    return EffectSplitResultV1(
        train=sorted(buckets["train"], key=lambda item: item.record_id),
        val=sorted(buckets["val"], key=lambda item: item.record_id),
        test=sorted(buckets["test"], key=lambda item: item.record_id),
    )


def fit_effect_model_v1(
    train_records: list[RichSyntheticCohortRecord],
    val_records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
    alpha_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 5.0, 10.0),
    validation_selection_profile: str = DEFAULT_EFFECT_VALIDATION_SELECTION_PROFILE_V1,
    validation_selection_tolerance: float = 0.0,
) -> tuple[EffectModelV1Artifact, dict[str, EffectEvaluationMetricsV1]]:
    train_pair_rows = build_effect_dataset_pairs_v1(train_records)
    val_pair_rows = build_effect_dataset_pairs_v1(val_records)
    training_view_issues = validate_effect_dataset_training_view_contract_v1(
        train_pair_rows + val_pair_rows
    )
    if training_view_issues:
        raise ValueError(
            "dataset_f_effect_training_view_v1 violation: "
            + "; ".join(training_view_issues)
        )

    train_rows = [
        build_effect_training_feature_dict_v1(pair_row) for pair_row in train_pair_rows
    ]
    vectorizer = EffectFeatureVectorizerV1.fit(train_rows)
    output_names = sorted(train_records[0].delta_z_by_domain) if train_records else []

    x_train = np.asarray(vectorizer.transform(train_rows), dtype=float)
    y_train = _build_target_matrix(train_records, output_names)

    best_artifact: EffectModelV1Artifact | None = None
    best_val_metrics: EffectEvaluationMetricsV1 | None = None
    best_train_metrics: EffectEvaluationMetricsV1 | None = None
    best_selection_score: float | None = None
    best_selection_summary: dict[str, object] | None = None
    alpha_search: list[dict[str, object]] = []

    for alpha in alpha_grid:
        weights, intercepts = _fit_multitarget_ridge(x_train, y_train, alpha=alpha)
        artifact = EffectModelV1Artifact(
            cohort_version=train_records[0].cohort_version if train_records else "unknown",
            seed=seed,
            alpha=alpha,
            feature_names=vectorizer.feature_names,
            output_names=output_names,
            intercepts=[round(float(value), 8) for value in intercepts],
            weights=[
                [round(float(weight), 8) for weight in output_weights]
                for output_weights in weights
            ],
            validation_selection_profile=validation_selection_profile,
            validation_selection_tolerance=round(float(validation_selection_tolerance), 6),
        )
        train_metrics = evaluate_effect_model_v1(artifact, train_records)
        val_metrics = evaluate_effect_model_v1(artifact, val_records)
        selection_summary = build_effect_validation_selection_summary_v1(
            artifact,
            val_records=val_records,
            val_metrics=val_metrics,
            profile=validation_selection_profile,
        )
        selection_score = float(selection_summary["selection_score"])
        alpha_search.append(
            {
                "alpha": round(float(alpha), 6),
                **selection_summary,
            }
        )
        if _is_better_effect_validation_candidate_v1(
            candidate_score=selection_score,
            candidate_alpha=alpha,
            best_score=best_selection_score,
            best_alpha=best_artifact.alpha if best_artifact is not None else None,
            tolerance=validation_selection_tolerance,
        ):
            best_artifact = artifact
            best_val_metrics = val_metrics
            best_train_metrics = train_metrics
            best_selection_score = selection_score
            best_selection_summary = selection_summary

    assert best_artifact is not None
    assert best_val_metrics is not None
    assert best_train_metrics is not None
    assert best_selection_summary is not None
    calibrated_artifact = _fit_policy_proxy_calibration(
        best_artifact,
        train_records=train_records,
        val_records=val_records,
    ).model_copy(
        update={
            "validation_selection_score": round(float(best_selection_score), 6),
            "validation_selection_summary": {
                **best_selection_summary,
                "selected_alpha": round(float(best_artifact.alpha), 6),
                "alpha_search": alpha_search,
            },
        }
    )
    best_train_metrics = evaluate_effect_model_v1(calibrated_artifact, train_records)
    best_val_metrics = evaluate_effect_model_v1(calibrated_artifact, val_records)
    return calibrated_artifact, {"train": best_train_metrics, "val": best_val_metrics}


def evaluate_effect_model_v1(
    artifact: EffectModelV1Artifact,
    records: list[RichSyntheticCohortRecord],
) -> EffectEvaluationMetricsV1:
    actual_matrix = np.asarray(
        [
            [record.delta_z_by_domain[output_name] for output_name in artifact.output_names]
            for record in records
        ],
        dtype=float,
    )
    predicted_matrix = np.asarray(
        [
            [
                predict_domain_deltas_v1(artifact, record)[output_name]
                for output_name in artifact.output_names
            ]
            for record in records
        ],
        dtype=float,
    )
    zero_matrix = np.zeros_like(actual_matrix)

    domain_mae = {
        output_name: round(
            _mae(actual_matrix[:, index], predicted_matrix[:, index]),
            6,
        )
        for index, output_name in enumerate(artifact.output_names)
    }
    actual_aggregate = (
        actual_matrix.mean(axis=1) if len(actual_matrix) else np.asarray([], dtype=float)
    )
    predicted_aggregate = np.asarray(
        [predict_aggregate_delta_v1(artifact, record) for record in records],
        dtype=float,
    )
    actual_policy_proxy = np.asarray(
        [record.expected_effect_proxy for record in records],
        dtype=float,
    )
    predicted_policy_proxy = np.asarray(
        [predict_policy_effect_proxy_v1(artifact, record) for record in records],
        dtype=float,
    )
    zero_aggregate = np.zeros_like(actual_aggregate)
    zero_policy_proxy = np.zeros_like(actual_policy_proxy)

    return EffectEvaluationMetricsV1(
        mean_domain_mae=round(
            float(np.mean(np.abs(actual_matrix - predicted_matrix))) if len(actual_matrix) else 0.0,
            6,
        ),
        mean_domain_rmse=round(
            float(sqrt(np.mean((actual_matrix - predicted_matrix) ** 2)))
            if len(actual_matrix)
            else 0.0,
            6,
        ),
        aggregate_mae=round(_mae(actual_aggregate, predicted_aggregate), 6),
        aggregate_rmse=round(_rmse(actual_aggregate, predicted_aggregate), 6),
        aggregate_r2=round(_r2(actual_aggregate, predicted_aggregate), 6),
        policy_proxy_mae=round(_mae(actual_policy_proxy, predicted_policy_proxy), 6),
        policy_proxy_rmse=round(_rmse(actual_policy_proxy, predicted_policy_proxy), 6),
        zero_baseline_mean_domain_mae=round(
            float(np.mean(np.abs(actual_matrix - zero_matrix))) if len(actual_matrix) else 0.0,
            6,
        ),
        zero_baseline_aggregate_mae=round(
            _mae(actual_aggregate, zero_aggregate),
            6,
        ),
        zero_baseline_policy_proxy_mae=round(
            _mae(actual_policy_proxy, zero_policy_proxy),
            6,
        ),
        domain_mae=domain_mae,
    )


def build_effect_feature_schema_v1(
    artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    prefix_counts: dict[str, int] = {}
    for feature_name in artifact.feature_names:
        prefix = feature_name.split("::", 1)[0] if "::" in feature_name else "scalar"
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    training_view_enforcement = summarize_effect_training_view_enforcement_v1(artifact)
    training_feature_family_audit = summarize_effect_training_feature_family_boundary_v1(
        artifact
    )
    return {
        "model_name": artifact.model_name,
        "target_name": artifact.target_name,
        "cohort_version": artifact.cohort_version,
        "feature_count": len(artifact.feature_names),
        "output_names": artifact.output_names,
        "policy_proxy_calibration": {
            "slope": artifact.policy_proxy_slope,
            "intercept": artifact.policy_proxy_intercept,
            "clip_min": artifact.policy_proxy_clip_min,
            "clip_max": artifact.policy_proxy_clip_max,
        },
        "validation_selection": {
            "profile": artifact.validation_selection_profile,
            "score": artifact.validation_selection_score,
            "tolerance": artifact.validation_selection_tolerance,
            "summary": artifact.validation_selection_summary,
        },
        "training_view_enforcement": training_view_enforcement,
        "training_feature_family_audit": training_feature_family_audit,
        "feature_prefix_counts": dict(sorted(prefix_counts.items())),
        "feature_names": artifact.feature_names,
    }


def validate_effect_feature_schema_v1(schema: dict[str, object]) -> list[str]:
    issues: list[str] = []
    training_view_enforcement = schema.get("training_view_enforcement")
    if not isinstance(training_view_enforcement, dict):
        training_view_enforcement = {}
    training_feature_family_audit = schema.get("training_feature_family_audit")
    if not isinstance(training_feature_family_audit, dict):
        training_feature_family_audit = {}
    feature_names = schema.get("feature_names")
    if not isinstance(feature_names, list):
        feature_names = []
    allowed_source_family_counts = training_feature_family_audit.get(
        "allowed_source_family_counts"
    )
    if not isinstance(allowed_source_family_counts, dict):
        allowed_source_family_counts = {}
    forbidden_leakage_family_counts = training_feature_family_audit.get(
        "forbidden_leakage_family_counts"
    )
    if not isinstance(forbidden_leakage_family_counts, dict):
        forbidden_leakage_family_counts = {}
    forbidden_feature_names_present = training_view_enforcement.get(
        "forbidden_feature_names_present"
    )
    if not isinstance(forbidden_feature_names_present, list):
        forbidden_feature_names_present = []
    unknown_features = training_feature_family_audit.get("unknown_features")
    if not isinstance(unknown_features, list):
        unknown_features = []

    if schema.get("feature_count") != len(feature_names):
        issues.append("feature_count_does_not_match_feature_names_length")
    if (
        training_view_enforcement.get("contract_version")
        != "dataset_f_effect_training_view_v1"
    ):
        issues.append("unexpected_training_view_contract_version")
    if training_view_enforcement.get("training_input_allowed_fields") != list(
        EFFECT_TRAINING_ALLOWED_SOURCE_FIELDS_V1
    ):
        issues.append("training_input_allowed_fields_drifted_from_contract")
    if training_feature_family_audit.get("allowed_source_fields") != list(
        EFFECT_TRAINING_ALLOWED_SOURCE_FIELDS_V1
    ):
        issues.append("allowed_source_fields_drifted_from_contract")
    if training_view_enforcement.get("training_input_allowed_fields") != (
        training_feature_family_audit.get("allowed_source_fields")
    ):
        issues.append("training_view_and_feature_family_allowed_fields_mismatch")
    if sorted(allowed_source_family_counts) != sorted(EFFECT_TRAINING_ALLOWED_SOURCE_FIELDS_V1):
        issues.append("allowed_source_family_counts_keys_drifted")
    if (
        training_feature_family_audit.get("classified_feature_count")
        != sum(int(value) for value in allowed_source_family_counts.values())
    ):
        issues.append("classified_feature_count_mismatch")
    if training_feature_family_audit.get("unknown_feature_count") != len(unknown_features):
        issues.append("unknown_feature_count_mismatch")
    if sorted(forbidden_leakage_family_counts) != sorted(
        EFFECT_TRAINING_FORBIDDEN_LEAKAGE_FAMILY_PATTERNS_V1
    ):
        issues.append("forbidden_leakage_family_counts_keys_drifted")
    if training_view_enforcement.get("forbidden_feature_count") != len(
        forbidden_feature_names_present
    ):
        issues.append("forbidden_feature_count_mismatch")
    if training_feature_family_audit.get("forbidden_leakage_feature_count") != sum(
        int(value) for value in forbidden_leakage_family_counts.values()
    ):
        issues.append("forbidden_leakage_feature_count_mismatch")
    if (
        int(training_feature_family_audit.get("classified_feature_count", 0))
        + int(training_feature_family_audit.get("forbidden_leakage_feature_count", 0))
        != len(feature_names)
    ):
        issues.append("feature_family_audit_does_not_cover_feature_names")

    return issues


def render_effect_training_report_v1(
    *,
    artifact: EffectModelV1Artifact,
    split: EffectSplitResultV1,
    train_metrics: EffectEvaluationMetricsV1,
    val_metrics: EffectEvaluationMetricsV1,
    test_metrics: EffectEvaluationMetricsV1,
    test_records: list[RichSyntheticCohortRecord],
) -> dict[str, object]:
    return {
        "model_name": artifact.model_name,
        "cohort_version": artifact.cohort_version,
        "seed": artifact.seed,
        "alpha": artifact.alpha,
        "policy_proxy_calibration": {
            "slope": artifact.policy_proxy_slope,
            "intercept": artifact.policy_proxy_intercept,
            "clip_min": artifact.policy_proxy_clip_min,
            "clip_max": artifact.policy_proxy_clip_max,
        },
        "validation_selection": {
            "profile": artifact.validation_selection_profile,
            "score": artifact.validation_selection_score,
            "tolerance": artifact.validation_selection_tolerance,
            "summary": artifact.validation_selection_summary,
        },
        "training_view_enforcement": summarize_effect_training_view_enforcement_v1(
            artifact
        ),
        "feature_count": len(artifact.feature_names),
        "output_names": artifact.output_names,
        "split_record_counts": {
            "train": len(split.train),
            "val": len(split.val),
            "test": len(split.test),
        },
        "metrics": {
            "train": train_metrics.model_dump(mode="json"),
            "val": val_metrics.model_dump(mode="json"),
            "test": test_metrics.model_dump(mode="json"),
        },
        "top_output_features": {
            output_name: _top_weight_features(artifact, output_name)
            for output_name in artifact.output_names
        },
        "sample_predictions": [
            {
                "record_id": record.record_id,
                "actual_domain_delta": record.delta_z_by_domain,
                "predicted_domain_delta": predict_domain_deltas_v1(artifact, record),
                "actual_aggregate_delta": round(
                    sum(record.delta_z_by_domain.values()) / len(record.delta_z_by_domain),
                    6,
                ),
                "predicted_aggregate_delta": predict_aggregate_delta_v1(artifact, record),
                "actual_policy_effect_proxy": record.expected_effect_proxy,
                "predicted_policy_effect_proxy": predict_policy_effect_proxy_v1(
                    artifact,
                    record,
                ),
            }
            for record in test_records[:5]
        ],
    }


def render_effect_training_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# effect model v1 evaluation",
        "",
        f"- model_name: `{report['model_name']}`",
        f"- cohort_version: `{report['cohort_version']}`",
        f"- seed: `{report['seed']}`",
        f"- alpha: `{report['alpha']}`",
        (
            "- policy_proxy_calibration: "
            f"slope=`{report['policy_proxy_calibration']['slope']}`, "
            f"intercept=`{report['policy_proxy_calibration']['intercept']}`"
        ),
        (
            "- validation_selection: "
            f"profile=`{report['validation_selection']['profile']}`, "
            f"score=`{report['validation_selection']['score']}`, "
            f"tolerance=`{report['validation_selection']['tolerance']}`"
        ),
        (
            "- training_view_enforcement: "
            f"contract_version=`{report['training_view_enforcement']['contract_version']}`, "
            f"forbidden_feature_count=`{report['training_view_enforcement']['forbidden_feature_count']}`"
        ),
        f"- feature_count: `{report['feature_count']}`",
        f"- output_names: `{', '.join(report['output_names'])}`",
        "",
        "## Split Sizes",
    ]
    for key, value in report["split_record_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Metrics"])
    for split_name, metrics in report["metrics"].items():
        lines.append(
            f"- `{split_name}`: "
            f"mean_domain_mae=`{metrics['mean_domain_mae']}`, "
            f"aggregate_mae=`{metrics['aggregate_mae']}`, "
            f"aggregate_rmse=`{metrics['aggregate_rmse']}`, "
            f"aggregate_r2=`{metrics['aggregate_r2']}`, "
            f"policy_proxy_mae=`{metrics['policy_proxy_mae']}`, "
            f"zero_baseline_aggregate_mae=`{metrics['zero_baseline_aggregate_mae']}`"
        )
    return "\n".join(lines) + "\n"


def render_effect_feature_schema_markdown_v1(schema: dict[str, object]) -> str:
    lines = [
        "# effect model v1 feature schema",
        "",
        f"- model_name: `{schema['model_name']}`",
        f"- cohort_version: `{schema['cohort_version']}`",
        f"- target_name: `{schema['target_name']}`",
        f"- feature_count: `{schema['feature_count']}`",
        f"- output_names: `{', '.join(schema['output_names'])}`",
        (
            "- policy_proxy_calibration: "
            f"slope=`{schema['policy_proxy_calibration']['slope']}`, "
            f"intercept=`{schema['policy_proxy_calibration']['intercept']}`"
        ),
        (
            "- validation_selection: "
            f"profile=`{schema['validation_selection']['profile']}`, "
            f"score=`{schema['validation_selection']['score']}`, "
            f"tolerance=`{schema['validation_selection']['tolerance']}`"
        ),
        (
            "- training_view_enforcement: "
            f"contract_version=`{schema['training_view_enforcement']['contract_version']}`, "
            f"forbidden_feature_count=`{schema['training_view_enforcement']['forbidden_feature_count']}`"
        ),
    ]
    lines.extend(["", "## Training View Enforcement"])
    lines.append(
        "- allowed_top_level_fields: "
        f"`{schema['training_view_enforcement']['training_input_allowed_fields']}`"
    )
    lines.append(
        "- forbidden_feature_names_checked: "
        f"`{schema['training_view_enforcement']['forbidden_feature_names_checked']}`"
    )
    lines.append(
        "- forbidden_feature_names_present: "
        f"`{schema['training_view_enforcement']['forbidden_feature_names_present']}`"
    )
    lines.extend(["", "## Training Feature Family Audit"])
    lines.append(
        "- allowed_source_family_counts: "
        f"`{schema['training_feature_family_audit']['allowed_source_family_counts']}`"
    )
    lines.append(
        "- forbidden_leakage_family_counts: "
        f"`{schema['training_feature_family_audit']['forbidden_leakage_family_counts']}`"
    )
    lines.append(
        "- unknown_features: "
        f"`{schema['training_feature_family_audit']['unknown_features']}`"
    )
    lines.extend(["", "## Feature Prefix Counts"])
    for key, value in schema["feature_prefix_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Feature Names"])
    for feature_name in schema["feature_names"]:
        lines.append(f"- `{feature_name}`")
    return "\n".join(lines) + "\n"


def build_effect_dataset_split_manifest_v1(
    split: EffectSplitResultV1,
    *,
    seed: int,
) -> dict[str, object]:
    split_payload: dict[str, object] = {
        "seed": seed,
        "strategy": "sha256(seed:user_id)[0] ratio -> train<0.6, val<0.8, else test",
        "splits": {},
    }
    for split_name, records in (
        ("train", split.train),
        ("val", split.val),
        ("test", split.test),
    ):
        user_ids = sorted({record.user_id for record in records})
        split_payload["splits"][split_name] = {
            "record_count": len(records),
            "user_count": len(user_ids),
            "record_ids": [record.record_id for record in records],
            "user_ids": user_ids,
        }
    return split_payload


def build_effect_dataset_manifest_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    dataset_path: str | Path,
    seed: int,
    split_manifest_path: str | Path,
) -> dict[str, object]:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import (
        CGM_THRESHOLD_EDGE_EFFECT_PROXY_RANGE,
        THRESHOLD_EDGE_EFFECT_PROXY_RANGE,
        validate_rich_synthetic_cohort,
    )

    split = split_effect_records_by_user_v1(records, seed=seed)
    split_manifest = build_effect_dataset_split_manifest_v1(split, seed=seed)
    cohort_version = records[0].cohort_version if records else "unknown"
    goals = sorted({record.request.goals[0].value for record in records if record.request.goals})
    risk_tier_counts: dict[str, int] = {}
    next_action_counts: dict[str, int] = {}
    goal_counts: dict[str, int] = {}
    modality_counts = {"cgm": 0, "wearable": 0, "genetic": 0}
    for record in records:
        risk_tier_counts[record.labels.risk_tier] = (
            risk_tier_counts.get(record.labels.risk_tier, 0) + 1
        )
        next_action = record.labels.next_action.value
        next_action_counts[next_action] = next_action_counts.get(next_action, 0) + 1
        if record.request.goals:
            goal_key = record.request.goals[0].value
            goal_counts[goal_key] = goal_counts.get(goal_key, 0) + 1
        modality_counts["cgm"] += int(record.request.input_availability.cgm)
        modality_counts["wearable"] += int(record.request.input_availability.wearable)
        modality_counts["genetic"] += int(record.request.input_availability.genetic)

    threshold_edge_low_risk_count = sum(
        1
        for record in records
        if (
            record.labels.risk_tier == "low"
            and THRESHOLD_EDGE_EFFECT_PROXY_RANGE[0]
            <= record.expected_effect_proxy
            <= THRESHOLD_EDGE_EFFECT_PROXY_RANGE[1]
        )
    )
    threshold_edge_low_risk_cgm_count = sum(
        1
        for record in records
        if (
            record.labels.risk_tier == "low"
            and record.request.input_availability.cgm
            and CGM_THRESHOLD_EDGE_EFFECT_PROXY_RANGE[0]
            <= record.expected_effect_proxy
            <= CGM_THRESHOLD_EDGE_EFFECT_PROXY_RANGE[1]
        )
    )
    low_risk_reoptimize_count = sum(
        1
        for record in records
        if (
            record.labels.risk_tier == "low"
            and record.labels.next_action.value == "re_optimize"
        )
    )
    low_risk_monitor_only_count = sum(
        1
        for record in records
        if (
            record.labels.risk_tier == "low"
            and record.labels.next_action.value == "monitor_only"
        )
    )

    return {
        "dataset_id": "dataset_f_effect_prepost_v1",
        "dataset_label": "Dataset F effect pre/post synthetic longitudinal cohort",
        "dataset_path": str(Path(dataset_path)),
        "cohort_version": cohort_version,
        "seed": seed,
        "case_count": len(records),
        "user_count": len({record.user_id for record in records}),
        "trajectory_steps_per_user": sorted({record.trajectory_step for record in records}),
        "goal_set": goals,
        "generator_audit": {
            "present": True,
            "source": (
                "wellnessbox_rnd.synthetic.rich_longitudinal_v4."
                "generate_rich_synthetic_cohort_v4"
            ),
            "validator_source": (
                "wellnessbox_rnd.synthetic.rich_longitudinal_v4."
                "validate_rich_synthetic_cohort"
            ),
            "validation_issues": validate_rich_synthetic_cohort(records),
            "dedicated_dataset_manifest_present_before_loop": False,
            "gap_addressed_this_loop": (
                "missing dataset-focused manifest and split artifact for Dataset F"
            ),
        },
        "distribution_summary": {
            "goal_counts": dict(sorted(goal_counts.items())),
            "risk_tier_counts": dict(sorted(risk_tier_counts.items())),
            "next_action_counts": dict(sorted(next_action_counts.items())),
            "modality_record_counts": modality_counts,
            "threshold_edge_counts": {
                "low_risk_effect_proxy_0_14_to_0_28": threshold_edge_low_risk_count,
                "low_risk_cgm_effect_proxy_0_14_to_0_24": threshold_edge_low_risk_cgm_count,
                "low_risk_monitor_only": low_risk_monitor_only_count,
                "low_risk_reoptimize": low_risk_reoptimize_count,
            },
        },
        "training_ready": {
            "training_script": "scripts/train_effect_model_v3.py",
            "dataset_path": str(Path(dataset_path)),
            "split_manifest_path": str(Path(split_manifest_path)),
            "recommended_seed": seed,
            "recommended_artifact_path": "artifacts/models/effect_model_v3.json",
            "recommended_eval_report_path": "artifacts/reports/effect_model_v3_eval.json",
        },
        "split_summary": {
            split_name: {
                "record_count": split_manifest["splits"][split_name]["record_count"],
                "user_count": split_manifest["splits"][split_name]["user_count"],
            }
            for split_name in ("train", "val", "test")
        },
        "sample_record_ids": [record.record_id for record in records[:5]],
    }


def render_effect_dataset_manifest_markdown_v1(manifest: dict[str, object]) -> str:
    lines = [
        "# dataset f effect pre/post manifest",
        "",
        f"- dataset_id: `{manifest['dataset_id']}`",
        f"- dataset_path: `{manifest['dataset_path']}`",
        f"- cohort_version: `{manifest['cohort_version']}`",
        f"- seed: `{manifest['seed']}`",
        f"- case_count: `{manifest['case_count']}`",
        f"- user_count: `{manifest['user_count']}`",
        f"- goal_set: `{', '.join(manifest['goal_set'])}`",
        "",
        "## Audit",
        f"- generator_present: `{manifest['generator_audit']['present']}`",
        f"- generator_source: `{manifest['generator_audit']['source']}`",
        f"- validator_source: `{manifest['generator_audit']['validator_source']}`",
        (
            "- dedicated_dataset_manifest_present_before_loop: "
            f"`{manifest['generator_audit']['dedicated_dataset_manifest_present_before_loop']}`"
        ),
        f"- gap_addressed_this_loop: `{manifest['generator_audit']['gap_addressed_this_loop']}`",
        f"- validation_issues: `{len(manifest['generator_audit']['validation_issues'])}`",
        "",
        "## Split Summary",
    ]
    for split_name, summary in manifest["split_summary"].items():
        lines.append(
            f"- `{split_name}`: record_count=`{summary['record_count']}`, "
            f"user_count=`{summary['user_count']}`"
        )
    lines.extend(["", "## Threshold Edge Counts"])
    for key, value in manifest["distribution_summary"]["threshold_edge_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Next Loop Handoff"])
    lines.append(
        f"- training_script: `{manifest['training_ready']['training_script']}`"
    )
    lines.append(f"- dataset_path: `{manifest['training_ready']['dataset_path']}`")
    lines.append(
        f"- split_manifest_path: `{manifest['training_ready']['split_manifest_path']}`"
    )
    lines.append(
        f"- recommended_seed: `{manifest['training_ready']['recommended_seed']}`"
    )
    return "\n".join(lines) + "\n"


def build_effect_dataset_pair_split_manifest_v1(
    rows: list[EffectDatasetPairRowV1],
    *,
    seed: int,
) -> dict[str, object]:
    grouped: dict[str, list[EffectDatasetPairRowV1]] = {}
    for row in rows:
        grouped.setdefault(row.user_id, []).append(row)

    buckets: dict[str, list[EffectDatasetPairRowV1]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    for user_id in sorted(grouped):
        digest = hashlib.sha256(f"{seed}:{user_id}".encode()).digest()[0]
        ratio = digest / 255.0
        split_name = "train" if ratio < 0.6 else "val" if ratio < 0.8 else "test"
        buckets[split_name].extend(grouped[user_id])

    return {
        "seed": seed,
        "strategy": "sha256(seed:user_id)[0] ratio -> train<0.6, val<0.8, else test",
        "splits": {
            split_name: {
                "pair_count": len(sorted_rows),
                "user_count": len({row.user_id for row in sorted_rows}),
                "pair_ids": [row.pair_id for row in sorted_rows],
                "user_ids": sorted({row.user_id for row in sorted_rows}),
            }
            for split_name, sorted_rows in (
                (name, sorted(values, key=lambda item: item.pair_id))
                for name, values in buckets.items()
            )
        },
    }


def validate_effect_dataset_pair_split_manifest_v1(
    rows: list[EffectDatasetPairRowV1],
    split_manifest: dict[str, object],
    *,
    source_dataset_path: str | Path,
    frozen_eval_dataset_path: str | Path = "data/frozen_eval/frozen_eval_v1.jsonl",
) -> dict[str, object]:
    issues: list[str] = []
    splits = split_manifest["splits"]
    all_pair_ids = {row.pair_id for row in rows}
    all_user_ids = {row.user_id for row in rows}
    split_pair_sets = {
        split_name: set(split_data["pair_ids"])
        for split_name, split_data in splits.items()
    }
    split_user_sets = {
        split_name: set(split_data["user_ids"])
        for split_name, split_data in splits.items()
    }
    combined_split_pair_ids = set().union(*split_pair_sets.values()) if split_pair_sets else set()
    combined_split_user_ids = set().union(*split_user_sets.values()) if split_user_sets else set()
    split_names = tuple(sorted(splits))
    pair_overlap_counts: dict[str, int] = {}
    user_overlap_counts: dict[str, int] = {}

    for index, left_name in enumerate(split_names):
        for right_name in split_names[index + 1 :]:
            pair_overlap_key = f"{left_name}__{right_name}"
            user_overlap_key = f"{left_name}__{right_name}"
            pair_overlap = split_pair_sets[left_name] & split_pair_sets[right_name]
            user_overlap = split_user_sets[left_name] & split_user_sets[right_name]
            pair_overlap_counts[pair_overlap_key] = len(pair_overlap)
            user_overlap_counts[user_overlap_key] = len(user_overlap)
            if pair_overlap:
                issues.append(f"pair overlap detected across splits: {pair_overlap_key}")
            if user_overlap:
                issues.append(f"user overlap detected across splits: {user_overlap_key}")

    missing_pair_ids = sorted(all_pair_ids - combined_split_pair_ids)
    extra_pair_ids = sorted(combined_split_pair_ids - all_pair_ids)
    missing_user_ids = sorted(all_user_ids - combined_split_user_ids)
    extra_user_ids = sorted(combined_split_user_ids - all_user_ids)
    if missing_pair_ids:
        issues.append("split manifest missing pair_ids from dataset rows")
    if extra_pair_ids:
        issues.append("split manifest contains pair_ids not present in dataset rows")
    if missing_user_ids:
        issues.append("split manifest missing user_ids from dataset rows")
    if extra_user_ids:
        issues.append("split manifest contains user_ids not present in dataset rows")

    normalized_source_dataset_path = Path(source_dataset_path).as_posix()
    normalized_frozen_eval_dataset_path = Path(frozen_eval_dataset_path).as_posix()
    shares_path_with_frozen_eval = (
        normalized_source_dataset_path == normalized_frozen_eval_dataset_path
    )
    if shares_path_with_frozen_eval:
        issues.append("dataset f source path must not match frozen eval dataset path")

    return {
        "issues": issues,
        "pair_coverage": {
            "dataset_pair_count": len(all_pair_ids),
            "manifest_pair_count": len(combined_split_pair_ids),
            "missing_pair_id_count": len(missing_pair_ids),
            "extra_pair_id_count": len(extra_pair_ids),
        },
        "user_coverage": {
            "dataset_user_count": len(all_user_ids),
            "manifest_user_count": len(combined_split_user_ids),
            "missing_user_id_count": len(missing_user_ids),
            "extra_user_id_count": len(extra_user_ids),
        },
        "split_disjointness": {
            "pair_overlap_counts": pair_overlap_counts,
            "user_overlap_counts": user_overlap_counts,
        },
        "contamination_safeguards": {
            "source_dataset_path": normalized_source_dataset_path,
            "frozen_eval_dataset_path": normalized_frozen_eval_dataset_path,
            "shares_path_with_frozen_eval": shares_path_with_frozen_eval,
        },
    }


def summarize_effect_dataset_pairs_v1(
    rows: list[EffectDatasetPairRowV1],
    *,
    dataset_path: str | Path,
    source_dataset_path: str | Path,
    split_manifest_path: str | Path,
    seed: int,
) -> dict[str, object]:
    total_rows = len(rows)
    recommended_item_count = sum(len(row.recommended_set) for row in rows)
    split_manifest = build_effect_dataset_pair_split_manifest_v1(rows, seed=seed)
    split_validation = validate_effect_dataset_pair_split_manifest_v1(
        rows,
        split_manifest,
        source_dataset_path=source_dataset_path,
    )
    top_level_keys = list(EFFECT_DATASET_PAIR_TOP_LEVEL_FIELDS)
    training_view_contract = build_effect_dataset_training_view_contract_v1()
    training_view_contract_issues = validate_effect_dataset_training_view_contract_v1(rows)
    top_level_coverage = {
        key: round(
            sum(1 for row in rows if key in row.model_dump(mode="json")) / total_rows * 100.0,
            2,
        )
        if total_rows
        else 0.0
        for key in top_level_keys
    }
    nested_coverage = {
        "baseline": {
            "aggregate_z": round(
                sum(1 for row in rows if row.baseline.aggregate_z is not None)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "domain_z": round(
                sum(1 for row in rows if row.baseline.domain_z) / total_rows * 100.0,
                2,
            )
            if total_rows
            else 0.0,
        },
        "follow_up": {
            "aggregate_z": round(
                sum(1 for row in rows if row.follow_up.aggregate_z is not None)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "domain_z": round(
                sum(1 for row in rows if row.follow_up.domain_z) / total_rows * 100.0,
                2,
            )
            if total_rows
            else 0.0,
        },
        "recommended_set_item": {
            "ingredient_key": round(
                sum(1 for row in rows for item in row.recommended_set if item.ingredient_key)
                / recommended_item_count
                * 100.0,
                2,
            )
            if recommended_item_count
            else 0.0,
            "daily_dose": round(
                sum(1 for row in rows for item in row.recommended_set if item.daily_dose >= 0.0)
                / recommended_item_count
                * 100.0,
                2,
            )
            if recommended_item_count
            else 0.0,
            "dose_unit": round(
                sum(1 for row in rows for item in row.recommended_set if item.dose_unit)
                / recommended_item_count
                * 100.0,
                2,
            )
            if recommended_item_count
            else 0.0,
            "schedule": round(
                sum(1 for row in rows for item in row.recommended_set if item.schedule)
                / recommended_item_count
                * 100.0,
                2,
            )
            if recommended_item_count
            else 0.0,
            "regimen_status": round(
                sum(
                    1 for row in rows for item in row.recommended_set if item.regimen_status
                )
                / recommended_item_count
                * 100.0,
                2,
            )
            if recommended_item_count
            else 0.0,
        },
        "period": {
            "trajectory_step": round(
                sum(1 for row in rows if row.period.trajectory_step >= 0) / total_rows * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "start_day_index": round(
                sum(1 for row in rows if row.period.start_day_index >= 0) / total_rows * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "end_day_index": round(
                sum(1 for row in rows if row.period.end_day_index >= 0) / total_rows * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "days_from_baseline": round(
                sum(1 for row in rows if row.period.days_from_baseline >= 0)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
        },
        "input_flags": {
            "survey": round(
                sum(1 for row in rows if isinstance(row.input_flags.survey, bool))
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "nhis": round(
                sum(1 for row in rows if isinstance(row.input_flags.nhis, bool))
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "wearable": round(
                sum(1 for row in rows if isinstance(row.input_flags.wearable, bool))
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "cgm": round(
                sum(1 for row in rows if isinstance(row.input_flags.cgm, bool))
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "genetic": round(
                sum(1 for row in rows if isinstance(row.input_flags.genetic, bool))
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
        },
        "response_profile": {
            "trajectory_mode": round(
                sum(1 for row in rows if row.response_profile.trajectory_mode)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "response_family": round(
                sum(1 for row in rows if row.response_profile.response_family)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "response_strength_band": round(
                sum(1 for row in rows if row.response_profile.response_strength_band)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "adherence_band": round(
                sum(1 for row in rows if row.response_profile.adherence_band)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "tolerability_band": round(
                sum(1 for row in rows if row.response_profile.tolerability_band)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "modality_signature": round(
                sum(1 for row in rows if row.response_profile.modality_signature)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
        },
        "provenance": {
            "source_request_id": round(
                sum(1 for row in rows if row.provenance.source_request_id)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "rng_seed": round(
                sum(1 for row in rows if row.provenance.rng_seed >= 0) / total_rows * 100.0,
                2,
            )
            if total_rows
            else 0.0,
            "trajectory_mode": round(
                sum(1 for row in rows if row.provenance.trajectory_mode)
                / total_rows
                * 100.0,
                2,
            )
            if total_rows
            else 0.0,
        },
    }
    return {
        "dataset_id": "dataset_f_effect_prepost_pairs_v1",
        "dataset_path": str(Path(dataset_path)),
        "source_dataset_path": str(Path(source_dataset_path)),
        "case_count": total_rows,
        "user_count": len({row.user_id for row in rows}),
        "recommended_item_count": recommended_item_count,
        "goal_counts": _count_string_values(row.goal for row in rows),
        "next_action_counts": _count_string_values(row.next_action for row in rows),
        "risk_tier_counts": _count_string_values(row.risk_tier for row in rows),
        "adverse_event_count": sum(1 for row in rows if row.adverse_event),
        "input_flag_counts": {
            "survey": sum(1 for row in rows if row.input_flags.survey),
            "nhis": sum(1 for row in rows if row.input_flags.nhis),
            "wearable": sum(1 for row in rows if row.input_flags.wearable),
            "cgm": sum(1 for row in rows if row.input_flags.cgm),
            "genetic": sum(1 for row in rows if row.input_flags.genetic),
        },
        "period_summary": {
            "trajectory_step_counts": _count_string_values(
                str(row.period.trajectory_step) for row in rows
            ),
            "max_days_from_baseline": max(
                (row.period.days_from_baseline for row in rows),
                default=0,
            ),
        },
        "response_profile_summary": {
            "trajectory_mode_counts": _count_string_values(
                row.response_profile.trajectory_mode for row in rows
            ),
            "response_family_counts": _count_string_values(
                row.response_profile.response_family for row in rows
            ),
            "response_strength_band_counts": _count_string_values(
                row.response_profile.response_strength_band for row in rows
            ),
            "adherence_band_counts": _count_string_values(
                row.response_profile.adherence_band for row in rows
            ),
            "tolerability_band_counts": _count_string_values(
                row.response_profile.tolerability_band for row in rows
            ),
            "modality_signature_counts": _count_string_values(
                row.response_profile.modality_signature for row in rows
            ),
        },
        "schema_key_coverage_pct": {
            "top_level": top_level_coverage,
            "nested": nested_coverage,
        },
        "split_manifest_path": str(Path(split_manifest_path)),
        "dataset_provenance": {
            "source_dataset_path": str(Path(source_dataset_path)),
            "source_cohort_version": rows[0].cohort_version if rows else "unknown",
            "generator_source": (
                "wellnessbox_rnd.synthetic.rich_longitudinal_v4."
                "generate_rich_synthetic_cohort_v4"
            ),
            "validator_source": (
                "wellnessbox_rnd.synthetic.rich_longitudinal_v4."
                "validate_rich_synthetic_cohort"
            ),
            "split_seed": seed,
            "split_manifest_path": str(Path(split_manifest_path)),
            "frozen_eval_dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
            "shares_path_with_frozen_eval": str(Path(source_dataset_path))
            == "data\\frozen_eval\\frozen_eval_v1.jsonl",
        },
        "training_view_contract": {
            **training_view_contract,
            "issues": training_view_contract_issues,
        },
        "split_summary": {
            split_name: {
                "pair_count": split_manifest["splits"][split_name]["pair_count"],
                "user_count": split_manifest["splits"][split_name]["user_count"],
            }
            for split_name in ("train", "val", "test")
        },
        "split_validation": split_validation,
        "recommended_training_source": {
            "dataset_path": "data/synthetic/synthetic_longitudinal_v4.jsonl",
            "split_manifest_path": (
                "artifacts/reports/dataset_f_effect_prepost_split_manifest_v1.json"
            ),
            "seed": seed,
            "training_script": "scripts/train_effect_model_v3.py",
        },
        "sample_pair_ids": [row.pair_id for row in rows[:5]],
    }


def render_effect_dataset_pairs_markdown_v1(summary: dict[str, object]) -> str:
    lines = [
        "# dataset f effect pre/post pairs",
        "",
        f"- dataset_id: `{summary['dataset_id']}`",
        f"- dataset_path: `{summary['dataset_path']}`",
        f"- source_dataset_path: `{summary['source_dataset_path']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- user_count: `{summary['user_count']}`",
        f"- adverse_event_count: `{summary['adverse_event_count']}`",
        f"- recommended_item_count: `{summary['recommended_item_count']}`",
        "",
        "## Split Summary",
    ]
    for split_name, values in summary["split_summary"].items():
        lines.append(
            f"- `{split_name}`: pair_count=`{values['pair_count']}`, "
            f"user_count=`{values['user_count']}`"
        )
    lines.extend(["", "## Input Flag Counts"])
    for key, value in summary["input_flag_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Response Profile Summary"])
    for key, value in summary["response_profile_summary"]["response_family_counts"].items():
        lines.append(f"- `response_family::{key}`: `{value}`")
    for key, value in summary["response_profile_summary"]["response_strength_band_counts"].items():
        lines.append(f"- `response_strength_band::{key}`: `{value}`")
    for key, value in summary["response_profile_summary"]["adherence_band_counts"].items():
        lines.append(f"- `adherence_band::{key}`: `{value}`")
    for key, value in summary["response_profile_summary"]["tolerability_band_counts"].items():
        lines.append(f"- `tolerability_band::{key}`: `{value}`")
    for key, value in summary["response_profile_summary"]["modality_signature_counts"].items():
        lines.append(f"- `modality_signature::{key}`: `{value}`")
    lines.extend(["", "## Provenance"])
    lines.append(
        f"- generator_source: `{summary['dataset_provenance']['generator_source']}`"
    )
    lines.append(
        f"- validator_source: `{summary['dataset_provenance']['validator_source']}`"
    )
    lines.append(
        f"- split_seed: `{summary['dataset_provenance']['split_seed']}`"
    )
    lines.append(
        "- shares_path_with_frozen_eval: "
        f"`{summary['dataset_provenance']['shares_path_with_frozen_eval']}`"
    )
    lines.extend(["", "## Split Validation"])
    lines.append(
        f"- issues: `{summary['split_validation']['issues']}`"
    )
    lines.append(
        "- pair_coverage: "
        f"`{summary['split_validation']['pair_coverage']}`"
    )
    lines.append(
        "- user_coverage: "
        f"`{summary['split_validation']['user_coverage']}`"
    )
    lines.append(
        "- split_disjointness: "
        f"`{summary['split_validation']['split_disjointness']}`"
    )
    lines.append(
        "- contamination_safeguards: "
        f"`{summary['split_validation']['contamination_safeguards']}`"
    )
    lines.extend(["", "## Training View Contract"])
    lines.append(
        "- contract_version: "
        f"`{summary['training_view_contract']['contract_version']}`"
    )
    lines.append(
        "- baseline_fact_fields: "
        f"`{summary['training_view_contract']['baseline_fact_fields']}`"
    )
    lines.append(
        "- intervention_assignment_fields: "
        f"`{summary['training_view_contract']['intervention_assignment_fields']}`"
    )
    lines.append(
        "- follow_up_outcome_fields: "
        f"`{summary['training_view_contract']['follow_up_outcome_fields']}`"
    )
    lines.append(
        "- training_input_allowed_fields: "
        f"`{summary['training_view_contract']['training_input_allowed_fields']}`"
    )
    lines.append(
        "- training_input_forbidden_fields: "
        f"`{summary['training_view_contract']['training_input_forbidden_fields']}`"
    )
    lines.append(
        f"- issues: `{summary['training_view_contract']['issues']}`"
    )
    lines.extend(["", "## Schema Key Coverage"])
    for key, value in summary["schema_key_coverage_pct"]["top_level"].items():
        lines.append(f"- `top_level::{key}`: `{value}`")
    for section_name, section_values in summary["schema_key_coverage_pct"]["nested"].items():
        for key, value in section_values.items():
            lines.append(f"- `{section_name}::{key}`: `{value}`")
    lines.extend(["", "## Training Handoff"])
    lines.append(
        f"- training_script: `{summary['recommended_training_source']['training_script']}`"
    )
    lines.append(
        f"- source_dataset_path: `{summary['recommended_training_source']['dataset_path']}`"
    )
    lines.append(
        "- source_split_manifest_path: "
        f"`{summary['recommended_training_source']['split_manifest_path']}`"
    )
    lines.append(f"- seed: `{summary['recommended_training_source']['seed']}`")
    return "\n".join(lines) + "\n"


def write_effect_dataset_pairs_jsonl_v1(
    path: str | Path,
    rows: list[EffectDatasetPairRowV1],
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=lambda item: item.pair_id)
    target.write_text(
        "\n".join(row.model_dump_json() for row in sorted_rows) + "\n",
        encoding="utf-8",
    )


def write_effect_training_outputs_v1(
    *,
    artifact: EffectModelV1Artifact,
    report: dict[str, object],
    feature_schema: dict[str, object],
    artifact_path: str | Path,
    report_json_path: str | Path,
    report_md_path: str | Path,
    split_json_path: str | Path,
    feature_schema_json_path: str | Path,
    feature_schema_md_path: str | Path,
    split: EffectSplitResultV1,
) -> None:
    artifact_target = Path(artifact_path)
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    split_json_target = Path(split_json_path)
    feature_schema_json_target = Path(feature_schema_json_path)
    feature_schema_md_target = Path(feature_schema_md_path)
    for path in (
        artifact_target,
        report_json_target,
        report_md_target,
        split_json_target,
        feature_schema_json_target,
        feature_schema_md_target,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    artifact_target.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(
        render_effect_training_markdown_v1(report),
        encoding="utf-8",
    )
    split_json_target.write_text(
        json.dumps(
            {
                "train_record_ids": [record.record_id for record in split.train],
                "val_record_ids": [record.record_id for record in split.val],
                "test_record_ids": [record.record_id for record in split.test],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    feature_schema_json_target.write_text(
        json.dumps(feature_schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    feature_schema_md_target.write_text(
        render_effect_feature_schema_markdown_v1(feature_schema),
        encoding="utf-8",
    )


def _build_target_matrix(
    records: list[RichSyntheticCohortRecord],
    output_names: list[str],
) -> np.ndarray:
    return np.asarray(
        [
            [record.delta_z_by_domain[output_name] for output_name in output_names]
            for record in records
        ],
        dtype=float,
    )


def build_effect_validation_selection_summary_v1(
    artifact: EffectModelV1Artifact,
    *,
    val_records: list[RichSyntheticCohortRecord],
    val_metrics: EffectEvaluationMetricsV1,
    profile: str = DEFAULT_EFFECT_VALIDATION_SELECTION_PROFILE_V1,
) -> dict[str, object]:
    slice_summary = _build_effect_validation_slice_summary_v1(
        artifact,
        records=val_records,
    )
    selection_score = _effect_validation_selection_score_v1(
        val_metrics=val_metrics,
        slice_summary=slice_summary,
        profile=profile,
    )
    return {
        "selection_stage": "pre_policy_proxy_calibration",
        "profile": profile,
        "selection_score": round(float(selection_score), 6),
        "aggregate_mae": val_metrics.aggregate_mae,
        "aggregate_r2": val_metrics.aggregate_r2,
        "pre_policy_proxy_mae": val_metrics.policy_proxy_mae,
        "slice_summary": slice_summary,
    }


def _fit_multitarget_ridge(
    x: np.ndarray,
    y: np.ndarray,
    *,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray]:
    x_bias = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    regularizer = np.eye(x_bias.shape[1]) * alpha
    regularizer[0, 0] = 0.0
    solution = np.linalg.pinv(x_bias.T @ x_bias + regularizer) @ x_bias.T @ y
    intercepts = solution[0]
    weights = solution[1:].T
    return weights, intercepts


def _build_effect_validation_slice_summary_v1(
    artifact: EffectModelV1Artifact,
    *,
    records: list[RichSyntheticCohortRecord],
) -> dict[str, object]:
    cgm_records = [record for record in records if record.request.input_availability.cgm]
    non_cgm_records = [record for record in records if not record.request.input_availability.cgm]
    low_risk_records = [record for record in records if record.labels.risk_tier == "low"]
    low_risk_cgm_records = [
        record
        for record in low_risk_records
        if record.request.input_availability.cgm
    ]
    goal_values = sorted(
        {record.request.goals[0].value for record in records if record.request.goals}
    )
    goal_slice_aggregate_mae = {
        goal: _evaluate_effect_slice_aggregate_mae_v1(
            artifact,
            [
                record
                for record in records
                if record.request.goals and record.request.goals[0].value == goal
            ],
        )
        for goal in goal_values
    }
    goal_slice_values = list(goal_slice_aggregate_mae.values())
    low_risk_response_family_aggregate_mae = _build_response_family_aggregate_mae_v1(
        artifact,
        records=low_risk_records,
    )
    low_risk_response_family_values = list(low_risk_response_family_aggregate_mae.values())
    low_risk_cgm_response_family_aggregate_mae = _build_response_family_aggregate_mae_v1(
        artifact,
        records=low_risk_cgm_records,
    )
    low_risk_cgm_response_family_values = list(
        low_risk_cgm_response_family_aggregate_mae.values()
    )
    return {
        "case_count": len(records),
        "cgm_case_count": len(cgm_records),
        "non_cgm_case_count": len(non_cgm_records),
        "low_risk_case_count": len(low_risk_records),
        "low_risk_cgm_case_count": len(low_risk_cgm_records),
        "cgm_aggregate_mae": _evaluate_effect_slice_aggregate_mae_v1(
            artifact,
            cgm_records,
        ),
        "non_cgm_aggregate_mae": _evaluate_effect_slice_aggregate_mae_v1(
            artifact,
            non_cgm_records,
        ),
        "goal_slice_aggregate_mae": goal_slice_aggregate_mae,
        "mean_goal_slice_aggregate_mae": round(
            float(np.mean(goal_slice_values)) if goal_slice_values else 0.0,
            6,
        ),
        "worst_goal_slice_aggregate_mae": round(
            float(max(goal_slice_values)) if goal_slice_values else 0.0,
            6,
        ),
        "low_risk_response_family_aggregate_mae": low_risk_response_family_aggregate_mae,
        "mean_low_risk_response_family_aggregate_mae": round(
            float(np.mean(low_risk_response_family_values))
            if low_risk_response_family_values
            else 0.0,
            6,
        ),
        "worst_low_risk_response_family_aggregate_mae": round(
            float(max(low_risk_response_family_values))
            if low_risk_response_family_values
            else 0.0,
            6,
        ),
        "low_risk_cgm_response_family_aggregate_mae": (
            low_risk_cgm_response_family_aggregate_mae
        ),
        "mean_low_risk_cgm_response_family_aggregate_mae": round(
            float(np.mean(low_risk_cgm_response_family_values))
            if low_risk_cgm_response_family_values
            else 0.0,
            6,
        ),
        "worst_low_risk_cgm_response_family_aggregate_mae": round(
            float(max(low_risk_cgm_response_family_values))
            if low_risk_cgm_response_family_values
            else 0.0,
            6,
        ),
    }


def _evaluate_effect_slice_aggregate_mae_v1(
    artifact: EffectModelV1Artifact,
    records: list[RichSyntheticCohortRecord],
) -> float:
    if not records:
        return 0.0
    return evaluate_effect_model_v1(artifact, records).aggregate_mae


def _effect_validation_selection_score_v1(
    *,
    val_metrics: EffectEvaluationMetricsV1,
    slice_summary: dict[str, object],
    profile: str,
) -> float:
    if profile == "aggregate_mae_v1":
        return float(val_metrics.aggregate_mae)
    if profile == "allowed_slice_balance_v1":
        mean_goal_slice_aggregate_mae = float(slice_summary["mean_goal_slice_aggregate_mae"])
        cgm_gap = abs(
            float(slice_summary["cgm_aggregate_mae"])
            - float(slice_summary["non_cgm_aggregate_mae"])
        )
        return round(
            float(val_metrics.aggregate_mae)
            + (0.25 * mean_goal_slice_aggregate_mae)
            + (0.1 * cgm_gap),
            6,
        )
    if profile != "allowed_slice_heterogeneity_v1":
        raise ValueError(f"Unsupported effect validation selection profile: {profile}")

    mean_goal_slice_aggregate_mae = float(slice_summary["mean_goal_slice_aggregate_mae"])
    cgm_gap = abs(
        float(slice_summary["cgm_aggregate_mae"])
        - float(slice_summary["non_cgm_aggregate_mae"])
    )
    mean_low_risk_response_family_aggregate_mae = float(
        slice_summary["mean_low_risk_response_family_aggregate_mae"]
    )
    worst_low_risk_response_family_aggregate_mae = float(
        slice_summary["worst_low_risk_response_family_aggregate_mae"]
    )
    mean_low_risk_cgm_response_family_aggregate_mae = float(
        slice_summary["mean_low_risk_cgm_response_family_aggregate_mae"]
    )
    worst_low_risk_cgm_response_family_aggregate_mae = float(
        slice_summary["worst_low_risk_cgm_response_family_aggregate_mae"]
    )
    return round(
        float(val_metrics.aggregate_mae)
        + (0.2 * mean_goal_slice_aggregate_mae)
        + (0.05 * cgm_gap)
        + (0.2 * mean_low_risk_response_family_aggregate_mae)
        + (0.2 * worst_low_risk_response_family_aggregate_mae)
        + (0.15 * mean_low_risk_cgm_response_family_aggregate_mae)
        + (0.15 * worst_low_risk_cgm_response_family_aggregate_mae),
        6,
    )


def _build_response_family_aggregate_mae_v1(
    artifact: EffectModelV1Artifact,
    *,
    records: list[RichSyntheticCohortRecord],
) -> dict[str, float]:
    response_families = sorted(
        {
            build_effect_dataset_response_profile_v1(record).response_family
            for record in records
        }
    )
    return {
        response_family: _evaluate_effect_slice_aggregate_mae_v1(
            artifact,
            [
                record
                for record in records
                if build_effect_dataset_response_profile_v1(record).response_family
                == response_family
            ],
        )
        for response_family in response_families
    }


def _is_better_effect_validation_candidate_v1(
    *,
    candidate_score: float,
    candidate_alpha: float,
    best_score: float | None,
    best_alpha: float | None,
    tolerance: float,
) -> bool:
    if best_score is None or best_alpha is None:
        return True
    if candidate_score < (best_score - tolerance):
        return True
    return abs(candidate_score - best_score) <= tolerance and candidate_alpha > best_alpha


def _fit_policy_proxy_calibration(
    artifact: EffectModelV1Artifact,
    *,
    train_records: list[RichSyntheticCohortRecord],
    val_records: list[RichSyntheticCohortRecord],
) -> EffectModelV1Artifact:
    calibration_records = train_records + val_records
    if not calibration_records:
        return artifact

    predicted = np.asarray(
        [predict_aggregate_delta_v1(artifact, record) for record in calibration_records],
        dtype=float,
    )
    actual = np.asarray(
        [record.expected_effect_proxy for record in calibration_records],
        dtype=float,
    )
    if len(predicted) == 0:
        return artifact
    design = np.column_stack([predicted, np.ones(len(predicted))])
    slope, intercept = np.linalg.lstsq(design, actual, rcond=None)[0]
    slope = float(max(0.0, slope))
    intercept = float(intercept)
    return artifact.model_copy(
        update={
            "policy_proxy_slope": round(slope, 8),
            "policy_proxy_intercept": round(intercept, 8),
        }
    )


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    return float(np.mean(np.abs(actual - predicted)))


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    return float(sqrt(np.mean((actual - predicted) ** 2)))


def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    baseline = np.mean(actual)
    denom = np.sum((actual - baseline) ** 2)
    if denom == 0:
        return 0.0
    numer = np.sum((actual - predicted) ** 2)
    return float(1.0 - (numer / denom))


def _top_weight_features(
    artifact: EffectModelV1Artifact,
    output_name: str,
    *,
    limit: int = 8,
) -> list[dict[str, float | str]]:
    output_index = artifact.output_names.index(output_name)
    pairs = list(zip(artifact.feature_names, artifact.weights[output_index], strict=True))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    return [
        {"feature": name, "weight": round(weight, 6)}
        for name, weight in pairs[:limit]
    ]


def _count_string_values(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_effect_training_feature_dict_v1(
    pair_row: EffectDatasetPairRowV1,
) -> dict[str, float]:
    features: dict[str, float] = {
        "trajectory_step": float(pair_row.period.trajectory_step),
        "day_index": float(pair_row.period.end_day_index),
        "goal_count": 1.0,
        "wearable_available": float(pair_row.input_flags.wearable),
        "cgm_available": float(pair_row.input_flags.cgm),
        "genetic_available": float(pair_row.input_flags.genetic),
        "nhis_available": float(pair_row.input_flags.nhis),
        "baseline_aggregate_z": float(pair_row.baseline.aggregate_z),
        "regimen_count": float(len(pair_row.recommended_set)),
        "active_regimen_count": float(
            sum(1 for item in pair_row.recommended_set if item.regimen_status == "active")
        ),
        "planned_regimen_count": float(
            sum(1 for item in pair_row.recommended_set if item.regimen_status == "planned")
        ),
        "reduced_regimen_count": float(
            sum(1 for item in pair_row.recommended_set if item.regimen_status == "reduced")
        ),
        "stopped_regimen_count": float(
            sum(1 for item in pair_row.recommended_set if item.regimen_status == "stopped")
        ),
        "total_daily_dose": float(
            round(sum(item.daily_dose for item in pair_row.recommended_set), 3)
        ),
    }

    for goal in RecommendationGoal:
        features[f"goal::{goal.value}"] = float(pair_row.goal == goal.value)
        features[f"baseline::{goal.value}"] = float(
            pair_row.baseline.domain_z.get(goal.value, 0.0)
        )

    for regimen_item in pair_row.recommended_set:
        features[f"regimen::{regimen_item.ingredient_key}"] = 1.0
        features[f"dose::{regimen_item.ingredient_key}"] = float(regimen_item.daily_dose)
        features[f"schedule::{regimen_item.schedule}"] = 1.0
        features[f"regimen_status::{regimen_item.regimen_status}"] = 1.0

    return features


def summarize_effect_training_view_enforcement_v1(
    artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    contract = build_effect_dataset_training_view_contract_v1()
    forbidden_present = [
        feature_name
        for feature_name in EFFECT_TRAINING_VIEW_FORBIDDEN_FEATURE_NAMES
        if feature_name in artifact.feature_names
    ]
    return {
        "contract_version": contract["contract_version"],
        "training_input_allowed_fields": contract["training_input_allowed_fields"],
        "forbidden_feature_names_checked": list(
            EFFECT_TRAINING_VIEW_FORBIDDEN_FEATURE_NAMES
        ),
        "forbidden_feature_names_present": forbidden_present,
        "forbidden_feature_count": len(forbidden_present),
    }


def summarize_effect_training_feature_family_boundary_v1(
    artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    allowed_source_family_counts = {
        field_name: 0 for field_name in EFFECT_TRAINING_ALLOWED_SOURCE_FIELDS_V1
    }
    feature_to_source_family: dict[str, str] = {}
    unknown_features: list[str] = []
    for feature_name in artifact.feature_names:
        source_family = _classify_effect_training_feature_source_family_v1(feature_name)
        if source_family is None:
            if _match_effect_training_forbidden_family_v1(feature_name) is None:
                unknown_features.append(feature_name)
            continue
        allowed_source_family_counts[source_family] += 1
        feature_to_source_family[feature_name] = source_family

    forbidden_leakage_family_counts = {
        family_name: 0
        for family_name in EFFECT_TRAINING_FORBIDDEN_LEAKAGE_FAMILY_PATTERNS_V1
    }
    forbidden_leakage_features_present: dict[str, list[str]] = {
        family_name: []
        for family_name in EFFECT_TRAINING_FORBIDDEN_LEAKAGE_FAMILY_PATTERNS_V1
    }
    for feature_name in artifact.feature_names:
        family_name = _match_effect_training_forbidden_family_v1(feature_name)
        if family_name is None:
            continue
        forbidden_leakage_family_counts[family_name] += 1
        forbidden_leakage_features_present[family_name].append(feature_name)

    forbidden_leakage_features_present = {
        family_name: feature_names
        for family_name, feature_names in forbidden_leakage_features_present.items()
        if feature_names
    }

    return {
        "allowed_source_fields": list(EFFECT_TRAINING_ALLOWED_SOURCE_FIELDS_V1),
        "allowed_source_family_counts": allowed_source_family_counts,
        "classified_feature_count": sum(allowed_source_family_counts.values()),
        "feature_to_source_family": feature_to_source_family,
        "unknown_features": unknown_features,
        "unknown_feature_count": len(unknown_features),
        "forbidden_leakage_family_patterns_checked": {
            family_name: list(patterns)
            for family_name, patterns in (
                EFFECT_TRAINING_FORBIDDEN_LEAKAGE_FAMILY_PATTERNS_V1.items()
            )
        },
        "forbidden_leakage_family_counts": forbidden_leakage_family_counts,
        "forbidden_leakage_features_present": forbidden_leakage_features_present,
        "forbidden_leakage_feature_count": sum(
            forbidden_leakage_family_counts.values()
        ),
    }


def validate_effect_training_feature_family_boundary_v1(
    artifact: EffectModelV1Artifact,
) -> list[str]:
    audit = summarize_effect_training_feature_family_boundary_v1(artifact)
    issues: list[str] = []
    classified_or_forbidden_count = (
        audit["classified_feature_count"] + audit["forbidden_leakage_feature_count"]
    )
    if classified_or_forbidden_count != len(artifact.feature_names):
        issues.append("unclassified training feature names detected")
    if audit["unknown_feature_count"] != 0:
        issues.append(
            "unknown training feature names present: "
            + ", ".join(audit["unknown_features"])
        )
    for family_name, count in audit["allowed_source_family_counts"].items():
        if count == 0:
            issues.append(f"allowed source family missing from artifact: {family_name}")
    if audit["forbidden_leakage_feature_count"] != 0:
        issues.append(
            "forbidden leakage-prone feature families present: "
            + ", ".join(
                f"{family_name}={len(feature_names)}"
                for family_name, feature_names in sorted(
                    audit["forbidden_leakage_features_present"].items()
                )
            )
        )
    return issues


def _classify_effect_training_feature_source_family_v1(
    feature_name: str,
) -> str | None:
    if feature_name.startswith("goal::") or feature_name == "goal_count":
        return "goal"
    if feature_name.startswith("baseline::") or feature_name == "baseline_aggregate_z":
        return "baseline"
    if feature_name in {
        "wearable_available",
        "cgm_available",
        "genetic_available",
        "nhis_available",
    }:
        return "input_flags"
    if feature_name in {"trajectory_step", "day_index"}:
        return "period"
    if feature_name.startswith(
        ("regimen::", "dose::", "schedule::", "regimen_status::")
    ) or feature_name in {
        "regimen_count",
        "active_regimen_count",
        "planned_regimen_count",
        "reduced_regimen_count",
        "stopped_regimen_count",
        "total_daily_dose",
    }:
        return "recommended_set"
    return None


def _match_effect_training_forbidden_family_v1(feature_name: str) -> str | None:
    for family_name, patterns in EFFECT_TRAINING_FORBIDDEN_LEAKAGE_FAMILY_PATTERNS_V1.items():
        if any(feature_name.startswith(pattern) for pattern in patterns):
            return family_name
    return None
