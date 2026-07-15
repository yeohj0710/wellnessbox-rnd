from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from wellnessbox_rnd.governance.original_plan_audit import audit_original_plan_manifest_v1
from wellnessbox_rnd.governance.original_plan_report import (
    CompletionDisposition,
    build_original_plan_completion_report_v1,
    render_original_plan_completion_report_markdown_v1,
)
from wellnessbox_rnd.schemas.original_plan_manifest import (
    EvidenceStage,
    RepositoryName,
    load_original_plan_manifest_v1,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOTS = {RepositoryName.WELLNESSBOX_RND: REPOSITORY_ROOT}
SCRIPT_PATH = Path("scripts/build_original_plan_completion_report.py")


def _manifest_copy():
    return load_original_plan_manifest_v1().model_copy(deep=True)


def _draft_by_id(manifest, requirement_id: str):
    return next(
        requirement
        for group in manifest.groups
        for requirement in group.requirements
        if requirement.requirement_id == requirement_id
    )


def _completion_by_id(report, requirement_id: str):
    return next(
        requirement
        for requirement in report.requirements
        if requirement.requirement_id == requirement_id
    )


def test_current_report_covers_all_requirements_without_inflating_completion() -> None:
    manifest = _manifest_copy()
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)

    report = build_original_plan_completion_report_v1(manifest, audit)

    assert report.requirement_count == 120
    assert report.disposition_counts == {
        CompletionDisposition.COMPLETE: 21,
        CompletionDisposition.PARTIAL: 0,
        CompletionDisposition.PENDING: 98,
        CompletionDisposition.EXTERNAL: 1,
        CompletionDisposition.CONTRADICTED: 0,
    }
    assert _completion_by_id(report, "OP-010").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-011").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-013").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-014").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-015").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-016").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-017").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-018").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-019").disposition == CompletionDisposition.PENDING
    assert _completion_by_id(report, "OP-020").disposition == CompletionDisposition.COMPLETE
    assert _completion_by_id(report, "OP-039").disposition == CompletionDisposition.EXTERNAL


def test_report_marks_lower_valid_stage_as_partial() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-019")
    requirement.claimed_stage = EvidenceStage.IMPLEMENTED
    requirement.evidence.implementation_files = [
        "wellnessbox-rnd/src/wellnessbox_rnd/schemas/original_plan_manifest.py"
    ]
    requirement.evidence.test_files = [
        "wellnessbox-rnd/tests/test_original_plan_manifest.py"
    ]
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)

    report = build_original_plan_completion_report_v1(manifest, audit)

    assert _completion_by_id(report, "OP-019").disposition == CompletionDisposition.PARTIAL


def test_report_downgrades_broken_completion_claim_to_contradicted() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-031")
    requirement.evidence.implementation_files = [
        "wellnessbox-rnd/src/wellnessbox_rnd/safety/does_not_exist.py"
    ]
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)

    report = build_original_plan_completion_report_v1(manifest, audit)
    completion = _completion_by_id(report, "OP-031")

    assert completion.disposition == CompletionDisposition.CONTRADICTED
    assert "evidence_file_missing" in completion.reasons


def test_report_limits_contract_contradiction_to_the_affected_requirement() -> None:
    manifest = _manifest_copy()
    requirement = _draft_by_id(manifest, "OP-031")
    requirement.evidence.test_files = []
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)

    report = build_original_plan_completion_report_v1(manifest, audit)

    assert _completion_by_id(report, "OP-031").disposition == CompletionDisposition.CONTRADICTED
    assert _completion_by_id(report, "OP-032").disposition == CompletionDisposition.COMPLETE


def test_report_rejects_audit_from_different_manifest_content() -> None:
    manifest = _manifest_copy()
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)
    _draft_by_id(manifest, "OP-011").title = "감사 이후 변경된 요구사항"

    with pytest.raises(ValueError, match="audit_manifest_sha256_mismatch"):
        build_original_plan_completion_report_v1(manifest, audit)


def test_global_source_failure_invalidates_every_existing_completion_claim() -> None:
    manifest = _manifest_copy()
    manifest.original_plan_sha256 = "0" * 64
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)

    report = build_original_plan_completion_report_v1(manifest, audit)

    assert report.disposition_counts[CompletionDisposition.COMPLETE] == 0
    assert report.disposition_counts[CompletionDisposition.CONTRADICTED] == 21
    assert "original_plan_sha256_mismatch" in report.global_audit_issues


def test_markdown_uses_audited_korean_status_language() -> None:
    manifest = _manifest_copy()
    audit = audit_original_plan_manifest_v1(manifest, repository_roots=REPOSITORY_ROOTS)
    report = build_original_plan_completion_report_v1(manifest, audit)

    markdown = render_original_plan_completion_report_markdown_v1(report)

    assert "원계획 요구사항 포함: **120/120건**" in markdown
    assert "| 완료 | 21 |" in markdown
    assert "| 대기 | 98 |" in markdown
    assert "전체 완료: **100%**" not in markdown


def test_report_cli_writes_and_checks_deterministic_artifacts(tmp_path: Path) -> None:
    json_output = tmp_path / "completion.json"
    markdown_output = tmp_path / "completion.md"
    command = [
        sys.executable,
        str(SCRIPT_PATH),
        "--json-output",
        str(json_output),
        "--markdown-output",
        str(markdown_output),
    ]

    generated = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    checked = subprocess.run(
        [*command, "--check"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    markdown_output.write_text("stale\n", encoding="utf-8")
    stale = subprocess.run(
        [*command, "--check"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert generated.returncode == 0
    assert checked.returncode == 0
    assert stale.returncode == 1
    assert json.loads(generated.stdout)["disposition_counts"]["COMPLETE"] == 21
    assert str(markdown_output) in json.loads(stale.stdout)["stale_outputs"]
