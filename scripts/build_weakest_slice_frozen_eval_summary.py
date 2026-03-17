from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.weakest_slice_audit import (
    build_weakest_slice_frozen_eval_summary,
    load_json_artifact,
    write_weakest_slice_frozen_eval_summary_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a human-readable weakest-slice frozen-eval summary artifact"
    )
    parser.add_argument(
        "--audit-json",
        default="artifacts/reports/weakest_slice_frozen_eval_audit_v1.json",
        help="Weakest-slice audit JSON path",
    )
    parser.add_argument(
        "--eval-report",
        default="artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json",
        help="Frozen eval report JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
        help="Output summary JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.md",
        help="Output summary markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_weakest_slice_frozen_eval_summary(
        audit=load_json_artifact(args.audit_json),
        audit_path=args.audit_json,
        eval_report=load_json_artifact(args.eval_report),
        eval_report_path=args.eval_report,
    )
    write_weakest_slice_frozen_eval_summary_files(
        summary,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
