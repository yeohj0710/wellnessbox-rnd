from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.efficacy.service import score_candidate
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.knowledge.goal_priors import (
    load_goal_prior_registry,
    validate_goal_prior_registry,
)
from wellnessbox_rnd.knowledge.runtime_db import (
    RuntimeKnowledgeDB,
    build_runtime_knowledge_db,
    validate_runtime_knowledge_db,
)
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op041_op042_ingredient_mapping_goal_prior_smoke_v1.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify cross-repository ingredient mapping and evidence-linked goal priors."
    )
    parser.add_argument(
        "--wellnessbox-root",
        type=Path,
        default=Path(
            os.getenv(
                "WELLNESSBOX_EVIDENCE_ROOT",
                str(PROJECT_ROOT.parent / "wellnessbox"),
            )
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = _args()
    service_root = args.wellnessbox_root.resolve()
    rnd_contract = PROJECT_ROOT / "data/contracts/wellnessbox_ingredient_identifier_map_v1.json"
    service_contract = service_root / "contracts/wb-rnd/ingredient-identifier-map-v1.json"
    if rnd_contract.read_bytes() != service_contract.read_bytes():
        raise RuntimeError("ingredient_identifier_contract_mismatch")

    with tempfile.TemporaryDirectory(prefix="op041-op042-") as temporary:
        authority_output = Path(temporary) / "authority.json"
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts/run_wellnessbox_final_safety_authority_smoke.py"),
                "--wellnessbox-root",
                str(service_root),
                "--output",
                str(authority_output),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "final_safety_authority_dependency_failed:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        authority = json.loads(authority_output.read_text(encoding="utf-8"))

    observed_authority = authority["observed"]
    if observed_authority["mapping_version"] != "2026-07-16.1":
        raise RuntimeError("mapping_version_not_observed")
    if observed_authority["mapped_service_ingredient_id"] != "ING:MAGNESIUM":
        raise RuntimeError("mapped_service_identifier_not_observed")
    if observed_authority["unmapped_identifier_http_status"] != 502:
        raise RuntimeError("unmapped_identifier_not_fail_closed")

    reference_artifact = KnowledgeBaseArtifact.model_validate_json(
        (PROJECT_ROOT / "data/knowledge/reference_knowledge_base_v1.json").read_text(
            encoding="utf-8"
        )
    )
    registry = load_goal_prior_registry()
    prior_issues = validate_goal_prior_registry(
        registry,
        reference_artifact=reference_artifact,
    )
    if prior_issues:
        raise RuntimeError(f"invalid_goal_priors:{','.join(prior_issues)}")
    runtime_db = build_runtime_knowledge_db()
    repeated_runtime_db = build_runtime_knowledge_db()
    if runtime_db.model_dump(mode="json") != repeated_runtime_db.model_dump(mode="json"):
        raise RuntimeError("fresh_runtime_db_builder_is_not_deterministic")
    runtime_issues = validate_runtime_knowledge_db(runtime_db)
    if runtime_issues:
        raise RuntimeError(f"invalid_runtime_db:{','.join(runtime_issues)}")
    stored_runtime_db = RuntimeKnowledgeDB.model_validate_json(
        (PROJECT_ROOT / "data/knowledge/runtime_knowledge_db_v1.json").read_text(encoding="utf-8")
    )
    if stored_runtime_db.model_dump(mode="json") != runtime_db.model_dump(mode="json"):
        raise RuntimeError("stored_runtime_db_does_not_match_fresh_builder")

    intake = normalize_request(
        RecommendationRequest(
            user_profile=UserProfile(
                age=41,
                biological_sex=BiologicalSex.MALE,
                pregnant=False,
            ),
            goals=[RecommendationGoal.HEART_HEALTH],
        )
    )
    catalog = get_catalog_index()
    omega3_score = score_candidate(catalog["omega3"], intake, safety_review=False)
    coq10_score = score_candidate(catalog["coq10"], intake, safety_review=False)
    if omega3_score.goal_alignment != 35.0 or coq10_score.goal_alignment != 35.0:
        raise RuntimeError("goal_prior_score_not_consumed")

    report = {
        "schema_version": "op041_op042_ingredient_mapping_goal_prior_smoke_v1",
        "requirement_stages": {
            "OP-041": "INTEGRATED",
            "OP-042": "IMPLEMENTED",
        },
        "checks": [
            "cross_repository_mapping_contract_byte_identity",
            "actual_api_tips_mapped_identifier_enrichment",
            "actual_api_tips_unmapped_identifier_fail_closed",
            "all_recommendation_goals_have_evidence_linked_priors",
            "runtime_goal_prior_validation",
            "fresh_runtime_db_builder_is_deterministic",
            "stored_runtime_db_matches_fresh_builder",
            "candidate_scorer_consumes_registered_priors",
        ],
        "mapping": {
            "version": observed_authority["mapping_version"],
            "mapped_service_ingredient_id": observed_authority["mapped_service_ingredient_id"],
            "unmapped_identifier_http_status": observed_authority[
                "unmapped_identifier_http_status"
            ],
            "rnd_contract_sha256": _sha256(rnd_contract),
            "service_contract_sha256": _sha256(service_contract),
        },
        "goal_priors": {
            "version": registry.prior_version,
            "record_count": len(registry.records),
            "covered_goals": sorted({record.goal_key.value for record in registry.records}),
            "reference_ids": sorted(
                {
                    reference_id
                    for record in registry.records
                    for reference_id in record.reference_ids
                }
            ),
            "omega3_heart_goal_alignment": omega3_score.goal_alignment,
            "coq10_heart_goal_alignment": coq10_score.goal_alignment,
        },
        "source_identity": authority["source_identity"],
        "production_operation_proven": False,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
