from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wellnessbox_rnd.training.approved_draft_dataset import (
    build_approved_draft_dataset_manifest_v1,
    verify_manifest_is_approved_only,
)
from wellnessbox_rnd.training.candidate_promotion import (
    build_candidate_promotion_decision_v1,
    evaluate_safety_regression_v1,
)

ROOT = Path(__file__).resolve().parents[1]


def _row(draft_id: str, status: str, reviewer: str | None, reviewed_at: str | None):
    return {
        "draft_id": draft_id,
        "record_type": "counseling_note",
        "review_status": status,
        "reviewer_id": reviewer,
        "reviewed_at": reviewed_at,
        "model_identifier": "draft-model-v1",
        "prompt_version": "p1",
        "content_json": json.dumps({"text": draft_id}, ensure_ascii=False),
        "created_at": f"2026-07-27T00:00:0{draft_id[-1]}Z",
        "row_sha256": f"sha-{draft_id}",
    }


LEDGER_ROWS = [
    _row("d1", "approved", "권혁찬", "2026-07-27T01:00:00Z"),
    _row("d2", "approved_with_edits", "권혁찬", "2026-07-27T01:05:00Z"),
    _row("d3", "pending", None, None),
    _row("d4", "rejected", "권혁찬", "2026-07-27T01:10:00Z"),
    _row("d5", "approved", "웰니스박스", "2026-07-27T01:15:00Z"),
    _row("d6", "approved", "여형준", "2026-07-27T01:20:00Z"),
]


def _manifest():
    return build_approved_draft_dataset_manifest_v1(
        LEDGER_ROWS, database_path="etc/x.sqlite3", database_sha256="db-sha"
    )


def _report(safety: float, adverse: float, coverage: float = 90.0, action: float = 90.0):
    def metric(score: float, target: float, comparison: str):
        passed = score >= target if comparison == "min" else score <= target
        return {"score": score, "target": target, "comparison": comparison, "passed": passed}

    return {
        "case_count": 256,
        "summary": {
            "safety_reference_accuracy_pct": metric(safety, 95.0, "min"),
            "adverse_event_count_yearly": metric(adverse, 5.0, "max"),
            "recommendation_coverage_pct": metric(coverage, 80.0, "min"),
            "next_action_accuracy_pct": metric(action, 80.0, "min"),
        },
    }


class ApprovedDraftDatasetTest(unittest.TestCase):
    def test_only_human_approved_drafts_enter_the_manifest(self) -> None:
        manifest = _manifest()

        self.assertEqual(
            [item["draft_id"] for item in manifest["included_drafts"]], ["d1", "d2"]
        )

    def test_every_excluded_draft_records_why(self) -> None:
        manifest = _manifest()
        reasons = {item["draft_id"]: item["reason"] for item in manifest["excluded_drafts"]}

        self.assertEqual(reasons["d3"], "pending_review")
        self.assertEqual(reasons["d4"], "rejected_by_reviewer")
        self.assertEqual(reasons["d5"], "reviewed_by_owner_or_system_account")
        self.assertEqual(reasons["d6"], "reviewed_by_owner_or_system_account")

    def test_dataset_digest_changes_when_an_approved_draft_changes(self) -> None:
        first = _manifest()
        edited = [dict(row) for row in LEDGER_ROWS]
        edited[0]["content_json"] = json.dumps({"text": "edited"}, ensure_ascii=False)
        second = build_approved_draft_dataset_manifest_v1(
            edited, database_path="etc/x.sqlite3", database_sha256="db-sha"
        )

        self.assertNotEqual(first["dataset_sha256"], second["dataset_sha256"])

    def test_verifier_blocks_a_tampered_manifest(self) -> None:
        manifest = _manifest()
        manifest["included_drafts"].append(
            {"draft_id": "d3", "review_status": "pending", "reviewer_id": ""}
        )
        check = verify_manifest_is_approved_only(manifest)

        self.assertEqual(check["status"], "BLOCKED")
        self.assertIn("d3", check["violation_draft_ids"])

    def test_verifier_accepts_the_untouched_manifest(self) -> None:
        self.assertEqual(verify_manifest_is_approved_only(_manifest())["status"], "READY")


class SafetyRegressionGateTest(unittest.TestCase):
    def test_identical_reports_do_not_regress(self) -> None:
        verdict = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(96.0, 2.0))

        self.assertEqual(verdict["status"], "READY")
        self.assertFalse(verdict["safety_regressed"])

    def test_lower_safety_accuracy_is_a_regression(self) -> None:
        verdict = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(95.5, 2.0))

        self.assertTrue(verdict["safety_regressed"])
        self.assertIn("safety_reference_accuracy_pct", verdict["regressed_metrics"])

    def test_more_adverse_events_is_a_regression(self) -> None:
        verdict = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(96.0, 3.0))

        self.assertIn("adverse_event_count_yearly", verdict["regressed_metrics"])

    def test_metric_that_stops_passing_is_a_regression_even_within_tolerance(self) -> None:
        verdict = evaluate_safety_regression_v1(
            _report(95.0, 2.0), _report(94.9, 2.0), tolerance=1.0
        )

        self.assertIn("safety_reference_accuracy_pct", verdict["regressed_metrics"])

    def test_missing_metric_fails_closed(self) -> None:
        candidate = _report(96.0, 2.0)
        del candidate["summary"]["safety_reference_accuracy_pct"]
        verdict = evaluate_safety_regression_v1(_report(96.0, 2.0), candidate)

        self.assertTrue(verdict["safety_regressed"])

    def test_different_case_counts_are_rejected(self) -> None:
        candidate = _report(96.0, 2.0)
        candidate["case_count"] = 128

        with self.assertRaises(ValueError):
            evaluate_safety_regression_v1(_report(96.0, 2.0), candidate)


class PromotionDecisionTest(unittest.TestCase):
    def _decision(self, *, gate: str, regression: dict, current: str | None = None):
        return build_candidate_promotion_decision_v1(
            dataset_manifest=_manifest(),
            regression=regression,
            candidate_artifact_path="artifacts/models/candidate.json",
            current_artifact_path=current,
            decided_at="2026-07-27T02:00:00Z",
            decided_by="여형준",
            training_gate_status=gate,
        )

    def test_closed_gate_keeps_the_current_model(self) -> None:
        clean = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(96.0, 2.0))
        decision = self._decision(gate="no_go_keep_training_blocked", regression=clean)

        self.assertEqual(decision["decision"], "keep_current_model")
        self.assertIn("training_gate_not_open:no_go_keep_training_blocked", decision["blockers"])

    def test_safety_regression_keeps_the_current_model_even_with_an_open_gate(self) -> None:
        regressed = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(90.0, 2.0))
        decision = self._decision(gate="go", regression=regressed)

        self.assertEqual(decision["decision"], "keep_current_model")
        self.assertIn("safety_regression_detected", decision["blockers"])

    def test_open_gate_and_clean_safety_allow_replacement(self) -> None:
        clean = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(97.0, 1.0))
        decision = self._decision(gate="go", regression=clean)

        self.assertEqual(decision["decision"], "replace_with_candidate")
        self.assertEqual(decision["blockers"], [])

    def test_rollback_records_the_artifact_to_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            current = Path(temp) / "current.json"
            current.write_text('{"model": "current"}', encoding="utf-8")
            clean = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(96.0, 2.0))
            decision = self._decision(gate="go", regression=clean, current=str(current))

        self.assertEqual(decision["rollback"]["restore_artifact_path"], str(current))
        self.assertEqual(len(decision["rollback"]["restore_artifact_sha256"]), 64)

    def test_an_unnamed_decider_is_rejected(self) -> None:
        clean = evaluate_safety_regression_v1(_report(96.0, 2.0), _report(96.0, 2.0))

        with self.assertRaises(ValueError):
            build_candidate_promotion_decision_v1(
                dataset_manifest=_manifest(),
                regression=clean,
                candidate_artifact_path="artifacts/models/candidate.json",
                current_artifact_path=None,
                decided_at="2026-07-27T02:00:00Z",
                decided_by="   ",
                training_gate_status="go",
            )


class TrainingCommandGateTest(unittest.TestCase):
    def test_command_refuses_to_train_while_the_gate_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            manifest_path = temp_path / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest(), ensure_ascii=False), encoding="utf-8"
            )
            gate_path = temp_path / "gate.json"
            gate_path.write_text(
                json.dumps(
                    {
                        "gate_decision": {
                            "authorized_now": False,
                            "decision": "no_go_keep_training_blocked",
                            "failed_criteria": ["criterion_1"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            plan_path = temp_path / "plan.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/train_approved_draft_candidate.py",
                    "--dataset-manifest",
                    str(manifest_path),
                    "--gate-report",
                    str(gate_path),
                    "--plan-output",
                    str(plan_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            plan = json.loads(plan_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 2)
        self.assertFalse(plan["executed"])
        self.assertIn("training_gate_not_open:no_go_keep_training_blocked", plan["blockers"])
        self.assertEqual(plan["approved_draft_ids"], ["d1", "d2"])
        self.assertEqual(len(plan["config_sha256"]), 64)

    def test_missing_gate_report_also_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            manifest_path = temp_path / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest(), ensure_ascii=False), encoding="utf-8"
            )
            plan_path = temp_path / "plan.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/train_approved_draft_candidate.py",
                    "--dataset-manifest",
                    str(manifest_path),
                    "--gate-report",
                    str(temp_path / "absent.json"),
                    "--plan-output",
                    str(plan_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 2)


class CandidateEvalInjectionTest(unittest.TestCase):
    def test_runner_accepts_a_candidate_artifact_argument(self) -> None:
        from wellnessbox_rnd.evals.runner import run_eval

        with self.assertRaises(ValueError):
            run_eval(
                "data/frozen_eval/frozen_eval_v1.jsonl",
                candidate_artifact_path="artifacts/models/candidate.json",
            )

    def test_run_eval_cli_exposes_the_candidate_flags(self) -> None:
        source = (ROOT / "scripts/run_eval.py").read_text(encoding="utf-8")

        self.assertIn("--candidate-artifact", source)
        self.assertIn("--enable-learned-reranking", source)


if __name__ == "__main__":
    unittest.main()
