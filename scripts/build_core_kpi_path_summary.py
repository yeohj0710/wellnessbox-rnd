from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.core_kpi_path_summary import (
    build_core_kpi_path_summary,
    load_json,
    write_core_kpi_path_summary_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a compact summary artifact for the current core KPI path."
    )
    parser.add_argument(
        "--final-kpi-compare-report",
        default="artifacts/reports/final_kpi_compare_report_v1.json",
    )
    parser.add_argument(
        "--baseline-followup-pro-event-contract",
        default="artifacts/reports/baseline_followup_pro_event_contract_v1.json",
    )
    parser.add_argument(
        "--pro-scoring-contract",
        default="artifacts/reports/pro_scoring_contract_v1.json",
    )
    parser.add_argument(
        "--weakest-slice-frozen-eval-audit",
        default="artifacts/reports/weakest_slice_frozen_eval_audit_v1.json",
    )
    parser.add_argument(
        "--cgm-geometry-summary",
        default="artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json",
    )
    parser.add_argument(
        "--learned-runtime-boundary-audit",
        default="artifacts/reports/learned_runtime_boundary_audit_v1.json",
    )
    parser.add_argument(
        "--latest-effect-candidate-reject-decision",
        default="artifacts/reports/latest_effect_candidate_reject_decision_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/core_kpi_path_summary_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/core_kpi_path_summary_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_core_kpi_path_summary(
        final_kpi_compare_report=load_json(args.final_kpi_compare_report),
        final_kpi_compare_report_path=args.final_kpi_compare_report,
        baseline_followup_pro_event_contract=load_json(
            args.baseline_followup_pro_event_contract
        ),
        baseline_followup_pro_event_contract_path=args.baseline_followup_pro_event_contract,
        pro_scoring_contract=load_json(args.pro_scoring_contract),
        pro_scoring_contract_path=args.pro_scoring_contract,
        weakest_slice_frozen_eval_audit=load_json(args.weakest_slice_frozen_eval_audit),
        weakest_slice_frozen_eval_audit_path=args.weakest_slice_frozen_eval_audit,
        cgm_geometry_summary=load_json(args.cgm_geometry_summary),
        cgm_geometry_summary_path=args.cgm_geometry_summary,
        learned_runtime_boundary_audit=load_json(args.learned_runtime_boundary_audit),
        learned_runtime_boundary_audit_path=args.learned_runtime_boundary_audit,
        latest_effect_candidate_reject_decision=load_json(
            args.latest_effect_candidate_reject_decision
        ),
        latest_effect_candidate_reject_decision_path=args.latest_effect_candidate_reject_decision,
    )
    write_core_kpi_path_summary_files(
        summary,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
