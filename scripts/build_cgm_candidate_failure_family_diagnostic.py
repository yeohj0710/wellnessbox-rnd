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
            "Build a bounded diagnostic proving whether the training_view_enforced "
            "candidate is cgm-only bad or dominated by another failure family"
        )
    )
    parser.add_argument(
        "--compare-report",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_replay_compare_v1.json"
        ),
        help="Replay compare JSON path",
    )
    parser.add_argument(
        "--attribution-report",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_replay_attribution_v1.json"
        ),
        help="Replay attribution JSON path",
    )
    parser.add_argument(
        "--cgm-feature-audit-report",
        default="artifacts/reports/cgm_combined_replay_feature_audit_v1.json",
        help="CGM combined replay feature audit JSON path",
    )
    parser.add_argument(
        "--cgm-slice-bridge-report",
        default="artifacts/reports/cgm_slice_bridge_summary_v1.json",
        help="CGM slice bridge summary JSON path",
    )
    parser.add_argument(
        "--cgm-event-report",
        default="artifacts/reports/cgm_normalized_event_bridge_v1.json",
        help="CGM normalized event bridge JSON path",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_cgm_failure_family_diagnostic_v1.json"
        ),
        help="Output diagnostic JSON path",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_cgm_failure_family_diagnostic_v1.md"
        ),
        help="Output diagnostic markdown path",
    )
    return parser


def main() -> int:
    from wellnessbox_rnd.evals.cgm_candidate_failure_family_diagnostic import (
        build_cgm_candidate_failure_family_diagnostic,
        load_json_artifact,
        write_cgm_candidate_failure_family_diagnostic_files,
    )

    args = build_parser().parse_args()
    diagnostic = build_cgm_candidate_failure_family_diagnostic(
        compare_report=load_json_artifact(args.compare_report),
        compare_report_path=args.compare_report,
        attribution_report=load_json_artifact(args.attribution_report),
        attribution_report_path=args.attribution_report,
        cgm_feature_audit_report=load_json_artifact(args.cgm_feature_audit_report),
        cgm_feature_audit_report_path=args.cgm_feature_audit_report,
        cgm_slice_bridge_report=load_json_artifact(args.cgm_slice_bridge_report),
        cgm_slice_bridge_report_path=args.cgm_slice_bridge_report,
        cgm_event_report=load_json_artifact(args.cgm_event_report),
        cgm_event_report_path=args.cgm_event_report,
    )
    write_cgm_candidate_failure_family_diagnostic_files(
        diagnostic=diagnostic,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "cgm_only_failure_hypothesis_supported": diagnostic["hypothesis_gate"][
                    "cgm_only_failure_hypothesis_supported"
                ],
                "validation_issues": diagnostic["validation_issues"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
