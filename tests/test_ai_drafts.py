import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from wellnessbox_rnd.interim.ai_drafts import (
    AiDraftCreateV1,
    AiDraftDecisionV1,
    AiDraftService,
    DownstreamPurpose,
)
from wellnessbox_rnd.interim.store import InterimStore

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


def _service(tmp_path) -> AiDraftService:
    store = InterimStore(tmp_path / "ai-drafts.sqlite3")
    store.migrate()
    return AiDraftService(store)


def _create(service: AiDraftService, key: str) -> dict[str, object]:
    return service.create(
        AiDraftCreateV1(
            record_type="safety_rule_candidate",
            model_identifier="draft-model-v1",
            prompt_version="prompt-v1",
            content={"ingredient": key, "action": "review"},
            rationale={"evidence_ids": [f"ev-{key}"]},
            idempotency_key=key,
        ),
        created_at=NOW,
    )


def test_draft_persists_complete_provenance_and_idempotency(tmp_path) -> None:
    service = _service(tmp_path)
    first = _create(service, "one")
    retry = _create(service, "one")
    assert first["draft_id"] == retry["draft_id"]
    assert retry["deduplicated"] is True
    assert first["generation_source"] == "ai_draft"
    assert first["review_status"] == "pending"
    assert first["reviewer_id"] is None
    assert first["reviewed_at"] is None
    assert first["edit_diff"] is None
    assert first["rejection_reason"] is None


@pytest.mark.parametrize("purpose", list(DownstreamPurpose))
@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_unapproved_draft_is_blocked_from_every_downstream(
    tmp_path, purpose: DownstreamPurpose, status: str
) -> None:
    service = _service(tmp_path)
    draft = _create(service, f"{purpose}-{status}")
    if status == "rejected":
        service.decide(
            draft_id=str(draft["draft_id"]),
            decision=AiDraftDecisionV1(
                review_status="rejected",
                reviewer_id="pharmacist-1",
                rejection_reason="근거가 부족함",
            ),
            reviewed_at=NOW + timedelta(minutes=1),
        )
    with pytest.raises(PermissionError, match="unapproved_ai_draft_blocked"):
        service.consume_approved(draft_ids=[str(draft["draft_id"])], purpose=purpose)


def test_approved_and_edited_drafts_are_consumable(tmp_path) -> None:
    service = _service(tmp_path)
    approved = _create(service, "approved")
    edited = _create(service, "edited")
    service.decide(
        draft_id=str(approved["draft_id"]),
        decision=AiDraftDecisionV1(review_status="approved", reviewer_id="pharmacist-1"),
        reviewed_at=NOW + timedelta(minutes=1),
    )
    edited_result = service.decide(
        draft_id=str(edited["draft_id"]),
        decision=AiDraftDecisionV1(
            review_status="approved_with_edits",
            reviewer_id="pharmacist-1",
            edited_content={"ingredient": "edited", "action": "allow"},
        ),
        reviewed_at=NOW + timedelta(minutes=2),
    )
    consumed = service.consume_approved(
        draft_ids=[str(approved["draft_id"]), str(edited["draft_id"])],
        purpose=DownstreamPurpose.KNOWLEDGE,
    )
    assert len(consumed) == 2
    assert edited_result["edit_diff"]["after"]["action"] == "allow"
    assert service.summary() == {
        "generated": 2,
        "reviewed": 2,
        "pending": 0,
        "approved": 1,
        "approved_with_edits": 1,
        "rejected": 0,
    }


def test_decision_is_single_use_and_reviewed_row_is_immutable(tmp_path) -> None:
    service = _service(tmp_path)
    draft = _create(service, "immutable")
    decision = AiDraftDecisionV1(review_status="approved", reviewer_id="pharmacist-1")
    service.decide(
        draft_id=str(draft["draft_id"]),
        decision=decision,
        reviewed_at=NOW + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="ai_draft_already_decided"):
        service.decide(
            draft_id=str(draft["draft_id"]),
            decision=decision,
            reviewed_at=NOW + timedelta(minutes=2),
        )
    with pytest.raises(sqlite3.IntegrityError, match="reviewed_ai_draft_immutable"):
        with service.store.transaction() as connection:
            connection.execute(
                "update ai_drafts set reviewer_id='other' where draft_id=?",
                (draft["draft_id"],),
            )
