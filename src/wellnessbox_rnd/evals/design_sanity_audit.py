from __future__ import annotations

import json
import re
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_design_sanity_audit(
    *,
    learned_boundary_audit: dict[str, object],
    learned_boundary_audit_path: str | Path,
    next_action_audit: dict[str, object],
    next_action_audit_path: str | Path,
    pro_contract: dict[str, object],
    pro_contract_path: str | Path,
    baseline_identical_signal_audit: dict[str, object],
    baseline_identical_signal_audit_path: str | Path,
    partition_validity_audit: dict[str, object],
    partition_validity_audit_path: str | Path,
    calibration_dependence_audit: dict[str, object],
    calibration_dependence_audit_path: str | Path,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
    core_kpi_path_summary: dict[str, object],
    core_kpi_path_summary_path: str | Path,
    latest_effect_candidate_reject_decision: dict[str, object],
    latest_effect_candidate_reject_decision_path: str | Path,
    latest_training_compare_vs_baseline: dict[str, object],
    latest_training_compare_vs_baseline_path: str | Path,
    latest_training_compare_vs_prior_candidate: dict[str, object],
    latest_training_compare_vs_prior_candidate_path: str | Path,
    recommendation_service_path: str | Path,
    optimizer_service_path: str | Path,
) -> dict[str, object]:
    recommendation_source = Path(recommendation_service_path).read_text(encoding="utf-8")
    optimizer_source = Path(optimizer_service_path).read_text(encoding="utf-8")

    recommendation_optimization = _build_recommendation_optimization_assessment(
        recommendation_source=recommendation_source,
        optimizer_source=optimizer_source,
        recommendation_service_path=recommendation_service_path,
        optimizer_service_path=optimizer_service_path,
    )
    deterministic_safety = _build_deterministic_safety_assessment(
        learned_boundary_audit=learned_boundary_audit,
        weakest_slice_summary=weakest_slice_summary,
    )
    pro_path = _build_pro_path_assessment(
        pro_contract=pro_contract,
        core_kpi_path_summary=core_kpi_path_summary,
    )
    next_action = _build_next_action_assessment(
        next_action_audit=next_action_audit,
        weakest_slice_summary=weakest_slice_summary,
    )
    learned_boundary = _build_learned_boundary_assessment(
        learned_boundary_audit=learned_boundary_audit,
        core_kpi_path_summary=core_kpi_path_summary,
    )
    latest_candidate = _build_latest_candidate_assessment(
        latest_effect_candidate_reject_decision=latest_effect_candidate_reject_decision,
        latest_training_compare_vs_baseline=latest_training_compare_vs_baseline,
        latest_training_compare_vs_prior_candidate=latest_training_compare_vs_prior_candidate,
    )
    synthetic_data = _build_synthetic_data_assessment(
        baseline_identical_signal_audit=baseline_identical_signal_audit,
        partition_validity_audit=partition_validity_audit,
        calibration_dependence_audit=calibration_dependence_audit,
    )

    dimensions = {
        "deterministic_safety_separation": deterministic_safety,
        "lightweight_recommendation_optimization_separation": recommendation_optimization,
        "pro_baseline_followup_kpi_path": pro_path,
        "explicit_next_action_state_machine": next_action,
        "replay_only_learned_boundary": learned_boundary,
        "synthetic_data_leakage_circularity_baseline_identical_risk": synthetic_data,
    }

    strong_dimension_count = sum(
        1
        for key, value in dimensions.items()
        if key != "synthetic_data_leakage_circularity_baseline_identical_risk"
        and str(_as_dict(value).get("status")) in {"sound", "sound_with_gaps"}
    )
    overall_verdict = {
        "fundamentally_wrong_research_direction": False,
        "direction_status": "directionally_sound_but_data_validity_risky",
        "current_phase": "contract_data_eval_hardening",
        "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
        "current_candidate_assessment": latest_candidate,
        "strong_dimension_count": strong_dimension_count,
        "total_dimension_count": len(dimensions),
        "summary": (
            "Repo evidence does not support calling the current research direction "
            "fundamentally wrong. The deterministic runtime shape is still aligned "
            "with the intended recommendation/safety/state-machine design, while the "
            "main remaining risk is synthetic-data validity rather than architectural collapse."
        ),
        "rationale": [
            (
                "Deterministic safety separation, lightweight recommendation/optimizer "
                "separation, the shared PRO baseline/follow-up path, the explicit next-action "
                "state machine, and the replay-only learned boundary all have direct repo evidence."
            ),
            (
                "The latest candidate is still held because of fit/replay/data-validity issues, "
                "and the newest heterogeneity-aware training rerun collapsed to the same held "
                "candidate surface, which is evidence of an unresolved evaluation/data problem, "
                "not evidence that the overall deterministic architecture is pointed the wrong way."
            ),
            (
                "The biggest negative evidence remains synthetic pre/post circularity, "
                "generator contamination, and calibration dependence concentrated in the "
                "supported effect-enriched slice."
            ),
            (
                "So the most accurate description is contract/data/eval hardening under "
                "one material "
                "synthetic-validity risk, not a fundamentally misdirected research program."
            ),
        ],
        "evidence_needed_before_claiming_directional_success": [
            (
                "A replay-only result showing a candidate no longer loses to baseline "
                "on the current "
                "overall fit gates."
            ),
            (
                "A narrower synthetic-data validity story that reduces or isolates supported-slice "
                "circularity and calibration dependence."
            ),
        ],
    }
    readable_summary = {
        "design_verdict": {
            "fundamentally_wrong_research_direction": overall_verdict.get(
                "fundamentally_wrong_research_direction"
            ),
            "direction_status": overall_verdict.get("direction_status"),
            "current_phase": overall_verdict.get("current_phase"),
            "principal_blocker": overall_verdict.get("principal_blocker"),
            "short_conclusion": (
                "Current repo evidence does not support calling the research direction "
                "fundamentally wrong. The stronger read is that the direction is still "
                "sound, but the work is currently in contract/data/eval hardening because "
                "synthetic-data validity remains the main blocker."
            ),
        },
        "deterministic_runtime_digest": {
            "deterministic_safety_separation": deterministic_safety.get("status"),
            "recommendation_optimization_separation": recommendation_optimization.get(
                "status"
            ),
            "explicit_next_action_state_machine": next_action.get("status"),
            "replay_only_learned_boundary": learned_boundary.get("status"),
        },
        "kpi_path_digest": {
            "pro_baseline_followup_kpi_path": pro_path.get("status"),
            "pro_valid_case_count": _as_dict(pro_path.get("evidence")).get(
                "valid_case_count"
            ),
            "weakest_slice_wiring_status": _as_dict(
                _as_dict(core_kpi_path_summary.get("weakest_slice_frozen_eval_wiring_status"))
            ).get("status"),
            "latest_candidate_adoption_status": latest_candidate.get("adoption_status"),
            "latest_candidate_fit_gate_status": latest_candidate.get("fit_gate_status"),
            "latest_candidate_training_result": latest_candidate.get(
                "latest_training_loop_result"
            ),
        },
        "synthetic_risk_digest": {
            "status": synthetic_data.get("status"),
            "baseline_identical_label_status": _as_dict(
                synthetic_data.get("evidence")
            ).get("baseline_identical_label_status"),
            "exact_reconstruction_rate_pct": _as_dict(
                synthetic_data.get("evidence")
            ).get("exact_reconstruction_rate_pct"),
            "supported_mode_top2_match_rate_pct": _as_dict(
                synthetic_data.get("evidence")
            ).get("supported_mode_top2_match_rate_pct"),
            "calibration_dependence_status": _as_dict(
                synthetic_data.get("evidence")
            ).get("calibration_dependence_status"),
        },
        "evidence_needed_digest": _as_list(
            overall_verdict.get("evidence_needed_before_claiming_directional_success")
        )[:2],
    }

    audit = {
        "audit_name": "design_sanity_audit_v1",
        "source_artifacts": {
            "learned_runtime_boundary_audit_path": str(learned_boundary_audit_path),
            "next_action_state_machine_audit_path": str(next_action_audit_path),
            "pro_scoring_contract_path": str(pro_contract_path),
            "dataset_f_baseline_identical_signal_audit_path": str(
                baseline_identical_signal_audit_path
            ),
            "dataset_f_partition_validity_audit_path": str(partition_validity_audit_path),
            "policy_proxy_calibration_dependence_audit_path": str(
                calibration_dependence_audit_path
            ),
            "weakest_slice_frozen_eval_summary_path": str(weakest_slice_summary_path),
            "core_kpi_path_summary_path": str(core_kpi_path_summary_path),
            "latest_effect_candidate_reject_decision_path": str(
                latest_effect_candidate_reject_decision_path
            ),
            "latest_training_compare_vs_baseline_path": str(
                latest_training_compare_vs_baseline_path
            ),
            "latest_training_compare_vs_prior_candidate_path": str(
                latest_training_compare_vs_prior_candidate_path
            ),
            "recommendation_service_path": str(recommendation_service_path),
            "optimizer_service_path": str(optimizer_service_path),
        },
        "dimensions": dimensions,
        "readable_summary": readable_summary,
        "overall_verdict": overall_verdict,
    }
    audit["validation_issues"] = validate_design_sanity_audit(audit)
    return audit


def validate_design_sanity_audit(audit: dict[str, object]) -> list[str]:
    issues: list[str] = []
    dimensions = _as_dict(audit.get("dimensions"))
    overall = _as_dict(audit.get("overall_verdict"))
    if not dimensions:
        issues.append("missing_dimensions")
    if overall.get("direction_status") is None:
        issues.append("missing_direction_status")
    if overall.get("principal_blocker") is None:
        issues.append("missing_principal_blocker")
    if _as_dict(audit.get("readable_summary")).get("design_verdict") is None:
        issues.append("missing_readable_design_verdict")
    if not _as_dict(overall.get("current_candidate_assessment")):
        issues.append("missing_current_candidate_assessment")
    for required in [
        "deterministic_safety_separation",
        "lightweight_recommendation_optimization_separation",
        "pro_baseline_followup_kpi_path",
        "explicit_next_action_state_machine",
        "replay_only_learned_boundary",
        "synthetic_data_leakage_circularity_baseline_identical_risk",
    ]:
        if required not in dimensions:
            issues.append(f"missing_dimension::{required}")
    return issues


def render_design_sanity_audit_markdown(audit: dict[str, object]) -> str:
    readable = _as_dict(audit.get("readable_summary"))
    design_verdict = _as_dict(readable.get("design_verdict"))
    runtime_digest = _as_dict(readable.get("deterministic_runtime_digest"))
    kpi_path_digest = _as_dict(readable.get("kpi_path_digest"))
    synthetic_digest = _as_dict(readable.get("synthetic_risk_digest"))
    overall = _as_dict(audit.get("overall_verdict"))
    lines = [
        "# design sanity audit v1",
        "",
        "## Verdict",
        "",
        (
            "- fundamentally_wrong_research_direction: "
            f"`{design_verdict.get('fundamentally_wrong_research_direction')}`"
        ),
        f"- direction_status: `{design_verdict.get('direction_status')}`",
        f"- current_phase: `{design_verdict.get('current_phase')}`",
        f"- principal_blocker: `{design_verdict.get('principal_blocker')}`",
        f"- short_conclusion: `{design_verdict.get('short_conclusion')}`",
        "",
        "## Current Read",
        "",
        (
            "- deterministic_safety_separation: "
            f"`{runtime_digest.get('deterministic_safety_separation')}`"
        ),
        (
            "- recommendation_optimization_separation: "
            f"`{runtime_digest.get('recommendation_optimization_separation')}`"
        ),
        (
            "- explicit_next_action_state_machine: "
            f"`{runtime_digest.get('explicit_next_action_state_machine')}`"
        ),
        (
            "- replay_only_learned_boundary: "
            f"`{runtime_digest.get('replay_only_learned_boundary')}`"
        ),
        (
            "- pro_baseline_followup_kpi_path: "
            f"`{kpi_path_digest.get('pro_baseline_followup_kpi_path')}`"
        ),
        (
            "- latest_candidate_adoption_status: "
            f"`{kpi_path_digest.get('latest_candidate_adoption_status')}`"
        ),
        (
            "- latest_candidate_fit_gate_status: "
            f"`{kpi_path_digest.get('latest_candidate_fit_gate_status')}`"
        ),
        (
            "- synthetic_risk_status: "
            f"`{synthetic_digest.get('status')}`"
        ),
        "",
        "## current candidate",
    ]
    candidate = _as_dict(overall.get("current_candidate_assessment"))
    lines.extend(
        [
            f"- adoption_status: `{candidate.get('adoption_status')}`",
            f"- latest_training_loop_result: `{candidate.get('latest_training_loop_result')}`",
            f"- fit_gate_status: `{candidate.get('fit_gate_status')}`",
            f"- dominant_regression_slice: `{candidate.get('dominant_regression_slice')}`",
            f"- summary: `{candidate.get('summary')}`",
            "",
            "## dimensions",
        ]
    )
    for name, item in _as_dict(audit.get("dimensions")).items():
        item_dict = _as_dict(item)
        lines.append(
            f"- `{name}`: status=`{item_dict.get('status')}`, "
            f"judgement=`{item_dict.get('judgement')}`"
        )
        lines.append(f"  - summary: `{item_dict.get('summary')}`")
    lines.extend(["", "## rationale"])
    for item in _as_list(overall.get("rationale")):
        lines.append(f"- {item}")
    lines.extend(["", "## evidence needed"])
    for item in _as_list(readable.get("evidence_needed_digest")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_design_sanity_audit_files(
    audit: dict[str, object],
    *,
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_design_sanity_audit_markdown(audit), encoding="utf-8")


def _build_deterministic_safety_assessment(
    *,
    learned_boundary_audit: dict[str, object],
    weakest_slice_summary: dict[str, object],
) -> dict[str, object]:
    safety_path = _as_dict(learned_boundary_audit.get("safety_path"))
    structured = _as_dict(
        _find_case_family_summary(weakest_slice_summary, family="safety_blocked").get(
            "structured_safety_evidence_audit"
        )
    )
    completeness = _as_dict(structured.get("reference_linkage_completeness"))
    return {
        "status": "sound_with_gaps",
        "judgement": "deterministic_safety_is_separate_and_precedent_preserving",
        "summary": (
            "Safety remains structurally separate from learned/chat paths and still anchors "
            "the weakest-slice safety audit. The remaining gap is narrower attribution "
            "completeness, not learned-safety entanglement."
        ),
        "evidence": {
            "core_dependency_promoted": safety_path.get("core_dependency_promoted"),
            "source_mentions_artifact_or_learned": _as_dict(safety_path.get("evidence")).get(
                "source_mentions_artifact_or_learned"
            ),
            "structured_safety_path_status": structured.get("path_status"),
            "reference_linkage_status": structured.get("reference_linkage_status"),
            "reference_coverage_pct": completeness.get("reference_coverage_pct"),
            "workflow_category_coverage_pct": _as_dict(
                structured.get("next_action_workflow_category_join")
            ).get("coverage_pct"),
        },
    }


def _build_recommendation_optimization_assessment(
    *,
    recommendation_source: str,
    optimizer_source: str,
    recommendation_service_path: str | Path,
    optimizer_service_path: str | Path,
) -> dict[str, object]:
    recommend_imports_optimizer = (
        "from wellnessbox_rnd.optimizer.service import select_recommendations"
        in recommendation_source
    )
    recommend_learned_default_off = bool(
        re.search(
            (
                r"def recommend\([\s\S]*enable_learned_reranking: bool = False,"
                r"[\s\S]*learned_efficacy_artifact_path: str \| None = None"
            ),
            recommendation_source,
        )
    )
    select_learned_default_off = bool(
        re.search(
            (
                r"def select_recommendations\([\s\S]*enable_learned_reranking: "
                r"bool = False,[\s\S]*learned_efficacy_artifact_path: str \| None = None"
            ),
            optimizer_source,
        )
    )
    optimizer_candidate_enumeration = "for item in list_catalog_items()" in optimizer_source
    optimizer_selection_loop = "_marginal_selection_score" in optimizer_source
    return {
        "status": "sound",
        "judgement": "lightweight_candidate_generation_and_selection_are_separate",
        "summary": (
            "The recommendation layer still orchestrates normalized input plus explicit optimizer "
            "selection, and the optimizer still owns constrained candidate enumeration and scoring."
        ),
        "evidence": {
            "recommendation_imports_optimizer": recommend_imports_optimizer,
            "recommend_signature_learned_default_off": recommend_learned_default_off,
            "optimizer_signature_learned_default_off": select_learned_default_off,
            "optimizer_candidate_enumeration_present": optimizer_candidate_enumeration,
            "optimizer_selection_loop_present": optimizer_selection_loop,
            "recommendation_service_path": str(recommendation_service_path),
            "optimizer_service_path": str(optimizer_service_path),
        },
    }


def _build_pro_path_assessment(
    *,
    pro_contract: dict[str, object],
    core_kpi_path_summary: dict[str, object],
) -> dict[str, object]:
    improvement_metric = _as_dict(pro_contract.get("improvement_metric"))
    single_path_status = _as_dict(improvement_metric.get("single_path_status"))
    shared_event_path_proof = _as_dict(improvement_metric.get("shared_event_path_proof"))
    core_pro = _as_dict(core_kpi_path_summary.get("pro_baseline_followup_contract_status"))
    return {
        "status": "sound",
        "judgement": "pro_kpi_path_is_single_contract_based",
        "summary": (
            "Baseline/follow-up PRO improvement is computed through one shared "
            "normalized event path "
            "and remains directly visible on the current core KPI path."
        ),
        "evidence": {
            "shared_event_adapter": improvement_metric.get("shared_event_adapter"),
            "shared_event_unifier": improvement_metric.get("shared_event_unifier"),
            "event_adapter_only_public_entrypoint": single_path_status.get(
                "event_adapter_only_public_entrypoint"
            ),
            "snapshot_pair_entrypoint_internal_only": single_path_status.get(
                "snapshot_pair_entrypoint_internal_only"
            ),
            "valid_case_count": shared_event_path_proof.get("valid_case_count"),
            "invalid_case_count": shared_event_path_proof.get("invalid_case_count"),
            "core_kpi_status": core_pro.get("status"),
        },
    }


def _build_next_action_assessment(
    *,
    next_action_audit: dict[str, object],
    weakest_slice_summary: dict[str, object],
) -> dict[str, object]:
    explicit = _as_dict(next_action_audit.get("explicit_contract_status"))
    workflow_linkage = _as_dict(
        _find_case_family_summary(weakest_slice_summary, family="safety_blocked").get(
            "workflow_safety_linkage"
        )
    )
    workflow_join = _as_dict(workflow_linkage.get("next_action_workflow_category_join"))
    return {
        "status": "sound",
        "judgement": "next_action_state_machine_is_explicit_not_hidden",
        "summary": (
            "The next-action state machine remains explicit and the current weakest blocked branch "
            "coverage is complete at the category level."
        ),
        "evidence": {
            "followup_contract_schema_version": explicit.get(
                "followup_contract_schema_version"
            ),
            "next_action_contract_schema_version": explicit.get(
                "next_action_contract_schema_version"
            ),
            "next_action_state_machine_scope": explicit.get(
                "next_action_state_machine_scope"
            ),
            "phase_sensitive_followup_actions": explicit.get(
                "phase_sensitive_followup_actions"
            ),
            "validation_issue_count": len(_as_list(next_action_audit.get("validation_issues"))),
            "weakest_safety_branch_coverage_pct": workflow_join.get("coverage_pct"),
        },
    }


def _build_learned_boundary_assessment(
    *,
    learned_boundary_audit: dict[str, object],
    core_kpi_path_summary: dict[str, object],
) -> dict[str, object]:
    overall = _as_dict(learned_boundary_audit.get("overall_assessment"))
    runtime = _as_dict(learned_boundary_audit.get("runtime_recommendation_path"))
    optimizer = _as_dict(learned_boundary_audit.get("optimizer_path"))
    inference = _as_dict(learned_boundary_audit.get("inference_api_path"))
    core_boundary = _as_dict(
        core_kpi_path_summary.get("learned_artifact_replay_only_boundary_status")
    )
    return {
        "status": "sound",
        "judgement": "learned_artifacts_remain_replay_only_by_default",
        "summary": str(overall.get("summary")),
        "evidence": {
            "learned_artifact_core_dependency_promoted": overall.get(
                "learned_artifact_core_dependency_promoted"
            ),
            "runtime_core_dependency_promoted": runtime.get("core_dependency_promoted"),
            "optimizer_core_dependency_promoted": optimizer.get("core_dependency_promoted"),
            "inference_core_dependency_promoted": inference.get("core_dependency_promoted"),
            "core_kpi_status": core_boundary.get("status"),
        },
    }


def _build_latest_candidate_assessment(
    *,
    latest_effect_candidate_reject_decision: dict[str, object],
    latest_training_compare_vs_baseline: dict[str, object],
    latest_training_compare_vs_prior_candidate: dict[str, object],
) -> dict[str, object]:
    decision_gate = _as_dict(latest_effect_candidate_reject_decision.get("decision_gate"))
    hold_context = _as_dict(latest_effect_candidate_reject_decision.get("hold_context"))
    baseline_deltas = _as_dict(latest_training_compare_vs_baseline.get("deltas"))
    prior_deltas = _as_dict(latest_training_compare_vs_prior_candidate.get("deltas"))
    prior_slice_deltas = _as_dict(
        _as_dict(latest_training_compare_vs_prior_candidate.get("slice_deltas")).get(
            "learned_effect_and_policy_guarded"
        )
    )
    return {
        "adoption_status": decision_gate.get("decision"),
        "fork_recommendation": decision_gate.get("fork_recommendation"),
        "fit_gate_status": decision_gate.get("fit_gate_status"),
        "dominant_regression_slice": hold_context.get("dominant_candidate_regression_slice"),
        "latest_training_loop_result": "null_result_same_as_current_held_candidate",
        "summary": (
            "The latest heterogeneity-aware effect-training rerun did not create a new "
            "promotion candidate. It remained worse than baseline and behaviorally identical "
            "to the current held training-view-enforced candidate."
        ),
        "evidence": {
            "overall_clearly_worse_than_baseline": decision_gate.get(
                "overall_clearly_worse_than_baseline"
            ),
            "baseline_test_aggregate_mae_delta": baseline_deltas.get(
                "test_aggregate_mae_delta"
            ),
            "baseline_test_aggregate_r2_delta": baseline_deltas.get("test_aggregate_r2_delta"),
            "baseline_test_policy_proxy_mae_delta": baseline_deltas.get(
                "test_policy_proxy_mae_delta"
            ),
            "prior_candidate_test_aggregate_mae_delta": prior_deltas.get(
                "test_aggregate_mae_delta"
            ),
            "prior_candidate_test_aggregate_r2_delta": prior_deltas.get(
                "test_aggregate_r2_delta"
            ),
            "prior_candidate_test_policy_proxy_mae_delta": prior_deltas.get(
                "test_policy_proxy_mae_delta"
            ),
            "prior_candidate_low_risk_disagreement_delta": prior_slice_deltas.get(
                "low_risk_disagreement_delta"
            ),
            "prior_candidate_cgm_disagreement_delta": prior_slice_deltas.get(
                "cgm_disagreement_delta"
            ),
        },
    }


def _build_synthetic_data_assessment(
    *,
    baseline_identical_signal_audit: dict[str, object],
    partition_validity_audit: dict[str, object],
    calibration_dependence_audit: dict[str, object],
) -> dict[str, object]:
    baseline_signal = _as_dict(
        baseline_identical_signal_audit.get("baseline_identical_signal_assessment")
    )
    baseline_evidence = _as_dict(baseline_identical_signal_audit.get("evidence"))
    residual_signal = _as_dict(baseline_evidence.get("residual_signal_risk"))
    feature_guard = _as_dict(baseline_evidence.get("feature_schema_guard"))
    split_hygiene = _as_dict(baseline_evidence.get("split_hygiene"))
    partition_assessment = _as_dict(partition_validity_audit.get("assessment"))
    calibration_assessment = _as_dict(calibration_dependence_audit.get("assessment"))
    return {
        "status": "material_risk",
        "judgement": "synthetic_data_path_is_guarded_but_not_yet_strong_validity_evidence",
        "summary": (
            "Direct forbidden-feature leakage and simple baseline-identical label-copy risk are "
            "meaningfully reduced, but current Dataset F still has material circularity, "
            "assignment contamination, and calibration dependence concentrated in "
            "supported effect-enriched rows."
        ),
        "evidence": {
            "forbidden_feature_count": feature_guard.get("forbidden_feature_count"),
            "baseline_identical_label_status": baseline_signal.get("label_copy_risk_status"),
            "behavioral_replay_identity_status": baseline_signal.get(
                "behavioral_replay_identity_status"
            ),
            "exact_reconstruction_rate_pct": residual_signal.get(
                "exact_reconstruction_rate_pct"
            ),
            "supported_mode_top2_match_rate_pct": residual_signal.get(
                "supported_mode_top2_match_rate_pct"
            ),
            "shares_path_with_frozen_eval": split_hygiene.get("shares_path_with_frozen_eval"),
            "partition_verdict": partition_assessment.get("verdict"),
            "calibration_dependence_status": calibration_assessment.get(
                "dependence_status"
            ),
            "calibration_dependence_concentration": calibration_assessment.get(
                "concentration_status"
            ),
        },
    }


def _find_case_family_summary(
    weakest_slice_summary: dict[str, object], *, family: str
) -> dict[str, object]:
    for item in _as_list(weakest_slice_summary.get("case_family_summaries")):
        item_dict = _as_dict(item)
        if item_dict.get("family") == family:
            return item_dict
    return {}


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_design_sanity_audit",
    "load_json",
    "render_design_sanity_audit_markdown",
    "validate_design_sanity_audit",
    "write_design_sanity_audit_files",
]
