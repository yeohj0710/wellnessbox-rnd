from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

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
            second = result["next_draft"]
            console.decide_draft(
                database_path=str(database),
                draft_id=second["draft_id"],
                reviewer_id="pharmacist-1",
                decision="approved",
            )
            cycle_path = root / "session/ai_draft_downstream_cycle_v1.json"
            cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
            self.assertEqual(cycle["training_consumed_count"], 2)
            self.assertEqual(cycle["evaluation_consumed_count"], 2)
            self.assertEqual(console.state["steps"]["H-003"]["status"], "completed")

    def test_external_validation_rejects_arbitrary_file_in_production_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fake_root = Path(temp) / "project"
            fake_root.mkdir()
            console = FinalSessionConsole(fake_root)
            invalid = Path(temp) / "not-an-external-result.json"
            invalid.write_text('{"status":"PASS"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                console.register_external_validation(str(invalid))

    def test_operations_require_pass_status_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            console.record_operations(
                "operator",
                {
                    key: {"status": "FAIL", "evidence": "probe failed"}
                    for key in (
                        "rnd_api",
                        "wellnessbox_environment",
                        "health_check",
                        "browser_roundtrip",
                    )
                },
            )
            self.assertEqual(console.state["steps"]["H-007"]["status"], "deferred")

    def test_operations_keep_previously_registered_requirement_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            console = FinalSessionConsole(ROOT, state_root=temp_path / "session")
            requirement_id = console._stage_gap_ids()[0]
            evidence = temp_path / "requirement.json"
            evidence.write_text(
                json.dumps({"requirement_id": requirement_id, "status": "PASS"}),
                encoding="utf-8",
            )
            console.record_operations(
                "operator",
                {"requirement_evidence": {requirement_id: str(evidence)}},
            )
            console.record_operations("operator", {})
            registered = console.state["steps"]["H-007"][
                "registered_requirement_evidence"
            ]
            self.assertIn(requirement_id, registered)

    def test_console_html_has_automatic_draft_queue_and_structured_operations(self) -> None:
        html = (ROOT / "scripts/run_final_session_console.py").read_text(encoding="utf-8")
        self.assertIn("data.next_draft", html)
        self.assertIn("draftReviewerId", html)
        self.assertIn('type="checkbox" id="check-${id}"', html)
        self.assertNotIn("운영 확인 JSON", html)

    def test_finalize_registers_policy_before_resigning_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            console = FinalSessionConsole(root)
            for step in console.state["steps"].values():
                step["status"] = "completed"
            console.state["steps"]["H-006"].update(
                {
                    "key_path": "key.pem",
                    "issuer_id": "issuer",
                    "validation_receipt_path": "v.json",
                    "independent_review_receipt_path": "r.json",
                    "public_key_ed25519_base64": "key",
                }
            )
            events: list[str] = []

            def commit(_: list[Path], message: str) -> None:
                events.append(message)

            def sign(**_: object) -> dict[str, str]:
                self.assertIn("docs: register final receipt trust policy", events)
                events.append("signed")
                return {
                    "validation_receipt_path": str(root / "v.json"),
                    "independent_review_receipt_path": str(root / "r.json"),
                }

            with (
                patch.object(console, "_register_final_signoffs", return_value=[]),
                patch.object(
                    console, "_register_receipt_policy", return_value=root / "policy.json"
                ),
                patch.object(console, "_git_commit", side_effect=commit),
                patch.object(console, "sign_receipts", side_effect=sign),
                patch.object(console, "run_final_audit", return_value={"status": "READY"}),
            ):
                result = console.finalize_and_audit()
            self.assertTrue(result["finalized"])
            self.assertLess(
                events.index("docs: register final receipt trust policy"), events.index("signed")
            )

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
