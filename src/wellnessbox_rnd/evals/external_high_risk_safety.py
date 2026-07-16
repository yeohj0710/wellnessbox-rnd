from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
    Severity,
)

CASE_SCHEMA = "external_high_risk_safety_case_v2"
ATTESTATION_SCHEMA = "external_high_risk_safety_attestation_v2"
VERIFICATION_RECEIPT_SCHEMA = "external_high_risk_safety_verification_receipt_v1"
COVERAGE_PROTOCOL_SCHEMA = "external_high_risk_safety_coverage_protocol_v1"
COVERAGE_TRUST_ROOTS_SCHEMA = "external_high_risk_safety_coverage_trust_roots_v1"
ATTESTATION_TRUST_ROOTS_SCHEMA = "external_high_risk_safety_attestation_trust_roots_v1"
REPORT_SCHEMA = "external_high_risk_safety_report_v2"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
COVERAGE_TRUST_ROOTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "original_plan"
    / "contracts"
    / "op039_external_coverage_trust_roots_v1.json"
)
ATTESTATION_TRUST_ROOTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "original_plan"
    / "contracts"
    / "op039_external_attestation_trust_roots_v1.json"
)
_INTERNAL_DATASET_PATH_MARKERS = ("/data/frozen_eval/", "/data/synthetic/")
_PLACEHOLDER_MARKERS = (
    "dummy",
    "example",
    "fixture",
    "internal",
    "placeholder",
    "sample",
    "synthetic",
    "test organization",
)


class ExternalHighRiskEvalContractError(ValueError):
    """Raised when inputs cannot support independently verified evaluation."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExternalHighRiskSafetyCaseV2(_StrictModel):
    schema_version: Literal[CASE_SCHEMA]
    case_id: str = Field(min_length=1, max_length=200)
    risk_tier: Literal["high"]
    expected_final_disposition: Literal["blocked"]
    hazard_stratum: str = Field(min_length=1, max_length=200)
    expected_blocking_rule_ids: list[str] = Field(min_length=1)
    label_basis: str = Field(min_length=1, max_length=2000)
    request: RecommendationRequest


class ExternalHighRiskSafetyAttestationV2(_StrictModel):
    schema_version: Literal[ATTESTATION_SCHEMA]
    attestation_id: str = Field(min_length=1, max_length=200)
    dataset_id: str = Field(min_length=1, max_length=200)
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_count: int = Field(gt=0)
    source_kind: Literal["independent_clinical_review"]
    review_organization: str = Field(min_length=1, max_length=300)
    reviewer_role: str = Field(min_length=1, max_length=200)
    independent_of_implementation_team: Literal[True]
    labeling_protocol_reference: str = Field(min_length=1, max_length=500)
    attestation_reference: str = Field(min_length=1, max_length=500)
    labeling_started_at: AwareDatetime
    attested_at: AwareDatetime


class ExternalAttestationVerificationReceiptV1(_StrictModel):
    schema_version: Literal[VERIFICATION_RECEIPT_SCHEMA]
    attestation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_status: Literal["verified"]
    verifier_organization: str = Field(min_length=1, max_length=300)
    verifier_role: str = Field(min_length=1, max_length=200)
    independent_of_implementation_team: Literal[True]
    verification_method: str = Field(min_length=1, max_length=500)
    verification_reference: str = Field(min_length=1, max_length=500)
    verified_at: AwareDatetime


class ApprovedExternalAttestationV1(_StrictModel):
    dataset_id: str = Field(min_length=1, max_length=200)
    coverage_protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    labeling_protocol_reference: str = Field(min_length=1, max_length=500)
    approval_reference: str = Field(min_length=1, max_length=500)
    attestation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExternalHighRiskCoverageProtocolV1(_StrictModel):
    schema_version: Literal[COVERAGE_PROTOCOL_SCHEMA]
    protocol_id: str = Field(min_length=1, max_length=200)
    frozen_at: AwareDatetime
    labeling_protocol_reference: str = Field(min_length=1, max_length=500)
    minimum_case_count: int = Field(gt=0)
    minimum_cases_per_hazard_stratum: dict[str, int] = Field(min_length=1)

    @field_validator("minimum_cases_per_hazard_stratum")
    @classmethod
    def validate_stratum_minimums(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not key.strip() or minimum < 1 for key, minimum in value.items()):
            raise ValueError("hazard stratum names and minimums must be positive")
        return value


class ApprovedCoverageProtocolV1(_StrictModel):
    coverage_protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_reference: str = Field(min_length=1, max_length=500)


class ExternalHighRiskCoverageTrustRootsV1(_StrictModel):
    schema_version: Literal[COVERAGE_TRUST_ROOTS_SCHEMA]
    frozen_at: AwareDatetime
    approval_authority: str = Field(min_length=1, max_length=300)
    approved_coverage_protocols: list[ApprovedCoverageProtocolV1]
    approval_record_references: list[str]

class ExternalHighRiskAttestationTrustRootsV1(_StrictModel):
    schema_version: Literal[ATTESTATION_TRUST_ROOTS_SCHEMA]
    frozen_at: AwareDatetime
    approval_authority: str = Field(min_length=1, max_length=300)
    approved_attestations: list[ApprovedExternalAttestationV1]
    approval_record_references: list[str]


class ExternalHighRiskSafetyEvalReportV2(_StrictModel):
    schema_version: Literal[REPORT_SCHEMA] = REPORT_SCHEMA
    dataset_id: str
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attestation_id: str
    attestation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_protocol_id: str
    coverage_protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_approval_reference: str
    attestation_approval_reference: str
    coverage_trust_roots_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attestation_trust_roots_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attestation_authenticity: Literal["verified_by_frozen_trust_registry"] = (
        "verified_by_frozen_trust_registry"
    )
    case_count: int = Field(gt=0)
    cases_by_hazard_stratum: dict[str, int]
    engine_code_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    engine_git_tree_sha1: str = Field(pattern=r"^[0-9a-f]{40}$")
    evaluator_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    engine_versions: list[str]
    engine_modes: list[str]
    matched_rule_versions: dict[str, list[int]]
    hard_false_negative_target: Literal[0] = 0
    hard_false_negative_count: int = Field(ge=0)
    hard_false_negative_case_ids: list[str] = Field(default_factory=list)
    rule_mismatch_case_ids: list[str] = Field(default_factory=list)
    evaluation_error_case_ids: list[str] = Field(default_factory=list)
    status: Literal["PASS", "FAIL"]


def run_external_high_risk_safety_eval(
    *,
    dataset_path: str | Path,
    attestation_path: str | Path,
    verification_receipt_path: str | Path,
    coverage_protocol_path: str | Path,
    output_path: str | Path | None = None,
    recommend_fn: Callable[[RecommendationRequest], RecommendationResponse] = recommend,
) -> ExternalHighRiskSafetyEvalReportV2:
    dataset = Path(dataset_path).resolve()
    attestation_file = Path(attestation_path).resolve()
    receipt_file = Path(verification_receipt_path).resolve()
    coverage_protocol_file = Path(coverage_protocol_path).resolve()
    _reject_internal_dataset_path(dataset)

    dataset_bytes = _read_required_file(dataset, "dataset")
    attestation_bytes = _read_required_file(attestation_file, "attestation")
    receipt_bytes = _read_required_file(receipt_file, "verification receipt")
    coverage_protocol_bytes = _read_required_file(
        coverage_protocol_file, "coverage protocol"
    )
    coverage_roots_bytes = _read_required_file(
        COVERAGE_TRUST_ROOTS_PATH, "repository coverage trust roots"
    )
    attestation_roots_bytes = _read_required_file(
        ATTESTATION_TRUST_ROOTS_PATH, "repository attestation trust roots"
    )
    dataset_hash = _sha256_bytes(dataset_bytes)
    attestation_hash = _sha256_bytes(attestation_bytes)
    receipt_hash = _sha256_bytes(receipt_bytes)
    coverage_protocol_hash = _sha256_bytes(coverage_protocol_bytes)
    coverage_roots_hash = _sha256_bytes(coverage_roots_bytes)
    attestation_roots_hash = _sha256_bytes(attestation_roots_bytes)

    attestation = _parse_json_model(
        attestation_bytes, ExternalHighRiskSafetyAttestationV2, "external attestation"
    )
    receipt = _parse_json_model(
        receipt_bytes, ExternalAttestationVerificationReceiptV1, "verification receipt"
    )
    coverage_protocol = _parse_json_model(
        coverage_protocol_bytes,
        ExternalHighRiskCoverageProtocolV1,
        "coverage protocol",
    )
    coverage_roots = _parse_json_model(
        coverage_roots_bytes,
        ExternalHighRiskCoverageTrustRootsV1,
        "repository coverage trust roots",
    )
    attestation_roots = _parse_json_model(
        attestation_roots_bytes,
        ExternalHighRiskAttestationTrustRootsV1,
        "repository attestation trust roots",
    )
    _validate_non_placeholder_contracts(attestation, receipt, coverage_protocol)
    coverage_approval = next(
        (
            entry
            for entry in coverage_roots.approved_coverage_protocols
            if entry.coverage_protocol_sha256 == coverage_protocol_hash
        ),
        None,
    )
    if coverage_approval is None:
        raise ExternalHighRiskEvalContractError(
            "coverage protocol SHA-256 is not pinned by repository trust roots"
        )
    if coverage_approval.approval_reference not in coverage_roots.approval_record_references:
        raise ExternalHighRiskEvalContractError(
            "coverage protocol approval reference is not registered"
        )
    if not (
        coverage_protocol.frozen_at
        <= coverage_roots.frozen_at
        < attestation.labeling_started_at
        <= attestation.attested_at
    ):
        raise ExternalHighRiskEvalContractError(
            "coverage protocol approval must precede labeling start and attestation"
        )
    if (
        attestation.labeling_protocol_reference
        != coverage_protocol.labeling_protocol_reference
    ):
        raise ExternalHighRiskEvalContractError(
            "attestation labeling protocol does not match frozen coverage protocol"
        )
    if attestation.dataset_sha256 != dataset_hash:
        raise ExternalHighRiskEvalContractError(
            "attested dataset SHA-256 does not match the supplied dataset"
        )
    if receipt.attestation_sha256 != attestation_hash:
        raise ExternalHighRiskEvalContractError(
            "verification receipt does not match the supplied attestation"
        )
    if receipt.verified_at <= attestation.attested_at:
        raise ExternalHighRiskEvalContractError(
            "verification receipt must be issued after external attestation"
        )
    attestation_approval = next(
        (
            entry
            for entry in attestation_roots.approved_attestations
            if entry.attestation_sha256 == attestation_hash
            and entry.verification_receipt_sha256 == receipt_hash
            and entry.dataset_id == attestation.dataset_id
            and entry.coverage_protocol_sha256 == coverage_protocol_hash
            and entry.labeling_protocol_reference
            == coverage_protocol.labeling_protocol_reference
        ),
        None,
    )
    if attestation_approval is None:
        raise ExternalHighRiskEvalContractError(
            "attestation and verification receipt are not pinned by repository trust roots"
        )
    if (
        attestation_approval.approval_reference
        not in attestation_roots.approval_record_references
    ):
        raise ExternalHighRiskEvalContractError(
            "attestation approval reference is not registered"
        )
    if attestation_roots.frozen_at < receipt.verified_at:
        raise ExternalHighRiskEvalContractError(
            "attestation trust roots must be frozen after verification receipt"
        )

    cases = _parse_cases(dataset_bytes)
    if attestation.case_count != len(cases):
        raise ExternalHighRiskEvalContractError(
            "attested case_count does not match the supplied dataset"
        )
    cases_by_stratum = Counter(case.hazard_stratum for case in cases)
    _validate_coverage(cases_by_stratum, len(cases), coverage_protocol)
    engine_code_commit, engine_git_tree_sha1 = _engine_git_identity()

    hard_false_negative_ids: list[str] = []
    rule_mismatch_ids: list[str] = []
    evaluation_error_ids: list[str] = []
    engine_versions: set[str] = set()
    engine_modes: set[str] = set()
    matched_rule_versions: defaultdict[str, set[int]] = defaultdict(set)
    for case in cases:
        try:
            response = RecommendationResponse.model_validate(recommend_fn(case.request))
        except Exception:
            evaluation_error_ids.append(case.case_id)
            continue
        engine_versions.add(response.metadata.engine_version)
        engine_modes.add(response.metadata.mode)
        blocker_rules = {
            rule.rule_id: rule
            for rule in response.safety_summary.rule_refs
            if rule.severity == Severity.BLOCKER
        }
        matched_rules = set(case.expected_blocking_rule_ids) & set(blocker_rules)
        rule_matches = bool(matched_rules)
        if not rule_matches:
            rule_mismatch_ids.append(case.case_id)
        for rule_id in matched_rules:
            matched_rule_versions[rule_id].add(blocker_rules[rule_id].rule_version)
        if (
            response.status != RecommendationStatus.BLOCKED
            or response.safety_summary.status != RecommendationStatus.BLOCKED
            or bool(response.recommendations)
            or not rule_matches
        ):
            hard_false_negative_ids.append(case.case_id)

    report = ExternalHighRiskSafetyEvalReportV2(
        dataset_id=attestation.dataset_id,
        dataset_sha256=dataset_hash,
        attestation_id=attestation.attestation_id,
        attestation_sha256=attestation_hash,
        verification_receipt_sha256=receipt_hash,
        coverage_protocol_id=coverage_protocol.protocol_id,
        coverage_protocol_sha256=coverage_protocol_hash,
        coverage_approval_reference=coverage_approval.approval_reference,
        attestation_approval_reference=attestation_approval.approval_reference,
        coverage_trust_roots_sha256=coverage_roots_hash,
        attestation_trust_roots_sha256=attestation_roots_hash,
        case_count=len(cases),
        cases_by_hazard_stratum=dict(sorted(cases_by_stratum.items())),
        engine_code_commit=engine_code_commit,
        engine_git_tree_sha1=engine_git_tree_sha1,
        evaluator_source_sha256=_sha256_bytes(Path(__file__).read_bytes()),
        engine_versions=sorted(engine_versions),
        engine_modes=sorted(engine_modes),
        matched_rule_versions={
            rule_id: sorted(versions)
            for rule_id, versions in sorted(matched_rule_versions.items())
        },
        hard_false_negative_count=len(hard_false_negative_ids),
        hard_false_negative_case_ids=hard_false_negative_ids,
        rule_mismatch_case_ids=rule_mismatch_ids,
        evaluation_error_case_ids=evaluation_error_ids,
        status=(
            "PASS"
            if not hard_false_negative_ids and not evaluation_error_ids
            else "FAIL"
        ),
    )
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    return report


def _read_required_file(path: Path, label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ExternalHighRiskEvalContractError(f"unable to read {label}: {path}") from error
    if not payload:
        raise ExternalHighRiskEvalContractError(f"{label} must not be empty")
    return payload


def _parse_json_model(payload: bytes, model_type, label: str):
    try:
        return model_type.model_validate_json(payload)
    except (UnicodeDecodeError, ValidationError) as error:
        raise ExternalHighRiskEvalContractError(f"invalid {label} contract: {error}") from error


def _parse_cases(payload: bytes) -> list[ExternalHighRiskSafetyCaseV2]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExternalHighRiskEvalContractError("dataset must be UTF-8 JSONL") from error
    cases: list[ExternalHighRiskSafetyCaseV2] = []
    case_ids: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = ExternalHighRiskSafetyCaseV2.model_validate_json(line)
        except ValidationError as error:
            raise ExternalHighRiskEvalContractError(
                f"invalid external case at line {line_number}: {error}"
            ) from error
        if case.case_id in case_ids:
            raise ExternalHighRiskEvalContractError(f"duplicate external case_id: {case.case_id}")
        case_ids.add(case.case_id)
        cases.append(case)
    if not cases:
        raise ExternalHighRiskEvalContractError("dataset must include at least one case")
    return cases


def _validate_coverage(
    counts: Counter[str],
    case_count: int,
    coverage_protocol: ExternalHighRiskCoverageProtocolV1,
) -> None:
    if case_count < coverage_protocol.minimum_case_count:
        raise ExternalHighRiskEvalContractError("dataset is below the frozen minimum_case_count")
    shortages = {
        stratum: minimum - counts.get(stratum, 0)
        for stratum, minimum in coverage_protocol.minimum_cases_per_hazard_stratum.items()
        if counts.get(stratum, 0) < minimum
    }
    if shortages:
        raise ExternalHighRiskEvalContractError(
            f"dataset is below frozen hazard-stratum minimums: {shortages}"
        )


def _validate_non_placeholder_contracts(attestation, receipt, coverage_protocol) -> None:
    values = {
        "review_organization": attestation.review_organization,
        "reviewer_role": attestation.reviewer_role,
        "labeling_protocol_reference": attestation.labeling_protocol_reference,
        "attestation_reference": attestation.attestation_reference,
        "verifier_organization": receipt.verifier_organization,
        "verifier_role": receipt.verifier_role,
        "verification_method": receipt.verification_method,
        "verification_reference": receipt.verification_reference,
        "coverage_protocol_id": coverage_protocol.protocol_id,
        "coverage_labeling_protocol_reference": (
            coverage_protocol.labeling_protocol_reference
        ),
    }
    for field_name, value in values.items():
        normalized = value.casefold()
        if any(marker in normalized for marker in _PLACEHOLDER_MARKERS):
            raise ExternalHighRiskEvalContractError(
                f"{field_name} contains placeholder or internal provenance"
            )


def _reject_internal_dataset_path(path: Path) -> None:
    normalized = f"/{path.as_posix().lower().strip('/')}/"
    if any(marker in normalized for marker in _INTERNAL_DATASET_PATH_MARKERS):
        raise ExternalHighRiskEvalContractError(
            "repository internal or synthetic dataset path cannot support external validation"
        )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _engine_git_identity() -> tuple[str, str]:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if status.stdout.strip():
            raise ExternalHighRiskEvalContractError(
                "external evaluation requires a clean committed worktree"
            )
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ExternalHighRiskEvalContractError("engine Git identity is unavailable") from error
    return commit, tree
