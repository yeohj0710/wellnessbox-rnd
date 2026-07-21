from __future__ import annotations

import os
from pathlib import Path

from wellnessbox_rnd.governance.original_plan_audit import (
    OriginalPlanAuditStatus,
    audit_original_plan_manifest_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    RepositoryName,
    calculate_original_plan_manifest_sha256_v1,
    load_original_plan_manifest_v1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(RND_ROOT.parent / "wellnessbox"))
).resolve()
REPO_ROOTS = {
    RepositoryName.WELLNESSBOX_RND: RND_ROOT,
    RepositoryName.WELLNESSBOX: SERVICE_ROOT,
}


def _manifest_copy():
    return load_original_plan_manifest_v1().model_copy(deep=True)


def _draft_by_id(manifest, requirement_id: str):
    return next(
        requirement
        for group in manifest.groups
        for requirement in group.requirements
        if requirement.requirement_id == requirement_id
    )


def test_original_plan_audit_accepts_current_claimed_evidence() -> None:
    report = audit_original_plan_manifest_v1(
        _manifest_copy(),
        repository_roots=REPO_ROOTS,
    )

    assert report.status == OriginalPlanAuditStatus.PASS
    assert report.requirement_count == 120
    assert report.claimed_requirement_count == 67
    assert report.manifest_sha256 == calculate_original_plan_manifest_sha256_v1(
        _manifest_copy()
    )
    assert report.source_hash_matches is True
    assert report.checked_evidence_file_count > 0
    assert report.issues == []


def test_original_plan_audit_rejects_missing_evidence_file() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-031")
    requirement.evidence.implementation_files = [
        "wellnessbox-rnd/src/wellnessbox_rnd/safety/does_not_exist.py"
    ]

    report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=REPO_ROOTS,
    )

    assert any(
        issue.code == "evidence_file_missing"
        and issue.requirement_id == "OP-031"
        for issue in report.issues
    )


def test_original_plan_audit_attributes_contract_violation_to_requirement() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-031")
    requirement.evidence.test_files = []

    report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=REPO_ROOTS,
    )

    assert any(
        issue.code == "manifest_contract_violation"
        and issue.requirement_id == "OP-031"
        for issue in report.issues
    )


def test_original_plan_audit_rejects_evidence_owned_by_another_repository() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-031")
    requirement.owners = [RepositoryName.WELLNESSBOX]

    report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=REPO_ROOTS,
    )

    assert any(
        issue.code == "evidence_owner_not_declared"
        and issue.requirement_id == "OP-031"
        for issue in report.issues
    )


def test_original_plan_audit_rejects_repository_path_escape() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-031")
    requirement.evidence.implementation_files = [
        "wellnessbox-rnd/../wellnessbox/AGENTS.md"
    ]

    report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=REPO_ROOTS,
    )

    assert any(
        issue.code == "evidence_path_escape"
        and issue.requirement_id == "OP-031"
        for issue in report.issues
    )


def test_original_plan_audit_rejects_untracked_evidence() -> None:
    manifest = _manifest_copy()
    tracked_files = {
        RepositoryName.WELLNESSBOX_RND: set(),
    }

    report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=REPO_ROOTS,
        tracked_files_by_repository=tracked_files,
    )

    assert any(issue.code == "evidence_file_untracked" for issue in report.issues)


def test_original_plan_audit_rejects_pdf_hash_mismatch() -> None:
    manifest = _manifest_copy()
    manifest.original_plan_sha256 = "0" * 64

    report = audit_original_plan_manifest_v1(
        manifest,
        repository_roots=REPO_ROOTS,
    )

    assert report.source_hash_matches is False
    assert any(issue.code == "original_plan_sha256_mismatch" for issue in report.issues)
