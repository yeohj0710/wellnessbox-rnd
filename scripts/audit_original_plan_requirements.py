from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.governance.original_plan_audit import (
    OriginalPlanAuditStatus,
    audit_original_plan_manifest_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    DEFAULT_ORIGINAL_PLAN_MANIFEST_PATH,
    RepositoryName,
    load_original_plan_manifest_v1,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Audit original-plan completion claims against tracked repository evidence."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_ORIGINAL_PLAN_MANIFEST_PATH),
        help="Manifest JSON path. Relative paths resolve from the wellnessbox-rnd root.",
    )
    parser.add_argument(
        "--rnd-root",
        default=str(REPOSITORY_ROOT),
        help="wellnessbox-rnd repository root",
    )
    parser.add_argument(
        "--wellnessbox-root",
        default=None,
        help="Optional wellnessbox service repository root",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rnd_root = Path(args.rnd_root).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = rnd_root / manifest_path

    repository_roots: dict[RepositoryName, Path] = {
        RepositoryName.WELLNESSBOX_RND: rnd_root,
    }
    service_root = _resolve_service_root(args.wellnessbox_root, rnd_root=rnd_root)
    if service_root is not None:
        repository_roots[RepositoryName.WELLNESSBOX] = service_root

    report = audit_original_plan_manifest_v1(
        load_original_plan_manifest_v1(manifest_path),
        repository_roots=repository_roots,
    )
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if report.status == OriginalPlanAuditStatus.PASS else 1


def _resolve_service_root(value: str | None, *, rnd_root: Path) -> Path | None:
    if value:
        return Path(value).resolve()
    configured = os.environ.get("WELLNESSBOX_EVIDENCE_ROOT")
    if configured:
        return Path(configured).resolve()
    sibling = rnd_root.parent / "wellnessbox"
    return sibling.resolve() if sibling.is_dir() else None


if __name__ == "__main__":
    raise SystemExit(main())
