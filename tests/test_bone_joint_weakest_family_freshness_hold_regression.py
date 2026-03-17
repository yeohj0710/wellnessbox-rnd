import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_bone_joint_weakest_family_freshness_hold_regression() -> None:
    freshness_audit = _load_json(
        "artifacts/reports/bone_joint_weakest_family_freshness_audit_v1.json"
    )
    bone_joint_decision = _load_json(
        "artifacts/reports/bone_joint_weakest_family_decision_v1.json"
    )

    assert freshness_audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert freshness_audit["freshness_gate"]["reopen_bone_joint_review"] is False
    assert (
        freshness_audit["freshness_gate"]["decision"]
        == "no_new_bone_joint_source_since_decision"
    )
    assert freshness_audit["source_artifacts"]["tracked_source_count"] == 3
    assert freshness_audit["evidence_summary"]["newer_source_count"] == 0

    tracked_sources = freshness_audit["evidence_summary"]["tracked_sources"]
    assert len(tracked_sources) == 3
    assert all(
        source["is_newer_than_bone_joint_decision"] is False
        for source in tracked_sources
    )

    assert bone_joint_decision["decision_gate"]["keep_explicit_empty_anchor"] is True
    assert bone_joint_decision["decision_gate"]["decision"] == "keep_explicit_empty_anchor"
