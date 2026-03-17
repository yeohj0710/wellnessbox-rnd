from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_synthetic_prepost_path_audit(
    *,
    dataset_path: str | Path,
    pair_dataset_path: str | Path,
    path_safety_audit: dict[str, object],
    path_safety_audit_path: str | Path,
    baseline_identical_audit: dict[str, object],
    baseline_identical_audit_path: str | Path,
    partition_validity_audit: dict[str, object],
    partition_validity_audit_path: str | Path,
    design_sanity_audit: dict[str, object],
    design_sanity_audit_path: str | Path,
) -> dict[str, object]:
    dataset_summary = _as_dict(path_safety_audit.get("dataset_summary"))
    risk_assessment = _as_dict(path_safety_audit.get("risk_assessment"))
    baseline_assessment = _as_dict(
        baseline_identical_audit.get("baseline_identical_signal_assessment")
    )
    baseline_evidence = _as_dict(baseline_identical_audit.get("evidence"))
    split_hygiene = _as_dict(baseline_evidence.get("split_hygiene"))
    partition_assessment = _as_dict(partition_validity_audit.get("assessment"))
    sanity_overall = _as_dict(design_sanity_audit.get("overall_verdict"))

    leakage = _as_dict(risk_assessment.get("leakage"))
    circularity = _as_dict(risk_assessment.get("circularity"))
    baseline_identical = _as_dict(risk_assessment.get("baseline_identical_label"))
    generator_contamination = _as_dict(risk_assessment.get("generator_contamination"))
    frozen_eval_contamination = _as_dict(risk_assessment.get("frozen_eval_contamination"))

    leakage_evidence = _as_dict(leakage.get("evidence"))
    circularity_evidence = _as_dict(circularity.get("evidence"))
    baseline_identical_evidence = _as_dict(baseline_identical.get("evidence"))
    generator_evidence = _as_dict(generator_contamination.get("evidence"))
    frozen_eval_evidence = _as_dict(frozen_eval_contamination.get("evidence"))

    pinpointed_risk_paths = [
        {
            "risk_family": "leakage_guard",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:169",
            "kind": "contract",
            "detail": (
                "dataset_f_effect_training_view_v1 currently restricts training inputs to "
                "goal, baseline, input_flags, recommended_set, and period."
            ),
        },
        {
            "risk_family": "leakage_guard",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1939",
            "kind": "feature_path",
            "detail": (
                "build_effect_training_feature_dict_v1 emits baseline and intervention-assignment "
                "features only; direct follow_up/adverse_event/next_action fields are absent."
            ),
        },
        {
            "risk_family": "calibration_target_coupling",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1862",
            "kind": "calibration_target",
            "detail": (
                "_fit_policy_proxy_calibration still regresses predicted aggregate delta onto "
                "generator-produced expected_effect_proxy."
            ),
        },
        {
            "risk_family": "generator_contamination",
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:207",
            "kind": "generator_entrypoint",
            "detail": (
                "_build_effect_rich_user_records_v4 reruns recommend(request) before synthetic "
                "outcomes are generated for supported effect-enriched rows."
            ),
        },
        {
            "risk_family": "circularity",
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:625",
            "kind": "generator_formula",
            "detail": (
                "_build_effect_rich_follow_up_v4 deterministically produces follow_up_pro, "
                "delta_z_by_domain, and expected_effect_proxy from baseline/request/regimen/"
                "adherence_proxy/side_effect_proxy/step."
            ),
        },
        {
            "risk_family": "generator_contamination",
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:765",
            "kind": "label_formula",
            "detail": (
                "_label_effect_rich_action_v4 thresholds expected_effect_proxy, adherence_proxy, "
                "and side_effect_proxy directly into next_action labels."
            ),
        },
        {
            "risk_family": "pair_contract_mixing",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:90",
            "kind": "pair_contract",
            "detail": (
                "EffectDatasetPairRowV1 still stores baseline, follow_up, expected_effect_proxy, "
                "adherence_proxy, side_effect_proxy, next_action, and adverse_event in one row "
                "shape even though training-view enforcement later filters the inputs."
            ),
        },
        {
            "risk_family": "frozen_eval_guard",
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1044",
            "kind": "contamination_guard",
            "detail": (
                "Dataset F split validation still rejects source paths that match the frozen-eval "
                "dataset path."
            ),
        },
    ]

    safe_now = [
        "forbidden training feature count remains 0 under dataset_f_effect_training_view_v1",
        "split hygiene remains clean with pair overlap 0 and user overlap 0",
        "frozen-eval path sharing remains false and exact line overlap remains 0",
        (
            "baseline-identical label-copy risk is low because 70/96 "
            "constant-baseline users still show label variation"
        ),
    ]
    risky_now = [
        (
            "supported effect-enriched rows still have 100% exact reconstruction "
            "from the synthetic generator"
        ),
        (
            "supported effect-enriched rows still have 100% top-2 recommendation "
            "assignment match to the generator recommender"
        ),
        (
            "policy-proxy calibration still depends materially on "
            "generator-produced expected_effect_proxy"
        ),
        (
            "supported and unsupported rows still should not be pooled into one "
            "learned-efficacy validity claim"
        ),
    ]
    risk_matrix = {
        "leakage": {
            "status": leakage.get("status"),
            "headline": (
                "training-view enforcement blocks direct follow_up and other "
                "outcome-side fields from learned inputs."
            ),
        },
        "circularity": {
            "status": circularity.get("status"),
            "headline": (
                "supported rows still reconstruct exactly from generator-produced "
                "follow_up formulas."
            ),
        },
        "baseline_identical_label": {
            "status": baseline_assessment.get("label_copy_risk_status"),
            "headline": (
                "baseline-identical label-copy risk is reduced because many "
                "constant-baseline users still vary labels."
            ),
        },
        "generator_contamination": {
            "status": generator_contamination.get("status"),
            "headline": (
                "generator recommendation and label formulas still shape supported "
                "training targets directly."
            ),
        },
        "frozen_eval_contamination": {
            "status": frozen_eval_contamination.get("status"),
            "headline": (
                "path-level and exact-line checks still show no frozen-eval overlap."
            ),
        },
    }
    pinpointed_path_digest = {
        risk_family: [
            item["path"]
            for item in pinpointed_risk_paths
            if item["risk_family"] == risk_family
        ]
        for risk_family in sorted({item["risk_family"] for item in pinpointed_risk_paths})
    }

    return {
        "audit_name": "synthetic_prepost_path_audit_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "pair_dataset_path": str(Path(pair_dataset_path)),
            "path_safety_audit_path": str(path_safety_audit_path),
            "baseline_identical_audit_path": str(baseline_identical_audit_path),
            "partition_validity_audit_path": str(partition_validity_audit_path),
            "design_sanity_audit_path": str(design_sanity_audit_path),
        },
        "risk_posture": {
            "leakage_status": leakage.get("status"),
            "circularity_status": circularity.get("status"),
            "baseline_identical_label_status": baseline_assessment.get(
                "label_copy_risk_status"
            ),
            "generator_contamination_status": generator_contamination.get("status"),
            "frozen_eval_contamination_status": frozen_eval_contamination.get("status"),
            "calibration_dependence_status": partition_assessment.get(
                "calibration_dependence_status"
            ),
            "calibration_dependence_concentration": partition_assessment.get(
                "calibration_dependence_concentration"
            ),
            "partition_verdict": partition_assessment.get("verdict"),
        },
        "evidence_snapshot": {
            "case_count": dataset_summary.get("case_count"),
            "pair_row_count": dataset_summary.get("pair_row_count"),
            "supported_effect_enriched_record_count": dataset_summary.get(
                "supported_effect_enriched_record_count"
            ),
            "unsupported_or_base_clone_record_count": dataset_summary.get(
                "unsupported_or_base_clone_record_count"
            ),
            "forbidden_training_feature_count": leakage_evidence.get(
                "forbidden_training_feature_count"
            ),
            "training_input_allowed_fields": leakage_evidence.get(
                "training_input_allowed_fields"
            ),
            "training_input_forbidden_fields": leakage_evidence.get(
                "training_input_forbidden_fields"
            ),
            "exact_reconstruction_rate_pct": circularity_evidence.get(
                "exact_reconstruction_rate_pct"
            ),
            "supported_mode_top2_match_rate_pct": generator_evidence.get(
                "supported_mode_top2_match_rate_pct"
            ),
            "constant_baseline_user_count": baseline_identical_evidence.get(
                "constant_baseline_user_count"
            ),
            "constant_baseline_with_label_variation_user_count": (
                baseline_identical_evidence.get(
                    "constant_baseline_with_label_variation_user_count"
                )
            ),
            "constant_baseline_with_label_variation_rate_pct": (
                baseline_identical_evidence.get(
                    "constant_baseline_with_label_variation_rate_pct"
                )
            ),
            "shares_path_with_frozen_eval": split_hygiene.get(
                "shares_path_with_frozen_eval"
            ),
            "exact_line_overlap_count": frozen_eval_evidence.get(
                "exact_line_overlap_count"
            ),
            "principal_blocker": sanity_overall.get("principal_blocker"),
        },
        "readable_summary": {
            "risk_matrix": risk_matrix,
            "safe_now_digest": {
                "forbidden_training_feature_count": leakage_evidence.get(
                    "forbidden_training_feature_count"
                ),
                "training_input_allowed_fields": leakage_evidence.get(
                    "training_input_allowed_fields"
                ),
                "training_input_forbidden_fields": leakage_evidence.get(
                    "training_input_forbidden_fields"
                ),
                "constant_baseline_with_label_variation_rate_pct": (
                    baseline_identical_evidence.get(
                        "constant_baseline_with_label_variation_rate_pct"
                    )
                ),
                "shares_path_with_frozen_eval": split_hygiene.get(
                    "shares_path_with_frozen_eval"
                ),
                "exact_line_overlap_count": frozen_eval_evidence.get(
                    "exact_line_overlap_count"
                ),
            },
            "risky_now_digest": {
                "exact_reconstruction_rate_pct": circularity_evidence.get(
                    "exact_reconstruction_rate_pct"
                ),
                "supported_mode_top2_match_rate_pct": generator_evidence.get(
                    "supported_mode_top2_match_rate_pct"
                ),
                "calibration_dependence_status": partition_assessment.get(
                    "calibration_dependence_status"
                ),
                "calibration_dependence_concentration": partition_assessment.get(
                    "calibration_dependence_concentration"
                ),
                "partition_verdict": partition_assessment.get("verdict"),
            },
            "pinpointed_path_digest": pinpointed_path_digest,
            "one_line_read": (
                "Direct feature leakage and frozen-eval contamination are guarded, "
                "but supported-slice circularity, generator contamination, and "
                "calibration-target coupling still make this path unsafe for a strong "
                "independent efficacy claim."
            ),
        },
        "pinpointed_risk_paths": pinpointed_risk_paths,
        "overall_assessment": {
            "verdict": "guarded_but_not_safe_for_strong_independent_efficacy_claim",
            "summary": (
                "Current synthetic pre/post path is meaningfully guarded against direct feature "
                "leakage and frozen-eval contamination, but it is still unsafe to treat strong "
                "Dataset F fit as independent efficacy evidence because circularity, generator "
                "contamination, and calibration-target coupling remain concentrated in the "
                "supported effect-enriched slice."
            ),
            "principal_safe_families": [
                "leakage_guard",
                "baseline_identical_label_copy",
                "frozen_eval_contamination",
            ],
            "principal_risky_families": [
                "circularity",
                "generator_contamination",
                "calibration_target_coupling",
            ],
            "safe_now": safe_now,
            "risky_now": risky_now,
            "kpi_read": (
                "This path is safer than before on direct leakage and frozen-eval hygiene, but "
                "current synthetic fit still should be read as replay/audit signal rather than "
                "standalone learned-efficacy proof."
            ),
        },
        "validation_issues": validate_synthetic_prepost_path_audit(
            risk_posture={
                "leakage_status": leakage.get("status"),
                "circularity_status": circularity.get("status"),
                "generator_contamination_status": generator_contamination.get("status"),
                "frozen_eval_contamination_status": frozen_eval_contamination.get("status"),
                "calibration_dependence_status": partition_assessment.get(
                    "calibration_dependence_status"
                ),
                "partition_verdict": partition_assessment.get("verdict"),
            },
            evidence_snapshot={
                "forbidden_training_feature_count": leakage_evidence.get(
                    "forbidden_training_feature_count"
                ),
                "exact_reconstruction_rate_pct": circularity_evidence.get(
                    "exact_reconstruction_rate_pct"
                ),
                "supported_mode_top2_match_rate_pct": generator_evidence.get(
                    "supported_mode_top2_match_rate_pct"
                ),
                "shares_path_with_frozen_eval": split_hygiene.get(
                    "shares_path_with_frozen_eval"
                ),
                "exact_line_overlap_count": frozen_eval_evidence.get(
                    "exact_line_overlap_count"
                ),
            },
        ),
    }


def validate_synthetic_prepost_path_audit(
    *,
    risk_posture: dict[str, object],
    evidence_snapshot: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    if risk_posture.get("leakage_status") != "guarded_but_not_zero":
        issues.append("leakage guard status drifted")
    if risk_posture.get("circularity_status") != "high_risk":
        issues.append("circularity status drifted")
    if risk_posture.get("generator_contamination_status") != "high_risk":
        issues.append("generator contamination status drifted")
    if risk_posture.get("frozen_eval_contamination_status") != "low_risk":
        issues.append("frozen-eval contamination status drifted")
    if risk_posture.get("partition_verdict") != "do_not_pool_supported_and_base_clone_validity":
        issues.append("partition validity verdict drifted")
    if risk_posture.get("calibration_dependence_status") != "material":
        issues.append("calibration dependence status drifted")
    if _to_int(evidence_snapshot.get("forbidden_training_feature_count")) != 0:
        issues.append("forbidden training feature count must stay zero")
    if _to_float(evidence_snapshot.get("exact_reconstruction_rate_pct")) != 100.0:
        issues.append("supported exact reconstruction rate must stay 100%")
    if _to_float(evidence_snapshot.get("supported_mode_top2_match_rate_pct")) != 100.0:
        issues.append("supported top2 assignment match rate must stay 100%")
    if bool(evidence_snapshot.get("shares_path_with_frozen_eval")):
        issues.append("synthetic dataset must not share path with frozen eval")
    if _to_int(evidence_snapshot.get("exact_line_overlap_count")) != 0:
        issues.append("synthetic dataset must keep exact line overlap with frozen eval at zero")
    return issues


def render_synthetic_prepost_path_audit_markdown(audit: dict[str, object]) -> str:
    lines = [
        "# synthetic prepost path audit v1",
        "",
        f"- verdict: `{_as_dict(audit.get('overall_assessment')).get('verdict')}`",
        f"- summary: `{_as_dict(audit.get('overall_assessment')).get('summary')}`",
        "",
        "## Readable Summary",
        f"- readable_summary: `{audit.get('readable_summary')}`",
        "",
        "## Risk Posture",
        f"- risk_posture: `{audit.get('risk_posture')}`",
        "",
        "## Evidence Snapshot",
        f"- evidence_snapshot: `{audit.get('evidence_snapshot')}`",
        "",
        "## Pinpointed Risk Paths",
    ]
    for item in _as_list(audit.get("pinpointed_risk_paths")):
        item_dict = _as_dict(item)
        lines.append(
            "- "
            f"{item_dict.get('path')} "
            f"[{item_dict.get('risk_family')}/{item_dict.get('kind')}]: "
            f"{item_dict.get('detail')}"
        )
    overall = _as_dict(audit.get("overall_assessment"))
    lines.extend(["", "## Safe Now"])
    for item in _as_list(overall.get("safe_now")):
        lines.append(f"- {item}")
    lines.extend(["", "## Risky Now"])
    for item in _as_list(overall.get("risky_now")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_synthetic_prepost_path_audit_files(
    *,
    audit: dict[str, object],
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_synthetic_prepost_path_audit_markdown(audit), encoding="utf-8")


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _to_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


__all__ = [
    "build_synthetic_prepost_path_audit",
    "load_json",
    "render_synthetic_prepost_path_audit_markdown",
    "validate_synthetic_prepost_path_audit",
    "write_synthetic_prepost_path_audit_files",
]
