from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.data_lake import (
    all_used_sources_allow_storage,
    derive_profile_id,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

DEVICE_ASSESSMENT_SCHEMA_VERSION = "device_recommendation_assessment_v1"
DevicePhase = Literal["BASELINE", "FOLLOW_UP"]
DeviceOrigin = Literal["DEVICE_PROVIDER", "SIMULATION_FIXTURE"]
DeviceSessionDataClass = Literal[
    "PRODUCTION_DEVICE_SESSION",
    "SIMULATED_DEVICE_SESSION",
]


class DeviceRecommendationAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(pattern=r"^device_assessment_[A-Za-z0-9_-]{8,96}$")
    phase: DevicePhase
    baseline_assessment_id: str | None = Field(
        default=None,
        pattern=r"^device_assessment_[A-Za-z0-9_-]{8,96}$",
    )
    data_class: DeviceSessionDataClass
    session_origin: DeviceOrigin
    recommendation_request: RecommendationRequest

    @model_validator(mode="after")
    def validate_boundary(self) -> DeviceRecommendationAssessmentRequest:
        expected = {
            "DEVICE_PROVIDER": DataClass.PRODUCTION_DEVICE_SESSION,
            "SIMULATION_FIXTURE": DataClass.SIMULATED_DEVICE_SESSION,
        }[self.session_origin]
        if self.data_class != expected:
            raise ValueError("device_session_origin_data_class_mismatch")
        if self.phase == "BASELINE" and self.baseline_assessment_id is not None:
            raise ValueError("baseline_device_assessment_cannot_reference_baseline")
        if self.phase == "FOLLOW_UP" and self.baseline_assessment_id is None:
            raise ValueError("follow_up_device_assessment_requires_baseline")
        snapshot = self.recommendation_request.sensor_genetic_snapshot
        source_profile = self.recommendation_request.source_profile
        if source_profile is None or source_profile.subject_id is None:
            raise ValueError("device_assessment_requires_explicit_subject_id")
        if not all_used_sources_allow_storage(self.recommendation_request):
            raise ValueError("device_assessment_used_source_storage_consent_required")
        if snapshot is None or not (snapshot.wearable_available or snapshot.cgm_available):
            raise ValueError("device_assessment_requires_wearable_or_cgm_values")
        for source in ("wearable", "cgm"):
            if getattr(snapshot, f"{source}_available"):
                consent = getattr(self.recommendation_request.data_source_consents, source)
                if not consent.use_for_recommendation:
                    raise ValueError(f"{source}_recommendation_consent_required")
                if not consent.allow_persistent_storage:
                    raise ValueError(f"{source}_persistent_storage_consent_required")
        return self


class DeviceRecommendationAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["device_recommendation_assessment_v1"]
    assessment_id: str
    phase: DevicePhase
    baseline_assessment_id: str | None
    data_class: DeviceSessionDataClass
    session_origin: DeviceOrigin
    recommendation_status: str
    sensor_snapshot: dict[str, Any]
    score_snapshot: dict[str, dict[str, float]]
    sensor_changes: dict[str, dict[str, float | None]]
    score_changes: dict[str, dict[str, float | bool | None]]
    persisted: bool
    deduplicated: bool


def assess_device_recommendation(
    payload: DeviceRecommendationAssessmentRequest,
    *,
    store: InterimStore,
) -> DeviceRecommendationAssessmentResponse:
    request = payload.recommendation_request
    sensor_snapshot = _numeric_sensor_snapshot(request)
    response = recommend(request)
    score_snapshot = {
        item.ingredient_key: {
            "wearable_adjustment": item.score_breakdown.wearable_adjustment,
            "cgm_adjustment": item.score_breakdown.cgm_adjustment,
            "total": item.score_breakdown.total,
        }
        for item in response.recommendations
    }
    sensor_changes: dict[str, dict[str, float | None]] = {}
    score_changes: dict[str, dict[str, float | bool | None]] = {}
    baseline = None
    if payload.baseline_assessment_id is not None:
        baseline = _load_assessment(store, payload.baseline_assessment_id)
        if baseline["phase"] != "BASELINE":
            raise ValueError("device_follow_up_reference_must_be_baseline")
        if baseline["profile_id"] != derive_profile_id(request):
            raise ValueError("device_follow_up_profile_mismatch")
        if baseline["data_class"] != payload.data_class:
            raise ValueError("device_follow_up_data_class_mismatch")
        if baseline["session_origin"] != payload.session_origin:
            raise ValueError("device_follow_up_origin_mismatch")
        baseline_sensor = json.loads(baseline["sensor_snapshot_json"])
        baseline_scores = json.loads(baseline["score_snapshot_json"])
        sensor_changes = _numeric_changes(baseline_sensor, sensor_snapshot)
        score_changes = calculate_device_score_changes(baseline_scores, score_snapshot)

    request_sha256 = _sha256(request.model_dump(mode="json"))
    values = {
        "assessment_id": payload.assessment_id,
        "profile_id": derive_profile_id(request),
        "phase": payload.phase,
        "baseline_assessment_id": payload.baseline_assessment_id,
        "data_class": payload.data_class,
        "session_origin": payload.session_origin,
        "request_sha256": request_sha256,
        "sensor_snapshot_json": _canonical(sensor_snapshot),
        "score_snapshot_json": _canonical(score_snapshot),
        "sensor_changes_json": _canonical(sensor_changes),
        "score_changes_json": _canonical(score_changes),
    }
    deduplicated = _persist(store, values)
    return DeviceRecommendationAssessmentResponse(
        schema_version=DEVICE_ASSESSMENT_SCHEMA_VERSION,
        assessment_id=payload.assessment_id,
        phase=payload.phase,
        baseline_assessment_id=payload.baseline_assessment_id,
        data_class=payload.data_class,
        session_origin=payload.session_origin,
        recommendation_status=response.status,
        sensor_snapshot=sensor_snapshot,
        score_snapshot=score_snapshot,
        sensor_changes=sensor_changes,
        score_changes=score_changes,
        persisted=True,
        deduplicated=deduplicated,
    )


def _numeric_sensor_snapshot(request: RecommendationRequest) -> dict[str, Any]:
    snapshot = request.sensor_genetic_snapshot
    assert snapshot is not None
    payload = snapshot.model_dump(mode="json")
    return {
        key: value
        for key, value in payload.items()
        if key.startswith(("wearable_", "cgm_")) or key in {
            "daily_steps",
            "sleep_hours",
            "resting_heart_rate_bpm",
            "mean_glucose_mg_dl",
            "postprandial_peak_mg_dl",
            "postprandial_rise_mg_dl",
            "time_in_range_pct",
            "time_in_range_lower_mg_dl",
            "time_in_range_upper_mg_dl",
        }
    }


def _numeric_changes(
    baseline: dict[str, Any], follow_up: dict[str, Any]
) -> dict[str, dict[str, float | None]]:
    changes: dict[str, dict[str, float | None]] = {}
    for key in sorted(set(baseline) | set(follow_up)):
        before, after = baseline.get(key), follow_up.get(key)
        if isinstance(before, (int, float)) and not isinstance(before, bool) and isinstance(
            after, (int, float)
        ) and not isinstance(after, bool):
            changes[key] = {
                "baseline": float(before),
                "follow_up": float(after),
                "delta": round(float(after) - float(before), 6),
            }
    return changes


def calculate_device_score_changes(
    baseline: dict[str, dict[str, float]],
    follow_up: dict[str, dict[str, float]],
) -> dict[str, dict[str, float | bool | None]]:
    changes: dict[str, dict[str, float | bool | None]] = {}
    for ingredient in sorted(set(baseline) | set(follow_up)):
        before = baseline.get(ingredient)
        after = follow_up.get(ingredient)
        terms: dict[str, float | bool | None] = {
            "selected_at_baseline": before is not None,
            "selected_at_follow_up": after is not None,
        }
        for term in ("wearable_adjustment", "cgm_adjustment", "total"):
            terms[f"{term}_delta"] = (
                None
                if before is None or after is None
                else round(after[term] - before[term], 6)
            )
        changes[ingredient] = terms
    return changes


def _persist(store: InterimStore, values: dict[str, Any]) -> bool:
    with store.transaction(immediate=True) as connection:
        existing = connection.execute(
            "select * from device_recommendation_assessments where assessment_id=?",
            (values["assessment_id"],),
        ).fetchone()
        if existing is not None:
            if any(existing[key] != value for key, value in values.items()):
                raise ValueError("device_assessment_identity_conflict")
            return True
        connection.execute(
            """
            insert into device_recommendation_assessments(
              assessment_id, profile_id, phase, baseline_assessment_id, data_class,
              session_origin, request_sha256, sensor_snapshot_json, score_snapshot_json,
              sensor_changes_json, score_changes_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*values.values(), datetime.now(UTC).isoformat()),
        )
    return False


def _load_assessment(store: InterimStore, assessment_id: str) -> dict[str, Any]:
    connection = store.connect()
    try:
        row = connection.execute(
            "select * from device_recommendation_assessments where assessment_id=?",
            (assessment_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("device_baseline_assessment_not_found")
    return dict(row)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


__all__ = [
    "DeviceRecommendationAssessmentRequest",
    "DeviceRecommendationAssessmentResponse",
    "assess_device_recommendation",
    "calculate_device_score_changes",
]
