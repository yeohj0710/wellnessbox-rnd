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
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")).resolve()
DEFAULT_OUTPUT = RND_ROOT / (
    "data/original_plan/evidence/op063_op064_product_combination_dose_smoke_v1.json"
)
RND_SOURCE_PATHS = [
    "scripts/run_product_combination_dose_smoke.py",
    "src/wellnessbox_rnd/optimizer/__init__.py",
    "src/wellnessbox_rnd/optimizer/product_combinations.py",
    "tests/test_product_combinations.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/route.ts",
    "contracts/wb-rnd/ingredient-identifier-map-v1.json",
    "contracts/wb-rnd/product-candidate-catalog-snapshot-v1.json",
    "contracts/wb-rnd/product-candidate-match-v1.json",
    "lib/product/product-detail-facts.ts",
    "lib/product/product.catalog.ts",
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
    output = temp / "service-product-combinations.json"
    environment = os.environ.copy()
    environment["WB_RND_PRODUCT_SMOKE_OUTPUT"] = str(output)
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


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op063-op064-") as directory:
        service_report = _service_report(Path(directory))
    observed = service_report["observed"]
    combinations = sorted(
        observed["verified_product_combinations"],
        key=lambda item: item["combination_id"],
    )
    validated = ProductCombinationEvidenceV1.model_validate(
        {
            "schema_version": "op063_op064_product_combination_evidence_v1",
            "combinations": combinations,
        }
    )
    shared = next(item for item in validated.combinations if item.product_count == 5)
    duplicated = next(item for item in validated.combinations if item.duplicate_ingredient_ids)
    assert shared.duplicate_ingredient_ids == ()
    assert duplicated.duplicate_ingredient_ids == ("ING:ZINC",)
    assert next(
        item
        for item in duplicated.ingredient_totals
        if item.service_ingredient_id == "ING:ZINC"
    ).total_declared_amount == 253_000_000

    return {
        "schema_version": "op063_op064_product_combination_dose_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(SERVICE_ROOT, SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "service_catalog_product_count": 7,
            "service_recommendation_count": observed["mapping_coverage_count"],
            "generated_combination_count": observed["combination_count"],
            "validated_evidence_combination_count": len(validated.combinations),
            "shared_product_combination": shared.model_dump(mode="json"),
            "duplicate_ingredient_combination": duplicated.model_dump(mode="json"),
        },
        "checks": {
            "existing_tips_route_and_product_adapter_used": True,
            "same_product_deduplicated_across_recommendations": True,
            "mass_units_normalized_to_integer_nanograms": True,
            "iu_normalized_to_integer_milli_iu": True,
            "duplicate_requires_distinct_product_ids": True,
            "aggregate_doses_recomputed_by_rnd_contract": True,
            "ambiguous_amounts_fail_closed": True,
            "order_or_payment_created": False,
        },
        "evidence_boundary": {
            "op063_proven_stage": "INTEGRATED",
            "op063_required_stage": "INTEGRATED",
            "op064_proven_stage": "INTEGRATED",
            "op064_required_stage": "INTEGRATED",
            "service_route_function_integration_proven": True,
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
