from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

contract_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_half_offset_local_contract"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only local contract artifact for trajectory_step "
            "half-offset handling inside the threshold_duration_sensitive "
            "mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--fix-scope-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_fix_scope_decision_v1.json"
        ),
        help="Current half-offset fix-scope decision JSON path.",
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
            "trajectory_step_half_offset_local_contract_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_local_contract_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = contract_module.build_trajectory_step_half_offset_local_contract(
        fix_scope_decision=contract_module.load_json_artifact(args.fix_scope_decision),
        fix_scope_decision_path=args.fix_scope_decision,
        half_offset_counterfactual=contract_module.load_json_artifact(
            args.half_offset_counterfactual
        ),
        half_offset_counterfactual_path=args.half_offset_counterfactual,
    )
    contract_module.write_trajectory_step_half_offset_local_contract_files(
        contract=contract,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
