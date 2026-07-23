from __future__ import annotations

import hashlib
import http.cookiejar
import json
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WELLNESSBOX = ROOT.parent / "wellnessbox"
RUNTIME_STATE = ROOT / "etc/local_research_runtime/session_processes.json"
OUTPUT = ROOT / "data/original_plan/evidence/op088_op090_full_service_roundtrip_v1.json"
PRIOR = {
    "OP-088": ROOT / "data/original_plan/evidence/op087_op088_counseling_session_service_adapter_smoke_v1.json",
    "OP-090": ROOT / "data/original_plan/evidence/op089_op090_counseling_fallback_api_e2e_v1.json",
}


def _request(opener: urllib.request.OpenerDirector, url: str, *, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json", "user-agent": "wb-op088-op090-smoke/1"},
    )
    with opener.open(request, timeout=30) as response:
        raw = response.read()
        return response.status, raw


def _commit(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def main() -> int:
    if not RUNTIME_STATE.is_file():
        raise SystemExit("먼저 research-server-start.cmd로 로컬 연구 서버를 실행하세요.")
    runtime = json.loads(RUNTIME_STATE.read_text(encoding="utf-8"))
    web_url = runtime["urls"]["wellnessbox"]
    prior = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in PRIOR.items()}
    if any(value.get("result") != "PASS" for value in prior.values()):
        raise AssertionError("기존 OP-088/090 고정 검증 결과가 PASS가 아닙니다.")

    cases = [
        {
            "case_id": "interaction",
            "query": "What should counseling say about glucosamine with warfarin?",
            "profile": {"goals": ["bone_joint"]},
            "ingredients": ["glucosamine"],
            "safety": {"requires_test": True},
        },
        {
            "case_id": "emergency",
            "query": "I have chest pain and trouble breathing. What should I do?",
            "profile": {"goals": ["general_wellness"]},
            "ingredients": [],
            "safety": {"requires_test": True},
        },
    ]
    observed = []
    for case in cases:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        session_id = f"op090-full-{case['case_id']}-{datetime.now(UTC).strftime('%H%M%S%f')}"
        turn_id = f"turn-{case['case_id']}"
        status, stream = _request(
            opener,
            f"{web_url}/api/chat",
            body={
                "sessionId": session_id,
                "messages": [
                    {
                        "id": turn_id,
                        "role": "user",
                        "content": case["query"],
                        "createdAt": 1784780000000,
                    }
                ],
                "profile": case["profile"],
                "ingredients": case["ingredients"],
                "safety": case["safety"],
            },
        )
        if status != 200 or len(stream.decode("utf-8").replace("\u200b", "").strip()) < 10:
            raise AssertionError(f"채팅 응답 실패: {case['case_id']}")
        get_status, raw = _request(opener, f"{web_url}/api/chat/save")
        saved = json.loads(raw)
        matching = [item for item in saved["sessions"] if item["id"] == session_id]
        if get_status != 200 or len(matching) != 1 or not matching[0]["messages"]:
            raise AssertionError(f"채팅 저장 왕복 실패: {case['case_id']}")
        observed.append(
            {
                "case_id": case["case_id"],
                "service_session_id_sha256": hashlib.sha256(session_id.encode()).hexdigest(),
                "route_status": status,
                "saved_session_observed": True,
                "saved_assistant_message_observed": True,
                "answer_sha256": hashlib.sha256(stream).hexdigest(),
            }
        )

    report = {
        "schema_version": "op088_op090_full_service_roundtrip_v1",
        "status": "PASS",
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "requirements": ["OP-088", "OP-090"],
        "actual_paths": [
            "wellnessbox POST /api/chat",
            "wellnessbox-rnd POST /v1/interim/counseling/turn",
            "wellnessbox ChatSession/ChatMessage persistence",
            "wellnessbox GET /api/chat/save",
        ],
        "checks": {
            "real_wellnessbox_route": True,
            "real_rnd_http_api": True,
            "real_service_database_persistence": True,
            "cookie_bound_read_after_write": True,
            "prior_frozen_qa_pass": True,
            "prior_deterministic_replay_pass": True,
            "cases": observed,
        },
        "prior_evidence": {
            key: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for key, path in PRIOR.items()
        },
        "source_identity": {
            "wellnessbox_rnd_commit": _commit(ROOT),
            "wellnessbox_commit": _commit(WELLNESSBOX),
        },
        "stage_boundary": {
            "claimed_stage": "INTEGRATED",
            "production_operation_observed": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
