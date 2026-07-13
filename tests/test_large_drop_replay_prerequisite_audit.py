from __future__ import annotations

import json
from pathlib import Path

from wellnessbox_rnd.evals.large_drop_replay_prerequisite_audit import (
    build_large_drop_replay_prerequisite_audit,
    write_large_drop_replay_prerequisite_audit,
)


def test_audit_blocks_and_names_missing_roles(tmp_path: Path) -> None:
    present = tmp_path / "present.json"
    present.write_text("{}", encoding="utf-8")

    report = build_large_drop_replay_prerequisite_audit(
        {
            "dataset": present,
            "held_candidate_effect_artifact": tmp_path / "missing.json",
        }
    )

    assert report["status"] == "blocked_missing_prerequisites"
    assert report["missing_roles"] == ["held_candidate_effect_artifact"]
    assert report["training_allowed"] is False
    assert report["runtime_promotion_allowed"] is False
    assert report["required_inputs"][0]["sha256"]


def test_audit_ready_and_writer_round_trip(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('{"a":1}', encoding="utf-8")
    second.write_text('{"b":2}', encoding="utf-8")

    report = build_large_drop_replay_prerequisite_audit(
        {"dataset": first, "policy_artifact": second}
    )
    output = tmp_path / "audit.json"
    write_large_drop_replay_prerequisite_audit(report, output)

    assert report["status"] == "ready"
    assert report["missing_roles"] == []
    assert json.loads(output.read_text(encoding="utf-8")) == report
