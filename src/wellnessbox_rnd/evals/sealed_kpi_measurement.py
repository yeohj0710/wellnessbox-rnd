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
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    MedicationInput,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)

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
_KPI1_ENGINE_PATHS = (
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
    "src/wellnessbox_rnd/domain/intake.py",
)
_KPI1_INPUT_ADAPTER_ID = "kpi1_reference_prompt_to_recommendation_request_v1"


def kpi3_event_from_prompt(prompt: str) -> dict[str, Any]:
    """Translate one blinded clinical-language situation into engine input."""
    observation = prompt.rsplit("/ 관찰:", maxsplit=1)[-1]
    matches = [event for marker, event in _KPI3_SIGNAL_EVENTS if marker in observation]
    if len(matches) != 1:
        raise ValueError(f"kpi3_prompt_signal_match_count:{len(matches)}")
    return _KPI3_EVENT_DEFAULTS | matches[0]


def _kpi1_goal_from_prompt(*, area: str, target: str) -> RecommendationGoal:
    text = f"{area} {target}"
    if any(marker in text for marker in ("수면", "숙면", "불면")):
        return RecommendationGoal.SLEEP_SUPPORT
    if any(marker in text for marker in ("장", "배변", "변비", "설사", "위 ", "소화")):
        return RecommendationGoal.GUT_HEALTH
    if any(marker in text for marker in ("골밀도", "뼈 건강", "관절", "치조골")):
        return RecommendationGoal.BONE_JOINT
    if any(marker in text for marker in ("면역", "감염", "알레르기", "염증")):
        return RecommendationGoal.IMMUNITY_SUPPORT
    if any(marker in text for marker in ("혈당", "인슐린", "당화", "당뇨")):
        return RecommendationGoal.BLOOD_GLUCOSE
    if any(
        marker in text
        for marker in ("LDL", "TG", "콜레스테롤", "혈관", "고혈압", "혈류", "치질")
    ):
        return RecommendationGoal.HEART_HEALTH
    if any(
        marker in text for marker in ("에너지", "피로", "무기력", "소진", "자율신경")
    ):
        return RecommendationGoal.ENERGY_SUPPORT
    if any(
        marker in text
        for marker in ("스트레스", "불안", "우울", "정서", "공황", "긴장", "신경")
    ):
        return RecommendationGoal.STRESS_SUPPORT
    return RecommendationGoal.GENERAL_WELLNESS


def kpi1_request_from_prompt(prompt: str) -> RecommendationRequest:
    """Translate a reference-corpus prompt without reading its answer."""
    if not prompt.startswith("영역 "):
        raise ValueError("kpi1_prompt_prefix_invalid")
    body = prompt[len("영역 ") :]
    try:
        area, body = body.split(" / 판정 「", maxsplit=1)
        target, body = body.split("」 / 나이 ", maxsplit=1)
        age_text, medication = body.split(" / 복용약 ", maxsplit=1)
        age = int(age_text)
    except (TypeError, ValueError) as exc:
        raise ValueError("kpi1_prompt_structure_invalid") from exc
    medications = [] if medication == "없음" else [MedicationInput(name=medication)]
    return RecommendationRequest(
        user_profile=UserProfile(age=age, biological_sex=BiologicalSex.UNDISCLOSED),
        goals=[_kpi1_goal_from_prompt(area=area, target=target)],
        medications=medications,
    )


def generate_kpi1_engine_outputs(
    drafts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Run recommendation cases without accepting or consulting reference answers."""
    outputs: dict[str, dict[str, Any]] = {}
    for draft in drafts:
        case_id = str(draft["case_id"])
        try:
            request = kpi1_request_from_prompt(str(draft["prompt"]))
            response = recommend(request)
            payload = response.model_dump(mode="json")
            outputs[case_id] = {
                "actual_answer": list(payload["candidate_pool_trace"]["selected_candidate_keys"]),
                "engine_status": payload["status"],
                "execution_success": True,
                "postcondition_success": isinstance(payload["recommendations"], list),
                "goal": request.goals[0].value,
                "medication": [item.name for item in request.medications],
                "error": None,
            }
        except (KeyError, TypeError, ValueError) as exc:
            outputs[case_id] = {
                "actual_answer": [],
                "engine_status": None,
                "execution_success": False,
                "postcondition_success": False,
                "goal": None,
                "medication": [],
                "error": f"{type(exc).__name__}:{exc}",
            }
    return outputs


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


def run_kpi1_measurement(
    *,
    seal: dict[str, Any],
    drafts: list[dict[str, Any]],
    measured_at: str | None = None,
) -> dict[str, Any]:
    """Run all KPI-1 prompts through the declared recommendation engine."""
    seal_check = verify_seal(seal)
    if not seal_check["seal_intact"]:
        raise ValueError("reference_standard_seal_broken")
    if seal.get("indicator_id") != "KPI-1":
        raise ValueError("kpi1_measurement_requires_kpi1_seal")

    prompts = {str(item["case_id"]): str(item["prompt"]) for item in drafts}
    reference = dict(seal.get("cases", {}))
    if set(prompts) != set(reference):
        raise ValueError("kpi1_prompt_and_seal_case_ids_mismatch")

    engine_outputs = generate_kpi1_engine_outputs(drafts)
    per_case: list[dict[str, Any]] = []
    for case_id in sorted(prompts):
        engine = engine_outputs[case_id]
        expected = list(reference[case_id])
        expected_set = set(expected)
        actual = set(engine["actual_answer"])
        matched_count = len(expected_set & actual)
        score = 100.0 * matched_count / len(expected_set) if expected_set else 0.0
        per_case.append(
            {
                "case_id": case_id,
                "expected_answer": expected,
                **engine,
                "matched_count": matched_count,
                "score_pct": round(score, 4),
                "correct": score == 100.0,
            }
        )

    case_count = len(per_case)
    mean_score = sum(item["score_pct"] for item in per_case) / case_count if case_count else 0.0
    return {
        "schema_version": MEASUREMENT_SCHEMA,
        "indicator_id": "KPI-1",
        "system_under_test_id": seal.get("provenance", {})
        .get("role_separation", {})
        .get("system_under_test_id"),
        "input_adapter_id": _KPI1_INPUT_ADAPTER_ID,
        "input_adapter_sha256": hashlib.sha256(
            json.dumps(
                {
                    "goal_markers": [
                        "수면",
                        "장",
                        "배변",
                        "골밀도",
                        "면역",
                        "혈당",
                        "LDL",
                        "에너지",
                        "스트레스",
                    ],
                    "prompt_structure": "영역 / 판정 / 나이 / 복용약",
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "engine_artifacts": [
            {"path": path, "sha256": _file_sha256(_ROOT / path)}
            for path in _KPI1_ENGINE_PATHS
        ],
        "measurement_environment": MEASUREMENT_ENVIRONMENT,
        "measured_at": measured_at
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "seal_sha256": seal["seal_sha256"],
        "seal_intact_before_measurement": True,
        "case_count": case_count,
        "minimum_sample_count": seal["minimum_sample_count"],
        "meets_minimum_sample": case_count >= int(seal["minimum_sample_count"]),
        "mean_score_pct": round(mean_score, 4),
        "target_pct": 80.0,
        "target_met": case_count >= int(seal["minimum_sample_count"])
        and mean_score >= 80.0,
        "execution_failure_count": sum(
            not bool(item["execution_success"]) for item in per_case
        ),
        "postcondition_failure_count": sum(
            not bool(item["postcondition_success"]) for item in per_case
        ),
        "exact_case_match_count": sum(bool(item["correct"]) for item in per_case),
        "per_case": per_case,
        "note": (
            "연구 기간 내부 측정값이다. 연구 종료 후 공인시험기관 최종 검증을 "
            "별도로 수행한다."
        ),
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "generate_kpi1_engine_outputs",
    "generate_kpi3_engine_outputs",
    "kpi1_request_from_prompt",
    "kpi3_event_from_prompt",
    "load_json",
    "run_kpi1_measurement",
    "run_kpi3_measurement",
]
