from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

AUDIT_NAME = "large_drop_replay_prerequisite_audit_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_large_drop_replay_prerequisite_audit(
    required_paths: dict[str, str | Path],
) -> dict[str, object]:
    required_inputs: list[dict[str, object]] = []
    missing_roles: list[str] = []

    for role, raw_path in required_paths.items():
        path = Path(raw_path)
        exists = path.is_file()
        if not exists:
            missing_roles.append(role)
        required_inputs.append(
            {
                "role": role,
                "path": str(path),
                "exists": exists,
                "bytes": path.stat().st_size if exists else None,
                "sha256": _sha256(path) if exists else None,
            }
        )

    status = "ready" if not missing_roles else "blocked_missing_prerequisites"
    return {
        "audit_name": AUDIT_NAME,
        "target_replay_slice": {
            "trajectory_mode": "threshold_duration_sensitive",
            "margin_bucket": "mid_margin",
            "proxy_drop_bucket": "large_drop",
            "expected_case_count": 3,
        },
        "status": status,
        "required_input_count": len(required_inputs),
        "present_input_count": len(required_inputs) - len(missing_roles),
        "missing_input_count": len(missing_roles),
        "missing_roles": missing_roles,
        "required_inputs": required_inputs,
        "training_allowed": False,
        "runtime_promotion_allowed": False,
        "next_action": (
            "run_large_drop_replay_attribution"
            if status == "ready"
            else "restore_exact_held_candidate_and_prior_replay_evidence_without_retraining"
        ),
    }


def write_large_drop_replay_prerequisite_audit(
    report: dict[str, object],
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def restore_large_drop_replay_prerequisites(
    *,
    archive_root: str | Path,
    repository_root: str | Path,
    manifest: dict[str, object],
) -> dict[str, object]:
    archive = Path(archive_root).resolve()
    repository = Path(repository_root).resolve()
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("restore manifest must contain a non-empty files list")

    verified: list[dict[str, object]] = []
    issues: list[str] = []
    for raw_item in raw_files:
        if not isinstance(raw_item, dict):
            raise ValueError("restore manifest file entries must be objects")
        role = str(raw_item.get("role", ""))
        source_relative = Path(str(raw_item.get("source", "")))
        destination_relative = Path(str(raw_item.get("destination", "")))
        expected_sha256 = str(raw_item.get("sha256", "")).lower()
        source = (archive / source_relative).resolve()
        destination = (repository / destination_relative).resolve()
        if archive not in source.parents or repository not in destination.parents:
            issues.append(f"{role}:path_outside_allowed_root")
            continue
        if not source.is_file():
            issues.append(f"{role}:source_missing")
            continue
        actual_sha256 = _sha256(source)
        if len(expected_sha256) != 64 or actual_sha256 != expected_sha256:
            issues.append(f"{role}:sha256_mismatch")
            continue
        verified.append(
            {
                "role": role,
                "source": str(source_relative),
                "destination": str(destination_relative),
                "bytes": source.stat().st_size,
                "sha256": actual_sha256,
                "source_path": source,
                "destination_path": destination,
            }
        )

    if issues:
        return {
            "status": "blocked_restore_verification_failed",
            "verified_count": len(verified),
            "restored_count": 0,
            "issues": issues,
        }

    for item in verified:
        source = item.pop("source_path")
        destination = item.pop("destination_path")
        assert isinstance(source, Path)
        assert isinstance(destination, Path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.restore.tmp")
        shutil.copyfile(source, temporary)
        temporary.replace(destination)

    return {
        "status": "restored_verified_prerequisites",
        "verified_count": len(verified),
        "restored_count": len(verified),
        "issues": [],
        "files": verified,
    }


__all__ = [
    "build_large_drop_replay_prerequisite_audit",
    "restore_large_drop_replay_prerequisites",
    "write_large_drop_replay_prerequisite_audit",
]
