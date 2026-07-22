from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from wellnessbox_rnd.governance.final_completion_audit import audit_final_completion_v1
from wellnessbox_rnd.schemas.original_plan_manifest import RepositoryName

ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(ROOT.parent / "wellnessbox"))
).resolve()
MANIFEST = ROOT / "data/original_plan/requirements_manifest_v1.json"
POLICY = ROOT / "data/original_plan/op120_final_audit_policy_v1.json"
CASES = ROOT / "data/original_plan/op120_final_completion_audit_cases_v1.json"
REPORTS = ROOT / "docs/original_plan/research_reports"
OUTPUT = ROOT / "data/original_plan/evidence/op120_final_completion_audit_v1.json"
SOURCE_PATHS = (
    "src/wellnessbox_rnd/governance/final_completion_audit.py",
    "tests/test_final_completion_audit.py",
    "scripts/run_final_completion_audit.py",
    "data/original_plan/op120_final_audit_policy_v1.json",
    "data/original_plan/op120_final_completion_audit_cases_v1.json",
    "data/original_plan/requirements_manifest_v1.json",
    "docs/original_plan/research_reports/OP-120.md",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_head_identity() -> tuple[str, dict[str, str]]:
    blobs: dict[str, str] = {}
    for path in SOURCE_PATHS:
        committed_blob = git("rev-parse", f"HEAD:{path}")
        working_blob = git("hash-object", path)
        if working_blob != committed_blob:
            raise RuntimeError(f"source differs from HEAD: {path}")
        blobs[path] = committed_blob
    return git("log", "-1", "--format=%H", "--", *SOURCE_PATHS), blobs


def main() -> int:
    audit = audit_final_completion_v1(
        manifest_path=MANIFEST,
        reports_dir=REPORTS,
        policy_path=POLICY,
        repository_roots={
            RepositoryName.WELLNESSBOX_RND: ROOT,
            RepositoryName.WELLNESSBOX: SERVICE_ROOT,
        },
    )
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    facts = audit.facts
    observed = {
        "requirement_inventory": {"requirement_count": facts.requirement_count},
        "claimed_inventory": {
            "claimed_requirement_count": facts.claimed_requirement_count
        },
        "required_stage_gaps": {
            "nonexternal_stage_gap_count": len(facts.nonexternal_stage_gap_ids)
        },
        "external_validation": {
            "external_validation_gap_ids": facts.external_validation_gap_ids
        },
        "research_reports": {
            "report_count": facts.report_count,
            "missing_report_count": len(facts.missing_report_ids),
        },
        "canonical_evidence": {
            "audit_passed": facts.canonical_evidence_audit_passed
        },
        "completion_receipts": {
            "validation": facts.validation_receipt_valid,
            "independent_review": facts.independent_review_receipt_valid,
        },
        "completion_decision": {
            "status": audit.status.value,
            "goal_complete": audit.goal_complete,
        },
    }
    expected = {item["case_id"]: item["expected"] for item in cases["cases"]}
    if observed != expected:
        raise AssertionError({"expected": expected, "observed": observed})
    source_commit, source_blobs = verified_head_identity()
    payload = {
        "schema_version": "op120_final_completion_audit_v1",
        "requirement": {
            "requirement_id": "OP-120",
            "required_stage": "OPERATED",
            "claimed_stage": "IMPLEMENTED",
        },
        "dataset": {
            "path": CASES.relative_to(ROOT).as_posix(),
            "case_count": len(cases["cases"]),
            "sha256": sha256(CASES),
        },
        "audit": audit.model_dump(mode="json"),
        "observed": observed,
        "source_identity": {"commit": source_commit, "blobs": source_blobs},
        "stage_boundary": {
            "final_auditor_implemented": True,
            "final_audit_ready": False,
            "goal_complete": False,
        },
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
