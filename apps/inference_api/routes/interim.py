from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.interim.agent import BoundedAgent
from wellnessbox_rnd.interim.behavior_log import BehaviorLogRecorder
from wellnessbox_rnd.interim.connectors import ingest_device_session, source_adapters
from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.data_lake import (
    ConsentStorageDeniedError,
    ExecutionLedger,
    ExecutionLedgerError,
    ExecutionNotFoundError,
    IdempotencyConflictError,
    open_data_lake_store,
)
from wellnessbox_rnd.interim.inference import recommend_with_registered_model
from wellnessbox_rnd.interim.kpi import evaluate_proxy_kpis
from wellnessbox_rnd.interim.safety import evaluate_safety
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.schemas.recommendation import DataSource


def require_internal_token(
    token: str | None = Header(default=None, alias="x-wb-rnd-token"),
) -> None:
    expected = os.getenv("WB_RND_INTERIM_INTERNAL_TOKEN", "")
    environment = os.getenv("WB_RND_APP_ENV", os.getenv("APP_ENV", "local")).lower()
    enabled = os.getenv("WB_RND_INTERIM_ENABLED", "").lower() in {"1", "true", "yes"}
    if (environment == "production" or enabled) and not expected:
        raise HTTPException(status_code=503, detail="internal_token_not_configured")
    if expected and (token is None or not hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="invalid_internal_token")


router = APIRouter(
    prefix="/interim",
    tags=["interim-proxy"],
    dependencies=[Depends(require_internal_token)],
)


def _store() -> InterimStore:
    return open_data_lake_store()


class ProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    consent_scopes: list[str]
    profile: dict[str, Any]


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    goals: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    safety: dict[str, Any] = Field(default_factory=dict)


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    tool_name: str
    arguments: dict[str, Any]
    consent_scopes: list[str] = Field(default_factory=list)


class DeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    profile_id: str
    source: str
    consent_scopes: list[str]
    payload: dict[str, Any]
    environment: str = "simulation"


class ExecutionEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal["conversation", "followup_evaluation"]
    source: DataSource
    idempotency_key: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any]


class BehaviorEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    event_name: str = Field(min_length=1, max_length=64)
    occurred_at: str = Field(min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
def status() -> dict[str, Any]:
    store = _store()
    tables = (
        "proxy_cases",
        "pro_observations",
        "adverse_events",
        "connector_sessions",
        "kpi_results",
        "profile_snapshots",
        "consent_snapshots",
        "executions",
        "execution_events",
        "execution_identities",
        "behavior_events",
    )
    return {
        "mode": DataClass.PROXY_GOLD_SIMULATION,
        "real_research_complete": False,
        "database": str(store.database_path),
        "counts": {table: int(store.scalar(f"select count(*) from {table}")) for table in tables},
    }


@router.get("/kpis")
def kpis() -> dict[str, Any]:
    return evaluate_proxy_kpis(_store()).to_dict()


@router.post("/profiles")
def upsert_profile(payload: ProfileRequest) -> dict[str, Any]:
    canonical = json.dumps(
        payload.profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    with _store().transaction() as connection:
        connection.execute(
            """
            insert into user_profiles values (?, ?, ?, ?, ?, ?)
            on conflict(profile_id) do update set
              consent_scopes_json=excluded.consent_scopes_json,
              payload_json=excluded.payload_json, payload_sha256=excluded.payload_sha256
            """,
            (
                payload.profile_id,
                DataClass.PROXY_GOLD_SIMULATION,
                json.dumps(payload.consent_scopes),
                canonical,
                hashlib.sha256(canonical.encode()).hexdigest(),
                datetime.now(UTC).isoformat(),
            ),
        )
    return {"profile_id": payload.profile_id, "stored": True}


@router.post("/recommendations")
def recommendation(payload: RecommendationRequest) -> dict[str, Any]:
    store = _store()
    profile_rows = store.rows(
        "select payload_json from user_profiles where profile_id=?", (payload.profile_id,)
    )
    if not profile_rows:
        raise HTTPException(status_code=404, detail="profile_not_found")
    profile = json.loads(profile_rows[0][0])
    prediction = recommend_with_registered_model(store, profile=profile, goals=payload.goals)
    safety_payload = dict(payload.safety)
    safety_payload.update(profile)
    safety_payload["ingredients"] = list(prediction.ingredients)
    safety_payload["medications"] = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in profile.get("medications", [])
    ]
    decision = evaluate_safety(safety_payload, store=store)
    run_id = f"rec_{uuid4().hex}"
    status_value = "BLOCKED" if decision.hard_failure else "READY"
    ranked = (
        []
        if decision.hard_failure
        else [
            {
                "ingredient": ingredient,
                "rank": index + 1,
                "score": prediction.scores[index],
                "evidence_ids": list(prediction.evidence_ids),
            }
            for index, ingredient in enumerate(prediction.ingredients)
        ]
    )
    request_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    response = {
        "run_id": run_id,
        "status": status_value,
        "mode": DataClass.PROXY_GOLD_SIMULATION,
        "simulation": True,
        "model_id": prediction.model_id,
        "safety_action": decision.action,
        "findings": [finding.__dict__ for finding in decision.findings],
        "recommendations": ranked,
        "uncertainty": "실제 약사 골드 라벨로 교체 전인 시뮬레이션 결과입니다.",
    }
    with store.transaction() as connection:
        connection.execute(
            "insert into recommendation_runs values (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                payload.profile_id,
                prediction.model_id,
                status_value,
                request_hash,
                json.dumps(response, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        connection.executemany(
            "insert into recommendation_items values (?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    item["ingredient"],
                    item["rank"],
                    item["score"],
                    "ALLOW",
                    json.dumps(item["evidence_ids"]),
                )
                for item in ranked
            ],
        )
    return response


@router.post("/agent/runs")
def create_agent_run(
    profile_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    return BoundedAgent(_store()).create_run(profile_id=profile_id, idempotency_key=idempotency_key)


@router.post("/agent/tools")
def execute_tool(payload: ToolRequest) -> dict[str, Any]:
    try:
        return BoundedAgent(_store()).execute_tool(
            run_id=payload.run_id,
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            consent_scopes=set(payload.consent_scopes),
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/connectors/device")
def connector(payload: DeviceRequest) -> dict[str, Any]:
    try:
        return ingest_device_session(
            _store(),
            session_id=payload.session_id,
            profile_id=payload.profile_id,
            source=payload.source,
            consent_scopes=set(payload.consent_scopes),
            payload=payload.payload,
            environment=payload.environment,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.get("/executions/{execution_id}")
def execution_trace(execution_id: str) -> dict[str, Any]:
    try:
        return ExecutionLedger(_store()).get_trace(execution_id).model_dump(mode="json")
    except ExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/executions/{execution_id}/events")
def append_execution_event(
    execution_id: str,
    payload: ExecutionEventRequest,
) -> dict[str, Any]:
    try:
        result = ExecutionLedger(_store()).append_event(
            execution_id=execution_id,
            event_type=payload.event_type,
            source=payload.source.value,
            idempotency_key=payload.idempotency_key,
            payload=payload.payload,
        )
        return result.model_dump(mode="json")
    except ExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ConsentStorageDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/behavior-events")
def append_behavior_event(payload: BehaviorEventRequest) -> dict[str, Any]:
    try:
        result = BehaviorLogRecorder(_store()).append_event(
            profile_id=payload.profile_id,
            event_name=payload.event_name,
            occurred_at=payload.occurred_at,
            idempotency_key=payload.idempotency_key,
            payload=payload.payload,
        )
        return result.model_dump(mode="json")
    except ConsentStorageDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ExecutionLedgerError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/log-classes")
def log_class_summary() -> dict[str, Any]:
    return BehaviorLogRecorder(_store()).log_class_summary().model_dump(mode="json")


@router.get("/admin/sources")
def admin_sources() -> dict[str, Any]:
    rows = _store().rows("select * from source_registry order by source_id")
    return {
        "items": [dict(row) for row in rows],
        "adapters": [item.__dict__ for item in source_adapters()],
    }


@router.get("/admin/reviews")
def review_queue(
    status_filter: Annotated[str, Query(alias="status")] = "OPEN",
    pharmacy_id: Annotated[int, Query(ge=1)] = 1,
) -> dict[str, Any]:
    rows = _store().rows(
        "select * from review_tasks where status=? and pharmacy_id=? order by created_at",
        (status_filter, pharmacy_id),
    )
    return {"mode": DataClass.PROXY_GOLD_SIMULATION, "items": [dict(row) for row in rows]}


@router.post("/admin/reviews/{review_id}/decision")
def decide_review(review_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    pharmacy_id = decision.pop("pharmacy_id", None)
    if not isinstance(pharmacy_id, int) or pharmacy_id < 1:
        raise HTTPException(status_code=422, detail="pharmacy_id_required")
    with _store().transaction() as connection:
        changed = connection.execute(
            """
            update review_tasks set status='COMPLETED', decision_json=?, completed_at=?
            where review_id=? and pharmacy_id=? and status='OPEN'
            """,
            (
                json.dumps(decision, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
                review_id,
                pharmacy_id,
            ),
        ).rowcount
    if changed != 1:
        raise HTTPException(status_code=409, detail="review_already_decided_or_missing")
    return {"review_id": review_id, "status": "COMPLETED", "immutable": True}
