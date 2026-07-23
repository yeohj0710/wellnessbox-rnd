from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "etc/local_research_runtime"
STATE_PATH = RUNTIME_ROOT / "session_processes.json"
STOP_PATH = RUNTIME_ROOT / "stop.request"


def main() -> int:
    if not STATE_PATH.is_file():
        print("실행 중인 로컬 연구 서버가 없습니다.")
        return 0
    STOP_PATH.write_text("stop\n", encoding="ascii")
    print("로컬 연구 서버에 종료를 요청했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
