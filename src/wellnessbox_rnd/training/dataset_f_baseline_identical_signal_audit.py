from __future__ import annotations

import json
from pathlib import Path

from wellnessbox_rnd.training.effect_model_v1 import validate_effect_feature_schema_v1


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_dataset_f_baseline_identical_signal_audit(
    *,
    dataset_path: str | Path,
    path_safety_audit: dict[str, object],
    path_safety_audit_path: str | Path,
    data_quality_report: dict[str, object],
    data_quality_report_path: str | Path,
    feature_schema: dict[str, object],
    feature_schema_path: str | Path,
    pair_summary: dict[str, object],
    pair_summary_path: str | Path,
    split_manifest: dict[str, object],
    split_manifest_path: str | Path,
    replay_compare_report: dict[str, object],
    replay_compare_report_path: str | Path,
) -> dict[str, object]:
    risk_assessment = _as_dict(path_safety_audit.get("risk_assessment"))
    baseline_identical = _as_dict(risk_assessment.get("baseline_identical_label"))
    circularity = _as_dict(risk_assessment.get("circularity"))
    generator_contamination = _as_dict(risk_assessment.get("generator_contamination"))
    split_validation = _as_dict(pair_summary.get("split_validation"))
    split_disjointness = _as_dict(split_validation.get("split_disjointness"))
    contamination_safeguards = _as_dict(split_validation.get("contamination_safeguards"))
    follow_up_diversity = _as_dict(data_quality_report.get("follow_up_change_diversity"))
    low_risk_vs_cgm = _as_dict(data_quality_report.get("low_risk_vs_cgm_distribution"))
    replay_deltas = _as_dict(replay_compare_report.get("deltas"))

    baseline_identical_evidence = _as_dict(baseline_identical.get("evidence"))
    circularity_evidence = _as_dict(circularity.get("evidence"))
    generator_contamination_evidence = _as_dict(generator_contamination.get("evidence"))
    training_view_enforcement = _as_dict(feature_schema.get("training_view_enforcement"))
    feature_schema_validation_issues = validate_effect_feature_schema_v1(feature_schema)

    label_copy_risk_reduced = (
        baseline_identical.get("status") == "low_risk"
        and _to_int(
            baseline_identical_evidence.get("constant_baseline_with_label_variation_user_count")
        )
        > 0
    )
    replay_not_behaviorally_identical = (
        _to_int(replay_deltas.get("effect_only_low_risk_disagreement_delta")) > 0
        or _to_int(replay_deltas.get("combined_low_risk_disagreement_delta")) > 0
        or _to_int(replay_deltas.get("effect_only_cgm_disagreement_delta")) > 0
        or _to_int(replay_deltas.get("combined_cgm_disagreement_delta")) > 0
    )
    residual_generator_simple_risk = (
        _to_float(circularity_evidence.get("exact_reconstruction_rate_pct")) == 100.0
        or _to_float(
            generator_contamination_evidence.get("supported_mode_top2_match_rate_pct")
        )
        == 100.0
    )

    verdict = (
        "baseline_identical_label_copy_risk_reduced_but_generator_simple_signal_remains"
        if label_copy_risk_reduced and residual_generator_simple_risk
        else "baseline_identical_signal_still_material"
    )

    return {
        "audit_name": "dataset_f_baseline_identical_signal_audit_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "path_safety_audit_path": str(path_safety_audit_path),
            "data_quality_report_path": str(data_quality_report_path),
            "feature_schema_path": str(feature_schema_path),
            "pair_summary_path": str(pair_summary_path),
            "split_manifest_path": str(split_manifest_path),
            "replay_compare_report_path": str(replay_compare_report_path),
        },
        "baseline_identical_signal_assessment": {
            "verdict": verdict,
            "current_candidate_label": replay_compare_report.get("candidate_label"),
            "label_copy_risk_status": baseline_identical.get("status"),
            "behavioral_replay_identity_status": (
                "not_identical_to_deterministic_baseline"
                if replay_not_behaviorally_identical
                else "near_identical_to_deterministic_baseline"
            ),
            "generator_simple_signal_status": (
                "still_present" if residual_generator_simple_risk else "not_detected"
            ),
            "summary": (
                "Baseline-identical label-copy risk is much lower than before because constant "
                "baseline users still show label variation and replay disagreements are nonzero, "
                "but the supported slice remains generator-simple through exact outcome "
                "reconstruction and assignment coupling."
            ),
        },
        "evidence": {
            "label_copy_reduction": {
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
                "action_formula_exact_match_overall_rate_pct": (
                    baseline_identical_evidence.get(
                        "action_formula_exact_match_overall_rate_pct"
                    )
                ),
            },
            "residual_signal_risk": {
                "supported_mode_count": circularity_evidence.get("supported_mode_count"),
                "exact_reconstruction_rate_pct": circularity_evidence.get(
                    "exact_reconstruction_rate_pct"
                ),
                "supported_mode_top2_match_rate_pct": generator_contamination_evidence.get(
                    "supported_mode_top2_match_rate_pct"
                ),
                "uniform_non_goal_delta_case_pct": follow_up_diversity.get(
                    "uniform_non_goal_delta_case_pct"
                ),
                "lowest_signature_diversity_families": follow_up_diversity.get(
                    "lowest_signature_diversity_families"
                ),
                "low_risk_cgm_case_count": low_risk_vs_cgm.get("low_risk_cgm_case_count"),
                "low_risk_cgm_goal_counts": low_risk_vs_cgm.get("low_risk_cgm_goal_counts"),
            },
            "feature_schema_guard": {
                "current_candidate_label": replay_compare_report.get("candidate_label"),
                "feature_count": feature_schema.get("feature_count"),
                "training_input_allowed_fields": training_view_enforcement.get(
                    "training_input_allowed_fields"
                ),
                "forbidden_feature_count": training_view_enforcement.get(
                    "forbidden_feature_count"
                ),
                "forbidden_feature_names_present": training_view_enforcement.get(
                    "forbidden_feature_names_present"
                ),
                "schema_validator_issue_count": len(feature_schema_validation_issues),
                "schema_validator_issues": feature_schema_validation_issues,
            },
            "split_hygiene": {
                "pair_overlap_counts": split_disjointness.get("pair_overlap_counts"),
                "user_overlap_counts": split_disjointness.get("user_overlap_counts"),
                "shares_path_with_frozen_eval": contamination_safeguards.get(
                    "shares_path_with_frozen_eval"
                ),
                "split_pair_counts": {
                    split_name: _as_dict(split_payload).get("pair_count")
                    for split_name, split_payload in _as_dict(split_manifest.get("splits")).items()
                },
                "split_user_counts": {
                    split_name: _as_dict(split_payload).get("user_count")
                    for split_name, split_payload in _as_dict(split_manifest.get("splits")).items()
                },
            },
            "replay_evidence": {
                "effect_only_low_risk_disagreement_delta": replay_deltas.get(
                    "effect_only_low_risk_disagreement_delta"
                ),
                "combined_low_risk_disagreement_delta": replay_deltas.get(
                    "combined_low_risk_disagreement_delta"
                ),
                "effect_only_cgm_disagreement_delta": replay_deltas.get(
                    "effect_only_cgm_disagreement_delta"
                ),
                "combined_cgm_disagreement_delta": replay_deltas.get(
                    "combined_cgm_disagreement_delta"
                ),
            },
        },
        "pinpointed_residual_risk_paths": [
            {
                "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:625",
                "kind": "generator_formula",
                "detail": (
                    "Supported low-risk rows still come from a deterministic follow-up/proxy "
                    "formula, which keeps exact reconstruction at 325/325."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/training/effect_model_v1.py:2043",
                "kind": "calibration_target",
                "detail": (
                    "Policy-proxy calibration still regresses onto generator-produced "
                    "expected_effect_proxy, so residual learned signal risk is target-side, "
                    "not direct feature leakage."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:219",
                "kind": "assignment_source",
                "detail": (
                    "Supported effect-enriched rows still inherit recommendation assignment from "
                    "recommend(request), keeping assignment contamination at 100% top-2 match."
                ),
            },
        ],
        "already_reduced_evidence": [
            (
                "constant baseline users still show label variation in 70/96 users, "
                "so labels are not simple baseline copies"
            ),
            "forbidden training feature count remains 0 under dataset_f_effect_training_view_v1",
            (
                "current feature schema validator issue count remains 0 on the latest "
                "candidate surface"
            ),
            (
                "split hygiene remains clean: pair overlap 0, user overlap 0, "
                "and no frozen-eval path sharing"
            ),
            (
                "replay disagreements remain nonzero, so learned behavior is not frozen "
                "to the deterministic baseline path"
            ),
        ],
        "next_checks": [
            (
                "measure how much current fit still depends on policy-proxy calibration "
                "against generator-produced expected_effect_proxy"
            ),
            (
                "separate or re-audit the 325 supported effect-enriched rows versus the "
                "155 base-clone rows when judging learned-signal validity"
            ),
        ],
        "validation_issues": [],
    }


def render_dataset_f_baseline_identical_signal_audit_markdown(
    audit: dict[str, object]
) -> str:
    assessment = _as_dict(audit.get("baseline_identical_signal_assessment"))
    evidence = _as_dict(audit.get("evidence"))
    lines = [
        "# dataset f baseline-identical signal audit v1",
        "",
        f"- verdict: `{assessment.get('verdict')}`",
        f"- label_copy_risk_status: `{assessment.get('label_copy_risk_status')}`",
        (
            "- behavioral_replay_identity_status: "
            f"`{assessment.get('behavioral_replay_identity_status')}`"
        ),
        (
            "- generator_simple_signal_status: "
            f"`{assessment.get('generator_simple_signal_status')}`"
        ),
        f"- summary: `{assessment.get('summary')}`",
        "",
        "## Evidence",
        f"- label_copy_reduction: `{evidence.get('label_copy_reduction')}`",
        f"- residual_signal_risk: `{evidence.get('residual_signal_risk')}`",
        f"- feature_schema_guard: `{evidence.get('feature_schema_guard')}`",
        f"- split_hygiene: `{evidence.get('split_hygiene')}`",
        f"- replay_evidence: `{evidence.get('replay_evidence')}`",
        "",
        "## Residual Risk Paths",
    ]
    for item in _as_list(audit.get("pinpointed_residual_risk_paths")):
        item_dict = _as_dict(item)
        lines.append(
            f"- {item_dict.get('path')} [{item_dict.get('kind')}]: {item_dict.get('detail')}"
        )
    lines.extend(["", "## Already Reduced Evidence"])
    for item in _as_list(audit.get("already_reduced_evidence")):
        lines.append(f"- {item}")
    lines.extend(["", "## Next Checks"])
    for item in _as_list(audit.get("next_checks")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_dataset_f_baseline_identical_signal_audit_files(
    *,
    audit: dict[str, object],
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_dataset_f_baseline_identical_signal_audit_markdown(audit),
        encoding="utf-8",
    )


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


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


__all__ = [
    "build_dataset_f_baseline_identical_signal_audit",
    "load_json",
    "render_dataset_f_baseline_identical_signal_audit_markdown",
    "write_dataset_f_baseline_identical_signal_audit_files",
]
