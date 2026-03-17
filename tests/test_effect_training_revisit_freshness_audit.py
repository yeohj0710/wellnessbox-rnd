from pathlib import Path

from wellnessbox_rnd.evals.effect_training_revisit_freshness_audit import (
    build_effect_training_revisit_freshness_audit,
    render_effect_training_revisit_freshness_audit_markdown,
    validate_effect_training_revisit_freshness_audit,
    write_effect_training_revisit_freshness_audit_files,
)


def test_build_effect_training_revisit_freshness_audit_keeps_gate_closed(
    tmp_path: Path,
) -> None:
    older_source = tmp_path / "older_source.json"
    newer_stability = tmp_path / "stability.json"
    older_source.write_text('{"ok": true}', encoding="utf-8")
    stability_payload = (
        '{"source_artifacts":{"baseline_candidate_summary_path":"'
        + older_source.as_posix()
        + '"},"decision_gate":{"decision":"current_defer_decision_still_holds",'
        + '"material_replay_change_detected":false}}'
    )
    newer_stability.write_text(
        stability_payload,
        encoding="utf-8",
    )

    audit = build_effect_training_revisit_freshness_audit(
        stability_decision={
            "source_artifacts": {
                "baseline_candidate_summary_path": str(older_source),
            },
            "decision_gate": {
                "decision": "current_defer_decision_still_holds",
                "material_replay_change_detected": False,
            },
        },
        stability_decision_path=newer_stability,
    )

    assert audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert audit["freshness_gate"]["revisit_gate_can_be_reopened"] is False
    assert (
        audit["freshness_gate"]["decision"]
        == "no_new_replay_source_since_stability_decision"
    )
    assert "no_newer_replay_source_artifacts" in audit["freshness_gate"]["reason_codes"]
    assert validate_effect_training_revisit_freshness_audit(audit) == []


def test_write_effect_training_revisit_freshness_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "effect_training_revisit_freshness_audit_v1",
        "freshness_gate": {
            "decision": "no_new_replay_source_since_stability_decision",
        },
        "evidence_summary": {
            "newer_source_count": 0,
        },
        "decision_rationale": ["No new replay source artifact exists."],
        "summary_findings": ["Keep the defer gate closed."],
        "validation_issues": [],
    }

    json_path = tmp_path / "effect_training_revisit_freshness_audit_v1.json"
    md_path = tmp_path / "effect_training_revisit_freshness_audit_v1.md"
    write_effect_training_revisit_freshness_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_effect_training_revisit_freshness_audit_markdown(audit)
    assert "## freshness gate" in markdown
    assert "## summary findings" in markdown
