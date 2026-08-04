"""Build one neutral identity-linkage package for the original KPI review batch."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.answer_key_workbench import load_workbench  # noqa: E402
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    load_registry,
    reviewer_identity_reference,
)

INDICATORS = ("KPI-1", "KPI-3", "KPI-4", "KPI-5")
EXPECTED_COUNTS = {"KPI-1": 51, "KPI-3": 100, "KPI-4": 93, "KPI-5": 91}
TOTAL_COUNT = 335
ANONYMOUS_REVIEWER = "비식별 검토자"
SOURCE_REVIEW_PATH = (
    ROOT
    / "data/original_plan/kpi/review_handoff/completed_review"
    / "kpi_completed_review.zip"
)
SOURCE_REVIEW_SHA256 = (
    "a9587f2c425510dc2490857de2ab67210b0c0b9894170db80e222563f1834e3c"
)
OUTPUT_DIR = ROOT / "data/original_plan/kpi/review_handoff/identity_linkage"
APPLICATION_PATH = (
    OUTPUT_DIR
    / "completed"
    / "kpi_original_review_identity_linkage_application_v1.json"
)
FORM_NAME = "kpi_original_review_identity_linkage.json"
PACKAGE_PATH = OUTPUT_DIR / "kpi_original_review_identity_linkage_input.zip"
RETURN_ZIP_NAME = "kpi_original_review_identity_linkage_completed.zip"


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def _workbench_path(root: Path, indicator_id: str) -> Path:
    return root / (
        "data/original_plan/kpi/workbench/"
        f"{_slug(indicator_id)}_workbench_v1.json"
    )


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def eligible_reviewer(root: Path = ROOT) -> dict[str, str]:
    registry = load_registry(root)
    eligible = [
        item
        for item in registry.get("registered_reviewers", [])
        if item.get("may_review_h005") is True
    ]
    if len(eligible) != 1:
        raise ValueError("expected_exactly_one_eligible_kpi_reviewer")
    item = eligible[0]
    return {
        "registered_name": str(item["name"]),
        "reviewer_identity_ref": reviewer_identity_reference(item),
        "qualification_stage": "pharmacist_candidate_preliminary_safety_review",
    }


def decision_scope(root: Path = ROOT) -> dict[str, Any]:
    scoped: dict[str, dict[str, Any]] = {}
    for indicator_id in INDICATORS:
        workbench = load_workbench(_workbench_path(root, indicator_id))
        decisions = {
            case_id: vars(decision)
            for case_id, decision in workbench.decisions.items()
            if decision.decided_by == ANONYMOUS_REVIEWER
            and not decision.reviewer_identity_ref
        }
        if len(decisions) != EXPECTED_COUNTS[indicator_id]:
            raise ValueError(
                f"{indicator_id}:anonymous_decision_count_changed:"
                f"{len(decisions)}:{EXPECTED_COUNTS[indicator_id]}"
            )
        scoped[indicator_id] = decisions
    return {
        "indicator_counts": EXPECTED_COUNTS,
        "total_decision_count": sum(len(items) for items in scoped.values()),
        "decision_scope_sha256": _canonical_sha256(scoped),
        "case_ids_sha256": _canonical_sha256(
            {
                indicator_id: sorted(items)
                for indicator_id, items in scoped.items()
            }
        ),
    }


def build_form(root: Path = ROOT) -> dict[str, Any]:
    source = root / SOURCE_REVIEW_PATH.relative_to(ROOT)
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_REVIEW_SHA256:
        raise ValueError("original_review_source_sha256_changed")
    identity = eligible_reviewer(root)
    application_path = root / APPLICATION_PATH.relative_to(ROOT)
    if application_path.is_file():
        application = json.loads(application_path.read_text(encoding="utf-8"))
        if application.get("status") != "APPLIED":
            raise ValueError("identity_link_application_status_invalid")
        scope = {
            "indicator_counts": application["indicator_counts"],
            "total_decision_count": application["total_decision_count"],
            "decision_scope_sha256": application["decision_scope_sha256"],
            "case_ids_sha256": application["case_ids_sha256"],
        }
    else:
        scope = decision_scope(root)
    if scope["total_decision_count"] != TOTAL_COUNT:
        raise ValueError("original_review_identity_scope_count_changed")
    return {
        "schema_version": "kpi_original_review_identity_linkage_v1",
        "source_review_zip_sha256": SOURCE_REVIEW_SHA256,
        "indicator_counts": scope["indicator_counts"],
        "total_decision_count": scope["total_decision_count"],
        "decision_scope_sha256": scope["decision_scope_sha256"],
        "case_ids_sha256": scope["case_ids_sha256"],
        "reviewer_identity_ref": identity["reviewer_identity_ref"],
        "qualification_stage": identity["qualification_stage"],
        "identity_link_status": "",
        "confirmed_at": "",
    }


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    form = build_form()
    summary = {
        "schema_version": "kpi_original_review_identity_linkage_summary_v1",
        "indicator_counts": form["indicator_counts"],
        "total_decision_count": form["total_decision_count"],
        "single_submission": True,
        "editable_fields": ["identity_link_status", "confirmed_at"],
        "allowed_identity_link_status": ["CONFIRMED", "NOT_CONFIRMED"],
    }
    files = {
        FORM_NAME: _json_bytes(form),
        "SUMMARY.json": _json_bytes(summary),
        "START_HERE.txt": (
            "kpi_original_review_identity_linkage.json에서 identity_link_status를 "
            "CONFIRMED 또는 NOT_CONFIRMED로 기록합니다.\n"
            "confirmed_at에는 시간대가 포함된 ISO 8601 시각을 기록합니다.\n"
            "MAKE_RETURN_ZIP.cmd를 실행하면 반환 ZIP이 생성됩니다.\n"
        ).encode(),
        "MAKE_RETURN_ZIP.cmd": (
            b"@echo off\r\n"
            b"setlocal\r\n"
            b'cd /d "%~dp0"\r\n'
            b"powershell -NoProfile -ExecutionPolicy Bypass -Command "
            b'"Compress-Archive -LiteralPath '
            + f"'{FORM_NAME}'".encode()
            + b" -DestinationPath '"
            + RETURN_ZIP_NAME.encode()
            + b"' -Force" + b'"\r\n'
        ),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (OUTPUT_DIR / name).write_bytes(content)
    with zipfile.ZipFile(PACKAGE_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    print(
        json.dumps(
            {
                "status": "READY",
                "package": str(PACKAGE_PATH),
                "package_sha256": hashlib.sha256(PACKAGE_PATH.read_bytes()).hexdigest(),
                "total_decision_count": TOTAL_COUNT,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
