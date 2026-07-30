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
    credential_method_problem,
    license_id_problem,
    load_draft_reviewer_ids,
    load_registry,
    normalize_identity,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_registry(ROOT)


def _reviewer(**overrides):
    reviewer = {
        "name": "권혁찬",
        "organization": "웰니스박스 TIPS 과제 참여연구원",
        "pharmacist_license_id": "제34567호",
        "credential_verification_method": "면허증 원본을 대면 확인함",
        "reviewer_role": "project_pharmacist",
        "relationship_to_project": "project_co_researcher",
        "independent_of_implementation_team": False,
        "was_ai_draft_reviewer": False,
    }
    reviewer.update(overrides)
    return reviewer


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

    def test_an_actual_pharmacist_is_not_blocked(self) -> None:
        self.assertIsNone(blocked_identity_match("권혁찬", REGISTRY))

    def test_normalisation_keeps_distinct_people_distinct(self) -> None:
        self.assertNotEqual(normalize_identity("권혁찬"), normalize_identity("여형준"))


class LicenseIdTest(unittest.TestCase):
    def test_empty_is_rejected(self) -> None:
        self.assertEqual(license_id_problem("", REGISTRY), "license_id_missing")

    def test_not_collected_placeholder_is_rejected(self) -> None:
        for value in ("not_collected", "NOT COLLECTED", "미수집", "n/a", "-"):
            with self.subTest(value=value):
                self.assertIsNotNone(license_id_problem(value, REGISTRY))

    def test_text_without_enough_digits_is_rejected(self) -> None:
        self.assertEqual(
            license_id_problem("license-actual-value", REGISTRY),
            "license_id_needs_at_least_4_digits",
        )

    def test_a_plausible_licence_number_passes(self) -> None:
        for value in ("제34567호", "34567", "KR-2019-88123"):
            with self.subTest(value=value):
                self.assertIsNone(license_id_problem(value, REGISTRY))


class CredentialMethodTest(unittest.TestCase):
    def test_owner_attestation_is_rejected(self) -> None:
        self.assertEqual(
            credential_method_problem("project_owner_attestation", REGISTRY),
            "credential_verification_method_is_self_or_owner_attestation",
        )

    def test_empty_and_placeholder_values_are_rejected(self) -> None:
        for value in ("", "n/a", "없음", "미확인", "self attestation"):
            with self.subTest(value=value):
                self.assertIsNotNone(credential_method_problem(value, REGISTRY))

    def test_too_short_a_description_is_rejected(self) -> None:
        self.assertIsNotNone(credential_method_problem("확인", REGISTRY))

    def test_a_described_method_passes(self) -> None:
        self.assertIsNone(
            credential_method_problem("면허증 원본을 대면 확인함", REGISTRY)
        )


class AiDraftReviewerCrossCheckTest(unittest.TestCase):
    def test_declaring_false_while_present_in_the_ledger_is_a_conflict(self) -> None:
        problem = ai_draft_reviewer_conflict(
            declared=False, reviewer_name="권혁찬", draft_reviewer_ids={"권혁찬"}
        )

        self.assertEqual(
            problem, "reviewer_appears_in_h003_draft_ledger_but_declared_otherwise"
        )

    def test_spacing_variants_still_match_the_ledger(self) -> None:
        problem = ai_draft_reviewer_conflict(
            declared=False, reviewer_name="권 혁찬", draft_reviewer_ids={"권혁찬"}
        )

        self.assertIsNotNone(problem)

    def test_declaring_true_while_present_is_accepted(self) -> None:
        self.assertIsNone(
            ai_draft_reviewer_conflict(
                declared=True, reviewer_name="권혁찬", draft_reviewer_ids={"권혁찬"}
            )
        )

    def test_a_reviewer_absent_from_the_ledger_is_accepted(self) -> None:
        self.assertIsNone(
            ai_draft_reviewer_conflict(
                declared=False, reviewer_name="다른약사", draft_reviewer_ids={"권혁찬"}
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
    def test_a_complete_reviewer_passes(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(), registry=REGISTRY, draft_reviewer_ids=set()
        )

        self.assertEqual(audit["status"], "READY")
        self.assertEqual(audit["problems"], [])

    def test_every_problem_is_reported_at_once(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(
                name="여 형준",
                pharmacist_license_id="not_collected",
                credential_verification_method="project_owner_attestation",
            ),
            registry=REGISTRY,
            draft_reviewer_ids=set(),
        )

        self.assertEqual(audit["status"], "BLOCKED")
        self.assertEqual(len(audit["problems"]), 3)

    def test_self_reported_draft_review_is_kept_as_a_warning(self) -> None:
        audit = audit_reviewer_credentials(
            _reviewer(was_ai_draft_reviewer=True),
            registry=REGISTRY,
            draft_reviewer_ids={"권혁찬"},
        )

        self.assertEqual(audit["status"], "READY")
        self.assertEqual(audit["warnings"], ["reviewer_also_reviewed_ai_drafts"])


class ConsoleRejectsWeakCredentialsTest(unittest.TestCase):
    def _document(self, **reviewer_overrides):
        cases_path = ROOT / "data/original_plan/op039_external_review_cases_v1.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        reviewer = _reviewer(name="외부약사", organization="독립약국", **reviewer_overrides)
        return {
            "schema_version": "op039_external_review_result_v1",
            "package_id": cases["package_id"],
            "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            "reviewer": reviewer,
            "decisions": [
                {"case_id": item["case_id"], "decision": "valid", "comment": "확인함"}
                for item in cases["cases"]
            ],
            "reviewed_at": "2026-07-27T06:00:00Z",
            "signature_name": reviewer["name"],
        }

    def _console(self, temp: str) -> FinalSessionConsole:
        return FinalSessionConsole(ROOT, state_root=Path(temp) / "session")

    def test_placeholder_licence_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                self._console(temp).register_external_validation_upload(
                    self._document(pharmacist_license_id="not_collected")
                )

    def test_owner_attestation_method_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                self._console(temp).register_external_validation_upload(
                    self._document(credential_verification_method="project_owner_attestation")
                )

    def test_owner_alias_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            document = self._document()
            document["reviewer"]["name"] = "여 형준"
            document["signature_name"] = "여 형준"
            with self.assertRaises(ValueError):
                self._console(temp).register_external_validation_upload(document)

    def test_a_complete_submission_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = self._console(temp)
            console.register_external_validation_upload(self._document())

            self.assertEqual(console.state["steps"]["H-005"]["status"], "completed")
            self.assertEqual(
                console.state["steps"]["H-005"]["review_character"],
                "project_pharmacist_expert_safety_review",
            )


if __name__ == "__main__":
    unittest.main()
