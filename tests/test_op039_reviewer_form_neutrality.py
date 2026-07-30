from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "data/original_plan/final_session/op039_external_reviewer_form.html"
CASES = ROOT / "data/original_plan/op039_external_review_cases_v1.json"


class _FormReader(HTMLParser):
    """Collect the parts of the H-005 form a reviewer is supposed to fill in."""

    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[dict[str, str | None]] = []
        self.textarea_bodies: list[str] = []
        self._open_textarea: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input":
            self.inputs.append(attributes)
        elif tag == "textarea":
            self._open_textarea = ""

    def handle_data(self, data: str) -> None:
        if self._open_textarea is not None:
            self._open_textarea += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "textarea" and self._open_textarea is not None:
            self.textarea_bodies.append(self._open_textarea)
            self._open_textarea = None


def _read_form() -> _FormReader:
    markup = FORM.read_text(encoding="utf-8")
    body = markup.split("<script>")[0]
    reader = _FormReader()
    reader.feed(body)
    return reader


class Op039ReviewerFormNeutralityTest(unittest.TestCase):
    def test_no_case_decision_is_preselected(self) -> None:
        reader = _read_form()
        radios = [item for item in reader.inputs if item.get("type") == "radio"]
        case_count = json.loads(CASES.read_text(encoding="utf-8"))["case_count"]

        self.assertEqual(len(radios), case_count * 2)
        self.assertEqual([item for item in radios if "checked" in item], [])

    def test_no_comment_is_prefilled(self) -> None:
        reader = _read_form()
        case_count = json.loads(CASES.read_text(encoding="utf-8"))["case_count"]

        self.assertEqual(len(reader.textarea_bodies), case_count)
        self.assertEqual([body for body in reader.textarea_bodies if body.strip()], [])

    def test_identity_fields_exist_and_are_empty(self) -> None:
        reader = _read_form()
        by_id = {item.get("id"): item for item in reader.inputs if item.get("id")}

        for field in ("name", "org", "signature"):
            with self.subTest(field=field):
                self.assertIn(field, by_id)
                self.assertIsNone(by_id[field].get("value"))

    def test_no_licence_fields_are_asked_for_before_licensure(self) -> None:
        reader = _read_form()
        by_id = {item.get("id") for item in reader.inputs if item.get("id")}

        self.assertNotIn("license", by_id)
        self.assertNotIn("credential", by_id)

    def test_ai_draft_reviewer_flag_is_an_unchecked_self_report(self) -> None:
        reader = _read_form()
        by_id = {item.get("id"): item for item in reader.inputs if item.get("id")}

        self.assertEqual(by_id["draftReviewer"].get("type"), "checkbox")
        self.assertNotIn("checked", by_id["draftReviewer"])

    def test_signature_is_typed_rather_than_copied_from_the_name_field(self) -> None:
        markup = FORM.read_text(encoding="utf-8")

        self.assertIn("signature_name:signature", markup)
        self.assertNotIn("signature_name:name", markup)
        self.assertIn("서명은 검토자 성명과 같아야 합니다", markup)

    def test_stored_judgments_are_not_copied_into_the_form(self) -> None:
        markup = FORM.read_text(encoding="utf-8")

        self.assertNotIn("not_collected", markup)
        self.assertNotIn("project_owner_attestation", markup)
        self.assertNotIn("AI 제안", markup)


if __name__ == "__main__":
    unittest.main()
