"""The KPI-3/4 drafts must not reproduce the tables the engine reads."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.blinded_drafters import (  # noqa: E402
    BLINDED_FROM,
    KPI3_UNDECIDED,
    NEXT_ACTION_VOCABULARY,
    draft_kpi3_cases,
    draft_kpi4_cases,
)

POLICY_PATH = ROOT / "data/original_plan/closed_loop_next_action_policy_v1.json"


class Kpi4BlindedDrafts(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = draft_kpi4_cases(ROOT, case_count=100)

    def test_meets_the_hundred_question_minimum_with_distinct_questions(self) -> None:
        self.assertEqual(len(self.cases), 100)
        self.assertEqual(len({case["prompt"] for case in self.cases}), 100)

    def test_answers_are_not_five_repeated_rubric_strings(self) -> None:
        distinct = {tuple(sorted(case["draft_answer"])) for case in self.cases}
        self.assertGreater(len(distinct), 50, "정답이 사실상 몇 종으로 수렴하면 유효 표본이 아니다")

    def test_every_case_carries_a_page_citation(self) -> None:
        for case in self.cases:
            self.assertIn("p", case["draft_rationale"])
            self.assertTrue(case["draft_answer"])

    def test_medication_context_changes_the_answer(self) -> None:
        """A drug context must add an obligation, otherwise context is decorative."""
        with_context = [
            case for case in self.cases
            if "supplement_depleted_nutrient" in case["draft_answer"]
            or "separate_dosing" in case["draft_answer"]
        ]
        self.assertGreater(len(with_context), 0)

    def test_case_ids_are_unique(self) -> None:
        ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))


class Kpi3BlindedScenarios(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = draft_kpi3_cases(ROOT, case_count=100)

    def test_produces_a_hundred_distinct_situations(self) -> None:
        self.assertEqual(len(self.cases), 100)
        self.assertEqual(len({case["prompt"] for case in self.cases}), 100)

    def test_no_answer_is_supplied(self) -> None:
        """The whole point: the action is not in this repository."""
        for case in self.cases:
            self.assertEqual(case["draft_answer"], [KPI3_UNDECIDED])

    def test_prompt_never_contains_a_policy_action(self) -> None:
        """Naming the action inside the situation would hand over the answer."""
        for case in self.cases:
            for action in NEXT_ACTION_VOCABULARY:
                self.assertNotIn(action, case["prompt"])

    def test_situations_do_not_reuse_the_policy_trigger_syntax(self) -> None:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        triggers = {
            str(key)
            for rule in policy["rules"]
            for key in rule.get("when", {})
        }
        for case in self.cases:
            for trigger in triggers:
                self.assertNotIn(trigger, case["prompt"])


class BlindingDeclaration(unittest.TestCase):
    def test_blinded_from_names_the_engine_tables(self) -> None:
        self.assertIn("data/original_plan/closed_loop_next_action_policy_v1.json", BLINDED_FROM)
        self.assertIn("data/rules/safety_rules.json", BLINDED_FROM)

    def test_blinded_files_are_not_read_by_the_drafters(self) -> None:
        source = (
            ROOT / "src/wellnessbox_rnd/evals/blinded_drafters.py"
        ).read_text(encoding="utf-8")
        body = source.split('BLINDED_FROM: tuple[str, ...] = (', 1)[1].split(")", 1)[1]
        self.assertNotIn("closed_loop_next_action_policy_v1.json", body)
        self.assertNotIn("safety_rules.json", body)
        self.assertNotIn("goal_ingredient_priors_v1.json", body)


if __name__ == "__main__":
    unittest.main()
