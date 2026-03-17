import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_effect_training_revisit_freshness_hold_regression() -> None:
    freshness_audit = _load_json(
        "artifacts/reports/effect_training_revisit_freshness_audit_v1.json"
    )
    stability_decision = _load_json(
        "artifacts/reports/effect_training_revisit_stability_decision_v1.json"
    )

    assert freshness_audit["freshness_gate"]["newer_source_artifact_detected"] is False
    assert freshness_audit["freshness_gate"]["revisit_gate_can_be_reopened"] is False
    assert (
        freshness_audit["freshness_gate"]["decision"]
        == "no_new_replay_source_since_stability_decision"
    )
    assert "stability_decision_present" in freshness_audit["freshness_gate"]["reason_codes"]
    assert (
        "no_newer_replay_source_artifacts"
        in freshness_audit["freshness_gate"]["reason_codes"]
    )

    stability_anchor = freshness_audit["evidence_summary"]["stability_decision"]
    assert stability_anchor["decision"] == "current_defer_decision_still_holds"
    assert stability_anchor["material_replay_change_detected"] is False
    assert stability_decision["decision_gate"]["decision"] == "current_defer_decision_still_holds"

    assert freshness_audit["source_artifacts"]["tracked_source_count"] == 4
    assert freshness_audit["evidence_summary"]["newer_source_count"] == 0
    assert len(freshness_audit["evidence_summary"]["tracked_sources"]) == 4
    assert all(
        source["is_newer_than_stability_decision"] is False
        for source in freshness_audit["evidence_summary"]["tracked_sources"]
    )
