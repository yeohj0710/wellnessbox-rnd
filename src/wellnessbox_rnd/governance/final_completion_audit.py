from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from enum import StrEnum
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.governance.original_plan_audit import (
    OriginalPlanAuditStatus,
    audit_original_plan_manifest_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    EvidenceStage,
    RepositoryName,
    load_original_plan_manifest_v1,
    materialize_original_plan_requirements_v1,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinalCompletionStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class FinalCompletionFactsV1(_StrictModel):
    requirement_count: int
    claimed_requirement_count: int
    nonexternal_stage_gap_ids: list[str] = Field(default_factory=list)
    external_validation_gap_ids: list[str] = Field(default_factory=list)
    report_count: int
    missing_report_ids: list[str] = Field(default_factory=list)
    canonical_evidence_audit_passed: bool
    validation_receipt_valid: bool
    independent_review_receipt_valid: bool


class FinalCompletionAuditV1(_StrictModel):
    status: FinalCompletionStatus
    goal_complete: bool
    facts: FinalCompletionFactsV1
    blockers: list[str] = Field(default_factory=list)


class FinalAuditPolicyV1(_StrictModel):
    schema_version: str
    required_requirement_count: int
    required_report_count: int
    validation_receipt_path: str | None
    independent_review_receipt_path: str | None
    trusted_issuers: list[TrustedIssuerV1] = Field(default_factory=list)


class TrustedIssuerV1(_StrictModel):
    issuer_id: str
    public_key_ed25519_base64: str


class CompletionReceiptV1(_StrictModel):
    schema_version: str
    status: str
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_audit_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issuer_id: str
    signature_ed25519_base64: str


class IndependentReviewReceiptV1(CompletionReceiptV1):
    critical_count: int
    important_count: int


def evaluate_final_completion_facts_v1(
    facts: FinalCompletionFactsV1,
) -> FinalCompletionAuditV1:
    blockers: list[str] = []
    if facts.requirement_count != 120:
        blockers.append(f"requirement_count:{facts.requirement_count}!=120")
    if facts.claimed_requirement_count != 120:
        blockers.append(f"claimed_requirement_count:{facts.claimed_requirement_count}!=120")
    if facts.nonexternal_stage_gap_ids:
        blockers.append(f"nonexternal_stage_gaps:{len(facts.nonexternal_stage_gap_ids)}")
    if facts.external_validation_gap_ids:
        blockers.append(f"external_validation_gaps:{len(facts.external_validation_gap_ids)}")
    if facts.report_count != 120 or facts.missing_report_ids:
        blockers.append(f"research_report_gaps:{len(facts.missing_report_ids)}")
    if not facts.canonical_evidence_audit_passed:
        blockers.append("canonical_evidence_audit_failed")
    if not facts.validation_receipt_valid:
        blockers.append("validation_receipt_missing_or_invalid")
    if not facts.independent_review_receipt_valid:
        blockers.append("independent_review_receipt_missing_or_invalid")
    status = FinalCompletionStatus.READY if not blockers else FinalCompletionStatus.BLOCKED
    return FinalCompletionAuditV1(
        status=status,
        goal_complete=status == FinalCompletionStatus.READY,
        facts=facts,
        blockers=blockers,
    )


def audit_final_completion_v1(
    *,
    manifest_path: str | Path,
    reports_dir: str | Path,
    policy_path: str | Path,
    repository_roots: dict[RepositoryName | str, str | Path],
) -> FinalCompletionAuditV1:
    manifest = load_original_plan_manifest_v1(manifest_path)
    requirements = materialize_original_plan_requirements_v1(manifest)
    canonical_audit = audit_original_plan_manifest_v1(manifest, repository_roots=repository_roots)
    stage_rank = {
        EvidenceStage.IMPLEMENTED: 1,
        EvidenceStage.INTEGRATED: 2,
        EvidenceStage.OPERATED: 3,
    }
    nonexternal_gaps = [
        item.requirement_id
        for item in requirements
        if item.required_stage != EvidenceStage.EXTERNAL
        and (
            item.claimed_stage not in stage_rank
            or stage_rank[item.claimed_stage] < stage_rank[item.required_stage]
        )
    ]
    external_gaps = [
        item.requirement_id
        for item in requirements
        if item.required_stage == EvidenceStage.EXTERNAL
        and item.claimed_stage != EvidenceStage.EXTERNAL
    ]
    report_root = Path(reports_dir)
    missing_reports = [
        item.requirement_id
        for item in requirements
        if not _valid_research_report(
            report_root / f"{item.requirement_id}.md",
            item.requirement_id,
            [
                reference
                for references in item.evidence.model_dump().values()
                if isinstance(references, list)
                for reference in references
                if isinstance(reference, str) and "/" in reference
            ],
        )
    ]
    policy = FinalAuditPolicyV1.model_validate_json(Path(policy_path).read_text(encoding="utf-8"))
    if policy.schema_version != "op120_final_audit_policy_v1":
        raise ValueError(f"unsupported final audit policy: {policy.schema_version}")
    canonical_audit_sha256 = hashlib.sha256(
        canonical_audit.model_dump_json().encode("utf-8")
    ).hexdigest()
    manifest_sha256 = canonical_audit.manifest_sha256
    facts = FinalCompletionFactsV1(
        requirement_count=len(requirements),
        claimed_requirement_count=sum(item.claimed_stage is not None for item in requirements),
        nonexternal_stage_gap_ids=nonexternal_gaps,
        external_validation_gap_ids=external_gaps,
        report_count=len(requirements) - len(missing_reports),
        missing_report_ids=missing_reports,
        canonical_evidence_audit_passed=canonical_audit.status == OriginalPlanAuditStatus.PASS,
        validation_receipt_valid=_receipt_valid(
            policy.validation_receipt_path,
            repository_roots,
            manifest_sha256,
            canonical_audit_sha256,
            policy.trusted_issuers,
        ),
        independent_review_receipt_valid=_review_receipt_valid(
            policy.independent_review_receipt_path,
            repository_roots,
            manifest_sha256,
            canonical_audit_sha256,
            policy.trusted_issuers,
        ),
    )
    if policy.required_requirement_count != 120 or policy.required_report_count != 120:
        raise ValueError("final audit policy must require exactly 120 requirements and reports")
    return evaluate_final_completion_facts_v1(facts)


def _receipt_valid(
    reference: object,
    repository_roots: dict[RepositoryName | str, str | Path],
    manifest_sha256: str,
    canonical_audit_sha256: str,
    trusted_issuers: list[TrustedIssuerV1],
) -> bool:
    resolved = _trusted_receipt_path(reference, repository_roots)
    if resolved is None:
        return False
    try:
        receipt = CompletionReceiptV1.model_validate_json(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        receipt.schema_version == "final_validation_receipt_v1"
        and receipt.status == "PASS"
        and receipt.manifest_sha256 == manifest_sha256
        and receipt.canonical_audit_sha256 == canonical_audit_sha256
        and receipt.source_commit
        in {_git_head(Path(root).resolve()) for root in repository_roots.values()}
        and _signature_valid(receipt, trusted_issuers)
    )


def _review_receipt_valid(
    reference: object,
    repository_roots: dict[RepositoryName | str, str | Path],
    manifest_sha256: str,
    canonical_audit_sha256: str,
    trusted_issuers: list[TrustedIssuerV1],
) -> bool:
    resolved = _trusted_receipt_path(reference, repository_roots)
    if resolved is None:
        return False
    try:
        receipt = IndependentReviewReceiptV1.model_validate_json(
            resolved.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return (
        receipt.schema_version == "independent_final_review_receipt_v1"
        and receipt.status == "PASS"
        and receipt.manifest_sha256 == manifest_sha256
        and receipt.canonical_audit_sha256 == canonical_audit_sha256
        and receipt.critical_count == 0
        and receipt.important_count == 0
        and receipt.source_commit
        in {_git_head(Path(root).resolve()) for root in repository_roots.values()}
        and _signature_valid(receipt, trusted_issuers)
    )


def _trusted_receipt_path(
    reference: object,
    repository_roots: dict[RepositoryName | str, str | Path],
) -> Path | None:
    if not isinstance(reference, str) or "/" not in reference:
        return None
    repository_name, relative = reference.split("/", 1)
    try:
        repository = RepositoryName(repository_name)
    except ValueError:
        return None
    roots = {
        RepositoryName(str(key)): Path(value).resolve() for key, value in repository_roots.items()
    }
    root = roots.get(repository)
    if root is None:
        return None
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", relative],
        capture_output=True,
        check=False,
    )
    return path if tracked.returncode == 0 else None


def _git_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def _valid_research_report(path: Path, requirement_id: str, evidence_references: list[str]) -> bool:
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    lines = content.splitlines()
    headings = [line for line in lines if line.startswith("## ")]
    section_bodies = [
        body.strip() for body in "\n".join(lines[1:]).split("\n## ")[1:] if "\n" in body
    ]
    semantic_groups = (
        ("요구", "문제"),
        ("검증", "테스트"),
        ("증거", "evidence"),
        ("완료", "단계", "stage", "한계"),
    )
    return (
        len(content.strip()) >= 500
        and lines[0].startswith(f"# {requirement_id} ")
        and len(headings) >= 3
        and len(headings) == len(set(headings))
        and len(section_bodies) == len(headings)
        and all(len(body) >= 80 for body in section_bodies)
        and sum(any(keyword in content for keyword in group) for group in semantic_groups) >= 3
        and any(
            reference in content or reference.split("/", 1)[1] in content
            for reference in evidence_references
        )
    )


def _signature_valid(receipt: CompletionReceiptV1, trusted_issuers: list[TrustedIssuerV1]) -> bool:
    issuer = next((item for item in trusted_issuers if item.issuer_id == receipt.issuer_id), None)
    if issuer is None:
        return False
    unsigned = receipt.model_dump(exclude={"signature_ed25519_base64"}, mode="json")
    message = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(issuer.public_key_ed25519_base64, validate=True)
        )
        public_key.verify(
            base64.b64decode(receipt.signature_ed25519_base64, validate=True), message
        )
    except (ValueError, InvalidSignature):
        return False
    return True
