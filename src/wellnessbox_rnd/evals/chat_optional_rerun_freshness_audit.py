from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_chat_optional_rerun_freshness_audit(
    *,
    rerun_audit: dict[str, object],
    rerun_audit_path: str | Path,
) -> dict[str, object]:
    audit_path = Path(rerun_audit_path)
    audit_mtime = _file_mtime_utc(audit_path)
    source_artifacts = _as_dict(rerun_audit.get("source_artifacts"))

    tracked_sources: list[dict[str, object]] = []
    newer_source_count = 0
    for label, raw_path in sorted(source_artifacts.items()):
        source_path = Path(str(raw_path))
        source_mtime = _file_mtime_utc(source_path)
        is_newer = source_mtime > audit_mtime
        if is_newer:
            newer_source_count += 1
        tracked_sources.append(
            {
                "label": label,
                "path": str(source_path),
                "last_modified_utc": source_mtime.isoformat(),
                "is_newer_than_rerun_audit": is_newer,
            }
        )

    rerun_decision = _as_dict(rerun_audit.get("rerun_decision"))
    newer_source_artifact_detected = newer_source_count > 0
    reopen_gate = newer_source_artifact_detected

    audit = {
        "audit_name": "chat_optional_rerun_freshness_audit_v1",
        "source_artifacts": {
            "rerun_audit_path": str(audit_path),
            "tracked_source_count": len(tracked_sources),
        },
        "freshness_gate": {
            "newer_source_artifact_detected": newer_source_artifact_detected,
            "reopen_optional_chat_review": reopen_gate,
            "decision": (
                "no_new_chat_optional_source_since_rerun_audit"
                if not reopen_gate
                else "newer_chat_optional_source_detected_rebuild_rerun_audit"
            ),
            "reason_codes": _reason_codes(
                newer_source_artifact_detected=newer_source_artifact_detected,
                prior_decision=str(rerun_decision.get("decision") or ""),
            ),
        },
        "evidence_summary": {
            "rerun_audit": {
                "path": str(audit_path),
                "decision": rerun_decision.get("decision"),
                "rerun_needed_now": rerun_decision.get("rerun_needed_now"),
                "last_modified_utc": audit_mtime.isoformat(),
            },
            "tracked_sources": tracked_sources,
            "newer_source_count": newer_source_count,
        },
        "decision_rationale": [
            (
                "This loop checks only whether any source artifact used by the current "
                "optional chat rerun audit is newer than that audit."
            ),
            (
                "If none are newer, there is no fresh optional-chat evidence that "
                "would justify reopening the current defer-live-rerun interpretation."
            ),
        ],
        "summary_findings": [
            (
                "No newer optional-chat source artifact has appeared since the current "
                "chat rerun audit."
            ),
            (
                "The current defer-live-rerun interpretation should stay in place until "
                "a chat source artifact actually changes."
            ),
        ],
    }
    audit["validation_issues"] = validate_chat_optional_rerun_freshness_audit(audit)
    return audit


def validate_chat_optional_rerun_freshness_audit(
    audit: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(audit.get("freshness_gate"))
    evidence = _as_dict(audit.get("evidence_summary"))
    rerun_audit = _as_dict(evidence.get("rerun_audit"))
    tracked_sources = _as_list(evidence.get("tracked_sources"))

    if gate.get("newer_source_artifact_detected") is not False:
        issues.append("unexpected_newer_chat_optional_source_artifact_detected")
    if gate.get("reopen_optional_chat_review") is not False:
        issues.append("unexpected_chat_optional_reopen_gate")
    if gate.get("decision") != "no_new_chat_optional_source_since_rerun_audit":
        issues.append("unexpected_chat_optional_freshness_decision")
    if rerun_audit.get("decision") != "defer_live_rerun_optional_only":
        issues.append("unexpected_chat_optional_rerun_decision_reference")
    if not tracked_sources:
        issues.append("tracked_chat_optional_sources_missing")
    return issues


def render_chat_optional_rerun_freshness_audit_markdown(
    audit: dict[str, object],
) -> str:
    lines = [
        "# chat optional rerun freshness audit v1",
        "",
        "## freshness gate",
        "",
        f"- freshness_gate: `{audit.get('freshness_gate', {})}`",
        "",
        "## evidence summary",
        "",
    ]
    for key, value in _as_dict(audit.get("evidence_summary")).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## decision rationale", ""])
    for item in _as_list(audit.get("decision_rationale")):
        lines.append(f"- {item}")
    lines.extend(["", "## summary findings", ""])
    for item in _as_list(audit.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{audit.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_chat_optional_rerun_freshness_audit_files(
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
    md_file.write_text(
        render_chat_optional_rerun_freshness_audit_markdown(audit),
        encoding="utf-8",
    )


def _file_mtime_utc(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _reason_codes(
    *,
    newer_source_artifact_detected: bool,
    prior_decision: str,
) -> list[str]:
    reasons: list[str] = []
    if prior_decision == "defer_live_rerun_optional_only":
        reasons.append("rerun_audit_present")
    if not newer_source_artifact_detected:
        reasons.append("no_newer_chat_optional_source_artifacts")
    return reasons


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_chat_optional_rerun_freshness_audit",
    "load_json_artifact",
    "render_chat_optional_rerun_freshness_audit_markdown",
    "validate_chat_optional_rerun_freshness_audit",
    "write_chat_optional_rerun_freshness_audit_files",
]
