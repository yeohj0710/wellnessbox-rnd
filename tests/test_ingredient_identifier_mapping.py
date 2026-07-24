from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.domain.loaders import load_ingredient_catalog

RND_ROOT = Path(__file__).resolve().parents[1]
RND_CONTRACT_PATH = (
    RND_ROOT / "data/contracts/wellnessbox_ingredient_identifier_map_v1.json"
)
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(RND_ROOT.parent / "wellnessbox"))
).resolve()
SERVICE_CONTRACT_PATH = (
    SERVICE_ROOT / "contracts/wb-rnd/ingredient-identifier-map-v1.json"
)
SERVICE_MODEL_PATH = SERVICE_ROOT / "data/tips/proxy-recommendation-model.json"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mapping(_StrictModel):
    service_ingredient_id: str = Field(pattern=r"^ING:[A-Z0-9_]+$")
    rnd_ingredient_key: str = Field(pattern=r"^[a-z0-9_]+$")
    relationship: str
    allowed_directions: list[str] = Field(min_length=1)


class UnmappedService(_StrictModel):
    service_ingredient_id: str
    reason: str = Field(min_length=1)


class UnmappedRnd(_StrictModel):
    rnd_ingredient_key: str
    reason: str = Field(min_length=1)


class IngredientMapContract(_StrictModel):
    schema_version: str
    mapping_version: str
    effective_at: str
    service_namespace: str
    service_candidate_source: str
    rnd_namespace: str
    rnd_catalog_source: str
    mappings: list[Mapping] = Field(min_length=1)
    unmapped_service_identifiers: list[UnmappedService]
    unmapped_rnd_identifiers: list[UnmappedRnd]


def _contract() -> IngredientMapContract:
    return IngredientMapContract.model_validate_json(
        RND_CONTRACT_PATH.read_text(encoding="utf-8")
    )


def test_service_and_rnd_identifier_map_contracts_are_byte_identical() -> None:
    assert SERVICE_CONTRACT_PATH.is_file()
    assert SERVICE_CONTRACT_PATH.read_bytes() == RND_CONTRACT_PATH.read_bytes()


def test_identifier_map_covers_both_current_catalogs_without_ambiguity() -> None:
    contract = _contract()
    service_model = json.loads(SERVICE_MODEL_PATH.read_text(encoding="utf-8"))
    service_ids = set(service_model["ingredients"])
    rnd_keys = {item.key for item in load_ingredient_catalog()}

    mapped_service = [item.service_ingredient_id for item in contract.mappings]
    mapped_rnd = [item.rnd_ingredient_key for item in contract.mappings]
    unmapped_service = [
        item.service_ingredient_id for item in contract.unmapped_service_identifiers
    ]
    unmapped_rnd = [
        item.rnd_ingredient_key for item in contract.unmapped_rnd_identifiers
    ]

    assert len(mapped_service) == len(set(mapped_service))
    assert len(mapped_rnd) == len(set(mapped_rnd))
    assert not set(mapped_service) & set(unmapped_service)
    assert not set(mapped_rnd) & set(unmapped_rnd)
    assert service_ids.issubset(set(mapped_service) | set(unmapped_service))
    assert set(mapped_rnd) | set(unmapped_rnd) == rnd_keys


def test_identifier_map_keeps_lossy_relationships_directional() -> None:
    contract = _contract()
    by_rnd_key = {item.rnd_ingredient_key: item for item in contract.mappings}

    for rnd_key in {"magnesium_glycinate", "vitamin_d3", "calcium_citrate"}:
        mapping = by_rnd_key[rnd_key]
        assert mapping.relationship == "service_broader"
        assert mapping.allowed_directions == ["rnd_to_service"]
    soluble_fiber = by_rnd_key["soluble_fiber"]
    assert soluble_fiber.relationship == "service_narrower"
    assert soluble_fiber.allowed_directions == ["rnd_to_service"]

    l_theanine = by_rnd_key["l_theanine"]
    assert l_theanine.service_ingredient_id == "ING:L_THEANINE"
    assert l_theanine.relationship == "equivalent"
    assert set(l_theanine.allowed_directions) == {"service_to_rnd", "rnd_to_service"}


def test_every_mapping_supports_the_live_rnd_to_service_response_direction() -> None:
    contract = _contract()

    assert contract.schema_version == "wb_rnd_ingredient_identifier_map_v1"
    assert contract.mapping_version == "2026-07-24.1"
    assert all(
        "rnd_to_service" in mapping.allowed_directions
        for mapping in contract.mappings
    )
