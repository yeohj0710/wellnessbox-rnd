import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.domain.sensor_parser import (
    validate_cgm_summary_csv_schema,
    validate_gene_profile_json_schema,
    validate_wearable_summary_csv_schema,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build sensor/genetic file schema validation report")
    parser.add_argument(
        "--wearable-csv",
        default="data/samples/wearable_summary_v1.csv",
        help="Wearable summary CSV fixture path",
    )
    parser.add_argument(
        "--cgm-csv",
        default="data/samples/cgm_summary_v1.csv",
        help="CGM summary CSV fixture path",
    )
    parser.add_argument(
        "--gene-json",
        default="data/samples/gene_profile_v1.json",
        help="Gene profile JSON fixture path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/sensor_genetic_file_schema_validation_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/sensor_genetic_file_schema_validation_v1.md",
        help="Output markdown report path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    wearable_result = validate_wearable_summary_csv_schema(
        Path(args.wearable_csv).read_text(encoding="utf-8")
    )
    cgm_result = validate_cgm_summary_csv_schema(Path(args.cgm_csv).read_text(encoding="utf-8"))
    gene_result = validate_gene_profile_json_schema(
        json.loads(Path(args.gene_json).read_text(encoding="utf-8"))
    )

    failure_probes = {
        "wearable_missing_step_column": validate_wearable_summary_csv_schema(
            "sleep_hours,restingHR\n6.5,58\n"
        ).model_dump(mode="json"),
        "cgm_missing_unit_for_avg_glucose": validate_cgm_summary_csv_schema(
            "avg_glucose,timeInRangePct\n6.8,78\n"
        ).model_dump(mode="json"),
        "gene_profile_invalid_type": validate_gene_profile_json_schema(
            {"markers": {"apoe": "e4"}}
        ).model_dump(mode="json"),
    }

    report = {
        "contract_id": "sensor_genetic_file_schema_validation_v1",
        "fixture_paths": {
            "wearable_summary_csv": args.wearable_csv,
            "cgm_summary_csv": args.cgm_csv,
            "gene_profile_json": args.gene_json,
        },
        "valid_fixture_results": {
            "wearable_summary_csv": wearable_result.model_dump(mode="json"),
            "cgm_summary_csv": cgm_result.model_dump(mode="json"),
            "gene_profile_json": gene_result.model_dump(mode="json"),
        },
        "failure_type_examples": failure_probes,
        "connected_flows": {
            "sensor_genetic_parser": [
                "wearable_summary.csv",
                "cgm_summary.csv",
                "gene_profile.json",
            ],
            "recommendation_input_enrichment": [
                "sleep_hours",
                "mean_glucose_mg_dl",
                "genetic_tags",
            ],
            "frozen_eval_sensor_slice": [
                "sensor_genetic_integration_rate_pct",
            ],
        },
    }

    report_json_path = Path(args.report_json)
    report_md_path = Path(args.report_md)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# sensor genetic file schema validation v1",
        "",
        "## valid fixtures",
        "",
    ]
    for name, result in report["valid_fixture_results"].items():
        lines.append(
            f"- `{name}`: passed=`{result['passed']}`, "
            f"failure_types=`{result['failure_types']}`"
        )
    lines.extend(["", "## failure type examples", ""])
    for name, result in report["failure_type_examples"].items():
        lines.append(f"- `{name}`: `{result['failure_types']}`")
    lines.extend(["", "## connected flows", ""])
    for name, fields in report["connected_flows"].items():
        lines.append(f"- `{name}`: {', '.join(fields)}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
