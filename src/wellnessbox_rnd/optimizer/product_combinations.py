from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

NormalizedDoseUnitV1 = Literal["ng", "milli_IU"]
ProductFormulationV1 = Literal["capsule", "tablet", "powder", "liquid", "gummy", "other"]


class ProductOfferV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pharmacy_product_id: StrictInt = Field(ge=1)
    price_krw: StrictInt = Field(ge=0)
    stock_count: StrictInt = Field(ge=1)
    option_type: str | None = None
    capacity: str | None = None


class ProductIngredientAmountV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service_ingredient_id: str = Field(pattern=r"^ING:[A-Z0-9_]+$")
    normalized_amount: StrictInt = Field(gt=0)
    normalized_unit: NormalizedDoseUnitV1
    source_label: str = Field(min_length=1)
    source_value: str = Field(min_length=1)


class SelectedProductV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    product_id: StrictInt = Field(ge=1)
    product_name: str = Field(min_length=1)
    formulation_kind: ProductFormulationV1
    offer: ProductOfferV1
    ingredient_amounts: tuple[ProductIngredientAmountV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_ingredient_amounts(self) -> SelectedProductV1:
        identities = [item.service_ingredient_id for item in self.ingredient_amounts]
        if len(set(identities)) != len(identities):
            raise ValueError("product ingredient identities must be unique")
        return self


class IngredientDoseTotalV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service_ingredient_id: str = Field(pattern=r"^ING:[A-Z0-9_]+$")
    total_declared_amount: StrictInt = Field(gt=0)
    unit: NormalizedDoseUnitV1
    product_ids: tuple[StrictInt, ...] = Field(min_length=1)
    duplicate_across_products: bool


class ProductCombinationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["wb_rnd_product_combination_v1"]
    combination_id: str = Field(pattern=r"^combo_[a-f0-9]{16}$")
    recommendation_service_ingredient_ids: tuple[str, ...] = Field(min_length=1)
    selected_products: tuple[SelectedProductV1, ...] = Field(min_length=1)
    product_count: StrictInt = Field(ge=1)
    total_cost_krw: StrictInt = Field(ge=0)
    ingredient_totals: tuple[IngredientDoseTotalV1, ...] = Field(min_length=1)
    duplicate_ingredient_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_derived_combination(self) -> ProductCombinationV1:
        recommendation_ids = self.recommendation_service_ingredient_ids
        if len(set(recommendation_ids)) != len(recommendation_ids):
            raise ValueError("recommendation ingredient identities must be unique")
        product_ids = tuple(item.product_id for item in self.selected_products)
        if product_ids != tuple(sorted(product_ids)) or len(set(product_ids)) != len(product_ids):
            raise ValueError("selected products must have unique sorted identities")
        if self.product_count != len(self.selected_products):
            raise ValueError("product count does not match selected products")
        if self.total_cost_krw != sum(item.offer.price_krw for item in self.selected_products):
            raise ValueError("total cost does not match selected offers")

        amounts: defaultdict[tuple[str, str], int] = defaultdict(int)
        amount_product_ids: defaultdict[tuple[str, str], set[int]] = defaultdict(set)
        ingredient_product_ids: defaultdict[str, set[int]] = defaultdict(set)
        for product in self.selected_products:
            for item in product.ingredient_amounts:
                key = (item.service_ingredient_id, item.normalized_unit)
                amounts[key] += item.normalized_amount
                amount_product_ids[key].add(product.product_id)
                ingredient_product_ids[item.service_ingredient_id].add(product.product_id)
        expected_totals = tuple(
            IngredientDoseTotalV1(
                service_ingredient_id=ingredient_id,
                total_declared_amount=amounts[(ingredient_id, unit)],
                unit=unit,
                product_ids=tuple(sorted(amount_product_ids[(ingredient_id, unit)])),
                duplicate_across_products=len(ingredient_product_ids[ingredient_id]) > 1,
            )
            for ingredient_id, unit in sorted(amounts)
        )
        if self.ingredient_totals != expected_totals:
            raise ValueError("ingredient totals do not match selected products")
        expected_duplicates = tuple(
            sorted(
                {
                    item.service_ingredient_id
                    for item in expected_totals
                    if item.duplicate_across_products
                }
            )
        )
        if self.duplicate_ingredient_ids != expected_duplicates:
            raise ValueError("duplicate ingredient identities do not match totals")

        identity = [
            {
                "product_id": item.product_id,
                "pharmacy_product_id": item.offer.pharmacy_product_id,
            }
            for item in self.selected_products
        ]
        digest = hashlib.sha256(
            json.dumps(identity, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        if self.combination_id != f"combo_{digest}":
            raise ValueError("combination identity does not match selected offers")
        return self


class ProductCombinationEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["op063_op064_product_combination_evidence_v1"]
    combinations: tuple[ProductCombinationV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_combination_set(self) -> ProductCombinationEvidenceV1:
        identities = tuple(item.combination_id for item in self.combinations)
        if identities != tuple(sorted(identities)) or len(set(identities)) != len(identities):
            raise ValueError("combination identities must be unique and sorted")
        return self


__all__ = [
    "IngredientDoseTotalV1",
    "ProductCombinationEvidenceV1",
    "ProductCombinationV1",
    "ProductIngredientAmountV1",
    "ProductOfferV1",
    "SelectedProductV1",
]
