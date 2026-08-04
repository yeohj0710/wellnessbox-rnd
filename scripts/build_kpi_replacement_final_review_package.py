"""Build the 65-case replacement review package with prefilled recommendations."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_handoff import (  # noqa: E402
    OUTPUT_DIR,
    REQUEST_NAMES,
    RESPONSE_NAMES,
    build_candidates,
)
from scripts.finalize_kpi_replacement_staging import (  # noqa: E402
    OPENAI_MODEL_ID,
    OPENAI_SOURCE_ZIP,
)
from scripts.import_kpi_replacement_responses import (  # noqa: E402
    STAGING_PATH,
    SnapshotZip,
    _load_json,
    _required_blinded_from,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    build_adaptive_review_plan,
)
from wellnessbox_rnd.evals.answer_key_workbench import Workbench  # noqa: E402

FINAL_REVIEW_DIR = OUTPUT_DIR / "final_review"
FINAL_REVIEW_ZIP = OUTPUT_DIR / "kpi_replacement_final_review_package.zip"
REVIEW_CSV_NAME = "kpi_replacement_review.csv"
IDENTITY_NAME = "reviewer_identity_selection.json"
INDICATORS = ("KPI-1", "KPI-4", "KPI-5")
CSV_FIELDS = (
    "indicator_id",
    "case_id",
    "prompt",
    "참조안_A",
    "참조안_A_근거",
    "참조안_A_신뢰도",
    "참조안_A_표시",
    "참조안_B",
    "참조안_B_근거",
    "참조안_B_신뢰도",
    "참조안_B_표시",
    "보조안_C",
    "보조안_C_근거",
    "보조안_C_신뢰도",
    "보조안_C_표시",
    "권고_선택",
    "권고_정답",
    "권고_근거",
    "결정",
    "수정_정답",
    "메모",
    "시작_시각",
    "종료_시각",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _joined(values: list[str]) -> str:
    return "|".join(values)


def _validate_supporting_responses() -> dict[str, dict[str, dict[str, Any]]]:
    reader = SnapshotZip(OPENAI_SOURCE_ZIP)
    result: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        for indicator_id in ("KPI-1", "KPI-5"):
            response, _ = _load_json(reader, RESPONSE_NAMES[indicator_id])
            if str(response.get("reviewing_agent", "")).casefold() != OPENAI_MODEL_ID:
                raise ValueError(f"{indicator_id}:supporting_agent_invalid")
            if response.get("engine_output_consulted") is not False:
                raise ValueError(f"{indicator_id}:supporting_response_consulted_engine")
            request = _read_json(OUTPUT_DIR / REQUEST_NAMES[indicator_id])
            if response.get("packet_sha256") != request["packet"]["packet_sha256"]:
                raise ValueError(f"{indicator_id}:supporting_packet_sha256_mismatch")
            required_blind = set(_required_blinded_from(request))
            if not required_blind.issubset(set(response.get("blinded_from", []))):
                raise ValueError(f"{indicator_id}:supporting_blinded_paths_missing")
            vocabulary = set(request["packet"]["answer_vocabulary"])
            expected_ids = {
                item["case_id"] for item in request["packet"]["cases"]
            }
            cases: dict[str, dict[str, Any]] = {}
            for item in response.get("cases", []):
                case_id = str(item.get("case_id", "")).strip()
                answer = sorted(
                    {
                        str(value).strip()
                        for value in item.get("proposed_answer", [])
                        if str(value).strip()
                    }
                )
                if not case_id or case_id in cases or not answer:
                    raise ValueError(f"{indicator_id}:supporting_case_invalid")
                if not set(answer).issubset(vocabulary):
                    raise ValueError(
                        f"{indicator_id}:supporting_answer_outside_vocabulary:{case_id}"
                    )
                confidence = float(item.get("confidence"))
                if not 0.0 <= confidence <= 1.0:
                    raise ValueError(
                        f"{indicator_id}:supporting_confidence_invalid:{case_id}"
                    )
                if not isinstance(item.get("flags", []), list):
                    raise ValueError(f"{indicator_id}:supporting_flags_invalid:{case_id}")
                cases[case_id] = {
                    "proposed_answer": answer,
                    "confidence": confidence,
                    "flags": sorted(
                        {
                            str(flag).strip()
                            for flag in item.get("flags", [])
                            if str(flag).strip()
                        }
                    ),
                    "rationale": str(item.get("rationale", "")).strip(),
                }
            if set(cases) != expected_ids:
                raise ValueError(f"{indicator_id}:supporting_case_set_mismatch")
            result[indicator_id] = cases
    finally:
        reader.close()
    return result


def build_workbenches(
    staging: dict[str, Any],
) -> dict[str, Workbench]:
    candidates = build_candidates()
    workbenches: dict[str, Workbench] = {}
    for indicator_id in INDICATORS:
        workbench = Workbench(indicator_id, deepcopy(candidates[indicator_id]))
        response = staging["responses"][indicator_id]
        if indicator_id == "KPI-4":
            primary = response["validated_record"]
            for draft in workbench.drafts:
                item = primary["cases"][draft.case_id]
                draft.draft_answer = list(item["proposed_answer"])
                draft.draft_rationale = str(item.get("rationale", ""))
                draft.draft_source = str(primary["draft_source"])
                draft.drafting_agent = str(primary["drafting_agent"])
                draft.blinded_from = list(primary["blinded_from"])
            workbench.primary_ai_draft = deepcopy(primary)
            workbench.ai_review = deepcopy(
                response["openai_second_opinion"]["validated_record"]
            )
        else:
            workbench.ai_review = deepcopy(response["validated_record"])
        workbenches[indicator_id] = workbench
    return workbenches


def _recommend(
    *,
    answer_a: list[str],
    confidence_a: float | None,
    answer_b: list[str],
    confidence_b: float,
    answer_c: list[str],
    confidence_c: float | None,
) -> tuple[str, list[str], str]:
    if answer_a == answer_b:
        return "A", answer_a, "서로 다른 제공자 계열의 참조안 일치"
    if answer_c and answer_b == answer_c:
        return "B", answer_b, "Anthropic 의견과 OpenAI 보조안 일치"
    options = [
        (confidence_a if confidence_a is not None else -1.0, "A", answer_a),
        (confidence_b, "B", answer_b),
    ]
    if answer_c and confidence_c is not None:
        options.append((confidence_c, "C", answer_c))
    confidence, label, answer = max(
        options,
        key=lambda item: (item[0], item[1] == "B", item[1] == "A"),
    )
    return label, answer, f"기록된 신뢰도 비교({confidence:.2f})"


def build_rows() -> tuple[list[dict[str, str]], dict[str, Any]]:
    staging = _read_json(STAGING_PATH)
    if staging.get("status") != "READY_FOR_FINAL_REVIEW_PACKAGE":
        raise ValueError("replacement_staging_not_ready_for_final_review")
    workbenches = build_workbenches(staging)
    supporting = _validate_supporting_responses()
    rows: list[dict[str, str]] = []
    summaries: list[dict[str, Any]] = []
    recommendation_counts: dict[str, int] = {}
    for indicator_id in INDICATORS:
        workbench = workbenches[indicator_id]
        plan = build_adaptive_review_plan(workbench)
        if plan.get("status") != "REVIEW_REQUIRED":
            raise ValueError(f"{indicator_id}:replacement_review_plan_not_required")
        required_ids = set(plan["required_detail_ids"])
        primary_cases = (workbench.primary_ai_draft or {}).get("cases", {})
        review_cases = workbench.ai_review["cases"]
        for draft in workbench.drafts:
            if draft.case_id not in required_ids:
                continue
            primary = primary_cases.get(draft.case_id, {})
            review = review_cases[draft.case_id]
            support = supporting.get(indicator_id, {}).get(draft.case_id, {})
            answer_a = sorted(draft.draft_answer)
            answer_b = sorted(review["proposed_answer"])
            answer_c = sorted(support.get("proposed_answer", []))
            label, recommendation, basis = _recommend(
                answer_a=answer_a,
                confidence_a=(
                    float(primary["confidence"]) if primary else None
                ),
                answer_b=answer_b,
                confidence_b=float(review["confidence"]),
                answer_c=answer_c,
                confidence_c=(
                    float(support["confidence"]) if support else None
                ),
            )
            recommendation_counts[label] = recommendation_counts.get(label, 0) + 1
            rows.append(
                {
                    "indicator_id": indicator_id,
                    "case_id": draft.case_id,
                    "prompt": draft.prompt,
                    "참조안_A": _joined(answer_a),
                    "참조안_A_근거": str(
                        primary.get("rationale", draft.draft_rationale)
                    ),
                    "참조안_A_신뢰도": str(primary.get("confidence", "")),
                    "참조안_A_표시": _joined(primary.get("flags", [])),
                    "참조안_B": _joined(answer_b),
                    "참조안_B_근거": str(review.get("rationale", "")),
                    "참조안_B_신뢰도": str(review.get("confidence", "")),
                    "참조안_B_표시": _joined(review.get("flags", [])),
                    "보조안_C": _joined(answer_c),
                    "보조안_C_근거": str(support.get("rationale", "")),
                    "보조안_C_신뢰도": str(support.get("confidence", "")),
                    "보조안_C_표시": _joined(support.get("flags", [])),
                    "권고_선택": label,
                    "권고_정답": _joined(recommendation),
                    "권고_근거": basis,
                    "결정": "",
                    "수정_정답": "",
                    "메모": "",
                    "시작_시각": "",
                    "종료_시각": "",
                }
            )
        summaries.append(
            {
                "indicator_id": indicator_id,
                "case_count": plan["case_count"],
                "agreement_count": plan["agreement_count"],
                "disagreement_count": plan["disagreement_count"],
                "flagged_count": plan["flagged_count"],
                "required_review_count": len(required_ids),
            }
        )
    return rows, {
        "schema_version": "kpi_replacement_final_review_summary_v1",
        "total_case_count": sum(item["case_count"] for item in summaries),
        "required_review_count": len(rows),
        "recommendation_counts": recommendation_counts,
        "indicators": summaries,
    }


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def _instructions_bytes() -> bytes:
    return (
        "KPI 교체 사례 검토 자료\n\n"
        "각 행에는 참조안과 권고안이 입력돼 있습니다.\n"
        "- 권고안이 적절하면 결정에 ACCEPT를 입력합니다.\n"
        "- 수정이 필요하면 결정에 EDIT를 입력하고 수정_정답에 값을 |로 구분해 씁니다.\n"
        "- 사용할 수 없으면 결정에 REJECT를 입력합니다.\n"
        "- 시작_시각과 종료_시각은 시간대가 있는 ISO 8601 형식으로 기록합니다.\n"
        "- 종료_시각은 시작_시각보다 최소 1초 뒤여야 합니다.\n\n"
        "작성 후 MAKE_RETURN_ZIP.cmd를 실행하고 생성된 "
        "kpi_replacement_final_review_completed.zip을 반환합니다.\n"
    ).encode()


def _return_script_bytes() -> bytes:
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        'cd /d "%~dp0"\r\n'
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        f"\"$files=@('{REVIEW_CSV_NAME}','{IDENTITY_NAME}'); "
        "$missing=@($files|Where-Object{-not(Test-Path -LiteralPath $_)}); "
        "if($missing){Write-Error ('Missing: '+($missing -join ', '));exit 2}; "
        "Compress-Archive -LiteralPath $files -DestinationPath "
        "'kpi_replacement_final_review_completed.zip' -Force\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "echo kpi_replacement_final_review_completed.zip\r\n"
    ).encode()


def _write_zip(files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(
        FINAL_REVIEW_ZIP, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def main() -> int:
    rows, summary = build_rows()
    FINAL_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    csv_bytes = _csv_bytes(rows)
    instructions = _instructions_bytes()
    return_script = _return_script_bytes()
    identity_bytes = (OUTPUT_DIR / "responses" / IDENTITY_NAME).read_bytes()
    summary["review_csv_sha256"] = hashlib.sha256(csv_bytes).hexdigest()
    summary_bytes = (
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    files = {
        REVIEW_CSV_NAME: csv_bytes,
        IDENTITY_NAME: identity_bytes,
        "START_HERE.txt": instructions,
        "MAKE_RETURN_ZIP.cmd": return_script,
        "SUMMARY.json": summary_bytes,
    }
    for name, content in files.items():
        (FINAL_REVIEW_DIR / name).write_bytes(content)
    _write_zip(files)
    print(
        json.dumps(
            {
                "status": "READY",
                "package": str(FINAL_REVIEW_ZIP),
                "package_sha256": hashlib.sha256(
                    FINAL_REVIEW_ZIP.read_bytes()
                ).hexdigest(),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
