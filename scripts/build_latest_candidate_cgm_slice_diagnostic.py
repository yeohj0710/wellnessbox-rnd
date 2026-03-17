from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.latest_candidate_cgm_slice_diagnostic import (
    build_latest_candidate_cgm_slice_diagnostic,
    load_json_artifact,
    write_latest_candidate_cgm_slice_diagnostic_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a bounded diagnostic proving whether the latest "
            "training_view_enforced_slice_balanced candidate is cgm-only bad"
        )
    )
    parser.add_argument(
        "--compare-report",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
        help="Latest candidate replay compare JSON path",
    )
    parser.add_argument(
        "--final-compare-report",
        default="artifacts/reports/final_kpi_compare_report_v1.json",
        help="Readable final compare JSON path",
    )
    parser.add_argument(
        "--cgm-feature-audit-report",
        default="artifacts/reports/cgm_combined_replay_feature_audit_v1.json",
        help="CGM combined replay feature audit JSON path",
    )
    parser.add_argument(
        "--cgm-geometry-report",
        default="artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json",
        help="CGM final-step geometry calibration JSON path",
    )
    parser.add_argument(
        "--cgm-slice-bridge-report",
        default="artifacts/reports/cgm_slice_bridge_summary_v1.json",
        help="CGM slice bridge summary JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/latest_candidate_cgm_slice_diagnostic_v1.json",
        help="Output diagnostic JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/latest_candidate_cgm_slice_diagnostic_v1.md",
        help="Output diagnostic markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    diagnostic = build_latest_candidate_cgm_slice_diagnostic(
        compare_report=load_json_artifact(args.compare_report),
        compare_report_path=args.compare_report,
        final_compare_report=load_json_artifact(args.final_compare_report),
        final_compare_report_path=args.final_compare_report,
        cgm_feature_audit_report=load_json_artifact(args.cgm_feature_audit_report),
        cgm_feature_audit_report_path=args.cgm_feature_audit_report,
        cgm_geometry_report=load_json_artifact(args.cgm_geometry_report),
        cgm_geometry_report_path=args.cgm_geometry_report,
        cgm_slice_bridge_report=load_json_artifact(args.cgm_slice_bridge_report),
        cgm_slice_bridge_report_path=args.cgm_slice_bridge_report,
    )
    write_latest_candidate_cgm_slice_diagnostic_files(
        diagnostic=diagnostic,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(diagnostic, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
