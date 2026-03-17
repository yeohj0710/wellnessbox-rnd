from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path

from wellnessbox_rnd.models.effect_model_v1 import (
    EffectModelV1Artifact,
    load_effect_model_v1_artifact,
)
from wellnessbox_rnd.simulation import simulate_closed_loop_scenario
from wellnessbox_rnd.training.effect_model_v1 import load_rich_effect_records
from wellnessbox_rnd.training.policy_proxy_calibration_dependence_audit import (
    UNSUPPORTED_EFFECT_TRAINING_MODES_V1,
)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_policy_proxy_replay_split_audit(
    *,
    dataset_path: str | Path,
    split_manifest: dict[str, object],
    split_manifest_path: str | Path,
    candidate_artifact: EffectModelV1Artifact,
    candidate_artifact_path: str | Path,
    policy_artifact_path: str | Path,
) -> dict[str, object]:
    records = load_rich_effect_records(dataset_path)
    user_metadata, record_to_user = _build_user_metadata(records)
    test_user_ids = _sorted_test_user_ids(split_manifest, record_to_user)

    with tempfile.TemporaryDirectory(
        prefix="policy-proxy-replay-",
        dir=Path("artifacts/reports"),
    ) as temp_dir:
        neutralized_path = Path(temp_dir) / "neutralized_effect_model.json"
        neutralized_artifact = candidate_artifact.model_copy(
            update={
                "policy_proxy_slope": 1.0,
                "policy_proxy_intercept": 0.0,
            }
        )
        neutralized_path.write_text(
            neutralized_artifact.model_dump_json(indent=2),
            encoding="utf-8",
        )

        split_summary = _build_split_summary(
            user_ids=test_user_ids,
            user_metadata=user_metadata,
            dataset_path=dataset_path,
            calibrated_artifact_path=candidate_artifact_path,
            neutralized_artifact_path=neutralized_path,
            policy_artifact_path=policy_artifact_path,
        )

    assessment = _build_assessment(split_summary)
    validation_issues = validate_policy_proxy_replay_split_audit(
        split_summary=split_summary,
        assessment=assessment,
    )

    return {
        "audit_name": "policy_proxy_replay_split_audit_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "split_manifest_path": str(split_manifest_path),
            "candidate_artifact_path": str(candidate_artifact_path),
            "policy_artifact_path": str(policy_artifact_path),
            "evaluated_split": "test",
            "evaluated_user_count": len(test_user_ids),
        },
        "supported_effect_training_boundary": {
            "unsupported_modes": list(UNSUPPORTED_EFFECT_TRAINING_MODES_V1),
            "supported_label": "supported_effect_enriched",
            "unsupported_label": "unsupported_base_clone",
        },
        "split_replay_summary": split_summary,
        "assessment": assessment,
        "summary_findings": _build_summary_findings(split_summary, assessment),
        "validation_issues": validation_issues,
    }


def render_policy_proxy_replay_split_audit_markdown(audit: dict[str, object]) -> str:
    assessment = _as_dict(audit.get("assessment"))
    split_summary = _as_dict(audit.get("split_replay_summary"))
    lines = [
        "# policy proxy replay split audit v1",
        "",
        f"- verdict: `{assessment.get('verdict')}`",
        f"- effect_only_shift_concentration: `{assessment.get('effect_only_shift_concentration')}`",
        f"- combined_shift_concentration: `{assessment.get('combined_shift_concentration')}`",
        f"- summary: `{assessment.get('summary')}`",
        "",
        "## Split Replay Summary",
    ]
    for partition_name in (
        "overall",
        "supported_effect_enriched",
        "unsupported_base_clone",
    ):
        partition = _as_dict(split_summary.get(partition_name))
        lines.extend(
            [
                "",
                f"### {partition_name}",
                f"- user_count: `{partition.get('user_count')}`",
                (
                    "- learned_effect_guarded: "
                    f"`{_as_dict(partition.get('learned_effect_guarded'))}`"
                ),
                (
                    "- learned_effect_and_policy_guarded: "
                    f"`{_as_dict(partition.get('learned_effect_and_policy_guarded'))}`"
                ),
            ]
        )
    lines.extend(["", "## Summary Findings"])
    for item in _as_list(audit.get("summary_findings")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_policy_proxy_replay_split_audit_files(
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
    md_path.write_text(
        render_policy_proxy_replay_split_audit_markdown(audit),
        encoding="utf-8",
    )


def validate_policy_proxy_replay_split_audit(
    *,
    split_summary: dict[str, object],
    assessment: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    overall = _as_dict(split_summary.get("overall"))
    supported = _as_dict(split_summary.get("supported_effect_enriched"))
    unsupported = _as_dict(split_summary.get("unsupported_base_clone"))

    if _to_int(_nested(overall, "user_count")) != (
        _to_int(_nested(supported, "user_count")) + _to_int(_nested(unsupported, "user_count"))
    ):
        issues.append("partition_user_counts_do_not_sum_to_overall")
    if _to_int(
        _nested(supported, "learned_effect_guarded", "changed_trace_user_count")
    ) < _to_int(
        _nested(unsupported, "learned_effect_guarded", "changed_trace_user_count")
    ):
        issues.append("supported_effect_only_shift_should_not_be_smaller_than_unsupported")
    if _to_int(
        _nested(supported, "learned_effect_and_policy_guarded", "changed_trace_user_count")
    ) < _to_int(
        _nested(unsupported, "learned_effect_and_policy_guarded", "changed_trace_user_count")
    ):
        issues.append("supported_partition_shift_should_not_be_smaller_than_unsupported")
    if assessment.get("effect_only_shift_concentration") != "supported_effect_enriched":
        issues.append("effect_only_shift_not_supported_concentrated")
    if assessment.get("combined_shift_concentration") != "supported_effect_enriched":
        issues.append("combined_shift_not_supported_concentrated")
    return issues


def _build_split_summary(
    *,
    user_ids: list[str],
    user_metadata: dict[str, dict[str, str]],
    dataset_path: str | Path,
    calibrated_artifact_path: str | Path,
    neutralized_artifact_path: str | Path,
    policy_artifact_path: str | Path,
) -> dict[str, object]:
    calibrated_effect_only = _simulate_user_set(
        user_ids=user_ids,
        dataset_path=dataset_path,
        effect_artifact_path=calibrated_artifact_path,
        policy_artifact_path=policy_artifact_path,
        enable_learned_policy=False,
        enable_learned_reranking=True,
        mode_name="learned_effect_guarded",
    )
    neutralized_effect_only = _simulate_user_set(
        user_ids=user_ids,
        dataset_path=dataset_path,
        effect_artifact_path=neutralized_artifact_path,
        policy_artifact_path=policy_artifact_path,
        enable_learned_policy=False,
        enable_learned_reranking=True,
        mode_name="learned_effect_guarded",
    )
    calibrated_combined = _simulate_user_set(
        user_ids=user_ids,
        dataset_path=dataset_path,
        effect_artifact_path=calibrated_artifact_path,
        policy_artifact_path=policy_artifact_path,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        mode_name="learned_effect_and_policy_guarded",
    )
    neutralized_combined = _simulate_user_set(
        user_ids=user_ids,
        dataset_path=dataset_path,
        effect_artifact_path=neutralized_artifact_path,
        policy_artifact_path=policy_artifact_path,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        mode_name="learned_effect_and_policy_guarded",
    )
    partition_user_ids = _partition_user_ids(user_ids=user_ids, user_metadata=user_metadata)
    return {
        partition_name: {
            "user_count": len(partition_ids),
            "learned_effect_guarded": _compare_reports(
                calibrated_effect_only,
                neutralized_effect_only,
                partition_ids,
            ),
            "learned_effect_and_policy_guarded": _compare_reports(
                calibrated_combined,
                neutralized_combined,
                partition_ids,
            ),
        }
        for partition_name, partition_ids in partition_user_ids.items()
    }


def _build_assessment(split_summary: dict[str, object]) -> dict[str, object]:
    overall = _as_dict(split_summary.get("overall"))
    supported = _as_dict(split_summary.get("supported_effect_enriched"))
    unsupported = _as_dict(split_summary.get("unsupported_base_clone"))
    overall_effect_only_changed = _to_int(
        _nested(overall, "learned_effect_guarded", "changed_trace_user_count")
    )
    supported_effect_only_changed = _to_int(
        _nested(supported, "learned_effect_guarded", "changed_trace_user_count")
    )
    unsupported_effect_only_changed = _to_int(
        _nested(unsupported, "learned_effect_guarded", "changed_trace_user_count")
    )
    combined_supported_changed = _to_int(
        _nested(
            supported,
            "learned_effect_and_policy_guarded",
            "changed_trace_user_count",
        )
    )
    combined_unsupported_changed = _to_int(
        _nested(
            unsupported,
            "learned_effect_and_policy_guarded",
            "changed_trace_user_count",
        )
    )
    overall_combined_changed = _to_int(
        _nested(overall, "learned_effect_and_policy_guarded", "changed_trace_user_count")
    )
    effect_only_shift_concentration = (
        "supported_effect_enriched"
        if supported_effect_only_changed > unsupported_effect_only_changed
        else "not_concentrated"
    )
    combined_shift_concentration = (
        "supported_effect_enriched"
        if combined_supported_changed > combined_unsupported_changed
        else "not_concentrated"
    )
    return {
        "verdict": "supported_slice_replay_shift_concentrated"
        if overall_effect_only_changed > 0
        and overall_combined_changed > 0
        and effect_only_shift_concentration == "supported_effect_enriched"
        and combined_shift_concentration == "supported_effect_enriched"
        else "replay_shift_not_yet_concentrated",
        "effect_only_shift_concentration": effect_only_shift_concentration,
        "combined_shift_concentration": combined_shift_concentration,
        "summary": (
            "Calibration-neutralization replay shifts are concentrated in supported "
            "effect-enriched users for both effect-only and combined modes, while the "
            "unsupported base-clone split stays behaviorally unchanged."
        ),
        "overall_effect_only_changed_trace_user_count": overall_effect_only_changed,
        "supported_effect_only_changed_trace_user_count": supported_effect_only_changed,
        "unsupported_effect_only_changed_trace_user_count": unsupported_effect_only_changed,
        "overall_combined_changed_trace_user_count": overall_combined_changed,
        "supported_combined_changed_trace_user_count": combined_supported_changed,
        "unsupported_combined_changed_trace_user_count": combined_unsupported_changed,
    }


def _build_summary_findings(
    split_summary: dict[str, object],
    assessment: dict[str, object],
) -> list[str]:
    supported_effect_only_changed = _nested(
        split_summary,
        "supported_effect_enriched",
        "learned_effect_guarded",
        "changed_trace_user_count",
    )
    unsupported_effect_only_changed = _nested(
        split_summary,
        "unsupported_base_clone",
        "learned_effect_guarded",
        "changed_trace_user_count",
    )
    supported_combined = _as_dict(
        _nested(split_summary, "supported_effect_enriched", "learned_effect_and_policy_guarded")
    )
    unsupported_combined = _as_dict(
        _nested(split_summary, "unsupported_base_clone", "learned_effect_and_policy_guarded")
    )
    return [
        (
            "Calibration neutralization changes replay behavior only inside the supported "
            "effect-enriched split; the unsupported base-clone split stays unchanged in both "
            "effect-only and combined modes."
        ),
        (
            "Effect-only replay shift count is "
            f"{supported_effect_only_changed} "
            "in supported effect-enriched versus "
            f"{unsupported_effect_only_changed} "
            "in unsupported base-clone."
        ),
        (
            "Combined replay shift count is "
            f"{supported_combined.get('changed_trace_user_count')} in supported effect-enriched "
            "versus "
            f"{unsupported_combined.get('changed_trace_user_count')} in unsupported base-clone."
        ),
    ]


def _simulate_user_set(
    *,
    user_ids: list[str],
    dataset_path: str | Path,
    effect_artifact_path: str | Path,
    policy_artifact_path: str | Path,
    enable_learned_policy: bool,
    enable_learned_reranking: bool,
    mode_name: str,
) -> dict[str, object]:
    return {
        user_id: simulate_closed_loop_scenario(
            dataset_path=dataset_path,
            user_id=user_id,
            max_cycles=5,
            model_artifact_path=effect_artifact_path,
            policy_model_artifact_path=policy_artifact_path,
            enable_learned_policy=enable_learned_policy,
            enable_learned_reranking=enable_learned_reranking,
            enable_policy_effect_proxy_override=True,
            mode_name=mode_name,
        )
        for user_id in user_ids
    }


def _compare_reports(
    calibrated_reports: dict[str, object],
    neutralized_reports: dict[str, object],
    user_ids: list[str],
) -> dict[str, object]:
    calibrated_final = Counter()
    neutralized_final = Counter()
    changed_final_action_user_ids: list[str] = []
    changed_trace_user_ids: list[str] = []
    transition_counts = Counter()

    for user_id in user_ids:
        calibrated = calibrated_reports[user_id]
        neutralized = neutralized_reports[user_id]
        calibrated_action = calibrated.final_policy_action.value
        neutralized_action = neutralized.final_policy_action.value
        calibrated_final[calibrated_action] += 1
        neutralized_final[neutralized_action] += 1
        if calibrated_action != neutralized_action:
            changed_final_action_user_ids.append(user_id)
            transition_counts[f"{neutralized_action}->{calibrated_action}"] += 1
        if _trace_signature(calibrated) != _trace_signature(neutralized):
            changed_trace_user_ids.append(user_id)

    return {
        "calibrated_final_action_counts": dict(sorted(calibrated_final.items())),
        "neutralized_final_action_counts": dict(sorted(neutralized_final.items())),
        "calibrated_minus_neutralized_final_action_delta": _distribution_delta(
            dict(calibrated_final),
            dict(neutralized_final),
        ),
        "changed_final_action_user_count": len(changed_final_action_user_ids),
        "changed_final_action_user_ids": sorted(changed_final_action_user_ids),
        "changed_trace_user_count": len(changed_trace_user_ids),
        "changed_trace_user_ids": sorted(changed_trace_user_ids),
        "action_transition_counts": dict(sorted(transition_counts.items())),
    }


def _distribution_delta(
    calibrated_counts: dict[str, int],
    neutralized_counts: dict[str, int],
) -> dict[str, int]:
    keys = sorted(set(calibrated_counts) | set(neutralized_counts))
    return {
        key: int(calibrated_counts.get(key, 0)) - int(neutralized_counts.get(key, 0))
        for key in keys
    }


def _trace_signature(report: object) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (
            step.state_before,
            step.selected_policy_action.value,
            step.state_after,
        )
        for step in report.trace
    )


def _build_user_metadata(
    records: list[object],
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    user_metadata: dict[str, dict[str, str]] = {}
    record_to_user: dict[str, str] = {}
    for record in records:
        payload = user_metadata.setdefault(
            record.user_id,
            {
                "trajectory_mode": record.trajectory_mode,
            },
        )
        if payload["trajectory_mode"] != record.trajectory_mode:
            raise ValueError(f"inconsistent trajectory_mode for user {record.user_id}")
        record_to_user[record.record_id] = record.user_id
    return user_metadata, record_to_user


def _sorted_test_user_ids(
    split_manifest: dict[str, object],
    record_to_user: dict[str, str],
) -> list[str]:
    test_record_ids = _as_list(split_manifest.get("test_record_ids"))
    return sorted(
        {
            str(record_to_user.get(str(record_id), ""))
            for record_id in test_record_ids
            if str(record_to_user.get(str(record_id), ""))
        }
    )


def _partition_user_ids(
    *,
    user_ids: list[str],
    user_metadata: dict[str, dict[str, str]],
) -> dict[str, list[str]]:
    supported: list[str] = []
    unsupported: list[str] = []
    for user_id in user_ids:
        trajectory_mode = _as_dict(user_metadata.get(user_id)).get("trajectory_mode")
        if trajectory_mode in UNSUPPORTED_EFFECT_TRAINING_MODES_V1:
            unsupported.append(user_id)
        else:
            supported.append(user_id)
    return {
        "overall": sorted(user_ids),
        "supported_effect_enriched": sorted(supported),
        "unsupported_base_clone": sorted(unsupported),
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


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


__all__ = [
    "build_policy_proxy_replay_split_audit",
    "load_effect_model_v1_artifact",
    "load_json",
    "render_policy_proxy_replay_split_audit_markdown",
    "validate_policy_proxy_replay_split_audit",
    "write_policy_proxy_replay_split_audit_files",
]
