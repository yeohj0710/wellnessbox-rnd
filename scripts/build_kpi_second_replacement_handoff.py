"""Build the two-case Anthropic handoff after final replacement rejections."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_handoff import (  # noqa: E402
    ANTHROPIC_MODEL_ID,
    OUTPUT_DIR,
    _engine_logic_paths,
    _workbench,
    build_candidates,
    build_kpi1_replacements,
)
from scripts.import_kpi_replacement_final_review import (  # noqa: E402
    DECISIONS_PATH,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    build_external_ai_request,
)
from wellnessbox_rnd.evals.answer_key_workbench import Workbench  # noqa: E402
from wellnessbox_rnd.evals.reference_corpus_drafters import (  # noqa: E402
    load_extract,
)

SECOND_DIR = OUTPUT_DIR / "second_replacement"
CANDIDATES_PATH = SECOND_DIR / "kpi1_second_replacement_candidates_v1.json"
REQUEST_PATH = SECOND_DIR / "kpi1_anthropic_review_request.json"
PACKAGE_PATH = SECOND_DIR / "kpi1_second_replacement_claude_package.zip"
IDENTITY_PATH = OUTPUT_DIR / "responses" / "reviewer_identity_selection.json"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _canonical_json_sha256(payload: dict[str, Any]) -> str:
    content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    return hashlib.sha256(content).hexdigest()


def build_candidates_and_request() -> tuple[dict[str, Any], dict[str, Any]]:
    decisions = _read_json(DECISIONS_PATH)
    rejected = decisions.get("replacement_required_case_ids", [])
    if rejected != ["kpi1-repl-022", "kpi1-repl-027"]:
        raise ValueError("second_replacement_rejected_case_set_changed")
    first_round = build_candidates()["KPI-1"]
    drafts = build_kpi1_replacements(
        _workbench("KPI-1"),
        load_extract(ROOT),
        _engine_logic_paths(),
        count=len(rejected),
        case_prefix="kpi1-repl2",
        excluded_prompts={draft.prompt for draft in first_round},
    )
    temporary = Workbench("KPI-1", drafts)
    request = build_external_ai_request(
        temporary,
        required_blinded_from=_engine_logic_paths(),
        requested_role="review",
        required_provider_family="anthropic",
    )
    request["blindness_contract"]["allowed_model_ids"] = [ANTHROPIC_MODEL_ID]
    request["instructions"][1] = (
        f"reviewing_agent에는 {ANTHROPIC_MODEL_ID}를 정확히 쓴다."
    )
    request["response_skeleton"]["reviewing_agent"] = ANTHROPIC_MODEL_ID
    request_payload = {
        key: value for key, value in request.items() if key != "request_sha256"
    }
    request["request_sha256"] = hashlib.sha256(
        json.dumps(
            request_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    candidates = {
        "schema_version": "kpi_second_replacement_candidates_v1",
        "source_final_decisions_sha256": _canonical_json_sha256(decisions),
        "replaces_rejected_case_ids": rejected,
        "count": len(drafts),
        "cases": [asdict(draft) for draft in drafts],
    }
    return candidates, request


def _bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    candidates, request = build_candidates_and_request()
    SECOND_DIR.mkdir(parents=True, exist_ok=True)
    candidate_bytes = _bytes(candidates)
    request_bytes = _bytes(request)
    CANDIDATES_PATH.write_bytes(candidate_bytes)
    REQUEST_PATH.write_bytes(request_bytes)
    files = {
        CANDIDATES_PATH.name: candidate_bytes,
        REQUEST_PATH.name: request_bytes,
        IDENTITY_PATH.name: IDENTITY_PATH.read_bytes(),
        "START_HERE.txt": (
            "kpi1_anthropic_review_request.json의 instructions와 "
            "response_skeleton에 맞춰 kpi1_response.json을 작성합니다.\n"
            "엔진 파일과 엔진 출력은 열지 않습니다.\n"
        ).encode(),
        "MAKE_RETURN_ZIP.cmd": (
            b"@echo off\r\n"
            b"setlocal\r\n"
            b'cd /d "%~dp0"\r\n'
            b"powershell -NoProfile -ExecutionPolicy Bypass -Command "
            b'"Compress-Archive -LiteralPath '
            b"'kpi1_response.json','reviewer_identity_selection.json' "
            b"-DestinationPath 'kpi1_second_replacement_completed.zip' -Force\"\r\n"
        ),
    }
    with zipfile.ZipFile(PACKAGE_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    print(
        json.dumps(
            {
                "status": "READY_FOR_ANTHROPIC_REVIEW",
                "case_count": candidates["count"],
                "package": str(PACKAGE_PATH),
                "package_sha256": hashlib.sha256(PACKAGE_PATH.read_bytes()).hexdigest(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
