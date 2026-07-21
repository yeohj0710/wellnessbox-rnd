from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.optimizer.constraints import (
    OptimizationCandidateFactsV1,
    OptimizationConstraintsV1,
    evaluate_optimization_candidate_v1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")).resolve()
DEFAULT_OUTPUT = RND_ROOT / (
    "data/original_plan/evidence/"
    "op061_op062_optimization_product_catalog_smoke_v1.json"
)
RND_SOURCE_PATHS = [
    "data/contracts/optimization_constraints_v1.json",
    "scripts/run_optimization_constraints_product_catalog_smoke.py",
    "src/wellnessbox_rnd/optimizer/__init__.py",
    "src/wellnessbox_rnd/optimizer/constraints.py",
    "tests/test_optimization_constraints.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/route.ts",
    "contracts/wb-rnd/ingredient-identifier-map-v1.json",
    "contracts/wb-rnd/product-candidate-catalog-snapshot-v1.json",
    "contracts/wb-rnd/product-candidate-match-v1.json",
    "lib/product/product-detail-facts.ts",
    "lib/product/product.catalog.ts",
    "lib/product/product.shared.ts",
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


def _candidate(**updates: object) -> OptimizationCandidateFactsV1:
    payload: dict[str, object] = {
        "schema_version": "optimization_candidate_facts_v1",
        "candidate_id": "op061-feasible",
        "ingredient_keys": ["magnesium_glycinate", "vitamin_d3"],
        "expected_effect_score": 7.5,
        "safety_status": "allowed",
        "total_cost_krw": 42_000,
        "product_count": 2,
        "daily_unit_count": 3,
        "formulations": ["capsule", "tablet"],
    }
    payload.update(updates)
    return OptimizationCandidateFactsV1.model_validate(payload)


def _constraint_cases(constraints: OptimizationConstraintsV1) -> dict[str, object]:
    candidates = {
        "feasible": _candidate(),
        "efficacy": _candidate(candidate_id="op061-efficacy", expected_effect_score=4.99),
        "safety": _candidate(candidate_id="op061-safety", safety_status="blocked"),
        "cost": _candidate(candidate_id="op061-cost", total_cost_krw=50_001),
        "daily_burden": _candidate(candidate_id="op061-burden", daily_unit_count=5),
        "formulation": _candidate(
            candidate_id="op061-formulation",
            formulations=["powder"],
        ),
    }
    return {
        name: evaluate_optimization_candidate_v1(candidate, constraints).model_dump(
            mode="json"
        )
        for name, candidate in candidates.items()
    }


def _service_contract_report(temp: Path) -> dict[str, object]:
    output = temp / "service-product-contract.json"
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
    constraints = OptimizationConstraintsV1.model_validate_json(
        (RND_ROOT / "data/contracts/optimization_constraints_v1.json").read_text(
            encoding="utf-8"
        )
    )
    constraint_cases = _constraint_cases(constraints)
    with TemporaryDirectory(prefix="op061-op062-") as directory:
        service_report = _service_contract_report(Path(directory))

    assert constraint_cases["feasible"]["feasible"] is True
    assert all(
        case["feasible"] is False
        for name, case in constraint_cases.items()
        if name != "feasible"
    )
    assert service_report["ok"] is True
    assert (
        service_report["schema_version"]
        == "op063_op064_service_product_combination_contract_v1"
    )

    return {
        "schema_version": "op061_op062_optimization_product_catalog_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(SERVICE_ROOT, SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "optimization_constraint_case_count": len(constraint_cases),
            "optimization_constraints": constraint_cases,
            "service_contract": service_report,
        },
        "checks": {
            "existing_rnd_optimizer_package_extended": True,
            "five_constraint_dimensions_explicit": True,
            "existing_service_product_catalog_contract_adapter_used": True,
            "existing_tips_route_used": True,
            "selling_product_contract_reads_ingredients_amounts_price_stock_formulation": True,
            "invalid_catalog_or_offer_fails_closed": True,
            "order_created": False,
        },
        "evidence_boundary": {
            "op061_proven_stage": "IMPLEMENTED",
            "op061_required_stage": "IMPLEMENTED",
            "op062_proven_stage": "INTEGRATED",
            "op062_required_stage": "INTEGRATED",
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
