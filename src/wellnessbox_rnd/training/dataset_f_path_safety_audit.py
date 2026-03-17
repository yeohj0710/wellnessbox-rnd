from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import (
    _build_effect_rich_follow_up_v4,
    _label_effect_rich_action_v4,
)
from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_dataset_pairs_v1,
    load_rich_effect_records,
)

SUPPORTED_EFFECT_RICH_MODES: tuple[str, ...] = (
    "threshold_continue_primary",
    "threshold_monitor_secondary",
    "threshold_reopt_edge",
    "threshold_cgm_balance",
    "threshold_delayed_flip",
    "threshold_duration_sensitive",
    "threshold_adherence_recovery",
)


def build_dataset_f_path_safety_audit(
    *,
    dataset_path: str | Path,
    pair_summary_path: str | Path,
    feature_schema_path: str | Path,
    eval_report_path: str | Path,
    frozen_eval_dataset_path: str | Path = "data/frozen_eval/frozen_eval_v1.jsonl",
) -> dict[str, object]:
    dataset_file = Path(dataset_path)
    pair_summary_file = Path(pair_summary_path)
    feature_schema_file = Path(feature_schema_path)
    eval_report_file = Path(eval_report_path)
    frozen_eval_file = Path(frozen_eval_dataset_path)

    records = load_rich_effect_records(dataset_file)
    rows = build_effect_dataset_pairs_v1(records)
    pair_summary = json.loads(pair_summary_file.read_text(encoding="utf-8"))
    feature_schema = json.loads(feature_schema_file.read_text(encoding="utf-8"))
    eval_report = json.loads(eval_report_file.read_text(encoding="utf-8"))

    supported_modes = set(SUPPORTED_EFFECT_RICH_MODES)
    supported_records = [
        record for record in records if record.trajectory_mode in supported_modes
    ]
    unsupported_records = [
        record for record in records if record.trajectory_mode not in supported_modes
    ]

    generator_reconstruction = _build_generator_reconstruction_summary(
        supported_records=supported_records,
        total_record_count=len(records),
    )
    action_reconstruction = _build_action_reconstruction_summary(records)
    recommendation_alignment = _build_recommendation_alignment_summary(records)
    baseline_label_drift = _build_baseline_label_drift_summary(records)
    frozen_eval_separation = _build_frozen_eval_separation_summary(
        dataset_file=dataset_file,
        frozen_eval_file=frozen_eval_file,
        pair_summary=pair_summary,
    )

    training_view_contract = pair_summary["training_view_contract"]
    feature_enforcement = feature_schema["training_view_enforcement"]
    leakage_findings = [
        {
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:141",
            "kind": "contract",
            "detail": (
                "dataset_f_effect_training_view_v1 keeps training inputs on "
                "goal/baseline/input_flags/recommended_set/period and forbids follow-up "
                "outcome-side fields."
            ),
        },
        {
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1714",
            "kind": "feature_path",
            "detail": (
                "build_effect_training_feature_dict_v1 emits only baseline and intervention "
                "assignment features; direct outcome-side proxy features are absent."
            ),
        },
        {
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1637",
            "kind": "calibration_target",
            "detail": (
                "_fit_policy_proxy_calibration still calibrates against generator-produced "
                "expected_effect_proxy, so leakage is reduced at input time but circular "
                "target coupling remains."
            ),
        },
    ]
    circularity_findings = [
        {
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:207",
            "kind": "generator_entrypoint",
            "detail": (
                "_build_effect_rich_user_records_v4 constructs low-risk effect-enriched "
                "records by rerunning recommend(request) before generating outcomes."
            ),
        },
        {
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:625",
            "kind": "generator_formula",
            "detail": (
                "_build_effect_rich_follow_up_v4 deterministically maps baseline, request, "
                "regimen, adherence_proxy, side_effect_proxy, and step to follow-up outcomes "
                "and expected_effect_proxy."
            ),
        },
        {
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1637",
            "kind": "calibration_target",
            "detail": (
                "policy proxy calibration regresses predicted aggregate delta directly onto "
                "record.expected_effect_proxy from the synthetic generator."
            ),
        },
    ]
    baseline_label_findings = [
        {
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:765",
            "kind": "label_formula",
            "detail": (
                "_label_effect_rich_action_v4 thresholds step and generator-side proxies; "
                "labels are not copied from baseline snapshots."
            ),
        },
        {
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:245",
            "kind": "pair_contract",
            "detail": (
                "Dataset F pair rows preserve both baseline and follow-up, allowing audit of "
                "whether labels drift despite constant baseline."
            ),
        },
    ]
    generator_contamination_findings = [
        {
            "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:219",
            "kind": "assignment_source",
            "detail": (
                "effect-enriched rows source recommendation candidates from recommend(request), "
                "so regimen assignment is coupled to the same recommender family used elsewhere."
            ),
        },
        {
            "path": "scripts/train_effect_model_v3.py:1",
            "kind": "training_entrypoint",
            "detail": (
                "training consumes the synthetic dataset path directly and therefore inherits "
                "the generator's recommendation assignment choices."
            ),
        },
    ]
    frozen_eval_findings = [
        {
            "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1044",
            "kind": "contamination_guard",
            "detail": (
                "Dataset F split validation explicitly rejects source paths that match the "
                "frozen-eval dataset path."
            ),
        },
        {
            "path": "scripts/run_eval.py:11",
            "kind": "eval_entrypoint",
            "detail": "Frozen eval defaults to data/frozen_eval/frozen_eval_v1.jsonl.",
        },
    ]

    leakage_status = (
        "guarded_but_not_zero"
        if feature_enforcement["forbidden_feature_count"] == 0
        and not training_view_contract["issues"]
        else "unsafe"
    )
    circularity_status = (
        "high_risk"
        if generator_reconstruction["exact_reconstruction_rate_pct"] == 100.0
        else "moderate_risk"
    )
    baseline_identical_status = (
        "low_risk"
        if baseline_label_drift["constant_baseline_with_label_variation_user_count"] > 0
        else "moderate_risk"
    )
    generator_contamination_status = (
        "high_risk"
        if recommendation_alignment["supported_mode_top2_match_rate_pct"] == 100.0
        else "moderate_risk"
    )
    frozen_eval_status = (
        "low_risk"
        if not frozen_eval_separation["shares_path_with_frozen_eval"]
        and frozen_eval_separation["exact_line_overlap_count"] == 0
        else "unsafe"
    )

    overall = {
        "highest_risk_family": "circularity",
        "highest_risk_summary": (
            "The current Dataset F training path no longer exposes direct outcome-side "
            "features, but the effect-enriched slice remains generator-circular because "
            "follow-up outcomes and policy proxy are exactly reproducible from the synthetic "
            "generator path."
        ),
        "safest_family": "frozen_eval_contamination",
        "kpi_interpretation": (
            "This path looks safer against direct feature leakage and frozen-eval contamination "
            "than before, but it is not yet safe enough to treat strong synthetic fit as "
            "independent efficacy evidence."
        ),
    }

    return {
        "audit_name": "dataset_f_path_safety_audit_v2",
        "scope": {
            "dataset_path": dataset_file.as_posix(),
            "pair_summary_path": pair_summary_file.as_posix(),
            "feature_schema_path": feature_schema_file.as_posix(),
            "eval_report_path": eval_report_file.as_posix(),
            "frozen_eval_dataset_path": frozen_eval_file.as_posix(),
        },
        "dataset_summary": {
            "case_count": len(records),
            "user_count": len({record.user_id for record in records}),
            "pair_row_count": len(rows),
            "supported_effect_enriched_record_count": len(supported_records),
            "unsupported_or_base_clone_record_count": len(unsupported_records),
            "supported_effect_enriched_mode_counts": _count_string_values(
                record.trajectory_mode for record in supported_records
            ),
            "unsupported_or_base_clone_mode_counts": _count_string_values(
                record.trajectory_mode for record in unsupported_records
            ),
        },
        "risk_assessment": {
            "leakage": {
                "status": leakage_status,
                "evidence": {
                    "training_view_contract_version": training_view_contract["contract_version"],
                    "training_view_contract_issue_count": len(training_view_contract["issues"]),
                    "forbidden_training_feature_count": feature_enforcement[
                        "forbidden_feature_count"
                    ],
                    "forbidden_training_feature_names_present": feature_enforcement[
                        "forbidden_feature_names_present"
                    ],
                    "training_input_allowed_fields": training_view_contract[
                        "training_input_allowed_fields"
                    ],
                    "training_input_forbidden_fields": training_view_contract[
                        "training_input_forbidden_fields"
                    ],
                },
                "pinpointed_paths": leakage_findings,
            },
            "circularity": {
                "status": circularity_status,
                "evidence": generator_reconstruction,
                "pinpointed_paths": circularity_findings,
            },
            "baseline_identical_label": {
                "status": baseline_identical_status,
                "evidence": {
                    **baseline_label_drift,
                    "action_formula_exact_match_overall_count": action_reconstruction[
                        "exact_match_count"
                    ],
                    "action_formula_exact_match_overall_rate_pct": action_reconstruction[
                        "exact_match_rate_pct"
                    ],
                },
                "pinpointed_paths": baseline_label_findings,
            },
            "generator_contamination": {
                "status": generator_contamination_status,
                "evidence": recommendation_alignment,
                "pinpointed_paths": generator_contamination_findings,
            },
            "frozen_eval_contamination": {
                "status": frozen_eval_status,
                "evidence": frozen_eval_separation,
                "pinpointed_paths": frozen_eval_findings,
            },
        },
        "current_training_path_evidence": {
            "feature_count": feature_schema["feature_count"],
            "test_metrics": eval_report["metrics"]["test"],
            "training_view_enforcement": feature_enforcement,
        },
        "overall_assessment": overall,
    }


def render_dataset_f_path_safety_audit_markdown(audit: dict[str, object]) -> str:
    scope = _as_dict(audit["scope"])
    dataset_summary = _as_dict(audit["dataset_summary"])
    current_training_path = _as_dict(audit["current_training_path_evidence"])
    overall = _as_dict(audit["overall_assessment"])
    risk_assessment = _as_dict(audit["risk_assessment"])

    lines = [
        "# dataset f path safety audit v2",
        "",
        "## Scope",
        f"- dataset_path: `{scope['dataset_path']}`",
        f"- pair_summary_path: `{scope['pair_summary_path']}`",
        f"- feature_schema_path: `{scope['feature_schema_path']}`",
        f"- eval_report_path: `{scope['eval_report_path']}`",
        f"- frozen_eval_dataset_path: `{scope['frozen_eval_dataset_path']}`",
        "",
        "## Dataset Summary",
        f"- case_count: `{dataset_summary['case_count']}`",
        f"- user_count: `{dataset_summary['user_count']}`",
        (
            "- supported_effect_enriched_record_count: "
            f"`{dataset_summary['supported_effect_enriched_record_count']}`"
        ),
        (
            "- unsupported_or_base_clone_record_count: "
            f"`{dataset_summary['unsupported_or_base_clone_record_count']}`"
        ),
        (
            "- supported_effect_enriched_mode_counts: "
            f"`{dataset_summary['supported_effect_enriched_mode_counts']}`"
        ),
        (
            "- unsupported_or_base_clone_mode_counts: "
            f"`{dataset_summary['unsupported_or_base_clone_mode_counts']}`"
        ),
        "",
        "## Current Training Path",
        f"- feature_count: `{current_training_path['feature_count']}`",
        f"- test_metrics: `{current_training_path['test_metrics']}`",
        (
            "- training_view_enforcement: "
            f"`{current_training_path['training_view_enforcement']}`"
        ),
        "",
        "## Risk Assessment",
    ]
    for risk_name in (
        "leakage",
        "circularity",
        "baseline_identical_label",
        "generator_contamination",
        "frozen_eval_contamination",
    ):
        risk = _as_dict(risk_assessment[risk_name])
        lines.append(f"### {risk_name}")
        lines.append(f"- status: `{risk['status']}`")
        lines.append(f"- evidence: `{risk['evidence']}`")
        for finding in risk["pinpointed_paths"]:
            finding_dict = _as_dict(finding)
            lines.append(
                f"- {finding_dict['path']} [{finding_dict['kind']}]: {finding_dict['detail']}"
            )
        lines.append("")

    lines.extend(
        [
            "## Overall Assessment",
            f"- highest_risk_family: `{overall['highest_risk_family']}`",
            f"- highest_risk_summary: `{overall['highest_risk_summary']}`",
            f"- safest_family: `{overall['safest_family']}`",
            f"- kpi_interpretation: `{overall['kpi_interpretation']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_dataset_f_path_safety_audit_files(
    *,
    audit: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(render_dataset_f_path_safety_audit_markdown(audit), encoding="utf-8")


def _build_generator_reconstruction_summary(
    *,
    supported_records: list,
    total_record_count: int,
) -> dict[str, object]:
    exact_follow_up_count = 0
    exact_delta_count = 0
    exact_proxy_count = 0
    exact_all_count = 0
    for record in supported_records:
        follow_up_pro, delta_z_by_domain, expected_effect_proxy = _build_effect_rich_follow_up_v4(
            baseline_pro=record.baseline_pro,
            request=record.request,
            regimen=record.regimen,
            step=record.trajectory_step,
            adherence_proxy=record.adherence_proxy,
            side_effect_proxy=record.side_effect_proxy,
            mode=record.trajectory_mode,
        )
        if follow_up_pro == record.follow_up_pro:
            exact_follow_up_count += 1
        if delta_z_by_domain == record.delta_z_by_domain:
            exact_delta_count += 1
        if expected_effect_proxy == record.expected_effect_proxy:
            exact_proxy_count += 1
        if (
            follow_up_pro == record.follow_up_pro
            and delta_z_by_domain == record.delta_z_by_domain
            and expected_effect_proxy == record.expected_effect_proxy
        ):
            exact_all_count += 1

    supported_count = len(supported_records)
    return {
        "supported_mode_count": supported_count,
        "exact_follow_up_reconstruction_count": exact_follow_up_count,
        "exact_delta_reconstruction_count": exact_delta_count,
        "exact_policy_proxy_reconstruction_count": exact_proxy_count,
        "exact_full_reconstruction_count": exact_all_count,
        "exact_reconstruction_rate_pct": _rate(exact_all_count, supported_count),
        "unsupported_mode_count": total_record_count - supported_count,
    }


def _build_action_reconstruction_summary(records: list) -> dict[str, object]:
    exact_match_count = 0
    mismatch_counts: Counter[str] = Counter()
    for record in records:
        predicted_action = _label_effect_rich_action_v4(
            step=record.trajectory_step,
            expected_effect_proxy=record.expected_effect_proxy,
            adherence_proxy=record.adherence_proxy,
            side_effect_proxy=record.side_effect_proxy,
        )
        if predicted_action == record.labels.next_action:
            exact_match_count += 1
        else:
            mismatch_counts[record.trajectory_mode] += 1
    return {
        "exact_match_count": exact_match_count,
        "exact_match_rate_pct": _rate(exact_match_count, len(records)),
        "mismatch_mode_counts": dict(sorted(mismatch_counts.items())),
    }


def _build_recommendation_alignment_summary(records: list) -> dict[str, object]:
    supported_modes = set(SUPPORTED_EFFECT_RICH_MODES)
    overall_top2_match = 0
    supported_top2_match = 0
    unsupported_top2_match = 0
    mismatch_examples: list[dict[str, object]] = []
    for record in records:
        response = recommend(record.request)
        top2 = [item.ingredient_key for item in response.recommendations[:2]]
        regimen_keys = [item.ingredient_key for item in record.regimen[:2]]
        if top2 == regimen_keys:
            overall_top2_match += 1
            if record.trajectory_mode in supported_modes:
                supported_top2_match += 1
            else:
                unsupported_top2_match += 1
        elif len(mismatch_examples) < 5:
            mismatch_examples.append(
                {
                    "record_id": record.record_id,
                    "trajectory_mode": record.trajectory_mode,
                    "recommended_top2": top2,
                    "dataset_regimen_top2": regimen_keys,
                }
            )

    supported_count = sum(record.trajectory_mode in supported_modes for record in records)
    unsupported_count = len(records) - supported_count
    return {
        "overall_top2_match_count": overall_top2_match,
        "overall_top2_match_rate_pct": _rate(overall_top2_match, len(records)),
        "supported_mode_top2_match_count": supported_top2_match,
        "supported_mode_top2_match_rate_pct": _rate(supported_top2_match, supported_count),
        "unsupported_mode_top2_match_count": unsupported_top2_match,
        "unsupported_mode_top2_match_rate_pct": _rate(unsupported_top2_match, unsupported_count),
        "mismatch_examples": mismatch_examples,
    }


def _build_baseline_label_drift_summary(records: list) -> dict[str, object]:
    by_user: dict[str, list] = {}
    for record in records:
        by_user.setdefault(record.user_id, []).append(record)

    constant_baseline_users = 0
    constant_baseline_with_label_variation = 0
    constant_baseline_without_label_variation = 0
    varying_label_examples: list[dict[str, object]] = []
    for user_id, user_records in sorted(by_user.items()):
        baseline_snapshots = {record.baseline_pro.model_dump_json() for record in user_records}
        label_values = [record.labels.next_action.value for record in sorted(
            user_records, key=lambda item: item.trajectory_step
        )]
        if len(baseline_snapshots) == 1:
            constant_baseline_users += 1
            if len(set(label_values)) > 1:
                constant_baseline_with_label_variation += 1
                if len(varying_label_examples) < 5:
                    varying_label_examples.append(
                        {
                            "user_id": user_id,
                            "trajectory_modes": sorted(
                                {record.trajectory_mode for record in user_records}
                            ),
                            "label_sequence": label_values,
                        }
                    )
            else:
                constant_baseline_without_label_variation += 1
    return {
        "constant_baseline_user_count": constant_baseline_users,
        "constant_baseline_with_label_variation_user_count": (
            constant_baseline_with_label_variation
        ),
        "constant_baseline_without_label_variation_user_count": (
            constant_baseline_without_label_variation
        ),
        "constant_baseline_with_label_variation_rate_pct": _rate(
            constant_baseline_with_label_variation,
            constant_baseline_users,
        ),
        "varying_label_examples": varying_label_examples,
    }


def _build_frozen_eval_separation_summary(
    *,
    dataset_file: Path,
    frozen_eval_file: Path,
    pair_summary: dict[str, object],
) -> dict[str, object]:
    dataset_bytes = dataset_file.read_bytes()
    frozen_eval_bytes = frozen_eval_file.read_bytes()
    dataset_lines = {
        line for line in dataset_file.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    frozen_eval_lines = {
        line for line in frozen_eval_file.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    contamination_safeguards = _as_dict(pair_summary["split_validation"])[
        "contamination_safeguards"
    ]
    return {
        "shares_path_with_frozen_eval": contamination_safeguards["shares_path_with_frozen_eval"],
        "source_dataset_path": contamination_safeguards["source_dataset_path"],
        "frozen_eval_dataset_path": contamination_safeguards["frozen_eval_dataset_path"],
        "source_dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "frozen_eval_dataset_sha256": hashlib.sha256(frozen_eval_bytes).hexdigest(),
        "exact_line_overlap_count": len(dataset_lines & frozen_eval_lines),
        "source_line_count": len(dataset_lines),
        "frozen_eval_line_count": len(frozen_eval_lines),
    }


def _count_string_values(values) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        counts[str(value)] += 1
    return dict(sorted(counts.items()))


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "SUPPORTED_EFFECT_RICH_MODES",
    "build_dataset_f_path_safety_audit",
    "render_dataset_f_path_safety_audit_markdown",
    "write_dataset_f_path_safety_audit_files",
]
