from __future__ import annotations

import argparse

from wellnessbox_rnd.evals.structured_safety_rule_overlap_freshness_audit import (
    build_structured_safety_rule_overlap_freshness_audit,
    load_json_artifact,
    write_structured_safety_rule_overlap_freshness_audit_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the structured-safety rule overlap freshness audit artifact."
    )
    parser.add_argument(
        "--overlap-decision",
        default="artifacts/reports/structured_safety_rule_overlap_decision_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/structured_safety_rule_overlap_freshness_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/structured_safety_rule_overlap_freshness_audit_v1.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overlap_decision = load_json_artifact(args.overlap_decision)
    audit = build_structured_safety_rule_overlap_freshness_audit(
        overlap_decision=overlap_decision,
        overlap_decision_path=args.overlap_decision,
    )
    write_structured_safety_rule_overlap_freshness_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )


if __name__ == "__main__":
    main()
