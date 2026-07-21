from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.optimizer.product_combinations import (
    ProductCombinationFilterPolicyV1,
    ProductCombinationV1,
    evaluate_product_combination_ranking_v1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")
).resolve()
DEFAULT_OUTPUT = RND_ROOT / (
    "data/original_plan/evidence/"
    "op067_op068_product_combination_top_k_smoke_v1.json"
)
RND_SOURCE_PATHS = [
    "scripts/run_product_combination_top_k_reproducibility_smoke.py",
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


def _service_report(output_path: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment.update(
        {
            "WB_RND_PRODUCT_SMOKE_OUTPUT": str(output_path),
            "WB_RND_INCLUDE_PRODUCT_COMBINATION_EVIDENCE": "1",
            "WB_RND_INCLUDE_PRODUCT_COMBINATION_FILTER_EVIDENCE": "1",
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


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op067-op068-") as directory:
        service_report = _service_report(Path(directory) / "service-report.json")
    if (
        service_report["schema_version"]
        != "op067_op068_service_product_combination_ranking_contract_v1"
    ):
        raise ValueError("unexpected service product-combination ranking report")
    observed = service_report["observed"]
    combinations = tuple(
        sorted(
            (
                ProductCombinationV1.model_validate(item)
                for item in observed["verified_filter_input_combinations"]
            ),
            key=lambda item: item.combination_id,
        )
    )
    policy = ProductCombinationFilterPolicyV1.model_validate(
        {
            key: value
            for key, value in observed["unfiltered_policy"].items()
            if key != "excluded_ingredient_keys"
        }
    )
    replay = observed["replay_identity"]
    evaluation = evaluate_product_combination_ranking_v1(
        combinations,
        policy,
        max_ranked_combinations=observed["max_ranked_product_combinations"],
        input_sha256=replay["input_sha256"],
        catalog_version=replay["catalog_version"],
    )
    assert [item.model_dump(mode="json") for item in evaluation.top_k] == observed[
        "top_k"
    ]
    assert [
        item.model_dump(mode="json") for item in evaluation.non_selection
    ] == observed["non_selection"]
    assert evaluation.replay_identity.model_dump(mode="json") == replay
    assert observed["repeated_top_k"] == observed["top_k"]
    assert observed["repeated_non_selection"] == observed["non_selection"]
    assert observed["repeated_replay_identity"] == replay
    assert observed["reordered_catalog_top_k"] == observed["top_k"]
    assert observed["reordered_catalog_non_selection"] == observed["non_selection"]
    assert observed["reordered_catalog_replay_identity"] == replay

    return {
        "schema_version": "op067_op068_product_combination_top_k_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(
                SERVICE_ROOT, SERVICE_SOURCE_PATHS
            ),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "evaluated_combination_count": len(combinations),
            "top_k_count": len(evaluation.top_k),
            "non_selected_combination_count": len(evaluation.non_selection),
            "ranking": evaluation.model_dump(mode="json"),
        },
        "checks": {
            "top_k_independently_recomputed": True,
            "every_evaluated_non_selected_combination_has_reason": True,
            "same_input_same_catalog_version_same_result": True,
            "catalog_row_order_does_not_change_version_or_result": True,
            "result_identity_independently_recomputed": True,
            "order_or_payment_created": False,
        },
        "evidence_boundary": {
            "op067_proven_stage": "INTEGRATED",
            "op067_required_stage": "INTEGRATED",
            "op068_proven_stage": "INTEGRATED",
            "op068_required_stage": "INTEGRATED",
            "service_route_function_integration_proven": True,
            "actual_ready_rnd_http_path_proven": False,
            "actual_prisma_query_executed": False,
            "production_catalog_freshness_proven": False,
            "production_deployment_proven": False,
            "production_operation_proven": False,
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
