from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.evals.training_readiness_gate import (
    build_training_readiness_gate,
    load_json,
    write_training_readiness_gate_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a strict GO/NO-GO training-readiness gate after replay attribution, "
            "synthetic-validity audit, and weakest-slice lineage evidence."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    parser.add_argument(
        "--case-count",
        type=int,
        default=480,
    )
    parser.add_argument(
        "--replay-attribution",
        default="artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json",
    )
    parser.add_argument(
        "--synthetic-validity-audit",
        default="artifacts/reports/synthetic_validity_audit_v1.json",
    )
    parser.add_argument(
        "--requested-weakest-slice-lineage-proof",
        default="artifacts/reports/weakest_slice_lineage_proof_v1.json",
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
    )
    parser.add_argument(
        "--parser-case-id-mismatch-decision",
        default="artifacts/reports/parser_case_id_mismatch_decision_v1.json",
    )
    parser.add_argument(
        "--structured-safety-rule-overlap-decision",
        default="artifacts/reports/structured_safety_rule_overlap_decision_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/training_readiness_gate_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/training_readiness_gate_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_training_readiness_gate(
        dataset_path=args.dataset,
        case_count=args.case_count,
        replay_attribution=load_json(args.replay_attribution),
        replay_attribution_path=args.replay_attribution,
        synthetic_validity_audit=load_json(args.synthetic_validity_audit),
        synthetic_validity_audit_path=args.synthetic_validity_audit,
        weakest_slice_summary=load_json(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
        parser_case_id_mismatch_decision=load_json(args.parser_case_id_mismatch_decision),
        parser_case_id_mismatch_decision_path=args.parser_case_id_mismatch_decision,
        structured_safety_rule_overlap_decision=load_json(
            args.structured_safety_rule_overlap_decision
        ),
        structured_safety_rule_overlap_decision_path=args.structured_safety_rule_overlap_decision,
        requested_weakest_slice_lineage_proof_path=args.requested_weakest_slice_lineage_proof,
    )
    write_training_readiness_gate_files(
        report=report,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "decision": report["gate_decision"]["decision"],
                "authorized_now": report["gate_decision"]["authorized_now"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
