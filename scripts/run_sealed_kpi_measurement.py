"""Run one sealed answer-key KPI as a research-phase internal measurement."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.evals.reference_standard import write_json  # noqa: E402
from wellnessbox_rnd.evals.sealed_kpi_measurement import (  # noqa: E402
    load_json,
    run_kpi1_measurement,
    run_kpi3_measurement,
    run_kpi4_measurement,
    run_kpi5_measurement,
)

ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--indicator",
        required=True,
        choices=("KPI-1", "KPI-3", "KPI-4", "KPI-5"),
    )
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    slug = args.indicator.lower().replace("-", "")
    seal = load_json(
        ROOT / f"data/original_plan/kpi/seals/{slug}_reference_seal_v1.json"
    )
    workbench = load_json(
        ROOT / f"data/original_plan/kpi/workbench/{slug}_workbench_v1.json"
    )
    measurement = {
        "KPI-1": run_kpi1_measurement,
        "KPI-3": run_kpi3_measurement,
        "KPI-4": run_kpi4_measurement,
        "KPI-5": run_kpi5_measurement,
    }[args.indicator]
    result = measurement(seal=seal, drafts=list(workbench["drafts"]))
    output = Path(args.output) if args.output else (
        ROOT
        / f"data/original_plan/kpi/measurements/{slug}_internal_measurement_v1.json"
    )
    write_json(output, result)
    print(
        json.dumps(
            {
                "status": "READY",
                "indicator_id": result["indicator_id"],
                "output": str(output),
                "case_count": result["case_count"],
                "accuracy_pct": result.get("accuracy_pct", result.get("mean_score_pct")),
                "target_met": result["target_met"],
                "measurement_environment": result["measurement_environment"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
