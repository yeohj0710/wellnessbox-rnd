import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import (
    DEFAULT_RICH_SYNTHETIC_SEED,
    DEFAULT_RICH_USER_COUNT,
    build_rich_policy_training_rows,
    generate_rich_synthetic_cohort,
    summarize_rich_policy_training_rows,
    summarize_rich_synthetic_cohort,
    validate_rich_policy_training_rows,
    validate_rich_synthetic_cohort,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Generate deterministic rich synthetic longitudinal and policy datasets"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_RICH_SYNTHETIC_SEED)
    parser.add_argument("--user-count", type=int, default=DEFAULT_RICH_USER_COUNT)
    parser.add_argument(
        "--cohort-output",
        default="data/synthetic/synthetic_longitudinal_v2.jsonl",
        help="JSONL output path for rich longitudinal cohort",
    )
    parser.add_argument(
        "--policy-output",
        default="data/synthetic/policy_training_v1.jsonl",
        help="JSONL output path for policy dataset",
    )
    parser.add_argument(
        "--cohort-report-json",
        default="artifacts/reports/synthetic_longitudinal_v2_summary.json",
        help="Summary report JSON path for cohort",
    )
    parser.add_argument(
        "--cohort-report-md",
        default="artifacts/reports/synthetic_longitudinal_v2_summary.md",
        help="Summary report markdown path for cohort",
    )
    parser.add_argument(
        "--policy-report-json",
        default="artifacts/reports/policy_training_v1_summary.json",
        help="Summary report JSON path for policy dataset",
    )
    parser.add_argument(
        "--policy-report-md",
        default="artifacts/reports/policy_training_v1_summary.md",
        help="Summary report markdown path for policy dataset",
    )
    parser.add_argument(
        "--sample-trace-output",
        default="artifacts/reports/synthetic_longitudinal_v2_trace_sample.json",
        help="JSON output path for a short sample trajectory trace",
    )
    return parser


def _render_cohort_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# synthetic longitudinal v2 summary",
        "",
        f"- cohort_version: `{summary['cohort_version']}`",
        f"- seed: `{summary['seed']}`",
        f"- user_count: `{summary['user_count']}`",
        f"- record_count: `{summary['record_count']}`",
        f"- adverse_event_count: `{summary['adverse_event_count']}`",
        f"- average_effect_proxy: `{summary['average_effect_proxy']}`",
        f"- average_adherence_proxy: `{summary['average_adherence_proxy']}`",
        f"- average_side_effect_proxy: `{summary['average_side_effect_proxy']}`",
        f"- average_delta_aggregate_z: `{summary['average_delta_aggregate_z']}`",
        "",
        "## Next Action Counts",
    ]
    for key, value in summary["next_action_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Risk Tier Counts"])
    for key, value in summary["risk_tier_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Modality Counts"])
    for key, value in summary["modality_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Trajectory Mode Counts"])
    for key, value in summary["trajectory_mode_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def _render_policy_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# policy training v1 summary",
        "",
        f"- dataset_version: `{summary['dataset_version']}`",
        f"- record_count: `{summary['record_count']}`",
        f"- user_count: `{summary['user_count']}`",
        f"- average_feature_count: `{summary['average_feature_count']}`",
        "",
        "## Next Action Counts",
    ]
    for key, value in summary["next_action_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Risk Tier Counts"])
    for key, value in summary["risk_tier_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Closed-loop State Counts"])
    for key, value in summary["state_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def _build_sample_trace(records: list[object]) -> list[dict[str, object]]:
    selected_user_ids: list[str] = []
    trace: list[dict[str, object]] = []
    for record in records:
        if record.user_id not in selected_user_ids:
            selected_user_ids.append(record.user_id)
        if len(selected_user_ids) > 2:
            break
    allowed = set(selected_user_ids[:2])
    for record in records:
        if record.user_id not in allowed:
            continue
        trace.append(
            {
                "record_id": record.record_id,
                "user_id": record.user_id,
                "trajectory_mode": record.trajectory_mode,
                "trajectory_step": record.trajectory_step,
                "day_index": record.day_index,
                "next_action": record.labels.next_action.value,
                "risk_tier": record.labels.risk_tier,
                "safety_status": record.labels.safety_status.value,
                "expected_effect_proxy": record.expected_effect_proxy,
                "adherence_proxy": record.adherence_proxy,
                "side_effect_proxy": record.side_effect_proxy,
                "regimen_keys": [item.ingredient_key for item in record.regimen],
            }
        )
    return trace


def _write_jsonl(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(row.model_dump_json() for row in rows) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    records = generate_rich_synthetic_cohort(seed=args.seed, user_count=args.user_count)
    cohort_issues = validate_rich_synthetic_cohort(records)
    rows = build_rich_policy_training_rows(records)
    policy_issues = validate_rich_policy_training_rows(rows)
    issues = cohort_issues + policy_issues
    if issues:
        print(json.dumps({"issues": issues}, ensure_ascii=False, indent=2))
        return 1

    cohort_summary = summarize_rich_synthetic_cohort(records, seed=args.seed)
    policy_summary = summarize_rich_policy_training_rows(rows)

    cohort_output = Path(args.cohort_output)
    policy_output = Path(args.policy_output)
    cohort_report_json = Path(args.cohort_report_json)
    cohort_report_md = Path(args.cohort_report_md)
    policy_report_json = Path(args.policy_report_json)
    policy_report_md = Path(args.policy_report_md)
    sample_trace_output = Path(args.sample_trace_output)

    _write_jsonl(cohort_output, records)
    _write_jsonl(policy_output, rows)
    cohort_report_json.parent.mkdir(parents=True, exist_ok=True)
    policy_report_json.parent.mkdir(parents=True, exist_ok=True)
    sample_trace_output.parent.mkdir(parents=True, exist_ok=True)

    cohort_report_json.write_text(
        cohort_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    cohort_report_md.write_text(
        _render_cohort_markdown(cohort_summary.model_dump(mode="json")),
        encoding="utf-8",
    )
    policy_report_json.write_text(
        policy_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    policy_report_md.write_text(
        _render_policy_markdown(policy_summary.model_dump(mode="json")),
        encoding="utf-8",
    )
    sample_trace_output.write_text(
        json.dumps(_build_sample_trace(records), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "cohort_output": str(cohort_output),
                "policy_output": str(policy_output),
                "cohort_report_json": str(cohort_report_json),
                "policy_report_json": str(policy_report_json),
                "sample_trace_output": str(sample_trace_output),
                "record_count": len(records),
                "policy_row_count": len(rows),
                "user_count": cohort_summary.user_count,
                "issues": [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
