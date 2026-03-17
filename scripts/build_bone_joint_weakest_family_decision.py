from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.bone_joint_weakest_family_decision import (
    build_bone_joint_weakest_family_decision,
    load_json_artifact,
    write_bone_joint_weakest_family_decision_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a decision artifact for whether bone_joint should remain an "
            "explicit empty weakest-family anchor."
        )
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
        help="Weakest-slice summary JSON path",
    )
    parser.add_argument(
        "--eval-report",
        default="artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json",
        help="Frozen eval report JSON path",
    )
    parser.add_argument(
        "--training-revisit-decision",
        default="artifacts/reports/effect_training_revisit_decision_v1.json",
        help="Effect training revisit decision JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/bone_joint_weakest_family_decision_v1.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/bone_joint_weakest_family_decision_v1.md",
        help="Output markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = build_bone_joint_weakest_family_decision(
        weakest_slice_summary=load_json_artifact(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
        eval_report=load_json_artifact(args.eval_report),
        eval_report_path=args.eval_report,
        training_revisit_decision=load_json_artifact(args.training_revisit_decision),
        training_revisit_decision_path=args.training_revisit_decision,
    )
    write_bone_joint_weakest_family_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
