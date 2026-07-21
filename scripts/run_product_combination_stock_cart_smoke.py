from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.optimizer.product_combinations import (
    CatalogProductIdentityV1,
    ProductCombinationFilterPolicyV1,
    ProductCombinationInventoryContextV1,
    ProductCombinationOptimizationInputV1,
    ProductCombinationStockCartEvidenceV1,
    ProductCombinationV1,
    evaluate_product_combination_ranking_v1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")).resolve()
DEFAULT_OUTPUT = RND_ROOT / (
    "data/original_plan/evidence/op069_op070_product_combination_stock_cart_smoke_v1.json"
)
RND_SOURCE_PATHS = [
    "scripts/run_product_combination_stock_cart_smoke.py",
    "src/wellnessbox_rnd/optimizer/__init__.py",
    "src/wellnessbox_rnd/optimizer/product_combinations.py",
    "tests/test_product_combinations.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/route.ts",
    "contracts/wb-rnd/ingredient-identifier-map-v1.json",
    "contracts/wb-rnd/product-candidate-match-v1.json",
    "lib/client/cart-storage.ts",
    "lib/server/wb-rnd-interim-route.ts",
    "lib/server/wb-rnd-product-candidates.ts",
    "scripts/qa/check-rnd-product-candidates.cts",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for root_name, root, paths in (
        ("wellnessbox-rnd", RND_ROOT, RND_SOURCE_PATHS),
        ("wellnessbox", SERVICE_ROOT, SERVICE_SOURCE_PATHS),
    ):
        for relative in sorted(paths):
            digest.update(f"{root_name}/{relative}".encode())
            digest.update(b"\0")
            digest.update((root / relative).read_bytes().replace(b"\r\n", b"\n"))
            digest.update(b"\0")
    return digest.hexdigest()


def _source_commit(root: Path, paths: list[str]) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _service_report(output_path: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment.update(
        {
            "WB_RND_PRODUCT_SMOKE_OUTPUT": str(output_path),
            "WB_RND_INCLUDE_PRODUCT_COMBINATION_STOCK_CART_EVIDENCE": "1",
        }
    )
    subprocess.run(
        [
            "node",
            "--conditions=react-server",
            "--import",
            "tsx",
            "scripts/qa/check-rnd-product-candidates.cts",
        ],
        cwd=SERVICE_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def _ranking(observed: dict[str, object], prefix: str):
    replay = observed[f"{prefix}_replay_identity"]
    assert isinstance(replay, dict)
    optimization_input = ProductCombinationOptimizationInputV1.model_validate(
        replay["optimization_input"]
    )
    constraints = optimization_input.constraints
    policy = ProductCombinationFilterPolicyV1(
        schema_version="product_optimization_constraints_v1",
        max_total_cost_krw=constraints.max_total_cost_krw,
        max_products=constraints.max_products,
        excluded_service_ingredient_ids=constraints.excluded_service_ingredient_ids,
        safety_rule_ids=constraints.safety_rule_ids,
    )
    combinations = tuple(
        sorted(
            (
                ProductCombinationV1.model_validate(item)
                for item in observed[f"{prefix}_combinations"]
            ),
            key=lambda item: item.combination_id,
        )
    )
    catalog_identity = tuple(
        CatalogProductIdentityV1.model_validate(item)
        for item in observed[f"{prefix}_catalog_identity"]
    )
    evaluation = evaluate_product_combination_ranking_v1(
        combinations,
        policy,
        max_ranked_combinations=3,
        optimization_input=optimization_input,
        catalog_identity=catalog_identity,
    )
    assert [item.model_dump(mode="json") for item in evaluation.top_k] == observed[
        f"{prefix}_top_k"
    ]
    assert [item.model_dump(mode="json") for item in evaluation.non_selection] == observed[
        f"{prefix}_non_selection"
    ]
    assert evaluation.replay_identity.model_dump(mode="json") == replay
    return evaluation


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op069-op070-") as directory:
        service_report = _service_report(Path(directory) / "service-report.json")
    observed = service_report["observed"]
    assert isinstance(observed, dict)
    previous_ranking = _ranking(observed, "previous")
    current_ranking = _ranking(observed, "current")
    evidence = ProductCombinationStockCartEvidenceV1.model_validate(
        {
            "schema_version": "product_combination_stock_cart_evidence_v1",
            "inventory_context": observed["inventory_context"],
            "previous_ranking": previous_ranking.model_dump(mode="json"),
            "current_ranking": current_ranking.model_dump(mode="json"),
            "substitution": observed["stock_substitution"],
            "cart_candidate": observed["substituted_cart_candidate"],
        }
    )
    context = ProductCombinationInventoryContextV1.model_validate(observed["inventory_context"])
    return {
        "schema_version": "op069_op070_product_combination_stock_cart_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(SERVICE_ROOT, SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "previous_combination_count": len(previous_ranking.combinations),
            "current_combination_count": len(current_ranking.combinations),
            "missing_offer_count": len(evidence.substitution.missing_pharmacy_product_ids),
            "cart_item_count": len(evidence.cart_candidate.items),
            "stock_cart_evidence": evidence.model_dump(mode="json"),
        },
        "checks": {
            "previous_top_combination_identity_verified": True,
            "missing_inventory_independently_verified": True,
            "current_safe_top_combination_independently_recomputed": True,
            "existing_cart_item_contract_preserved": True,
            "service_only_context_not_forwarded_to_rnd": (
                observed["inventory_context_forwarded_to_rnd"] is False
            ),
            "approval_required": evidence.cart_candidate.approval_required,
            "cart_storage_written": evidence.cart_candidate.cart_storage_written,
            "order_created": evidence.cart_candidate.order_created,
            "previous_context_combination_id": context.previous_combination_id,
        },
        "evidence_boundary": {
            "op069_proven_stage": "INTEGRATED",
            "op069_required_stage": "INTEGRATED",
            "op070_proven_stage": "INTEGRATED",
            "op070_required_stage": "INTEGRATED",
            "service_route_function_integration_proven": True,
            "actual_prisma_query_executed": False,
            "cart_storage_mutated": False,
            "user_approval_obtained": False,
            "order_or_order_item_created": False,
            "payment_created": False,
            "production_deployment_proven": False,
            "production_operation_proven": False,
        },
    }


def main() -> None:
    arguments = _args()
    result = run_smoke()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
