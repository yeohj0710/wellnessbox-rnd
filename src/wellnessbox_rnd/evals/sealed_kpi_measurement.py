"""Run research-phase measurements against pre-existing answer-key seals."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from wellnessbox_rnd.evals.reference_standard import verify_seal
from wellnessbox_rnd.interim.agent import AgentState, BoundedAgent
from wellnessbox_rnd.interim.store import InterimStore

MEASUREMENT_SCHEMA = "sealed_kpi_internal_measurement_v1"
MEASUREMENT_ENVIRONMENT = "research_phase_internal_measurement"

_KPI3_SIGNAL_EVENTS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("목표 지표에 변화가 없다", {"score_delta": 0.0}),
    ("속쓰림과 메스꺼움", {"dose_related_issue": True}),
    ("두드러기", {"adverse_event": True}),
    ("후속 측정값을 제출하지 않아", {"measurement_complete": False}),
    ("목표 지표가 개선됐고", {"score_delta": 0.1}),
    ("새 처방약이 추가", {"safety_review_required": True}),
    ("복용 순응도가 절반에 못 미친다", {"followup_submitted": False}),
    ("알레르기 이력이 새로 확인", {"safety_review_required": True}),
    ("혈액검사 수치가 경계값", {"ambiguous": True}),
    ("성분을 바꾸고 싶다고 요청", {"followup_submitted": False}),
    ("권장량을 넘겨 복용", {"dose_related_issue": True}),
    ("목표 지표가 오히려 나빠졌다", {"score_delta": -0.1}),
)

_KPI3_EVENT_DEFAULTS: dict[str, Any] = {
    "adverse_event": False,
    "ingredient_intolerance": False,
    "dose_related_issue": False,
    "safety_review_required": False,
    "followup_submitted": True,
    "measurement_complete": True,
    "ambiguous": False,
    "score_delta": 1.0,
}

_ROOT = Path(__file__).resolve().parents[3]
_KPI3_ENGINE_PATHS = (
    "src/wellnessbox_rnd/interim/agent.py",
    "src/wellnessbox_rnd/interim/next_action.py",
    "data/original_plan/closed_loop_next_action_policy_v1.json",
)


def kpi3_event_from_prompt(prompt: str) -> dict[str, Any]:
    """Translate one blinded clinical-language situation into engine input."""
    observation = prompt.rsplit("/ 관찰:", maxsplit=1)[-1]
    matches = [event for marker, event in _KPI3_SIGNAL_EVENTS if marker in observation]
    if len(matches) != 1:
        raise ValueError(f"kpi3_prompt_signal_match_count:{len(matches)}")
    return _KPI3_EVENT_DEFAULTS | matches[0]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_kpi3_engine_outputs(
    drafts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Execute prompts without accepting or consulting reference answers."""
    outputs: dict[str, dict[str, Any]] = {}
    with TemporaryDirectory(prefix="wellnessbox-kpi3-") as directory:
        store = InterimStore(Path(directory) / "measurement.sqlite3")
        store.migrate()
        agent = BoundedAgent(store)
        for draft in drafts:
            case_id = str(draft["case_id"])
            profile_id = f"usr_measurement_{case_id.replace('-', '_')}"
            try:
                event = kpi3_event_from_prompt(str(draft["prompt"]))
                with store.transaction() as connection:
                    connection.execute(
                        "insert into user_profiles values (?, 'PROXY_GOLD_SIMULATION', "
                        "'[]', '{}', 'measurement', ?)",
                        (profile_id, datetime.now(UTC).isoformat()),
                    )
                run = agent.create_run(
                    profile_id=profile_id,
                    idempotency_key=f"measurement::{case_id}",
                )
                with store.transaction() as connection:
                    connection.execute(
                        "update agent_runs set state_after=? where run_id=?",
                        (AgentState.FOLLOWUP_ACTIVE, run["run_id"]),
                    )
                result = agent.decide_followup_action(
                    run_id=run["run_id"],
                    event=event,
                )
                persisted_state_after = store.scalar(
                    "select state_after from agent_runs where run_id=?",
                    (run["run_id"],),
                )
                outputs[case_id] = {
                    "actual_action": [str(result["action"])],
                    "execution_success": True,
                    "postcondition_success": bool(result["postcondition_success"])
                    and persisted_state_after == result["state_after"],
                    "state_before": result["state_before"],
                    "state_after": result["state_after"],
                    "error": None,
                }
            except (KeyError, TypeError, ValueError) as exc:
                outputs[case_id] = {
                    "actual_action": [],
                    "execution_success": False,
                    "postcondition_success": False,
                    "state_before": None,
                    "state_after": None,
                    "error": f"{type(exc).__name__}:{exc}",
                }
    return outputs


def run_kpi3_measurement(
    *,
    seal: dict[str, Any],
    drafts: list[dict[str, Any]],
    measured_at: str | None = None,
) -> dict[str, Any]:
    """Run all KPI-3 prompts through the declared next-action engine."""
    seal_check = verify_seal(seal)
    if not seal_check["seal_intact"]:
        raise ValueError("reference_standard_seal_broken")
    if seal.get("indicator_id") != "KPI-3":
        raise ValueError("kpi3_measurement_requires_kpi3_seal")

    prompts = {str(item["case_id"]): str(item["prompt"]) for item in drafts}
    reference = dict(seal.get("cases", {}))
    if set(prompts) != set(reference):
        raise ValueError("kpi3_prompt_and_seal_case_ids_mismatch")

    engine_outputs = generate_kpi3_engine_outputs(drafts)
    per_case: list[dict[str, Any]] = []
    for case_id in sorted(prompts):
        engine = engine_outputs[case_id]
        expected = list(reference[case_id])
        correct = (
            expected == engine["actual_action"]
            and bool(engine["execution_success"])
            and bool(engine["postcondition_success"])
        )
        per_case.append(
            {
                "case_id": case_id,
                "expected_action": expected,
                **engine,
                "correct": correct,
            }
        )

    correct_count = sum(bool(item["correct"]) for item in per_case)
    case_count = len(per_case)
    score = 100.0 * correct_count / case_count if case_count else 0.0
    target_pct = 80.0
    return {
        "schema_version": MEASUREMENT_SCHEMA,
        "indicator_id": "KPI-3",
        "system_under_test_id": seal.get("provenance", {})
        .get("role_separation", {})
        .get("system_under_test_id"),
        "input_adapter_id": "kpi3_blinded_prompt_to_followup_event_v1",
        "input_adapter_sha256": hashlib.sha256(
            json.dumps(
                _KPI3_SIGNAL_EVENTS,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "engine_artifacts": [
            {"path": path, "sha256": _file_sha256(_ROOT / path)}
            for path in _KPI3_ENGINE_PATHS
        ],
        "measurement_environment": MEASUREMENT_ENVIRONMENT,
        "measured_at": measured_at
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "seal_sha256": seal["seal_sha256"],
        "seal_intact_before_measurement": True,
        "case_count": case_count,
        "minimum_sample_count": seal["minimum_sample_count"],
        "meets_minimum_sample": case_count >= int(seal["minimum_sample_count"]),
        "correct_count": correct_count,
        "accuracy_pct": round(score, 4),
        "target_pct": target_pct,
        "target_met": case_count >= int(seal["minimum_sample_count"])
        and score >= target_pct,
        "execution_failure_count": sum(
            not bool(item["execution_success"]) for item in per_case
        ),
        "postcondition_failure_count": sum(
            not bool(item["postcondition_success"]) for item in per_case
        ),
        "per_case": per_case,
        "note": (
            "연구 기간 내부 측정값이다. 연구 종료 후 공인시험기관 최종 검증을 "
            "별도로 수행한다."
        ),
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "generate_kpi3_engine_outputs",
    "kpi3_event_from_prompt",
    "load_json",
    "run_kpi3_measurement",
]
