from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_dataset_pairs_v1,
    load_rich_effect_records,
)

UNSUPPORTED_EFFECT_TRAINING_MODES_V1: tuple[str, ...] = (
    "reduce_side_effect",
    "safety_recheck_high_risk",
)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_dataset_f_partition_validity_audit(
    *,
    dataset_path: str | Path,
    path_safety_audit: dict[str, object],
    path_safety_audit_path: str | Path,
    calibration_dependence_audit: dict[str, object],
    calibration_dependence_audit_path: str | Path,
    pair_summary: dict[str, object],
    pair_summary_path: str | Path,
) -> dict[str, object]:
    rows = build_effect_dataset_pairs_v1(load_rich_effect_records(dataset_path))
    supported_rows = [
        row
        for row in rows
        if row.provenance.trajectory_mode not in UNSUPPORTED_EFFECT_TRAINING_MODES_V1
    ]
    unsupported_rows = [
        row
        for row in rows
        if row.provenance.trajectory_mode in UNSUPPORTED_EFFECT_TRAINING_MODES_V1
    ]

    path_risks = _as_dict(path_safety_audit.get("risk_assessment"))
    circularity = _as_dict(path_risks.get("circularity"))
    generator_contamination = _as_dict(path_risks.get("generator_contamination"))
    leakage = _as_dict(path_risks.get("leakage"))
    baseline_identical = _as_dict(path_risks.get("baseline_identical_label"))
    circularity_evidence = _as_dict(circularity.get("evidence"))
    contamination_evidence = _as_dict(generator_contamination.get("evidence"))
    calibration_assessment = _as_dict(calibration_dependence_audit.get("assessment"))
    calibration_artifacts = _as_dict(calibration_dependence_audit.get("artifact_summaries"))
    candidate_summary = _as_dict(calibration_artifacts.get("candidate"))
    baseline_summary = _as_dict(calibration_artifacts.get("baseline"))
    training_view_contract = _as_dict(pair_summary.get("training_view_contract"))

    supported_partition = _build_partition_summary(
        partition_name="supported_effect_enriched",
        rows=supported_rows,
        validity_role="generator_circular_effect_fit_surface",
        pair_summary=pair_summary,
        path_evidence={
            "circularity_status": circularity.get("status"),
            "exact_reconstruction_rate_pct": circularity_evidence.get(
                "exact_reconstruction_rate_pct"
            ),
            "assignment_top2_match_rate_pct": contamination_evidence.get(
                "supported_mode_top2_match_rate_pct"
            ),
            "candidate_test_calibration_gain": _nested(
                candidate_summary,
                "splits",
                "test",
                "supported_effect_enriched",
                "policy_proxy_calibration_gain",
            ),
            "baseline_test_calibration_gain": _nested(
                baseline_summary,
                "splits",
                "test",
                "supported_effect_enriched",
                "policy_proxy_calibration_gain",
            ),
        },
        interpretation=(
            "Use this partition as a bounded replay/audit surface only. It is the place where "
            "effect-rich variation lives, but it is also the place where exact generator "
            "reconstruction, assignment coupling, and calibration dependence are strongest."
        ),
    )
    unsupported_partition = _build_partition_summary(
        partition_name="unsupported_base_clone",
        rows=unsupported_rows,
        validity_role="high_risk_base_clone_control_surface",
        pair_summary=pair_summary,
        path_evidence={
            "circularity_status": "not_effect_enriched",
            "exact_reconstruction_rate_pct": None,
            "assignment_top2_match_rate_pct": contamination_evidence.get(
                "unsupported_mode_top2_match_rate_pct"
            ),
            "candidate_test_calibration_gain": _nested(
                candidate_summary,
                "splits",
                "test",
                "unsupported_base_clone",
                "policy_proxy_calibration_gain",
            ),
            "baseline_test_calibration_gain": _nested(
                baseline_summary,
                "splits",
                "test",
                "unsupported_base_clone",
                "policy_proxy_calibration_gain",
            ),
        },
        interpretation=(
            "Do not pool this partition with supported effect-enriched rows when judging learned "
            "effect validity. It behaves like a base-clone/high-risk control surface with safety "
            "and tolerability outcomes, not like the main effect-rich fit surface."
        ),
    )

    assessment = {
        "verdict": "do_not_pool_supported_and_base_clone_validity",
        "summary": (
            "The current Dataset F path should be judged as two separate validity stories: "
            "supported effect-enriched rows are replay-useful but generator-circular, while "
            "unsupported base-clone rows are high-risk control-like rows that should not be "
            "combined into one learned-efficacy claim."
        ),
        "supported_partition_role": supported_partition["validity_role"],
        "unsupported_partition_role": unsupported_partition["validity_role"],
        "leakage_status": leakage.get("status"),
        "baseline_identical_label_status": baseline_identical.get("status"),
        "calibration_dependence_status": calibration_assessment.get("dependence_status"),
        "calibration_dependence_concentration": calibration_assessment.get(
            "concentration_status"
        ),
    }

    validation_issues = validate_dataset_f_partition_validity_audit(
        supported_partition=supported_partition,
        unsupported_partition=unsupported_partition,
        pair_summary=pair_summary,
        training_view_contract=training_view_contract,
    )

    return {
        "audit_name": "dataset_f_partition_validity_audit_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "path_safety_audit_path": str(path_safety_audit_path),
            "calibration_dependence_audit_path": str(calibration_dependence_audit_path),
            "pair_summary_path": str(pair_summary_path),
        },
        "assessment": assessment,
        "shared_training_view_contract": {
            "contract_version": training_view_contract.get("contract_version"),
            "training_input_allowed_fields": training_view_contract.get(
                "training_input_allowed_fields"
            ),
            "training_input_forbidden_fields": training_view_contract.get(
                "training_input_forbidden_fields"
            ),
        },
        "partitions": {
            "supported_effect_enriched": supported_partition,
            "unsupported_base_clone": unsupported_partition,
        },
        "summary_findings": [
            (
                "Supported effect-enriched rows are all low-risk, have no adverse events, and "
                "carry the strongest replay signal, but they are also exactly reconstructible "
                "and fully assignment-coupled."
            ),
            (
                "Unsupported base-clone rows are all high-risk, contain all adverse events, and "
                "show weak or negative calibration benefit, so they should be treated as a "
                "separate control-like validity surface."
            ),
            (
                "Because the shared training-view contract spans both partitions, the next "
                "highest-ROI step is to split the audit view, not widen features or rerun training."
            ),
        ],
        "validation_issues": validation_issues,
    }


def render_dataset_f_partition_validity_audit_markdown(audit: dict[str, object]) -> str:
    assessment = _as_dict(audit.get("assessment"))
    partitions = _as_dict(audit.get("partitions"))
    supported = _as_dict(partitions.get("supported_effect_enriched"))
    unsupported = _as_dict(partitions.get("unsupported_base_clone"))
    supported_path_evidence = _as_dict(supported.get("path_evidence"))
    unsupported_path_evidence = _as_dict(unsupported.get("path_evidence"))
    lines = [
        "# dataset f partition validity audit v1",
        "",
        f"- verdict: `{assessment.get('verdict')}`",
        f"- summary: `{assessment.get('summary')}`",
        "",
        "## Supported Effect-Enriched",
        f"- validity_role: `{supported.get('validity_role')}`",
        f"- case_count: `{supported.get('case_count')}`",
        f"- user_count: `{supported.get('user_count')}`",
        f"- risk_tier_counts: `{supported.get('risk_tier_counts')}`",
        f"- next_action_counts: `{supported.get('next_action_counts')}`",
        f"- response_family_counts: `{supported.get('response_family_counts')}`",
        f"- adverse_event_count: `{supported.get('adverse_event_count')}`",
        f"- mean_aggregate_delta: `{supported.get('mean_aggregate_delta')}`",
        f"- mean_expected_effect_proxy: `{supported.get('mean_expected_effect_proxy')}`",
        f"- path_evidence: `{supported_path_evidence}`",
        f"- interpretation: `{supported.get('interpretation')}`",
        "",
        "## Unsupported Base-Clone",
        f"- validity_role: `{unsupported.get('validity_role')}`",
        f"- case_count: `{unsupported.get('case_count')}`",
        f"- user_count: `{unsupported.get('user_count')}`",
        f"- risk_tier_counts: `{unsupported.get('risk_tier_counts')}`",
        f"- next_action_counts: `{unsupported.get('next_action_counts')}`",
        f"- response_family_counts: `{unsupported.get('response_family_counts')}`",
        f"- adverse_event_count: `{unsupported.get('adverse_event_count')}`",
        f"- mean_aggregate_delta: `{unsupported.get('mean_aggregate_delta')}`",
        f"- mean_expected_effect_proxy: `{unsupported.get('mean_expected_effect_proxy')}`",
        f"- path_evidence: `{unsupported_path_evidence}`",
        f"- interpretation: `{unsupported.get('interpretation')}`",
        "",
        "## Summary Findings",
    ]
    for item in _as_list(audit.get("summary_findings")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_dataset_f_partition_validity_audit_files(
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
        render_dataset_f_partition_validity_audit_markdown(audit),
        encoding="utf-8",
    )


def validate_dataset_f_partition_validity_audit(
    *,
    supported_partition: dict[str, object],
    unsupported_partition: dict[str, object],
    pair_summary: dict[str, object],
    training_view_contract: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    expected_case_count = _to_int(pair_summary.get("case_count"))
    observed_case_count = _to_int(supported_partition.get("case_count")) + _to_int(
        unsupported_partition.get("case_count")
    )
    if observed_case_count != expected_case_count:
        issues.append("partition case counts must sum to the Dataset F case count")
    if _to_int(_nested(supported_partition, "risk_tier_counts", "low")) != _to_int(
        supported_partition.get("case_count")
    ):
        issues.append("supported effect-enriched partition must stay fully low-risk")
    if _to_int(_nested(unsupported_partition, "risk_tier_counts", "high")) != _to_int(
        unsupported_partition.get("case_count")
    ):
        issues.append("unsupported base-clone partition must stay fully high-risk")
    if (
        _to_float(
            _nested(
                supported_partition,
                "path_evidence",
                "exact_reconstruction_rate_pct",
            )
        )
        != 100.0
    ):
        issues.append("supported effect-enriched partition must keep 100% exact reconstruction")
    if (
        _to_float(
            _nested(
                supported_partition,
                "path_evidence",
                "assignment_top2_match_rate_pct",
            )
        )
        != 100.0
    ):
        issues.append("supported effect-enriched partition must keep 100% top2 assignment match")
    if (
        _to_float(
            _nested(
                supported_partition,
                "path_evidence",
                "candidate_test_calibration_gain",
            )
        )
        <= 0.0
    ):
        issues.append(
            "supported effect-enriched candidate test calibration gain must stay positive"
        )
    if (
        _to_float(
            _nested(
                unsupported_partition,
                "path_evidence",
                "candidate_test_calibration_gain",
            )
        )
        >= 0.0
    ):
        issues.append(
            "unsupported base-clone candidate test calibration gain must stay non-positive"
        )
    if training_view_contract.get("contract_version") != "dataset_f_effect_training_view_v1":
        issues.append("training-view contract version drifted")
    return issues


def _build_partition_summary(
    *,
    partition_name: str,
    rows: list[object],
    validity_role: str,
    pair_summary: dict[str, object],
    path_evidence: dict[str, object],
    interpretation: str,
) -> dict[str, object]:
    aggregate_deltas = [row.follow_up.aggregate_z - row.baseline.aggregate_z for row in rows]
    return {
        "partition_name": partition_name,
        "validity_role": validity_role,
        "case_count": len(rows),
        "user_count": len({row.user_id for row in rows}),
        "goal_counts": dict(sorted(Counter(row.goal for row in rows).items())),
        "risk_tier_counts": dict(sorted(Counter(row.risk_tier for row in rows).items())),
        "next_action_counts": dict(sorted(Counter(row.next_action for row in rows).items())),
        "response_family_counts": dict(
            sorted(Counter(row.response_profile.response_family for row in rows).items())
        ),
        "trajectory_mode_counts": dict(
            sorted(Counter(row.provenance.trajectory_mode for row in rows).items())
        ),
        "modality_counts": {
            "wearable": sum(int(row.input_flags.wearable) for row in rows),
            "cgm": sum(int(row.input_flags.cgm) for row in rows),
            "genetic": sum(int(row.input_flags.genetic) for row in rows),
            "nhis": sum(int(row.input_flags.nhis) for row in rows),
        },
        "adverse_event_count": sum(int(row.adverse_event) for row in rows),
        "mean_aggregate_delta": round(
            sum(aggregate_deltas) / len(aggregate_deltas) if aggregate_deltas else 0.0,
            6,
        ),
        "mean_expected_effect_proxy": round(
            sum(row.expected_effect_proxy for row in rows) / len(rows) if rows else 0.0,
            6,
        ),
        "shared_training_input_allowed_fields": _as_dict(
            pair_summary.get("training_view_contract")
        ).get("training_input_allowed_fields"),
        "path_evidence": path_evidence,
        "interpretation": interpretation,
    }


def _nested(payload: dict[str, object], *keys: str) -> object:
    current: object = payload
    for key in keys:
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
    return 0.0


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


__all__ = [
    "build_dataset_f_partition_validity_audit",
    "load_json",
    "render_dataset_f_partition_validity_audit_markdown",
    "validate_dataset_f_partition_validity_audit",
    "write_dataset_f_partition_validity_audit_files",
]
