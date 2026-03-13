import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.simulation import compare_batch_simulation_modes


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Compare combined replay with policy effect override enabled vs disabled"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=96)
    parser.add_argument(
        "--model-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Replay-only effect artifact path",
    )
    parser.add_argument(
        "--policy-model-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Replay-only policy artifact path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/combined_override_comparison_v1.json",
        help="Comparison report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/combined_override_comparison_v1.md",
        help="Comparison report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    override_on_report = compare_batch_simulation_modes(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_policy_effect_proxy_override=True,
    )
    override_off_report = compare_batch_simulation_modes(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_policy_effect_proxy_override=False,
    )
    override_on = _extract_combined_mode(override_on_report)
    override_off = _extract_combined_mode(override_off_report)

    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "override_on": _summarize_mode(override_on),
        "override_off": _summarize_mode(override_off),
        "deltas": _build_deltas(override_on=override_on, override_off=override_off),
    }

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
                "deltas": report["deltas"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _summarize_mode(mode) -> dict[str, object]:
    return {
        "mode_name": mode.mode_name,
        "final_policy_action_counts": mode.final_policy_action_counts,
        "policy_effect_override_applied_count": mode.policy_effect_override_applied_count,
        "raw_policy_disagreement_count": mode.raw_policy_disagreement_count,
        "low_risk_final_action_distribution": mode.cohort_slice_metrics[
            "low_risk_users"
        ].final_action_distribution,
        "cgm_final_action_distribution": mode.cohort_slice_metrics[
            "cgm_users"
        ].final_action_distribution,
        "low_risk_disagreement_count": mode.cohort_slice_metrics[
            "low_risk_users"
        ].deterministic_vs_learned_disagreement_count,
        "cgm_disagreement_count": mode.cohort_slice_metrics[
            "cgm_users"
        ].deterministic_vs_learned_disagreement_count,
    }


def _extract_combined_mode(report):
    return next(
        mode
        for mode in report.compared_modes
        if mode.mode_name == "learned_effect_and_policy_guarded"
    )


def _build_deltas(*, override_on, override_off) -> dict[str, int]:
    on_summary = _summarize_mode(override_on)
    off_summary = _summarize_mode(override_off)
    return {
        "policy_effect_override_applied_count_delta": (
            off_summary["policy_effect_override_applied_count"]
            - on_summary["policy_effect_override_applied_count"]
        ),
        "low_risk_monitor_only_delta": _action_delta(
            on_summary["low_risk_final_action_distribution"],
            off_summary["low_risk_final_action_distribution"],
            "monitor_only",
        ),
        "low_risk_re_optimize_delta": _action_delta(
            on_summary["low_risk_final_action_distribution"],
            off_summary["low_risk_final_action_distribution"],
            "re_optimize",
        ),
        "cgm_monitor_only_delta": _action_delta(
            on_summary["cgm_final_action_distribution"],
            off_summary["cgm_final_action_distribution"],
            "monitor_only",
        ),
        "cgm_re_optimize_delta": _action_delta(
            on_summary["cgm_final_action_distribution"],
            off_summary["cgm_final_action_distribution"],
            "re_optimize",
        ),
        "low_risk_disagreement_delta": (
            off_summary["low_risk_disagreement_count"]
            - on_summary["low_risk_disagreement_count"]
        ),
        "cgm_disagreement_delta": (
            off_summary["cgm_disagreement_count"]
            - on_summary["cgm_disagreement_count"]
        ),
    }


def _action_delta(
    on_counts: dict[str, int],
    off_counts: dict[str, int],
    action: str,
) -> int:
    return off_counts.get(action, 0) - on_counts.get(action, 0)


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# combined override comparison v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        f"- policy_model_artifact_path: `{report['policy_model_artifact_path']}`",
        "",
        "## Deltas",
    ]
    for key, value in report["deltas"].items():
        lines.append(f"- `{key}`: `{value}`")
    for key in ("override_on", "override_off"):
        summary = report[key]
        lines.extend(
            [
                "",
                f"## {key.replace('_', ' ').title()}",
                f"- final_policy_action_counts: `{summary['final_policy_action_counts']}`",
                (
                    "- low_risk_final_action_distribution: "
                    f"`{summary['low_risk_final_action_distribution']}`"
                ),
                (
                    "- cgm_final_action_distribution: "
                    f"`{summary['cgm_final_action_distribution']}`"
                ),
                (
                    "- policy_effect_override_applied_count: "
                    f"`{summary['policy_effect_override_applied_count']}`"
                ),
                f"- low_risk_disagreement_count: `{summary['low_risk_disagreement_count']}`",
                f"- cgm_disagreement_count: `{summary['cgm_disagreement_count']}`",
            ]
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
