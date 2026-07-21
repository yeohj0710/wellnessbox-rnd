from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from wellnessbox_rnd.interim.connectors import ingest_device_session
from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.safety import evaluate_safety
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.interim.workflow_contract import (
    CLOSED_LOOP_ALLOWED_OPERATIONS_V1,
    CLOSED_LOOP_TRANSITIONS_V1,
    ClosedLoopExecutionTraceV1,
    ClosedLoopOperation,
    ClosedLoopState,
    apply_closed_loop_transition_v1,
)

AgentState = ClosedLoopState
TRANSITIONS = CLOSED_LOOP_TRANSITIONS_V1

TOOL_NAMES = (
    "get_user_profile",
    "retrieve_evidence",
    "check_safety",
    "rank_ingredients",
    "optimize_regimen",
    "start_plan",
    "create_followup",
    "ingest_pro",
    "ingest_wearable",
)

_TOOL_OPERATIONS: dict[str, ClosedLoopOperation] = {
    "get_user_profile": ClosedLoopOperation.LOAD_PROFILE,
    "check_safety": ClosedLoopOperation.CHECK_SAFETY,
    "rank_ingredients": ClosedLoopOperation.GENERATE_CANDIDATES,
    "retrieve_evidence": ClosedLoopOperation.LOOKUP_EVIDENCE,
    "optimize_regimen": ClosedLoopOperation.OPTIMIZE,
    "start_plan": ClosedLoopOperation.START_PLAN,
    "create_followup": ClosedLoopOperation.SCHEDULE_FOLLOWUP,
    "ingest_pro": ClosedLoopOperation.INGEST_FOLLOWUP,
    "ingest_wearable": ClosedLoopOperation.INGEST_FOLLOWUP,
}

_DATABASE_LOCKS: dict[str, threading.RLock] = {}
_DATABASE_LOCKS_GUARD = threading.Lock()


def _database_lock(store: InterimStore) -> threading.RLock:
    key = str(store.database_path.resolve())
    with _DATABASE_LOCKS_GUARD:
        return _DATABASE_LOCKS.setdefault(key, threading.RLock())


def transition(current: AgentState, target: AgentState) -> AgentState:
    operations = [
        operation
        for operation in CLOSED_LOOP_ALLOWED_OPERATIONS_V1[current]
        if _transition_target(current, operation) == target
    ]
    if len(operations) != 1:
        raise ValueError(f"invalid_agent_transition:{current}:{target}")
    return apply_closed_loop_transition_v1(
        current=current,
        operation=operations[0],
        target=target,
    )


def _transition_target(
    current: AgentState,
    operation: ClosedLoopOperation,
) -> AgentState | None:
    for target in TRANSITIONS[current]:
        try:
            return apply_closed_loop_transition_v1(
                current=current,
                operation=operation,
                target=target,
            )
        except ValueError:
            continue
    return None


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


class BoundedAgent:
    def __init__(self, store: InterimStore):
        self.store = store

    def create_run(
        self,
        *,
        profile_id: str,
        idempotency_key: str,
        risk_tier: int = 1,
    ) -> dict[str, Any]:
        if not self.store.scalar(
            "select count(*) from user_profiles where profile_id=?", (profile_id,)
        ):
            raise ValueError("unknown_profile")
        scoped_key = f"{profile_id}:{idempotency_key}"
        existing = self.store.rows(
            "select * from agent_runs where idempotency_key=? and profile_id=?",
            (scoped_key, profile_id),
        )
        if existing:
            return dict(existing[0]) | {"deduplicated": True}
        run_id = f"run_{uuid4().hex}"
        now = datetime.now(UTC).isoformat()
        with self.store.transaction() as connection:
            connection.execute(
                """
                insert into agent_runs(
                  run_id, profile_id, idempotency_key, state_before, state_after,
                  risk_tier, status, created_at, completed_at
                ) values (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, null)
                """,
                (
                    run_id,
                    profile_id,
                    scoped_key,
                    AgentState.INTAKE,
                    AgentState.INTAKE,
                    risk_tier,
                    now,
                ),
            )
        return {"run_id": run_id, "state_after": AgentState.INTAKE, "deduplicated": False}

    def move(
        self,
        run_id: str,
        target: AgentState,
        *,
        operation: ClosedLoopOperation,
    ) -> AgentState:
        raise ValueError("direct_agent_move_forbidden")

    def _move_with_operation(
        self,
        *,
        run_id: str,
        operation: ClosedLoopOperation,
        target: AgentState,
    ) -> AgentState:
        row = self.store.rows("select state_after from agent_runs where run_id=?", (run_id,))
        if not row:
            raise ValueError("unknown_agent_run")
        current = AgentState(row[0][0])
        next_state = apply_closed_loop_transition_v1(
            current=current,
            operation=operation,
            target=target,
        )
        terminal = next_state in {AgentState.STOPPED, AgentState.COMPLETED}
        with self.store.transaction() as connection:
            connection.execute(
                """
                update agent_runs set state_before=?, state_after=?, status=?, completed_at=?
                where run_id=?
                """,
                (
                    current,
                    next_state,
                    "COMPLETED" if terminal else "ACTIVE",
                    datetime.now(UTC).isoformat() if terminal else None,
                    run_id,
                ),
            )
        return next_state

    def execute_tool(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        consent_scopes: set[str] | None = None,
    ) -> dict[str, Any]:
        with _database_lock(self.store):
            return self._execute_tool_serialized(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
                consent_scopes=consent_scopes,
            )

    def _execute_tool_serialized(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        consent_scopes: set[str] | None = None,
    ) -> dict[str, Any]:
        if tool_name not in TOOL_NAMES:
            raise ValueError("unknown_agent_tool")
        run_rows = self.store.rows("select * from agent_runs where run_id=?", (run_id,))
        if not run_rows:
            raise ValueError("unknown_agent_run")
        run = run_rows[0]
        if run["status"] != "ACTIVE":
            raise ValueError("agent_run_not_active")
        operation = _TOOL_OPERATIONS.get(tool_name)
        current_state = AgentState(run["state_after"])
        if (
            operation is not None
            and operation not in CLOSED_LOOP_ALLOWED_OPERATIONS_V1[current_state]
        ):
            raise ValueError(
                "workflow_operation_not_allowed:"
                f"{current_state.value}:{operation.value}"
            )
        profile_id = str(run["profile_id"])
        supplied_profile = str(arguments.get("profile_id", profile_id))
        if supplied_profile != profile_id:
            raise PermissionError("agent_run_owner_mismatch")
        profile_rows = self.store.rows(
            "select consent_scopes_json from user_profiles where profile_id=?",
            (profile_id,),
        )
        if not profile_rows:
            raise ValueError("unknown_profile")
        stored_scopes = set(json.loads(profile_rows[0][0]))
        requested_scopes = consent_scopes or stored_scopes
        scopes = stored_scopes & requested_scopes
        safe_arguments = dict(arguments) | {"profile_id": profile_id}
        with self.store.transaction(immediate=True) as connection:
            claimed = connection.execute(
                """
                update agent_runs set status='EXECUTING'
                where run_id=? and status='ACTIVE' and state_after=?
                """,
                (run_id, current_state),
            ).rowcount
        if claimed != 1:
            raise ValueError("agent_run_concurrent_operation")
        try:
            result = self._dispatch(run_id, tool_name, safe_arguments, scopes)
            if not isinstance(result, dict) or result.get("postcondition_success") is False:
                raise RuntimeError("tool_postcondition_failed")
        except Exception:
            with self.store.transaction(immediate=True) as connection:
                connection.execute(
                    "update agent_runs set status='ACTIVE' where run_id=? and status='EXECUTING'",
                    (run_id,),
                )
            raise
        with self.store.transaction() as connection:
            step_index = connection.execute(
                "select count(*) from agent_steps where run_id=?", (run_id,)
            ).fetchone()[0]
            connection.execute(
                """
                insert into agent_steps(
                  run_id, step_index, tool_name, arguments_sha256, result_sha256,
                  postcondition_success, reason_codes_json, created_at
                ) values (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    run_id,
                    step_index,
                    tool_name,
                    _sha(safe_arguments),
                    _sha(result),
                    _json(result.get("reason_codes", [])),
                    datetime.now(UTC).isoformat(),
                ),
            )
            if operation is not None:
                target = _transition_target(current_state, operation)
                if target is None:
                    raise ValueError(
                        "workflow_transition_target_missing:"
                        f"{current_state.value}:{operation.value}"
                    )
                connection.execute(
                    """
                    update agent_runs set state_before=?, state_after=?, status='ACTIVE'
                    where run_id=? and status='EXECUTING'
                    """,
                    (current_state, target, run_id),
                )
            else:
                connection.execute(
                    "update agent_runs set status='ACTIVE' where run_id=? and status='EXECUTING'",
                    (run_id,),
                )
        return result

    def execute_recommendation_workflow(
        self,
        *,
        profile_id: str,
        idempotency_key: str,
        safety_arguments: dict[str, Any],
        ingredients: list[str],
        evidence_query: str,
        max_items: int,
    ) -> dict[str, Any]:
        with _database_lock(self.store):
            return self._execute_recommendation_workflow_serialized(
                profile_id=profile_id,
                idempotency_key=idempotency_key,
                safety_arguments=safety_arguments,
                ingredients=ingredients,
                evidence_query=evidence_query,
                max_items=max_items,
            )

    def _execute_recommendation_workflow_serialized(
        self,
        *,
        profile_id: str,
        idempotency_key: str,
        safety_arguments: dict[str, Any],
        ingredients: list[str],
        evidence_query: str,
        max_items: int,
    ) -> dict[str, Any]:
        supplied_safety_ingredients = safety_arguments.get("ingredients")
        if (
            supplied_safety_ingredients is not None
            and list(supplied_safety_ingredients) != ingredients
        ):
            raise ValueError("safety_candidate_ingredients_mismatch")
        safety_arguments = dict(safety_arguments) | {"ingredients": list(ingredients)}
        request_identity = _sha(
            {
                "safety_arguments": safety_arguments,
                "ingredients": ingredients,
                "evidence_query": evidence_query,
                "max_items": max_items,
            }
        )
        run = self._create_workflow_run(
            profile_id=profile_id,
            base_idempotency_key=idempotency_key,
            request_identity=request_identity,
        )
        run_id = str(run["run_id"])
        if run["deduplicated"]:
            return self._durable_workflow_trace(run_id)
        steps: list[dict[str, str]] = []

        def execute(operation: ClosedLoopOperation, tool_name: str, arguments: dict[str, Any]):
            before = self._state(run_id)
            result = self.execute_tool(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
            )
            after = self._state(run_id)
            steps.append(
                {
                    "operation": operation.value,
                    "state_before": before.value,
                    "state_after": after.value,
                }
            )
            return result

        execute(
            ClosedLoopOperation.LOAD_PROFILE,
            "get_user_profile",
            {"profile_id": profile_id},
        )
        before_consent = self._state(run_id)
        self._move_with_operation(
            run_id=run_id,
            operation=ClosedLoopOperation.VERIFY_CONSENT,
            target=AgentState.PROFILE_READY,
        )
        self._record_internal_operation(run_id, ClosedLoopOperation.VERIFY_CONSENT)
        steps.append(
            {
                "operation": ClosedLoopOperation.VERIFY_CONSENT.value,
                "state_before": before_consent.value,
                "state_after": AgentState.PROFILE_READY.value,
            }
        )
        safety = execute(
            ClosedLoopOperation.CHECK_SAFETY,
            "check_safety",
            safety_arguments,
        )
        if safety["action"] in {"BLOCK", "STOP_AND_ESCALATE"}:
            self._stop_workflow(run_id, steps)
            return self._workflow_trace(run_id, steps, plan_start_recorded=False)

        ranked = execute(
            ClosedLoopOperation.GENERATE_CANDIDATES,
            "rank_ingredients",
            {"ingredients": ingredients},
        )
        if not ranked["ranked"]:
            self._stop_workflow(run_id, steps)
            return self._workflow_trace(run_id, steps, plan_start_recorded=False)

        evidence = execute(
            ClosedLoopOperation.LOOKUP_EVIDENCE,
            "retrieve_evidence",
            {"query": evidence_query},
        )
        evidence_ids = sorted(
            str(item["evidence_id"])
            for item in evidence["passages"]
            if item.get("evidence_id")
        )
        if not evidence_ids:
            self._stop_workflow(run_id, steps)
            return self._workflow_trace(run_id, steps, plan_start_recorded=False)
        supported_ranked = [
            item
            for item in ranked["ranked"]
            if any(
                str(item["ingredient"]).lower() in str(passage["passage_text"]).lower()
                for passage in evidence["passages"]
            )
        ]
        if not supported_ranked:
            self._stop_workflow(run_id, steps)
            return self._workflow_trace(run_id, steps, plan_start_recorded=False)

        optimized = execute(
            ClosedLoopOperation.OPTIMIZE,
            "optimize_regimen",
            {
                "ranked": supported_ranked,
                "max_items": max_items,
                "evidence_ids": evidence_ids,
            },
        )
        execute(
            ClosedLoopOperation.START_PLAN,
            "start_plan",
            {
                "regimen": optimized["regimen"],
                "evidence_ids": evidence_ids,
            },
        )
        return self._workflow_trace(run_id, steps, plan_start_recorded=True)

    def _state(self, run_id: str) -> AgentState:
        value = self.store.scalar("select state_after from agent_runs where run_id=?", (run_id,))
        if value is None:
            raise ValueError("unknown_agent_run")
        return AgentState(value)

    def _stop_workflow(self, run_id: str, steps: list[dict[str, str]]) -> None:
        before = self._state(run_id)
        self._move_with_operation(
            run_id=run_id,
            operation=ClosedLoopOperation.STOP,
            target=AgentState.STOPPED,
        )
        self._record_internal_operation(run_id, ClosedLoopOperation.STOP)
        steps.append(
            {
                "operation": ClosedLoopOperation.STOP.value,
                "state_before": before.value,
                "state_after": AgentState.STOPPED.value,
            }
        )

    def _workflow_trace(
        self,
        run_id: str,
        steps: list[dict[str, str]],
        *,
        plan_start_recorded: bool,
    ) -> dict[str, Any]:
        return ClosedLoopExecutionTraceV1.model_validate(
            {
                "run_id": run_id,
                "status": self._state(run_id),
                "steps": steps,
                "plan_start_recorded": plan_start_recorded,
            }
        ).model_dump(mode="json")

    def _record_internal_operation(
        self, run_id: str, operation: ClosedLoopOperation
    ) -> None:
        payload = {"operation": operation.value, "postcondition_success": True}
        with self.store.transaction() as connection:
            step_index = connection.execute(
                "select count(*) from agent_steps where run_id=?", (run_id,)
            ).fetchone()[0]
            connection.execute(
                """
                insert into agent_steps(
                  run_id, step_index, tool_name, arguments_sha256, result_sha256,
                  postcondition_success, reason_codes_json, created_at
                ) values (?, ?, ?, ?, ?, 1, '[]', ?)
                """,
                (
                    run_id,
                    step_index,
                    operation.value,
                    _sha(payload),
                    _sha(payload),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def _durable_workflow_trace(self, run_id: str) -> dict[str, Any]:
        rows = self.store.rows(
            "select tool_name from agent_steps where run_id=? order by step_index", (run_id,)
        )
        reverse_tools = {name: operation for name, operation in _TOOL_OPERATIONS.items()}
        internal = {ClosedLoopOperation.VERIFY_CONSENT.value, ClosedLoopOperation.STOP.value}
        operations = [
            ClosedLoopOperation(str(row[0])) if row[0] in internal else reverse_tools[str(row[0])]
            for row in rows
        ]
        current = AgentState.INTAKE
        steps: list[dict[str, str]] = []
        for operation in operations:
            target = _transition_target(current, operation)
            if target is None:
                raise ValueError("durable_workflow_trace_invalid")
            steps.append(
                {
                    "operation": operation.value,
                    "state_before": current.value,
                    "state_after": target.value,
                }
            )
            current = target
        return self._workflow_trace(
            run_id, steps, plan_start_recorded=ClosedLoopOperation.START_PLAN in operations
        )

    def _create_workflow_run(
        self,
        *,
        profile_id: str,
        base_idempotency_key: str,
        request_identity: str,
    ) -> dict[str, Any]:
        scoped_prefix = f"{profile_id}:{base_idempotency_key}:"
        expected_key = f"{scoped_prefix}{request_identity}"
        with self.store.transaction(immediate=True) as connection:
            if connection.execute(
                "select count(*) from user_profiles where profile_id=?", (profile_id,)
            ).fetchone()[0] == 0:
                raise ValueError("unknown_profile")
            existing = connection.execute(
                "select * from agent_runs where profile_id=? and idempotency_key like ?",
                (profile_id, f"{scoped_prefix}%"),
            ).fetchall()
            if existing:
                exact = [row for row in existing if str(row["idempotency_key"]) == expected_key]
                if exact:
                    return dict(exact[0]) | {"deduplicated": True}
                raise ValueError("workflow_idempotency_payload_conflict")
            run_id = f"run_{uuid4().hex}"
            now = datetime.now(UTC).isoformat()
            connection.execute(
                """
                insert into agent_runs(
                  run_id, profile_id, idempotency_key, state_before, state_after,
                  risk_tier, status, created_at, completed_at
                ) values (?, ?, ?, ?, ?, 1, 'ACTIVE', ?, null)
                """,
                (
                    run_id,
                    profile_id,
                    expected_key,
                    AgentState.INTAKE,
                    AgentState.INTAKE,
                    now,
                ),
            )
        return {"run_id": run_id, "state_after": AgentState.INTAKE, "deduplicated": False}

    def _dispatch(
        self, run_id: str, tool_name: str, arguments: dict[str, Any], scopes: set[str]
    ) -> dict[str, Any]:
        profile_id = str(arguments.get("profile_id", ""))
        if tool_name == "get_user_profile":
            rows = self.store.rows(
                "select payload_json from user_profiles where profile_id=?", (profile_id,)
            )
            if not rows:
                raise ValueError("unknown_profile")
            return {"profile": json.loads(rows[0][0]), "postcondition_success": True}
        if tool_name == "retrieve_evidence":
            query = str(arguments.get("query", ""))[:200]
            rows = self.store.rows(
                """
                select ep.evidence_id, ep.passage_text, ep.effective_at
                from evidence_passages ep
                join source_registry sr on sr.source_id=ep.source_id
                where ep.passage_text like ? and ep.approved_for_safety=1
                  and sr.retired_at is null
                  and sr.metadata_json not like '%\"quarantined\":true%'
                limit 10
                """,
                (f"%{query}%",),
            )
            return {
                "passages": [dict(row) | {"untrusted_content": True} for row in rows],
                "postcondition_success": True,
            }
        if tool_name == "check_safety":
            decision = evaluate_safety(arguments, store=self.store)
            return {
                "action": decision.action,
                "findings": [finding.__dict__ for finding in decision.findings],
                "postcondition_success": True,
            }
        if tool_name == "rank_ingredients":
            ingredients = sorted({str(value) for value in arguments.get("ingredients", [])})
            ranked = [
                {"ingredient": value, "score": round(1 / (index + 1), 4)}
                for index, value in enumerate(ingredients)
            ]
            return {"ranked": ranked, "postcondition_success": bool(ranked)}
        if tool_name == "optimize_regimen":
            ranked = list(arguments.get("ranked", []))[: int(arguments.get("max_items", 3))]
            return {"regimen": ranked, "postcondition_success": bool(ranked)}
        if tool_name == "start_plan":
            regimen = list(arguments.get("regimen", []))
            evidence_ids = list(arguments.get("evidence_ids", []))
            return {
                "plan_start_recorded": bool(regimen) and bool(evidence_ids),
                "postcondition_success": bool(regimen) and bool(evidence_ids),
            }
        if tool_name == "create_followup":
            if "followup:write" not in scopes:
                raise PermissionError("missing_followup_consent")
            plan_id = str(arguments.get("plan_id", "")).strip()
            now = datetime.now(UTC)
            due_at_raw = arguments.get("due_at")
            due_at = (
                datetime.fromisoformat(str(due_at_raw))
                if due_at_raw
                else now + timedelta(days=int(arguments.get("days", 14)))
            )
            reminder_at = due_at - timedelta(
                days=int(arguments.get("reminder_days_before", 1))
            )
            scheduled = WorkflowJobQueue(self.store).schedule_followup_with_reminder(
                followup_id=str(arguments.get("followup_id") or f"fu_{uuid4().hex}"),
                profile_id=profile_id,
                plan_id=plan_id,
                due_at=due_at,
                reminder_at=reminder_at,
                requested_data=[str(item) for item in arguments.get("requested_data", [])],
                now=now,
            )
            return scheduled | {"postcondition_success": True}
        if tool_name == "ingest_pro":
            if "pro:write" not in scopes:
                raise PermissionError("missing_pro_consent")
            observation_id = str(arguments.get("observation_id") or f"pro_{uuid4().hex}")
            payload = _json(arguments)
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    insert into pro_observations values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(observation_id) do nothing
                    """,
                    (
                        observation_id,
                        profile_id,
                        DataClass.INTERIM_RUNTIME_EVENT,
                        int(arguments.get("timepoint_weeks", 0)),
                        float(arguments.get("z_pre", 0)),
                        float(arguments.get("z_post", 0)),
                        float(arguments.get("percentile_point_change", 0)),
                        arguments.get("adherence"),
                        _sha(arguments),
                        payload,
                    ),
                )
            return {"observation_id": observation_id, "postcondition_success": True}
        if tool_name == "ingest_wearable":
            result = ingest_device_session(
                self.store,
                session_id=str(arguments["session_id"]),
                profile_id=profile_id,
                source=str(arguments.get("source", "W")),
                consent_scopes=scopes,
                payload=dict(arguments["payload"]),
                environment=str(arguments.get("environment", "simulation")),
            )
            return result | {"postcondition_success": bool(result["success"])}
        if tool_name == "log_adverse_event":
            if "ae:write" not in scopes:
                raise PermissionError("missing_ae_consent")
            return self._log_adverse_event(run_id, arguments)
        raise AssertionError("unreachable_tool")

    def _log_adverse_event(self, run_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        case_id = str(arguments.get("case_id") or f"ae_{uuid4().hex}")
        profile_id = str(arguments.get("profile_id", "")) or None
        serious = bool(arguments.get("serious"))
        review_id = f"review_{uuid4().hex}" if serious else None
        payload = _json(arguments)
        now = datetime.now(UTC).isoformat()
        with self.store.transaction() as connection:
            connection.execute(
                """
                insert into adverse_events values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(case_id) do nothing
                """,
                (
                    case_id,
                    profile_id,
                    DataClass.INTERIM_RUNTIME_EVENT,
                    int(arguments.get("related_to_recommendation", True)),
                    int(serious),
                    "ESCALATED" if serious else "RECORDED",
                    arguments.get("observation_month"),
                    _sha(arguments),
                    payload,
                ),
            )
            if serious:
                connection.execute(
                    """
                    update agent_runs set state_before=state_after, state_after='STOPPED',
                      status='COMPLETED', completed_at=? where run_id=? and status='ACTIVE'
                    """,
                    (now, run_id),
                )
                connection.execute(
                    """
                    update recommendation_runs set status='STOPPED'
                    where profile_id=? and status not in ('STOPPED','COMPLETED')
                    """,
                    (profile_id,),
                )
                connection.execute(
                    """
                    insert into review_tasks(
                      review_id, run_id, profile_id, data_class, simulation_badge,
                      urgency, reason_codes_json, status, decision_json, created_at, completed_at
                    )
                    values (?, null, ?, ?, 1, 'URGENT', ?, 'OPEN', null, ?, null)
                    """,
                    (
                        review_id,
                        profile_id,
                        DataClass.SYNTHETIC_SAFETY_PROXY,
                        _json(["SERIOUS_ADVERSE_EVENT"]),
                        now,
                    ),
                )
        return {
            "case_id": case_id,
            "plan_stopped": serious,
            "review_id": review_id,
            "postcondition_success": True,
        }
