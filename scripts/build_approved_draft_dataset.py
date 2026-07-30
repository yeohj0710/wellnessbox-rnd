"""Emit the approved-only training dataset manifest for H-003.

Reads the AI draft ledger read-only. Pending, rejected, and owner-reviewed
drafts are excluded with a recorded reason. Nothing is written to the ledger.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.training.approved_draft_dataset import (
    build_approved_draft_dataset_manifest_v1,
    load_draft_rows,
    verify_manifest_is_approved_only,
)

DEFAULT_DATABASE = "etc/local_research_runtime/interim.sqlite3"
DEFAULT_OUTPUT = "data/original_plan/final_session/approved_draft_dataset_manifest_v1.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=DEFAULT_DATABASE, help="AI draft ledger path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Manifest output path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows, digest = load_draft_rows(args.database)
    manifest = build_approved_draft_dataset_manifest_v1(
        rows, database_path=args.database, database_sha256=digest
    )
    check = verify_manifest_is_approved_only(manifest)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"manifest_path": str(output), **check}, ensure_ascii=False, indent=2))
    return 0 if check["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
