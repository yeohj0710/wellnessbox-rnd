from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from wellnessbox_rnd.schemas.recommendation import EngineMetadata, RecommendationResponse

CODE_COMMIT_ENV_VAR = "WB_RND_CODE_COMMIT"
CODE_COMMIT_SOURCES = ("environment", "git", "unresolved")
UNRESOLVED_CODE_COMMIT = "unresolved"

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")

RUNTIME_DATASET_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("runtime_knowledge_db_v1", "data/knowledge/runtime_knowledge_db_v1.json"),
    ("reference_knowledge_base_v1", "data/knowledge/reference_knowledge_base_v1.json"),
    ("safety_rules_v1", "data/rules/safety_rules.json"),
    ("ingredient_catalog_v1", "data/catalog/ingredients.json"),
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatasetIdentityRecord(_StrictModel):
    dataset_id: str
    path: str
    sha256: str


class ExecutionIdentityRecord(_StrictModel):
    execution_id: str
    model_id: str
    engine_version: str
    code_commit: str
    code_commit_source: str
    datasets: list[DatasetIdentityRecord]
    config: dict[str, Any]
    config_sha256: str
    created_at: str


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_git_head(repository_root: Path) -> str | None:
    head_path = repository_root / ".git" / "HEAD"
    try:
        head_text = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head_text:
        return None
    if not head_text.startswith("ref:"):
        candidate = head_text.lower()
        return candidate if _COMMIT_PATTERN.fullmatch(candidate) else None
    ref_name = head_text.removeprefix("ref:").strip()
    ref_path = repository_root / ".git" / Path(*ref_name.split("/"))
    try:
        ref_text = ref_path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        ref_text = ""
    if _COMMIT_PATTERN.fullmatch(ref_text):
        return ref_text
    packed_path = repository_root / ".git" / "packed-refs"
    try:
        packed_lines = packed_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in packed_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "^")):
            continue
        parts = stripped.split(" ", 1)
        if len(parts) == 2 and parts[1].strip() == ref_name:
            candidate = parts[0].strip().lower()
            return candidate if _COMMIT_PATTERN.fullmatch(candidate) else None
    return None


def resolve_code_commit(repository_root: Path | None = None) -> tuple[str, str]:
    override = os.getenv(CODE_COMMIT_ENV_VAR, "").strip()
    if override:
        if len(override) > 128:
            raise ValueError("code_commit_override_too_long")
        return "environment", override
    resolved = _resolve_git_head(repository_root or _REPOSITORY_ROOT)
    if resolved is not None:
        return "git", resolved
    return "unresolved", UNRESOLVED_CODE_COMMIT


def runtime_dataset_identities(
    repository_root: Path | None = None,
) -> list[DatasetIdentityRecord]:
    root = repository_root or _REPOSITORY_ROOT
    identities: list[DatasetIdentityRecord] = []
    for dataset_id, relative_path in RUNTIME_DATASET_ARTIFACTS:
        artifact_path = root / Path(relative_path)
        if not artifact_path.is_file():
            raise FileNotFoundError(f"runtime_dataset_artifact_missing:{relative_path}")
        identities.append(
            DatasetIdentityRecord(
                dataset_id=dataset_id,
                path=relative_path,
                sha256=_sha256_file(artifact_path),
            )
        )
    return identities


def build_execution_identity(
    *,
    execution_id: str,
    response: RecommendationResponse,
    created_at: str,
    repository_root: Path | None = None,
) -> ExecutionIdentityRecord:
    return build_runtime_identity(
        execution_id=execution_id,
        model_id=response.metadata.mode,
        engine_version=response.metadata.engine_version,
        created_at=created_at,
        repository_root=repository_root,
    )


def build_runtime_identity(
    *,
    execution_id: str,
    model_id: str,
    engine_version: str,
    created_at: str,
    repository_root: Path | None = None,
) -> ExecutionIdentityRecord:
    code_commit_source, code_commit = resolve_code_commit(repository_root)
    datasets = runtime_dataset_identities(repository_root)
    config: dict[str, Any] = {
        "model_id": model_id,
        "engine_version": engine_version,
        "app_env": os.getenv("WB_RND_APP_ENV", os.getenv("APP_ENV", "local")).lower(),
        "datasets": {item.dataset_id: item.sha256 for item in datasets},
    }
    return ExecutionIdentityRecord(
        execution_id=execution_id,
        model_id=model_id,
        engine_version=engine_version,
        code_commit=code_commit,
        code_commit_source=code_commit_source,
        datasets=datasets,
        config=config,
        config_sha256=_sha256_text(_canonical_json(config)),
        created_at=created_at,
    )


def build_current_deterministic_identity(
    *,
    execution_id: str,
    created_at: str,
    repository_root: Path | None = None,
) -> ExecutionIdentityRecord:
    metadata = EngineMetadata(mode="deterministic_baseline_v1")
    return build_runtime_identity(
        execution_id=execution_id,
        model_id=metadata.mode,
        engine_version=metadata.engine_version,
        created_at=created_at,
        repository_root=repository_root,
    )


def identity_version_payload(identity: ExecutionIdentityRecord) -> dict[str, Any]:
    return {
        "model_id": identity.model_id,
        "engine_version": identity.engine_version,
        "code_commit": identity.code_commit,
        "code_commit_source": identity.code_commit_source,
        "datasets": [item.model_dump(mode="json") for item in identity.datasets],
        "config": identity.config,
        "config_sha256": identity.config_sha256,
    }


def identity_version_sha256(identity: ExecutionIdentityRecord) -> str:
    return _sha256_text(_canonical_json(identity_version_payload(identity)))


__all__ = [
    "CODE_COMMIT_ENV_VAR",
    "CODE_COMMIT_SOURCES",
    "DatasetIdentityRecord",
    "ExecutionIdentityRecord",
    "RUNTIME_DATASET_ARTIFACTS",
    "UNRESOLVED_CODE_COMMIT",
    "build_current_deterministic_identity",
    "build_execution_identity",
    "build_runtime_identity",
    "identity_version_payload",
    "identity_version_sha256",
    "resolve_code_commit",
    "runtime_dataset_identities",
]
