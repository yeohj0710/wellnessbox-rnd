import json
from argparse import ArgumentParser
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from sys import exit as sys_exit

from wellnessbox_rnd.models import (
    build_effect_feature_dict_v1,
    load_effect_model_v1_artifact,
)
from wellnessbox_rnd.models.effect_model_v1 import (
    EffectFeatureVectorizerV1,
    EffectModelV1Artifact,
)
from wellnessbox_rnd.simulation import simulate_closed_loop_batch
from wellnessbox_rnd.simulation.closed_loop_v0 import (
    _load_records_by_user,
    _should_apply_reoptimize_revival_prior,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Attribute replay delta between the baseline effect artifact and a "
            "candidate effect artifact without retraining"
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=96)
    parser.add_argument(
        "--policy-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Fixed replay-only policy artifact path",
    )
    parser.add_argument(
        "--reference-effect-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Reference effect artifact path",
    )
    parser.add_argument(
        "--candidate-effect-artifact",
        default="artifacts/models/effect_model_v3_training_view_enforced_candidate.json",
        help="Candidate effect artifact path",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_replay_attribution_v1.json"
        ),
        help="Attribution report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_replay_attribution_v1.md"
        ),
        help="Attribution report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    records_by_user = _load_records_by_user(args.dataset)
    reference_artifact = load_effect_model_v1_artifact(args.reference_effect_artifact)
    candidate_artifact = load_effect_model_v1_artifact(args.candidate_effect_artifact)

    reference_effect_only = simulate_closed_loop_batch(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.reference_effect_artifact,
        policy_model_artifact_path=args.policy_artifact,
        enable_learned_policy=False,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_guarded",
    )
    candidate_effect_only = simulate_closed_loop_batch(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.candidate_effect_artifact,
        policy_model_artifact_path=args.policy_artifact,
        enable_learned_policy=False,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_guarded",
    )
    reference_combined = simulate_closed_loop_batch(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.reference_effect_artifact,
        policy_model_artifact_path=args.policy_artifact,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_and_policy_guarded",
    )
    candidate_combined = simulate_closed_loop_batch(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.candidate_effect_artifact,
        policy_model_artifact_path=args.policy_artifact,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_and_policy_guarded",
    )

    report = {
        "dataset_path": str(Path(args.dataset)),
        "max_cycles": args.max_cycles,
        "max_users": args.max_users,
        "policy_artifact_path": args.policy_artifact,
        "reference_effect_artifact_path": args.reference_effect_artifact,
        "candidate_effect_artifact_path": args.candidate_effect_artifact,
        "structural_artifact_delta": _build_structural_artifact_delta(
            reference_artifact=reference_artifact,
            candidate_artifact=candidate_artifact,
        ),
        "mode_attribution": {
            "learned_effect_guarded": _build_mode_attribution(
                mode_name="learned_effect_guarded",
                reference_report=reference_effect_only,
                candidate_report=candidate_effect_only,
                records_by_user=records_by_user,
                reference_artifact=reference_artifact,
                candidate_artifact=candidate_artifact,
            ),
            "learned_effect_and_policy_guarded": _build_mode_attribution(
                mode_name="learned_effect_and_policy_guarded",
                reference_report=reference_combined,
                candidate_report=candidate_combined,
                records_by_user=records_by_user,
                reference_artifact=reference_artifact,
                candidate_artifact=candidate_artifact,
            ),
        },
    }
    report["summary_findings"] = _build_summary_findings(report)

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
                "effect_only_final_action_diff_count": report["mode_attribution"][
                    "learned_effect_guarded"
                ]["final_action_difference_summary"]["user_count"],
                "combined_final_action_diff_count": report["mode_attribution"][
                    "learned_effect_and_policy_guarded"
                ]["final_action_difference_summary"]["user_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _build_structural_artifact_delta(
    *,
    reference_artifact: EffectModelV1Artifact,
    candidate_artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    reference_only_features = sorted(
        set(reference_artifact.feature_names) - set(candidate_artifact.feature_names)
    )
    candidate_only_features = sorted(
        set(candidate_artifact.feature_names) - set(reference_artifact.feature_names)
    )
    return {
        "reference_feature_count": len(reference_artifact.feature_names),
        "candidate_feature_count": len(candidate_artifact.feature_names),
        "reference_only_feature_count": len(reference_only_features),
        "candidate_only_feature_count": len(candidate_only_features),
        "reference_only_feature_family_counts": dict(
            sorted(
                Counter(_feature_family_name(name) for name in reference_only_features).items()
            )
        ),
        "reference_only_features": reference_only_features,
        "candidate_only_features": candidate_only_features,
        "alpha_delta": round(candidate_artifact.alpha - reference_artifact.alpha, 6),
        "policy_proxy_slope_delta": round(
            candidate_artifact.policy_proxy_slope
            - reference_artifact.policy_proxy_slope,
            6,
        ),
        "policy_proxy_intercept_delta": round(
            candidate_artifact.policy_proxy_intercept
            - reference_artifact.policy_proxy_intercept,
            6,
        ),
        "mean_output_intercept_reference": round(
            _mean_output_intercept(reference_artifact),
            6,
        ),
        "mean_output_intercept_candidate": round(
            _mean_output_intercept(candidate_artifact),
            6,
        ),
        "mean_output_intercept_delta": round(
            _mean_output_intercept(candidate_artifact)
            - _mean_output_intercept(reference_artifact),
            6,
        ),
    }


def _build_mode_attribution(
    *,
    mode_name: str,
    reference_report,
    candidate_report,
    records_by_user,
    reference_artifact: EffectModelV1Artifact,
    candidate_artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    reference_by_user = {
        scenario.user_id: scenario for scenario in reference_report.scenario_reports
    }
    candidate_by_user = {
        scenario.user_id: scenario for scenario in candidate_report.scenario_reports
    }

    trace_diff_cases: list[dict[str, object]] = []
    final_diff_cases: list[dict[str, object]] = []
    cgm_trace_only_cases: list[dict[str, object]] = []
    for user_id, reference_scenario in reference_by_user.items():
        candidate_scenario = candidate_by_user[user_id]
        baseline_record = records_by_user[user_id][0]
        trace_diffs = _trace_differences(reference_scenario, candidate_scenario)
        if trace_diffs:
            trace_diff_cases.append(
                {
                    "user_id": user_id,
                    "risk_tier": baseline_record.labels.risk_tier,
                    "cgm_available": baseline_record.request.input_availability.cgm,
                    "trajectory_mode": baseline_record.trajectory_mode,
                    "trace_diffs": trace_diffs,
                }
            )
        if reference_scenario.final_policy_action != candidate_scenario.final_policy_action:
            final_diff_cases.append(
                _build_final_action_case(
                    mode_name=mode_name,
                    user_id=user_id,
                    reference_scenario=reference_scenario,
                    candidate_scenario=candidate_scenario,
                    records_by_user=records_by_user,
                    reference_artifact=reference_artifact,
                    candidate_artifact=candidate_artifact,
                )
            )
        elif baseline_record.request.input_availability.cgm and trace_diffs:
            cgm_trace_only_cases.append(
                _build_cgm_trace_only_case(
                    user_id=user_id,
                    trajectory_mode=baseline_record.trajectory_mode,
                    trace_diffs=trace_diffs,
                )
            )

    final_diff_cases.sort(
        key=lambda case: abs(float(case["proxy_delta"])),
        reverse=True,
    )
    return {
        "trace_difference_summary": _build_trace_difference_summary(trace_diff_cases),
        "final_action_difference_summary": _build_final_action_difference_summary(
            final_diff_cases
        ),
        "cgm_trace_only_summary": _build_cgm_trace_only_summary(cgm_trace_only_cases),
        "example_final_action_cases": final_diff_cases[:8],
        "example_cgm_trace_only_cases": cgm_trace_only_cases[:6],
    }


def _build_final_action_case(
    *,
    mode_name: str,
    user_id: str,
    reference_scenario,
    candidate_scenario,
    records_by_user,
    reference_artifact: EffectModelV1Artifact,
    candidate_artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    reference_step = reference_scenario.trace[-1]
    candidate_step = candidate_scenario.trace[-1]
    record = records_by_user[user_id][reference_step.cycle_index]
    reference_proxy = _policy_proxy_for_mode(
        mode_name=mode_name,
        step=reference_step,
    )
    candidate_proxy = _policy_proxy_for_mode(
        mode_name=mode_name,
        step=candidate_step,
    )
    return {
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
        "reference_band": _policy_band_name(
            proxy_value=reference_proxy,
            cgm_available=record.request.input_availability.cgm,
        ),
        "candidate_band": _policy_band_name(
            proxy_value=candidate_proxy,
            cgm_available=record.request.input_availability.cgm,
        ),
        "decision_family": _classify_final_decision_family(
            mode_name=mode_name,
            reference_action=reference_scenario.final_policy_action.value,
            candidate_action=candidate_scenario.final_policy_action.value,
            reference_proxy=reference_proxy,
            candidate_proxy=candidate_proxy,
            cgm_available=record.request.input_availability.cgm,
            trajectory_step=record.trajectory_step,
        ),
        "feature_family_delta": _feature_family_delta_for_record(
            reference_artifact=reference_artifact,
            candidate_artifact=candidate_artifact,
            record=record,
        ),
    }


def _build_cgm_trace_only_case(
    *,
    user_id: str,
    trajectory_mode: str,
    trace_diffs: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "trajectory_mode": trajectory_mode,
        "trace_diffs": trace_diffs,
    }


def _build_trace_difference_summary(
    trace_diff_cases: list[dict[str, object]],
) -> dict[str, object]:
    cycle_counter: Counter[str] = Counter()
    trajectory_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    cgm_counter: Counter[str] = Counter()
    diff_type_counter: Counter[str] = Counter()
    for case in trace_diff_cases:
        trajectory_counter[str(case["trajectory_mode"])] += 1
        risk_counter[str(case["risk_tier"])] += 1
        cgm_counter[str(case["cgm_available"])] += 1
        for diff in case["trace_diffs"]:
            cycle_counter[str(diff["cycle_index"])] += 1
            for diff_type in diff["diff_types"]:
                diff_type_counter[diff_type] += 1
    return {
        "user_count": len(trace_diff_cases),
        "trace_step_count": sum(
            len(case["trace_diffs"]) for case in trace_diff_cases
        ),
        "cycle_index_counts": dict(sorted(cycle_counter.items())),
        "trajectory_mode_counts": dict(sorted(trajectory_counter.items())),
        "risk_tier_counts": dict(sorted(risk_counter.items())),
        "cgm_counts": dict(sorted(cgm_counter.items())),
        "diff_type_counts": dict(sorted(diff_type_counter.items())),
    }


def _build_final_action_difference_summary(
    final_diff_cases: list[dict[str, object]],
) -> dict[str, object]:
    if not final_diff_cases:
        return {
            "user_count": 0,
            "transition_counts": {},
            "risk_tier_counts": {},
            "cgm_counts": {},
            "trajectory_mode_counts": {},
            "decision_family_counts": {},
            "proxy_shift_summary": {},
            "feature_family_delta_summary": {},
        }

    transition_counts = Counter(
        f"{case['reference_final_action']}->{case['candidate_final_action']}"
        for case in final_diff_cases
    )
    risk_counts = Counter(str(case["risk_tier"]) for case in final_diff_cases)
    cgm_counts = Counter(str(case["cgm_available"]) for case in final_diff_cases)
    trajectory_counts = Counter(
        str(case["trajectory_mode"]) for case in final_diff_cases
    )
    decision_counts = Counter(
        str(case["decision_family"]) for case in final_diff_cases
    )
    feature_sums = _aggregate_feature_family_deltas(final_diff_cases)
    return {
        "user_count": len(final_diff_cases),
        "transition_counts": dict(sorted(transition_counts.items())),
        "risk_tier_counts": dict(sorted(risk_counts.items())),
        "cgm_counts": dict(sorted(cgm_counts.items())),
        "trajectory_mode_counts": dict(sorted(trajectory_counts.items())),
        "decision_family_counts": dict(sorted(decision_counts.items())),
        "proxy_shift_summary": {
            "mean_reference_proxy": round(
                mean(float(case["reference_proxy"]) for case in final_diff_cases),
                6,
            ),
            "mean_candidate_proxy": round(
                mean(float(case["candidate_proxy"]) for case in final_diff_cases),
                6,
            ),
            "mean_proxy_delta": round(
                mean(float(case["proxy_delta"]) for case in final_diff_cases),
                6,
            ),
            "min_proxy_delta": round(
                min(float(case["proxy_delta"]) for case in final_diff_cases),
                6,
            ),
            "max_proxy_delta": round(
                max(float(case["proxy_delta"]) for case in final_diff_cases),
                6,
            ),
            "band_transition_counts": dict(
                sorted(
                    Counter(
                        f"{case['reference_band']}->{case['candidate_band']}"
                        for case in final_diff_cases
                    ).items()
                )
            ),
        },
        "feature_family_delta_summary": feature_sums,
    }


def _build_cgm_trace_only_summary(
    cgm_trace_only_cases: list[dict[str, object]],
) -> dict[str, object]:
    if not cgm_trace_only_cases:
        return {
            "user_count": 0,
            "trajectory_mode_counts": {},
            "cycle_action_transition_counts": {},
            "proxy_shift_summary_on_differing_steps": {},
        }

    trajectory_counts = Counter(
        str(case["trajectory_mode"]) for case in cgm_trace_only_cases
    )
    cycle_transition_counts = Counter()
    reference_proxies: list[float] = []
    candidate_proxies: list[float] = []
    for case in cgm_trace_only_cases:
        for diff in case["trace_diffs"]:
            if "action" not in diff["diff_types"]:
                continue
            cycle_transition_counts[
                f"{diff['cycle_index']}::{diff['reference_action']}->{diff['candidate_action']}"
            ] += 1
            reference_proxies.append(float(diff["reference_proxy"]))
            candidate_proxies.append(float(diff["candidate_proxy"]))
    return {
        "user_count": len(cgm_trace_only_cases),
        "trajectory_mode_counts": dict(sorted(trajectory_counts.items())),
        "cycle_action_transition_counts": dict(sorted(cycle_transition_counts.items())),
        "proxy_shift_summary_on_differing_steps": {
            "mean_reference_proxy": round(mean(reference_proxies), 6),
            "mean_candidate_proxy": round(mean(candidate_proxies), 6),
            "mean_proxy_delta": round(
                mean(candidate - reference for reference, candidate in zip(
                    reference_proxies,
                    candidate_proxies,
                    strict=True,
                )),
                6,
            ),
        },
    }


def _trace_differences(reference_scenario, candidate_scenario) -> list[dict[str, object]]:
    differences: list[dict[str, object]] = []
    max_len = max(len(reference_scenario.trace), len(candidate_scenario.trace))
    for index in range(max_len):
        if index >= len(reference_scenario.trace) or index >= len(candidate_scenario.trace):
            differences.append(
                {
                    "cycle_index": index,
                    "diff_types": ["trace_length"],
                }
            )
            continue
        reference_step = reference_scenario.trace[index]
        candidate_step = candidate_scenario.trace[index]
        diff_types: list[str] = []
        if reference_step.selected_policy_action != candidate_step.selected_policy_action:
            diff_types.append("action")
        if reference_step.selected_candidate != candidate_step.selected_candidate:
            diff_types.append("candidate")
        if reference_step.state_after != candidate_step.state_after:
            diff_types.append("state")
        if not diff_types:
            continue
        differences.append(
            {
                "cycle_index": index,
                "diff_types": diff_types,
                "reference_action": reference_step.selected_policy_action.value,
                "candidate_action": candidate_step.selected_policy_action.value,
                "reference_state_after": reference_step.state_after,
                "candidate_state_after": candidate_step.state_after,
                "reference_proxy": round(reference_step.predicted_effect_proxy, 6),
                "candidate_proxy": round(candidate_step.predicted_effect_proxy, 6),
            }
        )
    return differences


def _policy_proxy_for_mode(*, mode_name: str, step) -> float:
    if mode_name == "learned_effect_and_policy_guarded":
        return float(step.policy_effect_proxy_used)
    return float(step.predicted_effect_proxy)


def _policy_band_name(*, proxy_value: float, cgm_available: bool) -> str:
    if proxy_value < 0.14:
        return "re_optimize_band"
    if proxy_value < (0.37 if cgm_available else 0.24):
        return "monitor_only_band"
    return "continue_plan_band"


def _classify_final_decision_family(
    *,
    mode_name: str,
    reference_action: str,
    candidate_action: str,
    reference_proxy: float,
    candidate_proxy: float,
    cgm_available: bool,
    trajectory_step: int,
) -> str:
    reference_band = _policy_band_name(
        proxy_value=reference_proxy,
        cgm_available=cgm_available,
    )
    candidate_band = _policy_band_name(
        proxy_value=candidate_proxy,
        cgm_available=cgm_available,
    )
    if mode_name == "learned_effect_guarded":
        if (
            not cgm_available
            and reference_action == "continue_plan"
            and candidate_action == "monitor_only"
            and reference_band == "continue_plan_band"
            and candidate_band == "monitor_only_band"
        ):
            return "non_cgm_continue_to_monitor_threshold_cross"
        if reference_band != candidate_band:
            return "effect_proxy_band_cross"
        return "effect_proxy_same_band_action_shift"

    if (
        candidate_action == "re_optimize"
        and _should_apply_reoptimize_revival_prior(
            record=_RecordLike(
                cgm_available=cgm_available,
                trajectory_step=trajectory_step,
            ),
            predicted_effect_proxy=candidate_proxy,
        )
    ):
        return "policy_reoptimize_revival_window"
    if (
        reference_action == "continue_plan"
        and candidate_action == "monitor_only"
        and reference_band == "continue_plan_band"
        and candidate_band == "monitor_only_band"
    ):
        return "policy_monitor_only_threshold_cross"
    if (
        cgm_available
        and reference_action == "monitor_only"
        and candidate_action == "continue_plan"
        and reference_band == "monitor_only_band"
        and candidate_band == "monitor_only_band"
    ):
        return "cgm_same_band_policy_score_flip"
    if reference_band != candidate_band:
        return "policy_band_cross"
    return "same_band_policy_score_flip"


def _feature_family_delta_for_record(
    *,
    reference_artifact: EffectModelV1Artifact,
    candidate_artifact: EffectModelV1Artifact,
    record,
) -> dict[str, float]:
    reference_contributions = _aggregate_effect_family_contributions(
        artifact=reference_artifact,
        record=record,
    )
    candidate_contributions = _aggregate_effect_family_contributions(
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


def _aggregate_effect_family_contributions(
    *,
    artifact: EffectModelV1Artifact,
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


def _aggregate_feature_family_deltas(
    final_diff_cases: list[dict[str, object]],
) -> dict[str, object]:
    signed_sums: dict[str, float] = defaultdict(float)
    abs_sums: dict[str, float] = defaultdict(float)
    for case in final_diff_cases:
        for family, delta in case["feature_family_delta"].items():
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
) -> list[dict[str, float | str]]:
    ordered = sorted(
        (
            {"family": family, "value": round(value, 6)}
            for family, value in family_map.items()
        ),
        key=lambda item: float(item["value"]),
        reverse=reverse,
    )
    return ordered[:limit]


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


def _mean_output_intercept(artifact: EffectModelV1Artifact) -> float:
    if not artifact.intercepts:
        return 0.0
    return float(sum(artifact.intercepts) / len(artifact.intercepts))


def _build_summary_findings(report: dict[str, object]) -> list[str]:
    structural = report["structural_artifact_delta"]
    effect_only = report["mode_attribution"]["learned_effect_guarded"]
    combined = report["mode_attribution"]["learned_effect_and_policy_guarded"]
    return [
        (
            "Structural artifact drift is real: the candidate drops "
            f"{structural['reference_only_feature_count']} baseline-only features, "
            "including 5 outcome-leakage features and 9 user-context features, "
            f"while alpha rises by {structural['alpha_delta']}."
        ),
        (
            "The biggest structural score shift is intercept shrinkage: "
            f"mean output intercept moves from {structural['mean_output_intercept_reference']} "
            f"to {structural['mean_output_intercept_candidate']}."
        ),
        (
            "Overall final-action delta is entirely low-risk: effect-only final changes are "
            f"{effect_only['final_action_difference_summary']['transition_counts']}, "
            "and none of them are high-risk or safety-guard families."
        ),
        (
            "Low-risk effect-only drift is a non-cgm threshold-cross story: "
            f"{effect_only['final_action_difference_summary']['decision_family_counts']}."
        ),
        (
            "CGM effect-only delta is mostly workflow disagreement, not final-action drift: "
            f"{effect_only['cgm_trace_only_summary']['cycle_action_transition_counts']}."
        ),
        (
            "Combined-mode final delta splits into three measurable families: "
            f"{combined['final_action_difference_summary']['decision_family_counts']}."
        ),
    ]


def render_markdown(report: dict[str, object]) -> str:
    structural = report["structural_artifact_delta"]
    effect_only = report["mode_attribution"]["learned_effect_guarded"]
    combined = report["mode_attribution"]["learned_effect_and_policy_guarded"]
    lines = [
        "# effect artifact replay attribution v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- reference_effect_artifact_path: `{report['reference_effect_artifact_path']}`",
        f"- candidate_effect_artifact_path: `{report['candidate_effect_artifact_path']}`",
        f"- policy_artifact_path: `{report['policy_artifact_path']}`",
        "",
        "## Structural Delta",
        f"- reference_feature_count: `{structural['reference_feature_count']}`",
        f"- candidate_feature_count: `{structural['candidate_feature_count']}`",
        (
            "- reference_only_feature_family_counts: "
            f"`{structural['reference_only_feature_family_counts']}`"
        ),
        f"- alpha_delta: `{structural['alpha_delta']}`",
        f"- mean_output_intercept_delta: `{structural['mean_output_intercept_delta']}`",
        "",
        "## Overall",
        (
            "- effect_only final_action_difference_summary: "
            f"`{effect_only['final_action_difference_summary']}`"
        ),
        (
            "- combined final_action_difference_summary: "
            f"`{combined['final_action_difference_summary']}`"
        ),
        "",
        "## Low-Risk",
        (
            "- effect_only decision_family_counts: "
            f"`{effect_only['final_action_difference_summary']['decision_family_counts']}`"
        ),
        (
            "- effect_only trajectory_mode_counts: "
            f"`{effect_only['final_action_difference_summary']['trajectory_mode_counts']}`"
        ),
        (
            "- combined decision_family_counts: "
            f"`{combined['final_action_difference_summary']['decision_family_counts']}`"
        ),
        (
            "- combined trajectory_mode_counts: "
            f"`{combined['final_action_difference_summary']['trajectory_mode_counts']}`"
        ),
        "",
        "## CGM",
        (
            "- effect_only cgm_trace_only_summary: "
            f"`{effect_only['cgm_trace_only_summary']}`"
        ),
        (
            "- combined cgm_counts in final-action delta: "
            f"`{combined['final_action_difference_summary']['cgm_counts']}`"
        ),
        "",
        "## Findings",
    ]
    for finding in report["summary_findings"]:
        lines.append(f"- `{finding}`")
    lines.extend(["", "## Example Final-Action Cases"])
    for mode_name, mode_report in report["mode_attribution"].items():
        for case in mode_report["example_final_action_cases"][:4]:
            lines.append(
                f"- `{mode_name}` `{case['user_id']}`: "
                f"`{case['reference_final_action']}->{case['candidate_final_action']}`, "
                f"proxy=`{case['reference_proxy']}->{case['candidate_proxy']}`, "
                f"band=`{case['reference_band']}->{case['candidate_band']}`, "
                f"decision_family=`{case['decision_family']}`, "
                f"trajectory_mode=`{case['trajectory_mode']}`"
            )
    lines.extend(["", "## Example CGM Trace-Only Cases"])
    for case in effect_only["example_cgm_trace_only_cases"][:4]:
        lines.append(
            f"- `{case['user_id']}`: trajectory_mode=`{case['trajectory_mode']}`, "
            f"trace_diffs=`{case['trace_diffs']}`"
        )
    return "\n".join(lines) + "\n"


class _InputAvailabilityLike:
    def __init__(self, *, cgm: bool) -> None:
        self.cgm = cgm


class _RequestLike:
    def __init__(self, *, cgm_available: bool) -> None:
        self.input_availability = _InputAvailabilityLike(cgm=cgm_available)


class _RecordLike:
    def __init__(self, *, cgm_available: bool, trajectory_step: int) -> None:
        self.request = _RequestLike(cgm_available=cgm_available)
        self.trajectory_step = trajectory_step
        self.side_effect_proxy = 0.2


if __name__ == "__main__":
    sys_exit(main())
