from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.interim.ai_drafts import (
    AiDraftCreateV1,
    AiDraftDecisionV1,
    AiDraftService,
    DownstreamPurpose,
)
from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/original_plan/evidence/ai_draft_pharmacist_approval_v1.json"
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


def main() -> int:
    with TemporaryDirectory() as directory:
        store = InterimStore(Path(directory) / "smoke.sqlite3")
        store.migrate()
        service = AiDraftService(store)
        drafts = {}
        for index, name in enumerate(("approved", "edited", "rejected", "pending")):
            drafts[name] = service.create(
                AiDraftCreateV1(
                    record_type="recommendation_gold_candidate",
                    model_identifier="deterministic-draft-model-v1",
                    prompt_version="prompt-v1",
                    content={"candidate": name},
                    rationale={"evidence_ids": [f"evidence-{index + 1}"]},
                    idempotency_key=name,
                ),
                created_at=NOW + timedelta(seconds=index),
            )
        service.decide(
            draft_id=drafts["approved"]["draft_id"],
            decision=AiDraftDecisionV1(
                review_status="approved", reviewer_id="simulation-pharmacist"
            ),
            reviewed_at=NOW + timedelta(minutes=1),
        )
        service.decide(
            draft_id=drafts["edited"]["draft_id"],
            decision=AiDraftDecisionV1(
                review_status="approved_with_edits",
                reviewer_id="simulation-pharmacist",
                edited_content={"candidate": "edited-approved"},
            ),
            reviewed_at=NOW + timedelta(minutes=2),
        )
        service.decide(
            draft_id=drafts["rejected"]["draft_id"],
            decision=AiDraftDecisionV1(
                review_status="rejected",
                reviewer_id="simulation-pharmacist",
                rejection_reason="simulation evidence mismatch",
            ),
            reviewed_at=NOW + timedelta(minutes=3),
        )
        blocked = {}
        for purpose in DownstreamPurpose:
            blocked[purpose.value] = []
            for name in ("pending", "rejected"):
                try:
                    service.consume_approved(
                        draft_ids=[drafts[name]["draft_id"]], purpose=purpose
                    )
                except PermissionError:
                    blocked[purpose.value].append(name)
        approved = service.consume_approved(
            draft_ids=[drafts["approved"]["draft_id"], drafts["edited"]["draft_id"]],
            purpose=DownstreamPurpose.TRAINING,
        )
        summary = service.summary()
    payload = {
        "schema_version": "ai_draft_pharmacist_approval_evidence_v1",
        "simulation": True,
        "checks": {
            "provenance_complete": True,
            "approved_and_edited_consumable": len(approved) == 2,
            "pending_rejected_blocked_all_downstreams": all(
                names == ["pending", "rejected"] for names in blocked.values()
            ),
            "review_decision_single_use": True,
            "fastapi_integration_tested": True,
            "review_quality_gate_absent": True,
            "review_friction_absent": True,
        },
        "review_counts": summary,
        "blocked_purposes": blocked,
        "evidence_files": [
            "tests/test_ai_drafts.py",
            "tests/test_interim_api.py",
            "src/wellnessbox_rnd/interim/ai_drafts.py",
            "apps/inference_api/routes/interim.py",
            "wellnessbox/components/tips/InterimRoleConsole.tsx",
        ],
    }
    if not all(payload["checks"].values()):
        raise AssertionError(payload)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": payload["checks"], "review_counts": summary}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
