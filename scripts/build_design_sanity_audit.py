from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.evals.design_sanity_audit import (
    build_design_sanity_audit,
    load_json,
    write_design_sanity_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build a short evidence-based design sanity audit")
    parser.add_argument(
        "--learned-boundary-audit",
        default="artifacts/reports/learned_runtime_boundary_audit_v1.json",
    )
    parser.add_argument(
        "--next-action-audit",
        default="artifacts/reports/next_action_state_machine_audit_v1.json",
    )
    parser.add_argument(
        "--pro-contract",
        default="artifacts/reports/pro_scoring_contract_v1.json",
    )
    parser.add_argument(
        "--baseline-identical-signal-audit",
        default="artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json",
    )
    parser.add_argument(
        "--partition-validity-audit",
        default="artifacts/reports/dataset_f_partition_validity_audit_v1.json",
    )
    parser.add_argument(
        "--calibration-dependence-audit",
        default="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
    )
    parser.add_argument(
        "--core-kpi-path-summary",
        default="artifacts/reports/core_kpi_path_summary_v1.json",
    )
    parser.add_argument(
        "--latest-effect-candidate-reject-decision",
        default="artifacts/reports/latest_effect_candidate_reject_decision_v1.json",
    )
    parser.add_argument(
        "--latest-training-compare-vs-baseline",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
    )
    parser.add_argument(
        "--latest-training-compare-vs-prior-candidate",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_"
            "replay_compare_vs_prior_candidate_v1.json"
        ),
    )
    parser.add_argument(
        "--recommendation-service",
        default="src/wellnessbox_rnd/orchestration/recommendation_service.py",
    )
    parser.add_argument(
        "--optimizer-service",
        default="src/wellnessbox_rnd/optimizer/service.py",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/design_sanity_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/design_sanity_audit_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_design_sanity_audit(
        learned_boundary_audit=load_json(args.learned_boundary_audit),
        learned_boundary_audit_path=args.learned_boundary_audit,
        next_action_audit=load_json(args.next_action_audit),
        next_action_audit_path=args.next_action_audit,
        pro_contract=load_json(args.pro_contract),
        pro_contract_path=args.pro_contract,
        baseline_identical_signal_audit=load_json(args.baseline_identical_signal_audit),
        baseline_identical_signal_audit_path=args.baseline_identical_signal_audit,
        partition_validity_audit=load_json(args.partition_validity_audit),
        partition_validity_audit_path=args.partition_validity_audit,
        calibration_dependence_audit=load_json(args.calibration_dependence_audit),
        calibration_dependence_audit_path=args.calibration_dependence_audit,
        weakest_slice_summary=load_json(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
        core_kpi_path_summary=load_json(args.core_kpi_path_summary),
        core_kpi_path_summary_path=args.core_kpi_path_summary,
        latest_effect_candidate_reject_decision=load_json(
            args.latest_effect_candidate_reject_decision
        ),
        latest_effect_candidate_reject_decision_path=args.latest_effect_candidate_reject_decision,
        latest_training_compare_vs_baseline=load_json(args.latest_training_compare_vs_baseline),
        latest_training_compare_vs_baseline_path=args.latest_training_compare_vs_baseline,
        latest_training_compare_vs_prior_candidate=load_json(
            args.latest_training_compare_vs_prior_candidate
        ),
        latest_training_compare_vs_prior_candidate_path=args.latest_training_compare_vs_prior_candidate,
        recommendation_service_path=args.recommendation_service,
        optimizer_service_path=args.optimizer_service,
    )
    write_design_sanity_audit_files(
        audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "direction_status": audit["overall_verdict"]["direction_status"],
                "fundamentally_wrong_research_direction": audit["overall_verdict"][
                    "fundamentally_wrong_research_direction"
                ],
                "principal_blocker": audit["overall_verdict"]["principal_blocker"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
