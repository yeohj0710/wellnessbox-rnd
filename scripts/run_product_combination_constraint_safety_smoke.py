from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.optimizer.product_combinations import (
    ProductCombinationEvidenceV1,
    ProductCombinationFilterPolicyV1,
    evaluate_product_combination_filters_v1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")).resolve()
DEFAULT_OUTPUT = RND_ROOT / (
    "data/original_plan/evidence/"
    "op065_op066_product_combination_filter_smoke_v1.json"
)
RND_SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "scripts/run_product_combination_constraint_safety_smoke.py",
    "src/wellnessbox_rnd/optimizer/__init__.py",
    "src/wellnessbox_rnd/optimizer/product_combinations.py",
    "tests/test_interim_api.py",
    "tests/test_product_combinations.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/route.ts",
    "contracts/wb-rnd/ingredient-identifier-map-v1.json",
    "contracts/wb-rnd/product-candidate-catalog-snapshot-v1.json",
    "contracts/wb-rnd/product-candidate-match-v1.json",
    "lib/product/product-detail-facts.ts",
    "lib/product/product.catalog.ts",
    "lib/server/wb-rnd-ingredient-map.ts",
    "lib/server/wb-rnd-interim-route.ts",
    "lib/server/wb-rnd-product-candidates.ts",
    "lib/server/wb-rnd-tips-route-test-hook.ts",
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


def _service_report(temp: Path) -> dict[str, object]:
    output = temp / "service-product-combination-filter.json"
    environment = os.environ.copy()
    environment["WB_RND_PRODUCT_SMOKE_OUTPUT"] = str(output)
    environment["WB_RND_INCLUDE_PRODUCT_COMBINATION_FILTER_EVIDENCE"] = "1"
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
    return json.loads(output.read_text(encoding="utf-8"))


def _combination_set(raw: list[dict[str, object]]):
    return ProductCombinationEvidenceV1.model_validate(
        {
            "schema_version": "op063_op064_product_combination_evidence_v1",
            "combinations": sorted(raw, key=lambda item: item["combination_id"]),
        }
    ).combinations


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op065-op066-") as directory:
        service_report = _service_report(Path(directory))
    if (
        service_report["schema_version"]
        != "op065_op066_service_product_combination_filter_contract_v1"
    ):
        raise ValueError("unexpected service product-combination filter report")
    observed = service_report["observed"]

    constrained_policy_raw = observed["constrained_policy"]
    constrained_policy = ProductCombinationFilterPolicyV1.model_validate(
        {
            **{
                key: value
                for key, value in constrained_policy_raw.items()
                if key != "excluded_ingredient_keys"
            },
            "excluded_service_ingredient_ids": (),
        }
    )
    filter_inputs = _combination_set(observed["verified_filter_input_combinations"])
    constrained_evaluation = evaluate_product_combination_filters_v1(
        filter_inputs, constrained_policy
    )
    eligible = _combination_set(observed["verified_eligible_product_combinations"])
    eligible_ids = tuple(item.combination_id for item in eligible)
    constrained_resolution = observed["constrained_resolution"]
    assert constrained_evaluation.eligible_combination_ids == eligible_ids
    assert constrained_evaluation.pre_filter_combination_count == constrained_resolution[
        "pre_filter_combination_count"
    ]
    assert constrained_evaluation.eligible_combination_count == constrained_resolution[
        "combination_count"
    ]
    assert len(constrained_evaluation.budget_excluded_combination_ids) == (
        constrained_resolution["budget_excluded_count"]
    )
    assert len(constrained_evaluation.product_count_excluded_combination_ids) == (
        constrained_resolution["product_count_excluded_count"]
    )

    safety_policy_raw = observed["safety_filter_policy"]
    safety_policy = ProductCombinationFilterPolicyV1.model_validate(
        {
            key: value
            for key, value in safety_policy_raw.items()
            if key != "excluded_ingredient_keys"
        }
    )
    safety_inputs = _combination_set(
        observed["verified_safety_filter_input_combinations"]
    )
    safety_evaluation = evaluate_product_combination_filters_v1(
        safety_inputs, safety_policy
    )
    safety_resolution = observed["safety_filtered_resolution"]
    assert safety_evaluation.eligible_combination_ids == ()
    assert len(safety_evaluation.safety_excluded_combination_ids) == (
        safety_resolution["safety_excluded_count"]
    )
    assert observed["contradictory_safety_reentry_http_status"] == 502
    assert (
        observed["contradictory_safety_reentry_reason"]
        == "WB_RND_PRODUCT_MATCH_excluded_recommendation_reentered"
    )

    return {
        "schema_version": "op065_op066_product_combination_filter_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(SERVICE_ROOT, SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "constraint_filter_input_combination_count": len(filter_inputs),
            "eligible_combination_count": len(eligible),
            "budget_excluded_combination_count": len(
                constrained_evaluation.budget_excluded_combination_ids
            ),
            "product_count_excluded_combination_count": len(
                constrained_evaluation.product_count_excluded_combination_ids
            ),
            "safety_filter_input_combination_count": len(safety_inputs),
            "safety_excluded_combination_count": len(
                safety_evaluation.safety_excluded_combination_ids
            ),
            "constrained_evaluation": constrained_evaluation.model_dump(mode="json"),
            "safety_evaluation": safety_evaluation.model_dump(mode="json"),
        },
        "checks": {
            "limits_validated_by_rnd_before_service_consumption": True,
            "over_budget_combinations_absent_from_output": True,
            "over_product_count_combinations_absent_from_output": True,
            "safety_excluded_product_ingredient_absent_from_output": True,
            "safety_excluded_recommendation_fails_closed": True,
            "filter_counts_independently_recomputed": True,
            "order_or_payment_created": False,
        },
        "evidence_boundary": {
            "op065_proven_stage": "INTEGRATED",
            "op065_required_stage": "INTEGRATED",
            "op066_proven_stage": "INTEGRATED",
            "op066_required_stage": "INTEGRATED",
            "service_route_function_integration_proven": True,
            "deterministic_rnd_safety_contract_proven": True,
            "configured_prisma_query_source_bound": True,
            "actual_prisma_query_executed": False,
            "production_catalog_operation_proven": False,
            "production_data_freshness_proven": False,
            "production_deployment_proven": False,
            "order_or_payment_created": False,
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
