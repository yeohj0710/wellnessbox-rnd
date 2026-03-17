import os
from pathlib import Path

from wellnessbox_rnd.evals.bone_joint_weakest_family_freshness_audit import (
    build_bone_joint_weakest_family_freshness_audit,
    render_bone_joint_weakest_family_freshness_audit_markdown,
    validate_bone_joint_weakest_family_freshness_audit,
    write_bone_joint_weakest_family_freshness_audit_files,
)


def test_build_bone_joint_weakest_family_freshness_audit_detects_newer_source(
    tmp_path: Path,
) -> None:
    older_decision = tmp_path / "decision.json"
    newer_source = tmp_path / "newer_source.json"
    older_decision.write_text(
        '{"source_artifacts":{"weakest_slice_summary_path":"'
        + newer_source.as_posix()
        + '"},"decision_gate":{"decision":"keep_explicit_empty_anchor",'
        + '"keep_explicit_empty_anchor":true}}',
        encoding="utf-8",
    )
    newer_source.write_text('{"ok": true}', encoding="utf-8")
    decision_mtime = older_decision.stat().st_mtime
    os.utime(newer_source, (decision_mtime + 10, decision_mtime + 10))

    audit = build_bone_joint_weakest_family_freshness_audit(
        bone_joint_decision={
            "source_artifacts": {
                "weakest_slice_summary_path": str(newer_source),
            },
            "decision_gate": {
                "decision": "keep_explicit_empty_anchor",
                "keep_explicit_empty_anchor": True,
            },
        },
        bone_joint_decision_path=older_decision,
    )

    assert audit["freshness_gate"]["newer_source_artifact_detected"] is True
    assert audit["freshness_gate"]["reopen_bone_joint_review"] is True
    assert (
        audit["freshness_gate"]["decision"]
        == "newer_bone_joint_source_detected_recheck_empty_anchor"
    )
    assert (
        "newer_bone_joint_source_artifact_detected"
        in audit["freshness_gate"]["reason_codes"]
    )
    assert validate_bone_joint_weakest_family_freshness_audit(audit) == []


def test_write_bone_joint_weakest_family_freshness_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "bone_joint_weakest_family_freshness_audit_v1",
        "freshness_gate": {
            "decision": "newer_bone_joint_source_detected_recheck_empty_anchor",
        },
        "evidence_summary": {
            "newer_source_count": 1,
        },
        "decision_rationale": ["A newer source artifact exists."],
        "summary_findings": ["Recheck the empty-anchor decision."],
        "validation_issues": [],
    }

    json_path = tmp_path / "bone_joint_weakest_family_freshness_audit_v1.json"
    md_path = tmp_path / "bone_joint_weakest_family_freshness_audit_v1.md"
    write_bone_joint_weakest_family_freshness_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_bone_joint_weakest_family_freshness_audit_markdown(audit)
    assert "## freshness gate" in markdown
    assert "## summary findings" in markdown
