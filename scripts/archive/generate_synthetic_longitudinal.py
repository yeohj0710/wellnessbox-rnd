import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.synthetic.longitudinal import (
    DEFAULT_SYNTHETIC_SEED,
    DEFAULT_USER_COUNT,
    generate_synthetic_longitudinal_cohort,
    summarize_synthetic_cohort,
    validate_synthetic_cohort,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate deterministic synthetic longitudinal cohort data")
    parser.add_argument("--seed", type=int, default=DEFAULT_SYNTHETIC_SEED)
    parser.add_argument("--user-count", type=int, default=DEFAULT_USER_COUNT)
    parser.add_argument(
        "--output",
        default="data/synthetic/synthetic_longitudinal_v1.jsonl",
        help="JSONL output path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/synthetic_longitudinal_v1_summary.json",
        help="Summary report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/synthetic_longitudinal_v1_summary.md",
        help="Summary report markdown path",
    )
    return parser


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# synthetic longitudinal cohort summary",
        "",
        f"- cohort_version: `{summary['cohort_version']}`",
        f"- seed: `{summary['seed']}`",
        f"- user_count: `{summary['user_count']}`",
        f"- record_count: `{summary['record_count']}`",
        f"- adverse_event_count: `{summary['adverse_event_count']}`",
        f"- average_effect_proxy: `{summary['average_effect_proxy']}`",
        f"- average_adherence_proxy: `{summary['average_adherence_proxy']}`",
        "",
        "## Step Counts",
    ]
    for key, value in summary["step_counts"].items():
        lines.append(f"- step_{key}: `{value}`")
    lines.extend(["", "## Next Action Counts"])
    for key, value in summary["next_action_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Risk Tier Counts"])
    for key, value in summary["risk_tier_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Closed-loop State Counts"])
    for key, value in summary["state_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    records = generate_synthetic_longitudinal_cohort(
        seed=args.seed,
        user_count=args.user_count,
    )
    issues = validate_synthetic_cohort(records)
    if issues:
        print(json.dumps({"issues": issues}, ensure_ascii=False, indent=2))
        return 1

    summary = summarize_synthetic_cohort(records, seed=args.seed)

    output_path = Path(args.output)
    report_json_path = Path(args.report_json)
    report_md_path = Path(args.report_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        "\n".join(record.model_dump_json() for record in records) + "\n",
        encoding="utf-8",
    )
    report_json_path.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_markdown(summary.model_dump(mode="json")),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "output": str(output_path),
                "report_json": str(report_json_path),
                "report_md": str(report_md_path),
                "record_count": len(records),
                "user_count": summary.user_count,
                "issues": [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
