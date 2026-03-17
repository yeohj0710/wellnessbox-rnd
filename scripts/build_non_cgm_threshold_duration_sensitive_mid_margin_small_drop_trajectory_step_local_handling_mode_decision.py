from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_local_handling_mode_decision"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only local-handling mode decision for direct trajectory_step "
            "handling inside the threshold_duration_sensitive mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--readiness",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_readiness_v1.json"
        ),
        help="Current trajectory_step local-handling readiness JSON path.",
    )
    parser.add_argument(
        "--trajectory-step-fix-scope-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1.json"
        ),
        help="Current trajectory_step fix-scope decision JSON path.",
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
        "--slice-diagnostic",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "diagnostic_v1.json"
        ),
        help="Current 5-case small-drop slice diagnostic JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = decision_module.build_trajectory_step_local_handling_mode_decision(
        readiness=decision_module.load_json_artifact(args.readiness),
        readiness_path=args.readiness,
        fix_scope_decision=decision_module.load_json_artifact(
            args.trajectory_step_fix_scope_decision
        ),
        fix_scope_decision_path=args.trajectory_step_fix_scope_decision,
        trajectory_step_counterfactual=decision_module.load_json_artifact(
            args.trajectory_step_counterfactual
        ),
        trajectory_step_counterfactual_path=args.trajectory_step_counterfactual,
        slice_diagnostic=decision_module.load_json_artifact(args.slice_diagnostic),
        slice_diagnostic_path=args.slice_diagnostic,
    )
    decision_module.write_trajectory_step_local_handling_mode_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
