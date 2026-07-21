import hashlib
import json

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.optimizer.product_combinations import ProductCombinationV1


def _combination_payload() -> dict[str, object]:
    selected_products = [
        {
            "product_id": 29,
            "product_name": "multi mineral",
            "formulation_kind": "capsule",
            "offer": {
                "pharmacy_product_id": 10029,
                "price_krw": 10000,
                "stock_count": 5,
                "option_type": "30 days",
                "capacity": "30 capsules",
            },
            "ingredient_amounts": [
                {
                    "service_ingredient_id": "ING:MAGNESIUM",
                    "normalized_amount": 100000000,
                    "normalized_unit": "ng",
                    "source_label": "ingredient amount",
                    "source_value": "magnesium 100 mg",
                },
                {
                    "service_ingredient_id": "ING:ZINC",
                    "normalized_amount": 10000000,
                    "normalized_unit": "ng",
                    "source_label": "ingredient amount",
                    "source_value": "zinc 10 mg",
                },
            ],
        },
        {
            "product_id": 42,
            "product_name": "zinc single",
            "formulation_kind": "tablet",
            "offer": {
                "pharmacy_product_id": 10042,
                "price_krw": 9000,
                "stock_count": 3,
                "option_type": None,
                "capacity": None,
            },
            "ingredient_amounts": [
                {
                    "service_ingredient_id": "ING:ZINC",
                    "normalized_amount": 15000000,
                    "normalized_unit": "ng",
                    "source_label": "ingredient amount",
                    "source_value": "zinc 15 mg",
                }
            ],
        },
    ]
    identity = [
        {
            "product_id": item["product_id"],
            "pharmacy_product_id": item["offer"]["pharmacy_product_id"],
        }
        for item in selected_products
    ]
    digest = hashlib.sha256(
        json.dumps(identity, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "schema_version": "wb_rnd_product_combination_v1",
        "combination_id": f"combo_{digest}",
        "recommendation_service_ingredient_ids": ["ING:MAGNESIUM", "ING:ZINC"],
        "selected_products": selected_products,
        "product_count": 2,
        "total_cost_krw": 19000,
        "ingredient_totals": [
            {
                "service_ingredient_id": "ING:MAGNESIUM",
                "total_declared_amount": 100000000,
                "unit": "ng",
                "product_ids": [29],
                "duplicate_across_products": False,
            },
            {
                "service_ingredient_id": "ING:ZINC",
                "total_declared_amount": 25000000,
                "unit": "ng",
                "product_ids": [29, 42],
                "duplicate_across_products": True,
            },
        ],
        "duplicate_ingredient_ids": ["ING:ZINC"],
    }


def test_combination_validates_duplicate_and_total_dose() -> None:
    result = ProductCombinationV1.model_validate(_combination_payload())
    assert result.product_count == 2
    assert result.total_cost_krw == 19000
    assert result.duplicate_ingredient_ids == ("ING:ZINC",)
    assert result.ingredient_totals[1].total_declared_amount == 25000000


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product_count", 3),
        ("total_cost_krw", 1),
        ("duplicate_ingredient_ids", []),
        ("combination_id", "combo_0000000000000000"),
    ],
)
def test_combination_rejects_forged_derived_fields(field: str, value: object) -> None:
    payload = _combination_payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        ProductCombinationV1.model_validate(payload)


def test_combination_rejects_forged_total_and_product_ids() -> None:
    payload = _combination_payload()
    totals = payload["ingredient_totals"]
    assert isinstance(totals, list)
    totals[1] = {
        **totals[1],
        "total_declared_amount": 26000000,
        "product_ids": [42],
    }
    with pytest.raises(ValidationError):
        ProductCombinationV1.model_validate(payload)


def test_combination_rejects_duplicate_product_identity() -> None:
    payload = _combination_payload()
    products = payload["selected_products"]
    assert isinstance(products, list)
    products.append(products[0])
    payload["product_count"] = 3
    payload["total_cost_krw"] = 29000
    with pytest.raises(ValidationError):
        ProductCombinationV1.model_validate(payload)


def test_combination_rejects_extra_fields_and_is_immutable() -> None:
    payload = _combination_payload()
    payload["untracked_score"] = 1
    with pytest.raises(ValidationError):
        ProductCombinationV1.model_validate(payload)

    result = ProductCombinationV1.model_validate(_combination_payload())
    with pytest.raises(AttributeError):
        result.selected_products.append(result.selected_products[0])  # type: ignore[attr-defined]


def test_mass_and_iu_totals_remain_separate() -> None:
    payload = _combination_payload()
    products = payload["selected_products"]
    totals = payload["ingredient_totals"]
    assert isinstance(products, list)
    assert isinstance(totals, list)
    products[0]["ingredient_amounts"].append(
        {
            "service_ingredient_id": "ING:VITAMIN_D",
            "normalized_amount": 2000000,
            "normalized_unit": "milli_IU",
            "source_label": "ingredient amount",
            "source_value": "vitamin d 2000 IU",
        }
    )
    totals.insert(
        1,
        {
            "service_ingredient_id": "ING:VITAMIN_D",
            "total_declared_amount": 2000000,
            "unit": "milli_IU",
            "product_ids": [29],
            "duplicate_across_products": False,
        },
    )
    result = ProductCombinationV1.model_validate(payload)
    assert result.ingredient_totals[1].unit == "milli_IU"


def test_duplicate_identity_spans_separate_mass_and_iu_totals() -> None:
    payload = _combination_payload()
    products = payload["selected_products"]
    assert isinstance(products, list)
    products[1]["ingredient_amounts"][0]["normalized_unit"] = "milli_IU"
    totals = payload["ingredient_totals"]
    assert isinstance(totals, list)
    totals[1:] = [
        {
            "service_ingredient_id": "ING:ZINC",
            "total_declared_amount": 15000000,
            "unit": "milli_IU",
            "product_ids": [42],
            "duplicate_across_products": True,
        },
        {
            "service_ingredient_id": "ING:ZINC",
            "total_declared_amount": 10000000,
            "unit": "ng",
            "product_ids": [29],
            "duplicate_across_products": True,
        },
    ]

    result = ProductCombinationV1.model_validate(payload)
    assert result.duplicate_ingredient_ids == ("ING:ZINC",)
    assert [item.unit for item in result.ingredient_totals[1:]] == [
        "milli_IU",
        "ng",
    ]
