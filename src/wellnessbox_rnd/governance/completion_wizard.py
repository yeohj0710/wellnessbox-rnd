"""One pass through everything the research still needs, in order.

The runner opens each screen, waits for the person, then checks the repository
to see whether the step actually landed. It never fills a judgment in and never
marks a human step done on its own — verification only reads what is stored.

Machine steps run by themselves. Steps behind the training gate report
`skipped_gate_closed` instead of failing, because a closed gate is the correct
state until the CGM blocker is resolved.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

PROGRESS_RELATIVE_PATH = "artifacts/final_session/completion_wizard_progress_v1.json"
PROGRESS_SCHEMA = "completion_wizard_progress_v1"
CONSOLE_URL = "http://127.0.0.1:8765/"
REVIEW_URL = "http://127.0.0.1:8765/op039-review"
TIPS_URL = "http://127.0.0.1:3001/research-login?redirect=/tips"
PHARM_URL = "http://127.0.0.1:3001/research-login?redirect=/pharm/tips"

StepKind = Literal["auto", "human"]
Verdict = Literal["done", "todo", "blocked", "skipped_gate_closed"]


@dataclass(frozen=True)
class Step:
    step_id: str
    title: str
    kind: StepKind
    instruction: str
    url: str | None = None
    command: list[str] | None = None
    needs_servers: bool = False
    gated_by_training: bool = False


@dataclass
class StepResult:
    step_id: str
    verdict: Verdict
    detail: str
    missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict in {"done", "skipped_gate_closed"}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


KNOWN_REVIEW_CHARACTERS = frozenset(
    {
        "pharmacist_candidate_preliminary_safety_review",
        "licensed_pharmacist_expert_safety_review",
        "post_completion_independent_organization_evaluation",
    }
)


def _session_start(artifacts: dict[str, Any]) -> str | None:
    return artifacts.get("session_started_at")


def read_session_state(root: Path) -> dict[str, Any]:
    state = _read_json(root / "data/original_plan/final_session/session_state_v1.json")
    return state or {"steps": {}}


def read_operational_counts(
    root: Path, *, session_started_at: str | None = None
) -> dict[str, int | None]:
    """Count real profiles and drafts without writing anything.

    Rows created before the session started belong to an earlier run. They are
    counted separately so a past session never looks like today's work.
    """
    database = root / "etc/local_research_runtime/interim.sqlite3"
    if not database.is_file():
        return {
            "distinct_actual_profiles": None,
            "pending_drafts": None,
            "reviewed_drafts": None,
            "earlier_profiles": None,
        }
    since = session_started_at or ""
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        profiles = connection.execute(
            "select count(distinct profile_id) from profile_snapshots "
            "where data_class = 'INTERIM_RUNTIME_EVENT' and created_at >= ?",
            (since,),
        ).fetchone()[0]
        earlier = connection.execute(
            "select count(distinct profile_id) from profile_snapshots "
            "where data_class = 'INTERIM_RUNTIME_EVENT' and created_at < ?",
            (since,),
        ).fetchone()[0]
        pending = connection.execute(
            "select count(*) from ai_drafts where review_status = 'pending'"
        ).fetchone()[0]
        reviewed = connection.execute(
            "select count(*) from ai_drafts "
            "where review_status != 'pending' and coalesce(reviewed_at, '') >= ?",
            (since,),
        ).fetchone()[0]
    except sqlite3.DatabaseError as exc:
        return {"error": str(exc)}  # type: ignore[return-value]
    finally:
        connection.close()
    return {
        "distinct_actual_profiles": int(profiles),
        "pending_drafts": int(pending),
        "reviewed_drafts": int(reviewed),
        "earlier_profiles": int(earlier),
    }


def training_gate_is_open(root: Path) -> bool:
    gate = _read_json(root / "artifacts/reports/training_readiness_gate_v2.json")
    if gate is None:
        return False
    return bool(gate.get("gate_decision", {}).get("authorized_now"))


def step_belongs_to_this_session(step: dict[str, Any], session_started_at: str | None) -> bool:
    """A completion saved before this session started is a past record, not today's work."""
    if session_started_at is None:
        return True
    updated_at = str(step.get("updated_at", ""))
    return bool(updated_at) and updated_at >= session_started_at


def _human_step_result(
    root: Path,
    step_id: str,
    *,
    label: str,
    session_started_at: str | None = None,
    extra: str = "",
) -> StepResult:
    state = read_session_state(root)
    step = state.get("steps", {}).get(step_id, {})
    if step.get("status") != "completed":
        status = step.get("status", "없음")
        return StepResult(
            step_id,
            "todo",
            f"{label}이(가) 아직 저장되지 않았습니다. 현재 상태: {status}.",
            [f"{step_id}_not_completed"],
        )
    if not step_belongs_to_this_session(step, session_started_at):
        return StepResult(
            step_id,
            "todo",
            (
                f"{label} 기록이 있으나 {step.get('updated_at', '시각 미상')} 로 "
                "이번 세션 시작 전입니다. 과거 기록은 이번 세션 근거로 쓰지 않으므로 다시 하세요."
            ),
            [f"{step_id}_completed_in_a_previous_session"],
        )
    return StepResult(step_id, "done", f"{label} 완료로 저장됨.{extra}")


def verify_preflight(root: Path, artifacts: dict[str, Any]) -> StepResult:
    result = artifacts.get("preflight")
    if result is None:
        return StepResult("PREFLIGHT", "todo", "사전 점검을 아직 실행하지 않았습니다.")
    if result.get("status") == "READY":
        return StepResult("PREFLIGHT", "done", "사전 점검 READY, 저장 경계 모두 불변.")
    blockers = [item.get("id", "?") for item in result.get("blockers", [])]
    return StepResult(
        "PREFLIGHT",
        "blocked",
        f"사전 점검이 {result.get('status')}입니다. 차단: {', '.join(blockers) or '없음'}",
        blockers,
    )


def verify_servers(root: Path, artifacts: dict[str, Any]) -> StepResult:
    health = artifacts.get("server_health", {})
    failing = [name for name, code in health.items() if code != 200]
    if health and not failing:
        return StepResult("SERVERS", "done", "R&D·콘솔·웹 화면이 모두 200입니다.")
    return StepResult(
        "SERVERS",
        "todo",
        "서버가 아직 준비되지 않았습니다." if not health else f"응답 실패: {', '.join(failing)}",
        failing,
    )


def verify_profiles(root: Path, artifacts: dict[str, Any]) -> StepResult:
    counts = read_operational_counts(root, session_started_at=_session_start(artifacts))
    profiles = counts.get("distinct_actual_profiles")
    if profiles is None:
        return StepResult("H-007", "blocked", "운영 DB를 읽지 못했습니다.", ["database_missing"])
    earlier = counts.get("earlier_profiles") or 0
    note = f" 이전 세션 프로필 {earlier}건은 세지 않았습니다." if earlier else ""
    if profiles >= 5:
        return StepResult(
            "H-007", "done", f"이번 세션에서 서로 다른 프로필 {profiles}건 저장.{note}"
        )
    return StepResult(
        "H-007",
        "todo",
        f"이번 세션 프로필이 {profiles}/5건입니다. {5 - profiles}건 더 입력하세요.{note}",
        ["distinct_profiles_below_target"],
    )


def verify_draft_review(root: Path, artifacts: dict[str, Any]) -> StepResult:
    counts = read_operational_counts(root, session_started_at=_session_start(artifacts))
    pending = counts.get("pending_drafts")
    reviewed = counts.get("reviewed_drafts")
    if pending is None:
        return StepResult("H-003", "blocked", "운영 DB를 읽지 못했습니다.", ["database_missing"])
    if pending == 0 and (reviewed or 0) > 0:
        return StepResult("H-003", "done", f"대기 0건, 이번 세션 검토 {reviewed}건.")
    if pending == 0:
        return StepResult(
            "H-003",
            "todo",
            "이번 세션에서 검토한 초안이 없습니다. H-007 실행 뒤 대기열이 생기면 처리하세요.",
            ["no_drafts_reviewed_this_session"],
        )
    return StepResult(
        "H-003", "todo", f"대기 초안이 {pending}건 남았습니다.", ["pending_drafts_remain"]
    )


def verify_dataset(root: Path, artifacts: dict[str, Any]) -> StepResult:
    check = artifacts.get("dataset_check")
    if check is None:
        return StepResult("DATASET", "todo", "승인 전용 데이터셋을 아직 만들지 않았습니다.")
    if check.get("status") == "READY":
        return StepResult(
            "DATASET", "done", f"승인 초안 {check.get('included_count', 0)}건으로 manifest 작성."
        )
    return StepResult(
        "DATASET", "blocked", "데이터셋 manifest 검증이 실패했습니다.", check.get(
            "violation_draft_ids", []
        )
    )


def verify_training(root: Path, artifacts: dict[str, Any]) -> StepResult:
    if not training_gate_is_open(root):
        return StepResult(
            "TRAIN",
            "skipped_gate_closed",
            "학습 게이트가 NO-GO라 훈련하지 않았습니다. 실행 계획만 기록했습니다.",
        )
    plan = artifacts.get("training_plan", {})
    if plan.get("executed"):
        return StepResult("TRAIN", "done", "후보 모델 학습을 1회 실행했습니다.")
    return StepResult("TRAIN", "todo", "학습 명령이 아직 성공하지 않았습니다.")


def verify_promotion(root: Path, artifacts: dict[str, Any]) -> StepResult:
    if not training_gate_is_open(root):
        return StepResult(
            "PROMOTION",
            "skipped_gate_closed",
            "후보 모델이 없어 교체 판정을 건너뜁니다. 현재 모델을 유지합니다.",
        )
    decision = artifacts.get("promotion_decision")
    if decision is None:
        return StepResult("PROMOTION", "todo", "교체 판정을 아직 내리지 않았습니다.")
    return StepResult(
        "PROMOTION", "done", f"판정: {decision.get('decision')}. 되돌릴 artifact를 기록했습니다."
    )


def verify_policy(root: Path, artifacts: dict[str, Any]) -> StepResult:
    return _human_step_result(
        root, "H-002", label="정책 9개 규칙 확인", session_started_at=_session_start(artifacts)
    )


def verify_tone(root: Path, artifacts: dict[str, Any]) -> StepResult:
    return _human_step_result(
        root, "H-004", label="보고서 문체 승인", session_started_at=_session_start(artifacts)
    )


def verify_safety_review(root: Path, artifacts: dict[str, Any]) -> StepResult:
    result = _human_step_result(
        root, "H-005", label="고위험 10건 검토", session_started_at=_session_start(artifacts)
    )
    if result.verdict != "done":
        return result
    step = read_session_state(root)["steps"]["H-005"]
    character = step.get("review_character", "")
    if step.get("requires_licensed_reconfirmation"):
        return StepResult(
            "H-005",
            "done",
            "예비 약사 사전 검토로 저장됨. 3차년도에 약사 자격으로 재검토해야 합니다.",
        )
    if character not in KNOWN_REVIEW_CHARACTERS:
        return StepResult(
            "H-005",
            "todo",
            "저장된 검토에 자격 단계 표시가 없습니다. 중립 화면 이전 기록이므로 다시 검토하세요.",
            ["h005_record_predates_the_candidate_model"],
        )
    return StepResult("H-005", "done", f"검토 저장됨({character}).")


def verify_receipts(root: Path, artifacts: dict[str, Any]) -> StepResult:
    return _human_step_result(
        root, "H-006", label="최종 영수증 2종 발급", session_started_at=_session_start(artifacts)
    )


def verify_audit(root: Path, artifacts: dict[str, Any]) -> StepResult:
    audit = artifacts.get("audit")
    if audit is None:
        return StepResult("AUDIT", "todo", "최종 감사를 아직 실행하지 않았습니다.")
    decision = audit.get("audit", {})
    if decision.get("status") == "READY" and decision.get("goal_complete"):
        return StepResult("AUDIT", "done", "최종 감사 120/120 READY, 차단 0건.")
    blockers = [item.get("id", "?") for item in decision.get("blockers", [])]
    return StepResult(
        "AUDIT", "blocked", f"최종 감사가 {decision.get('status')}입니다.", blockers
    )


Verifier = Callable[[Path, dict[str, Any]], StepResult]

STEPS: tuple[Step, ...] = (
    Step(
        "PREFLIGHT",
        "사전 점검",
        "auto",
        "운영 영수증을 만들지 않는 점검을 자동으로 실행합니다. 기다리기만 하면 됩니다.",
    ),
    Step(
        "SERVERS",
        "연구 서버 켜기",
        "human",
        "새 창에서 research-server-start.cmd 를 실행하고 "
        "'로컬 연구 서버가 준비됐습니다.' 문구가 뜰 때까지 기다리세요.",
        url=CONSOLE_URL,
    ),
    Step(
        "H-007",
        "실제 프로필 5건 입력",
        "human",
        "사용자 화면에서 실제 참여자 5명의 복용 전 자료와 후속평가를 하나씩 입력하세요. "
        "최종 확인 화면의 자동 저장 버튼은 누르지 않습니다.",
        url=TIPS_URL,
        needs_servers=True,
    ),
    Step(
        "H-003",
        "AI 초안 전수 검토",
        "human",
        "약사 화면 대기열의 초안을 하나씩 승인·수정 승인·반려로 처리하세요. "
        "대기 0건이 되어야 합니다.",
        url=PHARM_URL,
        needs_servers=True,
    ),
    Step(
        "DATASET",
        "승인 전용 데이터셋 만들기",
        "auto",
        "승인·수정 승인 초안만 골라 manifest를 만듭니다. 자동입니다.",
        command=["scripts/build_approved_draft_dataset.py"],
    ),
    Step(
        "TRAIN",
        "후보 모델 학습",
        "auto",
        "학습 게이트가 열려 있을 때만 실행합니다. NO-GO면 실행 계획만 남기고 넘어갑니다.",
        command=["scripts/train_approved_draft_candidate.py"],
        gated_by_training=True,
    ),
    Step(
        "PROMOTION",
        "안전 회귀 확인과 교체 판정",
        "auto",
        "기준 모델과 후보 모델을 같은 고정 평가로 비교하고 교체 여부를 기록합니다.",
        command=["scripts/decide_candidate_promotion.py"],
        gated_by_training=True,
    ),
    Step(
        "H-002",
        "정책 9개 규칙 확인",
        "human",
        "최종 확인 화면에서 다음 행동 규칙 9개를 읽고 승인 또는 수정 의견을 직접 입력하세요.",
        url=CONSOLE_URL,
        needs_servers=True,
    ),
    Step(
        "H-004",
        "보고서 문체 승인",
        "human",
        "무작위 보고서 2~3편을 읽고 오너가 직접 의견을 입력한 뒤 문체 확인을 누르세요.",
        url=CONSOLE_URL,
        needs_servers=True,
    ),
    Step(
        "H-005",
        "고위험 10건 검토",
        "human",
        "10건을 하나씩 직접 판정하고 근거를 적으세요. 이름·소속·서명만 입력하면 됩니다. "
        "예비 약사 사전 검토로 기록되며 3차년도에 약사 자격으로 재검토합니다.",
        url=REVIEW_URL,
        needs_servers=True,
    ),
    Step(
        "H-006",
        "최종 영수증 2종 발급",
        "human",
        "앞 단계가 모두 저장된 것을 확인한 뒤 오너가 영수증 서명을 누르세요.",
        url=CONSOLE_URL,
        needs_servers=True,
    ),
    Step(
        "AUDIT",
        "최종 감사",
        "auto",
        "현재 파일 내용으로 최종 완료 감사를 실행합니다. 자동입니다.",
        command=["scripts/run_final_completion_audit.py"],
    ),
)

VERIFIERS: dict[str, Verifier] = {
    "PREFLIGHT": verify_preflight,
    "SERVERS": verify_servers,
    "H-007": verify_profiles,
    "H-003": verify_draft_review,
    "DATASET": verify_dataset,
    "TRAIN": verify_training,
    "PROMOTION": verify_promotion,
    "H-002": verify_policy,
    "H-004": verify_tone,
    "H-005": verify_safety_review,
    "H-006": verify_receipts,
    "AUDIT": verify_audit,
}


def verify_step(step_id: str, root: Path, artifacts: dict[str, Any]) -> StepResult:
    return VERIFIERS[step_id](root, artifacts)


def next_pending_step(
    results: dict[str, StepResult], steps: tuple[Step, ...] = STEPS
) -> Step | None:
    """Return the first step that is not finished, so a stopped run can resume."""
    for step in steps:
        result = results.get(step.step_id)
        if result is None or not result.ok:
            return step
    return None


def progress_summary(
    results: dict[str, StepResult], steps: tuple[Step, ...] = STEPS
) -> dict[str, Any]:
    rows = []
    for index, step in enumerate(steps, start=1):
        result = results.get(step.step_id)
        rows.append(
            {
                "order": index,
                "step_id": step.step_id,
                "title": step.title,
                "kind": step.kind,
                "verdict": result.verdict if result else "todo",
                "detail": result.detail if result else "아직 확인하지 않았습니다.",
            }
        )
    finished = sum(1 for row in rows if row["verdict"] in {"done", "skipped_gate_closed"})
    return {
        "schema_version": PROGRESS_SCHEMA,
        "total_steps": len(rows),
        "finished_steps": finished,
        "all_finished": finished == len(rows),
        "steps": rows,
    }


def load_progress(root: Path) -> dict[str, Any]:
    return _read_json(root / PROGRESS_RELATIVE_PATH) or {}


def save_progress(root: Path, summary: dict[str, Any]) -> Path:
    path = root / PROGRESS_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path
