from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unicodedata import normalize as normalize_unicode

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

FIXTURE_PATH = Path("data/samples/api_recommend_consent_hash_request_v1.json")
client = TestClient(app)


def _load_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _resolve_mapping(
    payload: dict[str, Any],
    container_path: tuple[str, ...],
) -> dict[str, Any]:
    current: Any = payload
    for key in container_path:
        assert isinstance(current, dict)
        current = current[key]
    assert isinstance(current, dict)
    return current


def _assert_model_and_api_error(payload: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        RecommendationRequest.model_validate(payload)

    response = client.post("/v1/recommend", json=payload)

    assert response.status_code == 422
    assert message in response.text


@pytest.mark.parametrize(
    ("container_path", "unsupported_field"),
    [
        ((), "unsupported_top_level"),
        (("user_profile",), "unsupported_profile_field"),
        (("lifestyle",), "unsupported_lifestyle_field"),
        (("input_availability",), "unsupported_source"),
        (("preferences",), "unsupported_preference"),
    ],
)
def test_unsupported_fields_fail_closed_at_model_and_api_boundaries(
    container_path: tuple[str, ...],
    unsupported_field: str,
) -> None:
    payload = _load_payload()
    _resolve_mapping(payload, container_path)[unsupported_field] = "must-not-disappear"

    with pytest.raises(ValidationError) as error:
        RecommendationRequest.model_validate(payload)

    matching_errors = [
        item
        for item in error.value.errors()
        if item["type"] == "extra_forbidden" and item["loc"][-1] == unsupported_field
    ]
    assert len(matching_errors) == 1

    response = client.post("/v1/recommend", json=payload)
    assert response.status_code == 422
    assert any(
        item["type"] == "extra_forbidden"
        and item["loc"][-1] == unsupported_field
        for item in response.json()["detail"]
    )


def test_ambiguous_structured_dose_unit_is_rejected_at_model_and_api_boundaries() -> None:
    payload = _load_payload()
    payload["medications"] = [
        {
            "name": "metformin",
            "dose": {"amount": 500, "unit": "milligrams"},
        }
    ]

    with pytest.raises(ValidationError) as error:
        RecommendationRequest.model_validate(payload)
    assert any(
        item["type"] == "enum" and item["loc"][-1] == "unit"
        for item in error.value.errors()
    )

    response = client.post("/v1/recommend", json=payload)
    assert response.status_code == 422
    assert any(
        item["type"] == "enum" and item["loc"][-1] == "unit"
        for item in response.json()["detail"]
    )


def test_unsupported_laboratory_unit_is_rejected_at_model_and_api_boundaries() -> None:
    payload = _load_payload()
    payload["laboratory_observations"] = [
        {
            "code": "hba1c",
            "value": 6.1,
            "unit": "bananas",
            "reference_range": {"low": 4.0, "high": 5.6},
            "measured_at": "2026-07-15T09:30:00+09:00",
            "source": "survey",
        }
    ]

    _assert_model_and_api_error(payload, "unsupported laboratory unit")


def test_conflicting_duplicate_medications_are_rejected() -> None:
    payload = _load_payload()
    payload["medications"] = [
        {
            "name": "Metformin",
            "classification": {"code": "A10BA02", "system": "ATC"},
            "dose": {"amount": 500, "unit": "mg"},
        },
        {
            "name": " metformin ",
            "classification": {"code": "a10ba02", "system": "atc"},
            "dose": {"amount": 850, "unit": "mg"},
        },
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate medications")


def test_unicode_equivalent_medication_names_cannot_bypass_conflict_rejection() -> None:
    payload = _load_payload()
    medication_name = "메트포르민"
    payload["medications"] = [
        {
            "name": medication_name,
            "dose": {"amount": 500, "unit": "mg"},
        },
        {
            "name": normalize_unicode("NFD", medication_name),
            "dose": {"amount": 850, "unit": "mg"},
        },
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate medications")


def test_identical_duplicate_medications_remain_compatible() -> None:
    payload = _load_payload()
    medication = {
        "name": "Metformin",
        "classification": {"code": "A10BA02", "system": "ATC"},
        "dose": {"amount": 500, "unit": "mg"},
    }
    payload["medications"] = [medication, deepcopy(medication)]

    request = RecommendationRequest.model_validate(payload)
    response = client.post("/v1/recommend", json=payload)

    assert len(request.medications) == 2
    assert response.status_code == 200


def test_conflicting_duplicate_supplements_are_rejected() -> None:
    payload = _load_payload()
    payload["current_supplements"] = [
        {
            "name": "Daily D",
            "ingredients": [
                {
                    "name": "Vitamin D3",
                    "daily_dose": {"amount": 25, "unit": "mcg"},
                }
            ],
        },
        {
            "name": " daily d ",
            "ingredients": [
                {
                    "name": "vitamin d3",
                    "daily_dose": {"amount": 50, "unit": "mcg"},
                }
            ],
        },
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate supplements")


def test_compatibility_equivalent_supplement_names_cannot_bypass_conflict_rejection() -> None:
    payload = _load_payload()
    payload["current_supplements"] = [
        {
            "name": "Daily D",
            "daily_dose": {"amount": 1, "unit": "capsule"},
            "ingredients": ["Vitamin D3"],
        },
        {
            "name": "Ｄａｉｌｙ Ｄ",
            "daily_dose": {"amount": 2, "unit": "capsule"},
            "ingredients": ["Vitamin D3"],
        },
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate supplements")


def test_conflicting_duplicate_ingredients_within_supplement_are_rejected() -> None:
    payload = _load_payload()
    payload["current_supplements"] = [
        {
            "name": "Daily D",
            "ingredients": [
                {
                    "name": "Vitamin D3",
                    "daily_dose": {"amount": 25, "unit": "mcg"},
                },
                {
                    "name": " vitamin d3 ",
                    "daily_dose": {"amount": 50, "unit": "mcg"},
                },
            ],
        }
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate supplement ingredients")


def test_unicode_equivalent_ingredient_names_cannot_bypass_conflict_rejection() -> None:
    payload = _load_payload()
    ingredient_name = "비타민 D3"
    payload["current_supplements"] = [
        {
            "name": "Daily D",
            "ingredients": [
                {
                    "name": ingredient_name,
                    "daily_dose": {"amount": 25, "unit": "mcg"},
                },
                {
                    "name": normalize_unicode("NFD", ingredient_name),
                    "daily_dose": {"amount": 50, "unit": "mcg"},
                },
            ],
        }
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate supplement ingredients")


def test_exact_catalog_aliases_cannot_bypass_ingredient_conflict_rejection() -> None:
    payload = _load_payload()
    payload["current_supplements"] = [
        {
            "name": "Daily C",
            "ingredients": [
                {
                    "name": "vitamin c",
                    "daily_dose": {"amount": 100, "unit": "mg"},
                },
                {
                    "name": "ascorbic acid",
                    "daily_dose": {"amount": 200, "unit": "mg"},
                },
            ],
        }
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate supplement ingredients")


def test_duplicate_supplement_signatures_preserve_ingredient_multiplicity() -> None:
    payload = _load_payload()
    ingredient = {
        "name": "Vitamin D3",
        "daily_dose": {"amount": 25, "unit": "mcg"},
    }
    payload["current_supplements"] = [
        {
            "name": "Daily D",
            "ingredients": [ingredient],
        },
        {
            "name": " daily d ",
            "ingredients": [deepcopy(ingredient), deepcopy(ingredient)],
        },
    ]

    _assert_model_and_api_error(payload, "conflicting duplicate supplements")


def test_identical_duplicate_supplements_remain_compatible() -> None:
    payload = _load_payload()
    supplement = {
        "name": "Daily D",
        "ingredients": [
            {
                "name": "Vitamin D3",
                "daily_dose": {"amount": 25, "unit": "mcg"},
            }
        ],
    }
    payload["current_supplements"] = [supplement, deepcopy(supplement)]

    request = RecommendationRequest.model_validate(payload)
    response = client.post("/v1/recommend", json=payload)

    assert len(request.current_supplements) == 2
    assert response.status_code == 200


def test_existing_representative_request_remains_accepted_without_field_loss() -> None:
    payload = _load_payload()

    request = RecommendationRequest.model_validate(payload)
    response = client.post("/v1/recommend", json=payload)

    assert request.model_dump(mode="json", exclude_none=False) == payload
    assert response.status_code == 200
    assert response.json()["request_id"] == payload["request_id"]
