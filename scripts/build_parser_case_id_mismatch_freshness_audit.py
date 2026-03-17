from __future__ import annotations

import argparse

from wellnessbox_rnd.evals.parser_case_id_mismatch_freshness_audit import (
    build_parser_case_id_mismatch_freshness_audit,
    load_json_artifact,
    write_parser_case_id_mismatch_freshness_audit_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the parser case-id mismatch freshness audit artifact."
    )
    parser.add_argument(
        "--mismatch-decision",
        default="artifacts/reports/parser_case_id_mismatch_decision_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/parser_case_id_mismatch_freshness_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/parser_case_id_mismatch_freshness_audit_v1.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mismatch_decision = load_json_artifact(args.mismatch_decision)
    audit = build_parser_case_id_mismatch_freshness_audit(
        mismatch_decision=mismatch_decision,
        mismatch_decision_path=args.mismatch_decision,
    )
    write_parser_case_id_mismatch_freshness_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )


if __name__ == "__main__":
    main()
