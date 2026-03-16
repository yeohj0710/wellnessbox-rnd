from __future__ import annotations

import json
from pathlib import Path


def load_eval_report(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_eval_reports(
    baseline_report: dict[str, object],
    candidate_report: dict[str, object],
    *,
    baseline_report_path: str | Path,
    candidate_report_path: str | Path,
) -> dict[str, object]:
    baseline_summary = baseline_report.get("summary", {})
    candidate_summary = candidate_report.get("summary", {})
    metric_names = sorted(set(baseline_summary) | set(candidate_summary))

    metric_deltas: dict[str, dict[str, object]] = {}
    nonzero_metric_delta_count = 0
    changed_pass_count = 0
    for metric_name in metric_names:
        baseline_item = baseline_summary.get(metric_name, {})
        candidate_item = candidate_summary.get(metric_name, {})
        baseline_score = baseline_item.get("score")
        candidate_score = candidate_item.get("score")
        delta = _score_delta(baseline_score, candidate_score)
        pass_changed = baseline_item.get("passed") != candidate_item.get("passed")
        if delta not in (None, 0.0):
            nonzero_metric_delta_count += 1
        if pass_changed:
            changed_pass_count += 1
        metric_deltas[metric_name] = {
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "delta": delta,
            "baseline_passed": baseline_item.get("passed"),
            "candidate_passed": candidate_item.get("passed"),
            "pass_changed": pass_changed,
            "target": candidate_item.get("target", baseline_item.get("target")),
            "comparison": candidate_item.get("comparison", baseline_item.get("comparison")),
            "unit": candidate_item.get("unit", baseline_item.get("unit")),
        }

    weakest_slice_delta = _compare_weakest_slices(
        baseline_report.get("weakest_slice_summary"),
        candidate_report.get("weakest_slice_summary"),
    )

    return {
        "baseline_report_path": str(baseline_report_path),
        "candidate_report_path": str(candidate_report_path),
        "baseline_case_count": baseline_report.get("case_count"),
        "candidate_case_count": candidate_report.get("case_count"),
        "case_count_delta": _score_delta(
            baseline_report.get("case_count"),
            candidate_report.get("case_count"),
        ),
        "metric_deltas": metric_deltas,
        "weakest_slice_delta": weakest_slice_delta,
        "changed_metric_summary": {
            "metric_count": len(metric_deltas),
            "nonzero_metric_delta_count": nonzero_metric_delta_count,
            "pass_changed_count": changed_pass_count,
        },
    }


def write_eval_report_comparison_files(
    comparison: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_eval_report_comparison_markdown(comparison), encoding="utf-8")


def render_eval_report_comparison_markdown(comparison: dict[str, object]) -> str:
    weakest_slice_delta = comparison["weakest_slice_delta"]
    lines = [
        "# eval report comparison",
        "",
        f"- baseline_report_path: {comparison['baseline_report_path']}",
        f"- candidate_report_path: {comparison['candidate_report_path']}",
        f"- baseline_case_count: {comparison['baseline_case_count']}",
        f"- candidate_case_count: {comparison['candidate_case_count']}",
        f"- case_count_delta: {comparison['case_count_delta']}",
        f"- metric_count: {comparison['changed_metric_summary']['metric_count']}",
        "- nonzero_metric_delta_count: "
        f"{comparison['changed_metric_summary']['nonzero_metric_delta_count']}",
        f"- pass_changed_count: {comparison['changed_metric_summary']['pass_changed_count']}",
        "",
        "## metric deltas",
        "",
        "| metric | baseline | candidate | delta | baseline_passed | candidate_passed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for metric_name, item in comparison["metric_deltas"].items():
        lines.append(
            "| "
            f"{metric_name} | {item['baseline_score']} | {item['candidate_score']} | "
            f"{item['delta']} | {item['baseline_passed']} | {item['candidate_passed']} |"
        )

    lines.extend(["", "## weakest slice delta", ""])
    lines.append(f"- both_available: {weakest_slice_delta['both_available']}")
    lines.append(
        f"- baseline_overall_category: {weakest_slice_delta['baseline_overall_category']}"
    )
    lines.append(
        f"- candidate_overall_category: {weakest_slice_delta['candidate_overall_category']}"
    )
    lines.append(
        f"- overall_category_changed: {weakest_slice_delta['overall_category_changed']}"
    )
    if weakest_slice_delta["metric_category_changes"]:
        lines.extend(
            [
                "",
                "| metric | baseline_category | candidate_category | changed |",
                "| --- | --- | --- | --- |",
            ]
        )
        for metric_name, item in weakest_slice_delta["metric_category_changes"].items():
            lines.append(
                "| "
                f"{metric_name} | {item['baseline_category']} | "
                f"{item['candidate_category']} | {item['changed']} |"
            )
    return "\n".join(lines) + "\n"


def _compare_weakest_slices(
    baseline_weakest_slice: object,
    candidate_weakest_slice: object,
) -> dict[str, object]:
    if not isinstance(baseline_weakest_slice, dict) or not isinstance(
        candidate_weakest_slice, dict
    ):
        return {
            "both_available": False,
            "baseline_overall_category": _overall_category(baseline_weakest_slice),
            "candidate_overall_category": _overall_category(candidate_weakest_slice),
            "overall_category_changed": None,
            "metric_category_changes": {},
        }

    baseline_overall = _overall_category(baseline_weakest_slice)
    candidate_overall = _overall_category(candidate_weakest_slice)
    metric_names = sorted(
        set(baseline_weakest_slice.get("weakest_category_by_metric", {}))
        | set(candidate_weakest_slice.get("weakest_category_by_metric", {}))
    )
    metric_category_changes = {}
    for metric_name in metric_names:
        baseline_item = baseline_weakest_slice.get("weakest_category_by_metric", {}).get(
            metric_name, {}
        )
        candidate_item = candidate_weakest_slice.get("weakest_category_by_metric", {}).get(
            metric_name, {}
        )
        baseline_category = baseline_item.get("category")
        candidate_category = candidate_item.get("category")
        metric_category_changes[metric_name] = {
            "baseline_category": baseline_category,
            "candidate_category": candidate_category,
            "changed": baseline_category != candidate_category,
        }

    return {
        "both_available": True,
        "baseline_overall_category": baseline_overall,
        "candidate_overall_category": candidate_overall,
        "overall_category_changed": baseline_overall != candidate_overall,
        "metric_category_changes": metric_category_changes,
    }


def _overall_category(weakest_slice: object) -> str | None:
    if not isinstance(weakest_slice, dict):
        return None
    overall = weakest_slice.get("weakest_category_overall")
    if not isinstance(overall, dict):
        return None
    return overall.get("category")


def _score_delta(baseline_score: object, candidate_score: object) -> float | None:
    if not isinstance(baseline_score, (int, float)) or not isinstance(
        candidate_score, (int, float)
    ):
        return None
    return round(float(candidate_score) - float(baseline_score), 12)


__all__ = [
    "compare_eval_reports",
    "load_eval_report",
    "render_eval_report_comparison_markdown",
    "write_eval_report_comparison_files",
]
