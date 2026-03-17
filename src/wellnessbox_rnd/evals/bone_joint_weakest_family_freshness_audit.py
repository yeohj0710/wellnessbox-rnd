from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_bone_joint_weakest_family_freshness_audit(
    *,
    bone_joint_decision: dict[str, object],
    bone_joint_decision_path: str | Path,
) -> dict[str, object]:
    decision_path = Path(bone_joint_decision_path)
    decision_mtime = _file_mtime_utc(decision_path)
    source_artifacts = _as_dict(bone_joint_decision.get("source_artifacts"))

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
                "is_newer_than_bone_joint_decision": is_newer,
            }
        )

    decision_gate = _as_dict(bone_joint_decision.get("decision_gate"))
    newer_source_artifact_detected = newer_source_count > 0
    reopen_review = newer_source_artifact_detected

    audit = {
        "audit_name": "bone_joint_weakest_family_freshness_audit_v1",
        "source_artifacts": {
            "bone_joint_decision_path": str(decision_path),
            "tracked_source_count": len(tracked_sources),
        },
        "freshness_gate": {
            "newer_source_artifact_detected": newer_source_artifact_detected,
            "reopen_bone_joint_review": reopen_review,
            "decision": (
                "newer_bone_joint_source_detected_recheck_empty_anchor"
                if reopen_review
                else "no_new_bone_joint_source_since_decision"
            ),
            "reason_codes": _reason_codes(
                newer_source_artifact_detected=newer_source_artifact_detected,
                prior_decision=str(decision_gate.get("decision") or ""),
            ),
        },
        "evidence_summary": {
            "bone_joint_decision": {
                "path": str(decision_path),
                "decision": decision_gate.get("decision"),
                "keep_explicit_empty_anchor": decision_gate.get(
                    "keep_explicit_empty_anchor"
                ),
                "last_modified_utc": decision_mtime.isoformat(),
            },
            "tracked_sources": tracked_sources,
            "newer_source_count": newer_source_count,
        },
        "decision_rationale": [
            (
                "This loop checks only whether any source artifact used by the current "
                "bone_joint weakest-family decision is newer than that decision."
            ),
            (
                "If a source artifact is newer, the keep-empty decision should be rechecked "
                "from current evidence before assuming the old decision still reflects the "
                "latest weakest-family surface."
            ),
        ],
        "summary_findings": [
            (
                "A newer source artifact exists if `reopen_bone_joint_review = true`; that is "
                "a freshness signal, not by itself a claim that bone_joint became a blocker."
            ),
            (
                "If no source is newer, the current keep-empty-anchor interpretation can stay "
                "in place until a source artifact changes."
            ),
        ],
    }
    audit["validation_issues"] = validate_bone_joint_weakest_family_freshness_audit(audit)
    return audit


def validate_bone_joint_weakest_family_freshness_audit(
    audit: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(audit.get("freshness_gate"))
    evidence = _as_dict(audit.get("evidence_summary"))
    decision = _as_dict(evidence.get("bone_joint_decision"))
    tracked_sources = _as_list(evidence.get("tracked_sources"))

    if (
        decision.get("decision") != "keep_explicit_empty_anchor"
        or decision.get("keep_explicit_empty_anchor") is not True
    ):
        issues.append("unexpected_bone_joint_decision_reference")
    if gate.get("decision") not in {
        "newer_bone_joint_source_detected_recheck_empty_anchor",
        "no_new_bone_joint_source_since_decision",
    }:
        issues.append("unexpected_bone_joint_freshness_decision")
    if not tracked_sources:
        issues.append("tracked_bone_joint_sources_missing")
    return issues


def render_bone_joint_weakest_family_freshness_audit_markdown(
    audit: dict[str, object],
) -> str:
    lines = [
        "# bone joint weakest family freshness audit v1",
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


def write_bone_joint_weakest_family_freshness_audit_files(
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
        render_bone_joint_weakest_family_freshness_audit_markdown(audit),
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
    if prior_decision == "keep_explicit_empty_anchor":
        reasons.append("bone_joint_decision_present")
    if newer_source_artifact_detected:
        reasons.append("newer_bone_joint_source_artifact_detected")
    else:
        reasons.append("no_newer_bone_joint_source_artifacts")
    return reasons


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_bone_joint_weakest_family_freshness_audit",
    "load_json_artifact",
    "render_bone_joint_weakest_family_freshness_audit_markdown",
    "validate_bone_joint_weakest_family_freshness_audit",
    "write_bone_joint_weakest_family_freshness_audit_files",
]
