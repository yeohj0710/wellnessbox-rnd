from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.chat_optional_rerun_freshness_audit import (
    build_chat_optional_rerun_freshness_audit,
    load_json_artifact,
    write_chat_optional_rerun_freshness_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a freshness audit for whether any newer source artifact exists "
            "since the current optional chat rerun audit."
        )
    )
    parser.add_argument(
        "--rerun-audit",
        default="artifacts/reports/chat_optional_rerun_need_audit_v1.json",
        help="Optional chat rerun audit JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/chat_optional_rerun_freshness_audit_v1.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/chat_optional_rerun_freshness_audit_v1.md",
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_chat_optional_rerun_freshness_audit(
        rerun_audit=load_json_artifact(args.rerun_audit),
        rerun_audit_path=args.rerun_audit,
    )
    write_chat_optional_rerun_freshness_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
