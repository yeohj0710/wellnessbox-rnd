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
TARGET_PROXY_DROP_BUCKETS = ("large_drop", "medium_drop")


def build_non_cgm_residual_threshold_cross_attribution(
    *,
    dataset_path: str | Path,
    max_cycles: int,
    max_users: int,
    policy_artifact_path: str | Path,
    reference_effect_artifact_path: str | Path,
    candidate_effect_artifact_path: str | Path,
    family_diagnostic: dict[str, object],
    family_diagnostic_path: str | Path,
    subgroup_diagnostic: dict[str, object],
    subgroup_diagnostic_path: str | Path,
    mid_margin_diagnostic: dict[str, object],
    mid_margin_diagnostic_path: str | Path,
    prior_small_drop_attribution: dict[str, object],
    prior_small_drop_attribution_path: str | Path,
) -> dict[str, object]:
    family_cases = collect_non_cgm_threshold_cross_cases(
        dataset_path=dataset_path,
        max_cycles=max_cycles,
        max_users=max_users,
        policy_artifact_path=policy_artifact_path,
        reference_effect_artifact_path=reference_effect_artifact_path,
        candidate_effect_artifact_path=candidate_effect_artifact_path,
    )
    residual_cases = [
        case
        for case in family_cases
        if str(case.get("trajectory_mode")) == TARGET_TRAJECTORY_MODE
        and str(case.get("margin_bucket")) == TARGET_MARGIN_BUCKET
        and str(case.get("proxy_drop_bucket")) in TARGET_PROXY_DROP_BUCKETS
    ]
    residual_cases.sort(key=lambda case: float(case["proxy_drop"]), reverse=True)

    family_target = _as_dict(family_diagnostic.get("target_family"))
    subgroup_target = _as_dict(subgroup_diagnostic.get("subtarget"))
    mid_margin_target = _as_dict(mid_margin_diagnostic.get("bucket_target"))
    prior_chain = _as_dict(prior_small_drop_attribution.get("narrowing_chain"))
    prior_small_drop = _as_dict(prior_chain.get("small_drop"))

    reproduction_chain = {
        "family_case_count": len(family_cases),
        "threshold_duration_sensitive_case_count": sum(
            1
            for case in family_cases
            if str(case.get("trajectory_mode")) == TARGET_TRAJECTORY_MODE
        ),
        "mid_margin_case_count": sum(
            1
            for case in family_cases
            if str(case.get("trajectory_mode")) == TARGET_TRAJECTORY_MODE
            and str(case.get("margin_bucket")) == TARGET_MARGIN_BUCKET
        ),
        "prior_small_drop_case_count": int(prior_small_drop.get("observed_case_count", 0)),
        "current_residual_case_count": len(residual_cases),
    }
    bucket_counts = Counter(str(case["proxy_drop_bucket"]) for case in residual_cases)
    final_cycle_counts = Counter(str(case["final_cycle_index"]) for case in residual_cases)
    trajectory_step_values = sorted(
        {round(float(_feature_value(case, "trajectory_step")), 6) for case in residual_cases}
    )
    day_index_values = sorted(
        {round(float(_feature_value(case, "day_index")), 6) for case in residual_cases}
    )

    bucket_summaries = {
        bucket: _build_bucket_summary(
            [case for case in residual_cases if str(case["proxy_drop_bucket"]) == bucket]
        )
        for bucket in TARGET_PROXY_DROP_BUCKETS
    }
    subgroup_proxy_drop_bucket_counts = _as_dict(
        _as_dict(subgroup_diagnostic.get("workflow_summary")).get("proxy_drop_bucket_counts")
    )
    comfortable_margin_medium_drop_case_count = sum(
        1
        for case in family_cases
        if str(case.get("trajectory_mode")) == TARGET_TRAJECTORY_MODE
        and str(case.get("margin_bucket")) == "comfortable_margin"
        and str(case.get("proxy_drop_bucket")) == "medium_drop"
    )

    residual_contribution = _build_residual_contribution_summary(residual_cases)
    verdict = _build_verdict(
        residual_cases=residual_cases,
        residual_contribution=residual_contribution,
        bucket_summaries=bucket_summaries,
    )

    report = {
        "audit_name": "non_cgm_residual_threshold_cross_attribution_v2",
        "source_artifacts": {
            "dataset_path": str(dataset_path),
            "policy_artifact_path": str(policy_artifact_path),
            "reference_effect_artifact_path": str(reference_effect_artifact_path),
            "candidate_effect_artifact_path": str(candidate_effect_artifact_path),
            "family_diagnostic_path": str(family_diagnostic_path),
            "subgroup_diagnostic_path": str(subgroup_diagnostic_path),
            "mid_margin_diagnostic_path": str(mid_margin_diagnostic_path),
            "prior_small_drop_attribution_path": str(prior_small_drop_attribution_path),
        },
        "target_residual_slice": {
            "decision_family": family_target.get("name"),
            "transition": family_target.get("transition"),
            "trajectory_mode": subgroup_target.get("trajectory_mode"),
            "margin_bucket": mid_margin_target.get("margin_bucket"),
            "proxy_drop_buckets": list(TARGET_PROXY_DROP_BUCKETS),
            "observed_case_count": len(residual_cases),
            "bucket_case_counts": dict(sorted(bucket_counts.items())),
            "all_cases_non_cgm": all(case.get("cgm_available") is False for case in residual_cases),
            "all_final_step_cycle_4": final_cycle_counts == {"4": len(residual_cases)},
            "final_cycle_index_counts": dict(sorted(final_cycle_counts.items())),
            "trajectory_step_values": trajectory_step_values,
            "day_index_values": day_index_values,
        },
        "reproduction_chain": reproduction_chain,
        "artifact_reconciliation": {
            "threshold_duration_sensitive_proxy_drop_bucket_counts": (
                subgroup_proxy_drop_bucket_counts
            ),
            "mid_margin_proxy_drop_bucket_counts": dict(sorted(bucket_counts.items())),
            "comfortable_margin_medium_drop_case_count": (
                comfortable_margin_medium_drop_case_count
            ),
            "reconciliation_note": (
                "The full `threshold_duration_sensitive` subgroup still contains 2 "
                "`medium_drop` cases, but only 1 of them remains inside the requested "
                "`mid_margin` residual surface; the other sits in `comfortable_margin`."
            ),
        },
        "bucket_summaries": bucket_summaries,
        "residual_contribution_summary": residual_contribution,
        "verdict": verdict,
        "example_cases": [_minimal_case_digest(case) for case in residual_cases],
        "summary_findings": _build_summary_findings(
            reproduction_chain=reproduction_chain,
            residual_contribution=residual_contribution,
            verdict=verdict,
            bucket_summaries=bucket_summaries,
        ),
    }
    report["validation_issues"] = validate_non_cgm_residual_threshold_cross_attribution(report)
    return report


def validate_non_cgm_residual_threshold_cross_attribution(
    report: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    target = _as_dict(report.get("target_residual_slice"))
    chain = _as_dict(report.get("reproduction_chain"))
    contribution = _as_dict(report.get("residual_contribution_summary"))
    verdict = _as_dict(report.get("verdict"))
    bucket_summaries = _as_dict(report.get("bucket_summaries"))
    reconciliation = _as_dict(report.get("artifact_reconciliation"))

    if target.get("decision_family") != "non_cgm_continue_to_monitor_threshold_cross":
        issues.append("unexpected_family_name")
    if int(chain.get("family_case_count", 0)) != 26:
        issues.append("unexpected_family_case_count")
    if int(chain.get("threshold_duration_sensitive_case_count", 0)) != 10:
        issues.append("unexpected_threshold_duration_sensitive_case_count")
    if int(chain.get("mid_margin_case_count", 0)) != 9:
        issues.append("unexpected_mid_margin_case_count")
    if int(chain.get("prior_small_drop_case_count", 0)) != 5:
        issues.append("unexpected_prior_small_drop_case_count")
    if int(chain.get("current_residual_case_count", 0)) != 4:
        issues.append("unexpected_residual_case_count")
    if _as_dict(target.get("bucket_case_counts")) != {"large_drop": 3, "medium_drop": 1}:
        issues.append("unexpected_bucket_case_counts")
    if _as_dict(reconciliation.get("threshold_duration_sensitive_proxy_drop_bucket_counts")) != {
        "large_drop": 3,
        "medium_drop": 2,
        "small_drop": 5,
    }:
        issues.append("unexpected_subgroup_proxy_drop_bucket_counts")
    if int(reconciliation.get("comfortable_margin_medium_drop_case_count", 0)) != 1:
        issues.append("unexpected_comfortable_margin_medium_drop_case_count")
    if not bool(target.get("all_cases_non_cgm")):
        issues.append("residual_slice_contains_cgm_case")
    if not bool(target.get("all_final_step_cycle_4")):
        issues.append("residual_slice_not_final_step_only")
    if _as_list(target.get("trajectory_step_values")) != [-0.063114]:
        issues.append("trajectory_step_not_uniform")
    if _as_list(target.get("day_index_values")) != [0.071532]:
        issues.append("day_index_not_uniform")
    negative_abs_share_pct = _as_dict(contribution.get("negative_abs_share_pct"))
    if round(float(negative_abs_share_pct.get("score_geometry", 0.0)), 2) <= 50.0:
        issues.append("score_geometry_share_too_small")
    if round(float(negative_abs_share_pct.get("trajectory_step_behavior", 0.0)), 2) <= 0.0:
        issues.append("trajectory_step_share_missing")
    if round(float(negative_abs_share_pct.get("threshold_duration_interaction", 0.0)), 2) != 0.0:
        issues.append("unexpected_threshold_duration_negative_share")
    if int(contribution.get("mixed_overlap_case_count", 0)) != 4:
        issues.append("unexpected_mixed_overlap_case_count")
    if verdict.get("primary_residual_family") != "mixed_residual_overlap":
        issues.append("unexpected_primary_residual_family")
    if bool(verdict.get("explained_well_enough_for_future_gate_work")):
        issues.append("gate_work_unexpectedly_unblocked")
    large_drop_second = _as_dict(
        _as_dict(bucket_summaries.get("large_drop")).get("second_opposing_feature_counts")
    )
    medium_drop_second = _as_dict(
        _as_dict(bucket_summaries.get("medium_drop")).get("second_opposing_feature_counts")
    )
    if large_drop_second != {"schedule::before_dinner": 3}:
        issues.append("unexpected_large_drop_second_feature_pattern")
    if medium_drop_second != {"dose::l_theanine": 1}:
        issues.append("unexpected_medium_drop_second_feature_pattern")
    if not _as_list(report.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_residual_threshold_cross_attribution_markdown(
    report: dict[str, object]
) -> str:
    lines = [
        "# non-cgm residual threshold-cross attribution v2",
        "",
        "## target residual slice",
        "",
        f"- target_residual_slice: `{report.get('target_residual_slice', {})}`",
        "",
        "## reproduction chain",
        "",
        f"- reproduction_chain: `{report.get('reproduction_chain', {})}`",
        "",
        "## bucket summaries",
        "",
        f"- bucket_summaries: `{report.get('bucket_summaries', {})}`",
        "",
        "## artifact reconciliation",
        "",
        f"- artifact_reconciliation: `{report.get('artifact_reconciliation', {})}`",
        "",
        "## residual contribution summary",
        "",
        f"- residual_contribution_summary: `{report.get('residual_contribution_summary', {})}`",
        "",
        "## verdict",
        "",
        f"- verdict: `{report.get('verdict', {})}`",
        "",
        "## example cases",
        "",
        f"- example_cases: `{report.get('example_cases', [])}`",
        "",
        "## summary findings",
        "",
    ]
    for item in _as_list(report.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{report.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_non_cgm_residual_threshold_cross_attribution_files(
    *,
    report: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_non_cgm_residual_threshold_cross_attribution_markdown(report),
        encoding="utf-8",
    )


def _build_bucket_summary(cases: list[dict[str, object]]) -> dict[str, object]:
    if not cases:
        return {
            "observed_case_count": 0,
            "second_opposing_feature_counts": {},
        }

    second_feature_counts = Counter()
    top_negative_features: list[dict[str, object]] = []
    for case in cases:
        feature_name, feature_value = _second_opposing_feature(case)
        if feature_name is not None:
            second_feature_counts[feature_name] += 1
            top_negative_features.append(
                {
                    "user_id": case["user_id"],
                    "second_opposing_feature": feature_name,
                    "value": round(abs(feature_value), 6),
                }
            )

    return {
        "observed_case_count": len(cases),
        "proxy_drop_mean": round(mean(float(case["proxy_drop"]) for case in cases), 6),
        "reference_continue_margin_mean": round(
            mean(float(case["reference_continue_margin"]) for case in cases), 6
        ),
        "candidate_monitor_shortfall_mean": round(
            mean(float(case["candidate_monitor_shortfall"]) for case in cases), 6
        ),
        "intercept_abs_mean": round(
            mean(abs(float(_feature_value(case, "__intercept__"))) for case in cases), 6
        ),
        "trajectory_step_abs_mean": round(
            mean(abs(float(_feature_value(case, "trajectory_step"))) for case in cases), 6
        ),
        "trajectory_step_covers_shortfall_case_count": sum(
            1
            for case in cases
            if abs(float(_feature_value(case, "trajectory_step")))
            >= float(case["candidate_monitor_shortfall"])
        ),
        "intercept_covers_shortfall_case_count": sum(
            1
            for case in cases
            if abs(float(_feature_value(case, "__intercept__")))
            >= float(case["candidate_monitor_shortfall"])
        ),
        "second_opposing_feature_counts": dict(sorted(second_feature_counts.items())),
        "second_opposing_feature_examples": top_negative_features,
    }


def _build_residual_contribution_summary(
    residual_cases: list[dict[str, object]]
) -> dict[str, object]:
    negative_abs_by_category: dict[str, float] = defaultdict(float)
    category_case_presence: dict[str, int] = defaultdict(int)
    mixed_overlap_case_count = 0
    threshold_context_case_count = 0

    for case in residual_cases:
        per_case_category_abs: dict[str, float] = defaultdict(float)
        for feature_name, raw_value in _as_dict(case.get("feature_delta")).items():
            value = float(raw_value)
            if value >= 0.0:
                continue
            category = _residual_family_for_feature(str(feature_name))
            per_case_category_abs[category] += abs(value)
        for category, abs_value in per_case_category_abs.items():
            negative_abs_by_category[category] += abs_value
            if abs_value > 0.0:
                category_case_presence[category] += 1
        if (
            per_case_category_abs.get("score_geometry", 0.0) > 0.0
            and per_case_category_abs.get("trajectory_step_behavior", 0.0) > 0.0
        ):
            mixed_overlap_case_count += 1
        if (
            case.get("trajectory_mode") == TARGET_TRAJECTORY_MODE
            and int(case.get("final_cycle_index", 0)) == 4
        ):
            threshold_context_case_count += 1

    total_negative_abs = sum(negative_abs_by_category.values())
    negative_abs_share_pct = {
        category: round((value / total_negative_abs) * 100.0, 2)
        for category, value in sorted(negative_abs_by_category.items())
        if total_negative_abs > 0.0
    }

    return {
        "negative_abs_total": round(total_negative_abs, 6),
        "negative_abs_by_family": {
            category: round(value, 6)
            for category, value in sorted(negative_abs_by_category.items())
        },
        "negative_abs_share_pct": negative_abs_share_pct,
        "category_case_presence": dict(sorted(category_case_presence.items())),
        "mixed_overlap_case_count": mixed_overlap_case_count,
        "mixed_overlap_case_pct": round(
            (mixed_overlap_case_count / len(residual_cases)) * 100.0, 2
        ),
        "threshold_duration_context_case_count": threshold_context_case_count,
        "threshold_duration_context_pct": round(
            (threshold_context_case_count / len(residual_cases)) * 100.0, 2
        ),
        "interpretation_note": (
            "threshold_duration_interaction is treated as direct negative day_index mass only; "
            "its contextual presence is recorded separately because day_index is uniformly "
            "positive on this residual slice."
        ),
    }


def _build_verdict(
    *,
    residual_cases: list[dict[str, object]],
    residual_contribution: dict[str, object],
    bucket_summaries: dict[str, object],
) -> dict[str, object]:
    negative_abs_share_pct = _as_dict(residual_contribution.get("negative_abs_share_pct"))
    score_geometry_share_pct = float(negative_abs_share_pct.get("score_geometry", 0.0))
    trajectory_step_share_pct = float(
        negative_abs_share_pct.get("trajectory_step_behavior", 0.0)
    )
    mixed_overlap_case_pct = float(residual_contribution.get("mixed_overlap_case_pct", 0.0))

    primary_residual_family = "mixed_residual_overlap"
    if mixed_overlap_case_pct < 100.0 and score_geometry_share_pct >= 60.0:
        primary_residual_family = "score_geometry"
    if mixed_overlap_case_pct < 100.0 and trajectory_step_share_pct >= 60.0:
        primary_residual_family = "trajectory_step_behavior"

    large_drop_second = _as_dict(
        _as_dict(bucket_summaries.get("large_drop")).get("second_opposing_feature_counts")
    )
    medium_drop_second = _as_dict(
        _as_dict(bucket_summaries.get("medium_drop")).get("second_opposing_feature_counts")
    )
    single_local_contract_supported = (
        len(large_drop_second) == 1
        and len(medium_drop_second) == 1
        and set(large_drop_second) == set(medium_drop_second)
    )

    return {
        "primary_residual_family": primary_residual_family,
        "score_geometry_share_pct": round(score_geometry_share_pct, 2),
        "trajectory_step_behavior_share_pct": round(trajectory_step_share_pct, 2),
        "threshold_duration_interaction_direct_share_pct": round(
            float(negative_abs_share_pct.get("threshold_duration_interaction", 0.0)), 2
        ),
        "mixed_overlap_case_pct": round(mixed_overlap_case_pct, 2),
        "explained_well_enough_for_future_gate_work": False,
        "why_not_explained_well_enough": (
            "The residual is narrowed to 4 final-step cases, but it still requires a mixed "
            "story: global score geometry dominates total opposing mass, `trajectory_step` is "
            "uniformly present across all cases, and the second opposing feature differs by "
            "bucket (`schedule::before_dinner` for `large_drop`, `dose::l_theanine` for "
            "`medium_drop`)."
        ),
        "single_local_contract_supported_now": single_local_contract_supported,
        "current_smallest_credible_surface": (
            "threshold_duration_sensitive / mid_margin / {large_drop, medium_drop} with "
            "mixed score_geometry + trajectory_step overlap"
        ),
        "explained_vs_unexplained": {
            "explained": [
                "family reproduction and residual count",
                "final-step only threshold-duration context",
                "uniform negative trajectory_step contribution",
                "score_geometry dominance by negative mass share",
                "bucket-specific second opposing feature pattern",
            ],
            "still_unexplained": [
                "one bucket-agnostic local contract comparable to the prior 5-case small_drop path",
                "family-wide residual closure beyond this 4-case surface",
            ],
        },
    }


def _build_summary_findings(
    *,
    reproduction_chain: dict[str, object],
    residual_contribution: dict[str, object],
    verdict: dict[str, object],
    bucket_summaries: dict[str, object],
) -> list[str]:
    negative_abs_share_pct = _as_dict(residual_contribution.get("negative_abs_share_pct"))
    large_drop_second = _as_dict(
        _as_dict(bucket_summaries.get("large_drop")).get("second_opposing_feature_counts")
    )
    medium_drop_second = _as_dict(
        _as_dict(bucket_summaries.get("medium_drop")).get("second_opposing_feature_counts")
    )
    return [
        (
            "The dominant replay family still reproduces at 26 cases, and the requested "
            "residual slice narrows cleanly to 4 cases after removing the already-closed "
            "5-case `small_drop` path from the 9-case `threshold_duration_sensitive` / "
            "`mid_margin` bucket."
        ),
        (
            "All 4 residual cases remain non-CGM, final-step only, and share the same "
            "`trajectory_step = -0.063114` with the same positive `day_index = 0.071532`, "
            "so threshold-duration context is present but not a separate negative driver."
        ),
        (
            "Measured opposing mass is still dominated by score geometry "
            f"({negative_abs_share_pct.get('score_geometry')}%), with uniform "
            f"`trajectory_step` behavior providing the remaining "
            f"{negative_abs_share_pct.get('trajectory_step_behavior')}%."
        ),
        (
            "The residual is mixed rather than single-surface: `large_drop` cases share "
            f"{large_drop_second}, "
            "while the lone `medium_drop` case shifts to "
            f"{medium_drop_second}."
        ),
        (
            "So this loop explains the remaining residual well enough to name its smallest "
            "credible cause surface, but not well enough to support future gate work yet."
        ),
    ]


def _second_opposing_feature(case: dict[str, object]) -> tuple[str | None, float]:
    negatives = sorted(
        (
            (str(feature_name), float(value))
            for feature_name, value in _as_dict(case.get("feature_delta")).items()
            if float(value) < 0.0 and str(feature_name) not in {"__intercept__", "trajectory_step"}
        ),
        key=lambda item: item[1],
    )
    if not negatives:
        return None, 0.0
    feature_name, value = negatives[0]
    return feature_name, value


def _feature_value(case: dict[str, object], feature_name: str) -> float:
    return float(_as_dict(case.get("feature_delta")).get(feature_name, 0.0))


def _residual_family_for_feature(feature_name: str) -> str:
    if feature_name == "trajectory_step":
        return "trajectory_step_behavior"
    if feature_name == "day_index":
        return "threshold_duration_interaction"
    return "score_geometry"


def _minimal_case_digest(case: dict[str, object]) -> dict[str, object]:
    second_feature_name, second_feature_value = _second_opposing_feature(case)
    return {
        "user_id": case["user_id"],
        "proxy_drop_bucket": case["proxy_drop_bucket"],
        "proxy_drop": case["proxy_drop"],
        "reference_continue_margin": case["reference_continue_margin"],
        "candidate_monitor_shortfall": case["candidate_monitor_shortfall"],
        "trajectory_step": round(_feature_value(case, "trajectory_step"), 6),
        "day_index": round(_feature_value(case, "day_index"), 6),
        "second_opposing_feature": second_feature_name,
        "second_opposing_feature_value": round(second_feature_value, 6),
    }


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_residual_threshold_cross_attribution",
    "load_json_artifact",
    "render_non_cgm_residual_threshold_cross_attribution_markdown",
    "validate_non_cgm_residual_threshold_cross_attribution",
    "write_non_cgm_residual_threshold_cross_attribution_files",
]
