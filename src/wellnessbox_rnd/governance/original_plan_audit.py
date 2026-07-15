from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.schemas.original_plan_manifest import (
    EvidenceStage,
    OriginalPlanManifestV1,
    OriginalPlanRequirementV1,
    RepositoryName,
    materialize_original_plan_requirements_v1,
    validate_original_plan_manifest_v1,
)


class OriginalPlanAuditStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class OriginalPlanAuditIssueV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    requirement_id: str | None = None
    evidence_field: str | None = None
    reference: str | None = None
    detail: str | None = None


class OriginalPlanAuditReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OriginalPlanAuditStatus
    manifest_schema_version: str
    requirement_count: int
    claimed_requirement_count: int
    claimed_stage_counts: dict[EvidenceStage, int] = Field(default_factory=dict)
    checked_evidence_file_count: int
    source_hash_matches: bool
    issues: list[OriginalPlanAuditIssueV1] = Field(default_factory=list)


def audit_original_plan_manifest_v1(
    manifest: OriginalPlanManifestV1,
    *,
    repository_roots: Mapping[RepositoryName | str, str | Path],
    tracked_files_by_repository: Mapping[
        RepositoryName | str, set[str]
    ]
    | None = None,
) -> OriginalPlanAuditReportV1:
    roots = _normalize_repository_roots(repository_roots)
    tracked_files, tracking_issues = _resolve_tracked_files(
        roots,
        tracked_files_by_repository=tracked_files_by_repository,
    )
    issues = list(tracking_issues)

    for contract_issue in validate_original_plan_manifest_v1(manifest):
        issues.append(
            OriginalPlanAuditIssueV1(
                code="manifest_contract_violation",
                detail=contract_issue,
            )
        )

    source_hash_matches = _audit_original_plan_source(
        manifest,
        roots=roots,
        tracked_files=tracked_files,
        issues=issues,
    )
    _audit_manifest_reference(
        manifest.completion_program_path,
        reference_kind="completion_program",
        roots=roots,
        tracked_files=tracked_files,
        issues=issues,
    )

    requirements = materialize_original_plan_requirements_v1(manifest)
    claimed_requirements = [
        requirement for requirement in requirements if requirement.claimed_stage is not None
    ]
    claimed_stage_counts = {
        stage: sum(
            requirement.claimed_stage == stage for requirement in claimed_requirements
        )
        for stage in EvidenceStage
    }
    checked_evidence_references: set[str] = set()
    for requirement in claimed_requirements:
        _audit_requirement_evidence(
            requirement,
            roots=roots,
            tracked_files=tracked_files,
            checked_references=checked_evidence_references,
            issues=issues,
        )

    return OriginalPlanAuditReportV1(
        status=(OriginalPlanAuditStatus.PASS if not issues else OriginalPlanAuditStatus.FAIL),
        manifest_schema_version=manifest.schema_version,
        requirement_count=len(requirements),
        claimed_requirement_count=len(claimed_requirements),
        claimed_stage_counts=claimed_stage_counts,
        checked_evidence_file_count=len(checked_evidence_references),
        source_hash_matches=source_hash_matches,
        issues=issues,
    )


def _normalize_repository_roots(
    repository_roots: Mapping[RepositoryName | str, str | Path],
) -> dict[RepositoryName, Path]:
    return {
        RepositoryName(str(repository)): Path(root).resolve()
        for repository, root in repository_roots.items()
    }


def _resolve_tracked_files(
    roots: Mapping[RepositoryName, Path],
    *,
    tracked_files_by_repository: Mapping[RepositoryName | str, set[str]] | None,
) -> tuple[dict[RepositoryName, set[str]], list[OriginalPlanAuditIssueV1]]:
    if tracked_files_by_repository is not None:
        return (
            {
                RepositoryName(str(repository)): {
                    _normalize_relative_reference(path) for path in paths
                }
                for repository, paths in tracked_files_by_repository.items()
            },
            [],
        )

    tracked_files: dict[RepositoryName, set[str]] = {}
    issues: list[OriginalPlanAuditIssueV1] = []
    for repository, root in roots.items():
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except (OSError, subprocess.CalledProcessError) as error:
            issues.append(
                OriginalPlanAuditIssueV1(
                    code="tracked_file_index_unavailable",
                    reference=repository.value,
                    detail=str(error),
                )
            )
            tracked_files[repository] = set()
            continue
        tracked_files[repository] = {
            _normalize_relative_reference(path)
            for path in result.stdout.split("\0")
            if path
        }
    return tracked_files, issues


def _audit_original_plan_source(
    manifest: OriginalPlanManifestV1,
    *,
    roots: Mapping[RepositoryName, Path],
    tracked_files: Mapping[RepositoryName, set[str]],
    issues: list[OriginalPlanAuditIssueV1],
) -> bool:
    resolved = _audit_manifest_reference(
        manifest.original_plan_path,
        reference_kind="original_plan",
        roots=roots,
        tracked_files=tracked_files,
        issues=issues,
    )
    if resolved is None or not resolved.is_file():
        return False
    actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if actual_hash != manifest.original_plan_sha256:
        issues.append(
            OriginalPlanAuditIssueV1(
                code="original_plan_sha256_mismatch",
                reference=manifest.original_plan_path,
                detail=f"{actual_hash}!={manifest.original_plan_sha256}",
            )
        )
        return False
    return True


def _audit_manifest_reference(
    reference: str,
    *,
    reference_kind: str,
    roots: Mapping[RepositoryName, Path],
    tracked_files: Mapping[RepositoryName, set[str]],
    issues: list[OriginalPlanAuditIssueV1],
) -> Path | None:
    parsed = _parse_repository_reference(reference)
    if parsed is None:
        issues.append(
            OriginalPlanAuditIssueV1(
                code="manifest_reference_invalid",
                evidence_field=reference_kind,
                reference=reference,
            )
        )
        return None
    repository, relative = parsed
    path = _resolve_repository_path(repository, relative, roots=roots)
    if path is None:
        issues.append(
            OriginalPlanAuditIssueV1(
                code="manifest_reference_path_escape",
                evidence_field=reference_kind,
                reference=reference,
            )
        )
        return None
    if not path.is_file():
        issues.append(
            OriginalPlanAuditIssueV1(
                code="manifest_reference_missing",
                evidence_field=reference_kind,
                reference=reference,
            )
        )
        return path
    if relative not in tracked_files.get(repository, set()):
        issues.append(
            OriginalPlanAuditIssueV1(
                code="manifest_reference_untracked",
                evidence_field=reference_kind,
                reference=reference,
            )
        )
    return path


def _audit_requirement_evidence(
    requirement: OriginalPlanRequirementV1,
    *,
    roots: Mapping[RepositoryName, Path],
    tracked_files: Mapping[RepositoryName, set[str]],
    checked_references: set[str],
    issues: list[OriginalPlanAuditIssueV1],
) -> None:
    evidence = requirement.evidence
    file_fields = {
        "implementation_files": evidence.implementation_files,
        "test_files": evidence.test_files,
        "integration_evidence": evidence.integration_evidence,
        "operational_evidence": evidence.operational_evidence,
        "replacement_contracts": evidence.replacement_contracts,
    }
    for evidence_field, references in file_fields.items():
        for reference in references:
            checked_references.add(reference)
            _audit_evidence_reference(
                requirement,
                evidence_field=evidence_field,
                reference=reference,
                roots=roots,
                tracked_files=tracked_files,
                issues=issues,
            )


def _audit_evidence_reference(
    requirement: OriginalPlanRequirementV1,
    *,
    evidence_field: str,
    reference: str,
    roots: Mapping[RepositoryName, Path],
    tracked_files: Mapping[RepositoryName, set[str]],
    issues: list[OriginalPlanAuditIssueV1],
) -> None:
    parsed = _parse_repository_reference(reference)
    if parsed is None:
        issues.append(
            OriginalPlanAuditIssueV1(
                code="evidence_reference_invalid",
                requirement_id=requirement.requirement_id,
                evidence_field=evidence_field,
                reference=reference,
            )
        )
        return
    repository, relative = parsed
    if repository not in requirement.owners:
        issues.append(
            OriginalPlanAuditIssueV1(
                code="evidence_owner_not_declared",
                requirement_id=requirement.requirement_id,
                evidence_field=evidence_field,
                reference=reference,
            )
        )
    path = _resolve_repository_path(repository, relative, roots=roots)
    if path is None:
        issues.append(
            OriginalPlanAuditIssueV1(
                code="evidence_path_escape",
                requirement_id=requirement.requirement_id,
                evidence_field=evidence_field,
                reference=reference,
            )
        )
        return
    if not path.is_file():
        issues.append(
            OriginalPlanAuditIssueV1(
                code="evidence_file_missing",
                requirement_id=requirement.requirement_id,
                evidence_field=evidence_field,
                reference=reference,
            )
        )
        return
    if relative not in tracked_files.get(repository, set()):
        issues.append(
            OriginalPlanAuditIssueV1(
                code="evidence_file_untracked",
                requirement_id=requirement.requirement_id,
                evidence_field=evidence_field,
                reference=reference,
            )
        )


def _parse_repository_reference(
    reference: str,
) -> tuple[RepositoryName, str] | None:
    normalized = reference.replace("\\", "/")
    for repository in RepositoryName:
        prefix = f"{repository.value}/"
        if normalized.startswith(prefix):
            relative = normalized[len(prefix) :]
            if relative:
                return repository, _normalize_relative_reference(relative)
    return None


def _normalize_relative_reference(reference: str) -> str:
    return PurePosixPath(reference.replace("\\", "/")).as_posix()


def _resolve_repository_path(
    repository: RepositoryName,
    relative: str,
    *,
    roots: Mapping[RepositoryName, Path],
) -> Path | None:
    root = roots.get(repository)
    if root is None:
        return None
    path = (root / Path(*PurePosixPath(relative).parts)).resolve()
    if not path.is_relative_to(root):
        return None
    return path
