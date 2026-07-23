from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from wellnessbox_rnd.governance.final_session_console import FinalSessionConsole, run_rehearsal
from wellnessbox_rnd.interim.ai_drafts import AiDraftCreateV1, AiDraftService
from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]


class FinalSessionConsoleTest(unittest.TestCase):
    def test_console_persists_policy_reviews_and_deferrals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            console.confirm_alignment("owner-1")
            for rule in console.policy_rules():
                console.review_policy_rule(rule["rule_id"], "pharmacist-1", "approved")
            console.register_external_validation(None)
            restored = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            self.assertEqual(restored.state["steps"]["H-001"]["status"], "completed")
            self.assertEqual(restored.state["steps"]["H-002"]["status"], "completed")
            self.assertEqual(restored.state["steps"]["H-005"]["status"], "deferred")

    def test_console_decides_real_ai_draft_and_returns_next(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "drafts.sqlite3"
            store = InterimStore(database)
            store.migrate()
            service = AiDraftService(store)
            for index in range(2):
                service.create(
                    AiDraftCreateV1(
                        record_type="counseling",
                        model_identifier="simulation-model",
                        prompt_version="v1",
                        content={"text": f"draft-{index}"},
                        rationale={"basis": "simulation"},
                        idempotency_key=f"draft-{index}",
                    ),
                    created_at=datetime.now(UTC),
                )
            console = FinalSessionConsole(ROOT, state_root=root / "session")
            first = console.draft_queue(str(database))["items"][0]
            result = console.decide_draft(
                database_path=str(database),
                draft_id=first["draft_id"],
                reviewer_id="pharmacist-1",
                decision="approved",
            )
            self.assertIsNotNone(result["next_draft"])
            self.assertEqual(result["summary"]["approved"], 1)
            self.assertEqual(console.state["steps"]["H-003"]["status"], "pending")

    def test_rehearsal_completes_all_steps_without_production_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            production_state = ROOT / "data/original_plan/final_session/session_state_v1.json"
            before = production_state.read_bytes() if production_state.exists() else None
            result = run_rehearsal(ROOT, Path(temp) / "rehearsal")
            after = production_state.read_bytes() if production_state.exists() else None
            self.assertEqual(result["data_class"], "SIMULATION")
            self.assertEqual(result["audit"]["status"], "READY")
            self.assertTrue(all(item["status"] == "completed" for item in result["steps"].values()))
            self.assertFalse(result["production_paths_touched"])
            self.assertEqual(after, before)
            saved = json.loads((Path(temp) / "rehearsal/rehearsal_result_v1.json").read_text())
            self.assertTrue(saved["audit"]["goal_complete"])


if __name__ == "__main__":
    unittest.main()
