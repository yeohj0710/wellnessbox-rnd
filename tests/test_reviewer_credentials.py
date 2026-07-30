from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from wellnessbox_rnd.governance.final_session_console import FinalSessionConsole
from wellnessbox_rnd.governance.reviewer_credentials import (
    ai_draft_reviewer_conflict,
    audit_reviewer_credentials,
    blocked_identity_match,
    load_draft_reviewer_ids,
    load_registry,
    normalize_identity,
    registered_reviewer,
    review_character_for,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_registry(ROOT)
REVIEWER_NAME = "권혁찬"
REVIEWER_ORG = "웰니스박스 TIPS 과제 참여연구원"


def _reviewer(**overrides):
    reviewer = {
        "name": REVIEWER_NAME,
        "organization": REVIEWER_ORG,
        "reviewer_role": "project_pharmacist_candidate",
        "qualification_stage": "pharmacist_candidate",
        "relationship_to_project": "project_co_researcher",
        "implemented_system": False,
        "independent_of_implementation_team": False,
        "was_ai_draft_reviewer": False,
    }
    reviewer.update(overrides)
    return reviewer


class QualificationStageContractTest(unittest.TestCase):
    def test_year2_registry_records_candidates_not_licensed_pharmacists(self) -> None:
        stage = REGISTRY["qualification_stage"]

        self.assertEqual(stage["current_stage"], "pharmacist_candidate")
        self.assertEqual(stage["license_status"], "not_yet_licensed")
        self.assertEqual(stage["expected_licensure_period"], "2027-01")
        self.assertEqual(stage["licensed_review_period"], "year3")
        self.assertEqual(stage["research_deadline"], "2027-10")

    def test_both_participants_are_registered_as_candidates(self) -> None:
        stages = {
            entry["name"]: entry["qualification_stage"]
            for entry in REGISTRY["registered_reviewers"]
        }

        self.assertEqual(
            stages,
            {"여형준": "pharmacist_candidate", "권혁찬": "pharmacist_candidate"},
        )

    def test_the_owner_may_not_review_h005(self) -> None:
        owner = registered_reviewer("여형준", REGISTRY)

        self.assertFalse(owner["may_review_h005"])

    def test_a_candidate_review_is_never_labelled_as_licensed(self) -> None:
        self.assertEqual(
            review_character_for("pharmacist_candidate"),
            "pharmacist_candidate_preliminary_safety_review",
        )
        self.assertEqual(
            review_character_for("licensed_pharmacist"),
            "licensed_pharmacist_expert_safety_review",
        )


class OwnerIdentityBlockTest(unittest.TestCase):
    def test_exact_owner_name_is_blocked(self) -> None:
        self.assertEqual(blocked_identity_match("여형준", REGISTRY), "여형준")

    def test_spacing_variant_no_longer_slips_through(self) -> None:
        for variant in ("여 형준", " 여형준 ", "여\t형준"):
            with self.subTest(variant=variant):
                self.assertEqual(blocked_identity_match(variant, REGISTRY), "여형준")

    def test_registered_romanised_alias_is_blocked(self) -> None:
        for variant in ("Yeo Hyeongjun", "yeohyeongjun", "HJYEO"):
            with self.subTest(variant=variant):
                self.assertEqual(blocked_identity_match(variant, REGISTRY), "여형준")

    def test_system_account_and_its_aliases_are_blocked(self) -> None:
        for variant in ("웰니스박스", "웰니스 박스", "WellnessBox", "wellness box"):
            with self.subTest(variant=variant):
                self.assertEqual(blocked_identity_match(variant, REGISTRY), "웰니스박스")

    def test_zero_width_padding_does_not_bypass_the_block(self) -> None:
        self.assertEqual(blocked_identity_match("여​형‌준", REGISTRY), "여형준")

    def test_the_participating_reviewer_is_not_blocked(self) -> None:
        self.assertIsNone(blocked_identity_match(REVIEWER_NAME, REGISTRY))

    def test_normalisation_keeps_distinct_people_distinct(self) -> None:
        self.assertNotEqual(normalize_identity("권혁찬"), normalize_identity("여형준"))


class ParticipantLookupTest(unittest.TestCase):
    def test_a_registered_participant_is_found_despite_spacing(self) -> None:
        entry = registered_reviewer("권 혁찬", REGISTRY)

        self.assertIsNotNone(entry)
        self.assertEqual(entry["name"], "권혁찬")

    def test_an_unregistered_person_is_rejected(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(name="모르는사람", organization="어딘가"),
            registry=REGISTRY,
            draft_reviewer_ids=set(),
        )

        self.assertEqual(audit["status"], "BLOCKED")
        self.assertIn("reviewer_is_not_a_registered_project_participant", audit["problems"])

    def test_a_mismatched_organization_is_rejected(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(organization="다른 약국"), registry=REGISTRY, draft_reviewer_ids=set()
        )

        self.assertIn(
            "reviewer_organization_does_not_match_the_project_record", audit["problems"]
        )

    def test_only_name_and_organization_are_required(self) -> None:
        minimal = {
            "name": REVIEWER_NAME,
            "organization": REVIEWER_ORG,
            "was_ai_draft_reviewer": True,
        }
        audit = audit_reviewer_credentials(
            minimal, registry=REGISTRY, draft_reviewer_ids={REVIEWER_NAME}
        )

        self.assertEqual(audit["status"], "READY")

    def test_a_missing_organization_is_rejected(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(organization=""), registry=REGISTRY, draft_reviewer_ids=set()
        )

        self.assertIn("reviewer_organization_missing", audit["problems"])


class AiDraftReviewerCrossCheckTest(unittest.TestCase):
    def test_declaring_false_while_present_in_the_ledger_is_a_conflict(self) -> None:
        problem = ai_draft_reviewer_conflict(
            declared=False, reviewer_name=REVIEWER_NAME, draft_reviewer_ids={REVIEWER_NAME}
        )

        self.assertEqual(
            problem, "reviewer_appears_in_h003_draft_ledger_but_declared_otherwise"
        )

    def test_spacing_variants_still_match_the_ledger(self) -> None:
        self.assertIsNotNone(
            ai_draft_reviewer_conflict(
                declared=False, reviewer_name="권 혁찬", draft_reviewer_ids={REVIEWER_NAME}
            )
        )

    def test_declaring_true_while_present_is_accepted(self) -> None:
        self.assertIsNone(
            ai_draft_reviewer_conflict(
                declared=True, reviewer_name=REVIEWER_NAME, draft_reviewer_ids={REVIEWER_NAME}
            )
        )

    def test_a_missing_ledger_reads_as_no_reviewers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(load_draft_reviewer_ids(Path(temp) / "absent.sqlite3"), set())

    def test_reviewer_ids_are_read_from_a_real_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "ledger.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute("create table ai_drafts (reviewer_id text)")
            connection.executemany(
                "insert into ai_drafts values (?)", [("권혁찬",), ("웰니스박스",), (None,)]
            )
            connection.commit()
            connection.close()

            self.assertEqual(load_draft_reviewer_ids(database), {"권혁찬", "웰니스박스"})


class AuditReviewerCredentialsTest(unittest.TestCase):
    def test_a_registered_candidate_passes(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(), registry=REGISTRY, draft_reviewer_ids=set()
        )

        self.assertEqual(audit["status"], "READY")
        self.assertEqual(audit["problems"], [])
        self.assertEqual(audit["matched_participant"], REVIEWER_NAME)

    def test_the_audit_always_demands_a_licensed_reconfirmation_in_year2(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(), registry=REGISTRY, draft_reviewer_ids=set()
        )

        self.assertTrue(audit["requires_licensed_reconfirmation"])
        self.assertEqual(audit["qualification_stage"], "pharmacist_candidate")
        self.assertEqual(audit["license_status"], "not_yet_licensed")
        self.assertIn(
            "review_performed_before_licensure_requires_year3_reconfirmation",
            audit["warnings"],
        )

    def test_claiming_a_licence_the_reviewer_does_not_hold_is_refused(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(qualification_stage="licensed_pharmacist"),
            registry=REGISTRY,
            draft_reviewer_ids=set(),
        )

        self.assertEqual(audit["status"], "BLOCKED")
        self.assertIn("qualification_stage_must_be:pharmacist_candidate", audit["problems"])

    def test_the_owner_is_refused_even_with_a_matching_organization(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(name="여형준", organization="웰니스박스 TIPS 과제 책임연구원"),
            registry=REGISTRY,
            draft_reviewer_ids=set(),
        )

        self.assertEqual(audit["status"], "BLOCKED")
        self.assertIn("reviewer_is_a_blocked_identity:여형준", audit["problems"])

    def test_self_reported_draft_review_is_kept_as_a_warning(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(was_ai_draft_reviewer=True),
            registry=REGISTRY,
            draft_reviewer_ids={REVIEWER_NAME},
        )

        self.assertEqual(audit["status"], "READY")
        self.assertIn("reviewer_also_reviewed_ai_drafts", audit["warnings"])


class ConsoleRecordsAPreliminaryReviewTest(unittest.TestCase):
    def _document(self, **reviewer_overrides):
        cases_path = ROOT / "data/original_plan/op039_external_review_cases_v1.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        overrides = {"was_ai_draft_reviewer": True}
        overrides.update(reviewer_overrides)
        reviewer = _reviewer(**overrides)
        return {
            "schema_version": "op039_external_review_result_v1",
            "package_id": cases["package_id"],
            "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            "reviewer": reviewer,
            "decisions": [
                {"case_id": item["case_id"], "decision": "valid", "comment": "확인함"}
                for item in cases["cases"]
            ],
            "reviewed_at": "2026-07-30T06:00:00Z",
            "signature_name": reviewer["name"],
        }

    def _console(self, temp: str) -> FinalSessionConsole:
        return FinalSessionConsole(ROOT, state_root=Path(temp) / "session")

    def test_a_candidate_review_is_recorded_as_preliminary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = self._console(temp)
            console.register_external_validation_upload(self._document())
            step = console.state["steps"]["H-005"]

        self.assertEqual(step["status"], "completed")
        self.assertEqual(
            step["review_character"], "pharmacist_candidate_preliminary_safety_review"
        )
        self.assertTrue(step["requires_licensed_reconfirmation"])
        self.assertEqual(step["license_status"], "not_yet_licensed")
        self.assertEqual(step["expected_licensure_period"], "2027-01")

    def test_an_unregistered_reviewer_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                self._console(temp).register_external_validation_upload(
                    self._document(name="외부약사", organization="독립약국")
                )

    def test_the_owner_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            document = self._document()
            document["reviewer"]["name"] = "여 형준"
            document["signature_name"] = "여 형준"
            with self.assertRaises(ValueError):
                self._console(temp).register_external_validation_upload(document)

    def test_a_licensed_claim_from_a_candidate_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                self._console(temp).register_external_validation_upload(
                    self._document(qualification_stage="licensed_pharmacist")
                )


if __name__ == "__main__":
    unittest.main()
