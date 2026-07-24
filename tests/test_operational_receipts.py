from __future__ import annotations

from datetime import UTC, datetime

from wellnessbox_rnd.governance.operational_receipts import database_counts
from wellnessbox_rnd.interim.ai_drafts import (
    AiDraftCreateV1,
    AiDraftDecisionV1,
    AiDraftService,
)
from wellnessbox_rnd.interim.store import InterimStore


def test_pharmacist_counter_changes_only_after_actual_decision(tmp_path) -> None:
    database = tmp_path / "operational.sqlite3"
    store = InterimStore(database)
    store.migrate()
    service = AiDraftService(store)
    before = database_counts(database)
    draft = service.create(
        AiDraftCreateV1(
            record_type="actual_recommendation_review",
            model_identifier="deterministic-draft-model-v1",
            prompt_version="actual-recommendation-review-v1",
            content={"plan_id": "plan-1"},
            rationale={"source_execution_id": "execution-1"},
            idempotency_key="actual-recommendation:execution-1",
        ),
        created_at=datetime(2026, 7, 24, tzinfo=UTC),
    )
    pending = database_counts(database)
    service.decide(
        draft_id=draft["draft_id"],
        decision=AiDraftDecisionV1(
            review_status="approved",
            reviewer_id="웰니스박스",
        ),
        reviewed_at=datetime(2026, 7, 24, 0, 1, tzinfo=UTC),
    )
    reviewed = database_counts(database)

    assert before["ai_drafts"] == 0
    assert pending["ai_drafts"] == 1
    assert pending["ai_drafts_reviewed"] == 0
    assert reviewed["ai_drafts_reviewed"] == 1
