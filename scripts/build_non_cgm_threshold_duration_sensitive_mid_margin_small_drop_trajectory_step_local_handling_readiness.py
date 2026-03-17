from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

readiness_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_local_handling_readiness"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only readiness artifact for direct trajectory_step local "
            "handling inside the threshold_duration_sensitive mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--competition-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_score_competition_decision_v1.json"
        ),
        help="Current score-competition decision JSON path.",
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
        "--trajectory-step-fix-scope-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1.json"
        ),
        help="Current trajectory_step fix-scope decision JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_readiness_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_readiness_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    readiness = readiness_module.build_trajectory_step_local_handling_readiness(
        competition_decision=readiness_module.load_json_artifact(
            args.competition_decision
        ),
        competition_decision_path=args.competition_decision,
        trajectory_step_counterfactual=readiness_module.load_json_artifact(
            args.trajectory_step_counterfactual
        ),
        trajectory_step_counterfactual_path=args.trajectory_step_counterfactual,
        trajectory_step_fix_scope_decision=readiness_module.load_json_artifact(
            args.trajectory_step_fix_scope_decision
        ),
        trajectory_step_fix_scope_decision_path=args.trajectory_step_fix_scope_decision,
    )
    readiness_module.write_trajectory_step_local_handling_readiness_files(
        readiness=readiness,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
