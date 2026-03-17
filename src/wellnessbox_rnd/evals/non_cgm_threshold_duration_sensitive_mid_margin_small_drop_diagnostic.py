from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from wellnessbox_rnd.evals.non_cgm_threshold_cross_diagnostic import (
    collect_non_cgm_threshold_cross_cases,
    load_json_artifact,
)

TARGET_TRAJECTORY_MODE = "threshold_duration_sensitive"
TARGET_MARGIN_BUCKET = "mid_margin"
TARGET_PROXY_DROP_BUCKET = "small_drop"


def build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic(
    *,
    dataset_path: str | Path,
    max_cycles: int,
    max_users: int,
    policy_artifact_path: str | Path,
    reference_effect_artifact_path: str | Path,
    candidate_effect_artifact_path: str | Path,
    narrowing_decision: dict[str, object],
    narrowing_decision_path: str | Path,
) -> dict[str, object]:
    parent_cases = collect_non_cgm_threshold_cross_cases(
        dataset_path=dataset_path,
        max_cycles=max_cycles,
        max_users=max_users,
        policy_artifact_path=policy_artifact_path,
        reference_effect_artifact_path=reference_effect_artifact_path,
        candidate_effect_artifact_path=candidate_effect_artifact_path,
    )
    target_cases = [
        case
        for case in parent_cases
        if str(case.get("trajectory_mode")) == TARGET_TRAJECTORY_MODE
        and str(case.get("margin_bucket")) == TARGET_MARGIN_BUCKET
        and str(case.get("proxy_drop_bucket")) == TARGET_PROXY_DROP_BUCKET
    ]
    decision_gate = _as_dict(narrowing_decision.get("decision_gate"))
    expected_case_count = int(
        decision_gate.get("chosen_first_proxy_drop_bucket_case_count", 0)
    )
    workflow_summary = _build_workflow_summary(target_cases)
    case_summary = _build_case_summary(
        target_cases=target_cases,
        parent_case_count=len(parent_cases),
    )
    feature_summary = _build_feature_summary(target_cases)
    interpretation = _build_interpretation(
        case_summary=case_summary,
        feature_summary=feature_summary,
    )
    readable_summary = _build_readable_summary(
        target_cases=target_cases,
        parent_case_count=len(parent_cases),
        case_summary=case_summary,
        workflow_summary=workflow_summary,
        feature_summary=feature_summary,
        interpretation=interpretation,
    )
    diagnostic = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1"
        ),
        "source_artifacts": {
            "dataset_path": str(dataset_path),
            "policy_artifact_path": str(policy_artifact_path),
            "reference_effect_artifact_path": str(reference_effect_artifact_path),
            "candidate_effect_artifact_path": str(candidate_effect_artifact_path),
            "narrowing_decision_path": str(narrowing_decision_path),
        },
        "slice_target": {
            "parent_family": "non_cgm_continue_to_monitor_threshold_cross",
            "trajectory_mode": TARGET_TRAJECTORY_MODE,
            "margin_bucket": TARGET_MARGIN_BUCKET,
            "proxy_drop_bucket": TARGET_PROXY_DROP_BUCKET,
            "expected_case_count_from_narrowing_decision": expected_case_count,
            "observed_case_count": len(target_cases),
            "parent_family_case_count": len(parent_cases),
        },
        "workflow_summary": workflow_summary,
        "case_summary": case_summary,
        "feature_summary": feature_summary,
        "interpretation": interpretation,
        "readable_summary": readable_summary,
        "summary_findings": _build_summary_findings(readable_summary),
        "example_cases": target_cases[:5],
    }
    diagnostic["validation_issues"] = (
        validate_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic(
            diagnostic
        )
    )
    return diagnostic


def validate_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic(
    diagnostic: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    slice_target = _as_dict(diagnostic.get("slice_target"))
    case_summary = _as_dict(diagnostic.get("case_summary"))
    workflow_summary = _as_dict(diagnostic.get("workflow_summary"))
    feature_summary = _as_dict(diagnostic.get("feature_summary"))
    interpretation = _as_dict(diagnostic.get("interpretation"))
    readable_summary = _as_dict(diagnostic.get("readable_summary"))

    expected_case_count = int(
        slice_target.get("expected_case_count_from_narrowing_decision", 0)
    )
    observed_case_count = int(slice_target.get("observed_case_count", 0))
    if expected_case_count != observed_case_count:
        issues.append("narrowing_decision_case_count_mismatch")
    if slice_target.get("trajectory_mode") != TARGET_TRAJECTORY_MODE:
        issues.append("unexpected_trajectory_mode")
    if slice_target.get("margin_bucket") != TARGET_MARGIN_BUCKET:
        issues.append("unexpected_margin_bucket")
    if slice_target.get("proxy_drop_bucket") != TARGET_PROXY_DROP_BUCKET:
        issues.append("unexpected_proxy_drop_bucket")
    if case_summary.get("all_cases_match_target_mode") is not True:
        issues.append("trajectory_mode_drift_detected")
    if case_summary.get("all_cases_match_target_bucket") is not True:
        issues.append("margin_bucket_drift_detected")
    if case_summary.get("all_cases_match_target_proxy_drop_bucket") is not True:
        issues.append("proxy_drop_bucket_drift_detected")
    if case_summary.get("all_cases_non_cgm") is not True:
        issues.append("cgm_case_detected")
    if case_summary.get("all_transitions_match_target") is not True:
        issues.append("target_transition_drift_detected")
    if (
        int(
            sum(
                int(value)
                for value in _as_dict(workflow_summary.get("final_cycle_index_counts")).values()
            )
        )
        != observed_case_count
    ):
        issues.append("final_cycle_count_mismatch")
    if not _as_list(feature_summary.get("top_absolute_features")):
        issues.append("missing_feature_level_evidence")
    if interpretation.get("dominant_feature_family") != "intercept":
        issues.append("dominant_feature_family_not_intercept")
    if (
        _as_dict(readable_summary.get("feature_digest")).get("dominant_family")
        != interpretation.get("dominant_feature_family")
    ):
        issues.append("feature_digest_family_mismatch")
    if not _as_list(diagnostic.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_markdown(
    diagnostic: dict[str, object]
) -> str:
    lines = [
        "# non-cgm threshold-duration-sensitive mid-margin small-drop diagnostic v1",
        "",
        "## readable summary",
        "",
        f"- readable_summary: `{diagnostic.get('readable_summary', {})}`",
        "",
        "## slice target",
        "",
        f"- slice_target: `{diagnostic.get('slice_target', {})}`",
        "",
        "## workflow summary",
        "",
        f"- workflow_summary: `{diagnostic.get('workflow_summary', {})}`",
        "",
        "## case summary",
        "",
        f"- case_summary: `{diagnostic.get('case_summary', {})}`",
        "",
        "## feature summary",
        "",
        f"- feature_summary: `{diagnostic.get('feature_summary', {})}`",
        "",
        "## interpretation",
        "",
        f"- interpretation: `{diagnostic.get('interpretation', {})}`",
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


def write_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_files(
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
        render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_markdown(
            diagnostic
        ),
        encoding="utf-8",
    )


def _build_workflow_summary(target_cases: list[dict[str, object]]) -> dict[str, object]:
    final_cycle_counts = Counter(str(case["final_cycle_index"]) for case in target_cases)
    return {
        "final_cycle_index_counts": dict(sorted(final_cycle_counts.items())),
    }


def _build_case_summary(
    *,
    target_cases: list[dict[str, object]],
    parent_case_count: int,
) -> dict[str, object]:
    reference_margins = [float(case["reference_continue_margin"]) for case in target_cases]
    candidate_shortfalls = [float(case["candidate_monitor_shortfall"]) for case in target_cases]
    proxy_drops = [float(case["proxy_drop"]) for case in target_cases]
    share_pct = round((len(target_cases) / parent_case_count) * 100.0, 2)
    return {
        "all_cases_match_target_mode": all(
            str(case["trajectory_mode"]) == TARGET_TRAJECTORY_MODE for case in target_cases
        ),
        "all_cases_match_target_bucket": all(
            str(case["margin_bucket"]) == TARGET_MARGIN_BUCKET for case in target_cases
        ),
        "all_cases_match_target_proxy_drop_bucket": all(
            str(case["proxy_drop_bucket"]) == TARGET_PROXY_DROP_BUCKET for case in target_cases
        ),
        "all_cases_non_cgm": all(case["cgm_available"] is False for case in target_cases),
        "all_transitions_match_target": all(
            case["reference_final_action"] == "continue_plan"
            and case["candidate_final_action"] == "monitor_only"
            for case in target_cases
        ),
        "parent_family_share_pct": share_pct,
        "reference_continue_margin_summary": {
            "mean": round(mean(reference_margins), 6),
            "min": round(min(reference_margins), 6),
            "max": round(max(reference_margins), 6),
        },
        "candidate_monitor_shortfall_summary": {
            "mean": round(mean(candidate_shortfalls), 6),
            "min": round(min(candidate_shortfalls), 6),
            "max": round(max(candidate_shortfalls), 6),
        },
        "proxy_drop_summary": {
            "mean": round(mean(proxy_drops), 6),
            "min": round(min(proxy_drops), 6),
            "max": round(max(proxy_drops), 6),
        },
    }


def _build_feature_summary(target_cases: list[dict[str, object]]) -> dict[str, object]:
    family_signed_sums: dict[str, float] = defaultdict(float)
    family_abs_sums: dict[str, float] = defaultdict(float)
    feature_signed_sums: dict[str, float] = defaultdict(float)
    feature_abs_sums: dict[str, float] = defaultdict(float)
    for case in target_cases:
        for family, delta in _as_dict(case.get("feature_family_delta")).items():
            family_signed_sums[str(family)] += float(delta)
            family_abs_sums[str(family)] += abs(float(delta))
        for feature_name, delta in _as_dict(case.get("feature_delta")).items():
            feature_signed_sums[str(feature_name)] += float(delta)
            feature_abs_sums[str(feature_name)] += abs(float(delta))
    return {
        "top_absolute_families": _top_family_items(family_abs_sums, reverse=True),
        "top_negative_signed_families": _top_family_items(
            {key: value for key, value in family_signed_sums.items() if value < 0.0},
            reverse=False,
        ),
        "top_positive_signed_families": _top_family_items(
            {key: value for key, value in family_signed_sums.items() if value > 0.0},
            reverse=True,
        ),
        "top_absolute_features": _top_feature_items(feature_abs_sums, reverse=True),
        "top_negative_features": _top_feature_items(
            {key: value for key, value in feature_signed_sums.items() if value < 0.0},
            reverse=False,
        ),
        "top_positive_features": _top_feature_items(
            {key: value for key, value in feature_signed_sums.items() if value > 0.0},
            reverse=True,
        ),
    }


def _build_interpretation(
    *,
    case_summary: dict[str, object],
    feature_summary: dict[str, object],
) -> dict[str, object]:
    return {
        "dominant_feature_family": _first_family_name(
            _as_list(feature_summary.get("top_absolute_families"))
        ),
        "dominant_feature": _first_feature_name(
            _as_list(feature_summary.get("top_absolute_features"))
        ),
        "reference_continue_margin_mean": _as_dict(
            case_summary.get("reference_continue_margin_summary")
        ).get("mean"),
        "proxy_drop_mean": _as_dict(case_summary.get("proxy_drop_summary")).get("mean"),
        "summary": (
            "The smallest current replay-only slice remains the `small_drop` subset "
            "inside the `threshold_duration_sensitive` `mid_margin` bucket."
        ),
    }


def _build_readable_summary(
    *,
    target_cases: list[dict[str, object]],
    parent_case_count: int,
    case_summary: dict[str, object],
    workflow_summary: dict[str, object],
    feature_summary: dict[str, object],
    interpretation: dict[str, object],
) -> dict[str, object]:
    top_feature = _first_feature_item(_as_list(feature_summary.get("top_absolute_features")))
    return {
        "case_digest": {
            "observed_case_count": len(target_cases),
            "parent_family_case_count": parent_case_count,
            "parent_family_share_pct": case_summary.get("parent_family_share_pct"),
            "all_cases_non_cgm": case_summary.get("all_cases_non_cgm"),
        },
        "margin_digest": {
            "reference_continue_margin_mean": _as_dict(
                case_summary.get("reference_continue_margin_summary")
            ).get("mean"),
            "proxy_drop_mean": _as_dict(case_summary.get("proxy_drop_summary")).get("mean"),
            "proxy_drop_bucket": TARGET_PROXY_DROP_BUCKET,
            "final_cycle_index_counts": _as_dict(workflow_summary.get("final_cycle_index_counts")),
        },
        "feature_digest": {
            "dominant_family": interpretation.get("dominant_feature_family"),
            "dominant_feature": interpretation.get("dominant_feature"),
            "top_absolute_feature": top_feature,
        },
    }


def _build_summary_findings(readable_summary: dict[str, object]) -> list[str]:
    case_digest = _as_dict(readable_summary.get("case_digest"))
    margin_digest = _as_dict(readable_summary.get("margin_digest"))
    feature_digest = _as_dict(readable_summary.get("feature_digest"))
    return [
        (
            "The current replay-only next slice now has an explicit before-state: "
            f"`{TARGET_PROXY_DROP_BUCKET}` with {case_digest.get('observed_case_count')}/"
            f"{case_digest.get('parent_family_case_count')} parent-family cases."
        ),
        (
            "Its current mean reference continue margin and proxy drop are "
            f"{margin_digest.get('reference_continue_margin_mean')} and "
            f"{margin_digest.get('proxy_drop_mean')}."
        ),
        (
            "Its dominant feature family remains "
            f"`{feature_digest.get('dominant_family')}`, led by "
            f"`{feature_digest.get('dominant_feature')}`."
        ),
    ]


def _top_family_items(
    family_map: dict[str, float],
    *,
    reverse: bool,
    limit: int = 6,
) -> list[dict[str, object]]:
    ordered = sorted(
        (
            {"family": family, "value": round(value, 6)}
            for family, value in family_map.items()
        ),
        key=lambda item: float(item["value"]),
        reverse=reverse,
    )
    return ordered[:limit]


def _top_feature_items(
    feature_map: dict[str, float],
    *,
    reverse: bool,
    limit: int = 8,
) -> list[dict[str, object]]:
    ordered = sorted(
        (
            {
                "feature": feature_name,
                "family": (
                    "intercept"
                    if feature_name == "__intercept__"
                    else _feature_family_name(feature_name)
                ),
                "value": round(value, 6),
            }
            for feature_name, value in feature_map.items()
        ),
        key=lambda item: float(item["value"]),
        reverse=reverse,
    )
    return ordered[:limit]


def _first_family_name(items: list[object]) -> str | None:
    if not items:
        return None
    return str(_as_dict(items[0]).get("family"))


def _first_feature_name(items: list[object]) -> str | None:
    if not items:
        return None
    return str(_as_dict(items[0]).get("feature"))


def _first_feature_item(items: list[object]) -> dict[str, object]:
    if not items:
        return {}
    return _as_dict(items[0])


def _feature_family_name(feature_name: str) -> str:
    if feature_name.startswith("baseline::") or feature_name == "baseline_aggregate_z":
        return "baseline_outcome_state"
    if feature_name.startswith("goal::"):
        return "goal_family"
    if feature_name.startswith("regimen::"):
        return "regimen_composition"
    if feature_name.startswith("dose::") or feature_name == "total_daily_dose":
        return "dose_intensity"
    if feature_name.startswith("schedule::"):
        return "schedule_family"
    if feature_name.startswith("regimen_status::") or feature_name in {
        "regimen_count",
        "active_regimen_count",
        "planned_regimen_count",
        "reduced_regimen_count",
        "stopped_regimen_count",
    }:
        return "regimen_status_summary"
    if feature_name in {"trajectory_step", "day_index"}:
        return "workflow_timing"
    if feature_name in {
        "wearable_available",
        "cgm_available",
        "genetic_available",
        "nhis_available",
    }:
        return "input_modalities"
    if feature_name in {"adherence_proxy", "side_effect_proxy"} or feature_name.startswith(
        "risk_tier_"
    ):
        return "removed_outcome_leakage"
    return "user_context"


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic",
    "load_json_artifact",
    "render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_markdown",
    "validate_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic",
    "write_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_files",
]
