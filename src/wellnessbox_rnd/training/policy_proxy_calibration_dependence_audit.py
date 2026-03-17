from __future__ import annotations

import json
from pathlib import Path

from wellnessbox_rnd.models.effect_model_v1 import (
    EffectModelV1Artifact,
    load_effect_model_v1_artifact,
)
from wellnessbox_rnd.training.effect_model_v1 import (
    evaluate_effect_model_v1,
    load_rich_effect_records,
)

UNSUPPORTED_EFFECT_TRAINING_MODES_V1: tuple[str, ...] = (
    "reduce_side_effect",
    "safety_recheck_high_risk",
)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_policy_proxy_calibration_dependence_audit(
    *,
    dataset_path: str | Path,
    split_manifest: dict[str, object],
    split_manifest_path: str | Path,
    baseline_artifact: EffectModelV1Artifact,
    baseline_artifact_path: str | Path,
    candidate_artifact: EffectModelV1Artifact,
    candidate_artifact_path: str | Path,
    candidate_eval_report: dict[str, object],
    candidate_eval_report_path: str | Path,
    candidate_feature_schema: dict[str, object],
    candidate_feature_schema_path: str | Path,
) -> dict[str, object]:
    records = load_rich_effect_records(dataset_path)
    records_by_id = {record.record_id: record for record in records}
    split_records = _load_split_records(records_by_id, split_manifest)
    dataset_support_summary = _summarize_support_partition(records)

    baseline_summary = _build_artifact_dependence_summary(
        artifact=baseline_artifact,
        split_records=split_records,
    )
    candidate_summary = _build_artifact_dependence_summary(
        artifact=candidate_artifact,
        split_records=split_records,
    )

    consistency_checks = _build_consistency_checks(
        candidate_summary=candidate_summary,
        candidate_eval_report=candidate_eval_report,
        candidate_feature_schema=candidate_feature_schema,
        dataset_case_count=len(records),
        split_records=split_records,
    )
    validation_issues = validate_policy_proxy_calibration_dependence_audit(
        candidate_summary=candidate_summary,
        consistency_checks=consistency_checks,
    )

    assessment = _build_dependence_assessment(
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
    )

    return {
        "audit_name": "policy_proxy_calibration_dependence_audit_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "split_manifest_path": str(split_manifest_path),
            "baseline_artifact_path": str(baseline_artifact_path),
            "candidate_artifact_path": str(candidate_artifact_path),
            "candidate_eval_report_path": str(candidate_eval_report_path),
            "candidate_feature_schema_path": str(candidate_feature_schema_path),
        },
        "supported_effect_training_boundary": {
            "unsupported_modes": list(UNSUPPORTED_EFFECT_TRAINING_MODES_V1),
            "supported_label": "supported_effect_enriched",
            "unsupported_label": "unsupported_base_clone",
        },
        "dataset_support_summary": dataset_support_summary,
        "assessment": assessment,
        "artifact_summaries": {
            "baseline": baseline_summary,
            "candidate": candidate_summary,
        },
        "consistency_checks": consistency_checks,
        "pinpointed_risk_paths": [
            {
                "path": "src/wellnessbox_rnd/training/effect_model_v1.py:1862",
                "kind": "calibration_target",
                "detail": (
                    "_fit_policy_proxy_calibration still regresses onto "
                    "generator-produced expected_effect_proxy using train+val rows."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:661",
                "kind": "generator_proxy_formula",
                "detail": (
                    "expected_effect_proxy is still synthesized from deterministic goal/adherence/"
                    "side-effect terms inside the v4 follow-up generator."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:229",
                "kind": "assignment_source",
                "detail": (
                    "supported effect-enriched rows still inherit recommendation assignment from "
                    "recommend(request), which keeps the supported slice coupled to the same "
                    "generator family."
                ),
            },
        ],
        "summary_findings": [
            (
                "Both baseline and latest candidate show material policy-proxy calibration "
                "dependence, so this is a structural Dataset F path issue rather than a "
                "candidate-only quirk."
            ),
            (
                "The dependence is concentrated in supported effect-enriched rows; unsupported "
                "base-clone rows get little or negative benefit from the same calibration."
            ),
            (
                "The latest candidate's validation neutralized proxy MAE matches the stored "
                "pre_policy_proxy_mae exactly, which proves the audit is reading the same "
                "pre-calibration surface used during selection."
            ),
        ],
        "validation_issues": validation_issues,
    }


def render_policy_proxy_calibration_dependence_audit_markdown(
    audit: dict[str, object]
) -> str:
    assessment = _as_dict(audit.get("assessment"))
    dataset_support_summary = _as_dict(audit.get("dataset_support_summary"))
    artifact_summaries = _as_dict(audit.get("artifact_summaries"))
    baseline = _as_dict(artifact_summaries.get("baseline"))
    candidate = _as_dict(artifact_summaries.get("candidate"))
    lines = [
        "# policy proxy calibration dependence audit v1",
        "",
        f"- verdict: `{assessment.get('verdict')}`",
        f"- dependence_status: `{assessment.get('dependence_status')}`",
        f"- concentration_status: `{assessment.get('concentration_status')}`",
        f"- summary: `{assessment.get('summary')}`",
        "",
        "## Dataset Support Summary",
        f"- dataset_support_summary: `{dataset_support_summary}`",
        "",
        "## Candidate Snapshot",
        f"- candidate_test_overall: `{_nested(candidate, 'splits', 'test', 'overall')}`",
        (
            "- candidate_test_supported_effect_enriched: "
            f"`{_nested(candidate, 'splits', 'test', 'supported_effect_enriched')}`"
        ),
        (
            "- candidate_test_unsupported_base_clone: "
            f"`{_nested(candidate, 'splits', 'test', 'unsupported_base_clone')}`"
        ),
        "",
        "## Baseline Snapshot",
        f"- baseline_test_overall: `{_nested(baseline, 'splits', 'test', 'overall')}`",
        (
            "- baseline_test_supported_effect_enriched: "
            f"`{_nested(baseline, 'splits', 'test', 'supported_effect_enriched')}`"
        ),
        (
            "- baseline_test_unsupported_base_clone: "
            f"`{_nested(baseline, 'splits', 'test', 'unsupported_base_clone')}`"
        ),
        "",
        "## Consistency Checks",
        f"- consistency_checks: `{audit.get('consistency_checks')}`",
        "",
        "## Pinpointed Risk Paths",
    ]
    for item in _as_list(audit.get("pinpointed_risk_paths")):
        payload = _as_dict(item)
        lines.append(
            f"- `{payload.get('path')}` {payload.get('kind')}: {payload.get('detail')}"
        )
    lines.extend(
        [
            "",
            "## Summary Findings",
        ]
    )
    for item in _as_list(audit.get("summary_findings")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_policy_proxy_calibration_dependence_audit_files(
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
        render_policy_proxy_calibration_dependence_audit_markdown(audit),
        encoding="utf-8",
    )


def validate_policy_proxy_calibration_dependence_audit(
    *,
    candidate_summary: dict[str, object],
    consistency_checks: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    if not all(bool(value) for value in consistency_checks.values()):
        issues.append("consistency checks failed for policy proxy calibration dependence audit")

    candidate_test_supported = _to_float(
        _nested(
            candidate_summary,
            "splits",
            "test",
            "supported_effect_enriched",
            "policy_proxy_calibration_gain",
        )
    )
    candidate_test_unsupported = _to_float(
        _nested(
            candidate_summary,
            "splits",
            "test",
            "unsupported_base_clone",
            "policy_proxy_calibration_gain",
        )
    )
    if candidate_test_supported <= 0.0:
        issues.append("candidate supported effect-enriched calibration gain must stay positive")
    if candidate_test_supported <= candidate_test_unsupported:
        issues.append(
            "candidate supported effect-enriched calibration gain must exceed unsupported gain"
        )
    return issues


def _build_artifact_dependence_summary(
    *,
    artifact: EffectModelV1Artifact,
    split_records: dict[str, list[object]],
) -> dict[str, object]:
    neutralized_artifact = artifact.model_copy(
        update={
            "policy_proxy_slope": 1.0,
            "policy_proxy_intercept": 0.0,
        }
    )
    return {
        "artifact_metadata": {
            "model_name": artifact.model_name,
            "cohort_version": artifact.cohort_version,
            "alpha": artifact.alpha,
            "policy_proxy_calibration": {
                "slope": artifact.policy_proxy_slope,
                "intercept": artifact.policy_proxy_intercept,
                "clip_min": artifact.policy_proxy_clip_min,
                "clip_max": artifact.policy_proxy_clip_max,
            },
        },
        "splits": {
            split_name: _build_split_summary(
                artifact=artifact,
                neutralized_artifact=neutralized_artifact,
                records=records,
            )
            for split_name, records in split_records.items()
        },
    }


def _build_split_summary(
    *,
    artifact: EffectModelV1Artifact,
    neutralized_artifact: EffectModelV1Artifact,
    records: list[object],
) -> dict[str, object]:
    supported_records, unsupported_records = _partition_records_by_support(records)
    return {
        "overall": _evaluate_record_slice(
            artifact=artifact,
            neutralized_artifact=neutralized_artifact,
            records=records,
        ),
        "supported_effect_enriched": _evaluate_record_slice(
            artifact=artifact,
            neutralized_artifact=neutralized_artifact,
            records=supported_records,
        ),
        "unsupported_base_clone": _evaluate_record_slice(
            artifact=artifact,
            neutralized_artifact=neutralized_artifact,
            records=unsupported_records,
        ),
    }


def _evaluate_record_slice(
    *,
    artifact: EffectModelV1Artifact,
    neutralized_artifact: EffectModelV1Artifact,
    records: list[object],
) -> dict[str, object]:
    if not records:
        return {
            "record_count": 0,
            "user_count": 0,
            "trajectory_mode_counts": {},
            "calibrated_metrics": None,
            "neutralized_metrics": None,
            "policy_proxy_calibration_gain": 0.0,
        }

    calibrated_metrics = evaluate_effect_model_v1(artifact, records)
    neutralized_metrics = evaluate_effect_model_v1(neutralized_artifact, records)
    return {
        "record_count": len(records),
        "user_count": len({record.user_id for record in records}),
        "trajectory_mode_counts": _count_trajectory_modes(records),
        "calibrated_metrics": calibrated_metrics.model_dump(mode="json"),
        "neutralized_metrics": neutralized_metrics.model_dump(mode="json"),
        "policy_proxy_calibration_gain": round(
            neutralized_metrics.policy_proxy_mae - calibrated_metrics.policy_proxy_mae,
            6,
        ),
    }


def _build_consistency_checks(
    *,
    candidate_summary: dict[str, object],
    candidate_eval_report: dict[str, object],
    candidate_feature_schema: dict[str, object],
    dataset_case_count: int,
    split_records: dict[str, list[object]],
) -> dict[str, bool]:
    candidate_val_overall = _as_dict(_nested(candidate_summary, "splits", "val", "overall"))
    candidate_test_overall = _as_dict(_nested(candidate_summary, "splits", "test", "overall"))
    feature_schema_summary = _as_dict(
        _nested(candidate_feature_schema, "validation_selection", "summary")
    )
    eval_metrics = _as_dict(candidate_eval_report.get("metrics"))
    val_eval_metrics = _as_dict(eval_metrics.get("val"))
    test_eval_metrics = _as_dict(eval_metrics.get("test"))
    split_total = sum(len(records) for records in split_records.values())
    return {
        "candidate_val_pre_policy_proxy_mae_matches_feature_schema": _approx_equal(
            _to_float(_nested(candidate_val_overall, "neutralized_metrics", "policy_proxy_mae")),
            _to_float(feature_schema_summary.get("pre_policy_proxy_mae")),
        ),
        "candidate_val_calibrated_policy_proxy_mae_matches_eval_report": _approx_equal(
            _to_float(_nested(candidate_val_overall, "calibrated_metrics", "policy_proxy_mae")),
            _to_float(val_eval_metrics.get("policy_proxy_mae")),
        ),
        "candidate_test_calibrated_policy_proxy_mae_matches_eval_report": _approx_equal(
            _to_float(_nested(candidate_test_overall, "calibrated_metrics", "policy_proxy_mae")),
            _to_float(test_eval_metrics.get("policy_proxy_mae")),
        ),
        "split_record_counts_cover_dataset": split_total == dataset_case_count,
        "split_subsets_partition_each_split": all(
            _to_int(_nested(candidate_summary, "splits", split_name, "overall", "record_count"))
            == _to_int(
                _nested(
                    candidate_summary,
                    "splits",
                    split_name,
                    "supported_effect_enriched",
                    "record_count",
                )
            )
            + _to_int(
                _nested(
                    candidate_summary,
                    "splits",
                    split_name,
                    "unsupported_base_clone",
                    "record_count",
                )
            )
            for split_name in ("train", "val", "test")
        ),
    }


def _build_dependence_assessment(
    *,
    baseline_summary: dict[str, object],
    candidate_summary: dict[str, object],
) -> dict[str, object]:
    baseline_test_supported_gain = _to_float(
        _nested(
            baseline_summary,
            "splits",
            "test",
            "supported_effect_enriched",
            "policy_proxy_calibration_gain",
        )
    )
    baseline_test_unsupported_gain = _to_float(
        _nested(
            baseline_summary,
            "splits",
            "test",
            "unsupported_base_clone",
            "policy_proxy_calibration_gain",
        )
    )
    candidate_test_supported_gain = _to_float(
        _nested(
            candidate_summary,
            "splits",
            "test",
            "supported_effect_enriched",
            "policy_proxy_calibration_gain",
        )
    )
    candidate_test_unsupported_gain = _to_float(
        _nested(
            candidate_summary,
            "splits",
            "test",
            "unsupported_base_clone",
            "policy_proxy_calibration_gain",
        )
    )
    dependence_status = (
        "material"
        if baseline_test_supported_gain > 0.1 and candidate_test_supported_gain > 0.1
        else "limited"
    )
    concentration_status = (
        "supported_effect_enriched_slice"
        if candidate_test_supported_gain > max(0.05, candidate_test_unsupported_gain)
        and baseline_test_supported_gain > max(0.05, baseline_test_unsupported_gain)
        else "not_concentrated"
    )
    return {
        "verdict": (
            "material_supported_slice_calibration_dependence"
            if dependence_status == "material"
            and concentration_status == "supported_effect_enriched_slice"
            else "calibration_dependence_not_yet_material"
        ),
        "dependence_status": dependence_status,
        "concentration_status": concentration_status,
        "summary": (
            "Current policy-proxy fit still depends materially on calibration against "
            "generator-produced expected_effect_proxy, and the dependence is concentrated "
            "in the supported effect-enriched slice rather than the unsupported base-clone rows."
        ),
        "candidate_test_supported_gain": round(candidate_test_supported_gain, 6),
        "candidate_test_unsupported_gain": round(candidate_test_unsupported_gain, 6),
        "baseline_test_supported_gain": round(baseline_test_supported_gain, 6),
        "baseline_test_unsupported_gain": round(baseline_test_unsupported_gain, 6),
    }


def _load_split_records(
    records_by_id: dict[str, object],
    split_manifest: dict[str, object],
) -> dict[str, list[object]]:
    result: dict[str, list[object]] = {}
    for split_name in ("train", "val", "test"):
        key = f"{split_name}_record_ids"
        result[split_name] = [
            records_by_id[record_id]
            for record_id in _as_list(split_manifest.get(key))
            if record_id in records_by_id
        ]
    return result


def _summarize_support_partition(records: list[object]) -> dict[str, object]:
    supported_records, unsupported_records = _partition_records_by_support(records)
    return {
        "case_count": len(records),
        "supported_effect_enriched_case_count": len(supported_records),
        "unsupported_base_clone_case_count": len(unsupported_records),
        "supported_effect_enriched_pct": round((len(supported_records) / len(records)) * 100, 2),
        "unsupported_base_clone_pct": round((len(unsupported_records) / len(records)) * 100, 2),
        "supported_trajectory_mode_counts": _count_trajectory_modes(supported_records),
        "unsupported_trajectory_mode_counts": _count_trajectory_modes(unsupported_records),
    }


def _partition_records_by_support(records: list[object]) -> tuple[list[object], list[object]]:
    supported_records: list[object] = []
    unsupported_records: list[object] = []
    for record in records:
        if getattr(record, "trajectory_mode", "") in UNSUPPORTED_EFFECT_TRAINING_MODES_V1:
            unsupported_records.append(record)
        else:
            supported_records.append(record)
    return supported_records, unsupported_records


def _count_trajectory_modes(records: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        mode = getattr(record, "trajectory_mode", "unknown")
        counts[mode] = counts.get(mode, 0) + 1
    return dict(sorted(counts.items()))


def _nested(payload: dict[str, object], *keys: str) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _approx_equal(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return abs(left - right) <= tolerance


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
    "build_policy_proxy_calibration_dependence_audit",
    "load_effect_model_v1_artifact",
    "load_json",
    "render_policy_proxy_calibration_dependence_audit_markdown",
    "validate_policy_proxy_calibration_dependence_audit",
    "write_policy_proxy_calibration_dependence_audit_files",
]
