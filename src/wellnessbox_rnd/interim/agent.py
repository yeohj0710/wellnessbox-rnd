from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from wellnessbox_rnd.interim.connectors import ingest_device_session
from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.safety import evaluate_safety
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.interim.workflow_contract import (
    CLOSED_LOOP_ALLOWED_OPERATIONS_V1,
    CLOSED_LOOP_TRANSITIONS_V1,
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
    "create_followup",
    "ingest_pro",
    "ingest_wearable",
    "escalate_pharmacist",
    "log_adverse_event",
)


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

    def move(self, run_id: str, target: AgentState) -> AgentState:
        row = self.store.rows("select state_after from agent_runs where run_id=?", (run_id,))
        if not row:
            raise ValueError("unknown_agent_run")
        current = AgentState(row[0][0])
        next_state = transition(current, target)
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
        if tool_name not in TOOL_NAMES:
            raise ValueError("unknown_agent_tool")
        run_rows = self.store.rows("select * from agent_runs where run_id=?", (run_id,))
        if not run_rows:
            raise ValueError("unknown_agent_run")
        run = run_rows[0]
        if run["status"] != "ACTIVE":
            raise ValueError("agent_run_not_active")
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
        result = self._dispatch(run_id, tool_name, safe_arguments, scopes)
        if not isinstance(result, dict) or result.get("postcondition_success") is False:
            raise RuntimeError("tool_postcondition_failed")
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
        return result

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
        if tool_name == "create_followup":
            if "followup:write" not in scopes:
                raise PermissionError("missing_followup_consent")
            followup_id = f"fu_{uuid4().hex}"
            due_at = datetime.now(UTC) + timedelta(days=int(arguments.get("days", 14)))
            with self.store.transaction() as connection:
                connection.execute(
                    "insert into followups values (?, ?, ?, ?, 'OPEN', ?)",
                    (
                        followup_id,
                        profile_id,
                        due_at.isoformat(),
                        _json(arguments.get("requested_data", [])),
                        datetime.now(UTC).isoformat(),
                    ),
                )
            return {"followup_id": followup_id, "postcondition_success": True}
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
        if tool_name == "escalate_pharmacist":
            review_id = f"review_{uuid4().hex}"
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    insert into review_tasks(
                      review_id, run_id, profile_id, data_class, simulation_badge,
                      urgency, reason_codes_json, status, decision_json, created_at, completed_at
                    )
                    values (?, null, ?, ?, 1, ?, ?, 'OPEN', null, ?, null)
                    """,
                    (
                        review_id,
                        profile_id or None,
                        DataClass.PROXY_GOLD_SIMULATION,
                        arguments.get("urgency", "ROUTINE"),
                        _json(arguments.get("reason_codes", [])),
                        datetime.now(UTC).isoformat(),
                    ),
                )
            return {"review_id": review_id, "simulation_badge": True, "postcondition_success": True}
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
