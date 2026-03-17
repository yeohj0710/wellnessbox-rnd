from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_half_offset_fix_scope_decision"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only half-offset fix-scope decision for trajectory_step "
            "inside the threshold_duration_sensitive mid_margin small_drop target."
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
        "--probe-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
        ),
        help="Current fixed-uniform-offset first-probe decision JSON path.",
    )
    parser.add_argument(
        "--half-offset-counterfactual",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
        help="Current half-offset counterfactual JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_fix_scope_decision_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_fix_scope_decision_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = decision_module.build_trajectory_step_half_offset_fix_scope_decision(
        mode_decision=decision_module.load_json_artifact(args.mode_decision),
        mode_decision_path=args.mode_decision,
        probe_decision=decision_module.load_json_artifact(args.probe_decision),
        probe_decision_path=args.probe_decision,
        half_offset_counterfactual=decision_module.load_json_artifact(
            args.half_offset_counterfactual
        ),
        half_offset_counterfactual_path=args.half_offset_counterfactual,
    )
    decision_module.write_trajectory_step_half_offset_fix_scope_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
