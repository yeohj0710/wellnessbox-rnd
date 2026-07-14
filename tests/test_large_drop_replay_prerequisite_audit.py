from __future__ import annotations

import json
from pathlib import Path

from wellnessbox_rnd.evals.large_drop_replay_prerequisite_audit import (
    build_large_drop_replay_prerequisite_audit,
    restore_large_drop_replay_prerequisites,
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


def test_restore_requires_all_hashes_before_copying(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    repository = tmp_path / "repository"
    archive.mkdir()
    repository.mkdir()
    source = archive / "held.json"
    source.write_text('{"held":true}', encoding="utf-8")

    report = restore_large_drop_replay_prerequisites(
        archive_root=archive,
        repository_root=repository,
        manifest={
            "files": [
                {
                    "role": "held_candidate_effect_artifact",
                    "source": "held.json",
                    "destination": "artifacts/models/held.json",
                    "sha256": "0" * 64,
                }
            ]
        },
    )

    assert report["status"] == "blocked_restore_verification_failed"
    assert report["restored_count"] == 0
    assert not (repository / "artifacts/models/held.json").exists()


def test_restore_copies_verified_archive_file(tmp_path: Path) -> None:
    import hashlib

    archive = tmp_path / "archive"
    repository = tmp_path / "repository"
    archive.mkdir()
    repository.mkdir()
    source = archive / "held.json"
    payload = b'{"held":true}'
    source.write_bytes(payload)

    report = restore_large_drop_replay_prerequisites(
        archive_root=archive,
        repository_root=repository,
        manifest={
            "files": [
                {
                    "role": "held_candidate_effect_artifact",
                    "source": "held.json",
                    "destination": "artifacts/models/held.json",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            ]
        },
    )

    assert report["status"] == "restored_verified_prerequisites"
    assert report["restored_count"] == 1
    assert (repository / "artifacts/models/held.json").read_bytes() == payload
