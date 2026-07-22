from __future__ import annotations

import json
from pathlib import Path

import pytest

from wellnessbox_rnd.governance.external_dependency_registry import (
    ExternalDependencyRegistryError,
    audit_external_dependency_registry_v1,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/original_plan/requirements_manifest_v1.json"
REGISTRY = ROOT / "data/original_plan/op119_external_dependency_registry_v1.json"


def test_current_external_dependency_registry_is_complete_and_blocked() -> None:
    report = audit_external_dependency_registry_v1(
        registry_path=REGISTRY,
        manifest_path=MANIFEST,
        repository_root=ROOT,
    )

    assert report.status == "PASS"
    assert report.external_requirement_ids == ["OP-039"]
    assert report.registry_requirement_ids == ["OP-039"]
    assert report.blocked_requirement_ids == ["OP-039"]
    assert report.required_input_count == 4
    assert report.replacement_contract_count == 2
    assert report.blocking_reason_count == 4


def _write_changed(tmp_path: Path, mutate) -> Path:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_registry_rejects_missing_external_requirement(tmp_path: Path) -> None:
    path = _write_changed(tmp_path, lambda payload: payload["entries"].clear())
    with pytest.raises(ExternalDependencyRegistryError, match="requirement set"):
        audit_external_dependency_registry_v1(path, MANIFEST, ROOT)


def test_registry_rejects_empty_accountable_role(tmp_path: Path) -> None:
    path = _write_changed(
        tmp_path,
        lambda payload: payload["entries"][0]["accountable_owner"].update(
            {"role_id": ""}
        ),
    )
    with pytest.raises(ExternalDependencyRegistryError, match="role_id"):
        audit_external_dependency_registry_v1(path, MANIFEST, ROOT)


def test_registry_rejects_replacement_contract_drift(tmp_path: Path) -> None:
    path = _write_changed(
        tmp_path,
        lambda payload: payload["entries"][0]["replacement_contracts"].pop(),
    )
    with pytest.raises(ExternalDependencyRegistryError, match="replacement contracts"):
        audit_external_dependency_registry_v1(path, MANIFEST, ROOT)


def test_registry_rejects_ready_when_inputs_and_trust_roots_are_missing(
    tmp_path: Path,
) -> None:
    path = _write_changed(
        tmp_path,
        lambda payload: payload["entries"][0].update({"readiness": "READY"}),
    )
    with pytest.raises(ExternalDependencyRegistryError, match="READY"):
        audit_external_dependency_registry_v1(path, MANIFEST, ROOT)


def test_registry_rejects_unverified_blocker_observation(tmp_path: Path) -> None:
    path = _write_changed(
        tmp_path,
        lambda payload: payload["entries"][0]["blocking_reasons"][0].update(
            {"json_pointer": "/does_not_exist"}
        ),
    )
    with pytest.raises(ExternalDependencyRegistryError, match="json pointer"):
        audit_external_dependency_registry_v1(path, MANIFEST, ROOT)
