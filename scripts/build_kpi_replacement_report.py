"""Build the canonical report for KPI cases rejected during final review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    Workbench,
    load_workbench,
)

INDICATORS = ("KPI-1", "KPI-3", "KPI-4", "KPI-5")
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
DEFAULT_REVIEW_ZIP = (
    ROOT
    / "data/original_plan/kpi/review_handoff/completed_review"
    / "kpi_completed_review.zip"
)
DEFAULT_OUTPUT = (
    ROOT
    / "data/original_plan/kpi/review_handoff/completed_review"
    / "kpi_replacement_required_v1.json"
)


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def _workbench_path(indicator_id: str) -> Path:
    return WORKBENCH_DIR / f"{_slug(indicator_id)}_workbench_v1.json"


def build_report(
    workbenches: dict[str, Workbench], *, review_zip_sha256: str
) -> dict[str, Any]:
    indicators: list[dict[str, Any]] = []
    total = 0
    for indicator_id in INDICATORS:
        workbench = workbenches[indicator_id]
        review_cases = workbench.ai_review.get("cases", {})
        rejected: list[dict[str, Any]] = []
        for draft in workbench.drafts:
            decision = workbench.decisions.get(draft.case_id)
            if decision is None or decision.action != "rejected":
                continue
            second = review_cases.get(draft.case_id, {})
            rejected.append(
                {
                    "case_id": draft.case_id,
                    "prompt": draft.prompt,
                    "draft_answer": draft.draft_answer,
                    "independent_opinion": second.get("proposed_answer", []),
                    "review_note": decision.note,
                    "decided_by": decision.decided_by,
                    "decided_at": decision.decided_at,
                    "replacement_status": "required",
                }
            )
        indicators.append(
            {
                "indicator_id": indicator_id,
                "rejected_count": len(rejected),
                "rejected_cases": rejected,
            }
        )
        total += len(rejected)
    return {
        "schema_version": "kpi_replacement_required_v1",
        "source_review_zip_sha256": review_zip_sha256,
        "replacement_required_count": total,
        "indicator_counts": {
            item["indicator_id"]: item["rejected_count"] for item in indicators
        },
        "seal_ready_indicators": [
            item["indicator_id"]
            for item in indicators
            if item["rejected_count"] == 0
        ],
        "replacement_required_indicators": [
            item["indicator_id"]
            for item in indicators
            if item["rejected_count"] > 0
        ],
        "indicators": indicators,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-zip", type=Path, default=DEFAULT_REVIEW_ZIP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.review_zip.is_file():
        raise SystemExit(f"review_zip_missing:{args.review_zip}")
    workbenches = {
        indicator_id: load_workbench(_workbench_path(indicator_id))
        for indicator_id in INDICATORS
    }
    report = build_report(
        workbenches,
        review_zip_sha256=hashlib.sha256(args.review_zip.read_bytes()).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "READY",
                "output": str(args.output),
                "replacement_required_count": report[
                    "replacement_required_count"
                ],
                "indicator_counts": report["indicator_counts"],
                "seal_ready_indicators": report["seal_ready_indicators"],
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
