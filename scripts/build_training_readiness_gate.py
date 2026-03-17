from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.evals.training_readiness_gate import (
    build_training_readiness_gate,
    load_json,
    write_training_readiness_gate_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a strict GO/NO-GO memo for the next narrow effect-model "
            "training rerun."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    parser.add_argument(
        "--case-count",
        type=int,
        default=480,
    )
    parser.add_argument(
        "--replay-attribution",
        default="artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.json",
    )
    parser.add_argument(
        "--synthetic-validity-followup",
        default="artifacts/reports/synthetic_validity_followup_single_item_v1.json",
    )
    parser.add_argument(
        "--cgm-core-summary",
        default="artifacts/reports/core_kpi_path_summary_v1.json",
    )
    parser.add_argument(
        "--requested-cgm-geometry-audit",
        default="artifacts/reports/cgm_outside_band_final_step_geometry_v2.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/training_readiness_gate_v2.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/training_readiness_gate_v2.md",
    )
    return parser


def _load_optional_json(path: str) -> dict[str, object] | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    return load_json(file_path)


def main() -> int:
    args = build_parser().parse_args()
    report = build_training_readiness_gate(
        dataset_path=args.dataset,
        case_count=args.case_count,
        replay_attribution=load_json(args.replay_attribution),
        replay_attribution_path=args.replay_attribution,
        synthetic_validity_followup=load_json(args.synthetic_validity_followup),
        synthetic_validity_followup_path=args.synthetic_validity_followup,
        cgm_core_summary=load_json(args.cgm_core_summary),
        cgm_core_summary_path=args.cgm_core_summary,
        cgm_geometry_audit=_load_optional_json(args.requested_cgm_geometry_audit),
        cgm_geometry_audit_path=args.requested_cgm_geometry_audit,
    )
    write_training_readiness_gate_files(
        report=report,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "decision": report["gate_decision"]["decision"],
                "authorized_now": report["gate_decision"]["authorized_now"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
