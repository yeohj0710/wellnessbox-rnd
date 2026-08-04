"""Add truthful packet segments to already merged KPI review records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.apply_kpi_replacements import (  # noqa: E402
    INDICATORS,
    _workbench_path,
    bind_composite_packet_record,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    load_workbench,
    save_workbench,
)


def build_bound_workbenches():
    result = {}
    for indicator_id in INDICATORS:
        workbench = load_workbench(_workbench_path(indicator_id))
        bind_composite_packet_record(workbench.ai_review, workbench)
        bind_composite_packet_record(workbench.primary_ai_draft, workbench)
        result[indicator_id] = workbench
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workbenches = build_bound_workbenches()
    report = {
        indicator_id: {
            "ai_review_segment_count": len(
                workbench.ai_review.get("packet_segments", [])
            ),
            "primary_segment_count": len(
                workbench.primary_ai_draft.get("packet_segments", [])
            ),
        }
        for indicator_id, workbench in workbenches.items()
    }
    if args.apply:
        for indicator_id, workbench in workbenches.items():
            save_workbench(_workbench_path(indicator_id), workbench)
    print(json.dumps({"status": "APPLIED" if args.apply else "READY", **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
