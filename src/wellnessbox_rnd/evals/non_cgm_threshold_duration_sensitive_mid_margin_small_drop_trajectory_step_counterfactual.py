from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

TARGET_FEATURE = "trajectory_step"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_counterfactual(
    *,
    slice_diagnostic: dict[str, object],
    slice_diagnostic_path: str | Path,
    competition_decision: dict[str, object],
    competition_decision_path: str | Path,
) -> dict[str, object]:
    example_cases = _as_list(slice_diagnostic.get("example_cases"))
    case_rows = [_build_case_row(case) for case in example_cases]
    shortfalls = [float(row["candidate_monitor_shortfall"]) for row in case_rows]
    feature_values = [float(row["trajectory_step_value"]) for row in case_rows]
    feature_abs_values = [float(row["trajectory_step_abs_value"]) for row in case_rows]
    neutralized_shortfalls = [
        round(shortfall - feature_abs_value, 6)
        for shortfall, feature_abs_value in zip(shortfalls, feature_abs_values, strict=True)
    ]
    extra_penalty_shortfalls = [
        round(shortfall + feature_abs_value, 6)
        for shortfall, feature_abs_value in zip(shortfalls, feature_abs_values, strict=True)
    ]

    counterfactual = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1"
        ),
        "source_artifacts": {
            "slice_diagnostic_path": str(slice_diagnostic_path),
            "competition_decision_path": str(competition_decision_path),
        },
        "target": {
            "chosen_feature": _as_dict(competition_decision.get("decision_gate")).get(
                "chosen_first_opposing_feature"
            ),
            "observed_case_count": len(case_rows),
            "expected_feature_value": _as_dict(
                competition_decision.get("decision_gate")
            ).get("chosen_first_opposing_feature_value"),
        },
        "counterfactual_summary": {
            "current_shortfall_mean": round(mean(shortfalls), 6),
            "trajectory_step_signed_value_mean": round(mean(feature_values), 6),
            "trajectory_step_abs_value_mean": round(mean(feature_abs_values), 6),
            "neutralized_shortfall_mean": round(mean(neutralized_shortfalls), 6),
            "extra_penalty_shortfall_mean": round(mean(extra_penalty_shortfalls), 6),
            "feature_abs_exceeds_shortfall_case_count": sum(
                1
                for shortfall, feature_abs_value in zip(
                    shortfalls, feature_abs_values, strict=True
                )
                if feature_abs_value > shortfall
            ),
            "neutralize_clears_shortfall_case_count": sum(
                1
                for adjusted_shortfall in neutralized_shortfalls
                if adjusted_shortfall <= 0.0
            ),
            "extra_penalty_worsens_case_count": sum(
                1
                for original_shortfall, adjusted_shortfall in zip(
                    shortfalls, extra_penalty_shortfalls, strict=True
                )
                if adjusted_shortfall > original_shortfall
            ),
        },
        "readable_summary": {
            "case_digest": {
                "observed_case_count": len(case_rows),
                "feature_present_case_count": sum(
                    1 for value in feature_abs_values if value > 0.0
                ),
            },
            "counterfactual_digest": {
                "current_shortfall_mean": round(mean(shortfalls), 6),
                "trajectory_step_signed_value_mean": round(mean(feature_values), 6),
                "trajectory_step_abs_value_mean": round(mean(feature_abs_values), 6),
                "neutralize_clears_shortfall_case_count": sum(
                    1
                    for adjusted_shortfall in neutralized_shortfalls
                    if adjusted_shortfall <= 0.0
                ),
                "extra_penalty_worsens_case_count": sum(
                    1
                    for original_shortfall, adjusted_shortfall in zip(
                        shortfalls, extra_penalty_shortfalls, strict=True
                    )
                    if adjusted_shortfall > original_shortfall
                ),
            },
        },
        "case_rows": case_rows,
        "summary_findings": _build_summary_findings(
            case_count=len(case_rows),
            shortfall_mean=round(mean(shortfalls), 6),
            feature_mean=round(mean(feature_abs_values), 6),
            neutralize_clears_shortfall_case_count=sum(
                1
                for adjusted_shortfall in neutralized_shortfalls
                if adjusted_shortfall <= 0.0
            ),
            extra_penalty_worsens_case_count=sum(
                1
                for original_shortfall, adjusted_shortfall in zip(
                    shortfalls, extra_penalty_shortfalls, strict=True
                )
                if adjusted_shortfall > original_shortfall
            ),
        ),
    }
    counterfactual["validation_issues"] = validate_trajectory_step_counterfactual(
        counterfactual
    )
    return counterfactual


def validate_trajectory_step_counterfactual(
    counterfactual: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    target = _as_dict(counterfactual.get("target"))
    summary = _as_dict(counterfactual.get("counterfactual_summary"))
    case_rows = _as_list(counterfactual.get("case_rows"))

    if target.get("chosen_feature") != TARGET_FEATURE:
        issues.append("unexpected_feature_target")
    if int(target.get("observed_case_count", 0)) != len(case_rows):
        issues.append("case_row_count_mismatch")
    if int(summary.get("neutralize_clears_shortfall_case_count", 0)) != len(case_rows):
        issues.append("counterfactual_neutralize_does_not_clear_all_cases")
    if int(summary.get("extra_penalty_worsens_case_count", 0)) != len(case_rows):
        issues.append("counterfactual_extra_penalty_does_not_worsen_all_cases")
    if not _as_list(counterfactual.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_counterfactual_markdown(
    counterfactual: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step counterfactual v1"
        ),
        "",
        "## readable summary",
        "",
        f"- readable_summary: `{counterfactual.get('readable_summary', {})}`",
        "",
        "## target",
        "",
        f"- target: `{counterfactual.get('target', {})}`",
        "",
        "## counterfactual summary",
        "",
        f"- counterfactual_summary: `{counterfactual.get('counterfactual_summary', {})}`",
        "",
        "## summary findings",
        "",
    ]
    for item in _as_list(counterfactual.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{counterfactual.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trajectory_step_counterfactual_files(
    *,
    counterfactual: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(counterfactual, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_trajectory_step_counterfactual_markdown(counterfactual),
        encoding="utf-8",
    )


def _build_case_row(case: object) -> dict[str, object]:
    case_dict = _as_dict(case)
    feature_delta = _as_dict(case_dict.get("feature_delta"))
    feature_value = round(float(feature_delta.get(TARGET_FEATURE, 0.0)), 6)
    return {
        "user_id": case_dict.get("user_id"),
        "record_id": case_dict.get("record_id"),
        "candidate_monitor_shortfall": case_dict.get("candidate_monitor_shortfall"),
        "trajectory_step_value": feature_value,
        "trajectory_step_abs_value": round(abs(feature_value), 6),
    }


def _build_summary_findings(
    *,
    case_count: int,
    shortfall_mean: float,
    feature_mean: float,
    neutralize_clears_shortfall_case_count: int,
    extra_penalty_worsens_case_count: int,
) -> list[str]:
    return [
        (
            f"`trajectory_step` currently contributes mean opposing magnitude {feature_mean} "
            f"against mean monitor shortfall {shortfall_mean} across {case_count} cases."
        ),
        (
            "A replay-only neutralize counterfactual clears "
            f"{neutralize_clears_shortfall_case_count}/{case_count} cases."
        ),
        (
            "A replay-only extra-penalty counterfactual worsens "
            f"{extra_penalty_worsens_case_count}/{case_count} cases."
        ),
    ]


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_counterfactual",
    "load_json_artifact",
    "render_trajectory_step_counterfactual_markdown",
    "validate_trajectory_step_counterfactual",
    "write_trajectory_step_counterfactual_files",
]
