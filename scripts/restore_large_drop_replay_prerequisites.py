from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.evals.large_drop_replay_prerequisite_audit import (
    restore_large_drop_replay_prerequisites,
)


def main() -> int:
    parser = ArgumentParser(
        description="Restore held large-drop replay inputs only when every manifest hash matches."
    )
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/large_drop_replay_restore_v1.json",
    )
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = restore_large_drop_replay_prerequisites(
        archive_root=args.archive_root,
        repository_root=args.repository_root,
        manifest=manifest,
    )
    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "restored_verified_prerequisites" else 2


if __name__ == "__main__":
    raise SystemExit(main())
