from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator

NormalizedDoseUnitV1 = Literal["ng", "milli_IU"]
ProductFormulationV1 = Literal["capsule", "tablet", "powder", "liquid", "gummy", "other"]
ProductCombinationNonSelectionReasonV1 = Literal[
    "DETERMINISTIC_ID_TIE_BREAK",
    "HIGHER_COST",
    "MORE_PRODUCTS",
    "OVER_BUDGET",
    "OVER_MAX_PRODUCTS",
    "SAFETY_EXCLUDED_INGREDIENT",
    "SEARCH_TRUNCATED",
]


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


class ProductCombinationFilterPolicyV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_optimization_constraints_v1"]
    max_total_cost_krw: StrictInt = Field(ge=0)
    max_products: StrictInt = Field(ge=1, le=20)
    excluded_service_ingredient_ids: tuple[str, ...] = ()
    safety_rule_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_policy(self) -> ProductCombinationFilterPolicyV1:
        for values, label in (
            (self.excluded_service_ingredient_ids, "excluded ingredient identities"),
            (self.safety_rule_ids, "safety rule identities"),
        ):
            if values != tuple(sorted(values)) or len(set(values)) != len(values):
                raise ValueError(f"{label} must be unique and sorted")
        if self.excluded_service_ingredient_ids and not self.safety_rule_ids:
            raise ValueError("safety exclusions require safety rule identities")
        return self


class ProductCombinationFilterEvaluationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_filter_evaluation_v1"]
    policy: ProductCombinationFilterPolicyV1
    combinations: tuple[ProductCombinationV1, ...] = Field(min_length=1)
    eligible_combination_ids: tuple[str, ...]
    budget_excluded_combination_ids: tuple[str, ...]
    product_count_excluded_combination_ids: tuple[str, ...]
    safety_excluded_combination_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_filter_evaluation(self) -> ProductCombinationFilterEvaluationV1:
        identities = tuple(item.combination_id for item in self.combinations)
        if identities != tuple(sorted(identities)) or len(set(identities)) != len(identities):
            raise ValueError("filter input combination identities must be unique and sorted")
        expected = _derive_filter_identities(self.combinations, self.policy)
        observed = (
            self.eligible_combination_ids,
            self.budget_excluded_combination_ids,
            self.product_count_excluded_combination_ids,
            self.safety_excluded_combination_ids,
        )
        if observed != expected:
            raise ValueError("filter evaluation does not match combinations and policy")
        return self

    @property
    def pre_filter_combination_count(self) -> int:
        return len(self.combinations)

    @property
    def eligible_combination_count(self) -> int:
        return len(self.eligible_combination_ids)


def evaluate_product_combination_filters_v1(
    combinations: tuple[ProductCombinationV1, ...],
    policy: ProductCombinationFilterPolicyV1,
) -> ProductCombinationFilterEvaluationV1:
    eligible, budget, product_count, safety = _derive_filter_identities(combinations, policy)
    return ProductCombinationFilterEvaluationV1(
        schema_version="product_combination_filter_evaluation_v1",
        policy=policy,
        combinations=combinations,
        eligible_combination_ids=eligible,
        budget_excluded_combination_ids=budget,
        product_count_excluded_combination_ids=product_count,
        safety_excluded_combination_ids=safety,
    )


def _derive_filter_identities(
    combinations: tuple[ProductCombinationV1, ...],
    policy: ProductCombinationFilterPolicyV1,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    budget = {
        item.combination_id
        for item in combinations
        if item.total_cost_krw > policy.max_total_cost_krw
    }
    product_count = {
        item.combination_id for item in combinations if item.product_count > policy.max_products
    }
    excluded = set(policy.excluded_service_ingredient_ids)
    safety = {
        item.combination_id
        for item in combinations
        if any(total.service_ingredient_id in excluded for total in item.ingredient_totals)
    }
    eligible = {
        item.combination_id
        for item in combinations
        if item.combination_id not in budget | product_count | safety
    }
    return (
        tuple(sorted(eligible)),
        tuple(sorted(budget)),
        tuple(sorted(product_count)),
        tuple(sorted(safety)),
    )


class RankedProductCombinationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_ranking_v1"]
    rank: StrictInt = Field(ge=1)
    combination_id: str = Field(pattern=r"^combo_[a-f0-9]{16}$")
    ranking_tuple: tuple[StrictInt, StrictInt, str]


class ProductCombinationNonSelectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    combination_id: str = Field(pattern=r"^combo_[a-f0-9]{16}$")
    reason_codes: tuple[ProductCombinationNonSelectionReasonV1, ...] = Field(min_length=1)


class RankingRecommendationIdentityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ingredient: str = Field(min_length=1)
    service_ingredient_id: str = Field(pattern=r"^ING:[A-Z0-9_]+$")
    rank: StrictInt = Field(ge=1)
    score: StrictFloat
    evidence_ids: tuple[str, ...]


class RankingConstraintIdentityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_total_cost_krw: StrictInt = Field(ge=0)
    max_products: StrictInt = Field(ge=1, le=20)
    excluded_ingredient_keys: tuple[str, ...]
    excluded_service_ingredient_ids: tuple[str, ...]
    safety_rule_ids: tuple[str, ...]


class ProductCombinationOptimizationInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    recommendations: tuple[RankingRecommendationIdentityV1, ...]
    constraints: RankingConstraintIdentityV1


class CatalogIngredientDeclarationIdentityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)


class CatalogOfferIdentityV1(ProductOfferV1):
    pass


class CatalogProductIdentityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: StrictInt = Field(ge=1)
    name: str = Field(min_length=1)
    categories: tuple[str, ...] = Field(min_length=1)
    ingredient_declarations: tuple[CatalogIngredientDeclarationIdentityV1, ...] = Field(
        min_length=1
    )
    ingredient_amounts: tuple[ProductIngredientAmountV1, ...] = Field(min_length=1)
    formulation: str = Field(min_length=1)
    formulation_kind: ProductFormulationV1
    offers: tuple[CatalogOfferIdentityV1, ...] = Field(min_length=1)


class ProductCombinationReplayIdentityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_replay_identity_v1"]
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    catalog_version: str = Field(pattern=r"^catalog_[a-f0-9]{64}$")
    catalog_version_contract: Literal["product_catalog_content_sha256_v1"]
    result_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    optimization_input: ProductCombinationOptimizationInputV1


class ProductCombinationRankingEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_ranking_evidence_v1"]
    policy: ProductCombinationFilterPolicyV1
    max_ranked_combinations: StrictInt = Field(ge=1, le=10)
    combinations: tuple[ProductCombinationV1, ...] = Field(min_length=1)
    top_k: tuple[RankedProductCombinationV1, ...]
    non_selection: tuple[ProductCombinationNonSelectionV1, ...]
    catalog_identity: tuple[CatalogProductIdentityV1, ...] = Field(min_length=1)
    replay_identity: ProductCombinationReplayIdentityV1

    @model_validator(mode="after")
    def validate_ranking_evidence(self) -> ProductCombinationRankingEvidenceV1:
        identities = tuple(item.combination_id for item in self.combinations)
        if identities != tuple(sorted(identities)) or len(set(identities)) != len(identities):
            raise ValueError("ranking input combinations must be unique and sorted")
        expected_top, expected_non_selection = _derive_ranking(
            self.combinations,
            self.policy,
            self.max_ranked_combinations,
        )
        if self.top_k != expected_top:
            raise ValueError("top-k ranking does not match combinations and policy")
        if self.non_selection != expected_non_selection:
            raise ValueError("non-selection reasons do not match combinations and policy")
        constraints = self.replay_identity.optimization_input.constraints
        if (
            self.policy.max_total_cost_krw != constraints.max_total_cost_krw
            or self.policy.max_products != constraints.max_products
            or self.policy.excluded_service_ingredient_ids
            != constraints.excluded_service_ingredient_ids
            or self.policy.safety_rule_ids != constraints.safety_rule_ids
        ):
            raise ValueError("ranking policy does not match canonical optimization input")
        expected_input = _canonical_sha256(
            self.replay_identity.optimization_input.model_dump(mode="json")
        )
        catalog_payload = [item.model_dump(mode="json") for item in self.catalog_identity]
        expected_catalog = f"catalog_{_canonical_sha256(catalog_payload)}"
        if self.replay_identity.input_sha256 != expected_input:
            raise ValueError("ranking input identity does not match canonical input")
        if self.replay_identity.catalog_version != expected_catalog:
            raise ValueError("catalog identity does not match canonical catalog")
        expected_result_sha256 = _ranking_result_sha256(
            input_sha256=self.replay_identity.input_sha256,
            catalog_version=self.replay_identity.catalog_version,
            top_k=self.top_k,
            non_selection=self.non_selection,
        )
        if self.replay_identity.result_sha256 != expected_result_sha256:
            raise ValueError("ranking result identity does not match canonical result")
        return self


class ProductCombinationInventorySelectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    product_id: StrictInt = Field(ge=1)
    pharmacy_product_id: StrictInt = Field(ge=1)


class ProductCombinationInventoryContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_inventory_context_v1"]
    previous_catalog_version: str = Field(pattern=r"^catalog_[a-f0-9]{64}$")
    previous_combination_id: str = Field(pattern=r"^combo_[a-f0-9]{16}$")
    previous_selections: tuple[ProductCombinationInventorySelectionV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_inventory_context(self) -> ProductCombinationInventoryContextV1:
        identities = tuple(
            (item.product_id, item.pharmacy_product_id) for item in self.previous_selections
        )
        if identities != tuple(sorted(identities)):
            raise ValueError("inventory selections must be sorted")
        if len({item.product_id for item in self.previous_selections}) != len(identities) or len(
            {item.pharmacy_product_id for item in self.previous_selections}
        ) != len(identities):
            raise ValueError("inventory selections must have unique identities")
        identity_payload = [
            {"product_id": product_id, "pharmacy_product_id": offer_id}
            for product_id, offer_id in identities
        ]
        expected = f"combo_{_canonical_sha256(identity_payload)[:16]}"
        if self.previous_combination_id != expected:
            raise ValueError("inventory combination identity does not match selections")
        return self


class ProductCombinationStockSubstitutionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_stock_substitution_v1"]
    status: Literal[
        "NOT_REQUESTED",
        "UNCHANGED",
        "SUBSTITUTED",
        "UNAVAILABLE",
        "SEARCH_TRUNCATED",
        "CATALOG_CHANGED",
    ]
    previous_catalog_version: str | None
    current_catalog_version: str = Field(pattern=r"^catalog_[a-f0-9]{64}$")
    previous_combination_id: str | None
    current_combination_id: str | None
    missing_pharmacy_product_ids: tuple[StrictInt, ...]
    safety_constraints_preserved: bool | None


class ProductCombinationCartItemV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    productId: StrictInt = Field(ge=1)
    productName: str = Field(min_length=1)
    optionType: str = Field(min_length=1)
    quantity: Literal[1]


class ProductCombinationCartCandidateV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_cart_candidate_v1"]
    status: Literal["READY", "UNAVAILABLE"]
    unavailable_reason: (
        Literal["SEARCH_TRUNCATED", "NO_ELIGIBLE_COMBINATION", "OPTION_TYPE_MISSING"] | None
    )
    source_combination_id: str | None
    items: tuple[ProductCombinationCartItemV1, ...]
    approval_required: Literal[True]
    approval_status: Literal["NOT_APPROVED"]
    cart_storage_written: Literal[False]
    order_created: Literal[False]
    order_id: None


class ProductCombinationStockCartEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["product_combination_stock_cart_evidence_v1"]
    inventory_context: ProductCombinationInventoryContextV1
    previous_ranking: ProductCombinationRankingEvidenceV1
    current_ranking: ProductCombinationRankingEvidenceV1
    substitution: ProductCombinationStockSubstitutionV1
    cart_candidate: ProductCombinationCartCandidateV1

    @model_validator(mode="after")
    def validate_stock_cart_evidence(self) -> ProductCombinationStockCartEvidenceV1:
        previous_top = self.previous_ranking.top_k[0]
        current_top = self.current_ranking.top_k[0]
        previous_combination = next(
            item
            for item in self.previous_ranking.combinations
            if item.combination_id == previous_top.combination_id
        )
        current_combination = next(
            item
            for item in self.current_ranking.combinations
            if item.combination_id == current_top.combination_id
        )
        expected_selections = tuple(
            ProductCombinationInventorySelectionV1(
                product_id=item.product_id,
                pharmacy_product_id=item.offer.pharmacy_product_id,
            )
            for item in previous_combination.selected_products
        )
        if self.inventory_context.previous_selections != expected_selections:
            raise ValueError("inventory context does not match previous top combination")
        if (
            self.inventory_context.previous_catalog_version
            != self.previous_ranking.replay_identity.catalog_version
        ):
            raise ValueError("inventory context does not match previous catalog")
        current_offer_ids = {
            offer.pharmacy_product_id
            for product in self.current_ranking.catalog_identity
            for offer in product.offers
        }
        expected_missing = tuple(
            sorted(
                item.pharmacy_product_id
                for item in self.inventory_context.previous_selections
                if item.pharmacy_product_id not in current_offer_ids
            )
        )
        substitution = self.substitution
        if (
            substitution.status != "SUBSTITUTED"
            or substitution.previous_catalog_version
            != self.inventory_context.previous_catalog_version
            or substitution.current_catalog_version
            != self.current_ranking.replay_identity.catalog_version
            or substitution.previous_combination_id != previous_top.combination_id
            or substitution.current_combination_id != current_top.combination_id
            or substitution.missing_pharmacy_product_ids != expected_missing
            or not expected_missing
            or substitution.safety_constraints_preserved is not True
        ):
            raise ValueError("stock substitution does not match ranked catalog evidence")
        expected_items = tuple(
            ProductCombinationCartItemV1(
                productId=item.product_id,
                productName=item.product_name,
                optionType=item.offer.option_type,
                quantity=1,
            )
            for item in current_combination.selected_products
        )
        if (
            self.cart_candidate.status != "READY"
            or self.cart_candidate.unavailable_reason is not None
            or self.cart_candidate.source_combination_id != current_top.combination_id
            or self.cart_candidate.items != expected_items
        ):
            raise ValueError("cart candidate does not match current top combination")
        return self


def evaluate_product_combination_ranking_v1(
    combinations: tuple[ProductCombinationV1, ...],
    policy: ProductCombinationFilterPolicyV1,
    *,
    max_ranked_combinations: int,
    optimization_input: ProductCombinationOptimizationInputV1,
    catalog_identity: tuple[CatalogProductIdentityV1, ...],
) -> ProductCombinationRankingEvidenceV1:
    top_k, non_selection = _derive_ranking(
        combinations,
        policy,
        max_ranked_combinations,
    )
    input_sha256 = _canonical_sha256(optimization_input.model_dump(mode="json"))
    catalog_version = (
        f"catalog_{_canonical_sha256([item.model_dump(mode='json') for item in catalog_identity])}"
    )
    replay_identity = ProductCombinationReplayIdentityV1(
        schema_version="product_combination_replay_identity_v1",
        input_sha256=input_sha256,
        catalog_version=catalog_version,
        catalog_version_contract="product_catalog_content_sha256_v1",
        result_sha256=_ranking_result_sha256(
            input_sha256=input_sha256,
            catalog_version=catalog_version,
            top_k=top_k,
            non_selection=non_selection,
        ),
        optimization_input=optimization_input,
    )
    return ProductCombinationRankingEvidenceV1(
        schema_version="product_combination_ranking_evidence_v1",
        policy=policy,
        max_ranked_combinations=max_ranked_combinations,
        combinations=combinations,
        top_k=top_k,
        non_selection=non_selection,
        catalog_identity=catalog_identity,
        replay_identity=replay_identity,
    )


def _derive_ranking(
    combinations: tuple[ProductCombinationV1, ...],
    policy: ProductCombinationFilterPolicyV1,
    max_ranked_combinations: int,
) -> tuple[
    tuple[RankedProductCombinationV1, ...],
    tuple[ProductCombinationNonSelectionV1, ...],
]:
    eligible, budget, product_count, safety = _derive_filter_identities(combinations, policy)
    combination_by_id = {item.combination_id: item for item in combinations}
    ranked = sorted(
        (combination_by_id[identity] for identity in eligible),
        key=lambda item: (
            item.total_cost_krw,
            item.product_count,
            item.combination_id,
        ),
    )
    top_k = tuple(
        RankedProductCombinationV1(
            schema_version="product_combination_ranking_v1",
            rank=index + 1,
            combination_id=item.combination_id,
            ranking_tuple=(
                item.total_cost_krw,
                item.product_count,
                item.combination_id,
            ),
        )
        for index, item in enumerate(ranked[:max_ranked_combinations])
    )
    top_identities = {item.combination_id for item in top_k}
    eligible_identities = set(eligible)
    ranking_cutoff = ranked[min(len(ranked), max_ranked_combinations) - 1] if ranked else None
    budget_identities = set(budget)
    product_count_identities = set(product_count)
    safety_identities = set(safety)
    non_selection_items: list[ProductCombinationNonSelectionV1] = []
    for item in combinations:
        if item.combination_id in top_identities:
            continue
        reasons: list[ProductCombinationNonSelectionReasonV1] = []
        if item.combination_id in budget_identities:
            reasons.append("OVER_BUDGET")
        if item.combination_id in product_count_identities:
            reasons.append("OVER_MAX_PRODUCTS")
        if item.combination_id in safety_identities:
            reasons.append("SAFETY_EXCLUDED_INGREDIENT")
        if item.combination_id in eligible_identities:
            if ranking_cutoff is not None and (item.total_cost_krw > ranking_cutoff.total_cost_krw):
                reasons.append("HIGHER_COST")
            elif ranking_cutoff is not None and (item.product_count > ranking_cutoff.product_count):
                reasons.append("MORE_PRODUCTS")
            else:
                reasons.append("DETERMINISTIC_ID_TIE_BREAK")
        non_selection_items.append(
            ProductCombinationNonSelectionV1(
                combination_id=item.combination_id,
                reason_codes=tuple(sorted(reasons)),
            )
        )
    non_selection = tuple(non_selection_items)
    return top_k, non_selection


def _ranking_result_sha256(
    *,
    input_sha256: str,
    catalog_version: str,
    top_k: tuple[RankedProductCombinationV1, ...],
    non_selection: tuple[ProductCombinationNonSelectionV1, ...],
) -> str:
    payload = {
        "schema_version": "product_combination_ranking_v1",
        "input_sha256": input_sha256,
        "catalog_version": catalog_version,
        "top_k": [item.model_dump(mode="json") for item in top_k],
        "non_selection": [item.model_dump(mode="json") for item in non_selection],
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


__all__ = [
    "CatalogProductIdentityV1",
    "IngredientDoseTotalV1",
    "ProductCombinationEvidenceV1",
    "ProductCombinationFilterEvaluationV1",
    "ProductCombinationFilterPolicyV1",
    "ProductCombinationNonSelectionV1",
    "ProductCombinationOptimizationInputV1",
    "ProductCombinationInventoryContextV1",
    "ProductCombinationStockCartEvidenceV1",
    "ProductCombinationStockSubstitutionV1",
    "ProductCombinationCartCandidateV1",
    "ProductCombinationRankingEvidenceV1",
    "ProductCombinationReplayIdentityV1",
    "ProductCombinationV1",
    "ProductIngredientAmountV1",
    "ProductOfferV1",
    "SelectedProductV1",
    "evaluate_product_combination_filters_v1",
    "evaluate_product_combination_ranking_v1",
    "RankedProductCombinationV1",
]
