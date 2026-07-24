from __future__ import annotations

import hashlib
import json
import sqlite3
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
    def test_operational_wizard_submits_prefilled_actual_records_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            replies = [
                {
                    "execution_id": "exec_" + "1" * 32,
                    "plan_id": "plan_" + "2" * 32,
                    "baseline_event_id": "event_" + "3" * 32,
                },
                {"event_id": "event_" + "4" * 32, "action_decision": "maintain"},
            ]
            with patch.object(console, "_wellnessbox_json", side_effect=replies) as request:
                console.confirm_operational_baseline()
                console.confirm_operational_followup()

            baseline_body = request.call_args_list[0].kwargs["body"]
            self.assertEqual(baseline_body["profile"]["name"], "연구 프로필 01")
            self.assertEqual(baseline_body["researchProfileId"], "profile-01")
            self.assertEqual(baseline_body["profile"]["medications"], [])
            self.assertEqual(baseline_body["baseline"]["item_scores"], [2] * 7)
            self.assertEqual(baseline_body["dataClass"], "REAL_WORLD_OUTCOME")
            followup_body = request.call_args_list[1].kwargs["body"]
            self.assertEqual(followup_body["answers"]["item_scores"], [1] * 7)
            self.assertEqual(followup_body["takenDoseCount"], 12)
            self.assertEqual(followup_body["adverseEvents"], [])
            self.assertEqual(request.call_count, 2)

    def test_operational_wizard_requires_confirmation_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            with self.assertRaisesRegex(ValueError, "복용 전 저장 확인"):
                console.confirm_operational_followup()
            with self.assertRaisesRegex(ValueError, "후속평가 저장 확인"):
                console.confirm_operational_pharmacist()

    def test_pharmacist_confirmation_finalizes_and_collects_production_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            wizard = console._load_operational_wizard()
            wizard["baseline"] = {
                "status": "completed", "execution_id": "exec_1", "plan_id": "plan_1"
            }
            wizard["followup"] = {"status": "completed"}
            console.operational_wizard_path.parent.mkdir(parents=True, exist_ok=True)
            console.operational_wizard_path.write_text(
                json.dumps(wizard, ensure_ascii=False), encoding="utf-8"
            )
            database = Path(temp) / "interim.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute(
                "create table ai_drafts (draft_id text, record_type text, rationale_json text, "
                "review_status text, reviewer_id text, reviewed_at text, created_at text)"
            )
            connection.execute(
                "insert into ai_drafts values (?, ?, ?, ?, ?, ?, ?)",
                (
                    "draft_" + "5" * 32,
                    "actual_recommendation_review",
                    json.dumps({"source_execution_id": "exec_1"}),
                    "approved",
                    "권혁찬",
                    "2026-07-24T06:00:00Z",
                    "2026-07-24T05:00:00Z",
                ),
            )
            connection.commit()
            connection.close()
            with (
                patch.object(console, "_operational_database_path", return_value=database),
                patch.object(console, "_production_state", return_value=True),
                patch.object(
                    console,
                    "_finalize_current_operational_capture",
                    return_value={"status": "completed", "covered_requirement_count": 41},
                ) as finalize,
                patch.object(console, "collect_operational_receipts") as collect,
            ):
                result = console.confirm_operational_pharmacist()
            finalize.assert_called_once_with()
            collect.assert_called_once_with(operator_id="웰니스박스")
            completed = result["completed_profiles"][0]
            self.assertEqual(completed["operational_receipt"]["covered_requirement_count"], 41)
            self.assertEqual(completed["pharmacist_review"]["reviewer_id"], "권혁찬")
            self.assertEqual(result["profile_index"], 1)
            self.assertEqual(result["prefill"]["profile_id"], "profile-02")

    def test_h007_page_uses_three_prefilled_confirmation_buttons(self) -> None:
        page = (ROOT / "scripts/run_final_session_console.py").read_text(encoding="utf-8")
        self.assertIn("복용 전 저장 확인", page)
        self.assertIn("후속평가 저장 확인", page)
        self.assertIn("약사 판정 저장 여부 확인", page)
        self.assertNotIn("웰니스박스 명의로 승인", page)
        self.assertIn("프로필입니다", page)
        self.assertIn('"operational_baseline": console.confirm_operational_baseline', page)

    def test_local_operational_session_uses_automatic_research_login(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            url = console.view_state()["operational_urls"]["user_session"]
            self.assertEqual(
                url,
                "http://127.0.0.1:3001/research-login?redirect=/tips",
            )
            self.assertEqual(
                console.view_state()["operational_urls"]["pharmacist_review"],
                "http://127.0.0.1:3001/research-login?redirect=/pharm/tips",
            )

    def test_final_audit_button_shows_immediate_progress_feedback(self) -> None:
        page = (ROOT / "scripts/run_final_session_console.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="auditButton"', page)
        self.assertIn('aria-live="polite"', page)
        self.assertIn("완료 상태를 확인하고 있습니다. 약 30초만 기다려 주세요.", page)
        self.assertIn("initialStepSelected", page)
        self.assertIn("1. 설문·추천·후속평가 시작", page)
        self.assertIn("로그인은 자동으로 처리됩니다.", page)
        self.assertIn("auditButton.disabled=true", page)
        self.assertIn("auditButton.disabled=false", page)

    def test_console_renders_one_step_wizard_with_next_only_navigation(self) -> None:
        page = (ROOT / "scripts/run_final_session_console.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("const stepIds=['H-001','H-002','H-003','H-004','H-005','H-006','H-007']", page)
        self.assertIn('button onclick="nextStep()">다음</button>', page)
        self.assertIn("이 단계의 확인 버튼을 먼저 눌러 주세요.", page)
        self.assertIn("currentStepIndex++;await load()", page)
        self.assertIn("$('finalAudit').style.display='block'", page)

    def test_normal_local_launcher_does_not_rewrite_canonical_evidence(self) -> None:
        launcher = (ROOT / "research-server-start.cmd").read_text(encoding="utf-8")
        self.assertIn("python scripts\\run_local_research_session.py", launcher)
        self.assertNotIn("--verify", launcher)

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

    def test_console_approves_all_policy_rules_as_wellnessbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            console.approve_all_policy_rules()
            self.assertEqual(console.state["steps"]["H-002"]["status"], "completed")
            ledger = json.loads(
                (Path(temp) / "session/policy_rule_reviews_v1.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(ledger["reviews"]), 9)
            self.assertEqual(
                {item["reviewer_id"] for item in ledger["reviews"].values()},
                {"웰니스박스"},
            )

    def test_console_confirms_empty_draft_queue_without_path_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "drafts.sqlite3"
            console = FinalSessionConsole(ROOT, state_root=root / "session")
            console.confirm_empty_draft_queue(str(database))
            self.assertEqual(console.state["steps"]["H-003"]["status"], "completed")
            cycle = json.loads(
                (root / "session/ai_draft_downstream_cycle_v1.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(cycle["training_consumed_count"], 0)
            self.assertEqual(cycle["evaluation_consumed_count"], 0)

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

    def test_external_validation_upload_uses_session_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(
                ROOT, state_root=Path(temp) / "session", simulation=True
            )
            console.register_external_validation_upload(
                {"data_class": "SIMULATION", "status": "PASS"}
            )
            registered = Path(console.state["steps"]["H-005"]["registered_path"])
            self.assertTrue(registered.is_file())
            self.assertTrue(registered.is_relative_to(Path(temp)))

    def test_external_review_package_requires_project_pharmacist_actual_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            console = FinalSessionConsole(ROOT, state_root=Path(temp) / "session")
            cases_path = ROOT / "data/original_plan/op039_external_review_cases_v1.json"
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
            document = {
                "schema_version": "op039_external_review_result_v1",
                "package_id": cases["package_id"],
                "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
                "reviewer": {
                    "name": "외부약사",
                    "organization": "독립약국",
                    "pharmacist_license_id": "license-actual-value",
                    "contact": "reviewer@example.test",
                    "reviewer_role": "project_pharmacist",
                    "relationship_to_project": "project_co_researcher",
                    "credential_verification_method": "license_document_checked",
                    "independent_of_implementation_team": False,
                    "was_ai_draft_reviewer": False,
                },
                "decisions": [
                    {"case_id": item["case_id"], "decision": "valid", "comment": ""}
                    for item in cases["cases"]
                ],
                "reviewed_at": "2026-07-23T06:00:00Z",
                "signature_name": "외부약사",
            }
            console.register_external_validation_upload(document)
            self.assertEqual(console.state["steps"]["H-005"]["status"], "completed")
            document["reviewer"]["name"] = "여형준"
            document["signature_name"] = "여형준"
            with self.assertRaises(ValueError):
                console.register_external_validation_upload(document)

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

    def test_operational_coverage_shows_current_session_as_provisional_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "etc/local_research_runtime"
            runtime.mkdir(parents=True)
            database = runtime / "interim.sqlite3"
            connection = sqlite3.connect(database)
            try:
                connection.execute("create table user_profiles(id text)")
                connection.execute("insert into user_profiles values ('actual-use')")
                connection.commit()
            finally:
                connection.close()
            (runtime / "operational_capture.json").write_text(
                json.dumps({"database_counts_before": {"user_profiles": 0}}),
                encoding="utf-8",
            )
            mapping = root / "data/original_plan/operational_action_coverage_v1.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "signals": {"profile_or_survey": ["user_profiles"], "completed_session": []},
                        "actions": {"profile_or_survey": ["OP-001"], "completed_session": ["OP-002"]},
                    }
                ),
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "groups": [
                            {
                                "default_required_stage": "OPERATED",
                                "requirements": [
                                    {"requirement_id": "OP-001", "claimed_stage": "IMPLEMENTED"},
                                    {"requirement_id": "OP-002", "claimed_stage": "IMPLEMENTED"},
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            console = FinalSessionConsole(ROOT, state_root=root / "session")
            console.root = root
            console.manifest_path = manifest
            summary = console.operational_coverage_summary()
            self.assertEqual(summary["covered_count"], 0)
            self.assertEqual(summary["current_session_provisional_count"], 2)

    def test_operations_keep_previously_registered_requirement_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            console = FinalSessionConsole(ROOT, state_root=temp_path / "session")
            manifest = temp_path / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "groups": [
                            {
                                "default_required_stage": "OPERATED",
                                "requirements": [
                                    {
                                        "requirement_id": "OP-001",
                                        "claimed_stage": "INTEGRATED",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            console.manifest_path = manifest
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

    def test_operational_signoffs_promote_without_external_validation(self) -> None:
        etc_root = ROOT / "etc"
        etc_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=etc_root) as temp:
            temp_path = Path(temp)
            console = FinalSessionConsole(ROOT, state_root=temp_path / "session")
            evidence = temp_path / "OP-001.json"
            evidence.write_text(
                json.dumps({"requirement_id": "OP-001", "status": "PASS"}),
                encoding="utf-8",
            )
            operations = console.state_root / "operational_environment_signoff_v1.json"
            operations.write_text("{}", encoding="utf-8")
            manifest = temp_path / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "groups": [
                            {
                                "default_required_stage": "OPERATED",
                                "requirements": [
                                    {
                                        "requirement_id": "OP-001",
                                        "claimed_stage": "INTEGRATED",
                                        "evidence": {},
                                    },
                                    {
                                        "requirement_id": "OP-039",
                                        "claimed_stage": "IMPLEMENTED",
                                        "required_stage": "EXTERNAL",
                                        "evidence": {},
                                    },
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            console.manifest_path = manifest
            console.state["steps"]["H-007"] = {
                "status": "completed",
                "registered_requirement_evidence": {"OP-001": str(evidence)},
            }

            console._register_operational_signoffs()

            updated = json.loads(manifest.read_text(encoding="utf-8"))
            requirements = updated["groups"][0]["requirements"]
            self.assertEqual(requirements[0]["claimed_stage"], "OPERATED")
            self.assertEqual(requirements[1]["claimed_stage"], "IMPLEMENTED")

    def test_uploaded_operations_are_classified_without_user_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            console = FinalSessionConsole(ROOT, state_root=temp_path / "session")
            manifest = temp_path / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "groups": [
                            {
                                "default_required_stage": "OPERATED",
                                "requirements": [
                                    {
                                        "requirement_id": "OP-001",
                                        "claimed_stage": "INTEGRATED",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            console.manifest_path = manifest
            requirement_id = console._stage_gap_ids()[0]
            console.record_uploaded_operations(
                "웰니스박스",
                [
                    {"check": "rnd_api", "status": "PASS"},
                    {"requirement_id": requirement_id, "status": "PASS"},
                ],
            )
            step = console.state["steps"]["H-007"]
            self.assertEqual(step["checks"]["rnd_api"]["status"], "PASS")
            self.assertIn(requirement_id, step["registered_requirement_evidence"])

    def test_console_html_has_automatic_draft_queue_and_structured_operations(self) -> None:
        html = (ROOT / "scripts/run_final_session_console.py").read_text(encoding="utf-8")
        self.assertIn("data.next_draft", html)
        self.assertIn("draftReviewerId", html)
        self.assertIn("const defaultActor='웰니스박스'", html)
        self.assertIn("policy_all", html)
        self.assertIn('id="draftDb" type="hidden"', html)
        self.assertIn("receipts_prepare", html)
        self.assertIn('id="externalFile" type="file"', html)
        self.assertIn("operations_collect", html)
        self.assertNotIn("`이번 실행에서 감지`", html)
        self.assertIn("op039-external-review-package.zip", html)
        self.assertIn("약사 전문가 검토 화면 열기", html)
        review_form = (
            ROOT / "data/original_plan/final_session/op039_external_reviewer_form.html"
        ).read_text(encoding="utf-8")
        self.assertIn('value="valid" checked', review_form)
        self.assertIn("AI 제안", review_form)
        self.assertIn("수정하거나 그대로 제출해야 등록", review_form)
        self.assertIn("기존 오너의 판정은 자기검토", review_form)
        self.assertIn('value="권혁찬"', review_form)
        self.assertNotIn('id="license"', review_form)
        self.assertNotIn('id="credential"', review_form)
        self.assertNotIn('id="email"', review_form)
        self.assertNotIn('id="independent"', review_form)
        self.assertNotIn('id="signature"', review_form)
        self.assertNotIn("운영 확인 JSON", html)
        self.assertNotIn("외부 평가 결과 JSON 경로", html)

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

    def test_prepare_receipts_creates_default_key_only_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            console = FinalSessionConsole(ROOT, state_root=root / "session")
            key_path = root / "session/signing.pem"
            with patch.object(
                console,
                "sign_receipts",
                return_value={"issuer_id": "웰니스박스"},
            ) as sign:
                console.prepare_and_sign_receipts(str(key_path))
                first_key = key_path.read_bytes()
                console.prepare_and_sign_receipts(str(key_path))
            self.assertEqual(key_path.read_bytes(), first_key)
            self.assertEqual(sign.call_count, 2)

    def test_prepare_receipts_registers_trust_before_production_resign(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            console = FinalSessionConsole(ROOT, state_root=root / "session")
            key_path = root / "session/signing.pem"
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text("existing-key", encoding="utf-8")
            receipt = {
                "issuer_id": "웰니스박스",
                "public_key_ed25519_base64": "public",
                "validation_receipt_path": str(root / "validation.json"),
                "independent_review_receipt_path": str(root / "review.json"),
            }
            events: list[str] = []

            def sign(**_: object) -> dict[str, str]:
                events.append("sign")
                return receipt

            def commit(_: list[Path], message: str) -> None:
                events.append(message)

            with (
                patch.object(console, "_production_state", return_value=True),
                patch.object(console, "sign_receipts", side_effect=sign),
                patch.object(
                    console,
                    "_register_receipt_policy",
                    return_value=root / "policy.json",
                ),
                patch.object(console, "_git_commit", side_effect=commit),
                patch.object(console, "run_final_audit", return_value={"status": "BLOCKED"}),
            ):
                console.prepare_and_sign_receipts(str(key_path))
            self.assertEqual(events[0], "sign")
            self.assertEqual(events[1], "docs: register final receipt trust policy")
            self.assertEqual(events[2], "sign")
            self.assertEqual(events[3], "docs: register final signed receipts")

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
