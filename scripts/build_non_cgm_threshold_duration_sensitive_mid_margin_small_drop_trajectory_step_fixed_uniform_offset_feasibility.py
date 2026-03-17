from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

feasibility_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_fixed_uniform_offset_feasibility"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only feasibility artifact for trajectory_step "
            "fixed-uniform-offset local handling inside the threshold_duration_sensitive "
            "mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--mode-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.json"
        ),
        help="Current local-handling mode decision JSON path.",
    )
    parser.add_argument(
        "--trajectory-step-counterfactual",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        help="Current trajectory_step counterfactual JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_feasibility_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_feasibility_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    feasibility = feasibility_module.build_trajectory_step_fixed_uniform_offset_feasibility(
        mode_decision=feasibility_module.load_json_artifact(args.mode_decision),
        mode_decision_path=args.mode_decision,
        trajectory_step_counterfactual=feasibility_module.load_json_artifact(
            args.trajectory_step_counterfactual
        ),
        trajectory_step_counterfactual_path=args.trajectory_step_counterfactual,
    )
    feasibility_module.write_trajectory_step_fixed_uniform_offset_feasibility_files(
        feasibility=feasibility,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
