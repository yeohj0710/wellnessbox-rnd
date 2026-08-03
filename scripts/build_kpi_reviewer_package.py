"""Build the offline KPI answer review package from imported cross-provider opinions."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from wellnessbox_rnd.evals.adaptive_answer_key_review import (
    build_adaptive_review_plan,
)
from wellnessbox_rnd.evals.answer_key_workbench import load_workbench

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
HANDOFF_DIR = ROOT / "data/original_plan/kpi/review_handoff"
OUTPUT_DIR = HANDOFF_DIR / "final_review_package"
OUTPUT_ZIP = HANDOFF_DIR / "kpi_final_review_package.zip"
INDICATORS = ("KPI-1", "KPI-3", "KPI-4", "KPI-5")
CSV_FIELDS = (
    "case_id",
    "prompt",
    "안_A",
    "안_A_근거",
    "안_A_신뢰도",
    "안_A_표시",
    "안_B",
    "안_B_근거",
    "안_B_신뢰도",
    "안_B_표시",
    "검토_선택",
    "최종_답",
    "검토_메모",
    "검토_시작_시각",
    "검토_종료_시각",
)


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def _workbench_path(indicator_id: str) -> Path:
    return WORKBENCH_DIR / f"{_slug(indicator_id)}_workbench_v1.json"


def _joined(values: list[str]) -> str:
    return "|".join(values)


def build_rows(indicator_id: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    workbench = load_workbench(_workbench_path(indicator_id))
    plan = build_adaptive_review_plan(workbench)
    if plan["status"] != "REVIEW_REQUIRED":
        raise ValueError(
            f"{indicator_id}:review_package_requires_review_required_status:"
            f"{plan['status']}"
        )

    required = set(plan["required_detail_ids"])
    primary_cases = (workbench.primary_ai_draft or {}).get("cases", {})
    review_cases = workbench.ai_review.get("cases", {})
    rows: list[dict[str, str]] = []
    for draft in workbench.drafts:
        if draft.case_id not in required:
            continue
        primary = primary_cases.get(draft.case_id, {})
        review = review_cases[draft.case_id]
        rows.append(
            {
                "case_id": draft.case_id,
                "prompt": draft.prompt,
                "안_A": _joined(draft.draft_answer),
                "안_A_근거": str(primary.get("rationale", draft.draft_rationale)),
                "안_A_신뢰도": str(primary.get("confidence", "")),
                "안_A_표시": _joined(primary.get("flags", [])),
                "안_B": _joined(review["proposed_answer"]),
                "안_B_근거": str(review.get("rationale", "")),
                "안_B_신뢰도": str(review.get("confidence", "")),
                "안_B_표시": _joined(review.get("flags", [])),
                "검토_선택": "",
                "최종_답": "",
                "검토_메모": "",
                "검토_시작_시각": "",
                "검토_종료_시각": "",
            }
        )

    summary = {
        "indicator_id": indicator_id,
        "case_count": plan["case_count"],
        "agreement_count": plan["agreement_count"],
        "disagreement_count": plan["disagreement_count"],
        "flagged_count": plan["flagged_count"],
        "required_review_count": len(rows),
        "option_a_agent": (
            (workbench.primary_ai_draft or {}).get("drafting_agent")
            or workbench.drafts[0].drafting_agent
        ),
        "option_b_agent": workbench.ai_review.get("reviewing_agent"),
    }
    return rows, summary


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def _write_zip(files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    package_files: dict[str, bytes] = {}
    for indicator_id in INDICATORS:
        rows, summary = build_rows(indicator_id)
        content = _csv_bytes(rows)
        name = f"{_slug(indicator_id)}_review.csv"
        (OUTPUT_DIR / name).write_bytes(content)
        summary["csv_sha256"] = hashlib.sha256(content).hexdigest()
        summaries.append(summary)
        package_files[name] = content

    instructions = (
        "KPI 정답 검토 자료\n\n"
        "1. CSV 파일을 하나씩 엽니다.\n"
        "2. 각 행에서 안 A와 안 B의 답·근거·표시를 비교합니다.\n"
        "3. 검토_선택에는 A, B, CUSTOM, REJECT 중 하나를 씁니다.\n"
        "4. CUSTOM이면 최종_답에 허용 답을 |로 구분해 씁니다.\n"
        "5. A 또는 B이면 최종_답은 비워도 됩니다.\n"
        "6. 검토 시작·종료 시각은 ISO 8601 형식으로 기록합니다.\n"
        "7. reviewer_details.json의 이름·소속·검토일을 채웁니다. "
        "qualification_stage 값은 바꾸지 않습니다.\n"
        "8. 네 CSV와 reviewer_details.json, seal_disposal_review.json을 "
        "한 ZIP으로 묶어 반환합니다.\n\n"
        "현재 검토 대상: KPI-1 100건, KPI-3 100건, "
        "KPI-4 100건, KPI-5 100건.\n"
    ).encode()
    summary_bytes = (
        json.dumps(
            {"schema_version": "kpi_reviewer_package_v1", "indicators": summaries},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    (OUTPUT_DIR / "START_HERE.txt").write_bytes(instructions)
    (OUTPUT_DIR / "SUMMARY.json").write_bytes(summary_bytes)
    package_files["START_HERE.txt"] = instructions
    package_files["SUMMARY.json"] = summary_bytes
    for template in ("reviewer_details.json", "seal_disposal_review.json"):
        content = (HANDOFF_DIR / template).read_bytes()
        package_files[template] = content

    _write_zip(package_files)
    print(
        json.dumps(
            {
                "status": "READY",
                "output": str(OUTPUT_ZIP),
                "required_review_count": sum(
                    item["required_review_count"] for item in summaries
                ),
                "indicators": summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
