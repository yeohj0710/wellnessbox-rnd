import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_structured_safety_rule_overlap_freshness_hold_regression() -> None:
    freshness_audit = _load_json(
        "artifacts/reports/structured_safety_rule_overlap_freshness_audit_v1.json"
    )
    overlap_decision = _load_json(
        "artifacts/reports/structured_safety_rule_overlap_decision_v1.json"
    )

    assert freshness_audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert freshness_audit["freshness_gate"]["reopen_overlap_review"] is False
    assert (
        freshness_audit["freshness_gate"]["decision"]
        == "no_new_safety_source_since_overlap_decision"
    )
    assert freshness_audit["source_artifacts"]["tracked_source_count"] == 3
    assert freshness_audit["evidence_summary"]["newer_source_count"] == 0

    tracked_sources = freshness_audit["evidence_summary"]["tracked_sources"]
    assert len(tracked_sources) == 3
    assert all(
        source["is_newer_than_overlap_decision"] is False for source in tracked_sources
    )

    assert (
        overlap_decision["decision_gate"]["decision"]
        == "partial_rule_overlap_not_blocking_current_kpi_interpretation"
    )
    assert overlap_decision["decision_gate"]["blocks_kpi_interpretation"] is False
