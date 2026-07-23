from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wellnessbox_rnd.interim.store import InterimStore


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("ai_draft_datetime_must_be_timezone_aware")
    return value.astimezone(UTC)


class DraftReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_WITH_EDITS = "approved_with_edits"
    REJECTED = "rejected"


class DownstreamPurpose(StrEnum):
    TRAINING = "training"
    EVALUATION = "evaluation"
    RECOMMENDATION = "recommendation"
    KNOWLEDGE = "knowledge"


class AiDraftCreateV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_type: str = Field(min_length=1, max_length=80)
    model_identifier: str = Field(min_length=1, max_length=200)
    prompt_version: str = Field(min_length=1, max_length=100)
    content: dict[str, Any]
    rationale: dict[str, Any]
    idempotency_key: str = Field(min_length=1, max_length=200)


class AiDraftDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_status: DraftReviewStatus
    reviewer_id: str = Field(min_length=1, max_length=200)
    edited_content: dict[str, Any] | None = None
    rejection_reason: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_decision(self) -> AiDraftDecisionV1:
        if self.review_status == DraftReviewStatus.PENDING:
            raise ValueError("draft_decision_pending_forbidden")
        if self.review_status == DraftReviewStatus.APPROVED_WITH_EDITS:
            if self.edited_content is None:
                raise ValueError("draft_edited_content_required")
        elif self.edited_content is not None:
            raise ValueError("draft_edited_content_forbidden")
        if self.review_status == DraftReviewStatus.REJECTED:
            if not self.rejection_reason:
                raise ValueError("draft_rejection_reason_required")
        elif self.rejection_reason is not None:
            raise ValueError("draft_rejection_reason_forbidden")
        return self


class AiDraftService:
    def __init__(self, store: InterimStore):
        self.store = store

    def create(self, draft: AiDraftCreateV1, *, created_at: datetime) -> dict[str, Any]:
        created = _utc(created_at)
        identity = {
            "record_type": draft.record_type,
            "model_identifier": draft.model_identifier,
            "prompt_version": draft.prompt_version,
            "idempotency_key": draft.idempotency_key,
        }
        draft_id = "draft_" + hashlib.sha256(_json(identity).encode()).hexdigest()[:24]
        row_hash = _sha(identity | {"content": draft.content, "rationale": draft.rationale})
        with self.store.transaction(immediate=True) as connection:
            existing = connection.execute(
                "select * from ai_drafts where draft_id=?", (draft_id,)
            ).fetchone()
            if existing is not None:
                if str(existing["row_sha256"]) != row_hash:
                    raise ValueError("ai_draft_idempotency_conflict")
                return self._row(existing) | {"deduplicated": True}
            connection.execute(
                """
                insert into ai_drafts values (
                  ?, ?, 'ai_draft', ?, ?, ?, ?, 'pending',
                  null, null, null, null, ?, ?
                )
                """,
                (
                    draft_id,
                    draft.record_type,
                    draft.model_identifier,
                    draft.prompt_version,
                    _json(draft.content),
                    _json(draft.rationale),
                    created.isoformat(),
                    row_hash,
                ),
            )
            row = connection.execute(
                "select * from ai_drafts where draft_id=?", (draft_id,)
            ).fetchone()
        return self._row(row) | {"deduplicated": False}

    def decide(
        self,
        *,
        draft_id: str,
        decision: AiDraftDecisionV1,
        reviewed_at: datetime,
    ) -> dict[str, Any]:
        reviewed = _utc(reviewed_at)
        with self.store.transaction(immediate=True) as connection:
            row = connection.execute(
                "select * from ai_drafts where draft_id=?", (draft_id,)
            ).fetchone()
            if row is None:
                raise ValueError("ai_draft_missing")
            if str(row["review_status"]) != DraftReviewStatus.PENDING:
                raise ValueError("ai_draft_already_decided")
            content = json.loads(str(row["content_json"]))
            edit_diff = None
            if decision.review_status == DraftReviewStatus.APPROVED_WITH_EDITS:
                edit_diff = {"before": content, "after": decision.edited_content}
                content = decision.edited_content
            connection.execute(
                """
                update ai_drafts set content_json=?, review_status=?, reviewer_id=?,
                  reviewed_at=?, edit_diff_json=?, rejection_reason=?
                where draft_id=? and review_status='pending'
                """,
                (
                    _json(content),
                    decision.review_status.value,
                    decision.reviewer_id,
                    reviewed.isoformat(),
                    _json(edit_diff) if edit_diff is not None else None,
                    decision.rejection_reason,
                    draft_id,
                ),
            )
            decided = connection.execute(
                "select * from ai_drafts where draft_id=?", (draft_id,)
            ).fetchone()
        return self._row(decided)

    def queue(self) -> list[dict[str, Any]]:
        return [
            self._row(row)
            for row in self.store.rows(
                "select * from ai_drafts where review_status='pending' order by created_at"
            )
        ]

    def consume_approved(
        self, *, draft_ids: list[str], purpose: DownstreamPurpose
    ) -> list[dict[str, Any]]:
        del purpose
        if not draft_ids:
            return []
        placeholders = ",".join("?" for _ in draft_ids)
        rows = self.store.rows(
            f"select * from ai_drafts where draft_id in ({placeholders})", tuple(draft_ids)
        )
        found = {str(row["draft_id"]): row for row in rows}
        for draft_id in draft_ids:
            row = found.get(draft_id)
            if row is None:
                raise ValueError(f"ai_draft_missing:{draft_id}")
            if str(row["review_status"]) not in {
                DraftReviewStatus.APPROVED,
                DraftReviewStatus.APPROVED_WITH_EDITS,
            }:
                raise PermissionError(f"unapproved_ai_draft_blocked:{draft_id}")
        return [self._row(found[draft_id]) for draft_id in draft_ids]

    def summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in DraftReviewStatus}
        for row in self.store.rows(
            "select review_status, count(*) as count from ai_drafts group by review_status"
        ):
            counts[str(row["review_status"])] = int(row["count"])
        return {
            "generated": sum(counts.values()),
            "reviewed": sum(value for key, value in counts.items() if key != "pending"),
            **counts,
        }

    @staticmethod
    def _row(row) -> dict[str, Any]:
        result = dict(row)
        result["content"] = json.loads(result.pop("content_json"))
        result["rationale"] = json.loads(result.pop("rationale_json"))
        edit_diff_json = result.pop("edit_diff_json")
        result["edit_diff"] = json.loads(edit_diff_json) if edit_diff_json is not None else None
        return result


__all__ = [
    "AiDraftCreateV1",
    "AiDraftDecisionV1",
    "AiDraftService",
    "DownstreamPurpose",
    "DraftReviewStatus",
]
