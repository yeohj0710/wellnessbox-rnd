from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wellnessbox_rnd.governance.completion_wizard import (
    STEPS,
    VERIFIERS,
    next_pending_step,
    progress_summary,
    read_operational_counts,
    save_progress,
    step_belongs_to_this_session,
    training_gate_is_open,
    verify_answer_keys,
    verify_audit,
    verify_dataset,
    verify_draft_review,
    verify_preflight,
    verify_profiles,
    verify_safety_review,
    verify_step,
    verify_training,
)

ROOT = Path(__file__).resolve().parents[1]


def _fake_root(temp: str) -> Path:
    root = Path(temp)
    (root / "data/original_plan/final_session").mkdir(parents=True)
    (root / "etc/local_research_runtime").mkdir(parents=True)
    (root / "artifacts/reports").mkdir(parents=True)
    return root


def _write_state(root: Path, steps: dict) -> None:
    (root / "data/original_plan/final_session/session_state_v1.json").write_text(
        json.dumps({"steps": steps}, ensure_ascii=False), encoding="utf-8"
    )


def _write_ledger(root: Path, *, profiles: int, pending: int, reviewed: int) -> None:
    """Seed a ledger whose rows all belong to the current session."""
    database = root / "etc/local_research_runtime/interim.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "create table profile_snapshots (profile_id text, data_class text, created_at text)"
    )
    connection.execute("create table ai_drafts (review_status text, reviewed_at text)")
    connection.executemany(
        "insert into profile_snapshots values (?, 'INTERIM_RUNTIME_EVENT', '2026-07-30T09:00:00Z')",
        [(f"p{index}",) for index in range(profiles)],
    )
    connection.executemany(
        "insert into ai_drafts values (?, ?)",
        [("pending", None)] * pending + [("approved", "2026-07-30T09:00:00Z")] * reviewed,
    )
    connection.commit()
    connection.close()


def _write_ledger_at(
    root: Path, *, old_profiles: int, new_profiles: int, old_reviews: int = 0
) -> None:
    """Seed the ledger with rows on both sides of the 2026-07-30 session boundary."""
    database = root / "etc/local_research_runtime/interim.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "create table profile_snapshots (profile_id text, data_class text, created_at text)"
    )
    connection.execute("create table ai_drafts (review_status text, reviewed_at text)")
    connection.executemany(
        "insert into profile_snapshots values (?, 'INTERIM_RUNTIME_EVENT', '2026-07-24T00:00:00Z')",
        [(f"old{index}",) for index in range(old_profiles)],
    )
    connection.executemany(
        "insert into profile_snapshots values (?, 'INTERIM_RUNTIME_EVENT', '2026-07-30T09:00:00Z')",
        [(f"new{index}",) for index in range(new_profiles)],
    )
    connection.executemany(
        "insert into ai_drafts values ('approved', '2026-07-24T00:00:00Z')",
        [()] * old_reviews,
    )
    connection.commit()
    connection.close()


def _write_gate(root: Path, *, authorized: bool) -> None:
    (root / "artifacts/reports/training_readiness_gate_v2.json").write_text(
        json.dumps({"gate_decision": {"authorized_now": authorized}}), encoding="utf-8"
    )


def _write_answer_key_seals(root: Path, *, audited: bool = True) -> None:
    directory = root / "data/original_plan/kpi/seals"
    directory.mkdir(parents=True, exist_ok=True)
    for indicator_id in ("KPI-1", "KPI-3", "KPI-4", "KPI-5"):
        slug = indicator_id.lower().replace("-", "")
        payload = {
            "indicator_id": indicator_id,
            "case_count": 100,
            "meets_minimum_sample": True,
            "provenance": {
                "integrity_audit": {
                    "indicator_id": indicator_id,
                    "verdict": "PASS" if audited else "FAIL",
                }
            },
        }
        (directory / f"{slug}_reference_seal_v1.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )


class StepCatalogueTest(unittest.TestCase):
    def test_every_step_has_a_verifier(self) -> None:
        self.assertEqual({step.step_id for step in STEPS}, set(VERIFIERS))

    def test_human_steps_never_run_a_command(self) -> None:
        for step in STEPS:
            if step.kind == "human":
                with self.subTest(step=step.step_id):
                    self.assertIsNone(step.command)

    def test_the_order_puts_profiles_before_draft_review(self) -> None:
        order = [step.step_id for step in STEPS]

        self.assertLess(order.index("H-007"), order.index("H-003"))
        self.assertLess(order.index("H-003"), order.index("DATASET"))
        self.assertLess(order.index("H-005"), order.index("H-006"))
        self.assertEqual(order[-1], "AUDIT")

    def test_the_five_human_signoff_steps_are_all_present(self) -> None:
        human = {step.step_id for step in STEPS if step.kind == "human"}

        for required in ("H-002", "H-003", "H-004", "H-005", "H-006", "H-007"):
            with self.subTest(step=required):
                self.assertIn(required, human)


class ProfileVerificationTest(unittest.TestCase):
    def test_fewer_than_five_profiles_is_not_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger(root, profiles=3, pending=0, reviewed=0)
            result = verify_profiles(root, {})

        self.assertEqual(result.verdict, "todo")
        self.assertIn("3/5", result.detail)

    def test_five_distinct_profiles_finishes_the_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger(root, profiles=5, pending=0, reviewed=0)
            result = verify_profiles(root, {})

        self.assertEqual(result.verdict, "done")

    def test_a_missing_database_blocks_rather_than_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = verify_profiles(_fake_root(temp), {})

        self.assertEqual(result.verdict, "blocked")

    def test_counts_are_read_without_writing_to_the_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger(root, profiles=2, pending=1, reviewed=4)
            database = root / "etc/local_research_runtime/interim.sqlite3"
            before = database.read_bytes()
            counts = read_operational_counts(root)

            self.assertEqual(counts["distinct_actual_profiles"], 2)
            self.assertEqual(counts["pending_drafts"], 1)
            self.assertEqual(counts["reviewed_drafts"], 4)
            self.assertEqual(database.read_bytes(), before)


class DraftReviewVerificationTest(unittest.TestCase):
    def test_pending_drafts_block_the_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger(root, profiles=5, pending=2, reviewed=1)
            result = verify_draft_review(root, {})

        self.assertEqual(result.verdict, "todo")
        self.assertIn("pending_drafts_remain", result.missing)

    def test_an_empty_queue_with_no_reviews_is_not_treated_as_finished(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger(root, profiles=5, pending=0, reviewed=0)
            result = verify_draft_review(root, {})

        self.assertEqual(result.verdict, "todo")
        self.assertIn("no_drafts_reviewed_this_session", result.missing)

    def test_all_reviewed_finishes_the_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger(root, profiles=5, pending=0, reviewed=6)
            result = verify_draft_review(root, {})

        self.assertEqual(result.verdict, "done")


class HumanStepVerificationTest(unittest.TestCase):
    def test_a_step_the_person_has_not_saved_is_not_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_state(root, {"H-002": {"status": "pending"}})
            result = verify_step("H-002", root, {})

        self.assertEqual(result.verdict, "todo")

    def test_a_saved_step_is_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_state(root, {"H-004": {"status": "completed"}})
            result = verify_step("H-004", root, {})

        self.assertEqual(result.verdict, "done")

    def test_a_candidate_safety_review_reports_the_year3_obligation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_state(
                root,
                {
                    "H-005": {
                        "status": "completed",
                        "review_character": "pharmacist_candidate_preliminary_safety_review",
                        "requires_licensed_reconfirmation": True,
                    }
                },
            )
            result = verify_safety_review(root, {})

        self.assertEqual(result.verdict, "done")
        self.assertIn("3차년도", result.detail)

    def test_missing_state_file_reads_as_not_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = verify_step("H-006", _fake_root(temp), {})

        self.assertEqual(result.verdict, "todo")


class GatedStepTest(unittest.TestCase):
    def test_a_closed_gate_skips_training_instead_of_failing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_gate(root, authorized=False)
            result = verify_training(root, {})

        self.assertEqual(result.verdict, "skipped_gate_closed")
        self.assertTrue(result.ok)

    def test_a_missing_gate_report_also_skips(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(training_gate_is_open(_fake_root(temp)))

    def test_an_open_gate_requires_the_training_to_have_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_gate(root, authorized=True)

            self.assertEqual(verify_training(root, {}).verdict, "todo")
            self.assertEqual(
                verify_training(root, {"training_plan": {"executed": True}}).verdict, "done"
            )


class AutoStepVerificationTest(unittest.TestCase):
    def test_a_blocked_preflight_is_reported_with_its_blockers(self) -> None:
        artifacts = {"preflight": {"status": "BLOCKED", "blockers": [{"id": "H005_FORM"}]}}
        result = verify_preflight(ROOT, artifacts)

        self.assertEqual(result.verdict, "blocked")
        self.assertIn("H005_FORM", result.missing)

    def test_a_ready_preflight_passes(self) -> None:
        result = verify_preflight(ROOT, {"preflight": {"status": "READY", "blockers": []}})

        self.assertEqual(result.verdict, "done")

    def test_a_failed_dataset_check_blocks(self) -> None:
        result = verify_dataset(ROOT, {"dataset_check": {"status": "BLOCKED"}})

        self.assertEqual(result.verdict, "blocked")

    def test_a_blocked_audit_is_not_finished(self) -> None:
        artifacts = {"audit": {"audit": {"status": "BLOCKED", "blockers": [{"id": "X"}]}}}

        self.assertEqual(verify_audit(ROOT, artifacts).verdict, "blocked")

    def test_a_ready_audit_finishes(self) -> None:
        artifacts = {"audit": {"audit": {"status": "READY", "goal_complete": True}}}

        self.assertEqual(verify_audit(ROOT, artifacts).verdict, "done")

    def test_answer_keys_block_when_the_integrity_audit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_answer_key_seals(root)
            report = {
                "status": "BLOCKED",
                "completion_status": "BLOCKED",
                "completion_blockers": ["KPI-1"],
                "indicators": [
                    {"indicator_id": "KPI-1", "verdict": "FAIL"},
                    *[
                        {"indicator_id": indicator_id, "verdict": "PASS"}
                        for indicator_id in ("KPI-3", "KPI-4", "KPI-5")
                    ],
                ],
            }
            with patch(
                "wellnessbox_rnd.governance.completion_wizard.audit_repository",
                return_value=report,
            ):
                result = verify_answer_keys(root, {})

        self.assertEqual(result.verdict, "blocked")
        self.assertIn("KPI-1", result.missing)

    def test_answer_keys_require_current_and_recorded_audit_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_answer_key_seals(root)
            report = {
                "status": "READY",
                "completion_status": "READY",
                "completion_blockers": [],
                "indicators": [
                    {"indicator_id": indicator_id, "verdict": "PASS"}
                    for indicator_id in ("KPI-1", "KPI-3", "KPI-4", "KPI-5")
                ],
            }
            with patch(
                "wellnessbox_rnd.governance.completion_wizard.audit_repository",
                return_value=report,
            ):
                result = verify_answer_keys(root, {})

        self.assertEqual(result.verdict, "done")

    def test_answer_keys_block_when_workbench_or_seal_completion_is_pending(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_answer_key_seals(root)
            report = {
                "status": "READY",
                "completion_status": "BLOCKED",
                "completion_blockers": ["KPI-5"],
                "indicators": [
                    {"indicator_id": indicator_id, "verdict": "PASS"}
                    for indicator_id in ("KPI-1", "KPI-3", "KPI-4", "KPI-5")
                ],
            }
            with patch(
                "wellnessbox_rnd.governance.completion_wizard.audit_repository",
                return_value=report,
            ):
                result = verify_answer_keys(root, {})

        self.assertEqual(result.verdict, "blocked")
        self.assertIn("KPI-5", result.missing)


class ResumeTest(unittest.TestCase):
    def _results(self, finished: list[str]):
        return {
            step.step_id: verify_step("AUDIT", ROOT, {"audit": {"audit": {
                "status": "READY", "goal_complete": True}}})
            for step in STEPS
            if step.step_id in finished
        }

    def test_the_next_step_is_the_first_unfinished_one(self) -> None:
        results = self._results(["PREFLIGHT", "SERVERS"])
        step = next_pending_step(results)

        self.assertIsNotNone(step)
        self.assertEqual(step.step_id, "H-007")

    def test_no_next_step_when_everything_is_finished(self) -> None:
        results = self._results([step.step_id for step in STEPS])

        self.assertIsNone(next_pending_step(results))

    def test_progress_is_written_where_the_preflight_does_not_watch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            summary = progress_summary({})
            path = save_progress(root, summary)

            watched = (root / "data/original_plan/final_session").resolve()

            self.assertTrue(path.is_file())
            self.assertNotEqual(path.resolve().parent, watched)
            self.assertFalse(path.resolve().is_relative_to(watched))

    def test_summary_counts_skipped_gate_steps_as_finished(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_gate(root, authorized=False)
            summary = progress_summary({"TRAIN": verify_training(root, {})})

        row = next(item for item in summary["steps"] if item["step_id"] == "TRAIN")
        self.assertEqual(row["verdict"], "skipped_gate_closed")
        self.assertEqual(summary["finished_steps"], 1)


class SessionBoundaryTest(unittest.TestCase):
    """A completion stored by an earlier session must not count as today's work."""

    SESSION_START = "2026-07-30T00:00:00Z"

    def test_a_step_saved_before_the_session_started_is_not_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_state(
                root,
                {"H-002": {"status": "completed", "updated_at": "2026-07-23T04:13:35Z"}},
            )
            result = verify_step(
                "H-002", root, {"session_started_at": self.SESSION_START}
            )

        self.assertEqual(result.verdict, "todo")
        self.assertIn("H-002_completed_in_a_previous_session", result.missing)

    def test_a_step_saved_after_the_session_started_is_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_state(
                root,
                {"H-002": {"status": "completed", "updated_at": "2026-07-30T09:00:00Z"}},
            )
            result = verify_step(
                "H-002", root, {"session_started_at": self.SESSION_START}
            )

        self.assertEqual(result.verdict, "done")

    def test_a_step_without_a_timestamp_is_not_counted(self) -> None:
        self.assertFalse(
            step_belongs_to_this_session({"status": "completed"}, self.SESSION_START)
        )

    def test_profiles_from_an_earlier_session_are_reported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger_at(root, old_profiles=5, new_profiles=1)
            result = verify_profiles(root, {"session_started_at": self.SESSION_START})

        self.assertEqual(result.verdict, "todo")
        self.assertIn("1/5", result.detail)
        self.assertIn("이전 세션 프로필 5건", result.detail)

    def test_five_fresh_profiles_finish_the_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger_at(root, old_profiles=2, new_profiles=5)
            result = verify_profiles(root, {"session_started_at": self.SESSION_START})

        self.assertEqual(result.verdict, "done")

    def test_drafts_reviewed_in_an_earlier_session_do_not_finish_the_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_ledger_at(root, old_profiles=5, new_profiles=0, old_reviews=7)
            result = verify_draft_review(root, {"session_started_at": self.SESSION_START})

        self.assertEqual(result.verdict, "todo")
        self.assertIn("no_drafts_reviewed_this_session", result.missing)

    def test_an_h005_record_without_a_qualification_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = _fake_root(temp)
            _write_state(
                root,
                {"H-005": {"status": "completed", "updated_at": "2026-07-30T09:00:00Z"}},
            )
            result = verify_safety_review(root, {"session_started_at": self.SESSION_START})

        self.assertEqual(result.verdict, "todo")
        self.assertIn("h005_record_predates_the_candidate_model", result.missing)


if __name__ == "__main__":
    unittest.main()
