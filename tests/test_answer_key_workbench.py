from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wellnessbox_rnd.evals.answer_key_drafters import (
    DRAFT_SOURCE,
    draft_cases,
    draft_kpi1_cases,
)
from wellnessbox_rnd.evals.answer_key_workbench import (
    CaseDraft,
    Workbench,
    adjudicated_answer_key,
    assert_source_is_independent,
    build_drafts,
    build_provenance,
    decide,
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
        )

        self.assertFalse(packaged["engine_output_consulted"])
        self.assertEqual(packaged["draft_source"], DRAFT_SOURCE)

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

    def test_provenance_names_the_method_and_carries_the_edit_rate(self) -> None:
        bench = _bench(2)
        for draft in bench.drafts:
            bench.decisions[draft.case_id] = decide(
                draft=draft, final_answer=["magnesium"], decided_by="권혁찬"
            )
        provenance = build_provenance(bench, summarise_adjudication(bench))

        self.assertEqual(
            provenance["answer_key_method"], "independent_draft_then_human_adjudication"
        )
        self.assertFalse(provenance["engine_output_consulted_before_sealing"])
        self.assertEqual(provenance["adjudication"]["edit_rate_pct"], 100.0)


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


if __name__ == "__main__":
    unittest.main()
