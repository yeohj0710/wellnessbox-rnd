from pathlib import Path

from wellnessbox_rnd.evals.parser_case_id_mismatch_freshness_audit import (
    build_parser_case_id_mismatch_freshness_audit,
    render_parser_case_id_mismatch_freshness_audit_markdown,
    validate_parser_case_id_mismatch_freshness_audit,
    write_parser_case_id_mismatch_freshness_audit_files,
)


def test_build_parser_case_id_mismatch_freshness_audit_keeps_gate_closed(
    tmp_path: Path,
) -> None:
    older_source = tmp_path / "older_source.json"
    newer_decision = tmp_path / "decision.json"
    older_source.write_text('{"ok": true}', encoding="utf-8")
    decision_payload = (
        '{"source_artifacts":{"parser_report_path":"'
        + older_source.as_posix()
        + '"},"decision_gate":{"decision":"'
        + "mismatch_not_blocking_current_kpi_interpretation"
        + '","blocks_kpi_interpretation":false}}'
    )
    newer_decision.write_text(
        decision_payload,
        encoding="utf-8",
    )

    audit = build_parser_case_id_mismatch_freshness_audit(
        mismatch_decision={
            "source_artifacts": {
                "parser_report_path": str(older_source),
            },
            "decision_gate": {
                "decision": "mismatch_not_blocking_current_kpi_interpretation",
                "blocks_kpi_interpretation": False,
            },
        },
        mismatch_decision_path=newer_decision,
    )

    assert audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert audit["freshness_gate"]["reopen_case_id_mismatch_review"] is False
    assert (
        audit["freshness_gate"]["decision"]
        == "no_new_parser_source_since_mismatch_decision"
    )
    assert "no_newer_parser_source_artifacts" in audit["freshness_gate"]["reason_codes"]
    assert validate_parser_case_id_mismatch_freshness_audit(audit) == []


def test_write_parser_case_id_mismatch_freshness_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "parser_case_id_mismatch_freshness_audit_v1",
        "freshness_gate": {
            "decision": "no_new_parser_source_since_mismatch_decision",
        },
        "evidence_summary": {
            "newer_source_count": 0,
        },
        "decision_rationale": ["No new parser source artifact exists."],
        "summary_findings": ["Keep the non-blocking parser mismatch interpretation."],
        "validation_issues": [],
    }

    json_path = tmp_path / "parser_case_id_mismatch_freshness_audit_v1.json"
    md_path = tmp_path / "parser_case_id_mismatch_freshness_audit_v1.md"
    write_parser_case_id_mismatch_freshness_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_parser_case_id_mismatch_freshness_audit_markdown(audit)
    assert "## freshness gate" in markdown
    assert "## summary findings" in markdown
