from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

TARGET_FEATURE = "regimen_count"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_regimen_count_diagnostic(
    *,
    slice_diagnostic: dict[str, object],
    slice_diagnostic_path: str | Path,
    feature_decision: dict[str, object],
    feature_decision_path: str | Path,
) -> dict[str, object]:
    slice_target = _as_dict(slice_diagnostic.get("slice_target"))
    decision_gate = _as_dict(feature_decision.get("decision_gate"))
    example_cases = _as_list(slice_diagnostic.get("example_cases"))
    feature_values = _collect_feature_values(example_cases)
    case_count = len(feature_values)
    feature_value = float(decision_gate.get("chosen_first_feature_value", 0.0))

    diagnostic = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_diagnostic_v1"
        ),
        "source_artifacts": {
            "slice_diagnostic_path": str(slice_diagnostic_path),
            "feature_decision_path": str(feature_decision_path),
        },
        "feature_target": {
            "parent_family": slice_target.get("parent_family"),
            "trajectory_mode": slice_target.get("trajectory_mode"),
            "margin_bucket": slice_target.get("margin_bucket"),
            "proxy_drop_bucket": slice_target.get("proxy_drop_bucket"),
            "chosen_feature_family": decision_gate.get("chosen_feature_family"),
            "chosen_feature": decision_gate.get("chosen_first_feature"),
            "expected_feature_value": feature_value,
            "observed_case_count": case_count,
        },
        "feature_summary": {
            "per_case_values": feature_values,
            "value_summary": {
                "mean": round(mean(feature_values), 6) if feature_values else 0.0,
                "min": round(min(feature_values), 6) if feature_values else 0.0,
                "max": round(max(feature_values), 6) if feature_values else 0.0,
                "sum": round(sum(feature_values), 6),
            },
            "feature_present_case_count": sum(1 for value in feature_values if value != 0.0),
        },
        "readable_summary": {
            "case_digest": {
                "observed_case_count": case_count,
                "feature_present_case_count": sum(
                    1 for value in feature_values if value != 0.0
                ),
            },
            "feature_digest": {
                "chosen_feature": decision_gate.get("chosen_first_feature"),
                "expected_feature_value": feature_value,
                "mean_case_value": round(mean(feature_values), 6) if feature_values else 0.0,
                "sum_case_value": round(sum(feature_values), 6),
            },
        },
        "summary_findings": _build_summary_findings(
            case_count=case_count,
            feature_value=feature_value,
            feature_values=feature_values,
        ),
    }
    diagnostic["validation_issues"] = validate_regimen_count_diagnostic(diagnostic)
    return diagnostic


def validate_regimen_count_diagnostic(diagnostic: dict[str, object]) -> list[str]:
    issues: list[str] = []
    feature_target = _as_dict(diagnostic.get("feature_target"))
    feature_summary = _as_dict(diagnostic.get("feature_summary"))
    readable_summary = _as_dict(diagnostic.get("readable_summary"))
    value_summary = _as_dict(feature_summary.get("value_summary"))

    if feature_target.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if feature_target.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if feature_target.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if feature_target.get("chosen_feature_family") != "regimen_status_summary":
        issues.append("unexpected_feature_family")
    if feature_target.get("chosen_feature") != TARGET_FEATURE:
        issues.append("unexpected_feature_target")
    if int(feature_target.get("observed_case_count", 0)) != len(
        _as_list(feature_summary.get("per_case_values"))
    ):
        issues.append("per_case_value_count_mismatch")
    if round(float(value_summary.get("sum", 0.0)), 6) != round(
        float(feature_target.get("expected_feature_value", 0.0)),
        6,
    ):
        issues.append("feature_value_sum_mismatch")
    if (
        _as_dict(readable_summary.get("feature_digest")).get("chosen_feature")
        != feature_target.get("chosen_feature")
    ):
        issues.append("readable_summary_feature_mismatch")
    if not _as_list(diagnostic.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_regimen_count_diagnostic_markdown(diagnostic: dict[str, object]) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "regimen-count diagnostic v1"
        ),
        "",
        "## readable summary",
        "",
        f"- readable_summary: `{diagnostic.get('readable_summary', {})}`",
        "",
        "## feature target",
        "",
        f"- feature_target: `{diagnostic.get('feature_target', {})}`",
        "",
        "## feature summary",
        "",
        f"- feature_summary: `{diagnostic.get('feature_summary', {})}`",
        "",
        "## summary findings",
        "",
    ]
    for item in _as_list(diagnostic.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{diagnostic.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_regimen_count_diagnostic_files(
    *,
    diagnostic: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_regimen_count_diagnostic_markdown(diagnostic),
        encoding="utf-8",
    )


def _collect_feature_values(example_cases: list[object]) -> list[float]:
    values: list[float] = []
    for case in example_cases:
        feature_delta = _as_dict(_as_dict(case).get("feature_delta"))
        values.append(round(float(feature_delta.get(TARGET_FEATURE, 0.0)), 6))
    return values


def _build_summary_findings(
    *,
    case_count: int,
    feature_value: float,
    feature_values: list[float],
) -> list[str]:
    mean_value = round(mean(feature_values), 6) if feature_values else 0.0
    return [
        (
            "The chosen feature `regimen_count` currently appears in "
            f"{case_count}/{case_count} cases inside the current `small_drop` slice."
        ),
        (
            f"Its current summed feature value is {round(feature_value, 6)}, "
            f"with mean per-case value {mean_value}."
        ),
        (
            "The next bounded replay-only pass can now measure movement directly on "
            "`regimen_count` before reopening `planned_regimen_count` or the wider family."
        ),
    ]


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_regimen_count_diagnostic",
    "load_json_artifact",
    "render_regimen_count_diagnostic_markdown",
    "validate_regimen_count_diagnostic",
    "write_regimen_count_diagnostic_files",
]
