from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from wellnessbox_rnd.evals.answer_key_integrity import audit_repository
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
    "pyproject.toml",
    "src/wellnessbox_rnd/governance/final_completion_audit.py",
    "tests/test_final_completion_audit.py",
    "scripts/run_final_completion_audit.py",
    "scripts/audit_answer_key_integrity.py",
    "src/wellnessbox_rnd/evals/answer_key_integrity.py",
    "data/original_plan/contracts/engine_input_registry_v1.json",
    "data/original_plan/op120_final_audit_policy_v1.json",
    "data/original_plan/op120_final_completion_audit_cases_v1.json",
    "data/original_plan/requirements_manifest_v1.json",
    "docs/original_plan/research_reports/OP-120.md",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def audited_repository_commits(file_blobs: dict[str, str]) -> dict[str, str]:
    # File content is the audited input. Commits identify the repositories at
    # audit time, but they do not decide whether the content may be audited.
    del file_blobs
    return {
        "wellnessbox-rnd": git("rev-parse", "HEAD"),
        "wellnessbox": subprocess.check_output(
            ["git", "-C", str(SERVICE_ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_head_identity() -> tuple[str, dict[str, str]]:
    """Capture current source bytes and record HEAD without requiring a clean tree."""
    blobs: dict[str, str] = {}
    for path in SOURCE_PATHS:
        blobs[path] = git("hash-object", path)
    return git("rev-parse", "HEAD"), blobs


def working_tree_status(references: list[str]) -> dict[str, object]:
    """Report commit comparison separately from the content-based audit."""
    roots = {"wellnessbox-rnd": ROOT, "wellnessbox": SERVICE_ROOT}
    changed: list[str] = []
    repository_heads: dict[str, str] = {}
    for repository, root in roots.items():
        repository_heads[repository] = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    for reference in references:
        repository, relative = reference.split("/", 1)
        root = roots[repository]
        path = root / relative
        if not path.is_file():
            continue
        committed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", f"HEAD:{relative}"],
            capture_output=True,
            text=True,
            check=False,
        )
        working = subprocess.check_output(
            ["git", "-C", str(root), "hash-object", relative], text=True
        ).strip()
        if committed.returncode != 0 or working != committed.stdout.strip():
            changed.append(reference)
    return {
        "working_tree_matches_head": not changed,
        "changed_paths": changed,
        "repository_heads": repository_heads,
    }


def assert_no_regression(expected: dict[str, dict], observed: dict[str, dict]) -> None:
    regressions: dict[str, dict] = {}
    exact_cases = {"requirement_inventory"}
    for case_id in exact_cases:
        if observed[case_id] != expected[case_id]:
            regressions[case_id] = {
                "expected": expected[case_id],
                "observed": observed[case_id],
            }
    if (
        observed["claimed_inventory"]["claimed_requirement_count"]
        < expected["claimed_inventory"]["claimed_requirement_count"]
    ):
        regressions["claimed_inventory"] = observed["claimed_inventory"]
    if (
        observed["required_stage_gaps"]["nonexternal_stage_gap_count"]
        > expected["required_stage_gaps"]["nonexternal_stage_gap_count"]
    ):
        regressions["required_stage_gaps"] = observed["required_stage_gaps"]
    if not set(observed["external_validation"]["external_validation_gap_ids"]).issubset(
        expected["external_validation"]["external_validation_gap_ids"]
    ):
        regressions["external_validation"] = observed["external_validation"]
    reports = observed["research_reports"]
    expected_reports = expected["research_reports"]
    if (
        reports["report_count"] < expected_reports["report_count"]
        or reports["missing_report_count"] > expected_reports["missing_report_count"]
    ):
        regressions["research_reports"] = reports
    if expected["canonical_evidence"]["audit_passed"] and not observed[
        "canonical_evidence"
    ]["audit_passed"]:
        regressions["canonical_evidence"] = observed["canonical_evidence"]
    for field, required in expected["completion_receipts"].items():
        if required and not observed["completion_receipts"][field]:
            regressions.setdefault("completion_receipts", {})[field] = False
    status_rank = {"BLOCKED": 0, "READY": 1}
    expected_decision = expected["completion_decision"]
    observed_decision = observed["completion_decision"]
    if (
        status_rank[observed_decision["status"]] < status_rank[expected_decision["status"]]
        or (expected_decision["goal_complete"] and not observed_decision["goal_complete"])
    ):
        regressions["completion_decision"] = observed_decision
    if regressions:
        raise AssertionError({"regressions": regressions})


def apply_answer_key_integrity_gate(
    audit_payload: dict,
    answer_key_integrity: dict,
) -> dict:
    """Force the final audit closed unless all four current seals are auditable."""
    gated = json.loads(json.dumps(audit_payload))
    if answer_key_integrity.get("completion_status") == "READY":
        return gated
    gated["status"] = "BLOCKED"
    gated["goal_complete"] = False
    blockers = list(gated.get("blockers", []))
    if "answer_key_integrity_failed" not in blockers:
        blockers.append("answer_key_integrity_failed")
    gated["blockers"] = blockers
    return gated


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
    answer_key_integrity = audit_repository(ROOT)
    audit_payload = apply_answer_key_integrity_gate(
        audit.model_dump(mode="json"),
        answer_key_integrity,
    )
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    facts = audit.facts
    observed = {
        "requirement_inventory": {"requirement_count": facts.requirement_count},
        "claimed_inventory": {"claimed_requirement_count": facts.claimed_requirement_count},
        "required_stage_gaps": {
            "nonexternal_stage_gap_count": len(facts.nonexternal_stage_gap_ids)
        },
        "external_validation": {"external_validation_gap_ids": facts.external_validation_gap_ids},
        "research_reports": {
            "report_count": facts.report_count,
            "missing_report_count": len(facts.missing_report_ids),
        },
        "canonical_evidence": {"audit_passed": facts.canonical_evidence_audit_passed},
        "completion_receipts": {
            "validation": facts.validation_receipt_valid,
            "independent_review": facts.independent_review_receipt_valid,
        },
        "completion_decision": {
            "status": audit_payload["status"],
            "goal_complete": audit_payload["goal_complete"],
        },
    }
    expected = {item["case_id"]: item["expected"] for item in cases["cases"]}
    regression_error: AssertionError | None = None
    try:
        assert_no_regression(expected, observed)
    except AssertionError as exc:
        # Persist the observed BLOCKED state before returning non-zero. Without
        # this, a failed audit leaves the previous READY evidence on disk.
        regression_error = exc
    source_commit, source_blobs = verified_head_identity()
    audited_input_hashes = _audited_input_hashes()
    source_references = [f"wellnessbox-rnd/{path}" for path in SOURCE_PATHS]
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
        "audit": audit_payload,
        "answer_key_integrity": answer_key_integrity,
        "observed": observed,
        "source_identity": {
            "commit": source_commit,
            "blobs": source_blobs,
            "working_tree": working_tree_status(source_references),
        },
        "audited_input_identity": {
            "repository_commits": audited_repository_commits(audited_input_hashes),
            "file_blobs": audited_input_hashes,
            "working_tree": working_tree_status(sorted(audited_input_hashes)),
        },
        "stage_boundary": {
            "final_auditor_implemented": True,
            "final_audit_ready": audit_payload["status"] == "READY",
            "goal_complete": audit_payload["goal_complete"],
        },
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if regression_error is not None:
        print(str(regression_error), file=sys.stderr)
        return 1
    return 0


def _audited_input_hashes() -> dict[str, str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    references = {
        "wellnessbox-rnd/" + MANIFEST.relative_to(ROOT).as_posix(),
        "wellnessbox-rnd/pyproject.toml",
    }
    for field in ("validation_receipt_path", "independent_review_receipt_path"):
        if isinstance(policy.get(field), str):
            references.add(policy[field])
    for group in manifest["groups"]:
        for requirement in group["requirements"]:
            for values in requirement.get("evidence", {}).values():
                if isinstance(values, list):
                    references.update(
                        item for item in values if isinstance(item, str) and "/" in item
                    )
    for report in REPORTS.glob("OP-*.md"):
        references.add("wellnessbox-rnd/" + report.relative_to(ROOT).as_posix())
    blobs: dict[str, str] = {}
    roots = {"wellnessbox-rnd": ROOT, "wellnessbox": SERVICE_ROOT}
    for reference in sorted(references):
        repository, relative = reference.split("/", 1)
        path = roots[repository] / relative
        if path.is_file():
            working_blob = subprocess.check_output(
                ["git", "-C", str(roots[repository]), "hash-object", relative],
                text=True,
            ).strip()
            blobs[reference] = working_blob
    return blobs


if __name__ == "__main__":
    raise SystemExit(main())
