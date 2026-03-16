import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.domain.sensor_parser import normalize_sensor_genetic_payloads


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a deterministic sensor/genetic parser smoke report"
    )
    parser.add_argument(
        "--cases-json",
        default="data/samples/sensor_genetic_parser_cases_v1.json",
        help="Sample parser case JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/sensor_genetic_parser_smoke_v1.json",
        help="Parser smoke JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/sensor_genetic_parser_smoke_v1.md",
        help="Parser smoke markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cases = json.loads(Path(args.cases_json).read_text(encoding="utf-8"))
    normalized_cases = []
    for case in cases:
        snapshot = normalize_sensor_genetic_payloads(
            wearable_payload=case.get("wearable_payload"),
            cgm_payload=case.get("cgm_payload"),
            genetic_payload=case.get("genetic_payload"),
        )
        normalized_cases.append(
            {
                "case_id": case["case_id"],
                "normalized_snapshot": snapshot.model_dump(),
            }
        )

    report = {
        "case_count": len(normalized_cases),
        "cases_json_path": args.cases_json,
        "wearable_case_count": sum(
            1
            for case in normalized_cases
            if case["normalized_snapshot"]["wearable_available"]
        ),
        "cgm_case_count": sum(
            1 for case in normalized_cases if case["normalized_snapshot"]["cgm_available"]
        ),
        "genetic_case_count": sum(
            1
            for case in normalized_cases
            if case["normalized_snapshot"]["genetic_available"]
        ),
        "normalized_cases": normalized_cases,
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
        "# sensor genetic parser smoke v1",
        "",
        f"- cases_json_path: `{report['cases_json_path']}`",
        f"- case_count: `{report['case_count']}`",
        f"- wearable_case_count: `{report['wearable_case_count']}`",
        f"- cgm_case_count: `{report['cgm_case_count']}`",
        f"- genetic_case_count: `{report['genetic_case_count']}`",
        "",
        "## Cases",
    ]
    for case in report["normalized_cases"]:
        lines.append(
            f"- `{case['case_id']}`: `{case['normalized_snapshot']}`"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
