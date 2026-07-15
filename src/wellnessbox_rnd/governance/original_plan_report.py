from __future__ import annotations

import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.governance.original_plan_audit import (
    OriginalPlanAuditReportV1,
    OriginalPlanAuditStatus,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    EvidenceStage,
    OriginalPlanManifestV1,
    OriginalPlanRequirementV1,
    RequirementEvidenceV1,
    calculate_original_plan_manifest_sha256_v1,
    materialize_original_plan_requirements_v1,
)

ORIGINAL_PLAN_COMPLETION_REPORT_SCHEMA_VERSION_V1 = "original_plan_completion_v1"


class CompletionDisposition(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"
    EXTERNAL = "EXTERNAL"
    CONTRADICTED = "CONTRADICTED"


class _StrictReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementCompletionV1(_StrictReportModel):
    requirement_id: str
    group_id: str
    title: str
    source_refs: list[str]
    required_stage: EvidenceStage
    claimed_stage: EvidenceStage | None
    disposition: CompletionDisposition
    reasons: list[str] = Field(default_factory=list)
    evidence: RequirementEvidenceV1


class GroupCompletionSummaryV1(_StrictReportModel):
    group_id: str
    title: str
    requirement_count: int
    disposition_counts: dict[CompletionDisposition, int]


class OriginalPlanCompletionReportV1(_StrictReportModel):
    schema_version: str = ORIGINAL_PLAN_COMPLETION_REPORT_SCHEMA_VERSION_V1
    manifest_schema_version: str
    audited_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_plan_path: str
    original_plan_sha256: str
    audit_status: OriginalPlanAuditStatus
    audit_issue_count: int
    requirement_count: int
    disposition_counts: dict[CompletionDisposition, int]
    group_summaries: list[GroupCompletionSummaryV1]
    requirements: list[RequirementCompletionV1]
    global_audit_issues: list[str] = Field(default_factory=list)


_STAGE_RANK = {
    EvidenceStage.IMPLEMENTED: 1,
    EvidenceStage.INTEGRATED: 2,
    EvidenceStage.OPERATED: 3,
}

_DISPOSITION_LABELS = {
    CompletionDisposition.COMPLETE: "완료",
    CompletionDisposition.PARTIAL: "부분 완료",
    CompletionDisposition.PENDING: "대기",
    CompletionDisposition.EXTERNAL: "외부 검증",
    CompletionDisposition.CONTRADICTED: "모순",
}

_STAGE_LABELS = {
    EvidenceStage.IMPLEMENTED: "구현 검증",
    EvidenceStage.INTEGRATED: "통합 검증",
    EvidenceStage.OPERATED: "운영 검증",
    EvidenceStage.EXTERNAL: "외부 검증",
}

_REASON_LABELS = {
    "audited_evidence_meets_required_stage": "감사된 증거가 요구 단계를 충족함",
    "claimed_stage_below_required_stage": "현재 증거 단계가 요구 단계보다 낮음",
    "completion_claim_missing": "완료 증거가 아직 등록되지 않음",
    "external_validation_required": "외부 기관·실기기·법적 검증이 필요함",
    "global_audit_failed": "원본 또는 manifest 공통 감사가 실패함",
}


def build_original_plan_completion_report_v1(
    manifest: OriginalPlanManifestV1,
    audit_report: OriginalPlanAuditReportV1,
) -> OriginalPlanCompletionReportV1:
    requirements = materialize_original_plan_requirements_v1(manifest)
    if audit_report.manifest_schema_version != manifest.schema_version:
        raise ValueError("audit_manifest_schema_version_mismatch")
    if audit_report.requirement_count != len(requirements):
        raise ValueError("audit_requirement_count_mismatch")
    manifest_sha256 = calculate_original_plan_manifest_sha256_v1(manifest)
    if audit_report.manifest_sha256 != manifest_sha256:
        raise ValueError("audit_manifest_sha256_mismatch")

    requirement_issue_codes: dict[str, list[str]] = {}
    global_issue_codes: list[str] = []
    for issue in audit_report.issues:
        if issue.requirement_id is None:
            global_issue_codes.append(issue.code)
        else:
            requirement_issue_codes.setdefault(issue.requirement_id, []).append(issue.code)

    items = [
        _build_requirement_completion(
            requirement,
            requirement_issue_codes=requirement_issue_codes,
            global_audit_failed=bool(global_issue_codes),
        )
        for requirement in requirements
    ]
    disposition_counts = _count_dispositions(items)
    group_summaries = [
        GroupCompletionSummaryV1(
            group_id=group.group_id,
            title=group.title,
            requirement_count=len(group.requirements),
            disposition_counts=_count_dispositions(
                [item for item in items if item.group_id == group.group_id]
            ),
        )
        for group in manifest.groups
    ]
    return OriginalPlanCompletionReportV1(
        manifest_schema_version=manifest.schema_version,
        audited_manifest_sha256=manifest_sha256,
        original_plan_path=manifest.original_plan_path,
        original_plan_sha256=manifest.original_plan_sha256,
        audit_status=audit_report.status,
        audit_issue_count=len(audit_report.issues),
        requirement_count=len(items),
        disposition_counts=disposition_counts,
        group_summaries=group_summaries,
        requirements=items,
        global_audit_issues=global_issue_codes,
    )


def serialize_original_plan_completion_report_json_v1(
    report: OriginalPlanCompletionReportV1,
) -> str:
    return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"


def render_original_plan_completion_report_markdown_v1(
    report: OriginalPlanCompletionReportV1,
) -> str:
    lines = [
        "# 원계획 요구사항 완료 현황",
        "",
        "> 이 문서는 `requirements_manifest_v1.json`과 실제 증거 감사 결과에서 자동 생성됩니다.",
        "> 수동으로 상태를 수정하지 말고 manifest 증거와 구현을 먼저 갱신해야 합니다.",
        "",
        "## 전체 판정",
        "",
        (
            "- 증거 감사: "
            f"**{'통과' if report.audit_status == OriginalPlanAuditStatus.PASS else '실패'}**"
        ),
        f"- 원계획 요구사항 포함: **{report.requirement_count}/{report.requirement_count}건**",
        f"- 감사 이슈: **{report.audit_issue_count}건**",
        "- 전체 완료는 모든 비외부 요구사항이 요구 증거 단계를 충족해야 성립합니다.",
        "",
        "| 상태 | 건수 | 판정 기준 |",
        "| --- | ---: | --- |",
    ]
    criteria = {
        CompletionDisposition.COMPLETE: "감사된 증거가 요구 단계 이상임",
        CompletionDisposition.PARTIAL: "증거는 있으나 요구 단계보다 낮음",
        CompletionDisposition.PENDING: "완료 증거가 등록되지 않음",
        CompletionDisposition.EXTERNAL: "외부 기관·실기기·법적 검증이 필요함",
        CompletionDisposition.CONTRADICTED: "등록된 완료 증거가 감사 결과와 충돌함",
    }
    for disposition in CompletionDisposition:
        lines.append(
            f"| {_DISPOSITION_LABELS[disposition]} | "
            f"{report.disposition_counts[disposition]} | {criteria[disposition]} |"
        )

    lines.extend(
        [
            "",
            "## 그룹별 현황",
            "",
            "| 그룹 | 요구사항 | 완료 | 부분 완료 | 대기 | 외부 검증 | 모순 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group in report.group_summaries:
        counts = group.disposition_counts
        lines.append(
            f"| {group.group_id}. {group.title} | {group.requirement_count} | "
            f"{counts[CompletionDisposition.COMPLETE]} | "
            f"{counts[CompletionDisposition.PARTIAL]} | "
            f"{counts[CompletionDisposition.PENDING]} | "
            f"{counts[CompletionDisposition.EXTERNAL]} | "
            f"{counts[CompletionDisposition.CONTRADICTED]} |"
        )

    if report.global_audit_issues:
        lines.extend(["", "## 공통 감사 이슈", ""])
        lines.extend(f"- `{issue}`" for issue in report.global_audit_issues)

    for disposition in CompletionDisposition:
        matching = [item for item in report.requirements if item.disposition == disposition]
        lines.extend(
            [
                "",
                f"## {_DISPOSITION_LABELS[disposition]} ({len(matching)}건)",
                "",
            ]
        )
        if not matching:
            lines.append("- 없음")
            continue
        for item in matching:
            claimed_stage = (
                _STAGE_LABELS[item.claimed_stage] if item.claimed_stage is not None else "등록 없음"
            )
            reasons = ", ".join(
                _REASON_LABELS.get(reason, f"감사 이슈 `{reason}`")
                for reason in item.reasons
            )
            lines.append(
                f"- `{item.requirement_id}` [{item.group_id}] {item.title} "
                f"(요구: {_STAGE_LABELS[item.required_stage]}, 현재: {claimed_stage}; {reasons})"
            )

    return "\n".join(lines) + "\n"


def _build_requirement_completion(
    requirement: OriginalPlanRequirementV1,
    *,
    requirement_issue_codes: dict[str, list[str]],
    global_audit_failed: bool,
) -> RequirementCompletionV1:
    issue_codes = requirement_issue_codes.get(requirement.requirement_id, [])
    if issue_codes or (global_audit_failed and requirement.claimed_stage is not None):
        disposition = CompletionDisposition.CONTRADICTED
        reason_codes = (
            [*issue_codes, "global_audit_failed"]
            if global_audit_failed
            else issue_codes
        )
        reasons = list(dict.fromkeys(reason_codes))
    elif (
        requirement.required_stage == EvidenceStage.EXTERNAL
        or requirement.claimed_stage == EvidenceStage.EXTERNAL
    ):
        disposition = CompletionDisposition.EXTERNAL
        reasons = ["external_validation_required"]
    elif requirement.claimed_stage is None:
        disposition = CompletionDisposition.PENDING
        reasons = ["completion_claim_missing"]
    elif _STAGE_RANK[requirement.claimed_stage] >= _STAGE_RANK[requirement.required_stage]:
        disposition = CompletionDisposition.COMPLETE
        reasons = ["audited_evidence_meets_required_stage"]
    else:
        disposition = CompletionDisposition.PARTIAL
        reasons = ["claimed_stage_below_required_stage"]

    return RequirementCompletionV1(
        requirement_id=requirement.requirement_id,
        group_id=requirement.group_id,
        title=requirement.title,
        source_refs=requirement.source_refs,
        required_stage=requirement.required_stage,
        claimed_stage=requirement.claimed_stage,
        disposition=disposition,
        reasons=reasons,
        evidence=requirement.evidence,
    )


def _count_dispositions(
    requirements: list[RequirementCompletionV1],
) -> dict[CompletionDisposition, int]:
    return {
        disposition: sum(item.disposition == disposition for item in requirements)
        for disposition in CompletionDisposition
    }
