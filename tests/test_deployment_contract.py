from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.deployment import (
    REQUIRED_ENDPOINT_FAMILIES,
    build_endpoint_inventory,
    deployment_contract_required,
    validate_deployment_contract,
)


def _environment(tmp_path: Path) -> dict[str, str]:
    return {
        "WB_RND_APP_ENV": "staging",
        "WB_RND_INTERIM_ENABLED": "1",
        "WB_RND_DEPLOYMENT_TARGET": "private-rnd-api",
        "WB_RND_DEPLOYMENT_ID": "deploy-op101",
        "WB_RND_CODE_COMMIT": "a" * 40,
        "WB_RND_IMAGE_COMMIT": "a" * 40,
        "WB_RND_INTERIM_DATABASE": str((tmp_path / "persistent.sqlite3").resolve()),
        "WB_RND_DATABASE_DURABILITY": "provider_persistent_volume",
        "WB_RND_INTERNAL_AUTH_SCHEME": "shared_header_hmac_sha256_v1",
        "WB_RND_INTERIM_INTERNAL_TOKEN": "secret-token-material-at-least-32-bytes",
        "WB_RND_INTERNAL_TOKEN_SECRET_REF": "provider://secrets/wb-rnd-token",
        "WB_RND_WORKERS": "1",
    }


def test_deployment_contract_is_complete_and_does_not_expose_token(tmp_path: Path) -> None:
    contract = validate_deployment_contract(_environment(tmp_path)).to_dict()

    assert contract["status"] == "READY_FOR_PROVIDER_DEPLOYMENT"
    assert contract["database_durability"] == "provider_persistent_volume"
    assert contract["internal_auth_scheme"] == "shared_header_hmac_sha256_v1"
    assert "secret-token-material" not in str(contract)
    assert contract["provider_secret_store_configured"] is True


def test_staging_and_production_cannot_disable_contract() -> None:
    assert deployment_contract_required("staging", {}) is True
    assert deployment_contract_required("production", {}) is True
    assert deployment_contract_required("local", {}) is False


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("WB_RND_APP_ENV", "local", "app_env_must_be_staging_or_production"),
        ("WB_RND_INTERIM_ENABLED", "0", "interim_api_must_be_enabled"),
        ("WB_RND_INTERIM_DATABASE", "relative.sqlite3", "interim_database_must_be_absolute"),
        ("WB_RND_DATABASE_DURABILITY", "ephemeral", "database_durability"),
        ("WB_RND_INTERIM_INTERNAL_TOKEN", "short", "internal_token_minimum_32_bytes"),
        ("WB_RND_WORKERS", "2", "sqlite_deployment_requires_one_worker"),
        ("WB_RND_INTERNAL_TOKEN_SECRET_REF", "", "provider_secret_reference_required"),
    ],
)
def test_deployment_contract_fails_closed(
    tmp_path: Path, key: str, value: str, error: str
) -> None:
    environment = _environment(tmp_path)
    environment[key] = value

    with pytest.raises(ValueError, match=error):
        validate_deployment_contract(environment)


def test_endpoint_inventory_is_derived_from_mounted_routes() -> None:
    inventory = build_endpoint_inventory(list(app.routes))

    assert inventory["status"] == "COMPLETE"
    assert set(inventory["families"]) == set(REQUIRED_ENDPOINT_FAMILIES)
    assert all(item["mounted"] for item in inventory["families"].values())


def test_web_concurrency_alias_cannot_bypass_single_worker_contract(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment.pop("WB_RND_WORKERS")
    environment["WEB_CONCURRENCY"] = "2"

    with pytest.raises(ValueError, match="sqlite_deployment_requires_one_worker"):
        validate_deployment_contract(environment)


def test_declared_commit_must_match_image_commit(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment["WB_RND_IMAGE_COMMIT"] = "b" * 40

    with pytest.raises(ValueError, match="code_commit_must_match_image_commit"):
        validate_deployment_contract(environment)


def test_health_exposes_non_secret_endpoint_inventory() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["endpoint_inventory"]["status"] == "COMPLETE"
    assert response.json()["deployment_contract"] is None
