from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_synthetic_validity_followup_single_item(
    *,
    dataset_path: str | Path,
    synthetic_validity_audit: dict[str, object],
    synthetic_validity_audit_path: str | Path,
    calibration_dependence_audit: dict[str, object],
    calibration_dependence_audit_path: str | Path,
    partition_validity_audit: dict[str, object],
    partition_validity_audit_path: str | Path,
    policy_proxy_replay_split_audit: dict[str, object],
    policy_proxy_replay_split_audit_path: str | Path,
) -> dict[str, object]:
    path_map = _as_dict(synthetic_validity_audit.get("path_map"))
    training_inputs = _as_dict(path_map.get("training_inputs"))
    calibration_targets = _as_dict(path_map.get("calibration_targets"))
    split_independence = _as_dict(path_map.get("split_independence"))

    status_answers = _as_dict(synthetic_validity_audit.get("status_answers"))
    calibration_status = _as_dict(status_answers.get("calibration_target_coupling"))
    leakage_status = _as_dict(status_answers.get("direct_training_input_leakage"))
    frozen_eval_status = _as_dict(status_answers.get("frozen_eval_contamination"))

    partition_assessment = _as_dict(partition_validity_audit.get("assessment"))
    partitions = _as_dict(partition_validity_audit.get("partitions"))
    supported_partition = _as_dict(partitions.get("supported_effect_enriched"))
    unsupported_partition = _as_dict(partitions.get("unsupported_base_clone"))

    calibration_assessment = _as_dict(calibration_dependence_audit.get("assessment"))
    artifact_summaries = _as_dict(calibration_dependence_audit.get("artifact_summaries"))
    consistency_checks = _as_dict(calibration_dependence_audit.get("consistency_checks"))
    candidate_summary = _as_dict(artifact_summaries.get("candidate"))
    baseline_summary = _as_dict(artifact_summaries.get("baseline"))
    replay_assessment = _as_dict(policy_proxy_replay_split_audit.get("assessment"))

    case_count = _to_int(
        _nested(calibration_dependence_audit, "dataset_support_summary", "case_count")
    )
    candidate_test = _build_gain_concentration(
        split_summary=_as_dict(_nested(candidate_summary, "splits", "test")),
    )
    baseline_test = _build_gain_concentration(
        split_summary=_as_dict(_nested(baseline_summary, "splits", "test")),
    )

    acceptable_shared_assumptions = [
        {
            "claim": "direct_training_inputs_do_not_include_expected_effect_proxy",
            "status": "acceptable_shared_assumption",
            "evidence": {
                "allowed_fields": training_inputs.get("allowed_fields"),
                "forbidden_outcome_side_fields": training_inputs.get(
                    "forbidden_outcome_side_fields"
                ),
                "forbidden_feature_count": training_inputs.get(
                    "forbidden_feature_count"
                ),
                "leakage_status": leakage_status.get("status"),
            },
            "paths": [
                "src/wellnessbox_rnd/training/effect_model_v1.py:201",
                "src/wellnessbox_rnd/training/effect_model_v1.py:2043",
            ],
        },
        {
            "claim": "pre_policy_proxy_selection_surface_is_separated_and_reproducible",
            "status": "acceptable_shared_assumption",
            "evidence": {
                "selection_stage": calibration_targets.get("selection_stage"),
                "selection_pre_policy_proxy_mae": calibration_targets.get(
                    "selection_pre_policy_proxy_mae"
                ),
                "consistency_check": consistency_checks.get(
                    "candidate_val_pre_policy_proxy_mae_matches_feature_schema"
                ),
            },
            "paths": [
                "src/wellnessbox_rnd/training/effect_model_v1.py:1828",
                "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
            ],
        },
        {
            "claim": "supported_and_unsupported_validity_surfaces_are_already_split",
            "status": "acceptable_shared_assumption",
            "evidence": {
                "partition_verdict": partition_assessment.get("verdict"),
                "supported_case_count": supported_partition.get("case_count"),
                "unsupported_case_count": unsupported_partition.get("case_count"),
                "split_record_counts_cover_dataset": split_independence.get(
                    "split_record_counts_cover_dataset"
                ),
            },
            "paths": [
                "artifacts/reports/dataset_f_partition_validity_audit_v1.json",
                "artifacts/reports/synthetic_validity_audit_v1.json",
            ],
        },
    ]

    unacceptable_leakage_or_contamination = [
        {
            "claim": (
                "policy_proxy_calibration_still_targets_"
                "generator_produced_expected_effect_proxy"
            ),
            "status": "unacceptable_leakage_or_contamination",
            "evidence": {
                "fit_stage": calibration_targets.get("fit_stage"),
                "primary_target": calibration_targets.get("primary_target"),
                "calibration_dependence_status": calibration_assessment.get(
                    "dependence_status"
                ),
                "concentration_status": calibration_assessment.get(
                    "concentration_status"
                ),
            },
            "paths": [
                "src/wellnessbox_rnd/training/effect_model_v1.py:2043",
                "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:661",
            ],
        },
        {
            "claim": (
                "candidate_post_calibration_gain_is_concentrated_in_"
                "supported_effect_enriched_rows"
            ),
            "status": "unacceptable_leakage_or_contamination",
            "evidence": candidate_test,
            "paths": [
                "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
                "artifacts/reports/dataset_f_partition_validity_audit_v1.json",
            ],
        },
        {
            "claim": "baseline_shows_the_same_supported_slice_dependence_pattern",
            "status": "unacceptable_leakage_or_contamination",
            "evidence": baseline_test,
            "paths": [
                "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
            ],
        },
    ]

    ambiguous_remaining_risk = [
        {
            "claim": "some_post_calibration_improvement_could_be_ordinary_monotonic_alignment",
            "status": "ambiguous_risk_still_unproven",
            "reason": (
                "Current audits do not prove that every supported-slice calibration gain is "
                "pure contamination, but they also do not isolate any non-generator target "
                "anchor that would make the gain independent."
            ),
        },
        {
            "claim": "unsupported_negative_gain_does_not_prove_calibration_should_be_removed",
            "status": "ambiguous_risk_still_unproven",
            "reason": (
                "The current evidence is strong enough to reject calibrated proxy gain as "
                "training-gate evidence, but not strong enough to justify deleting "
                "calibration behavior from replay analysis."
            ),
        },
    ]

    validation_issues = validate_synthetic_validity_followup_single_item(
        calibration_status=calibration_status,
        frozen_eval_status=frozen_eval_status,
        candidate_test=candidate_test,
        baseline_test=baseline_test,
        replay_assessment=replay_assessment,
        consistency_checks=consistency_checks,
        acceptable_shared_assumptions=acceptable_shared_assumptions,
        unacceptable_leakage_or_contamination=unacceptable_leakage_or_contamination,
    )

    final_disposition = {
        "resolution_state": "still_risky",
        "actionable_for_future_gate_work": True,
            "summary": (
                "Calibration-target coupling is still risky rather than merely unproven: the "
                "post-calibration proxy gain remains structurally concentrated in the supported "
                "effect-enriched slice, replay shifts appear only on supported users under "
                "neutralization, and the target anchor is still generator-produced "
                "expected_effect_proxy."
            ),
        "what_is_resolved": [
            (
                "direct feature leakage into learned inputs remains guarded "
                "under the current training view"
            ),
            (
                "pre-policy-proxy selection is already separated enough to "
                "keep neutralized metrics readable"
            ),
        ],
        "what_remains_risky": [
            (
                "calibrated proxy gain is still materially supported-slice "
                "concentrated for both candidate and baseline artifacts"
            ),
            (
                "current post-calibration gain still cannot be treated as "
                "independent efficacy evidence for future rerun gating"
            ),
        ],
        "what_remains_unproven": [
            (
                "how much of the supported-slice post-calibration improvement "
                "would survive with a non-generator target anchor"
            ),
        ],
        "narrow_remediation_recommendation": (
            "For future training-gate work, keep pre-policy-proxy or neutralized proxy "
            "metrics as the gating surface and treat post-calibration expected_effect_proxy "
            "gain as replay-only diagnostic evidence until a non-generator target anchor is "
            "available."
        ),
    }

    return {
        "audit_name": "synthetic_validity_followup_single_item_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "case_count": case_count,
            "chosen_item": "calibration_target_coupling",
            "upstream_artifacts": {
                "synthetic_validity_audit_path": str(synthetic_validity_audit_path),
                "calibration_dependence_audit_path": str(
                    calibration_dependence_audit_path
                ),
                "partition_validity_audit_path": str(partition_validity_audit_path),
                "policy_proxy_replay_split_audit_path": str(
                    policy_proxy_replay_split_audit_path
                ),
            },
        },
        "selection": {
            "chosen_item": "calibration_target_coupling",
            "why_this_minimum_change_item": (
                "This is the highest-ROI minimum-change follow-up because current repo "
                "artifacts already separate pre-vs-post calibration and "
                "supported-vs-unsupported surfaces without needing any training rerun, "
                "runtime change, or synthetic generator redesign."
            ),
            "other_items_not_chosen_now": [
                (
                    "supported-slice circularity remains broader because it "
                    "touches generator formulas end-to-end"
                ),
                (
                    "generator contamination remains broader because it spans "
                    "assignment entrypoint and label formulas"
                ),
            ],
        },
        "evidence_path": {
            "acceptable_shared_assumptions": acceptable_shared_assumptions,
            "unacceptable_leakage_or_contamination": (
                unacceptable_leakage_or_contamination
            ),
            "ambiguous_remaining_risk": ambiguous_remaining_risk,
        },
        "measured_concentration": {
            "candidate_test": candidate_test,
            "baseline_test": baseline_test,
            "replay_shift_assessment": replay_assessment,
            "consistency_checks": consistency_checks,
        },
        "final_disposition": final_disposition,
        "validation_issues": validation_issues,
    }


def render_synthetic_validity_followup_single_item_markdown(
    audit: dict[str, object],
) -> str:
    scope = _as_dict(audit.get("scope"))
    selection = _as_dict(audit.get("selection"))
    evidence_path = _as_dict(audit.get("evidence_path"))
    measured = _as_dict(audit.get("measured_concentration"))
    disposition = _as_dict(audit.get("final_disposition"))

    lines = [
        "# synthetic validity followup single item v1",
        "",
        f"- chosen_item: `{scope.get('chosen_item')}`",
        f"- dataset_path: `{scope.get('dataset_path')}`",
        f"- case_count: `{scope.get('case_count')}`",
        f"- why_this_item: `{selection.get('why_this_minimum_change_item')}`",
        "",
        "## Acceptable Shared Assumptions",
    ]
    for item in _as_list(evidence_path.get("acceptable_shared_assumptions")):
        payload = _as_dict(item)
        lines.append(
            f"- {payload.get('claim')}: `{payload.get('evidence')}`"
        )
    lines.extend(
        [
            "",
            "## Unacceptable Leakage Or Contamination",
        ]
    )
    for item in _as_list(evidence_path.get("unacceptable_leakage_or_contamination")):
        payload = _as_dict(item)
        lines.append(
            f"- {payload.get('claim')}: `{payload.get('evidence')}`"
        )
    lines.extend(
        [
            "",
            "## Ambiguous Risk Still Unproven",
        ]
    )
    for item in _as_list(evidence_path.get("ambiguous_remaining_risk")):
        payload = _as_dict(item)
        lines.append(
            f"- {payload.get('claim')}: `{payload.get('reason')}`"
        )
    lines.extend(
        [
            "",
            "## Measured Concentration",
            f"- candidate_test: `{measured.get('candidate_test')}`",
            f"- baseline_test: `{measured.get('baseline_test')}`",
            f"- replay_shift_assessment: `{measured.get('replay_shift_assessment')}`",
            f"- consistency_checks: `{measured.get('consistency_checks')}`",
            "",
            "## Final Disposition",
            f"- resolution_state: `{disposition.get('resolution_state')}`",
            (
                "- actionable_for_future_gate_work: "
                f"`{disposition.get('actionable_for_future_gate_work')}`"
            ),
            f"- summary: `{disposition.get('summary')}`",
            f"- what_is_resolved: `{disposition.get('what_is_resolved')}`",
            f"- what_remains_risky: `{disposition.get('what_remains_risky')}`",
            (
                "- what_remains_unproven: "
                f"`{disposition.get('what_remains_unproven')}`"
            ),
            (
                "- narrow_remediation_recommendation: "
                f"`{disposition.get('narrow_remediation_recommendation')}`"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_synthetic_validity_followup_single_item_files(
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
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(
        render_synthetic_validity_followup_single_item_markdown(audit),
        encoding="utf-8",
    )


def validate_synthetic_validity_followup_single_item(
    *,
    calibration_status: dict[str, object],
    frozen_eval_status: dict[str, object],
    candidate_test: dict[str, object],
    baseline_test: dict[str, object],
    replay_assessment: dict[str, object],
    consistency_checks: dict[str, object],
    acceptable_shared_assumptions: list[dict[str, object]],
    unacceptable_leakage_or_contamination: list[dict[str, object]],
) -> list[str]:
    issues: list[str] = []
    if calibration_status.get("status") != "present":
        issues.append("calibration-target coupling must remain present for this follow-up")
    if frozen_eval_status.get("status") != "absent_on_current_checks":
        issues.append("frozen-eval contamination status must stay absent on current checks")
    if not all(bool(value) for value in consistency_checks.values()):
        issues.append("all upstream consistency checks must stay true")
    if _to_float(candidate_test.get("supported_share_of_net_gain_pct")) <= 100.0:
        issues.append("candidate supported slice should explain more than 100% of net gain")
    if _to_float(baseline_test.get("supported_share_of_net_gain_pct")) <= 100.0:
        issues.append("baseline supported slice should explain more than 100% of net gain")
    if replay_assessment.get("verdict") != "supported_slice_replay_shift_concentrated":
        issues.append("replay shift evidence must stay supported-slice concentrated")
    if len(acceptable_shared_assumptions) != 3:
        issues.append("exactly three acceptable shared assumptions are expected")
    if len(unacceptable_leakage_or_contamination) != 3:
        issues.append(
            "exactly three unacceptable leakage-or-contamination findings are expected"
        )
    return issues


def _build_gain_concentration(*, split_summary: dict[str, object]) -> dict[str, object]:
    overall = _as_dict(split_summary.get("overall"))
    supported = _as_dict(split_summary.get("supported_effect_enriched"))
    unsupported = _as_dict(split_summary.get("unsupported_base_clone"))

    overall_gain = _to_float(overall.get("policy_proxy_calibration_gain"))
    overall_count = _to_int(overall.get("record_count"))
    supported_gain = _to_float(supported.get("policy_proxy_calibration_gain"))
    unsupported_gain = _to_float(unsupported.get("policy_proxy_calibration_gain"))
    supported_count = _to_int(supported.get("record_count"))
    unsupported_count = _to_int(unsupported.get("record_count"))

    supported_weighted_contribution = round(
        _weighted_contribution(supported_gain, supported_count, overall_count), 6
    )
    unsupported_weighted_contribution = round(
        _weighted_contribution(unsupported_gain, unsupported_count, overall_count), 6
    )
    return {
        "overall_record_count": overall_count,
        "supported_record_count": supported_count,
        "unsupported_record_count": unsupported_count,
        "overall_gain": round(overall_gain, 6),
        "supported_gain": round(supported_gain, 6),
        "unsupported_gain": round(unsupported_gain, 6),
        "supported_weighted_contribution": supported_weighted_contribution,
        "unsupported_weighted_contribution": unsupported_weighted_contribution,
        "supported_share_of_net_gain_pct": _share_pct(
            supported_weighted_contribution, overall_gain
        ),
        "unsupported_share_of_net_gain_pct": _share_pct(
            unsupported_weighted_contribution, overall_gain
        ),
        "supported_minus_unsupported_gain": round(
            supported_gain - unsupported_gain, 6
        ),
    }


def _weighted_contribution(gain: float, count: int, total_count: int) -> float:
    if total_count <= 0:
        return 0.0
    return gain * count / total_count


def _share_pct(contribution: float, overall_gain: float) -> float | None:
    if abs(overall_gain) <= 1e-12:
        return None
    return round((contribution / overall_gain) * 100.0, 2)


def _nested(payload: dict[str, object], *path: str) -> object | None:
    current: object = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _to_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return 0.0


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(float(value))
    return 0
