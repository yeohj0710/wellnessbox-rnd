import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.simulation import (
    simulate_closed_loop_scenario,
    write_simulation_outputs,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Run closed-loop simulation harness on a synthetic user scenario"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v1.jsonl",
        help="Synthetic longitudinal dataset path",
    )
    parser.add_argument(
        "--user-id",
        default="syn-user-001",
        help="Synthetic user id to simulate from step-0 request",
    )
    parser.add_argument("--max-cycles", type=int, default=3)
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
        default="artifacts/reports/closed_loop_simulation_v0_syn_user_001.json",
        help="Simulation report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/closed_loop_simulation_v0_syn_user_001.md",
        help="Simulation report Markdown path",
    )
    parser.add_argument(
        "--enable-learned-reranking",
        action="store_true",
        help="Apply gated learned efficacy reranking inside the deterministic optimizer",
    )
    parser.add_argument(
        "--enable-learned-policy",
        action="store_true",
        help="Apply guarded learned policy selection inside simulation only",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = simulate_closed_loop_scenario(
        dataset_path=args.dataset,
        user_id=args.user_id,
        max_cycles=args.max_cycles,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_learned_policy=args.enable_learned_policy,
        enable_learned_reranking=args.enable_learned_reranking,
    )
    write_simulation_outputs(
        report=report,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "scenario_id": report.scenario_id,
                "user_id": report.user_id,
                "final_state": report.final_state,
                "final_policy_action": report.final_policy_action.value,
                "model_loaded": report.model_loaded,
                "policy_model_loaded": report.policy_model_loaded,
                "learned_policy_enabled": report.learned_policy_enabled,
                "learned_reranking_enabled": report.learned_reranking_enabled,
                "trace_length": len(report.trace),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
