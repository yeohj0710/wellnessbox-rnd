from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

attribution_module = import_module(
    "wellnessbox_rnd.evals.non_cgm_continue_to_monitor_threshold_cross_attribution"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only attribution report for the non_cgm "
            "continue_plan->monitor_only threshold-cross family on the current "
            "smallest surface."
        )
    )
    parser.add_argument(
        "--family-diagnostic",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
    )
    parser.add_argument(
        "--subgroup-diagnostic",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json",
    )
    parser.add_argument(
        "--mid-margin-diagnostic",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json",
    )
    parser.add_argument(
        "--small-drop-diagnostic",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
    )
    parser.add_argument(
        "--regimen-count-counterfactual",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.json"
        ),
    )
    parser.add_argument(
        "--trajectory-step-counterfactual",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
    )
    parser.add_argument(
        "--half-offset-counterfactual",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
    )
    parser.add_argument(
        "--local-contract",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_local_contract_v1.json"
        ),
    )
    parser.add_argument(
        "--final-kpi-compare-report",
        default="artifacts/reports/final_kpi_compare_report_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_continue_to_monitor_threshold_cross_attribution_v1.md"
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = attribution_module.build_non_cgm_continue_to_monitor_threshold_cross_attribution(
        family_diagnostic=attribution_module.load_json_artifact(args.family_diagnostic),
        family_diagnostic_path=args.family_diagnostic,
        subgroup_diagnostic=attribution_module.load_json_artifact(args.subgroup_diagnostic),
        subgroup_diagnostic_path=args.subgroup_diagnostic,
        mid_margin_diagnostic=attribution_module.load_json_artifact(args.mid_margin_diagnostic),
        mid_margin_diagnostic_path=args.mid_margin_diagnostic,
        small_drop_diagnostic=attribution_module.load_json_artifact(args.small_drop_diagnostic),
        small_drop_diagnostic_path=args.small_drop_diagnostic,
        regimen_count_counterfactual=attribution_module.load_json_artifact(
            args.regimen_count_counterfactual
        ),
        regimen_count_counterfactual_path=args.regimen_count_counterfactual,
        trajectory_step_counterfactual=attribution_module.load_json_artifact(
            args.trajectory_step_counterfactual
        ),
        trajectory_step_counterfactual_path=args.trajectory_step_counterfactual,
        half_offset_counterfactual=attribution_module.load_json_artifact(
            args.half_offset_counterfactual
        ),
        half_offset_counterfactual_path=args.half_offset_counterfactual,
        local_contract=attribution_module.load_json_artifact(args.local_contract),
        local_contract_path=args.local_contract,
        final_kpi_compare_report=attribution_module.load_json_artifact(
            args.final_kpi_compare_report
        ),
        final_kpi_compare_report_path=args.final_kpi_compare_report,
    )
    attribution_module.write_non_cgm_continue_to_monitor_threshold_cross_attribution_files(
        report=report,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
