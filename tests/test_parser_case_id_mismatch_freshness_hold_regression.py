import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_parser_case_id_mismatch_freshness_hold_regression() -> None:
    freshness_audit = _load_json(
        "artifacts/reports/parser_case_id_mismatch_freshness_audit_v1.json"
    )
    mismatch_decision = _load_json(
        "artifacts/reports/parser_case_id_mismatch_decision_v1.json"
    )

    assert freshness_audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert freshness_audit["freshness_gate"]["reopen_case_id_mismatch_review"] is False
    assert (
        freshness_audit["freshness_gate"]["decision"]
        == "no_new_parser_source_since_mismatch_decision"
    )
    assert freshness_audit["source_artifacts"]["tracked_source_count"] == 3
    assert freshness_audit["evidence_summary"]["newer_source_count"] == 0

    tracked_sources = freshness_audit["evidence_summary"]["tracked_sources"]
    assert len(tracked_sources) == 3
    assert all(
        source["is_newer_than_mismatch_decision"] is False
        for source in tracked_sources
    )

    assert (
        mismatch_decision["decision_gate"]["decision"]
        == "mismatch_not_blocking_current_kpi_interpretation"
    )
    assert mismatch_decision["decision_gate"]["blocks_kpi_interpretation"] is False
