from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.schemas.original_plan_manifest import (
    ORIGINAL_PLAN_MANIFEST_SCHEMA_VERSION_V1,
    EvidenceStage,
    OriginalPlanRequirementV1,
    RequirementEvidenceV1,
    load_original_plan_manifest_v1,
    materialize_original_plan_requirements_v1,
    validate_original_plan_manifest_v1,
    validate_requirement_evidence_v1,
)

MANIFEST_PATH = Path("data/original_plan/requirements_manifest_v1.json")


def test_original_plan_manifest_covers_all_120_requirements_without_gaps() -> None:
    manifest = load_original_plan_manifest_v1(MANIFEST_PATH)
    requirements = materialize_original_plan_requirements_v1(manifest)

    assert manifest.schema_version == ORIGINAL_PLAN_MANIFEST_SCHEMA_VERSION_V1
    assert manifest.original_plan_sha256 == (
        "31291e6f93977fa2d5d083d0161743c49debef25caf12dccf6edc7fa1c2197d4"
    )
    assert [item.requirement_id for item in requirements] == [
        f"OP-{index:03d}" for index in range(1, 121)
    ]
    assert {item.group_id for item in requirements} == set("ABCDEFGHIJKL")
    assert all(item.source_refs for item in requirements)
    assert all(item.owners for item in requirements)
    assert validate_original_plan_manifest_v1(manifest) == []


def test_original_plan_manifest_claims_only_currently_evidenced_steps() -> None:
    manifest = load_original_plan_manifest_v1(MANIFEST_PATH)
    requirements = materialize_original_plan_requirements_v1(manifest)
    claimed = {
        item.requirement_id: item.claimed_stage
        for item in requirements
        if item.claimed_stage is not None
    }

    assert claimed == {
        "OP-001": EvidenceStage.IMPLEMENTED,
        "OP-002": EvidenceStage.IMPLEMENTED,
        "OP-003": EvidenceStage.IMPLEMENTED,
        "OP-004": EvidenceStage.IMPLEMENTED,
        "OP-005": EvidenceStage.IMPLEMENTED,
        "OP-006": EvidenceStage.IMPLEMENTED,
        "OP-007": EvidenceStage.IMPLEMENTED,
        "OP-008": EvidenceStage.IMPLEMENTED,
        "OP-009": EvidenceStage.IMPLEMENTED,
        "OP-010": EvidenceStage.IMPLEMENTED,
        "OP-011": EvidenceStage.IMPLEMENTED,
        "OP-012": EvidenceStage.IMPLEMENTED,
        "OP-013": EvidenceStage.IMPLEMENTED,
        "OP-014": EvidenceStage.IMPLEMENTED,
        "OP-015": EvidenceStage.IMPLEMENTED,
        "OP-016": EvidenceStage.IMPLEMENTED,
        "OP-017": EvidenceStage.IMPLEMENTED,
        "OP-018": EvidenceStage.IMPLEMENTED,
        "OP-019": EvidenceStage.INTEGRATED,
        "OP-020": EvidenceStage.INTEGRATED,
        "OP-021": EvidenceStage.IMPLEMENTED,
        "OP-022": EvidenceStage.IMPLEMENTED,
        "OP-023": EvidenceStage.IMPLEMENTED,
        "OP-024": EvidenceStage.IMPLEMENTED,
        "OP-025": EvidenceStage.IMPLEMENTED,
        "OP-026": EvidenceStage.IMPLEMENTED,
        "OP-027": EvidenceStage.IMPLEMENTED,
        "OP-028": EvidenceStage.IMPLEMENTED,
        "OP-029": EvidenceStage.IMPLEMENTED,
        "OP-030": EvidenceStage.IMPLEMENTED,
        "OP-031": EvidenceStage.IMPLEMENTED,
        "OP-032": EvidenceStage.IMPLEMENTED,
        "OP-033": EvidenceStage.IMPLEMENTED,
        "OP-034": EvidenceStage.IMPLEMENTED,
        "OP-035": EvidenceStage.IMPLEMENTED,
        "OP-036": EvidenceStage.IMPLEMENTED,
        "OP-037": EvidenceStage.IMPLEMENTED,
        "OP-038": EvidenceStage.IMPLEMENTED,
        "OP-040": EvidenceStage.INTEGRATED,
        "OP-041": EvidenceStage.INTEGRATED,
        "OP-042": EvidenceStage.IMPLEMENTED,
        "OP-043": EvidenceStage.IMPLEMENTED,
        "OP-044": EvidenceStage.IMPLEMENTED,
        "OP-045": EvidenceStage.IMPLEMENTED,
        "OP-046": EvidenceStage.IMPLEMENTED,
        "OP-047": EvidenceStage.IMPLEMENTED,
        "OP-048": EvidenceStage.IMPLEMENTED,
        "OP-049": EvidenceStage.IMPLEMENTED,
        "OP-050": EvidenceStage.INTEGRATED,
        "OP-051": EvidenceStage.IMPLEMENTED,
        "OP-052": EvidenceStage.IMPLEMENTED,
        "OP-053": EvidenceStage.IMPLEMENTED,
        "OP-054": EvidenceStage.IMPLEMENTED,
        "OP-055": EvidenceStage.IMPLEMENTED,
        "OP-056": EvidenceStage.IMPLEMENTED,
        "OP-057": EvidenceStage.INTEGRATED,
        "OP-058": EvidenceStage.INTEGRATED,
        "OP-059": EvidenceStage.INTEGRATED,
        "OP-060": EvidenceStage.INTEGRATED,
        "OP-061": EvidenceStage.IMPLEMENTED,
        "OP-062": EvidenceStage.INTEGRATED,
        "OP-063": EvidenceStage.INTEGRATED,
        "OP-064": EvidenceStage.INTEGRATED,
        "OP-065": EvidenceStage.INTEGRATED,
        "OP-066": EvidenceStage.INTEGRATED,
        "OP-067": EvidenceStage.INTEGRATED,
        "OP-068": EvidenceStage.INTEGRATED,
        "OP-069": EvidenceStage.INTEGRATED,
        "OP-070": EvidenceStage.INTEGRATED,
        "OP-071": EvidenceStage.IMPLEMENTED,
        "OP-072": EvidenceStage.IMPLEMENTED,
            "OP-073": EvidenceStage.IMPLEMENTED,
            "OP-074": EvidenceStage.IMPLEMENTED,
            "OP-075": EvidenceStage.IMPLEMENTED,
            "OP-076": EvidenceStage.IMPLEMENTED,
            "OP-077": EvidenceStage.IMPLEMENTED,
            "OP-078": EvidenceStage.IMPLEMENTED,
        }


def test_implemented_claim_requires_implementation_and_test_evidence() -> None:
    requirement = OriginalPlanRequirementV1(
        requirement_id="OP-031",
        group_id="D",
        title="알레르기 규칙을 추천 전에 적용한다.",
        source_refs=["docs/context/original_plan.pdf#page=17"],
        owners=["wellnessbox-rnd"],
        required_stage=EvidenceStage.OPERATED,
        claimed_stage=EvidenceStage.IMPLEMENTED,
        evidence=RequirementEvidenceV1(),
    )

    assert validate_requirement_evidence_v1(requirement) == [
        "OP-031:implemented_claim_missing_implementation_files",
        "OP-031:implemented_claim_missing_test_files",
    ]


def test_operated_claim_requires_integration_and_operational_evidence() -> None:
    requirement = OriginalPlanRequirementV1(
        requirement_id="OP-040",
        group_id="D",
        title="프로덕션 추천 경로에서 안전 엔진의 최종 차단 권한을 검증한다.",
        source_refs=["docs/context/original_plan.pdf#page=17"],
        owners=["wellnessbox-rnd", "wellnessbox"],
        required_stage=EvidenceStage.OPERATED,
        claimed_stage=EvidenceStage.OPERATED,
        evidence=RequirementEvidenceV1(
            implementation_files=["wellnessbox-rnd/src/wellnessbox_rnd/safety/service.py"],
            test_files=["wellnessbox-rnd/tests/test_inference_api.py"],
        ),
    )

    assert validate_requirement_evidence_v1(requirement) == [
        "OP-040:integrated_claim_missing_integration_evidence",
        "OP-040:operated_claim_missing_operational_evidence",
    ]


def test_external_claim_requires_dependency_and_replacement_contract() -> None:
    requirement = OriginalPlanRequirementV1(
        requirement_id="OP-039",
        group_id="D",
        title="고위험 frozen eval을 외부 라벨로 검증한다.",
        source_refs=["docs/context/original_plan.pdf#page=25"],
        owners=["wellnessbox-rnd"],
        required_stage=EvidenceStage.EXTERNAL,
        claimed_stage=EvidenceStage.EXTERNAL,
        evidence=RequirementEvidenceV1(),
    )

    assert validate_requirement_evidence_v1(requirement) == [
        "OP-039:external_claim_missing_external_dependencies",
        "OP-039:external_claim_missing_replacement_contracts",
    ]


def test_evidence_stage_rejects_unrecognized_completion_wording() -> None:
    with pytest.raises(ValidationError):
        OriginalPlanRequirementV1(
            requirement_id="OP-001",
            group_id="A",
            title="원본 해시를 확인한다.",
            source_refs=["docs/context/original_plan.pdf"],
            owners=["wellnessbox-rnd"],
            required_stage="DONE",
        )


def test_requirement_schema_rejects_unrecognized_fields() -> None:
    with pytest.raises(ValidationError):
        OriginalPlanRequirementV1.model_validate(
            {
                "requirement_id": "OP-001",
                "group_id": "A",
                "title": "원본 해시를 확인한다.",
                "source_refs": ["docs/context/original_plan.pdf"],
                "owners": ["wellnessbox-rnd"],
                "required_stage": "IMPLEMENTED",
                "unsupported_completion_flag": True,
            }
        )
