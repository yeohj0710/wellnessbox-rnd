from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_structured_safety_rule_overlap_freshness_audit(
    *,
    overlap_decision: dict[str, object],
    overlap_decision_path: str | Path,
) -> dict[str, object]:
    decision_path = Path(overlap_decision_path)
    decision_mtime = _file_mtime_utc(decision_path)
    source_artifacts = _as_dict(overlap_decision.get("source_artifacts"))

    tracked_sources: list[dict[str, object]] = []
    newer_source_count = 0
    for label, raw_path in sorted(source_artifacts.items()):
        source_path = Path(str(raw_path))
        source_mtime = _file_mtime_utc(source_path)
        is_newer = source_mtime > decision_mtime
        if is_newer:
            newer_source_count += 1
        tracked_sources.append(
            {
                "label": label,
                "path": str(source_path),
                "last_modified_utc": source_mtime.isoformat(),
                "is_newer_than_overlap_decision": is_newer,
            }
        )

    decision_gate = _as_dict(overlap_decision.get("decision_gate"))
    newer_source_artifact_detected = newer_source_count > 0
    reopen_gate = newer_source_artifact_detected

    audit = {
        "audit_name": "structured_safety_rule_overlap_freshness_audit_v1",
        "source_artifacts": {
            "overlap_decision_path": str(decision_path),
            "tracked_source_count": len(tracked_sources),
        },
        "freshness_gate": {
            "newer_source_artifact_detected": newer_source_artifact_detected,
            "reopen_overlap_review": reopen_gate,
            "decision": (
                "no_new_safety_source_since_overlap_decision"
                if not reopen_gate
                else "newer_safety_source_detected_rebuild_overlap_decision"
            ),
            "reason_codes": _reason_codes(
                newer_source_artifact_detected=newer_source_artifact_detected,
                prior_decision=str(decision_gate.get("decision") or ""),
            ),
        },
        "evidence_summary": {
            "overlap_decision": {
                "path": str(decision_path),
                "decision": decision_gate.get("decision"),
                "blocks_kpi_interpretation": decision_gate.get("blocks_kpi_interpretation"),
                "last_modified_utc": decision_mtime.isoformat(),
            },
            "tracked_sources": tracked_sources,
            "newer_source_count": newer_source_count,
        },
        "decision_rationale": [
            (
                "This loop checks only whether any source artifact used by the current "
                "structured-safety overlap decision is newer than that decision."
            ),
            (
                "If none are newer, there is no fresh weakest-slice safety evidence that "
                "would justify reopening the current non-blocking interpretation."
            ),
        ],
        "summary_findings": [
            (
                "No newer weakest-slice safety source artifact has appeared since the current "
                "structured-safety overlap decision."
            ),
            (
                "The partial-but-non-blocking safety overlap interpretation should stay in "
                "place until a source artifact actually changes."
            ),
        ],
    }
    audit["validation_issues"] = validate_structured_safety_rule_overlap_freshness_audit(
        audit
    )
    return audit


def validate_structured_safety_rule_overlap_freshness_audit(
    audit: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(audit.get("freshness_gate"))
    evidence = _as_dict(audit.get("evidence_summary"))
    overlap_decision = _as_dict(evidence.get("overlap_decision"))
    tracked_sources = _as_list(evidence.get("tracked_sources"))

    if gate.get("newer_source_artifact_detected") is not False:
        issues.append("unexpected_newer_safety_source_artifact_detected")
    if gate.get("reopen_overlap_review") is not False:
        issues.append("unexpected_safety_overlap_reopen_gate")
    if gate.get("decision") != "no_new_safety_source_since_overlap_decision":
        issues.append("unexpected_safety_overlap_freshness_decision")
    if (
        overlap_decision.get("decision")
        != "partial_rule_overlap_not_blocking_current_kpi_interpretation"
    ):
        issues.append("unexpected_overlap_decision_reference")
    if not tracked_sources:
        issues.append("tracked_safety_sources_missing")
    return issues


def render_structured_safety_rule_overlap_freshness_audit_markdown(
    audit: dict[str, object],
) -> str:
    lines = [
        "# structured safety rule overlap freshness audit v1",
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


def write_structured_safety_rule_overlap_freshness_audit_files(
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
        render_structured_safety_rule_overlap_freshness_audit_markdown(audit),
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
    if prior_decision == "partial_rule_overlap_not_blocking_current_kpi_interpretation":
        reasons.append("overlap_decision_present")
    if not newer_source_artifact_detected:
        reasons.append("no_newer_safety_source_artifacts")
    return reasons


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_structured_safety_rule_overlap_freshness_audit",
    "load_json_artifact",
    "render_structured_safety_rule_overlap_freshness_audit_markdown",
    "validate_structured_safety_rule_overlap_freshness_audit",
    "write_structured_safety_rule_overlap_freshness_audit_files",
]
