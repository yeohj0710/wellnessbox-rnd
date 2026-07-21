import hashlib
import json

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.optimizer.product_combinations import (
    CatalogProductIdentityV1,
    ProductCombinationCartCandidateV1,
    ProductCombinationFilterEvaluationV1,
    ProductCombinationFilterPolicyV1,
    ProductCombinationInventoryContextV1,
    ProductCombinationOptimizationInputV1,
    ProductCombinationRankingEvidenceV1,
    ProductCombinationV1,
    evaluate_product_combination_filters_v1,
    evaluate_product_combination_ranking_v1,
)


def _ranking_provenance(max_total_cost_krw: int = 35_000):
    optimization_input = ProductCombinationOptimizationInputV1.model_validate(
        {
            "recommendations": [
                {
                    "ingredient": "zinc",
                    "service_ingredient_id": "ING:ZINC",
                    "rank": 1,
                    "score": 0.9,
                    "evidence_ids": ["EV-1"],
                }
            ],
            "constraints": {
                "max_total_cost_krw": max_total_cost_krw,
                "max_products": 2,
                "excluded_ingredient_keys": [],
                "excluded_service_ingredient_ids": [],
                "safety_rule_ids": [],
            },
        }
    )
    catalog_identity = (
        CatalogProductIdentityV1.model_validate(
            {
                "id": 1,
                "name": "zinc",
                "categories": ["zinc"],
                "ingredient_declarations": [{"label": "ingredient", "value": "zinc 10 mg"}],
                "ingredient_amounts": [
                    {
                        "service_ingredient_id": "ING:ZINC",
                        "normalized_amount": 10000000,
                        "normalized_unit": "ng",
                        "source_label": "ingredient",
                        "source_value": "zinc 10 mg",
                    }
                ],
                "formulation": "tablet",
                "formulation_kind": "tablet",
                "offers": [
                    {
                        "pharmacy_product_id": 1,
                        "price_krw": 10000,
                        "stock_count": 1,
                        "option_type": None,
                        "capacity": None,
                    }
                ],
            }
        ),
    )
    return optimization_input, catalog_identity


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


def _combination_variant(*, pharmacy_product_id: int, second_price_krw: int):
    payload = _combination_payload()
    products = payload["selected_products"]
    assert isinstance(products, list)
    products[1]["offer"]["pharmacy_product_id"] = pharmacy_product_id
    products[1]["offer"]["price_krw"] = second_price_krw
    payload["total_cost_krw"] = 10_000 + second_price_krw
    identity = [
        {
            "product_id": item["product_id"],
            "pharmacy_product_id": item["offer"]["pharmacy_product_id"],
        }
        for item in products
    ]
    digest = hashlib.sha256(
        json.dumps(identity, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    payload["combination_id"] = f"combo_{digest}"
    return payload


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


def test_combination_filter_recomputes_budget_and_product_count_exclusions() -> None:
    combinations = tuple(
        sorted(
            (
                ProductCombinationV1.model_validate(
                    _combination_variant(
                        pharmacy_product_id=20_001 + index,
                        second_price_krw=9_000 + index * 10_000,
                    )
                )
                for index in range(3)
            ),
            key=lambda item: item.combination_id,
        )
    )
    policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=25_000,
        max_products=2,
    )

    result = evaluate_product_combination_filters_v1(combinations, policy)

    assert result.pre_filter_combination_count == 3
    assert result.eligible_combination_count == 1
    assert len(result.budget_excluded_combination_ids) == 2
    assert result.product_count_excluded_combination_ids == ()
    assert result.safety_excluded_combination_ids == ()


def test_combination_filter_rejects_safety_excluded_ingredient_reentry() -> None:
    combination = ProductCombinationV1.model_validate(_combination_payload())
    policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=100_000,
        max_products=5,
        excluded_service_ingredient_ids=("ING:ZINC",),
        safety_rule_ids=("SAFE-OP066-TEST",),
    )

    result = evaluate_product_combination_filters_v1((combination,), policy)

    assert result.eligible_combination_ids == ()
    assert result.safety_excluded_combination_ids == (combination.combination_id,)


def test_combination_filter_rejects_forged_output_and_invalid_policy() -> None:
    combination = ProductCombinationV1.model_validate(_combination_payload())
    policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=100_000,
        max_products=5,
    )
    result = evaluate_product_combination_filters_v1((combination,), policy)
    forged = result.model_dump(mode="json")
    forged["eligible_combination_ids"] = []
    with pytest.raises(ValidationError):
        ProductCombinationFilterEvaluationV1.model_validate(forged)

    with pytest.raises(ValidationError):
        ProductCombinationFilterPolicyV1(
            schema_version="product_optimization_constraints_v1",
            max_total_cost_krw=100_000,
            max_products=5,
            excluded_service_ingredient_ids=("ING:ZINC",),
        )


def test_combination_ranking_recomputes_top_k_reasons_and_result_identity() -> None:
    combinations = tuple(
        sorted(
            (
                ProductCombinationV1.model_validate(
                    _combination_variant(
                        pharmacy_product_id=30_001 + index,
                        second_price_krw=9_000 + index * 10_000,
                    )
                )
                for index in range(4)
            ),
            key=lambda item: item.combination_id,
        )
    )
    policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=35_000,
        max_products=2,
    )

    first = evaluate_product_combination_ranking_v1(
        combinations,
        policy,
        max_ranked_combinations=1,
        optimization_input=_ranking_provenance()[0],
        catalog_identity=_ranking_provenance()[1],
    )
    second = evaluate_product_combination_ranking_v1(
        combinations,
        policy,
        max_ranked_combinations=1,
        optimization_input=_ranking_provenance()[0],
        catalog_identity=_ranking_provenance()[1],
    )

    assert first == second
    assert first.top_k[0].rank == 1
    assert first.top_k[0].ranking_tuple[:2] == (19_000, 2)
    reasons = {item.combination_id: item.reason_codes for item in first.non_selection}
    assert sum("HIGHER_COST" in item for item in reasons.values()) == 1
    assert sum("OVER_BUDGET" in item for item in reasons.values()) == 2
    assert first.replay_identity.result_sha256 == second.replay_identity.result_sha256


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("top_k", 0, "rank"), 2),
        (("non_selection", 0, "reason_codes"), []),
        (("replay_identity", "result_sha256"), "0" * 64),
        (("replay_identity", "optimization_input", "recommendations", 0, "score"), 0.8),
        (("catalog_identity", 0, "name"), "forged catalog name"),
    ],
)
def test_combination_ranking_rejects_forged_outputs(
    path: tuple[object, ...], value: object
) -> None:
    combinations = tuple(
        sorted(
            (
                ProductCombinationV1.model_validate(
                    _combination_variant(
                        pharmacy_product_id=40_001 + index,
                        second_price_krw=9_000 + index * 10_000,
                    )
                )
                for index in range(3)
            ),
            key=lambda item: item.combination_id,
        )
    )
    policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=25_000,
        max_products=2,
    )
    payload = evaluate_product_combination_ranking_v1(
        combinations,
        policy,
        max_ranked_combinations=1,
        optimization_input=_ranking_provenance(25_000)[0],
        catalog_identity=_ranking_provenance(25_000)[1],
    ).model_dump(mode="json")
    target: object = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        ProductCombinationRankingEvidenceV1.model_validate(payload)


def test_combination_ranking_rejects_policy_outside_hashed_input() -> None:
    combination = ProductCombinationV1.model_validate(_combination_payload())
    mismatched_policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=1,
        max_products=2,
    )
    with pytest.raises(ValidationError, match="policy does not match"):
        evaluate_product_combination_ranking_v1(
            (combination,),
            mismatched_policy,
            max_ranked_combinations=1,
            optimization_input=_ranking_provenance()[0],
            catalog_identity=_ranking_provenance()[1],
        )


def test_inventory_context_rejects_forged_combination_identity() -> None:
    with pytest.raises(ValidationError, match="identity does not match"):
        ProductCombinationInventoryContextV1.model_validate(
            {
                "schema_version": "product_combination_inventory_context_v1",
                "previous_catalog_version": f"catalog_{'1' * 64}",
                "previous_combination_id": f"combo_{'2' * 16}",
                "previous_selections": [{"product_id": 1, "pharmacy_product_id": 10}],
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approval_required", False),
        ("approval_status", "APPROVED"),
        ("cart_storage_written", True),
        ("order_created", True),
        ("order_id", 1),
    ],
)
def test_cart_candidate_rejects_preapproval_side_effects(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "schema_version": "product_combination_cart_candidate_v1",
        "status": "READY",
        "unavailable_reason": None,
        "source_combination_id": f"combo_{'1' * 16}",
        "items": [
            {
                "productId": 1,
                "productName": "zinc",
                "optionType": "30 days",
                "quantity": 1,
            }
        ],
        "approval_required": True,
        "approval_status": "NOT_APPROVED",
        "cart_storage_written": False,
        "order_created": False,
        "order_id": None,
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        ProductCombinationCartCandidateV1.model_validate(payload)
