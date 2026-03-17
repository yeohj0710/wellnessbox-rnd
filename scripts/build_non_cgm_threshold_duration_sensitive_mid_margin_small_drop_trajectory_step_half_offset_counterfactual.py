from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

counterfactual_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_half_offset_counterfactual"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only half-offset counterfactual for trajectory_step "
            "inside the threshold_duration_sensitive mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--probe-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
        ),
        help="Current fixed-uniform-offset probe decision JSON path.",
    )
    parser.add_argument(
        "--trajectory-step-counterfactual",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        help="Current full trajectory_step counterfactual JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    counterfactual = counterfactual_module.build_trajectory_step_half_offset_counterfactual(
        probe_decision=counterfactual_module.load_json_artifact(args.probe_decision),
        probe_decision_path=args.probe_decision,
        trajectory_step_counterfactual=counterfactual_module.load_json_artifact(
            args.trajectory_step_counterfactual
        ),
        trajectory_step_counterfactual_path=args.trajectory_step_counterfactual,
    )
    counterfactual_module.write_trajectory_step_half_offset_counterfactual_files(
        counterfactual=counterfactual,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
