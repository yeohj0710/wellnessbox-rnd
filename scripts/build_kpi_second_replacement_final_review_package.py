"""Build the final two-row decision package for KPI-1 replacements."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_final_review_package import (  # noqa: E402
    CSV_FIELDS,
    IDENTITY_NAME,
)
from scripts.build_kpi_second_replacement_handoff import (  # noqa: E402
    APPLICATION_REPORT,
    CANDIDATES_PATH,
    SECOND_DIR,
)
from scripts.import_kpi_second_replacement_response import (  # noqa: E402
    RESPONSE_DIR,
    STAGING_PATH,
)

FINAL_DIR = SECOND_DIR / "final_review"
REVIEW_CSV_NAME = "kpi1_second_replacement_review.csv"
PACKAGE_PATH = SECOND_DIR / "kpi1_second_replacement_final_review_package.zip"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _joined(values: list[str]) -> str:
    return "|".join(sorted(values))


def build_rows() -> tuple[list[dict[str, str]], dict[str, Any]]:
    staging = _read_json(STAGING_PATH)
    if staging.get("status") != "READY_FOR_FINAL_REVIEW_PACKAGE":
        raise ValueError("second_replacement_staging_not_ready")
    candidates = _read_json(CANDIDATES_PATH)
    drafts = {item["case_id"]: item for item in candidates.get("cases", [])}
    reviews = staging.get("validated_record", {}).get("cases", {})
    required = staging.get("review_plan", {}).get("required_detail_ids", [])
    if required != ["kpi1-repl2-001", "kpi1-repl2-002"]:
        raise ValueError("second_replacement_required_case_set_changed")
    if set(drafts) != set(required) or set(reviews) != set(required):
        raise ValueError("second_replacement_case_set_mismatch")

    rows: list[dict[str, str]] = []
    for case_id in required:
        draft = drafts[case_id]
        review = reviews[case_id]
        answer_a = sorted(draft["draft_answer"])
        answer_b = sorted(review["proposed_answer"])
        if answer_a == answer_b:
            recommendation_label = "A"
            recommendation = answer_a
            recommendation_basis = "서로 다른 제공자 계열의 참조안 일치"
        else:
            recommendation_label = "B"
            recommendation = answer_b
            recommendation_basis = (
                f"독립 2차 의견의 기록된 신뢰도({float(review['confidence']):.2f})"
            )
        rows.append(
            {
                "indicator_id": "KPI-1",
                "case_id": case_id,
                "prompt": str(draft["prompt"]),
                "참조안_A": _joined(answer_a),
                "참조안_A_근거": str(draft.get("draft_rationale", "")),
                "참조안_A_신뢰도": "",
                "참조안_A_표시": "",
                "참조안_B": _joined(answer_b),
                "참조안_B_근거": str(review.get("rationale", "")),
                "참조안_B_신뢰도": str(review.get("confidence", "")),
                "참조안_B_표시": _joined(review.get("flags", [])),
                "보조안_C": "",
                "보조안_C_근거": "",
                "보조안_C_신뢰도": "",
                "보조안_C_표시": "",
                "권고_선택": recommendation_label,
                "권고_정답": _joined(recommendation),
                "권고_근거": recommendation_basis,
                "결정": "",
                "수정_정답": "",
                "메모": "",
                "시작_시각": "",
                "종료_시각": "",
            }
        )
    return rows, {
        "schema_version": "kpi_second_replacement_final_review_summary_v1",
        "case_count": len(rows),
        "required_review_count": len(rows),
        "recommendation_counts": {
            label: sum(row["권고_선택"] == label for row in rows)
            for label in ("A", "B")
        },
        "option_c_available": False,
    }


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + stream.getvalue()).encode()


def _return_script_bytes() -> bytes:
    return (
        b"@echo off\r\n"
        b"setlocal\r\n"
        b'cd /d "%~dp0"\r\n'
        b"powershell -NoProfile -ExecutionPolicy Bypass -Command "
        b'"Compress-Archive -LiteralPath '
        b"'kpi1_second_replacement_review.csv','reviewer_identity_selection.json' "
        b"-DestinationPath 'kpi1_second_replacement_final_review_completed.zip' -Force\"\r\n"
    )


def _write_zip(files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(PACKAGE_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def main() -> int:
    if APPLICATION_REPORT.is_file() and PACKAGE_PATH.is_file():
        application = _read_json(APPLICATION_REPORT)
        if application.get("status") == "APPLIED_ALL_REPLACEMENTS":
            print(
                json.dumps(
                    {
                        "status": "ARCHIVED_AFTER_APPLICATION",
                        "package": str(PACKAGE_PATH),
                        "package_sha256": hashlib.sha256(
                            PACKAGE_PATH.read_bytes()
                        ).hexdigest(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
    rows, summary = build_rows()
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    csv_bytes = _csv_bytes(rows)
    identity_bytes = (RESPONSE_DIR / IDENTITY_NAME).read_bytes()
    summary["review_csv_sha256"] = hashlib.sha256(csv_bytes).hexdigest()
    files = {
        REVIEW_CSV_NAME: csv_bytes,
        IDENTITY_NAME: identity_bytes,
        "START_HERE.txt": (
            "두 행의 참조안과 권고안을 확인합니다.\n"
            "결정에는 ACCEPT, EDIT, REJECT 중 하나를 기록합니다.\n"
            "EDIT이면 수정_정답에 값을 |로 구분해 기록합니다.\n"
            "시작_시각과 종료_시각은 시간대가 포함된 ISO 8601 형식으로 기록합니다.\n"
        ).encode(),
        "MAKE_RETURN_ZIP.cmd": _return_script_bytes(),
        "SUMMARY.json": (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode(),
    }
    for name, content in files.items():
        (FINAL_DIR / name).write_bytes(content)
    _write_zip(files)
    print(
        json.dumps(
            {
                "status": "READY_FOR_FINAL_REVIEW",
                "case_count": len(rows),
                "package": str(PACKAGE_PATH),
                "package_sha256": hashlib.sha256(PACKAGE_PATH.read_bytes()).hexdigest(),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
