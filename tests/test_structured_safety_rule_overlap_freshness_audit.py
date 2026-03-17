from pathlib import Path

from wellnessbox_rnd.evals.structured_safety_rule_overlap_freshness_audit import (
    build_structured_safety_rule_overlap_freshness_audit,
    render_structured_safety_rule_overlap_freshness_audit_markdown,
    validate_structured_safety_rule_overlap_freshness_audit,
    write_structured_safety_rule_overlap_freshness_audit_files,
)


def test_build_structured_safety_rule_overlap_freshness_audit_keeps_gate_closed(
    tmp_path: Path,
) -> None:
    older_source = tmp_path / "older_source.json"
    newer_decision = tmp_path / "decision.json"
    older_source.write_text('{"ok": true}', encoding="utf-8")
    decision_payload = (
        '{"source_artifacts":{"weakest_slice_audit_path":"'
        + older_source.as_posix()
        + '"},"decision_gate":{"decision":"'
        + "partial_rule_overlap_not_blocking_current_kpi_interpretation"
        + '","blocks_kpi_interpretation":false}}'
    )
    newer_decision.write_text(
        decision_payload,
        encoding="utf-8",
    )

    audit = build_structured_safety_rule_overlap_freshness_audit(
        overlap_decision={
            "source_artifacts": {
                "weakest_slice_audit_path": str(older_source),
            },
            "decision_gate": {
                "decision": "partial_rule_overlap_not_blocking_current_kpi_interpretation",
                "blocks_kpi_interpretation": False,
            },
        },
        overlap_decision_path=newer_decision,
    )

    assert audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert audit["freshness_gate"]["reopen_overlap_review"] is False
    assert (
        audit["freshness_gate"]["decision"]
        == "no_new_safety_source_since_overlap_decision"
    )
    assert "no_newer_safety_source_artifacts" in audit["freshness_gate"]["reason_codes"]
    assert validate_structured_safety_rule_overlap_freshness_audit(audit) == []


def test_write_structured_safety_rule_overlap_freshness_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "structured_safety_rule_overlap_freshness_audit_v1",
        "freshness_gate": {
            "decision": "no_new_safety_source_since_overlap_decision",
        },
        "evidence_summary": {
            "newer_source_count": 0,
        },
        "decision_rationale": ["No new safety source artifact exists."],
        "summary_findings": ["Keep the non-blocking overlap interpretation."],
        "validation_issues": [],
    }

    json_path = tmp_path / "structured_safety_rule_overlap_freshness_audit_v1.json"
    md_path = tmp_path / "structured_safety_rule_overlap_freshness_audit_v1.md"
    write_structured_safety_rule_overlap_freshness_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_structured_safety_rule_overlap_freshness_audit_markdown(audit)
    assert "## freshness gate" in markdown
    assert "## summary findings" in markdown
