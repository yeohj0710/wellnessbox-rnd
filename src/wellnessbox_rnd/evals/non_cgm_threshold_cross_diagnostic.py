from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from wellnessbox_rnd.models import build_effect_feature_dict_v1, load_effect_model_v1_artifact
from wellnessbox_rnd.models.effect_model_v1 import EffectFeatureVectorizerV1
from wellnessbox_rnd.simulation import simulate_closed_loop_batch
from wellnessbox_rnd.simulation.closed_loop_v0 import _load_records_by_user

NON_CGM_CONTINUE_TO_MONITOR_FAMILY = "non_cgm_continue_to_monitor_threshold_cross"
NON_CGM_CONTINUE_THRESHOLD = 0.24


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_non_cgm_threshold_cross_diagnostic(
    *,
    dataset_path: str | Path,
    max_cycles: int,
    max_users: int,
    policy_artifact_path: str | Path,
    reference_effect_artifact_path: str | Path,
    candidate_effect_artifact_path: str | Path,
    compare_report: dict[str, object],
    compare_report_path: str | Path,
) -> dict[str, object]:
    reference_artifact = load_effect_model_v1_artifact(reference_effect_artifact_path)
    candidate_artifact = load_effect_model_v1_artifact(candidate_effect_artifact_path)
    cases = collect_non_cgm_threshold_cross_cases(
        dataset_path=dataset_path,
        max_cycles=max_cycles,
        max_users=max_users,
        policy_artifact_path=policy_artifact_path,
        reference_effect_artifact_path=reference_effect_artifact_path,
        candidate_effect_artifact_path=candidate_effect_artifact_path,
    )
    expected_case_count = _expected_case_count(compare_report)
    case_summary = _build_case_summary(cases)
    workflow_summary = _build_workflow_summary(cases)
    feature_summary = _build_feature_summary(
        cases,
        reference_artifact=reference_artifact,
        candidate_artifact=candidate_artifact,
    )
    interpretation = _build_interpretation(
        case_summary=case_summary,
        workflow_summary=workflow_summary,
        feature_summary=feature_summary,
    )
    readable_summary = _build_readable_summary(
        target_family_case_count=len(cases),
        workflow_summary=workflow_summary,
        case_summary=case_summary,
        feature_summary=feature_summary,
        interpretation=interpretation,
    )

    diagnostic = {
        "audit_name": "non_cgm_threshold_cross_diagnostic_v1",
        "source_artifacts": {
            "dataset_path": str(dataset_path),
            "policy_artifact_path": str(policy_artifact_path),
            "reference_effect_artifact_path": str(reference_effect_artifact_path),
            "candidate_effect_artifact_path": str(candidate_effect_artifact_path),
            "compare_report_path": str(compare_report_path),
        },
        "target_family": {
            "name": NON_CGM_CONTINUE_TO_MONITOR_FAMILY,
            "mode": "learned_effect_guarded",
            "expected_case_count_from_compare": expected_case_count,
            "observed_case_count": len(cases),
            "transition": "continue_plan->monitor_only",
            "non_cgm_only": True,
        },
        "workflow_summary": workflow_summary,
        "case_summary": case_summary,
        "feature_summary": feature_summary,
        "interpretation": interpretation,
        "readable_summary": readable_summary,
        "summary_findings": _build_summary_findings(readable_summary),
        "example_cases": cases[:8],
    }
    diagnostic["validation_issues"] = validate_non_cgm_threshold_cross_diagnostic(
        diagnostic
    )
    return diagnostic


def collect_non_cgm_threshold_cross_cases(
    *,
    dataset_path: str | Path,
    max_cycles: int,
    max_users: int,
    policy_artifact_path: str | Path,
    reference_effect_artifact_path: str | Path,
    candidate_effect_artifact_path: str | Path,
) -> list[dict[str, object]]:
    records_by_user = _load_records_by_user(str(dataset_path))
    reference_artifact = load_effect_model_v1_artifact(reference_effect_artifact_path)
    candidate_artifact = load_effect_model_v1_artifact(candidate_effect_artifact_path)
    reference_effect_only = simulate_closed_loop_batch(
        dataset_path=str(dataset_path),
        max_cycles=max_cycles,
        max_users=max_users,
        model_artifact_path=str(reference_effect_artifact_path),
        policy_model_artifact_path=str(policy_artifact_path),
        enable_learned_policy=False,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_guarded",
    )
    candidate_effect_only = simulate_closed_loop_batch(
        dataset_path=str(dataset_path),
        max_cycles=max_cycles,
        max_users=max_users,
        model_artifact_path=str(candidate_effect_artifact_path),
        policy_model_artifact_path=str(policy_artifact_path),
        enable_learned_policy=False,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_guarded",
    )
    return _collect_target_cases(
        reference_effect_only=reference_effect_only,
        candidate_effect_only=candidate_effect_only,
        records_by_user=records_by_user,
        reference_artifact=reference_artifact,
        candidate_artifact=candidate_artifact,
    )


def validate_non_cgm_threshold_cross_diagnostic(
    diagnostic: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    target_family = _as_dict(diagnostic.get("target_family"))
    case_summary = _as_dict(diagnostic.get("case_summary"))
    workflow_summary = _as_dict(diagnostic.get("workflow_summary"))
    interpretation = _as_dict(diagnostic.get("interpretation"))
    readable_summary = _as_dict(diagnostic.get("readable_summary"))

    expected_case_count = int(target_family.get("expected_case_count_from_compare", 0))
    observed_case_count = int(target_family.get("observed_case_count", 0))
    if expected_case_count != observed_case_count:
        issues.append("compare_and_diagnostic_case_count_mismatch")
    if case_summary.get("all_cases_non_cgm") is not True:
        issues.append("non_cgm_family_contains_cgm_case")
    if case_summary.get("all_transitions_match_target") is not True:
        issues.append("target_transition_drift_detected")
    if case_summary.get("all_band_crosses_match_target") is not True:
        issues.append("band_cross_drift_detected")
    if not _as_list(_as_dict(diagnostic.get("feature_summary")).get("top_absolute_features")):
        issues.append("missing_feature_level_evidence")
    if "threshold_edge_only_story_supported" not in interpretation:
        issues.append("missing_threshold_edge_interpretation")
    if (
        int(
            sum(
                int(value)
                for value in _as_dict(
                    workflow_summary.get("reference_continue_margin_bucket_counts")
                ).values()
            )
        )
        != observed_case_count
    ):
        issues.append("margin_bucket_count_mismatch")
    if (
        int(
            sum(
                int(value)
                for value in _as_dict(workflow_summary.get("proxy_drop_bucket_counts")).values()
            )
        )
        != observed_case_count
    ):
        issues.append("proxy_drop_bucket_count_mismatch")
    if (
        _as_dict(readable_summary.get("dominant_feature_digest")).get("family")
        != interpretation.get("dominant_feature_family")
    ):
        issues.append("dominant_feature_family_summary_mismatch")
    if not _as_list(diagnostic.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_threshold_cross_diagnostic_markdown(
    diagnostic: dict[str, object]
) -> str:
    target_family = _as_dict(diagnostic.get("target_family"))
    workflow_summary = _as_dict(diagnostic.get("workflow_summary"))
    case_summary = _as_dict(diagnostic.get("case_summary"))
    feature_summary = _as_dict(diagnostic.get("feature_summary"))
    interpretation = _as_dict(diagnostic.get("interpretation"))
    readable_summary = _as_dict(diagnostic.get("readable_summary"))
    lines = [
        "# non-cgm threshold-cross diagnostic v1",
        "",
        "## readable summary",
        "",
        f"- readable_summary: `{readable_summary}`",
        "",
        "## target family",
        "",
        f"- target_family: `{target_family}`",
        "",
        "## workflow summary",
        "",
        f"- workflow_summary: `{workflow_summary}`",
        "",
        "## case summary",
        "",
        f"- case_summary: `{case_summary}`",
        "",
        "## feature summary",
        "",
        f"- feature_summary: `{feature_summary}`",
        "",
        "## interpretation",
        "",
        f"- interpretation: `{interpretation}`",
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


def write_non_cgm_threshold_cross_diagnostic_files(
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
        render_non_cgm_threshold_cross_diagnostic_markdown(diagnostic),
        encoding="utf-8",
    )


def _collect_target_cases(
    *,
    reference_effect_only,
    candidate_effect_only,
    records_by_user,
    reference_artifact,
    candidate_artifact,
) -> list[dict[str, object]]:
    reference_by_user = {
        scenario.user_id: scenario for scenario in reference_effect_only.scenario_reports
    }
    candidate_by_user = {
        scenario.user_id: scenario for scenario in candidate_effect_only.scenario_reports
    }
    cases: list[dict[str, object]] = []
    for user_id, reference_scenario in reference_by_user.items():
        candidate_scenario = candidate_by_user[user_id]
        if reference_scenario.final_policy_action == candidate_scenario.final_policy_action:
            continue
        case = _build_target_case(
            user_id=user_id,
            reference_scenario=reference_scenario,
            candidate_scenario=candidate_scenario,
            records_by_user=records_by_user,
            reference_artifact=reference_artifact,
            candidate_artifact=candidate_artifact,
        )
        if not case:
            continue
        case["reference_continue_margin"] = round(
            float(case["reference_proxy"]) - NON_CGM_CONTINUE_THRESHOLD,
            6,
        )
        case["candidate_monitor_shortfall"] = round(
            NON_CGM_CONTINUE_THRESHOLD - float(case["candidate_proxy"]),
            6,
        )
        case["proxy_drop"] = round(
            float(case["reference_proxy"]) - float(case["candidate_proxy"]),
            6,
        )
        case["margin_bucket"] = _margin_bucket(float(case["reference_continue_margin"]))
        case["proxy_drop_bucket"] = _proxy_drop_bucket(float(case["proxy_drop"]))
        case["feature_delta"] = _feature_contribution_delta_for_record(
            reference_artifact=reference_artifact,
            candidate_artifact=candidate_artifact,
            record=records_by_user[user_id][int(case["final_cycle_index"])],
        )
        cases.append(case)
    cases.sort(key=lambda case: float(case["proxy_drop"]), reverse=True)
    return cases


def _build_target_case(
    *,
    user_id: str,
    reference_scenario,
    candidate_scenario,
    records_by_user,
    reference_artifact,
    candidate_artifact,
) -> dict[str, object]:
    reference_step = reference_scenario.trace[-1]
    candidate_step = candidate_scenario.trace[-1]
    record = records_by_user[user_id][reference_step.cycle_index]
    reference_proxy = float(reference_step.predicted_effect_proxy)
    candidate_proxy = float(candidate_step.predicted_effect_proxy)
    reference_band = _policy_band_name(
        proxy_value=reference_proxy,
        cgm_available=record.request.input_availability.cgm,
    )
    candidate_band = _policy_band_name(
        proxy_value=candidate_proxy,
        cgm_available=record.request.input_availability.cgm,
    )
    case = {
        "user_id": user_id,
        "record_id": record.record_id,
        "trajectory_mode": record.trajectory_mode,
        "risk_tier": record.labels.risk_tier,
        "cgm_available": record.request.input_availability.cgm,
        "final_cycle_index": reference_step.cycle_index,
        "reference_final_action": reference_scenario.final_policy_action.value,
        "candidate_final_action": candidate_scenario.final_policy_action.value,
        "reference_proxy": round(reference_proxy, 6),
        "candidate_proxy": round(candidate_proxy, 6),
        "proxy_delta": round(candidate_proxy - reference_proxy, 6),
        "reference_band": reference_band,
        "candidate_band": candidate_band,
        "decision_family": _classify_final_decision_family(
            reference_action=reference_scenario.final_policy_action.value,
            candidate_action=candidate_scenario.final_policy_action.value,
            reference_band=reference_band,
            candidate_band=candidate_band,
            cgm_available=record.request.input_availability.cgm,
        ),
        "feature_family_delta": _feature_family_delta_for_record(
            reference_artifact=reference_artifact,
            candidate_artifact=candidate_artifact,
            record=record,
        ),
    }
    if case["decision_family"] != NON_CGM_CONTINUE_TO_MONITOR_FAMILY:
        return {}
    return case


def _build_workflow_summary(cases: list[dict[str, object]]) -> dict[str, object]:
    trajectory_counts = Counter(str(case["trajectory_mode"]) for case in cases)
    final_cycle_counts = Counter(str(case["final_cycle_index"]) for case in cases)
    margin_bucket_counts = Counter(str(case["margin_bucket"]) for case in cases)
    proxy_drop_bucket_counts = Counter(str(case["proxy_drop_bucket"]) for case in cases)
    return {
        "trajectory_mode_counts": dict(sorted(trajectory_counts.items())),
        "final_cycle_index_counts": dict(sorted(final_cycle_counts.items())),
        "reference_continue_margin_bucket_counts": dict(sorted(margin_bucket_counts.items())),
        "proxy_drop_bucket_counts": dict(sorted(proxy_drop_bucket_counts.items())),
    }


def _build_case_summary(cases: list[dict[str, object]]) -> dict[str, object]:
    if not cases:
        return {
            "all_cases_non_cgm": False,
            "all_transitions_match_target": False,
            "all_band_crosses_match_target": False,
        }
    reference_margins = [float(case["reference_continue_margin"]) for case in cases]
    candidate_shortfalls = [float(case["candidate_monitor_shortfall"]) for case in cases]
    proxy_drops = [float(case["proxy_drop"]) for case in cases]
    return {
        "all_cases_non_cgm": all(case["cgm_available"] is False for case in cases),
        "all_transitions_match_target": all(
            case["reference_final_action"] == "continue_plan"
            and case["candidate_final_action"] == "monitor_only"
            for case in cases
        ),
        "all_band_crosses_match_target": all(
            case["reference_band"] == "continue_plan_band"
            and case["candidate_band"] == "monitor_only_band"
            for case in cases
        ),
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


def _build_feature_summary(
    cases: list[dict[str, object]],
    *,
    reference_artifact,
    candidate_artifact,
) -> dict[str, object]:
    if not cases:
        return {
            "feature_family_delta_summary": {},
            "top_absolute_features": [],
            "top_negative_features": [],
            "top_positive_features": [],
        }
    feature_family_delta_summary = _aggregate_feature_family_deltas(cases)
    signed_sums: dict[str, float] = defaultdict(float)
    abs_sums: dict[str, float] = defaultdict(float)
    for case in cases:
        for feature_name, delta in _as_dict(case.get("feature_delta")).items():
            signed_sums[str(feature_name)] += float(delta)
            abs_sums[str(feature_name)] += abs(float(delta))
    return {
        "feature_family_delta_summary": feature_family_delta_summary,
        "top_absolute_features": _top_feature_items(abs_sums, reverse=True),
        "top_negative_features": _top_feature_items(
            {key: value for key, value in signed_sums.items() if value < 0.0},
            reverse=False,
        ),
        "top_positive_features": _top_feature_items(
            {key: value for key, value in signed_sums.items() if value > 0.0},
            reverse=True,
        ),
        "reference_only_structural_top_features": [
            item
            for item in _top_feature_items(abs_sums, reverse=True)
            if str(item["feature"]) in set(reference_artifact.feature_names)
            and str(item["feature"]) not in set(candidate_artifact.feature_names)
        ],
    }


def _build_interpretation(
    *,
    case_summary: dict[str, object],
    workflow_summary: dict[str, object],
    feature_summary: dict[str, object],
) -> dict[str, object]:
    margin_bucket_counts = _as_dict(
        workflow_summary.get("reference_continue_margin_bucket_counts")
    )
    near_edge_count = int(margin_bucket_counts.get("near_edge", 0))
    mid_margin_count = int(margin_bucket_counts.get("mid_margin", 0))
    comfortable_count = int(margin_bucket_counts.get("comfortable_margin", 0))
    total_cases = near_edge_count + mid_margin_count + comfortable_count
    threshold_edge_only_story_supported = total_cases > 0 and near_edge_count == total_cases

    top_family = _first_family_name(
        _as_list(
            _as_dict(feature_summary.get("feature_family_delta_summary")).get(
                "top_absolute_families"
            )
        )
    )
    top_feature = _first_feature_name(_as_list(feature_summary.get("top_absolute_features")))

    return {
        "threshold_edge_only_story_supported": threshold_edge_only_story_supported,
        "near_edge_case_count": near_edge_count,
        "non_edge_case_count": mid_margin_count + comfortable_count,
        "dominant_workflow_modes": _top_count_items(
            _as_dict(workflow_summary.get("trajectory_mode_counts"))
        ),
        "dominant_feature_family": top_family,
        "dominant_feature": top_feature,
        "reference_continue_margin_mean": _as_dict(
            case_summary.get("reference_continue_margin_summary")
        ).get("mean"),
        "reference_only_structural_delta_present": bool(
            _as_list(feature_summary.get("reference_only_structural_top_features"))
        ),
        "summary": (
            "This regression is not explained as pure threshold-edge widening alone: "
            f"{mid_margin_count + comfortable_count}/{total_cases} cases start with more "
            "than a near-edge continue margin, and the dominant contribution pattern is "
            f"{top_family} led by {top_feature}."
        ),
    }


def _build_readable_summary(
    *,
    target_family_case_count: int,
    workflow_summary: dict[str, object],
    case_summary: dict[str, object],
    feature_summary: dict[str, object],
    interpretation: dict[str, object],
) -> dict[str, object]:
    margin_buckets = _as_dict(workflow_summary.get("reference_continue_margin_bucket_counts"))
    proxy_drop_buckets = _as_dict(workflow_summary.get("proxy_drop_bucket_counts"))
    workflow_modes = _as_dict(workflow_summary.get("trajectory_mode_counts"))
    top_feature = _first_feature_item(_as_list(feature_summary.get("top_absolute_features")))
    reference_only_feature = _first_feature_item(
        _as_list(feature_summary.get("reference_only_structural_top_features"))
    )
    return {
        "case_digest": {
            "observed_case_count": target_family_case_count,
            "transition": "continue_plan->monitor_only",
            "all_cases_non_cgm": case_summary.get("all_cases_non_cgm"),
            "threshold_edge_only_story_supported": interpretation.get(
                "threshold_edge_only_story_supported"
            ),
        },
        "margin_digest": {
            "reference_continue_margin_mean": _as_dict(
                case_summary.get("reference_continue_margin_summary")
            ).get("mean"),
            "reference_continue_margin_bucket_counts": margin_buckets,
            "proxy_drop_mean": _as_dict(case_summary.get("proxy_drop_summary")).get("mean"),
            "proxy_drop_bucket_counts": proxy_drop_buckets,
        },
        "workflow_digest": {
            "dominant_workflow_modes": _top_count_items(workflow_modes),
        },
        "dominant_feature_digest": {
            "family": interpretation.get("dominant_feature_family"),
            "feature": interpretation.get("dominant_feature"),
            "top_absolute_feature": top_feature,
            "reference_only_structural_feature": reference_only_feature,
        },
    }


def _build_summary_findings(readable_summary: dict[str, object]) -> list[str]:
    case_digest = _as_dict(readable_summary.get("case_digest"))
    margin_digest = _as_dict(readable_summary.get("margin_digest"))
    dominant_feature_digest = _as_dict(readable_summary.get("dominant_feature_digest"))
    return [
        (
            "The current dominant low-risk replay blocker remains "
            "`non_cgm_continue_to_monitor_threshold_cross` with "
            f"{case_digest.get('observed_case_count')} observed non-CGM "
            "`continue_plan->monitor_only` cases."
        ),
        (
            "The blocker is not a pure threshold-edge story: current reference "
            f"margin buckets are {margin_digest.get('reference_continue_margin_bucket_counts')}."
        ),
        (
            "The current dominant feature family remains "
            f"`{dominant_feature_digest.get('family')}`, led by "
            f"`{dominant_feature_digest.get('feature')}`."
        ),
    ]


def _expected_case_count(compare_report: dict[str, object]) -> int:
    effect_only = _as_dict(
        _as_dict(compare_report.get("slice_deltas")).get("learned_effect_guarded")
    )
    low_risk_delta = _as_dict(effect_only.get("low_risk_final_action_delta"))
    return abs(int(low_risk_delta.get("monitor_only", 0)))


def _feature_contribution_delta_for_record(
    *,
    reference_artifact,
    candidate_artifact,
    record,
) -> dict[str, float]:
    reference_contributions = _aggregate_feature_contributions(
        artifact=reference_artifact,
        record=record,
    )
    candidate_contributions = _aggregate_feature_contributions(
        artifact=candidate_artifact,
        record=record,
    )
    return {
        feature_name: round(
            candidate_contributions.get(feature_name, 0.0)
            - reference_contributions.get(feature_name, 0.0),
            6,
        )
        for feature_name in sorted(
            set(reference_contributions) | set(candidate_contributions)
        )
    }


def _aggregate_feature_contributions(
    *,
    artifact,
    record,
) -> dict[str, float]:
    feature_row = build_effect_feature_dict_v1(record)
    vectorizer = EffectFeatureVectorizerV1(feature_names=artifact.feature_names)
    vector = vectorizer.transform([feature_row])[0]
    feature_totals: dict[str, float] = defaultdict(float)
    feature_totals["__intercept__"] = _mean_output_intercept(artifact)
    for output_index in range(len(artifact.output_names)):
        output_weights = artifact.weights[output_index]
        for feature_name, feature_value, weight in zip(
            artifact.feature_names,
            vector,
            output_weights,
            strict=True,
        ):
            feature_totals[str(feature_name)] += (
                float(weight) * float(feature_value) / len(artifact.output_names)
            )
    return dict(feature_totals)


def _feature_family_delta_for_record(
    *,
    reference_artifact,
    candidate_artifact,
    record,
) -> dict[str, float]:
    reference_contributions = _aggregate_feature_family_contributions(
        artifact=reference_artifact,
        record=record,
    )
    candidate_contributions = _aggregate_feature_family_contributions(
        artifact=candidate_artifact,
        record=record,
    )
    return {
        family: round(
            candidate_contributions.get(family, 0.0)
            - reference_contributions.get(family, 0.0),
            6,
        )
        for family in sorted(set(reference_contributions) | set(candidate_contributions))
    }


def _aggregate_feature_family_contributions(
    *,
    artifact,
    record,
) -> dict[str, float]:
    feature_row = build_effect_feature_dict_v1(record)
    vectorizer = EffectFeatureVectorizerV1(feature_names=artifact.feature_names)
    vector = vectorizer.transform([feature_row])[0]
    family_totals: dict[str, float] = defaultdict(float)
    family_totals["intercept"] = _mean_output_intercept(artifact)
    for output_index in range(len(artifact.output_names)):
        output_weights = artifact.weights[output_index]
        for feature_name, feature_value, weight in zip(
            artifact.feature_names,
            vector,
            output_weights,
            strict=True,
        ):
            family_totals[_feature_family_name(feature_name)] += (
                float(weight) * float(feature_value) / len(artifact.output_names)
            )
    return dict(family_totals)


def _aggregate_feature_family_deltas(cases: list[dict[str, object]]) -> dict[str, object]:
    signed_sums: dict[str, float] = defaultdict(float)
    abs_sums: dict[str, float] = defaultdict(float)
    for case in cases:
        for family, delta in _as_dict(case.get("feature_family_delta")).items():
            signed_sums[str(family)] += float(delta)
            abs_sums[str(family)] += abs(float(delta))
    return {
        "top_absolute_families": _top_family_items(abs_sums, reverse=True),
        "top_negative_signed_families": _top_family_items(
            {key: value for key, value in signed_sums.items() if value < 0.0},
            reverse=False,
        ),
        "top_positive_signed_families": _top_family_items(
            {key: value for key, value in signed_sums.items() if value > 0.0},
            reverse=True,
        ),
    }


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


def _classify_final_decision_family(
    *,
    reference_action: str,
    candidate_action: str,
    reference_band: str,
    candidate_band: str,
    cgm_available: bool,
) -> str:
    if (
        not cgm_available
        and reference_action == "continue_plan"
        and candidate_action == "monitor_only"
        and reference_band == "continue_plan_band"
        and candidate_band == "monitor_only_band"
    ):
        return NON_CGM_CONTINUE_TO_MONITOR_FAMILY
    if reference_band != candidate_band:
        return "effect_proxy_band_cross"
    return "effect_proxy_same_band_action_shift"


def _policy_band_name(*, proxy_value: float, cgm_available: bool) -> str:
    if proxy_value < 0.14:
        return "re_optimize_band"
    if proxy_value < (0.37 if cgm_available else NON_CGM_CONTINUE_THRESHOLD):
        return "monitor_only_band"
    return "continue_plan_band"


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


def _mean_output_intercept(artifact) -> float:
    if not artifact.intercepts:
        return 0.0
    return float(sum(artifact.intercepts) / len(artifact.intercepts))


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
                    _feature_family_name(feature_name)
                    if feature_name != "__intercept__"
                    else "intercept"
                ),
                "value": round(value, 6),
            }
            for feature_name, value in feature_map.items()
        ),
        key=lambda item: float(item["value"]),
        reverse=reverse,
    )
    return ordered[:limit]


def _margin_bucket(margin: float) -> str:
    if margin <= 0.03:
        return "near_edge"
    if margin <= 0.06:
        return "mid_margin"
    return "comfortable_margin"


def _proxy_drop_bucket(proxy_drop: float) -> str:
    if proxy_drop < 0.06:
        return "small_drop"
    if proxy_drop < 0.09:
        return "medium_drop"
    return "large_drop"


def _top_count_items(counter_map: dict[str, object], limit: int = 3) -> list[dict[str, object]]:
    ordered = sorted(
        ({"name": key, "count": int(value)} for key, value in counter_map.items()),
        key=lambda item: int(item["count"]),
        reverse=True,
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


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_threshold_cross_diagnostic",
    "collect_non_cgm_threshold_cross_cases",
    "load_json_artifact",
    "render_non_cgm_threshold_cross_diagnostic_markdown",
    "validate_non_cgm_threshold_cross_diagnostic",
    "write_non_cgm_threshold_cross_diagnostic_files",
]
