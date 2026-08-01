from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import scripts.run_answer_key_workbench as workbench_cli
from wellnessbox_rnd.evals.answer_key_drafters import (
    DRAFT_SOURCE,
    DRAFTERS,
    draft_cases,
    draft_kpi1_cases,
)
from wellnessbox_rnd.evals.answer_key_workbench import (
    CaseDraft,
    Decision,
    Workbench,
    adjudicated_answer_key,
    assert_source_is_independent,
    build_drafts,
    build_provenance,
    build_seal_disposal_record,
    decide,
    discard_seal_with_audit_trail,
    load_workbench,
    save_workbench,
    summarise_adjudication,
)

ROOT = Path(__file__).resolve().parents[1]


def _draft(case_id="c1", answer=None):
    return CaseDraft(
        case_id=case_id,
        prompt="목표 sleep_support",
        draft_answer=answer or ["magnesium", "l_theanine"],
        draft_source=DRAFT_SOURCE,
        drafting_agent="codex",
        blinded_from=["engine/policy.json"],
    )


def _bench(count=3):
    return Workbench("KPI-1", [_draft(f"c{index}") for index in range(count)], {})


class DraftSourceIndependenceTest(unittest.TestCase):
    """The thing being measured may not write its own answer key."""

    def test_the_recommendation_engine_may_not_draft(self) -> None:
        for source in (
            "recommendation_engine",
            "wellnessbox_rnd.orchestration.recommendation_service",
            "ENGINE_OUTPUT",
            "derived from system_under_test",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                assert_source_is_independent(source)

    def test_an_empty_source_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_source_is_independent("   ")

    def test_an_independent_knowledge_source_is_allowed(self) -> None:
        assert_source_is_independent(DRAFT_SOURCE)
        assert_source_is_independent("literature_review_by_reviewer")

    def test_build_drafts_refuses_an_engine_source(self) -> None:
        with self.assertRaises(ValueError):
            build_drafts(
                indicator_id="KPI-1",
                cases=[{"case_id": "c1", "draft_answer": ["a"]}],
                draft_source="recommendation_engine",
            )

    def test_drafts_record_that_no_engine_output_was_consulted(self) -> None:
        packaged = build_drafts(
            indicator_id="KPI-1",
            cases=[{"case_id": "c1", "draft_answer": ["a"]}],
            draft_source=DRAFT_SOURCE,
            drafting_agent="codex",
            blinded_from=["data/rules/safety_rules.json"],
        )

        self.assertFalse(packaged["engine_output_consulted"])
        self.assertEqual(packaged["draft_source"], DRAFT_SOURCE)
        self.assertEqual(packaged["drafting_agent"], "codex")
        self.assertEqual(
            packaged["blinded_from"],
            ["data/rules/safety_rules.json"],
        )
        self.assertEqual(packaged["drafts"][0]["drafting_agent"], "codex")

    def test_an_empty_draft_answer_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_drafts(
                indicator_id="KPI-1",
                cases=[{"case_id": "c1", "draft_answer": []}],
                draft_source=DRAFT_SOURCE,
            )


class DecisionTest(unittest.TestCase):
    def test_keeping_the_draft_records_an_acceptance(self) -> None:
        draft = _draft()
        decision = decide(
            draft=draft, final_answer=list(draft.draft_answer), decided_by="권혁찬"
        )

        self.assertEqual(decision.action, "accepted")

    def test_changing_the_draft_records_an_edit(self) -> None:
        decision = decide(draft=_draft(), final_answer=["magnesium"], decided_by="권혁찬")

        self.assertEqual(decision.action, "edited")

    def test_reordering_alone_is_still_an_acceptance(self) -> None:
        decision = decide(
            draft=_draft(), final_answer=["l_theanine", "magnesium"], decided_by="권혁찬"
        )

        self.assertEqual(decision.action, "accepted")

    def test_a_rejection_drops_the_case(self) -> None:
        decision = decide(draft=_draft(), final_answer=None, decided_by="권혁찬", note="부적절")

        self.assertEqual(decision.action, "rejected")
        self.assertEqual(decision.final_answer, [])

    def test_an_unnamed_decider_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decide(draft=_draft(), final_answer=["a"], decided_by="  ")

    def test_an_empty_final_answer_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decide(draft=_draft(), final_answer=[], decided_by="권혁찬")

    def test_review_duration_and_mode_are_recorded(self) -> None:
        decision = decide(
            draft=_draft(),
            final_answer=["magnesium"],
            decided_by="권혁찬",
            review_duration_seconds=0.4,
        )

        self.assertEqual(decision.review_duration_seconds, 0.4)
        self.assertEqual(decision.decision_mode, "detailed_review")
        self.assertTrue(decision.reviewed_in_detail)

    def test_negative_review_duration_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "review_duration_seconds_must_be_finite_and_non_negative",
        ):
            decide(
                draft=_draft(),
                final_answer=["magnesium"],
                decided_by="권혁찬",
                review_duration_seconds=-0.1,
            )

    def test_nonfinite_review_duration_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "review_duration_seconds_must_be_finite_and_non_negative",
        ):
            decide(
                draft=_draft(),
                final_answer=["magnesium"],
                decided_by="권혁찬",
                review_duration_seconds=float("nan"),
            )


class AdjudicationSummaryTest(unittest.TestCase):
    def test_accepting_everything_unchanged_is_surfaced_not_hidden(self) -> None:
        bench = _bench()
        for draft in bench.drafts:
            bench.decisions[draft.case_id] = decide(
                draft=draft, final_answer=list(draft.draft_answer), decided_by="권혁찬"
            )
        summary = summarise_adjudication(bench)

        self.assertEqual(summary["edit_rate_pct"], 0.0)
        self.assertIn(
            "edit_rate_zero_every_draft_was_accepted_unchanged", summary["warnings"]
        )

    def test_a_real_review_reports_its_edit_rate(self) -> None:
        bench = _bench(4)
        for index, draft in enumerate(bench.drafts):
            final = ["magnesium"] if index < 2 else list(draft.draft_answer)
            bench.decisions[draft.case_id] = decide(
                draft=draft, final_answer=final, decided_by="권혁찬"
            )
        summary = summarise_adjudication(bench)

        self.assertEqual(summary["edit_rate_pct"], 50.0)
        self.assertEqual(summary["counts"], {
            "accepted": 2, "edited": 2, "rejected": 0, "pending": 0
        })
        self.assertNotIn(
            "edit_rate_zero_every_draft_was_accepted_unchanged", summary["warnings"]
        )

    def test_unreviewed_cases_are_counted_as_pending(self) -> None:
        bench = _bench(5)
        bench.decisions["c0"] = decide(
            draft=bench.drafts[0], final_answer=["magnesium"], decided_by="권혁찬"
        )
        summary = summarise_adjudication(bench)

        self.assertEqual(summary["counts"]["pending"], 4)
        self.assertFalse(summary["complete"])

    def test_more_than_one_reviewer_is_flagged(self) -> None:
        bench = _bench(2)
        bench.decisions["c0"] = decide(
            draft=bench.drafts[0], final_answer=["a"], decided_by="권혁찬"
        )
        bench.decisions["c1"] = decide(
            draft=bench.drafts[1], final_answer=["b"], decided_by="다른사람"
        )
        summary = summarise_adjudication(bench)

        self.assertIn("multiple_reviewers_recorded", summary["warnings"])

    def test_rejected_cases_leave_the_answer_key(self) -> None:
        bench = _bench(3)
        bench.decisions["c0"] = decide(
            draft=bench.drafts[0], final_answer=["magnesium"], decided_by="권혁찬"
        )
        bench.decisions["c1"] = decide(
            draft=bench.drafts[1], final_answer=None, decided_by="권혁찬"
        )
        key = adjudicated_answer_key(bench)

        self.assertIn("c0", key)
        self.assertNotIn("c1", key)
        self.assertNotIn("c2", key)

    def test_summary_separates_detailed_and_batch_approved_cases(self) -> None:
        bench = _bench(2)
        bench.decisions["c0"] = decide(
            draft=bench.drafts[0],
            final_answer=list(bench.drafts[0].draft_answer),
            decided_by="권혁찬",
        )
        bench.decisions["c1"] = decide(
            draft=bench.drafts[1],
            final_answer=list(bench.drafts[1].draft_answer),
            decided_by="권혁찬",
            decision_mode="ai_consensus_batch_approval",
            reviewed_in_detail=False,
        )

        summary = summarise_adjudication(bench)

        self.assertEqual(summary["detailed_review_count"], 1)
        self.assertEqual(summary["batch_approved_count"], 1)

    def test_provenance_names_the_method_and_carries_the_edit_rate(self) -> None:
        bench = _bench(2)
        for draft in bench.drafts:
            bench.decisions[draft.case_id] = decide(
                draft=draft, final_answer=["magnesium"], decided_by="권혁찬"
            )
        provenance = build_provenance(
            bench,
            summarise_adjudication(bench),
            system_under_test_id="wellnessbox-recommendation-engine-v1",
        )

        self.assertEqual(
            provenance["answer_key_method"], "independent_draft_then_human_adjudication"
        )
        self.assertFalse(provenance["engine_output_consulted_before_sealing"])
        self.assertEqual(provenance["adjudication"]["edit_rate_pct"], 100.0)

    def test_provenance_carries_drafting_agent_and_blinded_files(self) -> None:
        bench = Workbench(
            "KPI-1",
            [
                CaseDraft(
                    case_id="c1",
                    prompt="질문",
                    draft_answer=["a"],
                    draft_source="reference",
                    drafting_agent="codex",
                    blinded_from=["engine/policy.json"],
                )
            ],
            {},
        )
        provenance = build_provenance(
            bench,
            summarise_adjudication(bench),
            system_under_test_id="wellnessbox-recommendation-engine-v1",
        )

        self.assertEqual(provenance["drafting_agent"], "codex")
        self.assertEqual(provenance["blinded_from"], ["engine/policy.json"])

    def test_kpi4_role_separation_requires_a_different_provider_family(self) -> None:
        bench = Workbench(
            "KPI-4",
            [
                CaseDraft(
                    case_id="c1",
                    prompt="질문",
                    draft_answer=["a"],
                    draft_source="reference",
                    drafting_agent="codex",
                    blinded_from=["engine/policy.json"],
                )
            ],
            {},
        )
        summary = summarise_adjudication(bench)

        with self.assertRaisesRegex(
            ValueError,
            "system_under_test_id_required",
        ):
            build_provenance(bench, summary)
        with self.assertRaisesRegex(
            ValueError,
            "drafting_actor_is_system_under_test",
        ):
            build_provenance(
                bench,
                summary,
                system_under_test_id="CODEX",
            )
        with self.assertRaisesRegex(
            ValueError,
            "system_under_test_provider_family_required_for_kpi4",
        ):
            build_provenance(
                bench,
                summary,
                system_under_test_id="wellnessbox-chat-v1",
            )
        with self.assertRaisesRegex(
            ValueError,
            "kpi4_drafting_agent_matches_system_under_test_provider_family",
        ):
            build_provenance(
                bench,
                summary,
                system_under_test_id="wellnessbox-chat-v1",
                system_under_test_provider_family="openai",
            )
        with self.assertRaisesRegex(
            ValueError,
            "system_under_test_provider_family_unknown_for_kpi4",
        ):
            build_provenance(
                bench,
                summary,
                system_under_test_id="wellnessbox-chat-v1",
                system_under_test_provider_family="unknown-vendor",
            )
        provenance = build_provenance(
            bench,
            summary,
            system_under_test_id="wellnessbox-chat-v1",
            system_under_test_provider_family="anthropic",
        )
        separation = provenance["role_separation"]
        self.assertTrue(separation["exact_identity_separated"])
        self.assertTrue(separation["provider_family_separated"])
        self.assertTrue(separation["provider_family_is_a_validity_gate"])


class PersistenceTest(unittest.TestCase):
    def test_a_saved_workbench_round_trips(self) -> None:
        bench = _bench(2)
        bench.decisions["c0"] = decide(
            draft=bench.drafts[0], final_answer=["magnesium"], decided_by="권혁찬"
        )
        with tempfile.TemporaryDirectory() as temp:
            path = save_workbench(Path(temp) / "wb.json", bench)
            restored = load_workbench(path)

        self.assertEqual(len(restored.drafts), 2)
        self.assertEqual(restored.decisions["c0"].action, "edited")
        self.assertEqual(restored.pending()[0].case_id, "c1")

    def test_ai_review_and_batch_approval_round_trip(self) -> None:
        bench = _bench(1)
        bench.primary_ai_draft = {
            "schema_version": "blind_primary_ai_answer_draft_v1",
            "drafting_agent": "claude",
        }
        bench.ai_review = {"schema_version": "independent_ai_answer_review_v1"}
        bench.batch_approval = {"approved_by": "권혁찬"}
        with tempfile.TemporaryDirectory() as temp:
            path = save_workbench(Path(temp) / "wb.json", bench)
            restored = load_workbench(path)

        self.assertEqual(restored.ai_review, bench.ai_review)
        self.assertEqual(restored.batch_approval, bench.batch_approval)
        self.assertEqual(restored.primary_ai_draft, bench.primary_ai_draft)

    def test_adaptive_review_fields_round_trip(self) -> None:
        bench = _bench(2)
        bench.ai_review = {
            "schema_version": "independent_ai_answer_review_v1",
            "reviewing_agent": "claude",
            "cases": {},
        }
        bench.batch_approval = {
            "approved_by": "여형준",
            "approved_at": "2026-08-01T01:00:00Z",
        }
        bench.decisions["c0"] = Decision(
            case_id="c0",
            action="accepted",
            final_answer=list(bench.drafts[0].draft_answer),
            decided_by="여형준",
            decided_at="2026-08-01T01:00:00Z",
            note="AI 합의안 일괄 승인; 개별 상세 검토 아님",
            decision_mode="ai_consensus_batch_approval",
            reviewed_in_detail=False,
        )

        with tempfile.TemporaryDirectory() as temp:
            restored = load_workbench(
                save_workbench(Path(temp) / "adaptive.json", bench)
            )

        self.assertEqual(restored.ai_review, bench.ai_review)
        self.assertEqual(restored.batch_approval, bench.batch_approval)
        self.assertEqual(
            restored.decisions["c0"].decision_mode,
            "ai_consensus_batch_approval",
        )
        self.assertFalse(restored.decisions["c0"].reviewed_in_detail)

    def test_summary_separates_detailed_review_from_batch_approval(self) -> None:
        bench = _bench(2)
        bench.decisions["c0"] = decide(
            draft=bench.drafts[0],
            final_answer=list(bench.drafts[0].draft_answer),
            decided_by="여형준",
        )
        bench.decisions["c1"] = Decision(
            case_id="c1",
            action="accepted",
            final_answer=list(bench.drafts[1].draft_answer),
            decided_by="여형준",
            decided_at="2026-08-01T01:00:00Z",
            decision_mode="ai_consensus_batch_approval",
            reviewed_in_detail=False,
        )

        summary = summarise_adjudication(bench)

        self.assertEqual(summary["detailed_review_count"], 1)
        self.assertEqual(summary["batch_approved_count"], 1)
        self.assertEqual(summary["detailed_edit_rate_pct"], 0.0)

    def test_legacy_workbench_without_new_provenance_fields_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.json"
            path.write_text(
                json.dumps(
                    {
                        "indicator_id": "KPI-1",
                        "drafts": [
                            {
                                "case_id": "c1",
                                "prompt": "질문",
                                "draft_answer": ["a"],
                                "draft_source": "reference",
                            }
                        ],
                        "decisions": {},
                    }
                ),
                encoding="utf-8",
            )
            restored = load_workbench(path)

        self.assertEqual(restored.drafts[0].drafting_agent, "")
        self.assertEqual(restored.drafts[0].blinded_from, [])
        self.assertEqual(restored.ai_review, {})
        self.assertIsNone(restored.batch_approval)
        self.assertEqual(restored.primary_ai_draft, {})


class SealDisposalTest(unittest.TestCase):
    def test_disposal_requires_a_named_person_and_reason(self) -> None:
        fields = {
            "indicator_id": "KPI-1",
            "seal_sha256": "abc",
            "discarded_by": "권혁찬",
            "reason": "과속 검토",
            "original_seal_path": "active.json",
            "archived_seal_path": "archive/seal.json",
            "archived_workbench_path": "archive/workbench.json",
        }
        with self.assertRaises(ValueError):
            build_seal_disposal_record(**{**fields, "discarded_by": " "})
        with self.assertRaises(ValueError):
            build_seal_disposal_record(**{**fields, "reason": " "})

    def test_confirmed_disposal_archives_and_resets_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal_path = root / "active.json"
            bench_path = root / "workbench.json"
            history_path = root / "history.json"
            archive_dir = root / "archive"
            bench = _bench(2)
            bench.batch_approval = {"approved_by": "권혁찬"}
            for draft in bench.drafts:
                bench.decisions[draft.case_id] = decide(
                    draft=draft,
                    final_answer=list(draft.draft_answer),
                    decided_by="권혁찬",
                    decided_at="2026-07-31T08:20:00Z",
                )
            save_workbench(bench_path, bench)
            seal_path.write_text(
                json.dumps(
                    {
                        "indicator_id": "KPI-1",
                        "seal_sha256": "abc123",
                    }
                ),
                encoding="utf-8",
            )

            record = discard_seal_with_audit_trail(
                active_seal_path=seal_path,
                workbench_path=bench_path,
                history_path=history_path,
                archive_dir=archive_dir,
                record_root=root,
                discarded_by="여형준",
                reason="과속 자동 수락 검토를 무효화",
                discarded_at="2026-07-31T09:00:00Z",
            )

            restored = load_workbench(bench_path)
            provenance = build_provenance(
                restored,
                summarise_adjudication(restored),
                system_under_test_id="wellnessbox-recommendation-engine-v1",
            )
            self.assertFalse(seal_path.exists())
            self.assertEqual(len(restored.decisions), 0)
            self.assertIsNone(restored.batch_approval)
            self.assertEqual(restored.seal_disposals, [record])
            self.assertEqual(provenance["prior_seal_disposals"], [record])
            self.assertTrue(Path(root / record["archived_seal_path"]).is_file())
            self.assertTrue(Path(root / record["archived_workbench_path"]).is_file())
            history = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(history["events"], [record])

    def test_cli_cancels_without_exact_human_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal_path = root / "active.json"
            bench_path = root / "workbench.json"
            seal_path.write_text(
                json.dumps({"indicator_id": "KPI-1", "seal_sha256": "abc123"}),
                encoding="utf-8",
            )
            save_workbench(bench_path, _bench(1))
            args = SimpleNamespace(
                indicator="KPI-1",
                by="여형준",
                reason="과속 자동 수락 검토를 무효화",
            )

            with (
                patch.object(workbench_cli, "seal_path", return_value=seal_path),
                patch.object(workbench_cli, "workbench_path", return_value=bench_path),
                patch("builtins.input", return_value="아니오"),
            ):
                result = workbench_cli.cmd_discard_seal(args)

            self.assertEqual(result, 2)
            self.assertTrue(seal_path.is_file())
            self.assertEqual(load_workbench(bench_path).decisions, {})

    def test_cli_can_confirm_a_seal_relocated_before_audited_disposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            active_path = root / "active.json"
            legacy_path = root / "discarded" / "legacy.json"
            legacy_path.parent.mkdir()
            bench_path = root / "workbench.json"
            legacy_path.write_text(
                json.dumps({"indicator_id": "KPI-1", "seal_sha256": "abc123"}),
                encoding="utf-8",
            )
            save_workbench(bench_path, _bench(1))
            args = SimpleNamespace(
                indicator="KPI-1",
                by="여형준",
                reason="사람 확인 없이 옮겨진 과속 검토 봉인을 정식 폐기함",
            )

            with (
                patch.object(workbench_cli, "seal_path", return_value=active_path),
                patch.object(
                    workbench_cli,
                    "legacy_discarded_seal_path",
                    return_value=legacy_path,
                ),
                patch.object(workbench_cli, "workbench_path", return_value=bench_path),
                patch.object(
                    workbench_cli,
                    "seal_disposal_history_path",
                    return_value=root / "history.json",
                ),
                patch.object(workbench_cli, "SEAL_DISPOSAL_DIR", root / "disposals"),
                patch("builtins.input", return_value="KPI-1 봉인 폐기"),
                patch.object(workbench_cli, "say"),
            ):
                result = workbench_cli.cmd_discard_seal(args)

            self.assertEqual(result, 0)
            self.assertFalse(legacy_path.exists())
            self.assertTrue((root / "history.json").is_file())
            restored = load_workbench(bench_path)
            self.assertEqual(len(restored.seal_disposals), 1)
            self.assertEqual(restored.seal_disposals[0]["discarded_by"], "여형준")


class ReviewPacingTest(unittest.TestCase):
    def test_rushed_decision_is_not_saved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = save_workbench(Path(temp) / "workbench.json", _bench(1))
            args = SimpleNamespace(indicator="KPI-1", by="권혁찬")
            with (
                patch.object(workbench_cli, "workbench_path", return_value=path),
                patch.object(
                    workbench_cli.time,
                    "monotonic",
                    side_effect=[0.0, workbench_cli.MIN_SECONDS_PER_CASE / 2],
                ),
                patch("builtins.input", return_value=""),
                patch.object(workbench_cli, "say"),
            ):
                result = workbench_cli.cmd_review(args)

            restored = load_workbench(path)
            self.assertEqual(result, 0)
            self.assertEqual(restored.decisions, {})
            self.assertEqual(len(restored.pending()), 1)


class DraftCliRoutingTest(unittest.TestCase):
    def test_kpi3_uses_the_blinded_drafter_and_records_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "workbench.json"
            args = SimpleNamespace(
                indicator="KPI-3",
                count=1,
                cases=None,
                draft_source=None,
                drafting_agent=None,
                blinded_from=None,
                blinded_from_registry=False,
                overwrite=False,
            )
            with (
                patch.object(workbench_cli, "workbench_path", return_value=path),
                patch.object(workbench_cli, "say"),
            ):
                result = workbench_cli.cmd_draft(args)

            restored = load_workbench(path)
            draft = restored.drafts[0]
            self.assertEqual(result, 0)
            self.assertEqual(
                draft.draft_source,
                workbench_cli.BLINDED_DRAFT_SOURCES["KPI-3"],
            )
            self.assertEqual(draft.drafting_agent, "codex")
            self.assertIn(
                "data/original_plan/closed_loop_next_action_policy_v1.json",
                draft.blinded_from,
            )
            self.assertEqual(draft.draft_answer, ["미정_검토자가_판단"])


class Kpi1DrafterTest(unittest.TestCase):
    def test_it_produces_the_full_hundred_cases(self) -> None:
        self.assertEqual(len(draft_kpi1_cases(ROOT, case_count=100)), 100)

    def test_every_case_has_a_non_empty_draft_answer(self) -> None:
        cases = draft_kpi1_cases(ROOT, case_count=100)

        self.assertTrue(all(case["draft_answer"] for case in cases))

    def test_case_ids_are_unique(self) -> None:
        ids = [case["case_id"] for case in draft_kpi1_cases(ROOT, case_count=100)]

        self.assertEqual(len(ids), len(set(ids)))

    def test_cases_cover_more_than_one_context(self) -> None:
        prompts = [case["prompt"] for case in draft_kpi1_cases(ROOT, case_count=100)]

        self.assertTrue(any("warfarin" in prompt for prompt in prompts))
        self.assertTrue(any("임신" in prompt for prompt in prompts))

    def test_the_drafter_is_deterministic(self) -> None:
        self.assertEqual(
            draft_kpi1_cases(ROOT, case_count=20), draft_kpi1_cases(ROOT, case_count=20)
        )

    def test_an_indicator_without_a_drafter_says_so(self) -> None:
        with self.assertRaises(KeyError):
            draft_cases("KPI-9", ROOT)


class AllDraftersTest(unittest.TestCase):
    """Every answer-key indicator must reach its 100-case minimum."""

    INDICATORS = ("KPI-1", "KPI-3", "KPI-4", "KPI-5")

    def test_each_indicator_has_a_drafter(self) -> None:
        self.assertEqual(set(DRAFTERS), set(self.INDICATORS))

    def test_each_drafter_reaches_one_hundred_cases(self) -> None:
        for indicator_id in self.INDICATORS:
            with self.subTest(indicator=indicator_id):
                self.assertEqual(len(draft_cases(indicator_id, ROOT, case_count=100)), 100)

    def test_no_drafter_emits_an_empty_answer(self) -> None:
        for indicator_id in self.INDICATORS:
            cases = draft_cases(indicator_id, ROOT, case_count=100)
            with self.subTest(indicator=indicator_id):
                self.assertTrue(all(case["draft_answer"] for case in cases))

    def test_case_ids_are_unique_per_indicator(self) -> None:
        for indicator_id in self.INDICATORS:
            ids = [case["case_id"] for case in draft_cases(indicator_id, ROOT, case_count=100)]
            with self.subTest(indicator=indicator_id):
                self.assertEqual(len(ids), len(set(ids)))

    def test_every_case_carries_a_rationale(self) -> None:
        for indicator_id in self.INDICATORS:
            cases = draft_cases(indicator_id, ROOT, case_count=100)
            with self.subTest(indicator=indicator_id):
                self.assertTrue(all(case["draft_rationale"] for case in cases))

    def test_each_drafter_is_deterministic(self) -> None:
        for indicator_id in self.INDICATORS:
            with self.subTest(indicator=indicator_id):
                self.assertEqual(
                    draft_cases(indicator_id, ROOT, case_count=30),
                    draft_cases(indicator_id, ROOT, case_count=30),
                )

    def test_kpi3_covers_every_next_action_rule(self) -> None:
        actions = {
            case["draft_answer"][0] for case in draft_cases("KPI-3", ROOT, case_count=100)
        }

        self.assertGreaterEqual(len(actions), 9)
        self.assertIn("stop_and_escalate", actions)


if __name__ == "__main__":
    unittest.main()
