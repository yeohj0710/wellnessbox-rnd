from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

REQUIRED_ENDPOINT_FAMILIES = {
    "health": ("GET", "/health"),
    "recommendation": ("POST", "/v1/recommend"),
    "state_machine": ("POST", "/v1/interim/plan-lifecycle/transitions"),
    "device": ("POST", "/v1/interim/connectors/device"),
    "counseling": ("POST", "/v1/interim/counseling/turns"),
}
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class RouteLike(Protocol):
    path: str
    methods: set[str] | None


@dataclass(frozen=True)
class DeploymentContract:
    schema_version: str
    status: str
    app_env: str
    deployment_target: str
    deployment_id: str
    code_commit: str
    database_path: str
    database_durability: str
    internal_auth_scheme: str
    internal_token_sha256_prefix: str
    workers: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_deployment_contract(
    environment: Mapping[str, str] | None = None,
) -> DeploymentContract:
    values = os.environ if environment is None else environment
    errors: list[str] = []
    app_env = values.get("WB_RND_APP_ENV", "").strip().lower()
    if app_env not in {"staging", "production"}:
        errors.append("app_env_must_be_staging_or_production")
    if values.get("WB_RND_INTERIM_ENABLED", "").lower() not in {"1", "true", "yes"}:
        errors.append("interim_api_must_be_enabled")
    deployment_target = values.get("WB_RND_DEPLOYMENT_TARGET", "").strip()
    if not deployment_target:
        errors.append("deployment_target_required")
    deployment_id = values.get("WB_RND_DEPLOYMENT_ID", "").strip()
    if not deployment_id:
        errors.append("deployment_id_required")
    code_commit = values.get("WB_RND_CODE_COMMIT", "").strip().lower()
    if not _COMMIT_PATTERN.fullmatch(code_commit):
        errors.append("code_commit_must_be_full_sha")
    database_value = values.get("WB_RND_INTERIM_DATABASE", "").strip()
    database_path = Path(database_value) if database_value else Path()
    if not database_value or not database_path.is_absolute():
        errors.append("interim_database_must_be_absolute")
    durability = values.get("WB_RND_DATABASE_DURABILITY", "").strip()
    if durability != "provider_persistent_volume":
        errors.append("database_durability_must_be_provider_persistent_volume")
    auth_scheme = values.get("WB_RND_INTERNAL_AUTH_SCHEME", "").strip()
    if auth_scheme != "shared_header_hmac_sha256_v1":
        errors.append("internal_auth_scheme_unsupported")
    token = values.get("WB_RND_INTERIM_INTERNAL_TOKEN", "")
    if len(token.encode("utf-8")) < 32:
        errors.append("internal_token_minimum_32_bytes")
    try:
        workers = int(values.get("WB_RND_WORKERS", "1"))
    except ValueError:
        workers = 0
    if workers != 1:
        errors.append("sqlite_deployment_requires_one_worker")
    if errors:
        raise ValueError("deployment_contract_invalid:" + ",".join(sorted(errors)))
    return DeploymentContract(
        schema_version="wellnessbox_rnd_deployment_contract_v1",
        status="READY_FOR_PROVIDER_DEPLOYMENT",
        app_env=app_env,
        deployment_target=deployment_target,
        deployment_id=deployment_id,
        code_commit=code_commit,
        database_path=str(database_path),
        database_durability=durability,
        internal_auth_scheme=auth_scheme,
        internal_token_sha256_prefix=hashlib.sha256(token.encode()).hexdigest()[:12],
        workers=workers,
    )


def build_endpoint_inventory(routes: list[RouteLike]) -> dict[str, object]:
    mounted = {
        (method, route.path)
        for route in routes
        for method in sorted(route.methods or set())
        if method not in {"HEAD", "OPTIONS"}
    }
    families = {
        family: {
            "method": method,
            "path": path,
            "mounted": (method, path) in mounted,
        }
        for family, (method, path) in REQUIRED_ENDPOINT_FAMILIES.items()
    }
    missing = sorted(family for family, item in families.items() if not item["mounted"])
    if missing:
        raise ValueError("required_deployment_endpoints_missing:" + ",".join(missing))
    canonical = json.dumps(families, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": "wellnessbox_rnd_endpoint_inventory_v1",
        "status": "COMPLETE",
        "families": families,
        "inventory_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }
