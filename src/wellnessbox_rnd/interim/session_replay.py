from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from wellnessbox_rnd.interim.data_lake import (
    ExecutionNotFoundError,
    _canonical_json,
    _sha256,
    replay_response_payload,
)
from wellnessbox_rnd.interim.execution_identity import (
    DatasetIdentityRecord,
    ExecutionIdentityRecord,
    build_current_deterministic_identity,
    identity_version_payload,
    identity_version_sha256,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)

ReplayStatus = Literal["MATCH", "MISMATCH", "VERSION_MISMATCH"]
_EXECUTION_ID = re.compile(r"^exec_[a-f0-9]{32}$")
_MAX_MISMATCH_FIELDS = 20


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SavedSessionItem(_StrictModel):
    execution_id: str
    created_at: str
    execution_status: str
    replay_available: bool
    last_replay_status: ReplayStatus | None
    last_replayed_at: str | None


class SavedSessionSummary(_StrictModel):
    total_saved_sessions: int
    replayable_sessions: int
    unavailable_sessions: int
    replay_run_count: int
    items: list[SavedSessionItem]


class SessionReplayResult(_StrictModel):
    replay_id: str
    execution_id: str
    status: ReplayStatus
    input_match: bool
    version_match: bool
    output_match: bool | None
    expected_output_sha256: str
    actual_output_sha256: str | None
    stored_model_id: str
    stored_engine_version: str
    active_model_id: str
    active_engine_version: str
    mismatch_fields: list[str]
    replayed_at: str


class SessionReplayError(RuntimeError):
    pass


class SessionReplayUnavailableError(SessionReplayError):
    pass


class SessionReplayIntegrityError(SessionReplayError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identity_from_row(row: sqlite3.Row) -> ExecutionIdentityRecord:
    return ExecutionIdentityRecord(
        execution_id=str(row["execution_id"]),
        model_id=str(row["model_id"]),
        engine_version=str(row["engine_version"]),
        code_commit=str(row["code_commit"]),
        code_commit_source=str(row["code_commit_source"]),
        datasets=[
            DatasetIdentityRecord(**item)
            for item in json.loads(row["dataset_ids_json"])
        ],
        config=json.loads(row["config_json"]),
        config_sha256=str(row["config_sha256"]),
        created_at=str(row["identity_created_at"]),
    )


def _mismatch_fields(expected: object, actual: object, prefix: str = "") -> list[str]:
    if expected == actual:
        return []
    if isinstance(expected, dict) and isinstance(actual, dict):
        fields: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in expected or key not in actual:
                fields.append(path)
            else:
                fields.extend(_mismatch_fields(expected[key], actual[key], path))
            if len(fields) >= _MAX_MISMATCH_FIELDS:
                break
        return fields[:_MAX_MISMATCH_FIELDS]
    if isinstance(expected, list) and isinstance(actual, list):
        fields = []
        for index in range(max(len(expected), len(actual))):
            path = f"{prefix}[{index}]"
            if index >= len(expected) or index >= len(actual):
                fields.append(path)
            else:
                fields.extend(_mismatch_fields(expected[index], actual[index], path))
            if len(fields) >= _MAX_MISMATCH_FIELDS:
                break
        return fields[:_MAX_MISMATCH_FIELDS]
    return [prefix or "root"]


class SessionReplayLedger:
    def __init__(
        self,
        store: InterimStore,
        *,
        recommendation_runner: Callable[
            [RecommendationRequest], RecommendationResponse
        ] = recommend,
    ):
        self.store = store
        self.recommendation_runner = recommendation_runner

    def summary(self, *, limit: int = 20) -> SavedSessionSummary:
        if not 1 <= limit <= 100:
            raise ValueError("session_summary_limit_out_of_range")
        total = int(self.store.scalar("select count(*) from executions"))
        replayable = int(
            self.store.scalar("select count(*) from execution_replay_snapshots")
        )
        replay_runs = int(self.store.scalar("select count(*) from execution_replay_runs"))
        rows = self.store.rows(
            """
            select e.execution_id, e.created_at, e.status as execution_status,
                   case when snapshot.execution_id is null then 0 else 1 end
                     as replay_available,
                   (
                     select run.status from execution_replay_runs run
                     where run.execution_id=e.execution_id
                     order by run.created_at desc, run.rowid desc limit 1
                   ) as last_replay_status,
                   (
                     select run.created_at from execution_replay_runs run
                     where run.execution_id=e.execution_id
                     order by run.created_at desc, run.rowid desc limit 1
                   ) as last_replayed_at
            from executions e
            left join execution_replay_snapshots snapshot
              on snapshot.execution_id=e.execution_id
            order by e.created_at desc, e.rowid desc
            limit ?
            """,
            (limit,),
        )
        return SavedSessionSummary(
            total_saved_sessions=total,
            replayable_sessions=replayable,
            unavailable_sessions=total - replayable,
            replay_run_count=replay_runs,
            items=[
                SavedSessionItem(
                    execution_id=str(row["execution_id"]),
                    created_at=str(row["created_at"]),
                    execution_status=str(row["execution_status"]),
                    replay_available=bool(row["replay_available"]),
                    last_replay_status=row["last_replay_status"],
                    last_replayed_at=row["last_replayed_at"],
                )
                for row in rows
            ],
        )

    def replay(self, execution_id: str) -> SessionReplayResult:
        if not _EXECUTION_ID.fullmatch(execution_id):
            raise ValueError("invalid_execution_id")
        rows = self.store.rows(
            """
            select e.request_sha256 as execution_request_sha256,
                   snapshot.request_json, snapshot.request_sha256,
                   snapshot.expected_output_json, snapshot.expected_output_sha256,
                   identity.*, identity.created_at as identity_created_at
            from executions e
            left join execution_replay_snapshots snapshot
              on snapshot.execution_id=e.execution_id
            left join execution_identities identity
              on identity.execution_id=e.execution_id
            where e.execution_id=?
            """,
            (execution_id,),
        )
        if not rows:
            raise ExecutionNotFoundError(f"execution_not_found:{execution_id}")
        row = rows[0]
        if row["request_json"] is None:
            raise SessionReplayUnavailableError(
                f"session_replay_unavailable:{execution_id}"
            )
        if row["model_id"] is None:
            raise SessionReplayIntegrityError(
                f"execution_identity_missing:{execution_id}"
            )

        try:
            request_payload = json.loads(row["request_json"])
            expected_output = json.loads(row["expected_output_json"])
            request = RecommendationRequest.model_validate(request_payload)
        except (json.JSONDecodeError, ValueError) as error:
            raise SessionReplayIntegrityError(
                f"session_replay_snapshot_invalid:{execution_id}"
            ) from error
        request_sha256 = _sha256(request_payload)
        expected_output_sha256 = _sha256(expected_output)
        if (
            request_sha256 != str(row["request_sha256"])
            or request_sha256 != str(row["execution_request_sha256"])
            or expected_output_sha256 != str(row["expected_output_sha256"])
        ):
            raise SessionReplayIntegrityError(
                f"session_replay_snapshot_hash_mismatch:{execution_id}"
            )

        stored_identity = _identity_from_row(row)
        replayed_at = _now()
        active_identity = build_current_deterministic_identity(
            execution_id=execution_id,
            created_at=replayed_at,
        )
        stored_version = identity_version_payload(stored_identity)
        active_version = identity_version_payload(active_identity)
        code_identity_unresolved = any(
            identity.code_commit_source == "unresolved"
            or identity.code_commit == "unresolved"
            for identity in (stored_identity, active_identity)
        )
        version_mismatches = (
            ["code_commit"]
            if code_identity_unresolved
            else _mismatch_fields(stored_version, active_version)
        )
        if version_mismatches:
            return self._persist_result(
                execution_id=execution_id,
                status="VERSION_MISMATCH",
                expected_output_sha256=expected_output_sha256,
                actual_output_sha256=None,
                stored_identity=stored_identity,
                active_identity=active_identity,
                mismatch_fields=version_mismatches,
                replayed_at=replayed_at,
            )

        try:
            response = self.recommendation_runner(request)
        except Exception:
            self._persist_result(
                execution_id=execution_id,
                status="MISMATCH",
                expected_output_sha256=expected_output_sha256,
                actual_output_sha256=None,
                stored_identity=stored_identity,
                active_identity=active_identity,
                mismatch_fields=["recommendation_execution"],
                replayed_at=replayed_at,
            )
            raise
        actual_output = replay_response_payload(response)
        actual_output_sha256 = _sha256(actual_output)
        output_mismatches = _mismatch_fields(expected_output, actual_output)
        return self._persist_result(
            execution_id=execution_id,
            status="MATCH" if not output_mismatches else "MISMATCH",
            expected_output_sha256=expected_output_sha256,
            actual_output_sha256=actual_output_sha256,
            stored_identity=stored_identity,
            active_identity=active_identity,
            mismatch_fields=output_mismatches,
            replayed_at=replayed_at,
        )

    def _persist_result(
        self,
        *,
        execution_id: str,
        status: ReplayStatus,
        expected_output_sha256: str,
        actual_output_sha256: str | None,
        stored_identity: ExecutionIdentityRecord,
        active_identity: ExecutionIdentityRecord,
        mismatch_fields: list[str],
        replayed_at: str,
    ) -> SessionReplayResult:
        replay_id = f"replay_{uuid4().hex}"
        version_match = status != "VERSION_MISMATCH"
        output_match = None if not version_match else status == "MATCH"
        with self.store.transaction(immediate=True) as connection:
            connection.execute(
                """
                insert into execution_replay_runs(
                  replay_id, execution_id, status, input_match, version_match,
                  output_match, expected_output_sha256, actual_output_sha256,
                  mismatch_fields_json, stored_identity_sha256,
                  active_identity_sha256, created_at
                ) values (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    replay_id,
                    execution_id,
                    status,
                    int(version_match),
                    None if output_match is None else int(output_match),
                    expected_output_sha256,
                    actual_output_sha256,
                    _canonical_json(mismatch_fields[:_MAX_MISMATCH_FIELDS]),
                    identity_version_sha256(stored_identity),
                    identity_version_sha256(active_identity),
                    replayed_at,
                ),
            )
        return SessionReplayResult(
            replay_id=replay_id,
            execution_id=execution_id,
            status=status,
            input_match=True,
            version_match=version_match,
            output_match=output_match,
            expected_output_sha256=expected_output_sha256,
            actual_output_sha256=actual_output_sha256,
            stored_model_id=stored_identity.model_id,
            stored_engine_version=stored_identity.engine_version,
            active_model_id=active_identity.model_id,
            active_engine_version=active_identity.engine_version,
            mismatch_fields=mismatch_fields[:_MAX_MISMATCH_FIELDS],
            replayed_at=replayed_at,
        )


__all__ = [
    "SavedSessionItem",
    "SavedSessionSummary",
    "SessionReplayError",
    "SessionReplayIntegrityError",
    "SessionReplayLedger",
    "SessionReplayResult",
    "SessionReplayUnavailableError",
]
