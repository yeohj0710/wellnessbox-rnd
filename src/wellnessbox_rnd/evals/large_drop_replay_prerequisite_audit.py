from __future__ import annotations

import hashlib
import json
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


__all__ = [
    "build_large_drop_replay_prerequisite_audit",
    "write_large_drop_replay_prerequisite_audit",
]
