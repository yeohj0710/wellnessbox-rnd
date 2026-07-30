"""연구 마감까지 한 번에 진행하는 안내 실행기.

켜 놓고 Enter만 누르면서 따라가면 된다. 자동 단계는 알아서 돌고, 사람이 해야
하는 단계는 화면을 열어 주고 기다린다. 사람이 끝냈다고 하면 저장소를 다시 읽어
실제로 저장됐는지 확인하고, 저장되지 않았으면 다음으로 넘어가지 않는다.

판정을 대신 고르거나 채우지 않는다. push, 배포, 영수증 위조도 하지 않는다.
학습 게이트가 NO-GO면 훈련 단계는 실행 계획만 남기고 건너뛴다.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.governance.completion_wizard import (  # noqa: E402
    STEPS,
    Step,
    StepResult,
    load_progress,
    next_pending_step,
    progress_summary,
    save_progress,
    training_gate_is_open,
    verify_step,
)

ROOT = Path(__file__).resolve().parents[1]
INTERIM_PYTHON = ROOT / ".venv-interim/Scripts/python.exe"
HEALTH_URLS = {
    "rnd_health": "http://127.0.0.1:8000/health",
    "console_home": "http://127.0.0.1:8765/",
    "wellnessbox_health": "http://127.0.0.1:3001/api/internal/rnd/health",
}

BAR = "─" * 68


def resolve_session_start(force_new: bool) -> str:
    """Reuse the stored session start so a stopped run resumes instead of restarting."""
    stored = load_progress(ROOT).get("session_started_at")
    if stored and not force_new:
        return str(stored)
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def say(message: str = "") -> None:
    print(message, flush=True)


def python_for(script: str) -> str:
    """Preflight and the console need the interim interpreter; the rest do not."""
    interim = {"run_final_session_preflight.py", "run_final_session_console.py"}
    if Path(script).name in interim and INTERIM_PYTHON.is_file():
        return str(INTERIM_PYTHON)
    return sys.executable


def run_json_command(script: str, *args: str) -> tuple[int, dict[str, Any] | None, str]:
    completed = subprocess.run(
        [python_for(script), script, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        payload = None
    return completed.returncode, payload, (completed.stderr or "").strip()


def probe_health() -> dict[str, int]:
    health: dict[str, int] = {}
    for name, url in HEALTH_URLS.items():
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                health[name] = int(response.status)
        except (OSError, urllib.error.URLError) as exc:
            health[name] = getattr(exc, "code", 0) or 0
    return health


def run_auto_step(step: Step, artifacts: dict[str, Any]) -> None:
    if step.step_id == "PREFLIGHT":
        say("사전 점검을 실행합니다. 2~3분 걸립니다.")
        _, payload, error = run_json_command("scripts/run_final_session_preflight.py")
        artifacts["preflight"] = payload or {"status": "ERROR", "blockers": []}
        if error:
            say(f"  (표준 오류) {error[:300]}")
        return

    if step.step_id == "DATASET":
        _, payload, error = run_json_command("scripts/build_approved_draft_dataset.py")
        artifacts["dataset_check"] = payload
        if error:
            say(f"  (표준 오류) {error[:300]}")
        return

    if step.step_id == "TRAIN":
        if not training_gate_is_open(ROOT):
            say("학습 게이트가 NO-GO입니다. 실행 계획만 남기고 훈련은 하지 않습니다.")
        _, payload, _ = run_json_command("scripts/train_approved_draft_candidate.py")
        plan_path = ROOT / "data/original_plan/final_session/approved_draft_training_plan_v1.json"
        if plan_path.is_file():
            artifacts["training_plan"] = json.loads(plan_path.read_text(encoding="utf-8"))
        else:
            artifacts["training_plan"] = payload or {}
        return

    if step.step_id == "PROMOTION":
        if not training_gate_is_open(ROOT):
            say("후보 모델이 없으므로 교체 판정을 건너뜁니다. 현재 모델을 그대로 둡니다.")
            return
        say("후보 모델 평가와 교체 판정은 기준·후보 보고서 경로가 필요합니다.")
        say("FINAL_SESSION_RUNBOOK.md 의 '학습·평가 1회' 절 명령을 그대로 실행하세요.")
        return

    if step.step_id == "AUDIT":
        say("최종 감사를 실행합니다.")
        _, payload, error = run_json_command("scripts/run_final_completion_audit.py")
        artifacts["audit"] = payload
        if error:
            say(f"  (표준 오류) {error[:300]}")
        return


def show_step(order: int, total: int, step: Step) -> None:
    say()
    say(BAR)
    say(f"[{order}/{total}] {step.title}   ({'자동' if step.kind == 'auto' else '사람이 할 일'})")
    say(BAR)
    say(step.instruction)
    if step.url:
        say(f"화면: {step.url}")


def wait_for_person(step: Step, *, auto_open: bool) -> str:
    if step.url and auto_open:
        try:
            webbrowser.open(step.url)
        except OSError:
            pass
    say()
    say("끝났으면 Enter, 건너뛰려면 s, 그만두려면 q 를 누르세요.")
    try:
        return input("> ").strip().lower()
    except EOFError:
        return "q"


def report(result: StepResult) -> None:
    mark = {"done": "완료", "todo": "아직", "blocked": "막힘", "skipped_gate_closed": "건너뜀"}
    say(f"확인 결과: {mark[result.verdict]} — {result.detail}")


def print_summary(summary: dict[str, Any], progress_path: Path) -> None:
    say()
    say(BAR)
    say(f"진행 상황  {summary['finished_steps']}/{summary['total_steps']} 단계 완료")
    say(BAR)
    mark = {"done": "[v]", "todo": "[ ]", "blocked": "[!]", "skipped_gate_closed": "[-]"}
    for row in summary["steps"]:
        say(f" {mark[row['verdict']]} {row['order']:>2}. {row['title']}  — {row['detail']}")
    say()
    say(f"진행 기록: {progress_path}")
    if summary["all_finished"]:
        say("모든 단계가 끝났습니다. 2차년도 범위에서 더 할 일은 없습니다.")
    else:
        say("남은 단계가 있습니다. 같은 명령을 다시 실행하면 이어서 진행합니다.")


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status", action="store_true", help="아무것도 실행하지 않고 현재 진행 상황만 본다"
    )
    parser.add_argument("--no-open", action="store_true", help="화면을 자동으로 열지 않는다")
    parser.add_argument(
        "--new-session",
        action="store_true",
        help="이전 진행 기록을 버리고 지금부터 새 세션으로 시작한다",
    )
    args = parser.parse_args()

    artifacts: dict[str, Any] = {"session_started_at": resolve_session_start(args.new_session)}
    results: dict[str, StepResult] = {}
    total = len(STEPS)

    say(f"세션 시작 시각: {artifacts['session_started_at']}")
    say("이 시각 이전에 저장된 과거 기록은 이번 세션 근거로 세지 않습니다.")

    if args.status:
        for step in STEPS:
            if step.step_id in {"SERVERS"}:
                artifacts["server_health"] = probe_health()
            results[step.step_id] = verify_step(step.step_id, ROOT, artifacts)
        summary = progress_summary(results)
        summary["session_started_at"] = artifacts["session_started_at"]
        print_summary(summary, save_progress(ROOT, summary))
        return 0

    say(BAR)
    say(" 연구 마감 안내 실행기")
    say(BAR)
    say("Enter만 누르면서 따라가면 됩니다. 사람이 해야 하는 판정은 대신 하지 않습니다.")
    say("중간에 q 로 그만둬도 같은 명령을 다시 실행하면 이어서 진행합니다.")

    for order, step in enumerate(STEPS, start=1):
        show_step(order, total, step)

        if step.step_id == "SERVERS":
            artifacts["server_health"] = probe_health()
        result = verify_step(step.step_id, ROOT, artifacts)
        if result.ok:
            report(result)
            results[step.step_id] = result
            continue

        if step.kind == "auto":
            run_auto_step(step, artifacts)
            result = verify_step(step.step_id, ROOT, artifacts)
            report(result)
            results[step.step_id] = result
            if not result.ok:
                say("이 단계가 끝나지 않아 여기서 멈춥니다. 위 사유를 먼저 해결하세요.")
                break
            continue

        while True:
            answer = wait_for_person(step, auto_open=not args.no_open)
            if answer == "q":
                results[step.step_id] = result
                summary = progress_summary(results)
                summary["session_started_at"] = artifacts["session_started_at"]
                print_summary(summary, save_progress(ROOT, summary))
                return 0
            if answer == "s":
                say("건너뜁니다. 나중에 다시 실행하면 이 단계부터 확인합니다.")
                results[step.step_id] = result
                break
            if step.step_id == "SERVERS":
                artifacts["server_health"] = probe_health()
            result = verify_step(step.step_id, ROOT, artifacts)
            report(result)
            if result.ok:
                results[step.step_id] = result
                break
            say("아직 저장되지 않았습니다. 화면에서 마저 처리한 뒤 다시 Enter를 누르세요.")

        if not results.get(step.step_id, result).ok:
            break

    summary = progress_summary(results)
    summary["session_started_at"] = artifacts["session_started_at"]
    print_summary(summary, save_progress(ROOT, summary))
    remaining = next_pending_step(results)
    if remaining is not None:
        say(f"다음에 이어서 할 단계: {remaining.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
