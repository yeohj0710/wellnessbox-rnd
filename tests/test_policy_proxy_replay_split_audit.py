from pathlib import Path

from wellnessbox_rnd.training.policy_proxy_replay_split_audit import (
    build_policy_proxy_replay_split_audit,
    load_effect_model_v1_artifact,
    load_json,
    render_policy_proxy_replay_split_audit_markdown,
    write_policy_proxy_replay_split_audit_files,
)


def test_build_policy_proxy_replay_split_audit_shows_supported_combined_concentration() -> None:
    audit = build_policy_proxy_replay_split_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        split_manifest=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        split_manifest_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        candidate_artifact=load_effect_model_v1_artifact(
            "artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        candidate_artifact_path=(
            "artifacts/models/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        policy_artifact_path="artifacts/models/policy_model_v1.json",
    )

    assessment = audit["assessment"]
    overall_effect_only = audit["split_replay_summary"]["overall"]["learned_effect_guarded"]
    supported_combined = audit["split_replay_summary"]["supported_effect_enriched"][
        "learned_effect_and_policy_guarded"
    ]
    unsupported_combined = audit["split_replay_summary"]["unsupported_base_clone"][
        "learned_effect_and_policy_guarded"
    ]

    assert assessment["verdict"] == "supported_slice_replay_shift_concentrated"
    assert assessment["effect_only_shift_concentration"] == "supported_effect_enriched"
    assert overall_effect_only["changed_trace_user_count"] > 0
    assert audit["split_replay_summary"]["unsupported_base_clone"]["learned_effect_guarded"][
        "changed_trace_user_count"
    ] == 0
    assert supported_combined["changed_trace_user_count"] > unsupported_combined[
        "changed_trace_user_count"
    ]
    assert audit["validation_issues"] == []


def test_write_policy_proxy_replay_split_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = build_policy_proxy_replay_split_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        split_manifest=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        split_manifest_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        candidate_artifact=load_effect_model_v1_artifact(
            "artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        candidate_artifact_path=(
            "artifacts/models/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        policy_artifact_path="artifacts/models/policy_model_v1.json",
    )

    json_path = tmp_path / "policy_proxy_replay_split_audit_v1.json"
    md_path = tmp_path / "policy_proxy_replay_split_audit_v1.md"
    write_policy_proxy_replay_split_audit_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_policy_proxy_replay_split_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# policy proxy replay split audit v1" in markdown
    assert "Split Replay Summary" in markdown
    assert "Summary Findings" in markdown
