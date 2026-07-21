from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from wellnessbox_rnd.chat import (
    ChatAdapterRequest,
    generate_chat_answer_with_openai_fallback,
    load_approved_counseling_scope,
    load_retrieval_corpus_manifest,
)
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
from wellnessbox_rnd.interim.data_mutation import (
    DataMutationLedger,
    EventMutationNotFoundError,
    EventMutationStateError,
)
from wellnessbox_rnd.interim.inference import recommend_with_registered_model
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.kpi import evaluate_proxy_kpis
from wellnessbox_rnd.interim.plan_lifecycle import (
    PlanLifecycleService,
    PlanLifecycleTransitionRequestV1,
)
from wellnessbox_rnd.interim.reviews import (
    PharmacistReviewDecisionV1,
    PharmacistReviewService,
)
from wellnessbox_rnd.interim.safety import SafetyDecision, SafetyRank, evaluate_safety
from wellnessbox_rnd.interim.session_replay import (
    SessionReplayIntegrityError,
    SessionReplayLedger,
    SessionReplayUnavailableError,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_correction import correct_and_recalculate_pro_followup_v1
from wellnessbox_rnd.orchestration.pro_plan_service import (
    enroll_pro_plan_v1,
    record_or_correct_pro_followup_v1,
)
from wellnessbox_rnd.schemas.recommendation import (
    DataSource,
)
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationRequest as CoreRecommendationRequest,
)


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


def require_event_mutation_token(
    token: str | None = Header(default=None, alias="x-wb-rnd-token"),
) -> None:
    expected = os.getenv("WB_RND_INTERIM_INTERNAL_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="internal_token_not_configured")
    if token is None or not hmac.compare_digest(token, expected):
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


class ProductConstraintsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_total_cost_krw: StrictInt = Field(default=100_000, ge=0)
    max_products: StrictInt = Field(default=5, ge=1, le=20)


class ProductOptimizationConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_optimization_constraints_v1"] = (
        "product_optimization_constraints_v1"
    )
    max_total_cost_krw: StrictInt = Field(ge=0)
    max_products: StrictInt = Field(ge=1, le=20)
    excluded_ingredient_keys: tuple[str, ...] = ()
    safety_rule_ids: tuple[str, ...] = ()


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    goals: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    safety: dict[str, Any] = Field(default_factory=dict)
    product_constraints: ProductConstraintsRequest = Field(
        default_factory=ProductConstraintsRequest
    )


class CounselingTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["counseling_turn_request_v1"] = "counseling_turn_request_v1"
    service_session_id: str = Field(min_length=1, max_length=128)
    turn_id: str = Field(min_length=1, max_length=128)
    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    query: str = Field(min_length=1, max_length=2_000)
    answered_at: datetime
    profile: dict[str, Any]
    consent_scopes: list[str] = Field(default_factory=list)
    goals: list[str] = Field(min_length=1, max_length=20)
    ingredients: list[str] = Field(default_factory=list, max_length=20)
    safety: dict[str, Any] = Field(default_factory=dict)
    product_constraints: ProductConstraintsRequest = Field(
        default_factory=ProductConstraintsRequest
    )

    @model_validator(mode="after")
    def validate_answer_time(self) -> CounselingTurnRequest:
        if self.answered_at.tzinfo is None or self.answered_at.utcoffset() is None:
            raise ValueError("counseling_answered_at_timezone_required")
        return self


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    tool_name: str
    arguments: dict[str, Any]
    consent_scopes: list[str] = Field(default_factory=list)


class OrderedWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    idempotency_key: str = Field(min_length=1, max_length=128)
    safety: dict[str, Any]
    ingredients: list[str] = Field(min_length=1, max_length=20)
    evidence_query: str = Field(min_length=1, max_length=200)
    max_items: int = Field(ge=1, le=20)


class DuePlanCronRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: datetime | None = None


class DeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    profile_id: str
    source: str
    consent_scopes: list[str]
    payload: dict[str, Any]
    environment: str = "simulation"
    execution_id: str | None = None
    plan_id: str | None = None

    @model_validator(mode="after")
    def validate_plan_context(self) -> DeviceRequest:
        if (self.execution_id is None) != (self.plan_id is None):
            raise ValueError("device_plan_context_must_be_complete")
        return self


class AdverseEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=3, max_length=128)
    run_id: str | None = None
    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    execution_id: str
    plan_id: str = Field(min_length=3, max_length=128)
    serious: bool
    observed_at: datetime
    related_to_recommendation: bool = True


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


_CONSERVATIVE_LIST_FIELDS = (
    "symptoms",
    "conditions",
    "medications",
    "allergies",
    "risk_flags",
    "duplicate_ingredients",
)
_CONSERVATIVE_RISK_FLAGS = (
    "pregnant",
    "lactating",
    "above_ul",
    "requires_test",
    "timing_conflict",
    "label_constraint_violation",
)


def _stable_union(*values: object) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, list):
            continue
        for item in value:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def _merge_safety_input(
    profile: dict[str, Any],
    current: dict[str, Any],
    ingredients: list[str],
) -> dict[str, Any]:
    merged = dict(profile)
    merged.update(current)
    for field in _CONSERVATIVE_LIST_FIELDS:
        merged[field] = _stable_union(profile.get(field), current.get(field))
    merged["ingredients"] = _stable_union(
        profile.get("ingredients"), current.get("ingredients"), ingredients
    )
    for field in _CONSERVATIVE_RISK_FLAGS:
        merged[field] = bool(profile.get(field)) or bool(current.get(field))
    if "age" in profile:
        merged["age"] = profile["age"]
    surgery_windows = [
        value
        for value in (
            profile.get("surgery_within_days"),
            current.get("surgery_within_days"),
        )
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if surgery_windows:
        merged["surgery_within_days"] = min(surgery_windows)
    test_availability = [
        bool(source["test_available"])
        for source in (profile, current)
        if "test_available" in source
    ]
    if test_availability:
        merged["test_available"] = all(test_availability)
    evidence_expiry = [
        str(source["evidence_valid_until"])
        for source in (profile, current)
        if source.get("evidence_valid_until")
    ]
    if evidence_expiry:
        merged["evidence_valid_until"] = min(evidence_expiry)
    merged["medications"] = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in merged["medications"]
    ]
    return merged


def _source_safety_input(source: dict[str, Any], ingredients: list[str]) -> dict[str, Any]:
    payload = dict(source)
    payload["ingredients"] = _stable_union(source.get("ingredients"), ingredients)
    payload["medications"] = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in _stable_union(source.get("medications"))
    ]
    return payload


def _combine_safety_decisions(*decisions: SafetyDecision) -> SafetyDecision:
    findings = []
    seen = set()
    for decision in decisions:
        for finding in decision.findings:
            if finding not in seen:
                seen.add(finding)
                findings.append(finding)
    action = max(
        (decision.action for decision in decisions),
        key=lambda value: SafetyRank[value],
        default="PASS",
    )
    return SafetyDecision(action=action, findings=tuple(findings))


class EventMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    target_type: Literal["execution_event", "behavior_event"]
    target_event_id: str = Field(min_length=1, max_length=128)
    operation: Literal["correction", "deletion"]
    idempotency_key: str = Field(min_length=1, max_length=128)
    replacement_payload: dict[str, Any] | None = None


class PROCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(pattern=r"^exec_[a-f0-9]{32}$")
    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    target_event_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    replacement_payload: dict[str, Any]


class PROAnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument: Literal["PSQI", "ISI", "PSS10"]
    item_scores: list[int] = Field(min_length=1, max_length=10)


class PROPlanEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_request: CoreRecommendationRequest
    baseline: PROAnswersRequest
    observed_at: datetime
    data_class: Literal["SYNTHETIC_OUTCOME_PROXY", "REAL_WORLD_OUTCOME"] = "SYNTHETIC_OUTCOME_PROXY"


class PROFollowUpRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(pattern=r"^exec_[a-f0-9]{32}$")
    profile_id: str = Field(pattern=r"^usr_[a-f0-9]{16,64}$")
    plan_id: str = Field(min_length=3, max_length=128)
    timepoint: Literal["week_2", "week_4", "discontinuation"]
    answers: PROAnswersRequest
    observed_at: datetime
    actual_day_index: int = Field(ge=0)
    planned_dose_count: int = Field(ge=1)
    taken_dose_count: int = Field(ge=0)
    adverse_events: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    discontinuation_reason: str | None = Field(default=None, min_length=1, max_length=128)


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
        "execution_replay_snapshots",
        "execution_replay_runs",
        "behavior_events",
        "event_mutations",
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


def _recommendation(
    payload: RecommendationRequest, *, idempotency_identity: str | None = None
) -> dict[str, Any]:
    store = _store()
    profile_rows = store.rows(
        "select payload_json from user_profiles where profile_id=?", (payload.profile_id,)
    )
    if not profile_rows:
        raise HTTPException(status_code=404, detail="profile_not_found")
    try:
        BoundedAgent(store)._raise_if_recommendation_held(payload.profile_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    profile = json.loads(profile_rows[0][0])
    profile_safety_payload = _source_safety_input(profile, payload.ingredients)
    current_safety_payload = _source_safety_input(payload.safety, payload.ingredients)
    pre_safety_payload = _merge_safety_input(
        profile,
        payload.safety,
        payload.ingredients,
    )
    decision = _combine_safety_decisions(
        evaluate_safety(
            profile_safety_payload,
            store=store,
        ),
        evaluate_safety(
            current_safety_payload,
            store=store,
        ),
        evaluate_safety(
            pre_safety_payload,
            store=store,
            predicate_payloads=(profile_safety_payload, current_safety_payload),
        ),
    )
    prediction = None
    if not decision.hard_failure:
        prediction = recommend_with_registered_model(
            store,
            profile=profile,
            goals=payload.goals,
        )
        post_safety_payload = dict(pre_safety_payload)
        post_safety_payload["ingredients"] = list(prediction.ingredients)
        decision = _combine_safety_decisions(
            decision,
            evaluate_safety(
                post_safety_payload,
                store=store,
                predicate_payloads=(profile_safety_payload, current_safety_payload),
            ),
        )
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
    product_constraints = ProductOptimizationConstraints(
        max_total_cost_krw=payload.product_constraints.max_total_cost_krw,
        max_products=payload.product_constraints.max_products,
        excluded_ingredient_keys=(
            tuple(
                sorted(
                    {
                        item.strip().lower()
                        for item in (
                            *payload.ingredients,
                            *(prediction.ingredients if prediction is not None else ()),
                        )
                        if item.strip()
                    }
                )
            )
            if decision.hard_failure
            else ()
        ),
        safety_rule_ids=tuple(sorted({finding.rule_id for finding in decision.findings})),
    )
    response = {
        "run_id": run_id,
        "status": status_value,
        "mode": DataClass.PROXY_GOLD_SIMULATION,
        "simulation": True,
        "model_id": prediction.model_id if prediction is not None else None,
        "safety_action": decision.action,
        "findings": [finding.__dict__ for finding in decision.findings],
        "recommendations": ranked,
        "product_optimization_constraints": product_constraints.model_dump(mode="json"),
        "uncertainty": "실제 약사 골드 라벨로 교체 전인 시뮬레이션 결과입니다.",
    }
    with store.transaction(immediate=True) as connection:
        if BoundedAgent._recommendation_hold_exists(
            connection, profile_id=payload.profile_id
        ):
            raise HTTPException(
                status_code=409,
                detail="serious_adverse_event_recommendation_hold",
            )
        connection.execute(
            """
            insert into recommendation_runs(
              run_id, profile_id, model_id, status, request_sha256,
              response_json, created_at, completed_at, idempotency_identity
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                payload.profile_id,
                prediction.model_id if prediction is not None else None,
                status_value,
                request_hash,
                json.dumps(response, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
                idempotency_identity,
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


@router.post("/recommendations")
def recommendation(payload: RecommendationRequest) -> dict[str, Any]:
    return _recommendation(payload)


_COUNSELING_CORPUS_PATH = (
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    + "/data/knowledge/counseling_retrieval_corpus_manifest_v1.json"
)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@router.post("/counseling/turns")
def counseling_turn(payload: CounselingTurnRequest) -> dict[str, Any]:
    """Compose verified counseling and an existing recommendation run for one chat session."""
    store = _store()
    request_identity = _canonical_sha256(payload.model_dump(mode="json"))
    scoped_run_key = (
        f"{payload.profile_id}:counseling-session:{payload.service_session_id}"
    )
    prior_steps = store.rows(
        """
        select s.arguments_sha256, s.binding_json
        from agent_steps s join agent_runs r on r.run_id=s.run_id
        where r.profile_id=? and r.idempotency_key=?
          and s.tool_name='counseling_answer' and s.binding_json is not null
        """,
        (payload.profile_id, scoped_run_key),
    )
    for prior_step in prior_steps:
        binding = json.loads(str(prior_step["binding_json"]))
        if (
            binding.get("service_session_id") == payload.service_session_id
            and binding.get("turn_id") == payload.turn_id
            and str(prior_step["arguments_sha256"]) != request_identity
        ):
            raise HTTPException(status_code=409, detail="counseling_turn_payload_conflict")
    upsert_profile(
        ProfileRequest(
            profile_id=payload.profile_id,
            consent_scopes=payload.consent_scopes,
            profile=payload.profile,
        )
    )
    agent_run = BoundedAgent(store).create_run(
        profile_id=payload.profile_id,
        idempotency_key=f"counseling-session:{payload.service_session_id}",
    )
    manifest = load_retrieval_corpus_manifest(_COUNSELING_CORPUS_PATH)
    adapter_response = generate_chat_answer_with_openai_fallback(
        manifest,
        ChatAdapterRequest(
            query=payload.query,
            knowledge_scope=load_approved_counseling_scope(),
            as_of=payload.answered_at,
        ),
        allow_live_api=False,
    )
    if not adapter_response.verification.passed:
        raise HTTPException(status_code=422, detail="counseling_answer_verification_failed")

    recommendation_response: dict[str, Any] | None = None
    recommendation_payload = RecommendationRequest(
        profile_id=payload.profile_id,
        goals=payload.goals,
        ingredients=payload.ingredients,
        safety=payload.safety,
        product_constraints=payload.product_constraints,
    )
    recommendation_request_hash = hashlib.sha256(
        recommendation_payload.model_dump_json().encode()
    ).hexdigest()
    recommendation_idempotency_identity = _canonical_sha256(
        {
            "profile_id": payload.profile_id,
            "request_sha256": recommendation_request_hash,
        }
    )
    if adapter_response.answer.status != "safety_escalation":
        existing = store.rows(
            "select response_json from recommendation_runs "
            "where profile_id=? and request_sha256=? order by created_at limit 1",
            (payload.profile_id, recommendation_request_hash),
        )
        if existing:
            recommendation_response = json.loads(str(existing[0]["response_json"]))
        else:
            try:
                recommendation_response = _recommendation(
                    recommendation_payload,
                    idempotency_identity=recommendation_idempotency_identity,
                )
            except sqlite3.IntegrityError:
                concurrent = store.rows(
                    "select response_json from recommendation_runs "
                    "where profile_id=? and request_sha256=?",
                    (payload.profile_id, recommendation_request_hash),
                )
                if not concurrent:
                    raise
                recommendation_response = json.loads(
                    str(concurrent[0]["response_json"])
                )

    answer_payload = adapter_response.answer.model_dump(mode="json")
    binding_payload = {
        "schema_version": "counseling_session_binding_v1",
        "service_session_id": payload.service_session_id,
        "turn_id": payload.turn_id,
        "profile_id": payload.profile_id,
        "agent_run_id": str(agent_run["run_id"]),
        "answer_sha256": _canonical_sha256(answer_payload),
        "recommendation_run_id": (
            None if recommendation_response is None else recommendation_response["run_id"]
        ),
    }
    binding_sha256 = _canonical_sha256(binding_payload)
    with store.transaction(immediate=True) as connection:
        duplicate = connection.execute(
            "select arguments_sha256 from agent_steps "
            "where run_id=? and tool_name='counseling_answer' "
            "and json_extract(binding_json, '$.service_session_id')=? "
            "and json_extract(binding_json, '$.turn_id')=?",
            (agent_run["run_id"], payload.service_session_id, payload.turn_id),
        ).fetchone()
        if duplicate is not None and str(duplicate["arguments_sha256"]) != request_identity:
            raise HTTPException(status_code=409, detail="counseling_turn_payload_conflict")
        if duplicate is None:
            step_index = int(
                connection.execute(
                    "select coalesce(max(step_index), -1) + 1 from agent_steps where run_id=?",
                    (agent_run["run_id"],),
                ).fetchone()[0]
            )
            connection.execute(
                """
                insert into agent_steps(
                  run_id, step_index, tool_name, arguments_sha256, result_sha256,
                  postcondition_success, reason_codes_json, created_at,
                  binding_json, binding_sha256
                ) values (?, ?, 'counseling_answer', ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    agent_run["run_id"],
                    step_index,
                    request_identity,
                    binding_payload["answer_sha256"],
                    json.dumps(
                        [
                            "SERVICE_CHAT_SESSION_BOUND",
                            "RECOMMENDATION_SUPPRESSED_FOR_URGENT_SAFETY"
                            if recommendation_response is None
                            else "RECOMMENDATION_RUN_BOUND",
                        ],
                        separators=(",", ":"),
                    ),
                    payload.answered_at.isoformat(),
                    json.dumps(
                        binding_payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    binding_sha256,
                ),
            )

    return {
        "schema_version": "counseling_turn_response_v1",
        "service_session_id": payload.service_session_id,
        "turn_id": payload.turn_id,
        "agent_run_id": agent_run["run_id"],
        "answer": answer_payload,
        "verification": adapter_response.verification.model_dump(mode="json"),
        "recommendation_execution": (
            None
            if recommendation_response is None
            else {
                "run_id": recommendation_response["run_id"],
                "status": recommendation_response["status"],
                "simulation": recommendation_response["simulation"],
            }
        ),
        "session_binding_sha256": binding_sha256,
        "deduplicated": bool(agent_run.get("deduplicated")),
    }


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


@router.post("/agent/workflow")
def execute_ordered_workflow(payload: OrderedWorkflowRequest) -> dict[str, Any]:
    try:
        return BoundedAgent(_store()).execute_recommendation_workflow(
            profile_id=payload.profile_id,
            idempotency_key=payload.idempotency_key,
            safety_arguments=payload.safety,
            ingredients=payload.ingredients,
            evidence_query=payload.evidence_query,
            max_items=payload.max_items,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/agent/cron/due-plans")
def enqueue_due_plan_reevaluations(payload: DuePlanCronRequest) -> dict[str, object]:
    if payload.as_of is not None and os.environ.get("WB_RND_ALLOW_CRON_AS_OF_OVERRIDE") != "1":
        raise HTTPException(status_code=403, detail="cron_as_of_override_forbidden")
    try:
        return WorkflowJobQueue(_store()).enqueue_due_plan_reevaluations(
            as_of=payload.as_of or datetime.now(UTC)
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/plan-lifecycle/transitions",
    dependencies=[Depends(require_event_mutation_token)],
)
def transition_plan_lifecycle(
    payload: PlanLifecycleTransitionRequestV1,
) -> dict[str, Any]:
    try:
        return PlanLifecycleService(_store()).transition(payload).model_dump(mode="json")
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        detail = str(error)
        if detail in {
            "plan_lifecycle_execution_not_found",
            "plan_lifecycle_plan_not_found",
        }:
            status_code = 404
        elif "idempotency" in detail or "stale_state" in detail:
            status_code = 409
        else:
            status_code = 422
        raise HTTPException(status_code=status_code, detail=detail) from error


@router.post("/connectors/device")
def connector(payload: DeviceRequest) -> dict[str, Any]:
    try:
        store = _store()
        result = ingest_device_session(
            store,
            session_id=payload.session_id,
            profile_id=payload.profile_id,
            source=payload.source,
            consent_scopes=set(payload.consent_scopes),
            payload=payload.payload,
            environment=payload.environment,
        )
        if result["success"] and payload.execution_id and payload.plan_id:
            row = store.rows(
                "select row_sha256, payload_json from connector_sessions where session_id=?",
                (payload.session_id,),
            )[0]
            stored_payload = json.loads(row["payload_json"])
            observed_at = datetime.fromisoformat(
                str(stored_payload["observed_at"]).replace("Z", "+00:00")
            )
            result["next_job_decision"] = WorkflowJobQueue(
                store
            ).enqueue_input_reevaluation(
                profile_id=payload.profile_id,
                plan_id=payload.plan_id,
                execution_id=payload.execution_id,
                input_kind="DEVICE",
                input_id=payload.session_id,
                input_sha256=str(row["row_sha256"]),
                received_at=observed_at,
            )
        return result
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/agent/adverse-events",
    dependencies=[Depends(require_event_mutation_token)],
)
def record_adverse_event(payload: AdverseEventRequest) -> dict[str, Any]:
    try:
        return BoundedAgent(_store()).record_adverse_event(
            run_id=payload.run_id,
            arguments=payload.model_dump(mode="json", exclude={"run_id"}),
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        status_code = 409 if "idempotency" in str(error) else 422
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.get("/executions/{execution_id}")
def execution_trace(execution_id: str) -> dict[str, Any]:
    try:
        return ExecutionLedger(_store()).get_trace(execution_id).model_dump(mode="json")
    except ExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/executions")
def saved_executions(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    return SessionReplayLedger(_store()).summary(limit=limit).model_dump(mode="json")


@router.post("/executions/{execution_id}/replay")
def replay_execution(execution_id: str) -> dict[str, Any]:
    try:
        return SessionReplayLedger(_store()).replay(execution_id).model_dump(mode="json")
    except ExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SessionReplayUnavailableError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SessionReplayIntegrityError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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


@router.post(
    "/event-mutations",
    dependencies=[Depends(require_event_mutation_token)],
)
def mutate_event(payload: EventMutationRequest) -> dict[str, Any]:
    try:
        return DataMutationLedger(_store()).apply(**payload.model_dump()).model_dump(mode="json")
    except EventMutationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (IdempotencyConflictError, EventMutationStateError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/event-mutations/{mutation_id}",
    dependencies=[Depends(require_event_mutation_token)],
)
def event_mutation(mutation_id: str) -> dict[str, Any]:
    try:
        return DataMutationLedger(_store()).get(mutation_id).model_dump(mode="json")
    except EventMutationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/pro/followups/correct-and-recalculate",
    dependencies=[Depends(require_event_mutation_token)],
)
def correct_pro_followup(payload: PROCorrectionRequest) -> dict[str, Any]:
    try:
        return correct_and_recalculate_pro_followup_v1(
            _store(),
            **payload.model_dump(),
        ).model_dump(mode="json")
    except ExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (EventMutationStateError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/pro/plans",
    dependencies=[Depends(require_event_mutation_token)],
)
def enroll_pro_plan(payload: PROPlanEnrollmentRequest) -> dict[str, Any]:
    try:
        return enroll_pro_plan_v1(
            _store(),
            recommendation_request=payload.recommendation_request,
            instrument=payload.baseline.instrument,
            item_scores=payload.baseline.item_scores,
            observed_at=payload.observed_at,
            data_class=payload.data_class,
        )
    except ConsentStorageDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ExecutionLedgerError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/pro/followups",
    dependencies=[Depends(require_event_mutation_token)],
)
def record_pro_followup(payload: PROFollowUpRecordRequest) -> dict[str, Any]:
    try:
        store = _store()
        serious_events = [
            event for event in payload.adverse_events if event.get("severity") == "serious"
        ]
        stop_result = None
        if serious_events:
            event = serious_events[0]
            stop_result = BoundedAgent(store).record_adverse_event(
                run_id=None,
                arguments={
                    "case_id": str(event["adverse_event_id"]),
                    "profile_id": payload.profile_id,
                    "execution_id": payload.execution_id,
                    "plan_id": payload.plan_id,
                    "serious": True,
                    "observed_at": payload.observed_at.isoformat(),
                    "related_to_recommendation": event.get("relatedness") != "not_related",
                },
            )
        result = record_or_correct_pro_followup_v1(
            store,
            execution_id=payload.execution_id,
            profile_id=payload.profile_id,
            plan_id=payload.plan_id,
            timepoint=payload.timepoint,
            instrument=payload.answers.instrument,
            item_scores=payload.answers.item_scores,
            observed_at=payload.observed_at,
            actual_day_index=payload.actual_day_index,
            planned_dose_count=payload.planned_dose_count,
            taken_dose_count=payload.taken_dose_count,
            adverse_events=payload.adverse_events,
            discontinuation_reason=payload.discontinuation_reason,
        )
        if stop_result is not None:
            result["next_job_decision"] = stop_result
        elif payload.timepoint == "discontinuation":
            result["next_job_decision"] = {
                "schema_version": "followup_input_next_job_decision_v1",
                "decision": "STOP_PLAN",
                "reason_code": "PRO_DISCONTINUATION_RECEIVED",
                "next_job": None,
            }
        else:
            input_sha256 = str(
                store.scalar(
                    "select effective_payload_sha256 from execution_events where event_id=?",
                    (result["event_id"],),
                )
            )
            effective_observed_at = datetime.fromisoformat(
                result["interpretation"]["follow_up_event"]["observed_at"]
            )
            result["next_job_decision"] = WorkflowJobQueue(
                store
            ).enqueue_input_reevaluation(
                profile_id=payload.profile_id,
                plan_id=payload.plan_id,
                execution_id=payload.execution_id,
                input_kind="PRO",
                input_id=f"{result['event_id']}:{input_sha256[:16]}",
                input_sha256=input_sha256,
                received_at=effective_observed_at,
            )
        return result
    except ExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (EventMutationStateError, ValueError) as error:
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
    pharmacy_id: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, Any]:
    if pharmacy_id is None:
        rows = _store().rows(
            """
            select * from review_tasks
            where status=? and pharmacy_id is null order by created_at
            """,
            (status_filter,),
        )
    else:
        rows = _store().rows(
            """
            select * from review_tasks
            where status=? and (pharmacy_id=? or pharmacy_id is null) order by created_at
            """,
            (status_filter, pharmacy_id),
        )
    return {"mode": DataClass.PROXY_GOLD_SIMULATION, "items": [dict(row) for row in rows]}


@router.post("/admin/reviews/{review_id}/decision")
def decide_review(
    review_id: str, decision: PharmacistReviewDecisionV1
) -> dict[str, Any]:
    try:
        return PharmacistReviewService(_store()).complete_review(
            review_id=review_id,
            decision=decision,
            completed_at=datetime.now(UTC),
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        status_code = 404 if str(error) == "review_missing" else 409
        raise HTTPException(status_code=status_code, detail=str(error)) from error
