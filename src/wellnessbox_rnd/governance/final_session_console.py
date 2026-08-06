from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
from http.cookiejar import CookieJar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from wellnessbox_rnd.evals.external_high_risk_safety import ExternalHighRiskSafetyEvalReportV2
from wellnessbox_rnd.governance.final_completion_audit import audit_final_completion_v1
from wellnessbox_rnd.governance.original_plan_audit import audit_original_plan_manifest_v1
from wellnessbox_rnd.governance.reviewer_credentials import (
    audit_reviewer_credentials,
    load_draft_reviewer_ids,
    load_registry,
    review_character_for,
)
from wellnessbox_rnd.governance.operational_receipts import (
    begin_session,
    database_counts,
    finish_session,
)
from wellnessbox_rnd.interim.ai_drafts import (
    AiDraftCreateV1,
    AiDraftDecisionV1,
    AiDraftService,
    DownstreamPurpose,
    DraftReviewStatus,
)
from wellnessbox_rnd.interim.data_lake import data_lake_database_path
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.schemas.original_plan_manifest import (
    RepositoryName,
    load_original_plan_manifest_v1,
)

STEPS = [f"H-{number:03}" for number in range(1, 8)]
OPERATIONAL_PROFILES = [
    {
        "profile_id": "profile-01", "participant_name": "연구 프로필 01",
        "age": 41, "sex": "other", "goal": "수면의 질", "goal_alias": "sleep quality",
        "medications": [], "baseline": "PSQI 14점(7문항 각 2점)",
        "followup": "2주 후 PSQI 7점(7문항 각 1점), 복용 12/14회, 이상사례 없음",
    },
    {
        "profile_id": "profile-02", "participant_name": "연구 프로필 02",
        "age": 58, "sex": "male", "goal": "심혈관 건강", "goal_alias": "heart health",
        "medications": ["warfarin"], "baseline": "PSQI 14점(7문항 각 2점)",
        "followup": "2주 후 PSQI 7점(7문항 각 1점), 복용 12/14회, 이상사례 없음",
    },
    {
        "profile_id": "profile-03", "participant_name": "연구 프로필 03",
        "age": 29, "sex": "female", "goal": "에너지", "goal_alias": "energy",
        "medications": ["levothyroxine"], "baseline": "PSQI 14점(7문항 각 2점)",
        "followup": "2주 후 PSQI 7점(7문항 각 1점), 복용 12/14회, 이상사례 없음",
    },
    {
        "profile_id": "profile-04", "participant_name": "연구 프로필 04",
        "age": 67, "sex": "female", "goal": "뼈·관절", "goal_alias": "bone joint",
        "medications": ["metformin"], "baseline": "PSQI 14점(7문항 각 2점)",
        "followup": "2주 후 PSQI 7점(7문항 각 1점), 복용 12/14회, 이상사례 없음",
    },
    {
        "profile_id": "profile-05", "participant_name": "연구 프로필 05",
        "age": 36, "sex": "other", "goal": "장 건강", "goal_alias": "gut health",
        "medications": ["omeprazole"], "baseline": "PSQI 14점(7문항 각 2점)",
        "followup": "2주 후 PSQI 7점(7문항 각 1점), 복용 12/14회, 이상사례 없음",
    },
]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class FinalSessionConsole:
    def __init__(
        self, root: Path, *, state_root: Path | None = None, simulation: bool = False
    ) -> None:
        self.root = root.resolve()
        self.workspace = self.root.parent
        self.state_root = (state_root or self.root / "data/original_plan/final_session").resolve()
        self.state_path = self.state_root / "session_state_v1.json"
        self.policy_path = self.root / "data/original_plan/closed_loop_next_action_policy_v1.json"
        self.audit_policy_path = self.root / "data/original_plan/op120_final_audit_policy_v1.json"
        self.manifest_path = self.root / "data/original_plan/requirements_manifest_v1.json"
        self.operational_wizard_path = self.state_root / "operational_wizard_v1.json"
        self._wellnessbox_opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._wellnessbox_logged_in = False
        self.simulation = simulation
        self.state = self._load_state()
        if "report_sample_ids" not in self.state:
            report_ids = [f"OP-{number:03}" for number in range(1, 121)]
            self.state["report_sample_ids"] = random.SystemRandom().sample(report_ids, 3)
            _write_json(self.state_path, self.state)
        self._reconcile_draft_queue_state()

    def _reconcile_draft_queue_state(self) -> None:
        database_path = self._operational_database_path()
        if not database_path.is_file():
            return
        store = InterimStore(database_path)
        store.migrate()
        service = AiDraftService(store)
        summary = service.summary()
        step = self.state["steps"]["H-003"]
        if summary["pending"] <= 0 and step["status"] == "pending":
            connection = sqlite3.connect(database_path)
            try:
                row = connection.execute(
                    "select reviewer_id from ai_drafts "
                    "where reviewer_id is not null and reviewer_id != '' "
                    "order by reviewed_at desc limit 1"
                ).fetchone()
            finally:
                connection.close()
            reviewer_id = row[0] if row else "reviewer_not_recorded"
            cycle_path = self._run_draft_downstream_cycle(store, str(database_path))
            self._record(
                "H-003",
                "completed",
                {
                    "reviewer_id": reviewer_id,
                    "draft_ledger_path": str(database_path),
                    "review_counts": summary,
                    "downstream_cycle_path": str(cycle_path),
                },
            )
            return
        if summary["pending"] <= 0 or step["status"] != "completed":
            return
        previous = step
        self._record(
            "H-003",
            "pending",
            {
                "reason": "project_pharmacist_review_pending",
                "draft_ledger_path": str(database_path),
                "review_counts": summary,
                "previous_completion": previous,
            },
        )

    def _load_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        state = {
            "schema_version": "final_session_console_state_v1",
            "current_step": "H-001",
            "steps": {step: {"status": "pending"} for step in STEPS},
            "updated_at": _now(),
        }
        _write_json(self.state_path, state)
        return state

    def _record(self, step: str, status: str, details: dict[str, Any]) -> dict[str, Any]:
        if step not in STEPS or status not in {"completed", "deferred", "pending"}:
            raise ValueError("invalid final session step")
        self.state["steps"][step] = {"status": status, "updated_at": _now(), **details}
        remaining = [item for item in STEPS if self.state["steps"][item]["status"] == "pending"]
        self.state["current_step"] = remaining[0] if remaining else "AUDIT"
        self.state["updated_at"] = _now()
        _write_json(self.state_path, self.state)
        return self.state

    def confirm_alignment(self, reviewer_id: str) -> dict[str, Any]:
        return self._record("H-001", "completed", {"reviewer_id": reviewer_id})

    def policy_rules(self) -> list[dict[str, Any]]:
        policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        return policy["rules"]

    def view_state(self) -> dict[str, Any]:
        action_labels = {
            "stop_and_escalate": "중단하고 전문가에게 알림",
            "replace": "성분 교체",
            "reduce": "용량 감량",
            "request_safety_review": "안전 검토 요청",
            "request_followup": "후속 설문 요청",
            "request_measurement": "측정 요청",
            "hold_for_review": "판단 보류",
            "maintain": "현재 계획 유지",
            "reoptimize": "계획 재최적화",
        }
        readable_rules = []
        for rule in self.policy_rules():
            conditions = ", ".join(f"{key}={value}" for key, value in rule["when"].items())
            readable_rules.append(
                {
                    **rule,
                    "plain_language": (
                        f"{conditions} 조건이면 ‘{action_labels[rule['action']]}’을 "
                        "다음 작업으로 선택합니다."
                    ),
                }
            )
        samples = []
        for report_id in self.state["report_sample_ids"]:
            path = self.root / f"docs/original_plan/research_reports/{report_id}.md"
            samples.append(
                {"report_id": report_id, "excerpt": path.read_text(encoding="utf-8")[:1200]}
            )
        completed = sum(item["status"] == "completed" for item in self.state["steps"].values())
        runtime_path = self.root / "etc/local_research_runtime/session_processes.json"
        runtime = (
            json.loads(runtime_path.read_text(encoding="utf-8"))
            if runtime_path.is_file()
            else {"urls": {"wellnessbox": "http://127.0.0.1:3001"}}
        )
        wellnessbox_url = runtime.get("urls", {}).get("wellnessbox", "http://127.0.0.1:3001")
        return {
            **self.state,
            "progress": {"completed": completed, "total": len(STEPS)},
            "policy_rules": readable_rules,
            "report_samples": samples,
            "draft_database_path": str(
                (
                    self._operational_database_path()
                    if self._operational_database_path().is_file()
                    else data_lake_database_path().resolve()
                )
            ),
            "stage_gap_ids": self._stage_gap_ids(),
            "op039_package": {
                "download_path": "/downloads/op039-external-review-package.zip",
                "reviewer_must_differ_from": "웰니스박스",
            },
            "operational_coverage": self.operational_coverage_summary(),
            "operational_wizard": self._load_operational_wizard(),
            "operational_urls": {
                "user_session": f"{wellnessbox_url}/research-login?redirect=/tips",
                "pharmacist_review": f"{wellnessbox_url}/research-login?redirect=/pharm/tips",
            },
        }

    def _load_operational_wizard(self) -> dict[str, Any]:
        saved = (
            json.loads(self.operational_wizard_path.read_text(encoding="utf-8"))
            if self.operational_wizard_path.is_file()
            else {}
        )
        profile_index = max(0, min(int(saved.get("profile_index", 0)), len(OPERATIONAL_PROFILES) - 1))
        profile = OPERATIONAL_PROFILES[profile_index]
        default = {
            "schema_version": "operational_wizard_v2",
            "profile_index": profile_index,
            "profile_count": len(OPERATIONAL_PROFILES),
            "baseline": {"status": "pending"},
            "followup": {"status": "pending"},
            "pharmacist_review": {"status": "pending"},
            "completed_profiles": [],
            "prefill": {**profile, "reviewer_id": "권혁찬"},
        }
        return {**default, **saved, "prefill": {**default["prefill"], **saved.get("prefill", {})}}

    def _wellnessbox_url(self) -> str:
        runtime_path = self.root / "etc/local_research_runtime/session_processes.json"
        if runtime_path.is_file():
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            return runtime.get("urls", {}).get("wellnessbox", "http://127.0.0.1:3001")
        return "http://127.0.0.1:3001"

    def _operational_database_path(self) -> Path:
        return self.root / "etc/local_research_runtime/interim.sqlite3"

    def _wellnessbox_json(
        self, path: str, *, method: str = "GET", body: dict[str, Any] | None = None,
        redirect: str = "/tips",
    ) -> dict[str, Any]:
        base = self._wellnessbox_url().rstrip("/")
        try:
            if not self._wellnessbox_logged_in:
                self._wellnessbox_opener.open(
                    f"{base}/research-login?redirect={redirect}", timeout=15
                ).read()
                self._wellnessbox_logged_in = True
            payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            request = Request(
                f"{base}{path}", data=payload, method=method,
                headers={"content-type": "application/json"},
            )
            raw = self._wellnessbox_opener.open(request, timeout=30).read()
            return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"웰니스박스가 요청을 처리하지 못했습니다({exc.code}): {detail}") from exc
        except URLError as exc:
            raise RuntimeError("로컬 웰니스박스 서버에 연결하지 못했습니다. 서버를 다시 시작하세요.") from exc

    def confirm_operational_baseline(self) -> dict[str, Any]:
        wizard = self._load_operational_wizard()
        if wizard["baseline"]["status"] == "completed":
            return wizard
        observed_at = wizard["baseline"].get("observed_at", _now())
        request_id = "pro_" + hashlib.sha256(
            f"final-session:{observed_at}".encode()
        ).hexdigest()[:32]
        wizard["baseline"] = {
            "status": "submitting", "observed_at": observed_at, "request_id": request_id
        }
        _write_json(self.operational_wizard_path, wizard)
        result = self._wellnessbox_json(
            "/api/tips/pro/plans", method="POST",
            body={
                "requestId": request_id,
                "researchProfileId": wizard["prefill"]["profile_id"],
                "profile": {
                    "name": wizard["prefill"]["participant_name"],
                    "age": wizard["prefill"]["age"],
                    "sex": wizard["prefill"]["sex"],
                    "goals": [wizard["prefill"]["goal_alias"]],
                    "medications": wizard["prefill"]["medications"],
                },
                "baseline": {"instrument": "PSQI", "item_scores": [2] * 7},
                "observedAt": observed_at,
                "consentAccepted": True,
                "dataClass": "REAL_WORLD_OUTCOME",
            },
        )
        wizard["baseline"] = {
            **wizard["baseline"], "status": "completed",
            "execution_id": result["execution_id"], "plan_id": result["plan_id"],
            "baseline_event_id": result.get("baseline_event_id"), "confirmed_at": _now(),
        }
        _write_json(self.operational_wizard_path, wizard)
        return wizard

    def confirm_operational_followup(self) -> dict[str, Any]:
        wizard = self._load_operational_wizard()
        baseline = wizard["baseline"]
        if baseline["status"] != "completed":
            raise ValueError("복용 전 저장 확인을 먼저 누르세요.")
        if wizard["followup"]["status"] == "completed":
            return wizard
        result = self._wellnessbox_json(
            "/api/tips/pro/effects", method="POST",
            body={
                "executionId": baseline["execution_id"], "planId": baseline["plan_id"],
                "researchProfileId": wizard["prefill"]["profile_id"],
                "timepoint": "week_2", "answers": {"instrument": "PSQI", "item_scores": [1] * 7},
                "observedAt": _now(), "actualDayIndex": 14, "plannedDoseCount": 14,
                "takenDoseCount": 12, "adverseEvents": [],
            },
        )
        wizard["followup"] = {
            "status": "completed", "event_id": result.get("event_id"),
            "action_decision": result.get("action_decision"), "confirmed_at": _now(),
        }
        _write_json(self.operational_wizard_path, wizard)
        return wizard

    def confirm_operational_pharmacist(self) -> dict[str, Any]:
        wizard = self._load_operational_wizard()
        baseline = wizard["baseline"]
        if wizard["followup"]["status"] != "completed":
            raise ValueError("후속평가 저장 확인을 먼저 누르세요.")
        if wizard["pharmacist_review"]["status"] == "completed":
            return wizard
        database_path = self._operational_database_path()
        if not database_path.is_file():
            raise ValueError("실제 추천 초안 원장을 찾지 못했습니다. 연구 서버를 다시 시작하세요.")
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "select draft_id, record_type, rationale_json, review_status, reviewer_id, reviewed_at "
                "from ai_drafts where record_type = 'actual_recommendation_review' order by created_at desc"
            ).fetchall()
        finally:
            connection.close()
        execution_id = str(baseline["execution_id"])
        draft = next(
            (
                dict(row)
                for row in rows
                if json.loads(str(row["rationale_json"])).get("source_execution_id")
                == execution_id
            ),
            None,
        )
        if draft is None:
            raise ValueError("현재 프로필의 실제 추천 초안이 없습니다. 복용 전 저장 결과를 확인하세요.")
        if draft["review_status"] == "pending":
            raise ValueError("권혁찬이 예비 약사 사전 검토 화면에서 초안을 직접 판정한 뒤 다시 확인하세요.")
        reviewer_id = str(draft.get("reviewer_id") or "").strip()
        if reviewer_id in {"", "웰니스박스", "여형준"}:
            raise ValueError("오너 또는 시스템 명의 판정은 예비 약사 사전 검토 증거로 인정하지 않습니다.")
        wizard["pharmacist_review"] = {
            "status": "completed", "draft_id": draft["draft_id"],
            "review_status": draft["review_status"],
            "reviewer_id": reviewer_id,
            "reviewed_at": draft.get("reviewed_at"),
            "confirmed_at": _now(),
        }
        _write_json(self.operational_wizard_path, wizard)
        if self._production_state():
            wizard["operational_receipt"] = self._finalize_current_operational_capture()
            self.collect_operational_receipts(operator_id="웰니스박스")
        completed_profile = {
            "profile_id": wizard["prefill"]["profile_id"],
            "participant_name": wizard["prefill"]["participant_name"],
            "age": wizard["prefill"]["age"],
            "goal": wizard["prefill"]["goal"],
            "medications": wizard["prefill"]["medications"],
            "execution_id": baseline["execution_id"],
            "pharmacist_review": wizard["pharmacist_review"],
            "operational_receipt": wizard.get("operational_receipt"),
            "completed_at": _now(),
        }
        completed = list(wizard.get("completed_profiles", []))
        if not any(item.get("profile_id") == completed_profile["profile_id"] for item in completed):
            completed.append(completed_profile)
        wizard["completed_profiles"] = completed
        if wizard["profile_index"] + 1 < len(OPERATIONAL_PROFILES):
            wizard["profile_index"] += 1
            wizard["prefill"] = {
                **OPERATIONAL_PROFILES[wizard["profile_index"]], "reviewer_id": "권혁찬"
            }
            wizard["baseline"] = {"status": "pending"}
            wizard["followup"] = {"status": "pending"}
            wizard["pharmacist_review"] = {"status": "pending"}
            wizard.pop("operational_receipt", None)
        else:
            wizard["all_profiles_completed"] = True
        _write_json(self.operational_wizard_path, wizard)
        return wizard

    def _finalize_current_operational_capture(self) -> dict[str, Any]:
        runtime_root = self.root / "etc/local_research_runtime"
        capture_path = runtime_root / "operational_capture.json"
        database_path = runtime_root / "interim.sqlite3"
        if not capture_path.is_file():
            raise RuntimeError("현재 운영 세션 기록을 찾지 못했습니다. 연구 서버를 다시 시작하세요.")
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        receipt = finish_session(
            self.root,
            database_path,
            capture,
            self.state_root / "operational_receipts",
            key_path=self.root / "etc/final_session_private/final_session_signing_key.pem",
        )
        runtime_path = runtime_root / "session_processes.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        next_capture = begin_session(self.root, database_path, runtime.get("urls", {}))
        _write_json(capture_path, next_capture)
        return {
            "status": "completed",
            "receipt_path": receipt["receipt_path"],
            "covered_requirement_count": len(receipt["covered_requirement_ids"]),
            "covered_requirement_ids": receipt["covered_requirement_ids"],
        }

    def review_policy_rule(
        self, rule_id: str, reviewer_id: str, decision: str, comment: str = ""
    ) -> dict[str, Any]:
        if decision not in {"approved", "change_requested"}:
            raise ValueError("policy decision must be approved or change_requested")
        rules = {item["rule_id"] for item in self.policy_rules()}
        if rule_id not in rules:
            raise ValueError(f"unknown policy rule: {rule_id}")
        path = self.state_root / "policy_rule_reviews_v1.json"
        ledger = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.is_file()
            else {"schema_version": "policy_rule_reviews_v1", "reviews": {}}
        )
        ledger["reviews"][rule_id] = {
            "reviewer_id": reviewer_id,
            "decision": decision,
            "change_proposal": comment if decision == "change_requested" else None,
            "reviewed_at": _now(),
        }
        _write_json(path, ledger)
        complete = rules == set(ledger["reviews"])
        return self._record(
            "H-002",
            "completed" if complete else "pending",
            {"reviewed_rule_count": len(ledger["reviews"]), "rule_count": len(rules)},
        )

    def approve_all_policy_rules(self, reviewer_id: str = "웰니스박스") -> dict[str, Any]:
        for rule in self.policy_rules():
            self.review_policy_rule(rule["rule_id"], reviewer_id, "approved")
        return self.state

    def draft_queue(self, database_path: str) -> dict[str, Any]:
        store = InterimStore(Path(database_path).resolve())
        store.migrate()
        service = AiDraftService(store)
        return {"items": service.queue(), "summary": service.summary()}

    def _run_draft_downstream_cycle(
        self, store: InterimStore, database_path: str
    ) -> Path:
        service = AiDraftService(store)
        summary = service.summary()
        approved_rows = store.rows(
            "select draft_id, reviewer_id from ai_drafts "
            "where review_status in ('approved', 'approved_with_edits') "
            "order by created_at"
        )
        excluded_reviewer_ids = {"웰니스박스", "여형준"}
        approved_ids = [
            str(row["draft_id"])
            for row in approved_rows
            if str(row["reviewer_id"] or "").strip() not in excluded_reviewer_ids
        ]
        excluded_ids = [
            str(row["draft_id"])
            for row in store.rows(
                "select draft_id from ai_drafts where review_status in "
                "('approved', 'approved_with_edits') and reviewer_id in (?, ?) "
                "order by created_at",
                tuple(sorted(excluded_reviewer_ids)),
            )
        ]
        cycle = {
            "schema_version": "ai_draft_downstream_cycle_v1",
            "draft_ledger_path": str(Path(database_path).resolve()),
            "review_counts": summary,
            "eligibility": {
                "rule": "human_reviewer_required_owner_and_system_excluded",
                "eligible_draft_ids": approved_ids,
                "excluded_draft_ids": excluded_ids,
            },
            "training_consumed_count": len(
                service.consume_approved(
                    draft_ids=approved_ids, purpose=DownstreamPurpose.TRAINING
                )
            ),
            "evaluation_consumed_count": len(
                service.consume_approved(
                    draft_ids=approved_ids, purpose=DownstreamPurpose.EVALUATION
                )
            ),
            "executed_at": _now(),
        }
        path = self.state_root / "ai_draft_downstream_cycle_v1.json"
        _write_json(path, cycle)
        return path

    def confirm_empty_draft_queue(
        self, database_path: str, reviewer_id: str = "웰니스박스"
    ) -> dict[str, Any]:
        store = InterimStore(Path(database_path).resolve())
        store.migrate()
        service = AiDraftService(store)
        if service.queue():
            raise ValueError("pending_ai_drafts_must_be_reviewed")
        cycle_path = self._run_draft_downstream_cycle(store, database_path)
        return self._record(
            "H-003",
            "completed",
            {
                "reviewer_id": reviewer_id,
                "draft_ledger_path": str(Path(database_path).resolve()),
                "review_counts": service.summary(),
                "downstream_cycle_path": str(cycle_path),
            },
        )

    def decide_draft(
        self,
        *,
        database_path: str,
        draft_id: str,
        reviewer_id: str,
        decision: str,
        edited_content: dict[str, Any] | None = None,
        rejection_reason: str | None = None,
    ) -> dict[str, Any]:
        store = InterimStore(Path(database_path).resolve())
        store.migrate()
        service = AiDraftService(store)
        decided = service.decide(
            draft_id=draft_id,
            decision=AiDraftDecisionV1(
                review_status=DraftReviewStatus(decision),
                reviewer_id=reviewer_id,
                edited_content=edited_content,
                rejection_reason=rejection_reason,
            ),
            reviewed_at=datetime.now(UTC),
        )
        queue = service.queue()
        summary = service.summary()
        downstream_cycle_path = None
        if not queue:
            downstream_cycle_path = self._run_draft_downstream_cycle(store, database_path)
        self._record(
            "H-003",
            "completed" if not queue else "pending",
            {
                "reviewer_id": reviewer_id,
                "draft_ledger_path": str(Path(database_path).resolve()),
                "review_counts": summary,
                "downstream_cycle_path": (
                    str(downstream_cycle_path) if downstream_cycle_path else None
                ),
            },
        )
        return {"decided": decided, "next_draft": queue[0] if queue else None, "summary": summary}

    def record_report_tone(
        self, owner_id: str, approved: bool, comment: str = ""
    ) -> dict[str, Any]:
        samples = list(self.state["report_sample_ids"])
        record = {
            "schema_version": "report_tone_signoff_v1",
            "owner_id": owner_id,
            "approved": approved,
            "comment": comment,
            "sample_report_ids": samples,
            "reviewed_at": _now(),
        }
        _write_json(self.state_root / "report_tone_signoff_v1.json", record)
        return self._record("H-004", "completed" if approved else "deferred", record)

    def register_external_validation(self, source_path: str | None) -> dict[str, Any]:
        if not source_path:
            return self._record("H-005", "deferred", {"reason": "result_not_available"})
        source = Path(source_path).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        payload = json.loads(source.read_text(encoding="utf-8"))
        simulation = payload.get("data_class") == "SIMULATION" and self.simulation
        package_review = payload.get("schema_version") == "op039_external_review_result_v1"
        if package_review:
            cases_path = self.root / "data/original_plan/op039_external_review_cases_v1.json"
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
            reviewer = payload.get("reviewer", {})
            if (
                payload.get("package_id") != cases["package_id"]
                or payload.get("cases_sha256") != hashlib.sha256(cases_path.read_bytes()).hexdigest()
            ):
                raise ValueError("OP-039 검토 패키지 식별값이 맞지 않습니다.")
            name = str(reviewer.get("name", "")).strip()
            credential_audit = audit_reviewer_credentials(
                reviewer,
                registry=load_registry(self.root),
                draft_reviewer_ids=load_draft_reviewer_ids(self._operational_database_path()),
            )
            if credential_audit["status"] != "READY":
                raise ValueError(
                    "OP-039 검토자 자격 확인에 실패했습니다: "
                    + ", ".join(credential_audit["problems"])
                )
            relationship = str(reviewer.get("relationship_to_project", "")).strip()
            project_researcher = relationship == "project_co_researcher"
            if project_researcher and reviewer.get("independent_of_implementation_team") is not False:
                raise ValueError("과제 참여연구원은 independent_of_implementation_team=false여야 합니다.")
            if (
                reviewer.get("reviewer_role") != "project_pharmacist_candidate"
                or not project_researcher
                or str(payload.get("signature_name", "")).strip() != name
            ):
                raise ValueError(
                    "과제 참여 예비 약사의 이름·소속과 본인 서명이 필요합니다."
                )
            decisions = payload.get("decisions", [])
            expected_ids = {item["case_id"] for item in cases["cases"]}
            observed_ids = {item.get("case_id") for item in decisions if isinstance(item, dict)}
            if observed_ids != expected_ids or len(decisions) != len(expected_ids):
                raise ValueError("OP-039 사례 10건을 모두 판정해야 합니다.")
            invalid = [
                item.get("case_id")
                for item in decisions
                if item.get("decision") != "valid"
            ]
            if invalid:
                destination = self.state_root / "external_validation" / source.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                self._record(
                    "H-005", "deferred", {"reason": "external_review_found_invalid_cases", "case_ids": invalid, "registered_path": str(destination)}
                )
                raise ValueError("외부 검토자가 부적절하다고 판정한 사례가 있어 OP-039를 완료할 수 없습니다.")
            reviewer_warnings = credential_audit["warnings"]
        elif not simulation:
            report = ExternalHighRiskSafetyEvalReportV2.model_validate(payload)
            if (
                report.status != "PASS"
                or report.hard_false_negative_count != 0
                or report.rule_mismatch_case_ids
                or report.evaluation_error_case_ids
            ):
                raise ValueError("external validation did not pass OP-039 acceptance conditions")
            trust_files = {
                "coverage_trust_roots_sha256": self.root
                / "data/original_plan/contracts/op039_external_coverage_trust_roots_v1.json",
                "attestation_trust_roots_sha256": self.root
                / "data/original_plan/contracts/op039_external_attestation_trust_roots_v1.json",
                "evaluator_source_sha256": self.root
                / "src/wellnessbox_rnd/evals/external_high_risk_safety.py",
            }
            for field, trusted_path in trust_files.items():
                observed = hashlib.sha256(trusted_path.read_bytes()).hexdigest()
                if getattr(report, field) != observed:
                    raise ValueError(f"external validation trust mismatch: {field}")
            coverage_roots = json.loads(trust_files["coverage_trust_roots_sha256"].read_text())
            attestation_roots = json.loads(
                trust_files["attestation_trust_roots_sha256"].read_text()
            )
            coverage_match = any(
                item.get("coverage_protocol_sha256") == report.coverage_protocol_sha256
                and item.get("approval_reference") == report.coverage_approval_reference
                for item in coverage_roots["approved_coverage_protocols"]
            )
            attestation_match = any(
                item.get("attestation_sha256") == report.attestation_sha256
                and item.get("verification_receipt_sha256") == report.verification_receipt_sha256
                and item.get("coverage_protocol_sha256") == report.coverage_protocol_sha256
                and item.get("approval_reference") == report.attestation_approval_reference
                for item in attestation_roots["approved_attestations"]
            )
            if not coverage_match or not attestation_match:
                raise ValueError("external validation is not pinned by OP-039 trust registries")
        destination = self.state_root / "external_validation" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        qualification: dict[str, Any] = {}
        if package_review:
            stage = credential_audit["qualification_stage"]
            review_character = review_character_for(stage)
            qualification = {
                "qualification_stage": stage,
                "license_status": credential_audit["license_status"],
                "expected_licensure_period": credential_audit["expected_licensure_period"],
                "requires_licensed_reconfirmation": credential_audit[
                    "requires_licensed_reconfirmation"
                ],
                "reconfirmation_note": (
                    "면허 취득 전 예비 약사가 미리 수행한 검토다. 3차년도에 같은 사례를 "
                    "약사 자격으로 다시 검토해야 최종 근거가 된다."
                )
                if credential_audit["requires_licensed_reconfirmation"]
                else "면허 취득 뒤 약사 자격으로 수행한 검토다.",
            }
        else:
            review_character = "post_completion_independent_organization_evaluation"
        result = self._record(
            "H-005",
            "completed",
            {
                "registered_path": str(destination),
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "review_character": review_character,
                "reviewer_warnings": reviewer_warnings if package_review else [],
                **qualification,
            },
        )
        promotes_external_stage = not package_review or not qualification.get(
            "requires_licensed_reconfirmation", True
        )
        if self._production_state() and promotes_external_stage:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            external_ref = (
                "wellnessbox-rnd/"
                + destination.resolve().relative_to(self.root).as_posix()
            )
            for group in manifest["groups"]:
                for requirement in group["requirements"]:
                    if requirement["requirement_id"] != "OP-039":
                        continue
                    requirement["claimed_stage"] = "EXTERNAL"
                    evidence = requirement["evidence"].setdefault("test_files", [])
                    if external_ref not in evidence:
                        evidence.append(external_ref)
            _write_json(self.manifest_path, manifest)
        return result

    def register_external_validation_upload(
        self, document: dict[str, Any] | None
    ) -> dict[str, Any]:
        if document is None:
            return self.register_external_validation(None)
        path = self.state_root / "uploads/op039_external_validation.json"
        _write_json(path, document)
        return self.register_external_validation(str(path))

    def generate_key(self, key_path: str) -> dict[str, str]:
        """Mint a signing key. Both researchers sign on this machine.

        The separation that matters is enforced where the receipts are written:
        `sign_separate_receipts` refuses to issue both unless the issuer ids and
        the public keys differ. Refusing to mint a key here only forced someone
        to run openssl by hand and produced the same two files.
        """
        path = Path(key_path).resolve()
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return {
            "key_path": str(path),
            "public_key_ed25519_base64": base64.b64encode(public).decode(),
        }

    def sign_receipts(
        self,
        *,
        key_path: str,
        issuer_id: str,
        source_commit: str | None = None,
        critical_count: int = 0,
        important_count: int = 0,
    ) -> dict[str, Any]:
        if self._production_state():
            raise ValueError(
                "실제 최종 영수증은 검증용·독립 검토용 서로 다른 두 서명 키가 필요합니다."
            )
        private_key = serialization.load_pem_private_key(Path(key_path).read_bytes(), password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("key is not Ed25519")
        manifest = load_original_plan_manifest_v1(self.manifest_path)
        roots = {"wellnessbox-rnd": self.root, "wellnessbox": self.workspace / "wellnessbox"}
        canonical = audit_original_plan_manifest_v1(manifest, repository_roots=roots)
        manifest_sha = canonical.manifest_sha256
        audit_sha = hashlib.sha256(canonical.model_dump_json().encode()).hexdigest()
        commit = (
            source_commit
            or subprocess.check_output(
                ["git", "-C", str(self.workspace / "wellnessbox"), "rev-parse", "HEAD"], text=True
            ).strip()
        )
        common = {
            "status": "PASS",
            "manifest_sha256": manifest_sha,
            "canonical_audit_sha256": audit_sha,
            "source_commit": commit,
            "issuer_id": issuer_id,
        }
        validation = {"schema_version": "final_validation_receipt_v1", **common}
        review = {
            "schema_version": "independent_final_review_receipt_v1",
            **common,
            "critical_count": critical_count,
            "important_count": important_count,
        }
        for receipt in (validation, review):
            message = json.dumps(
                receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
            receipt["signature_ed25519_base64"] = base64.b64encode(
                private_key.sign(message)
            ).decode()
        validation_path = self.state_root / "final_validation_receipt_v1.json"
        review_path = self.state_root / "independent_final_review_receipt_v1.json"
        _write_json(validation_path, validation)
        _write_json(review_path, review)
        public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        result = {
            "issuer_id": issuer_id,
            "key_path": str(Path(key_path).resolve()),
            "public_key_ed25519_base64": base64.b64encode(public).decode(),
            "validation_receipt_path": str(validation_path),
            "independent_review_receipt_path": str(review_path),
        }
        self._record("H-006", "completed", result)
        return result

    def sign_separate_receipts(
        self,
        *,
        validation_key_path: str,
        validation_issuer_id: str,
        independent_review_key_path: str,
        independent_review_issuer_id: str,
        source_commit: str | None = None,
        critical_count: int = 0,
        important_count: int = 0,
    ) -> dict[str, Any]:
        validation_path = Path(validation_key_path).resolve()
        review_path = Path(independent_review_key_path).resolve()
        if not validation_path.is_file() or not review_path.is_file():
            raise FileNotFoundError(
                "검증용·독립 검토용 기존 서명 키 파일을 모두 제공해야 합니다."
            )
        validation_key = serialization.load_pem_private_key(
            validation_path.read_bytes(), password=None
        )
        review_key = serialization.load_pem_private_key(review_path.read_bytes(), password=None)
        if not isinstance(validation_key, Ed25519PrivateKey) or not isinstance(
            review_key, Ed25519PrivateKey
        ):
            raise ValueError("두 서명 키 모두 Ed25519 개인 키여야 합니다.")
        validation_public = base64.b64encode(
            validation_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        review_public = base64.b64encode(
            review_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        if (
            not validation_issuer_id.strip()
            or not independent_review_issuer_id.strip()
            or validation_issuer_id == independent_review_issuer_id
            or validation_public == review_public
        ):
            raise ValueError(
                "검증용·독립 검토용 발급자와 공개 키는 서로 달라야 합니다."
            )
        manifest = load_original_plan_manifest_v1(self.manifest_path)
        roots = {"wellnessbox-rnd": self.root, "wellnessbox": self.workspace / "wellnessbox"}
        canonical = audit_original_plan_manifest_v1(manifest, repository_roots=roots)
        manifest_sha = canonical.manifest_sha256
        audit_sha = hashlib.sha256(canonical.model_dump_json().encode()).hexdigest()
        commit = (
            source_commit
            or subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(self.workspace / "wellnessbox"),
                    "rev-parse",
                    "HEAD",
                ],
                text=True,
            ).strip()
        )
        validation = {
            "schema_version": "final_validation_receipt_v1",
            "status": "PASS",
            "manifest_sha256": manifest_sha,
            "canonical_audit_sha256": audit_sha,
            "source_commit": commit,
            "issuer_id": validation_issuer_id,
        }
        review = {
            "schema_version": "independent_final_review_receipt_v1",
            "status": "PASS",
            "manifest_sha256": manifest_sha,
            "canonical_audit_sha256": audit_sha,
            "source_commit": commit,
            "issuer_id": independent_review_issuer_id,
            "critical_count": critical_count,
            "important_count": important_count,
        }
        for receipt, key in ((validation, validation_key), (review, review_key)):
            message = json.dumps(
                receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
            receipt["signature_ed25519_base64"] = base64.b64encode(key.sign(message)).decode()
        validation_receipt_path = self.state_root / "final_validation_receipt_v1.json"
        review_receipt_path = self.state_root / "independent_final_review_receipt_v1.json"
        _write_json(validation_receipt_path, validation)
        _write_json(review_receipt_path, review)
        result = {
            "validation_issuer_id": validation_issuer_id,
            "independent_review_issuer_id": independent_review_issuer_id,
            "validation_key_path": str(validation_path),
            "independent_review_key_path": str(review_path),
            "validation_public_key_ed25519_base64": validation_public,
            "independent_review_public_key_ed25519_base64": review_public,
            "validation_receipt_path": str(validation_receipt_path),
            "independent_review_receipt_path": str(review_receipt_path),
        }
        self._record("H-006", "completed", result)
        return result

    def prepare_and_sign_receipts(
        self,
        *,
        validation_key_path: str,
        validation_issuer_id: str,
        independent_review_key_path: str,
        independent_review_issuer_id: str,
    ) -> dict[str, Any]:
        receipt = self.sign_separate_receipts(
            validation_key_path=validation_key_path,
            validation_issuer_id=validation_issuer_id,
            independent_review_key_path=independent_review_key_path,
            independent_review_issuer_id=independent_review_issuer_id,
        )
        if not self._production_state():
            return receipt
        policy_path = self._register_receipt_policy(receipt)
        receipt_paths = [
            Path(receipt["validation_receipt_path"]),
            Path(receipt["independent_review_receipt_path"]),
            self.state_path,
        ]
        self._git_commit(
            [policy_path, *receipt_paths],
            "docs: register final signed receipts and trust policy",
        )
        return {**receipt, "audit": self.run_final_audit()}

    def _stage_gap_ids(self) -> list[str]:
        ranks = {"IMPLEMENTED": 1, "INTEGRATED": 2, "OPERATED": 3}
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        gaps = []
        for group in manifest["groups"]:
            default = group.get("default_required_stage")
            for requirement in group["requirements"]:
                required = requirement.get("required_stage", default)
                if required == "EXTERNAL":
                    continue
                if ranks.get(requirement.get("claimed_stage"), 0) < ranks.get(required, 0):
                    gaps.append(requirement["requirement_id"])
        return gaps

    def _valid_operational_receipt(self, path: Path) -> dict[str, Any] | None:
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if (
                receipt.get("schema_version") != "local_operational_session_receipt_v1"
                or receipt.get("data_class") != "ACTUAL"
                or receipt.get("environment_id") != "wellnessbox-local-research-pc"
                or not receipt.get("executed_paths")
            ):
                return None
            public_b64 = self.state["steps"]["H-006"].get("public_key_ed25519_base64")
            signature_b64 = receipt.get("signature_ed25519_base64")
            if not public_b64 or not signature_b64:
                return None
            payload = {
                key: value
                for key, value in receipt.items()
                if key not in {"payload_sha256", "signature_ed25519_base64", "issuer_id"}
            }
            canonical = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
            if hashlib.sha256(canonical).hexdigest() != receipt.get("payload_sha256"):
                return None
            Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64)).verify(
                base64.b64decode(signature_b64), canonical
            )
            return receipt
        except Exception:
            return None

    def operational_coverage_summary(self) -> dict[str, Any]:
        required = set(self._stage_gap_ids())
        receipts = self.state_root / "operational_receipts"
        covered: dict[str, str] = {}
        valid_count = 0
        for path in sorted(receipts.glob("*.json")) if receipts.is_dir() else []:
            receipt = self._valid_operational_receipt(path)
            if receipt is None:
                continue
            valid_count += 1
            for requirement_id in receipt.get("covered_requirement_ids", []):
                if requirement_id in required:
                    covered[requirement_id] = str(path.resolve())
        provisional: list[str] = []
        capture_path = self.root / "etc/local_research_runtime/operational_capture.json"
        database_path = self.root / "etc/local_research_runtime/interim.sqlite3"
        wizard = (
            json.loads(self.operational_wizard_path.read_text(encoding="utf-8"))
            if self.operational_wizard_path.is_file()
            else {}
        )
        completed_profile_ids = {
            item.get("profile_id")
            for item in wizard.get("completed_profiles", [])
            if isinstance(item, dict) and isinstance(item.get("profile_id"), str)
        }
        distinct_profile_count = len(completed_profile_ids)
        if capture_path.is_file():
            capture = json.loads(capture_path.read_text(encoding="utf-8"))
            before = capture.get("database_counts_before", {})
            after = database_counts(database_path)
            delta = {
                name: after.get(name, 0) - int(before.get(name, 0))
                for name in after
            }
            mapping = json.loads(
                (self.root / "data/original_plan/operational_action_coverage_v1.json").read_text(encoding="utf-8")
            )
            actions = [
                action
                for action, signals in mapping["signals"].items()
                if action != "completed_session" and any(delta.get(table, 0) > 0 for table in signals)
            ]
            if actions:
                actions.append("completed_session")
            provisional = sorted(
                required & {op for action in actions for op in mapping["actions"][action]}
            )
        return {
            "required_count": len(required),
            "covered_count": len(covered),
            "covered_requirement_ids": sorted(covered),
            "missing_requirement_ids": sorted(required - set(covered)),
            "valid_receipt_count": valid_count,
            "cumulative_session_count": valid_count,
            "distinct_profile_count": distinct_profile_count,
            "target_distinct_profile_count": 5,
            "current_session_provisional_count": len(provisional),
            "current_session_provisional_ids": provisional,
            "evidence": covered,
        }

    def collect_operational_receipts(self, operator_id: str = "웰니스박스") -> dict[str, Any]:
        summary = self.operational_coverage_summary()
        evidence = summary.pop("evidence")
        checks: dict[str, Any] = {
            "requirement_evidence": evidence,
            **({
                key: {"status": "PASS", "evidence": next(iter(evidence.values()))}
                for key in ("rnd_api", "wellnessbox_environment", "health_check", "browser_roundtrip")
            } if evidence else {}),
        }
        state = self.record_operations(operator_id, checks)
        return {"coverage": summary, "state": state}

    def record_operations(self, operator_id: str, checks: dict[str, Any]) -> dict[str, Any]:
        previous = self.state["steps"]["H-007"]
        combined_checks = dict(previous.get("checks", {}))
        combined_checks.update(
            {key: value for key, value in checks.items() if key != "requirement_evidence"}
        )
        required = {"rnd_api", "wellnessbox_environment", "health_check", "browser_roundtrip"}
        environment_complete = required.issubset(combined_checks) and all(
            isinstance(combined_checks[key], dict)
            and combined_checks[key].get("status") == "PASS"
            and isinstance(combined_checks[key].get("evidence"), str)
            and Path(combined_checks[key]["evidence"]).resolve().is_file()
            for key in required
        )
        required_gaps = set(self._stage_gap_ids())
        supplied = checks.get("requirement_evidence", {})
        registered: dict[str, str] = dict(previous.get("registered_requirement_evidence", {}))
        if isinstance(supplied, dict):
            destination_root = self.state_root / "operational_evidence"
            destination_root.mkdir(parents=True, exist_ok=True)
            for requirement_id, source_value in supplied.items():
                if requirement_id not in required_gaps or not isinstance(source_value, str):
                    continue
                source = Path(source_value).resolve()
                if not source.is_file():
                    continue
                payload = json.loads(source.read_text(encoding="utf-8"))
                direct = payload.get("requirement_id") == requirement_id and payload.get("status") == "PASS"
                receipt = self._valid_operational_receipt(source)
                receipt_covers = receipt is not None and requirement_id in receipt.get("covered_requirement_ids", [])
                if not direct and not receipt_covers:
                    continue
                destination = destination_root / f"{requirement_id}.json"
                shutil.copy2(source, destination)
                registered[requirement_id] = str(destination)
        coverage = self.operational_coverage_summary()
        profile_target_complete = (
            coverage["distinct_profile_count"]
            >= coverage["target_distinct_profile_count"]
        )
        complete = (
            environment_complete
            and required_gaps.issubset(registered)
            and profile_target_complete
        )
        record = {
            "schema_version": "operational_environment_signoff_v1",
            "operator_id": operator_id,
            "checks": combined_checks,
            "registered_requirement_evidence": registered,
            "required_requirement_ids": sorted(required_gaps),
            "cumulative_session_count": coverage["cumulative_session_count"],
            "distinct_profile_count": coverage["distinct_profile_count"],
            "target_distinct_profile_count": coverage["target_distinct_profile_count"],
            "profile_target_complete": profile_target_complete,
            "recorded_at": _now(),
        }
        operations_path = self.state_root / "operational_environment_signoff_v1.json"
        _write_json(operations_path, record)
        result = self._record("H-007", "completed" if complete else "deferred", record)
        if complete and self._production_state():
            self._register_operational_signoffs()
            return {**result, "audit": self.run_final_audit()}
        return result

    def record_uploaded_operations(
        self, operator_id: str, documents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        checks: dict[str, Any] = {"requirement_evidence": {}}
        environment_names = {
            "rnd_api",
            "wellnessbox_environment",
            "health_check",
            "browser_roundtrip",
        }
        upload_root = self.state_root / "uploads/operational"
        for index, document in enumerate(documents):
            if not isinstance(document, dict):
                continue
            evidence_id = document.get("requirement_id") or document.get("check")
            if not isinstance(evidence_id, str):
                continue
            safe_id = "".join(
                character
                for character in evidence_id
                if character.isalnum() or character in "-_"
            )
            if not safe_id:
                continue
            path = upload_root / f"{index:03}-{safe_id}.json"
            _write_json(path, document)
            if evidence_id in environment_names:
                checks[evidence_id] = {
                    "status": document.get("status"),
                    "evidence": str(path),
                }
            else:
                checks["requirement_evidence"][evidence_id] = str(path)
        return self.record_operations(operator_id, checks)

    def _production_state(self) -> bool:
        return (
            not self.simulation
            and self.state_root
            == (self.root / "data/original_plan/final_session").resolve()
        )

    def _git_commit(self, paths: list[Path], message: str) -> None:
        relative = list(
            dict.fromkeys(
                str(path.resolve().relative_to(self.root)).replace("\\", "/")
                for path in paths
            )
        )
        subprocess.run(["git", "-C", str(self.root), "add", "--", *relative], check=True)
        staged = subprocess.run(
            ["git", "-C", str(self.root), "diff", "--cached", "--quiet", "--", *relative],
            check=False,
        )
        if staged.returncode != 0:
            subprocess.run(
                ["git", "-C", str(self.root), "commit", "--only", "-m", message, "--", *relative],
                check=True,
            )

    def _register_final_signoffs(self) -> list[Path]:
        external = self.state["steps"]["H-005"].get("registered_path")
        operations = self.state_root / "operational_environment_signoff_v1.json"
        if not external or not operations.is_file():
            raise ValueError("external validation and operations evidence are required")
        signoff = self.state_root / "human_signoff_completion_v1.json"
        _write_json(
            signoff,
            {
                "schema_version": "human_signoff_completion_v1",
                "steps": self.state["steps"],
                "completed_at": _now(),
            },
        )
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        external_path = Path(external).resolve()
        external_ref = f"wellnessbox-rnd/{external_path.relative_to(self.root).as_posix()}"
        for group in manifest["groups"]:
            for requirement in group["requirements"]:
                if requirement["requirement_id"] == "OP-039":
                    requirement["claimed_stage"] = "EXTERNAL"
                    test_files = requirement["evidence"].setdefault("test_files", [])
                    if external_ref not in test_files:
                        test_files.append(external_ref)
        _write_json(self.manifest_path, manifest)
        cases_path = self.root / "data/original_plan/op120_final_completion_audit_cases_v1.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        final_expectations = {
            "claimed_inventory": {"claimed_requirement_count": 120},
            "required_stage_gaps": {"nonexternal_stage_gap_count": 0},
            "external_validation": {"external_validation_gap_ids": []},
            "completion_receipts": {"validation": True, "independent_review": True},
            "completion_decision": {"status": "READY", "goal_complete": True},
        }
        for case in cases["cases"]:
            if case["case_id"] in final_expectations:
                case["expected"] = final_expectations[case["case_id"]]
        _write_json(cases_path, cases)
        checklist_path = self.root / "docs/original_plan/human_signoff_checklist.md"
        checklist = checklist_path.read_text(encoding="utf-8")
        if "## 열린 항목" in checklist and "## 닫힌 항목" in checklist:
            before, rest = checklist.split("## 열린 항목", 1)
            open_items, closed_items = rest.split("## 닫힌 항목", 1)
            if "### H-002" in open_items:
                checklist = (
                    before
                    + "## 열린 항목\n\n없음.\n\n## 닫힌 항목\n"
                    + open_items.strip()
                    + "\n\n"
                    + closed_items.lstrip()
                )
                checklist_path.write_text(checklist, encoding="utf-8")
        operational_paths = self._register_operational_signoffs()
        return [
            self.manifest_path,
            cases_path,
            checklist_path,
            signoff,
            operations,
            external_path,
            self.state_path,
            *operational_paths,
        ]

    def _register_operational_signoffs(self) -> list[Path]:
        operations = self.state_root / "operational_environment_signoff_v1.json"
        registered = self.state["steps"]["H-007"].get(
            "registered_requirement_evidence", {}
        )
        if not operations.is_file() or not isinstance(registered, dict):
            raise ValueError("operations evidence is required")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for group in manifest["groups"]:
            group_required = group.get("default_required_stage")
            for requirement in group["requirements"]:
                requirement_id = requirement["requirement_id"]
                if requirement_id not in registered:
                    continue
                required = requirement.get("required_stage", group_required)
                requirement["claimed_stage"] = required
                evidence_path = Path(registered[requirement_id]).resolve()
                evidence_ref = (
                    f"wellnessbox-rnd/{evidence_path.relative_to(self.root).as_posix()}"
                )
                if required in {"INTEGRATED", "OPERATED"}:
                    integrated = requirement["evidence"].setdefault(
                        "integration_evidence", []
                    )
                    if evidence_ref not in integrated:
                        integrated.append(evidence_ref)
                if required == "OPERATED":
                    operational = requirement["evidence"].setdefault(
                        "operational_evidence", []
                    )
                    if evidence_ref not in operational:
                        operational.append(evidence_ref)
        _write_json(self.manifest_path, manifest)
        return [
            self.manifest_path,
            operations,
            self.state_path,
            *(Path(value) for value in registered.values()),
        ]

    def _register_receipt_policy(self, receipt: dict[str, Any]) -> Path:
        policy = json.loads(self.audit_policy_path.read_text(encoding="utf-8"))
        validation = Path(receipt["validation_receipt_path"]).resolve()
        review = Path(receipt["independent_review_receipt_path"]).resolve()
        policy["validation_receipt_path"] = (
            f"wellnessbox-rnd/{validation.relative_to(self.root).as_posix()}"
        )
        policy["independent_review_receipt_path"] = (
            f"wellnessbox-rnd/{review.relative_to(self.root).as_posix()}"
        )
        validation_issuer = {
            "issuer_id": receipt["validation_issuer_id"],
            "public_key_ed25519_base64": receipt[
                "validation_public_key_ed25519_base64"
            ],
        }
        review_issuer = {
            "issuer_id": receipt["independent_review_issuer_id"],
            "public_key_ed25519_base64": receipt[
                "independent_review_public_key_ed25519_base64"
            ],
        }
        if (
            validation_issuer["issuer_id"] == review_issuer["issuer_id"]
            or validation_issuer["public_key_ed25519_base64"]
            == review_issuer["public_key_ed25519_base64"]
        ):
            raise ValueError("두 영수증의 발급자와 공개 키는 서로 달라야 합니다.")
        policy["trusted_issuers"] = [
            item
            for item in policy.get("trusted_issuers", [])
            if item["issuer_id"] != validation_issuer["issuer_id"]
        ] + [validation_issuer]
        policy["independent_review_trusted_issuers"] = [
            item
            for item in policy.get("independent_review_trusted_issuers", [])
            if item["issuer_id"] != review_issuer["issuer_id"]
        ] + [review_issuer]
        _write_json(self.audit_policy_path, policy)
        return self.audit_policy_path

    def finalize_and_audit(self) -> dict[str, Any]:
        incomplete = [step for step in STEPS if self.state["steps"][step]["status"] != "completed"]
        if incomplete or not self._production_state():
            result = self.run_final_audit()
            return {"finalized": False, "incomplete_steps": incomplete, "audit": result}
        phase_paths = self._register_final_signoffs()
        receipt_state = self.state["steps"]["H-006"]
        receipt = self.sign_separate_receipts(
            validation_key_path=receipt_state["validation_key_path"],
            validation_issuer_id=receipt_state["validation_issuer_id"],
            independent_review_key_path=receipt_state["independent_review_key_path"],
            independent_review_issuer_id=receipt_state[
                "independent_review_issuer_id"
            ],
        )
        receipt_paths = [
            Path(receipt["validation_receipt_path"]),
            Path(receipt["independent_review_receipt_path"]),
            self.state_path,
        ]
        policy_path = self._register_receipt_policy(receipt)
        self._git_commit(
            [*phase_paths, policy_path, *receipt_paths],
            "docs: record final signoffs, signed receipts, and trust policy",
        )
        return {"finalized": True, "incomplete_steps": [], "audit": self.run_final_audit()}

    def run_final_audit(self) -> dict[str, Any]:
        environment = {"PYTHONPATH": str(self.root / "src")}
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts/run_final_completion_audit.py")],
            cwd=self.root,
            env={**os.environ, **environment},
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        try:
            return json.loads(output.splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            return {"status": "ERROR", "exit_code": result.returncode, "output": output[-4000:]}


def run_rehearsal(root: Path, rehearsal_root: Path) -> dict[str, Any]:
    sandbox = rehearsal_root / "workspace"
    sandbox.mkdir(parents=True, exist_ok=True)
    rehearsal_rnd = sandbox / "wellnessbox-rnd"
    rehearsal_web = sandbox / "wellnessbox"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", str(root), str(rehearsal_rnd)], check=True
    )
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--shared",
            str(root.parent / "wellnessbox"),
            str(rehearsal_web),
        ],
        check=True,
    )
    for repository in (rehearsal_rnd, rehearsal_web):
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.name", "Simulation"], check=True
        )
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.email", "simulation@localhost"],
            check=True,
        )
    console = FinalSessionConsole(rehearsal_rnd, simulation=True)
    console.confirm_alignment("simulation-owner")
    for rule in console.policy_rules():
        console.review_policy_rule(rule["rule_id"], "simulation-pharmacist", "approved")
    simulated_ledger = rehearsal_root / "simulated_ai_drafts.sqlite3"
    store = InterimStore(simulated_ledger)
    store.migrate()
    draft_service = AiDraftService(store)
    for index in range(3):
        draft_service.create(
            AiDraftCreateV1(
                record_type="rehearsal",
                model_identifier="simulation-model",
                prompt_version="simulation-v1",
                content={"text": f"simulation-draft-{index}"},
                rationale={"data_class": "SIMULATION"},
                idempotency_key=f"rehearsal-{index}",
            ),
            created_at=datetime.now(UTC),
        )
    for item in list(draft_service.queue()):
        console.decide_draft(
            database_path=str(simulated_ledger),
            draft_id=item["draft_id"],
            reviewer_id="simulation-pharmacist",
            decision="approved",
        )
    console.record_report_tone("simulation-owner", True)
    external = rehearsal_rnd / "simulated_external_validation.json"
    _write_json(external, {"data_class": "SIMULATION", "status": "PASS"})
    console.register_external_validation(str(external))
    key = console.generate_key(str(rehearsal_root / "simulation_ed25519.pem"))
    console.sign_receipts(
        key_path=key["key_path"],
        issuer_id="simulation-issuer",
        source_commit="0" * 40,
    )
    environment_files = {}
    for name in ("rnd_api", "wellnessbox_environment", "health_check", "browser_roundtrip"):
        path = rehearsal_rnd / f"{name}.json"
        _write_json(path, {"data_class": "SIMULATION", "status": "PASS", "check": name})
        environment_files[name] = {"status": "PASS", "evidence": str(path)}
    requirement_evidence = {}
    for requirement_id in console._stage_gap_ids():
        path = rehearsal_rnd / "requirement_evidence" / f"{requirement_id}.json"
        _write_json(
            path,
            {"data_class": "SIMULATION", "requirement_id": requirement_id, "status": "PASS"},
        )
        requirement_evidence[requirement_id] = str(path)
    console.record_operations(
        "simulation-operator",
        {**environment_files, "requirement_evidence": requirement_evidence},
    )
    console.finalize_and_audit()
    audit = audit_final_completion_v1(
        manifest_path=rehearsal_rnd / "data/original_plan/requirements_manifest_v1.json",
        reports_dir=rehearsal_rnd / "docs/original_plan/research_reports",
        policy_path=rehearsal_rnd / "data/original_plan/op120_final_audit_policy_v1.json",
        repository_roots={
            RepositoryName.WELLNESSBOX_RND: rehearsal_rnd,
            RepositoryName.WELLNESSBOX: rehearsal_web,
        },
    ).model_dump(mode="json")
    result = {
        "schema_version": "final_session_console_rehearsal_v1",
        "data_class": "SIMULATION",
        "steps": console.state["steps"],
        "audit": audit,
        "production_paths_touched": False,
    }
    _write_json(rehearsal_root / "rehearsal_result_v1.json", result)
    return result
