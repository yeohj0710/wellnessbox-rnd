from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.governance.original_plan_audit import (
    OriginalPlanAuditStatus,
    audit_original_plan_manifest_v1,
)
from wellnessbox_rnd.governance.original_plan_report import (
    build_original_plan_completion_report_v1,
    render_original_plan_completion_report_markdown_v1,
    serialize_original_plan_completion_report_json_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    DEFAULT_ORIGINAL_PLAN_MANIFEST_PATH,
    RepositoryName,
    load_original_plan_manifest_v1,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUTPUT_PATH = Path("docs/original_plan/completion_status_v1.json")
DEFAULT_MARKDOWN_OUTPUT_PATH = Path("docs/original_plan/COMPLETION_STATUS.md")


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build the Korean original-plan completion report from audited evidence."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_ORIGINAL_PLAN_MANIFEST_PATH))
    parser.add_argument("--rnd-root", default=str(REPOSITORY_ROOT))
    parser.add_argument("--wellnessbox-root", default=None)
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT_PATH))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN_OUTPUT_PATH))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed report artifacts do not match current audited evidence.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rnd_root = Path(args.rnd_root).resolve()
    manifest_path = _resolve_path(args.manifest, root=rnd_root)
    json_output_path = _resolve_path(args.json_output, root=rnd_root)
    markdown_output_path = _resolve_path(args.markdown_output, root=rnd_root)

    repository_roots: dict[RepositoryName, Path] = {
        RepositoryName.WELLNESSBOX_RND: rnd_root,
    }
    service_root = _resolve_service_root(args.wellnessbox_root, rnd_root=rnd_root)
    if service_root is not None:
        repository_roots[RepositoryName.WELLNESSBOX] = service_root

    manifest = load_original_plan_manifest_v1(manifest_path)
    audit_report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=repository_roots,
    )
    completion_report = build_original_plan_completion_report_v1(manifest, audit_report)
    expected_json = serialize_original_plan_completion_report_json_v1(completion_report)
    expected_markdown = render_original_plan_completion_report_markdown_v1(completion_report)

    stale_outputs: list[str] = []
    if args.check:
        stale_outputs = _find_stale_outputs(
            {
                json_output_path: expected_json,
                markdown_output_path: expected_markdown,
            }
        )
    else:
        _write_text(json_output_path, expected_json)
        _write_text(markdown_output_path, expected_markdown)

    summary = {
        "audit_status": audit_report.status.value,
        "requirement_count": completion_report.requirement_count,
        "disposition_counts": {
            disposition.value: count
            for disposition, count in completion_report.disposition_counts.items()
        },
        "json_output": str(json_output_path),
        "markdown_output": str(markdown_output_path),
        "check_mode": args.check,
        "stale_outputs": stale_outputs,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if audit_report.status == OriginalPlanAuditStatus.PASS and not stale_outputs else 1


def _resolve_path(value: str, *, root: Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _resolve_service_root(value: str | None, *, rnd_root: Path) -> Path | None:
    if value:
        return Path(value).resolve()
    sibling = rnd_root.parent / "wellnessbox"
    return sibling.resolve() if sibling.is_dir() else None


def _find_stale_outputs(expected_outputs: dict[Path, str]) -> list[str]:
    return [
        str(path)
        for path, expected in expected_outputs.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != expected
    ]


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
