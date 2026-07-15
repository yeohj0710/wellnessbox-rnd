from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

ORIGINAL_PLAN_MANIFEST_SCHEMA_VERSION_V1 = "original_plan_requirements_v1"
DEFAULT_ORIGINAL_PLAN_MANIFEST_PATH = Path(
    "data/original_plan/requirements_manifest_v1.json"
)
_EXPECTED_REQUIREMENT_IDS = [f"OP-{index:03d}" for index in range(1, 121)]
_EXPECTED_GROUP_IDS = list("ABCDEFGHIJKL")


class _StrictManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RepositoryName(StrEnum):
    WELLNESSBOX_RND = "wellnessbox-rnd"
    WELLNESSBOX = "wellnessbox"


class EvidenceStage(StrEnum):
    IMPLEMENTED = "IMPLEMENTED"
    INTEGRATED = "INTEGRATED"
    OPERATED = "OPERATED"
    EXTERNAL = "EXTERNAL"


class RequirementEvidenceV1(_StrictManifestModel):
    implementation_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    integration_evidence: list[str] = Field(default_factory=list)
    operational_evidence: list[str] = Field(default_factory=list)
    external_dependencies: list[str] = Field(default_factory=list)
    replacement_contracts: list[str] = Field(default_factory=list)


class OriginalPlanRequirementDraftV1(_StrictManifestModel):
    requirement_id: str = Field(pattern=r"^OP-\d{3}$")
    title: str = Field(min_length=1)
    source_refs: list[str] | None = None
    owners: list[RepositoryName] | None = None
    required_stage: EvidenceStage | None = None
    claimed_stage: EvidenceStage | None = None
    evidence: RequirementEvidenceV1 = Field(default_factory=RequirementEvidenceV1)


class OriginalPlanRequirementGroupV1(_StrictManifestModel):
    group_id: str = Field(pattern=r"^[A-L]$")
    title: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    owners: list[RepositoryName] = Field(min_length=1)
    default_required_stage: EvidenceStage
    requirements: list[OriginalPlanRequirementDraftV1] = Field(min_length=1)


class OriginalPlanManifestV1(_StrictManifestModel):
    schema_version: str = ORIGINAL_PLAN_MANIFEST_SCHEMA_VERSION_V1
    original_plan_path: str
    original_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completion_program_path: str
    groups: list[OriginalPlanRequirementGroupV1] = Field(min_length=1)


class OriginalPlanRequirementV1(_StrictManifestModel):
    requirement_id: str = Field(pattern=r"^OP-\d{3}$")
    group_id: str = Field(pattern=r"^[A-L]$")
    title: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    owners: list[RepositoryName] = Field(min_length=1)
    required_stage: EvidenceStage
    claimed_stage: EvidenceStage | None = None
    evidence: RequirementEvidenceV1 = Field(default_factory=RequirementEvidenceV1)


def load_original_plan_manifest_v1(
    path: str | Path = DEFAULT_ORIGINAL_PLAN_MANIFEST_PATH,
) -> OriginalPlanManifestV1:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return OriginalPlanManifestV1.model_validate(payload)


def materialize_original_plan_requirements_v1(
    manifest: OriginalPlanManifestV1,
) -> list[OriginalPlanRequirementV1]:
    return [
        OriginalPlanRequirementV1(
            requirement_id=requirement.requirement_id,
            group_id=group.group_id,
            title=requirement.title,
            source_refs=list(requirement.source_refs or group.source_refs),
            owners=list(requirement.owners or group.owners),
            required_stage=requirement.required_stage or group.default_required_stage,
            claimed_stage=requirement.claimed_stage,
            evidence=requirement.evidence,
        )
        for group in manifest.groups
        for requirement in group.requirements
    ]


def validate_requirement_evidence_v1(
    requirement: OriginalPlanRequirementV1,
) -> list[str]:
    claimed_stage = requirement.claimed_stage
    if claimed_stage is None:
        return []

    issues: list[str] = []
    evidence = requirement.evidence
    if claimed_stage in {
        EvidenceStage.IMPLEMENTED,
        EvidenceStage.INTEGRATED,
        EvidenceStage.OPERATED,
    }:
        if not evidence.implementation_files:
            issues.append(
                f"{requirement.requirement_id}:implemented_claim_missing_implementation_files"
            )
        if not evidence.test_files:
            issues.append(f"{requirement.requirement_id}:implemented_claim_missing_test_files")
    if claimed_stage in {EvidenceStage.INTEGRATED, EvidenceStage.OPERATED}:
        if not evidence.integration_evidence:
            issues.append(
                f"{requirement.requirement_id}:integrated_claim_missing_integration_evidence"
            )
    if claimed_stage == EvidenceStage.OPERATED and not evidence.operational_evidence:
        issues.append(
            f"{requirement.requirement_id}:operated_claim_missing_operational_evidence"
        )
    if claimed_stage == EvidenceStage.EXTERNAL:
        if not evidence.external_dependencies:
            issues.append(
                f"{requirement.requirement_id}:external_claim_missing_external_dependencies"
            )
        if not evidence.replacement_contracts:
            issues.append(
                f"{requirement.requirement_id}:external_claim_missing_replacement_contracts"
            )
    return issues


def validate_original_plan_manifest_v1(
    manifest: OriginalPlanManifestV1,
) -> list[str]:
    issues: list[str] = []
    if manifest.schema_version != ORIGINAL_PLAN_MANIFEST_SCHEMA_VERSION_V1:
        issues.append(f"unsupported_schema_version:{manifest.schema_version}")

    group_ids = [group.group_id for group in manifest.groups]
    if group_ids != _EXPECTED_GROUP_IDS:
        issues.append(f"group_id_sequence_mismatch:{','.join(group_ids)}")

    requirements = materialize_original_plan_requirements_v1(manifest)
    requirement_ids = [item.requirement_id for item in requirements]
    if requirement_ids != _EXPECTED_REQUIREMENT_IDS:
        issues.append("requirement_id_sequence_mismatch")
    if len(requirement_ids) != len(set(requirement_ids)):
        issues.append("duplicate_requirement_ids")

    for group in manifest.groups:
        if len(group.requirements) != 10:
            issues.append(f"{group.group_id}:requirement_count:{len(group.requirements)}!=10")
    for requirement in requirements:
        issues.extend(validate_requirement_evidence_v1(requirement))
    return issues
