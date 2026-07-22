from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

REGISTRY_SCHEMA = "op119_external_dependency_registry_v1"


class ExternalDependencyRegistryError(ValueError):
    """Raised when the external dependency registry is incomplete or inflated."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountableOwnerV1(_StrictModel):
    role_id: str = Field(min_length=1, max_length=200)
    authority: str = Field(min_length=1, max_length=300)
    responsibility: str = Field(min_length=1, max_length=1000)


class RequiredExternalInputV1(_StrictModel):
    input_id: str = Field(min_length=1, max_length=200)
    supplier_role: str = Field(min_length=1, max_length=300)
    schema_version: str = Field(min_length=1, max_length=200)
    acceptance_contract: str = Field(min_length=1, max_length=500)
    provision_status: Literal["MISSING", "PROVIDED"]


class BlockingReasonV1(_StrictModel):
    code: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    source_path: str = Field(min_length=1, max_length=500)
    json_pointer: str = Field(pattern=r"^/[A-Za-z0-9_/-]+$")
    expected_observation: Literal["EMPTY_LIST"]


class ExternalDependencyEntryV1(_StrictModel):
    requirement_id: str = Field(pattern=r"^OP-[0-9]{3}$")
    accountable_owner: AccountableOwnerV1
    external_provider_role: str = Field(min_length=1, max_length=300)
    required_inputs: list[RequiredExternalInputV1] = Field(min_length=1)
    replacement_contracts: list[str] = Field(min_length=1)
    blocking_reasons: list[BlockingReasonV1] = Field(min_length=1)
    readiness: Literal["BLOCKED", "READY"]
    promotion_condition: str = Field(min_length=1, max_length=2000)


class ExternalDependencyRegistryV1(_StrictModel):
    schema_version: Literal[REGISTRY_SCHEMA]
    entries: list[ExternalDependencyEntryV1]


class ExternalDependencyRegistryAuditV1(_StrictModel):
    schema_version: Literal["op119_external_dependency_registry_audit_v1"] = (
        "op119_external_dependency_registry_audit_v1"
    )
    status: Literal["PASS"] = "PASS"
    external_requirement_ids: list[str]
    registry_requirement_ids: list[str]
    blocked_requirement_ids: list[str]
    required_input_count: int
    replacement_contract_count: int
    blocking_reason_count: int
    verified_observation_count: int


def audit_external_dependency_registry_v1(
    registry_path: str | Path,
    manifest_path: str | Path,
    repository_root: str | Path,
) -> ExternalDependencyRegistryAuditV1:
    root = Path(repository_root).resolve()
    try:
        registry = ExternalDependencyRegistryV1.model_validate_json(
            Path(registry_path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as error:
        raise ExternalDependencyRegistryError(f"invalid registry: {error}") from error
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    requirements = [
        requirement
        for group in manifest["groups"]
        for requirement in group["requirements"]
    ]
    external = {
        item["requirement_id"]: item
        for item in requirements
        if item.get("required_stage") == "EXTERNAL"
    }
    entries = {entry.requirement_id: entry for entry in registry.entries}
    if set(entries) != set(external) or len(entries) != len(registry.entries):
        raise ExternalDependencyRegistryError("external requirement set mismatch")

    verified_observations = 0
    for requirement_id, entry in entries.items():
        manifest_contracts = set(
            external[requirement_id].get("evidence", {}).get(
                "replacement_contracts", []
            )
        )
        if set(entry.replacement_contracts) != manifest_contracts:
            raise ExternalDependencyRegistryError(
                f"{requirement_id} replacement contracts do not match manifest"
            )
        for relative in entry.replacement_contracts:
            if not (root / _strip_repository_prefix(relative)).is_file():
                raise ExternalDependencyRegistryError(
                    f"replacement contract file missing: {relative}"
                )
        input_ids = [item.input_id for item in entry.required_inputs]
        reason_codes = [reason.code for reason in entry.blocking_reasons]
        if len(input_ids) != len(set(input_ids)) or len(reason_codes) != len(
            set(reason_codes)
        ):
            raise ExternalDependencyRegistryError("registry identifiers must be unique")
        if entry.readiness == "READY" and (
            any(item.provision_status != "PROVIDED" for item in entry.required_inputs)
            or entry.blocking_reasons
        ):
            raise ExternalDependencyRegistryError(
                f"{requirement_id} cannot be READY with missing inputs or blockers"
            )
        for reason in entry.blocking_reasons:
            source = root / _strip_repository_prefix(reason.source_path)
            try:
                value = _resolve_json_pointer(
                    json.loads(source.read_text(encoding="utf-8")),
                    reason.json_pointer,
                )
            except (OSError, KeyError, json.JSONDecodeError) as error:
                raise ExternalDependencyRegistryError(
                    f"unverified json pointer for {reason.code}: {error}"
                ) from error
            if reason.expected_observation == "EMPTY_LIST" and value != []:
                raise ExternalDependencyRegistryError(
                    f"blocking observation changed for {reason.code}"
                )
            verified_observations += 1

    return ExternalDependencyRegistryAuditV1(
        external_requirement_ids=sorted(external),
        registry_requirement_ids=sorted(entries),
        blocked_requirement_ids=sorted(
            entry.requirement_id
            for entry in entries.values()
            if entry.readiness == "BLOCKED"
        ),
        required_input_count=sum(len(entry.required_inputs) for entry in entries.values()),
        replacement_contract_count=sum(
            len(entry.replacement_contracts) for entry in entries.values()
        ),
        blocking_reason_count=sum(
            len(entry.blocking_reasons) for entry in entries.values()
        ),
        verified_observation_count=verified_observations,
    )


def _strip_repository_prefix(path: str) -> Path:
    prefix = "wellnessbox-rnd/"
    return Path(path[len(prefix) :] if path.startswith(prefix) else path)


def _resolve_json_pointer(document: object, pointer: str) -> object:
    value = document
    for token in pointer.lstrip("/").split("/"):
        if not isinstance(value, dict) or token not in value:
            raise KeyError(pointer)
        value = value[token]
    return value
