from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from run_wellnessbox_final_safety_authority_smoke import (
    run_smoke as run_authority_smoke,
)

from wellnessbox_rnd.evals.recommendation_replay_compare import (
    build_recommendation_replay_comparison,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op049_op050_replay_product_candidates_smoke_v1.json"
)
RND_SOURCE_PATHS = [
    "data/catalog/ingredients.json",
    "data/frozen_eval/frozen_eval_v1.jsonl",
    "data/knowledge/goal_ingredient_priors_v1.json",
    "data/original_plan/fixtures/op049_learned_replay_artifact_v1.json",
    "data/rules/candidate_signal_scoring_rules_v1.json",
    "data/rules/safety_rules.json",
    "scripts/run_learned_replay_product_candidates_smoke.py",
    "src/wellnessbox_rnd/domain/loaders.py",
    "src/wellnessbox_rnd/efficacy/service.py",
    "src/wellnessbox_rnd/evals/runner.py",
    "src/wellnessbox_rnd/evals/recommendation_replay_compare.py",
    "src/wellnessbox_rnd/knowledge/candidate_signals.py",
    "src/wellnessbox_rnd/knowledge/goal_priors.py",
    "src/wellnessbox_rnd/models/efficacy_model_v0.py",
    "src/wellnessbox_rnd/optimizer/service.py",
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
    "src/wellnessbox_rnd/safety/service.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/route.ts",
    "contracts/wb-rnd/ingredient-identifier-map-v1.json",
    "contracts/wb-rnd/product-candidate-catalog-snapshot-v1.json",
    "contracts/wb-rnd/product-candidate-match-v1.json",
    "lib/server/wb-rnd-ingredient-map.ts",
    "lib/server/wb-rnd-interim-route.ts",
    "lib/server/wb-rnd-interim-safety-authority.ts",
    "lib/server/wb-rnd-product-candidates.ts",
    "lib/server/wb-rnd-tips-route-test-hook.ts",
    "lib/product/product.catalog.ts",
    "lib/product/product.shared.ts",
    "package.json",
    "scripts/qa/check-rnd-final-safety-authority.cts",
    "scripts/qa/check-rnd-product-candidates.cts",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare learned/baseline replay and verify service product candidates."
    )
    parser.add_argument(
        "--wellnessbox-root",
        type=Path,
        default=Path(
            os.getenv("WELLNESSBOX_EVIDENCE_ROOT", str(PROJECT_ROOT.parent / "wellnessbox"))
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _git_source_commit(root: Path, paths: list[str]) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _source_sha256(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(paths):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _run_service_product_qa(
    *,
    wellnessbox_root: Path,
    output_path: Path,
) -> dict[str, object]:
    environment = os.environ.copy()
    environment.update(
        {
            "NODE_ENV": "test",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_PRODUCT_SMOKE_OUTPUT": str(output_path),
        }
    )
    result = subprocess.run(
        [_npm_command(), "run", "qa:rnd:product-candidates"],
        cwd=wellnessbox_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "WellnessBox product-candidate QA failed:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return json.loads(output_path.read_text(encoding="utf-8"))


def main() -> int:
    args = _args()
    wellnessbox_root = args.wellnessbox_root.resolve()
    if not (wellnessbox_root / "package.json").is_file():
        raise FileNotFoundError(f"WellnessBox root is invalid: {wellnessbox_root}")

    replay = build_recommendation_replay_comparison(
        dataset_path=PROJECT_ROOT / "data/frozen_eval/frozen_eval_v1.jsonl",
        learned_artifact_path=(
            PROJECT_ROOT
            / "data/original_plan/fixtures/op049_learned_replay_artifact_v1.json"
        ),
    )
    if replay.case_count != 256:
        raise RuntimeError("paired replay did not cover the frozen dataset")
    if replay.learned_applied_case_count == 0 or replay.selection_changed_case_count == 0:
        raise RuntimeError("paired replay did not observe a learned comparison delta")
    if (
        replay.response_status_changed_case_count
        or replay.next_action_changed_case_count
        or replay.safety_changed_case_count
    ):
        raise RuntimeError("learned replay changed a protected decision boundary")

    with tempfile.TemporaryDirectory(prefix="op049-op050-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        authority = run_authority_smoke(
            wellnessbox_root=wellnessbox_root,
            output_path=temporary_root / "authority.json",
        )
        product_conversion = _run_service_product_qa(
            wellnessbox_root=wellnessbox_root,
            output_path=temporary_root / "product-candidates.json",
        )

    if product_conversion["observed"]["mapping_coverage_count"] != 8:
        raise RuntimeError("service product conversion did not cover every mapping")
    if product_conversion["observed"]["unmatched_service_ingredient_ids"]:
        raise RuntimeError("service product conversion left mapped ingredients unmatched")

    report = {
        "schema_version": "op049_op050_replay_product_candidates_smoke_v1",
        "requirement_stages": {"OP-049": "IMPLEMENTED", "OP-050": "INTEGRATED"},
        "paired_replay": replay.model_dump(mode="json"),
        "service_product_conversion": product_conversion,
        "integration_boundary": {
            "service_route": "POST /api/tips",
            "service_product_catalog_path": (
                "existing product.catalog getProductCandidateCatalog path with "
                "in-stock PharmacyProduct predicate"
            ),
            "actual_rnd_http_process_observed": True,
            "actual_rnd_observation": authority["observed"],
            "ready_product_conversion_source": (
                "contract-valid R&D response injected through the existing "
                "test-only route dependency seam"
            ),
            "ready_two_process_product_conversion_proven": False,
            "production_operation_proven": False,
        },
        "source_identity": {
            "wellnessbox_rnd_commit": _git_source_commit(
                PROJECT_ROOT, RND_SOURCE_PATHS
            ),
            "wellnessbox_rnd_source_sha256": _source_sha256(
                PROJECT_ROOT, RND_SOURCE_PATHS
            ),
            "wellnessbox_commit": _git_source_commit(
                wellnessbox_root, SERVICE_SOURCE_PATHS
            ),
            "wellnessbox_source_sha256": _source_sha256(
                wellnessbox_root, SERVICE_SOURCE_PATHS
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
