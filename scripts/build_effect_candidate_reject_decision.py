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
            "Build a minimal reject/fork evidence artifact when an effect candidate "
            "is clearly worse overall than the current baseline"
        )
    )
    parser.add_argument(
        "--compare-report",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json"
        ),
        help="Replay compare JSON path",
    )
    parser.add_argument(
        "--final-compare-report",
        default=(
            "artifacts/reports/"
            "final_kpi_compare_report_v1.json"
        ),
        help="Readable final compare JSON path",
    )
    parser.add_argument(
        "--non-cgm-diagnostic-report",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        help="Dominant non-CGM regression diagnostic JSON path",
    )
    parser.add_argument(
        "--cgm-diagnostic-report",
        default=(
            "artifacts/reports/"
            "latest_candidate_cgm_slice_diagnostic_v1.json"
        ),
        help="CGM candidate diagnostic JSON path",
    )
    parser.add_argument(
        "--core-kpi-path-summary",
        default=(
            "artifacts/reports/"
            "core_kpi_path_summary_v1.json"
        ),
        help="Core KPI path summary JSON path",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "latest_effect_candidate_reject_decision_v1.json"
        ),
        help="Output decision JSON path",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "latest_effect_candidate_reject_decision_v1.md"
        ),
        help="Output decision markdown path",
    )
    return parser


def main() -> int:
    from wellnessbox_rnd.evals.effect_candidate_reject_decision import (
        build_effect_candidate_reject_decision,
        load_json_artifact,
        write_effect_candidate_reject_decision_files,
    )

    args = build_parser().parse_args()
    decision = build_effect_candidate_reject_decision(
        compare_report=load_json_artifact(args.compare_report),
        compare_report_path=args.compare_report,
        final_compare_report=load_json_artifact(args.final_compare_report),
        final_compare_report_path=args.final_compare_report,
        non_cgm_diagnostic_report=load_json_artifact(args.non_cgm_diagnostic_report),
        non_cgm_diagnostic_report_path=args.non_cgm_diagnostic_report,
        cgm_diagnostic_report=load_json_artifact(args.cgm_diagnostic_report),
        cgm_diagnostic_report_path=args.cgm_diagnostic_report,
        core_kpi_path_summary=load_json_artifact(args.core_kpi_path_summary),
        core_kpi_path_summary_path=args.core_kpi_path_summary,
    )
    write_effect_candidate_reject_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "decision": decision["decision_gate"]["decision"],
                "validation_issues": decision["validation_issues"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
