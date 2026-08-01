from __future__ import annotations

import unittest
from pathlib import Path

from wellnessbox_rnd.evals.reference_standard import (
    canonical_digest,
    indicator,
    load_contract,
    score_against_seal,
    seal_reference_standard,
    verify_seal,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_contract(ROOT)


def _seal(
    cases=None,
    sealed_by="권혁찬",
    indicator_id="KPI-1",
    provenance=None,
):
    return seal_reference_standard(
        indicator_id=indicator_id,
        cases=cases if cases is not None else {"case-1": ["omega3", "vitaminD"]},
        sealed_by=sealed_by,
        sealed_at="2026-07-30T12:00:00Z",
        contract=CONTRACT,
        provenance=provenance,
    )


class ContractTest(unittest.TestCase):
    def test_the_accredited_lab_test_is_after_research_not_a_gate(self) -> None:
        final = CONTRACT["final_verification"]

        self.assertIn("KOLAS", final["evaluation_environment"])
        self.assertEqual(final["when"], "after_research_completion")
        self.assertFalse(final["is_a_research_phase_gate"])

    def test_the_contract_covers_all_seven_indicators(self) -> None:
        ids = [item["id"] for item in CONTRACT["indicators"]]

        self.assertEqual(ids, [f"KPI-{number}" for number in range(1, 8)])

    def test_weights_sum_to_one_hundred(self) -> None:
        self.assertEqual(sum(item["weight"] for item in CONTRACT["indicators"]), 100)

    def test_the_effect_indicator_needs_a_hundred_real_people(self) -> None:
        spec = indicator(CONTRACT, "KPI-2")

        self.assertEqual(spec["minimum_sample"], {"unit": "person", "count": 100})
        self.assertFalse(spec["reference_standard"]["synthetic_allowed"])
        self.assertFalse(spec["internal_only_possible"])

    def test_answer_key_indicators_forbid_synthetic_reference_standards(self) -> None:
        for indicator_id in ("KPI-1", "KPI-3", "KPI-4", "KPI-5"):
            with self.subTest(indicator=indicator_id):
                spec = indicator(CONTRACT, indicator_id)
                self.assertFalse(spec["reference_standard"]["synthetic_allowed"])
                self.assertTrue(spec["reference_standard"]["must_precede_engine_output"])

    def test_training_input_may_be_synthetic_but_reference_standards_may_not(self) -> None:
        policy = CONTRACT["synthetic_data_policy"]

        self.assertTrue(policy["training_input"]["allowed"])
        self.assertFalse(policy["kpi_reference_standard"]["allowed"])
        self.assertTrue(policy["distribution_similarity_claim"]["allowed"])


class SealTest(unittest.TestCase):
    def test_a_seal_records_who_made_the_answer_and_when(self) -> None:
        seal = _seal()

        self.assertEqual(seal["sealed_by"], "권혁찬")
        self.assertEqual(seal["sealed_at"], "2026-07-30T12:00:00Z")
        self.assertFalse(seal["engine_output_seen_before_sealing"])

    def test_an_unnamed_sealer_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _seal(sealed_by="   ")

    def test_an_empty_answer_set_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _seal(cases={"case-1": []})

    def test_no_cases_at_all_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _seal(cases={})

    def test_the_minimum_sample_is_reported_not_silently_ignored(self) -> None:
        seal = _seal()

        self.assertEqual(seal["minimum_sample_count"], 100)
        self.assertFalse(seal["meets_minimum_sample"])

    def test_a_hundred_cases_meets_the_minimum(self) -> None:
        seal = _seal(cases={f"case-{index}": ["omega3"] for index in range(100)})

        self.assertTrue(seal["meets_minimum_sample"])

    def test_an_intact_seal_verifies(self) -> None:
        self.assertTrue(verify_seal(_seal())["seal_intact"])

    def test_editing_the_answer_after_sealing_is_detected(self) -> None:
        seal = _seal()
        seal["cases"]["case-1"].append("magnesium")
        check = verify_seal(seal)

        self.assertFalse(check["seal_intact"])
        self.assertEqual(check["status"], "BLOCKED")

    def test_editing_governance_provenance_after_sealing_is_detected(self) -> None:
        seal = _seal(
            provenance={
                "integrity_audit": {"verdict": "PASS"},
                "role_separation": {"system_under_test_id": "engine-v1"},
            }
        )
        seal["provenance"]["integrity_audit"]["verdict"] = "FAIL"

        check = verify_seal(seal)

        self.assertFalse(check["seal_intact"])
        self.assertEqual(check["reason"], "seal_payload_digest_mismatch")

    def test_legacy_case_only_digest_is_not_accepted_as_a_current_seal(self) -> None:
        seal = _seal()
        seal["schema_version"] = "reference_standard_seal_v1"
        seal["seal_sha256"] = canonical_digest(seal["cases"])

        check = verify_seal(seal)

        self.assertFalse(check["seal_intact"])
        self.assertEqual(check["reason"], "unsupported_seal_schema")

    def test_ingredient_order_does_not_change_the_digest(self) -> None:
        self.assertEqual(
            canonical_digest({"case-1": ["a", "b"]}), canonical_digest({"case-1": ["a", "b"]})
        )
        self.assertNotEqual(
            canonical_digest({"case-1": ["a", "b"]}), canonical_digest({"case-1": ["a", "c"]})
        )


class ScoringTest(unittest.TestCase):
    def test_a_perfect_engine_scores_one_hundred(self) -> None:
        seal = _seal(cases={"case-1": ["omega3", "vitaminD"]})
        result = score_against_seal(
            seal=seal, engine_output={"case-1": ["omega3", "vitaminD"]}
        )

        self.assertEqual(result["mean_score_pct"], 100.0)

    def test_the_score_follows_the_plan_formula(self) -> None:
        seal = _seal(cases={"case-1": ["a", "b", "c", "d"]})
        result = score_against_seal(seal=seal, engine_output={"case-1": ["a", "b", "x"]})

        self.assertEqual(result["mean_score_pct"], 50.0)
        self.assertEqual(result["per_case"][0]["missing_from_engine"], ["c", "d"])

    def test_extra_engine_ingredients_do_not_raise_the_score(self) -> None:
        seal = _seal(cases={"case-1": ["a", "b"]})
        result = score_against_seal(
            seal=seal, engine_output={"case-1": ["a", "b", "c", "d", "e"]}
        )

        self.assertEqual(result["mean_score_pct"], 100.0)
        self.assertEqual(result["per_case"][0]["engine_count"], 5)

    def test_a_missing_engine_case_scores_zero_and_is_listed(self) -> None:
        seal = _seal(cases={"case-1": ["a"], "case-2": ["b"]})
        result = score_against_seal(seal=seal, engine_output={"case-1": ["a"]})

        self.assertEqual(result["mean_score_pct"], 50.0)
        self.assertEqual(result["cases_missing_engine_output"], ["case-2"])

    def test_scoring_refuses_when_the_seal_was_edited(self) -> None:
        seal = _seal()
        seal["cases"]["case-1"] = ["omega3"]

        with self.assertRaises(ValueError):
            score_against_seal(seal=seal, engine_output={"case-1": ["omega3"]})

    def test_the_result_is_labelled_a_research_phase_measurement(self) -> None:
        result = score_against_seal(seal=_seal(), engine_output={"case-1": ["omega3"]})

        self.assertEqual(
            result["measurement_environment"], "research_phase_internal_measurement"
        )
        self.assertIn("연구 기간", result["note"])

    def test_the_result_carries_the_seal_provenance(self) -> None:
        seal = _seal()
        result = score_against_seal(seal=seal, engine_output={"case-1": ["omega3"]})

        self.assertEqual(result["sealed_by"], "권혁찬")
        self.assertEqual(result["seal_sha256"], seal["seal_sha256"])


if __name__ == "__main__":
    unittest.main()
