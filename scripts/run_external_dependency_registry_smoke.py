from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from wellnessbox_rnd.governance.external_dependency_registry import (
    audit_external_dependency_registry_v1,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/original_plan/op119_external_dependency_registry_v1.json"
CASES = ROOT / "data/original_plan/op119_external_dependency_registry_cases_v1.json"
MANIFEST = ROOT / "data/original_plan/requirements_manifest_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op119_external_dependency_registry_smoke_v1.json"
SOURCE_PATHS = (
    "src/wellnessbox_rnd/governance/external_dependency_registry.py",
    "tests/test_external_dependency_registry.py",
    "scripts/run_external_dependency_registry_smoke.py",
    "data/original_plan/op119_external_dependency_registry_v1.json",
    "data/original_plan/op119_external_dependency_registry_cases_v1.json",
    "data/original_plan/contracts/op039_external_input_contract_v1.json",
    "data/original_plan/requirements_manifest_v1.json",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_head_identity() -> tuple[str, dict[str, str]]:
    blobs: dict[str, str] = {}
    for path in SOURCE_PATHS:
        try:
            committed_blob = git("rev-parse", f"HEAD:{path}")
            working_blob = git("hash-object", path)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"source is not committed at HEAD: {path}") from error
        if working_blob != committed_blob:
            raise RuntimeError(f"source differs from HEAD: {path}")
        blobs[path] = committed_blob
    return git("log", "-1", "--format=%H", "--", *SOURCE_PATHS), blobs


def main() -> int:
    audit = audit_external_dependency_registry_v1(REGISTRY, MANIFEST, ROOT)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    entries = registry["entries"]
    observed = {
        "external_requirement_set": {
            "requirement_ids": audit.external_requirement_ids
        },
        "accountable_owner": {"owner_count": len(entries)},
        "external_provider_role": {
            "provider_role_count": sum(bool(item["external_provider_role"]) for item in entries)
        },
        "required_inputs": {
            "input_count": audit.required_input_count,
            "missing_count": sum(
                value["provision_status"] == "MISSING"
                for item in entries
                for value in item["required_inputs"]
            ),
        },
        "replacement_contracts": {
            "contract_count": audit.replacement_contract_count
        },
        "blocking_reasons": {
            "reason_count": audit.blocking_reason_count,
            "verified_observation_count": audit.verified_observation_count,
        },
        "readiness": {
            "blocked_requirement_ids": audit.blocked_requirement_ids,
            "ready_count": sum(item["readiness"] == "READY" for item in entries),
        },
        "promotion_condition": {
            "condition_count": sum(bool(item["promotion_condition"]) for item in entries)
        },
    }
    expected = {item["case_id"]: item["expected"] for item in cases["cases"]}
    if observed != expected:
        raise AssertionError({"expected": expected, "observed": observed})
    source_commit, source_blobs = verified_head_identity()
    report = {
        "schema_version": "op119_external_dependency_registry_smoke_v1",
        "requirement": {
            "requirement_id": "OP-119",
            "required_stage": "IMPLEMENTED",
            "claimed_stage": "IMPLEMENTED",
        },
        "dataset": {
            "path": CASES.relative_to(ROOT).as_posix(),
            "case_count": len(cases["cases"]),
            "sha256": sha256(CASES),
        },
        "registry": {
            "path": REGISTRY.relative_to(ROOT).as_posix(),
            "entry_count": len(entries),
            "sha256": sha256(REGISTRY),
        },
        "audit": audit.model_dump(mode="json"),
        "observed": observed,
        "source_identity": {
            "commit": source_commit,
            "blobs": source_blobs,
        },
        "stage_boundary": {
            "external_inputs_provided": False,
            "external_approvals_registered": False,
            "op039_external_validation_complete": False,
            "registry_contract_implemented": True,
        },
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
