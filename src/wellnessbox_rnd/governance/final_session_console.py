from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wellnessbox_rnd.governance.final_completion_audit import (
    FinalCompletionFactsV1,
    evaluate_final_completion_facts_v1,
)
from wellnessbox_rnd.governance.original_plan_audit import audit_original_plan_manifest_v1
from wellnessbox_rnd.interim.ai_drafts import (
    AiDraftDecisionV1,
    AiDraftService,
    DraftReviewStatus,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.schemas.original_plan_manifest import load_original_plan_manifest_v1

STEPS = [f"H-{number:03}" for number in range(1, 8)]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class FinalSessionConsole:
    def __init__(self, root: Path, *, state_root: Path | None = None) -> None:
        self.root = root.resolve()
        self.workspace = self.root.parent
        self.state_root = (state_root or self.root / "data/original_plan/final_session").resolve()
        self.state_path = self.state_root / "session_state_v1.json"
        self.policy_path = self.root / "data/original_plan/closed_loop_next_action_policy_v1.json"
        self.audit_policy_path = self.root / "data/original_plan/op120_final_audit_policy_v1.json"
        self.manifest_path = self.root / "data/original_plan/requirements_manifest_v1.json"
        self.state = self._load_state()

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
        for report_id in ("OP-023", "OP-078", "OP-106"):
            path = self.root / f"docs/original_plan/research_reports/{report_id}.md"
            samples.append(
                {"report_id": report_id, "excerpt": path.read_text(encoding="utf-8")[:1200]}
            )
        completed = sum(item["status"] == "completed" for item in self.state["steps"].values())
        return {
            **self.state,
            "progress": {"completed": completed, "total": len(STEPS)},
            "policy_rules": readable_rules,
            "report_samples": samples,
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

    def record_draft_review_summary(self, ledger_path: str, reviewer_id: str) -> dict[str, Any]:
        path = Path(ledger_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return self._record(
            "H-003",
            "completed",
            {"reviewer_id": reviewer_id, "draft_ledger_path": str(path)},
        )

    def draft_queue(self, database_path: str) -> dict[str, Any]:
        store = InterimStore(Path(database_path).resolve())
        store.migrate()
        service = AiDraftService(store)
        return {"items": service.queue(), "summary": service.summary()}

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
        self._record(
            "H-003",
            "completed" if not queue else "pending",
            {
                "reviewer_id": reviewer_id,
                "draft_ledger_path": str(Path(database_path).resolve()),
                "review_counts": summary,
            },
        )
        return {"decided": decided, "next_draft": queue[0] if queue else None, "summary": summary}

    def record_report_tone(
        self, owner_id: str, approved: bool, comment: str = ""
    ) -> dict[str, Any]:
        samples = ["OP-023", "OP-078", "OP-106"]
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
        destination = self.state_root / "external_validation" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return self._record(
            "H-005",
            "completed",
            {
                "registered_path": str(destination),
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            },
        )

    def generate_key(self, key_path: str) -> dict[str, str]:
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
            "public_key_ed25519_base64": base64.b64encode(public).decode(),
            "validation_receipt_path": str(validation_path),
            "independent_review_receipt_path": str(review_path),
        }
        self._record("H-006", "completed", result)
        return result

    def record_operations(self, operator_id: str, checks: dict[str, str]) -> dict[str, Any]:
        required = {"rnd_api", "wellnessbox_environment", "health_check", "browser_roundtrip"}
        complete = required.issubset(checks) and all(checks[key].strip() for key in required)
        record = {
            "schema_version": "operational_environment_signoff_v1",
            "operator_id": operator_id,
            "checks": checks,
            "recorded_at": _now(),
        }
        _write_json(self.state_root / "operational_environment_signoff_v1.json", record)
        return self._record("H-007", "completed" if complete else "deferred", record)

    def run_final_audit(self) -> dict[str, Any]:
        environment = {"PYTHONPATH": str(self.root / "src")}
        result = subprocess.run(
            ["python", str(self.root / "scripts/run_final_completion_audit.py")],
            cwd=self.root,
            env={**__import__("os").environ, **environment},
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
    console = FinalSessionConsole(root, state_root=rehearsal_root)
    console.confirm_alignment("simulation-owner")
    for rule in console.policy_rules():
        console.review_policy_rule(rule["rule_id"], "simulation-pharmacist", "approved")
    simulated_ledger = rehearsal_root / "simulated_ai_draft_ledger.json"
    _write_json(simulated_ledger, {"data_class": "SIMULATION", "reviewed": 3})
    console.record_draft_review_summary(str(simulated_ledger), "simulation-pharmacist")
    console.record_report_tone("simulation-owner", True)
    external = rehearsal_root / "simulated_external_validation.json"
    _write_json(external, {"data_class": "SIMULATION", "status": "PASS"})
    console.register_external_validation(str(external))
    key = console.generate_key(str(rehearsal_root / "simulation_ed25519.pem"))
    console.sign_receipts(
        key_path=key["key_path"],
        issuer_id="simulation-issuer",
        source_commit="0" * 40,
    )
    console.record_operations(
        "simulation-operator",
        {
            "rnd_api": "simulation-ready",
            "wellnessbox_environment": "simulation-ready",
            "health_check": "simulation-pass",
            "browser_roundtrip": "simulation-pass",
        },
    )
    audit = evaluate_final_completion_facts_v1(
        FinalCompletionFactsV1(
            requirement_count=120,
            claimed_requirement_count=120,
            nonexternal_stage_gap_ids=[],
            external_validation_gap_ids=[],
            report_count=120,
            missing_report_ids=[],
            canonical_evidence_audit_passed=True,
            validation_receipt_valid=True,
            independent_review_receipt_valid=True,
        )
    )
    result = {
        "schema_version": "final_session_console_rehearsal_v1",
        "data_class": "SIMULATION",
        "steps": console.state["steps"],
        "audit": audit.model_dump(mode="json"),
        "production_paths_touched": False,
    }
    _write_json(rehearsal_root / "rehearsal_result_v1.json", result)
    return result
