import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for import_root in (REPO_ROOT, SRC_ROOT):
    import_root_str = str(import_root)
    if import_root_str not in sys.path:
        sys.path.insert(0, import_root_str)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build an audit proving learned artifacts remain "
            "outside runtime core dependency paths"
        )
    )
    parser.add_argument(
        "--sample-request",
        default="data/samples/api_recommend_start_plan_request_v1.json",
        help="Sample request used for runtime smoke evidence",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/learned_runtime_boundary_audit_v1.json",
        help="Output audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/learned_runtime_boundary_audit_v1.md",
        help="Output audit markdown path",
    )
    return parser


def main() -> int:
    from wellnessbox_rnd.evals.learned_runtime_boundary_audit import (
        build_learned_runtime_boundary_audit,
        write_learned_runtime_boundary_audit_files,
    )

    args = build_parser().parse_args()
    audit = build_learned_runtime_boundary_audit(
        sample_request_path=args.sample_request,
    )
    write_learned_runtime_boundary_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "learned_artifact_core_dependency_promoted": audit["overall_assessment"][
                    "learned_artifact_core_dependency_promoted"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
