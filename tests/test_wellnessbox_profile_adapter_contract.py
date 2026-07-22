from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationRequest,
    WellnessBoxChatUserProfileV1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
RND_FIXTURE_PATH = RND_ROOT / "data/contracts/wellnessbox_profile_adapter_v1.json"
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(RND_ROOT.parent / "wellnessbox"))
).resolve()
SERVICE_FIXTURE_PATH = SERVICE_ROOT / "contracts/wb-rnd/profile-adapter-v1.json"
client = TestClient(app)


def _load_contract() -> dict[str, object]:
    return json.loads(RND_FIXTURE_PATH.read_text(encoding="utf-8"))


def _materialize_validation_case_value(case: dict[str, object]) -> object:
    factory = case.get("value_factory")
    if not isinstance(factory, dict):
        return deepcopy(case["value"])
    if factory["kind"] == "repeated_text_array":
        return [str(factory["text"]) * int(factory["count"])]
    if factory["kind"] == "repeated_array_item":
        return [deepcopy(factory["item"])] * int(factory["count"])
    raise AssertionError(f"Unsupported validation fixture factory: {factory['kind']}")


SOURCE_PROFILE_VALIDATION_CASES = _load_contract()["source_profile_validation_cases"]


def test_wellnessbox_and_rnd_contract_snapshots_are_identical() -> None:
    assert SERVICE_FIXTURE_PATH.is_file()
    assert SERVICE_FIXTURE_PATH.read_bytes() == RND_FIXTURE_PATH.read_bytes()


def test_adapter_contract_minimizes_source_profile_and_preserves_operational_mapping() -> None:
    contract = _load_contract()
    source_profile = contract["source_profile"]
    expected_request = contract["expected_request"]

    request = RecommendationRequest.model_validate(expected_request)

    assert request.source_profile is not None
    assert request.source_profile.schema_version == "wellnessbox.chat.UserProfile.v1"
    assert request.source_profile.subject_id == "usr_11112222333344445555666677778888"
    expected_minimized_profile = {
        key: value
        for key, value in source_profile.items()
        if key not in {"name", "caffeineSensitivity"}
    }
    assert (
        request.source_profile.profile.model_dump(exclude_none=True)
        == expected_minimized_profile
    )
    assert type(request.source_profile.profile.heightCm) is int
    assert type(request.source_profile.profile.weightKg) is int
    assert request.user_profile.model_dump(mode="json") == expected_request["user_profile"]
    assert [goal.value for goal in request.goals] == expected_request["goals"]
    assert [item.name for item in request.medications] == source_profile["medications"]
    assert request.conditions == source_profile["conditions"]
    assert request.allergies == source_profile["allergies"]
    assert request.dietary_patterns == source_profile["dietaryRestrictions"]


def test_adapter_contract_is_accepted_by_real_recommendation_endpoint() -> None:
    expected_request = _load_contract()["expected_request"]

    response = client.post("/v1/recommend", json=expected_request)

    assert response.status_code == 200
    assert response.json()["request_id"] == expected_request["request_id"]


def test_openapi_exposes_the_versioned_wellnessbox_profile_contract() -> None:
    schemas = app.openapi()["components"]["schemas"]
    request_schema = schemas[
        "wellnessbox_rnd__schemas__recommendation__RecommendationRequest"
    ]

    assert "source_profile" in request_schema["properties"]
    assert list(schemas["WellnessBoxChatUserProfileV1"]["properties"]) == [
        "name",
        "age",
        "sex",
        "heightCm",
        "weightKg",
        "conditions",
        "medications",
        "allergies",
        "goals",
        "dietaryRestrictions",
        "pregnantOrBreastfeeding",
        "caffeineSensitivity",
    ]


def test_rnd_source_profile_trace_rejects_unknown_wellnessbox_properties() -> None:
    payload = deepcopy(_load_contract()["expected_request"])
    payload["source_profile"]["profile"]["silentLossCandidate"] = "must fail"

    with pytest.raises(ValidationError) as error:
        RecommendationRequest.model_validate(payload)

    assert any(
        item["type"] == "extra_forbidden"
        and item["loc"][-1] == "silentLossCandidate"
        for item in error.value.errors()
    )
    response = client.post("/v1/recommend", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "case",
    SOURCE_PROFILE_VALIDATION_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_rnd_source_profile_validation_matches_shared_contract(
    case: dict[str, object],
) -> None:
    profile = deepcopy(_load_contract()["source_profile"])
    field = str(case["field"])
    value = _materialize_validation_case_value(case)
    profile[field] = value

    if case["expected"] == "accepted":
        validated = WellnessBoxChatUserProfileV1.model_validate(profile)
        assert validated.model_dump(exclude_none=True)[field] == profile[field]

        payload = deepcopy(_load_contract()["expected_request"])
        payload["source_profile"]["profile"][field] = value
        if field == "medications":
            payload["medications"] = [{"name": item} for item in value]
        if field == "age":
            payload["user_profile"]["age"] = int(value)
        request = RecommendationRequest.model_validate(payload)
        assert request.source_profile is not None
        assert request.source_profile.profile.model_dump(exclude_none=True)[field] == value
        response = client.post("/v1/recommend", json=payload)
        assert response.status_code == 200
        return

    with pytest.raises(ValidationError) as error:
        WellnessBoxChatUserProfileV1.model_validate(profile)
    expected_path = str(case["issue_path"]).split(".")
    assert any(
        [str(part) for part in item["loc"]][: len(expected_path)] == expected_path
        for item in error.value.errors()
    )
