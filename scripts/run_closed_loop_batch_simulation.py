import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.simulation import (
    compare_batch_simulation_modes,
    write_batch_simulation_outputs,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Run batch closed-loop simulation on multiple synthetic users"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v1.jsonl",
        help="Synthetic longitudinal dataset path",
    )
    parser.add_argument("--max-cycles", type=int, default=3)
    parser.add_argument("--max-users", type=int, default=48)
    parser.add_argument(
        "--model-artifact",
        default="artifacts/models/efficacy_model_v0.json",
        help="Optional learned efficacy model artifact path",
    )
    parser.add_argument(
        "--policy-model-artifact",
        default="artifacts/models/policy_model_v0.json",
        help="Optional learned policy model artifact path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.json",
        help="Batch simulation report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.md",
        help="Batch simulation report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = compare_batch_simulation_modes(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
    )
    write_batch_simulation_outputs(
        report=report,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    deterministic_mode, learned_mode = report.compared_modes
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "scenario_set_id": report.scenario_set_id,
                "scenario_count": deterministic_mode.scenario_count,
                "deterministic_total_trace_steps": deterministic_mode.total_trace_steps,
                "learned_total_trace_steps": learned_mode.total_trace_steps,
                "differing_final_state_user_ids": report.differing_final_state_user_ids,
                "differing_final_policy_user_ids": report.differing_final_policy_user_ids,
                "differing_policy_path_user_ids": report.differing_policy_path_user_ids,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
