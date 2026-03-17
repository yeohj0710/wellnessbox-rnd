from pathlib import Path

from wellnessbox_rnd.evals.chat_optional_rerun_freshness_audit import (
    build_chat_optional_rerun_freshness_audit,
    render_chat_optional_rerun_freshness_audit_markdown,
    validate_chat_optional_rerun_freshness_audit,
    write_chat_optional_rerun_freshness_audit_files,
)


def test_build_chat_optional_rerun_freshness_audit_keeps_gate_closed(
    tmp_path: Path,
) -> None:
    older_source = tmp_path / "older_source.json"
    newer_audit = tmp_path / "rerun_audit.json"
    older_source.write_text('{"ok": true}', encoding="utf-8")
    audit_payload = (
        '{"source_artifacts":{"chat_live_smoke_report_path":"'
        + older_source.as_posix()
        + '"},"rerun_decision":{"decision":"'
        + "defer_live_rerun_optional_only"
        + '","rerun_needed_now":false}}'
    )
    newer_audit.write_text(audit_payload, encoding="utf-8")

    audit = build_chat_optional_rerun_freshness_audit(
        rerun_audit={
            "source_artifacts": {
                "chat_live_smoke_report_path": str(older_source),
            },
            "rerun_decision": {
                "decision": "defer_live_rerun_optional_only",
                "rerun_needed_now": False,
            },
        },
        rerun_audit_path=newer_audit,
    )

    assert audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert audit["freshness_gate"]["reopen_optional_chat_review"] is False
    assert (
        audit["freshness_gate"]["decision"]
        == "no_new_chat_optional_source_since_rerun_audit"
    )
    assert "no_newer_chat_optional_source_artifacts" in audit["freshness_gate"][
        "reason_codes"
    ]
    assert validate_chat_optional_rerun_freshness_audit(audit) == []


def test_write_chat_optional_rerun_freshness_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "chat_optional_rerun_freshness_audit_v1",
        "freshness_gate": {
            "decision": "no_new_chat_optional_source_since_rerun_audit",
        },
        "evidence_summary": {
            "newer_source_count": 0,
        },
        "decision_rationale": ["No new chat optional source artifact exists."],
        "summary_findings": ["Keep the defer-live-rerun interpretation."],
        "validation_issues": [],
    }

    json_path = tmp_path / "chat_optional_rerun_freshness_audit_v1.json"
    md_path = tmp_path / "chat_optional_rerun_freshness_audit_v1.md"
    write_chat_optional_rerun_freshness_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_chat_optional_rerun_freshness_audit_markdown(audit)
    assert "## freshness gate" in markdown
    assert "## summary findings" in markdown
