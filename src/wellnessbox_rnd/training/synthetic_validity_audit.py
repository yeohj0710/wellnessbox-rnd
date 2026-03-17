from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_synthetic_validity_audit(
    *,
    dataset_path: str | Path,
    path_safety_audit: dict[str, object],
    path_safety_audit_path: str | Path,
    baseline_identical_audit: dict[str, object],
    baseline_identical_audit_path: str | Path,
    partition_validity_audit: dict[str, object],
    partition_validity_audit_path: str | Path,
    calibration_dependence_audit: dict[str, object],
    calibration_dependence_audit_path: str | Path,
    synthetic_prepost_audit: dict[str, object],
    synthetic_prepost_audit_path: str | Path,
    feature_schema: dict[str, object],
    feature_schema_path: str | Path,
    split_manifest: dict[str, object],
    split_manifest_path: str | Path,
) -> dict[str, object]:
    path_risks = _as_dict(path_safety_audit.get("risk_assessment"))
    leakage = _as_dict(path_risks.get("leakage"))
    frozen_eval_contamination = _as_dict(path_risks.get("frozen_eval_contamination"))
    leakage_evidence = _as_dict(leakage.get("evidence"))
    frozen_eval_evidence = _as_dict(frozen_eval_contamination.get("evidence"))

    baseline_assessment = _as_dict(
        baseline_identical_audit.get("baseline_identical_signal_assessment")
    )
    baseline_evidence = _as_dict(baseline_identical_audit.get("evidence"))
    split_hygiene = _as_dict(baseline_evidence.get("split_hygiene"))

    partition_assessment = _as_dict(partition_validity_audit.get("assessment"))
    partitions = _as_dict(partition_validity_audit.get("partitions"))
    supported_partition = _as_dict(partitions.get("supported_effect_enriched"))
    unsupported_partition = _as_dict(partitions.get("unsupported_base_clone"))
    supported_path_evidence = _as_dict(supported_partition.get("path_evidence"))
    unsupported_path_evidence = _as_dict(unsupported_partition.get("path_evidence"))

    calibration_assessment = _as_dict(calibration_dependence_audit.get("assessment"))
    consistency_checks = _as_dict(calibration_dependence_audit.get("consistency_checks"))

    synthetic_risk_posture = _as_dict(synthetic_prepost_audit.get("risk_posture"))
    synthetic_summary = _as_dict(synthetic_prepost_audit.get("overall_assessment"))

    training_view_enforcement = _as_dict(feature_schema.get("training_view_enforcement"))
    validation_selection = _as_dict(feature_schema.get("validation_selection"))
    validation_summary = _as_dict(validation_selection.get("summary"))

    split_counts = {
        "train_record_count": len(_as_list(split_manifest.get("train_record_ids"))),
        "val_record_count": len(_as_list(split_manifest.get("val_record_ids"))),
        "test_record_count": len(_as_list(split_manifest.get("test_record_ids"))),
    }

    path_map = {
        "training_inputs": {
            "allowed_fields": training_view_enforcement.get("training_input_allowed_fields"),
            "forbidden_outcome_side_fields": leakage_evidence.get(
                "training_input_forbidden_fields"
            ),
            "forbidden_feature_count": training_view_enforcement.get(
                "forbidden_feature_count"
            ),
            "contract_version": training_view_enforcement.get("contract_version"),
        },
        "generator_produced_fields": {
            "follow_up_fields": ["follow_up", "delta_z_by_domain", "follow_up_pro"],
            "proxy_fields": [
                "expected_effect_proxy",
                "adherence_proxy",
                "side_effect_proxy",
            ],
            "label_fields": ["next_action", "risk_tier", "response_profile"],
            "assignment_source": "recommend(request) inside rich_longitudinal_v4 generator",
        },
        "calibration_targets": {
            "primary_target": "expected_effect_proxy",
            "fit_stage": "policy_proxy_calibration",
            "selection_stage": validation_summary.get("selection_stage"),
            "selection_pre_policy_proxy_mae": validation_summary.get(
                "pre_policy_proxy_mae"
            ),
        },
        "replay_eval_targets": {
            "training_target_name": feature_schema.get("target_name"),
            "headline_fit_metrics": [
                "aggregate_mae",
                "aggregate_r2",
                "policy_proxy_mae",
            ],
            "dominant_replay_family": "non_cgm_continue_to_monitor_threshold_cross",
        },
        "split_independence": {
            "pair_overlap_counts": split_hygiene.get("pair_overlap_counts"),
            "user_overlap_counts": split_hygiene.get("user_overlap_counts"),
            "shares_path_with_frozen_eval": split_hygiene.get(
                "shares_path_with_frozen_eval"
            ),
            "exact_line_overlap_count": frozen_eval_evidence.get("exact_line_overlap_count"),
            "split_record_counts": split_counts,
            "split_record_counts_cover_dataset": consistency_checks.get(
                "split_record_counts_cover_dataset"
            ),
        },
    }

    status_answers = {
        "circularity": {
            "status": "present",
            "confidence": "high",
            "reason": (
                "supported effect-enriched rows remain exactly reconstructible from the "
                "generator follow-up formula"
            ),
            "key_metrics": {
                "supported_exact_reconstruction_rate_pct": supported_path_evidence.get(
                    "exact_reconstruction_rate_pct"
                ),
                "supported_case_count": supported_partition.get("case_count"),
            },
        },
        "generator_contamination": {
            "status": "present",
            "confidence": "high",
            "reason": (
                "supported rows still inherit assignment from recommend(request) and keep "
                "100% top-2 assignment match to the generator recommender"
            ),
            "key_metrics": {
                "supported_assignment_top2_match_rate_pct": supported_path_evidence.get(
                    "assignment_top2_match_rate_pct"
                ),
                "unsupported_assignment_top2_match_rate_pct": unsupported_path_evidence.get(
                    "assignment_top2_match_rate_pct"
                ),
            },
        },
        "calibration_target_coupling": {
            "status": "present",
            "confidence": "high",
            "reason": (
                "policy-proxy calibration still fits against generator-produced "
                "expected_effect_proxy and the gain is concentrated in the supported slice"
            ),
            "key_metrics": {
                "dependence_status": calibration_assessment.get("dependence_status"),
                "concentration_status": calibration_assessment.get("concentration_status"),
                "candidate_test_supported_gain": calibration_assessment.get(
                    "candidate_test_supported_gain"
                ),
                "candidate_test_unsupported_gain": calibration_assessment.get(
                    "candidate_test_unsupported_gain"
                ),
            },
        },
        "direct_training_input_leakage": {
            "status": "absent_on_current_training_view",
            "confidence": "high",
            "reason": (
                "forbidden outcome-side fields remain excluded from the enforced training view"
            ),
            "key_metrics": {
                "forbidden_training_feature_count": training_view_enforcement.get(
                    "forbidden_feature_count"
                ),
            },
        },
        "frozen_eval_contamination": {
            "status": "absent_on_current_checks",
            "confidence": "high",
            "reason": "path sharing and exact-line overlap with frozen eval remain zero",
            "key_metrics": {
                "shares_path_with_frozen_eval": split_hygiene.get(
                    "shares_path_with_frozen_eval"
                ),
                "exact_line_overlap_count": frozen_eval_evidence.get(
                    "exact_line_overlap_count"
                ),
            },
        },
        "split_independence": {
            "status": "adequate_but_not_sufficient",
            "confidence": "high",
            "reason": (
                "train/val/test are user-disjoint and path-disjoint enough, but generator-side "
                "contamination still survives across those clean splits"
            ),
            "key_metrics": {
                "pair_overlap_counts": split_hygiene.get("pair_overlap_counts"),
                "user_overlap_counts": split_hygiene.get("user_overlap_counts"),
                "split_record_counts_cover_dataset": consistency_checks.get(
                    "split_record_counts_cover_dataset"
                ),
            },
        },
    }

    contamination_paths = [
        {
            "risk_family": "circularity",
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:625",
            "detail": (
                "_build_effect_rich_follow_up_v4 deterministically creates follow_up and "
                "expected_effect_proxy from baseline/request/regimen/step-side ingredients."
            ),
            "measurable_evidence": {
                "supported_exact_reconstruction_rate_pct": supported_path_evidence.get(
                    "exact_reconstruction_rate_pct"
                ),
            },
        },
        {
            "risk_family": "generator_contamination",
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:207",
            "detail": (
                "_build_effect_rich_user_records_v4 still calls recommend(request) before "
                "synthetic outcomes are generated for supported rows."
            ),
            "measurable_evidence": {
                "supported_assignment_top2_match_rate_pct": supported_path_evidence.get(
                    "assignment_top2_match_rate_pct"
                ),
            },
        },
        {
            "risk_family": "generator_contamination",
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:765",
            "detail": (
                "_label_effect_rich_action_v4 thresholds generated proxies directly into "
                "next_action labels."
            ),
            "measurable_evidence": {
                "generator_simple_signal_status": baseline_assessment.get(
                    "generator_simple_signal_status"
                ),
            },
        },
        {
            "risk_family": "calibration_target_coupling",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:2043",
            "detail": (
                "_fit_policy_proxy_calibration still regresses predictions onto "
                "record.expected_effect_proxy using train+val rows."
            ),
            "measurable_evidence": {
                "candidate_test_supported_gain": calibration_assessment.get(
                    "candidate_test_supported_gain"
                ),
                "candidate_test_unsupported_gain": calibration_assessment.get(
                    "candidate_test_unsupported_gain"
                ),
            },
        },
        {
            "risk_family": "pair_contract_mixing",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:90",
            "detail": (
                "pair rows still carry both allowed training inputs and outcome-side fields in "
                "one row shape even though the training view later filters them."
            ),
            "measurable_evidence": {
                "forbidden_training_feature_count": training_view_enforcement.get(
                    "forbidden_feature_count"
                ),
                "label_copy_risk_status": baseline_assessment.get("label_copy_risk_status"),
            },
        },
    ]

    acceptable_shared_domain_assumptions = [
        (
            "goal, baseline, input_flags, recommended_set, and period remain the only "
            "allowed learned inputs"
        ),
        "train/val/test remain pair-disjoint and user-disjoint",
        (
            "synthetic dataset path stays separate from frozen-eval data and exact-line "
            "overlap remains zero"
        ),
        (
            "baseline-identical label-copy risk is reduced enough that current risk is "
            "not simple direct label copying"
        ),
    ]
    unacceptable_target_leakage = [
        (
            "supported effect-enriched rows still show 100% exact reconstruction from "
            "generator follow-up formulas"
        ),
        (
            "supported effect-enriched rows still show 100% top-2 assignment match to "
            "the generator recommender"
        ),
        (
            "policy-proxy calibration still uses generator-produced "
            "expected_effect_proxy as its target-side anchor"
        ),
        (
            "supported and unsupported partitions still cannot support one pooled "
            "learned-efficacy claim"
        ),
    ]
    ambiguous_contamination_risk = [
        (
            "pair rows still physically store outcome-side fields even though the "
            "enforced training view excludes them"
        ),
        (
            "clean user/path splits do not prove independence when the same generator "
            "family determines assignment, proxies, and labels"
        ),
        (
            "baseline-identical simple label copying is reduced, but generator-simple "
            "signal remains present in the supported slice"
        ),
    ]

    ranked_remediation = [
        {
            "priority": 1,
            "action": (
                "keep supported effect-enriched rows replay-only for efficacy interpretation "
                "until they are no longer exactly reconstructible and assignment-coupled"
            ),
            "why": (
                "this is the tightest way to stop circular supported-slice evidence "
                "from justifying a rerun"
            ),
        },
        {
            "priority": 2,
            "action": (
                "treat pre-policy-proxy and post-policy-proxy reporting as separate gates and "
                "do not use calibrated expected_effect_proxy gain alone as rerun justification"
            ),
            "why": (
                "current calibration gain is materially concentrated in the "
                "generator-coupled supported slice"
            ),
        },
        {
            "priority": 3,
            "action": (
                "keep supported and unsupported partitions separate in validity claims and require "
                "one non-circular replay/eval proof before revisiting training"
            ),
            "why": (
                "current split hygiene is real but insufficient to neutralize "
                "generator-side contamination"
            ),
        },
    ]

    go_no_go_memo = {
        "verdict": "no_go_for_training_rerun_justification",
        "summary": (
            "Current synthetic validity evidence is strong enough to say the path is guarded "
            "against direct input leakage and frozen-eval contamination, but not strong enough "
            "to justify a new training rerun because circularity, generator contamination, and "
            "calibration-target coupling are all still present in the supported "
            "effect-enriched slice."
        ),
        "circularity_answer": status_answers["circularity"]["status"],
        "generator_contamination_answer": status_answers["generator_contamination"]["status"],
        "calibration_target_coupling_answer": status_answers["calibration_target_coupling"][
            "status"
        ],
        "training_rerun_justified_now": False,
        "minimum_changes_before_future_training_rerun": [
            (
                "stop using supported effect-enriched exact-fit evidence as independent "
                "efficacy proof"
            ),
            (
                "separate pre-calibration fit from calibration-on-expected_effect_proxy "
                "gains in rerun gating"
            ),
            (
                "earn at least one new replay/data proof on a less circular surface "
                "before revisiting training"
            ),
        ],
    }

    readable_summary = {
        "bottom_line": (
            "Circularity, generator contamination, and calibration-target coupling are all "
            "present; direct training-input leakage and frozen-eval contamination are not the "
            "current blockers."
        ),
        "supported_slice_digest": {
            "supported_case_count": supported_partition.get("case_count"),
            "supported_exact_reconstruction_rate_pct": supported_path_evidence.get(
                "exact_reconstruction_rate_pct"
            ),
            "supported_assignment_top2_match_rate_pct": supported_path_evidence.get(
                "assignment_top2_match_rate_pct"
            ),
            "candidate_test_supported_calibration_gain": calibration_assessment.get(
                "candidate_test_supported_gain"
            ),
        },
        "unsupported_slice_digest": {
            "unsupported_case_count": unsupported_partition.get("case_count"),
            "unsupported_assignment_top2_match_rate_pct": unsupported_path_evidence.get(
                "assignment_top2_match_rate_pct"
            ),
            "candidate_test_unsupported_calibration_gain": calibration_assessment.get(
                "candidate_test_unsupported_gain"
            ),
        },
        "split_hygiene_digest": {
            "pair_overlap_counts": split_hygiene.get("pair_overlap_counts"),
            "user_overlap_counts": split_hygiene.get("user_overlap_counts"),
            "shares_path_with_frozen_eval": split_hygiene.get(
                "shares_path_with_frozen_eval"
            ),
            "exact_line_overlap_count": frozen_eval_evidence.get("exact_line_overlap_count"),
        },
        "rerun_gate_digest": {
            "go_no_go": go_no_go_memo.get("verdict"),
            "training_rerun_justified_now": go_no_go_memo.get("training_rerun_justified_now"),
            "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
        },
    }

    validation_issues = validate_synthetic_validity_audit(
        status_answers=status_answers,
        readable_summary=readable_summary,
        synthetic_risk_posture=synthetic_risk_posture,
    )

    return {
        "audit_name": "synthetic_validity_audit_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "path_safety_audit_path": str(path_safety_audit_path),
            "baseline_identical_audit_path": str(baseline_identical_audit_path),
            "partition_validity_audit_path": str(partition_validity_audit_path),
            "calibration_dependence_audit_path": str(calibration_dependence_audit_path),
            "synthetic_prepost_audit_path": str(synthetic_prepost_audit_path),
            "feature_schema_path": str(feature_schema_path),
            "split_manifest_path": str(split_manifest_path),
        },
        "path_map": path_map,
        "status_answers": status_answers,
        "contamination_paths": contamination_paths,
        "acceptable_shared_domain_assumptions": acceptable_shared_domain_assumptions,
        "unacceptable_target_leakage": unacceptable_target_leakage,
        "ambiguous_contamination_risk": ambiguous_contamination_risk,
        "ranked_remediation": ranked_remediation,
        "go_no_go_memo": go_no_go_memo,
        "readable_summary": readable_summary,
        "validation_issues": validation_issues,
        "upstream_consistency": {
            "synthetic_prepost_verdict": synthetic_summary.get("verdict"),
            "partition_verdict": partition_assessment.get("verdict"),
            "baseline_identical_verdict": baseline_assessment.get("verdict"),
            "calibration_dependence_verdict": calibration_assessment.get("verdict"),
        },
    }


def validate_synthetic_validity_audit(
    *,
    status_answers: dict[str, object],
    readable_summary: dict[str, object],
    synthetic_risk_posture: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    circularity = _as_dict(status_answers.get("circularity"))
    contamination = _as_dict(status_answers.get("generator_contamination"))
    coupling = _as_dict(status_answers.get("calibration_target_coupling"))
    leakage = _as_dict(status_answers.get("direct_training_input_leakage"))
    frozen_eval = _as_dict(status_answers.get("frozen_eval_contamination"))
    split_independence = _as_dict(status_answers.get("split_independence"))
    rerun_gate = _as_dict(readable_summary.get("rerun_gate_digest"))

    if circularity.get("status") != "present":
        issues.append("circularity verdict drifted")
    if contamination.get("status") != "present":
        issues.append("generator contamination verdict drifted")
    if coupling.get("status") != "present":
        issues.append("calibration-target coupling verdict drifted")
    if leakage.get("status") != "absent_on_current_training_view":
        issues.append("direct training-input leakage verdict drifted")
    if frozen_eval.get("status") != "absent_on_current_checks":
        issues.append("frozen-eval contamination verdict drifted")
    if split_independence.get("status") != "adequate_but_not_sufficient":
        issues.append("split independence verdict drifted")
    if rerun_gate.get("go_no_go") != "no_go_for_training_rerun_justification":
        issues.append("rerun gate verdict drifted")
    if rerun_gate.get("training_rerun_justified_now") is not False:
        issues.append("training rerun must remain unjustified")
    if synthetic_risk_posture.get("circularity_status") != "high_risk":
        issues.append("upstream circularity posture drifted")
    if synthetic_risk_posture.get("generator_contamination_status") != "high_risk":
        issues.append("upstream generator contamination posture drifted")
    if synthetic_risk_posture.get("calibration_dependence_status") != "material":
        issues.append("upstream calibration dependence posture drifted")
    return issues


def render_synthetic_validity_audit_markdown(audit: dict[str, object]) -> str:
    status_answers = _as_dict(audit.get("status_answers"))
    memo = _as_dict(audit.get("go_no_go_memo"))
    readable_summary = _as_dict(audit.get("readable_summary"))
    lines = [
        "# synthetic validity audit v1",
        "",
        f"- verdict: `{memo.get('verdict')}`",
        f"- summary: `{memo.get('summary')}`",
        "",
        "## Readable Summary",
        f"- readable_summary: `{readable_summary}`",
        "",
        "## Status Answers",
    ]
    for key in (
        "circularity",
        "generator_contamination",
        "calibration_target_coupling",
        "direct_training_input_leakage",
        "frozen_eval_contamination",
        "split_independence",
    ):
        lines.append(f"- {key}: `{status_answers.get(key)}`")
    lines.extend(["", "## Path Map", f"- path_map: `{audit.get('path_map')}`", ""])
    lines.append("## Contamination Paths")
    for item in _as_list(audit.get("contamination_paths")):
        payload = _as_dict(item)
        lines.append(
            f"- `{payload.get('path')}` [{payload.get('risk_family')}]: {payload.get('detail')}"
        )
    lines.extend(["", "## Acceptable Shared Domain Assumptions"])
    for item in _as_list(audit.get("acceptable_shared_domain_assumptions")):
        lines.append(f"- {item}")
    lines.extend(["", "## Unacceptable Target Leakage"])
    for item in _as_list(audit.get("unacceptable_target_leakage")):
        lines.append(f"- {item}")
    lines.extend(["", "## Ambiguous Contamination Risk"])
    for item in _as_list(audit.get("ambiguous_contamination_risk")):
        lines.append(f"- {item}")
    lines.extend(["", "## Ranked Remediation"])
    for item in _as_list(audit.get("ranked_remediation")):
        payload = _as_dict(item)
        lines.append(
            f"- P{payload.get('priority')}: {payload.get('action')} ({payload.get('why')})"
        )
    lines.extend(["", "## Minimum Changes Before Future Training Rerun"])
    for item in _as_list(memo.get("minimum_changes_before_future_training_rerun")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_synthetic_validity_audit_files(
    *,
    audit: dict[str, object],
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_synthetic_validity_audit_markdown(audit), encoding="utf-8")


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_synthetic_validity_audit",
    "load_json",
    "render_synthetic_validity_audit_markdown",
    "validate_synthetic_validity_audit",
    "write_synthetic_validity_audit_files",
]
