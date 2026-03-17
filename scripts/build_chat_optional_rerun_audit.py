from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals.chat_optional_rerun_audit import (
    build_chat_optional_rerun_audit,
    load_json,
    write_chat_optional_rerun_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a compact audit for whether the optional chat/OpenAI "
            "live rerun is still needed."
        )
    )
    parser.add_argument(
        "--chat-live-smoke-report",
        default="artifacts/reports/chat_openai_adapter_smoke_live_v1.json",
        help="Latest live chat/OpenAI smoke report JSON path.",
    )
    parser.add_argument(
        "--learned-boundary-audit",
        default="artifacts/reports/learned_runtime_boundary_audit_v1.json",
        help="Learned runtime boundary audit JSON path.",
    )
    parser.add_argument(
        "--design-sanity-audit",
        default="artifacts/reports/design_sanity_audit_v1.json",
        help="Design sanity audit JSON path.",
    )
    parser.add_argument(
        "--baseline-candidate-kpi-summary",
        default="artifacts/reports/baseline_candidate_kpi_summary_v1.json",
        help="Baseline/candidate KPI summary JSON path.",
    )
    parser.add_argument(
        "--final-kpi-compare-report",
        default="artifacts/reports/final_kpi_compare_report_v1.json",
        help="Readable final KPI compare report JSON path.",
    )
    parser.add_argument(
        "--effect-candidate-reject-decision",
        default="artifacts/reports/latest_effect_candidate_reject_decision_v1.json",
        help="Latest candidate reject/keep-baseline decision JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/chat_optional_rerun_need_audit_v1.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/chat_optional_rerun_need_audit_v1.md",
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_chat_optional_rerun_audit(
        chat_live_smoke_report=load_json(args.chat_live_smoke_report),
        chat_live_smoke_report_path=args.chat_live_smoke_report,
        learned_boundary_audit=load_json(args.learned_boundary_audit),
        learned_boundary_audit_path=args.learned_boundary_audit,
        design_sanity_audit=load_json(args.design_sanity_audit),
        design_sanity_audit_path=args.design_sanity_audit,
        baseline_candidate_kpi_summary=load_json(args.baseline_candidate_kpi_summary),
        baseline_candidate_kpi_summary_path=args.baseline_candidate_kpi_summary,
        final_kpi_compare_report=load_json(args.final_kpi_compare_report),
        final_kpi_compare_report_path=args.final_kpi_compare_report,
        effect_candidate_reject_decision=load_json(
            args.effect_candidate_reject_decision
        ),
        effect_candidate_reject_decision_path=args.effect_candidate_reject_decision,
    )
    write_chat_optional_rerun_audit_files(
        audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
