"""Train a candidate artifact from pharmacist-approved drafts, gate permitting.

The training readiness gate is the only thing that authorises a run. While the
gate says NO-GO this command resolves and records the exact training plan —
dataset digest, argv, config digest — and exits without training anything.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from wellnessbox_rnd.training.approved_draft_dataset import verify_manifest_is_approved_only

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = "data/original_plan/final_session/approved_draft_dataset_manifest_v1.json"
DEFAULT_GATE = "artifacts/reports/training_readiness_gate_v2.json"
DEFAULT_ARTIFACT = "artifacts/models/effect_model_candidate_approved_drafts.json"
DEFAULT_PLAN = "data/original_plan/final_session/approved_draft_training_plan_v1.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--gate-report", default=DEFAULT_GATE)
    parser.add_argument("--artifact", default=DEFAULT_ARTIFACT)
    parser.add_argument("--plan-output", default=DEFAULT_PLAN)
    parser.add_argument("--seed", type=int, default=20260311)
    return parser


def read_gate_status(gate_path: str | Path) -> dict[str, Any]:
    path = Path(gate_path)
    if not path.is_file():
        return {"status": "gate_report_missing", "authorized_now": False, "path": str(path)}
    gate = json.loads(path.read_text(encoding="utf-8"))
    decision = gate.get("gate_decision", {})
    return {
        "status": str(decision.get("decision", "unknown")),
        "authorized_now": bool(decision.get("authorized_now")),
        "failed_criteria": decision.get("failed_criteria", []),
        "path": str(path),
    }


def build_training_plan(
    *,
    manifest: dict[str, Any],
    manifest_path: str,
    gate: dict[str, Any],
    artifact: str,
    seed: int,
) -> dict[str, Any]:
    argv = [
        sys.executable,
        "scripts/train_effect_model_v3.py",
        "--dataset",
        manifest_path,
        "--seed",
        str(seed),
        "--artifact",
        artifact,
    ]
    config = {"seed": seed, "trainer": "scripts/train_effect_model_v3.py", "artifact": artifact}
    return {
        "schema_version": "approved_draft_training_plan_v1",
        "dataset_manifest_path": manifest_path,
        "dataset_sha256": manifest.get("dataset_sha256"),
        "approved_draft_count": len(manifest.get("included_drafts", [])),
        "approved_draft_ids": [item["draft_id"] for item in manifest.get("included_drafts", [])],
        "excluded_draft_count": len(manifest.get("excluded_drafts", [])),
        "training_gate": gate,
        "command": argv,
        "config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = Path(args.dataset_manifest)
    if not manifest_path.is_file():
        print(json.dumps({"status": "BLOCKED", "reason": "dataset_manifest_missing"}))
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check = verify_manifest_is_approved_only(manifest)
    gate = read_gate_status(args.gate_report)
    plan = build_training_plan(
        manifest=manifest,
        manifest_path=str(manifest_path),
        gate=gate,
        artifact=args.artifact,
        seed=args.seed,
    )

    blockers: list[str] = []
    if check["status"] != "READY":
        blockers.append("dataset_manifest_not_approved_only")
    if not plan["approved_draft_count"]:
        blockers.append("approved_draft_dataset_is_empty")
    if not gate["authorized_now"]:
        blockers.append(f"training_gate_not_open:{gate['status']}")

    plan["blockers"] = blockers
    plan["executed"] = False
    output = Path(args.plan_output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if blockers:
        output.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"status": "BLOCKED", "plan_path": str(output), "blockers": blockers},
                         ensure_ascii=False, indent=2))
        return 2

    completed = subprocess.run(plan["command"], cwd=ROOT, check=False)
    plan["executed"] = completed.returncode == 0
    plan["trainer_returncode"] = completed.returncode
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "READY" if plan["executed"] else "ERROR",
                      "plan_path": str(output)}, ensure_ascii=False, indent=2))
    return 0 if plan["executed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
