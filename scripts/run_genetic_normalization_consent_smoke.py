from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.domain.sensor_parser import normalize_sensor_genetic_payloads
from wellnessbox_rnd.efficacy.service import score_candidate
from wellnessbox_rnd.interim.data_lake import ExecutionLedger
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data/original_plan/op093_op094_genetic_normalization_consent_cases_v1.json"
SOURCE_PATHS = (
    ROOT / "scripts/run_genetic_normalization_consent_smoke.py",
    DATASET_PATH,
    ROOT / "src/wellnessbox_rnd/domain/sensor_parser.py",
    ROOT / "src/wellnessbox_rnd/schemas/recommendation.py",
    ROOT / "src/wellnessbox_rnd/domain/intake.py",
    ROOT / "src/wellnessbox_rnd/interim/data_lake.py",
    ROOT / "src/wellnessbox_rnd/efficacy/service.py",
    ROOT / "data/rules/candidate_signal_scoring_rules_v1.json",
)


def _git_blob_sha256(path: Path) -> str:
    content = subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    return hashlib.sha256(content).hexdigest()


def _source_commit() -> str:
    paths = [path.relative_to(ROOT).as_posix() for path in SOURCE_PATHS]
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *paths], cwd=ROOT, text=True
    ).strip()


def _request(case: dict[str, Any]) -> RecommendationRequest:
    return RecommendationRequest.model_validate(
        {
            "request_id": f"op093-op094-{case['case_id']}",
            "user_profile": {"age": 42, "biological_sex": "female", "pregnant": False},
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "allergies": [],
            "risk_flags": [],
            "medications": [],
            "current_supplements": [],
            "dietary_patterns": [],
            "laboratory_observations": [],
            "lifestyle": {
                "sleep_hours": 7,
                "stress_level": 2,
                "activity_level": "moderately_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "data_source_consents": {
                "survey": {"use_for_recommendation": True, "allow_persistent_storage": True},
                "nhis": {"use_for_recommendation": False, "allow_persistent_storage": False},
                "wearable": {"use_for_recommendation": False, "allow_persistent_storage": False},
                "cgm": {"use_for_recommendation": False, "allow_persistent_storage": False},
                "genetic": {
                    "use_for_recommendation": case["use_for_recommendation"],
                    "allow_persistent_storage": case["allow_persistent_storage"],
                },
            },
            "sensor_genetic_snapshot": {
                "genetic_available": True,
                "genetic_tags": ["lpl_triglyceride_risk"],
                "genetic_variants": [
                    {
                        "gene_symbol": "LPL",
                        "variant_id": "rs328",
                        "genotype": "C/G",
                        "interpretation": "increased_risk",
                        "interpretation_criterion": "panel-v1",
                        "testing_laboratory": "Example Genomics",
                        "tested_on": "2026-06-30",
                    }
                ],
            },
            "preferences": {"budget_level": "medium", "max_products": 2, "avoid_ingredients": []},
        }
    )


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = str(case["kind"])
    if kind.startswith("normalization"):
        try:
            snapshot = normalize_sensor_genetic_payloads(genetic_payload=case["payload"])
        except ValueError as error:
            if kind != "normalization_failure" or str(error) != case["expected_error"]:
                raise
            return {"case_id": case["case_id"], "result": "PASS", "error": str(error)}
        if kind != "normalization_success":
            raise AssertionError(f"expected_failure_not_raised:{case['case_id']}")
        variants = [item.model_dump(mode="json") for item in snapshot.genetic_variants]
        if "expected" in case and variants != [case["expected"]]:
            raise AssertionError(f"unexpected_variant:{case['case_id']}")
        if (
            "expected_gene_order" in case
            and [item["gene_symbol"] for item in variants] != case["expected_gene_order"]
        ):
            raise AssertionError(f"unexpected_variant_order:{case['case_id']}")
        if "expected_tags" in case and snapshot.genetic_tags != case["expected_tags"]:
            raise AssertionError(f"unexpected_tags:{case['case_id']}")
        return {
            "case_id": case["case_id"],
            "result": "PASS",
            "genetic_tags": snapshot.genetic_tags,
            "genetic_variants": variants,
        }

    request = _request(case)
    intake = normalize_request(request)
    score = score_candidate(get_catalog_index()["omega3"], intake, safety_review=False)
    if score.genetic_adjustment != case["expected_genetic_adjustment"]:
        raise AssertionError(f"unexpected_genetic_adjustment:{case['case_id']}")
    with tempfile.TemporaryDirectory() as directory:
        store = InterimStore(Path(directory) / "evidence.sqlite3")
        store.migrate()
        trace = ExecutionLedger(store).record_recommendation(
            request=request, response=recommend(request)
        )
        stored = None
        if trace.profile_snapshot_id is not None:
            stored = json.loads(
                store.rows(
                    "select payload_json from profile_snapshots where profile_snapshot_id=?",
                    (trace.profile_snapshot_id,),
                )[0][0]
            )
    genetic_stored = bool(stored and "genetic" in stored["persisted_sources"])
    if genetic_stored is not case["expected_stored"]:
        raise AssertionError(f"unexpected_genetic_storage:{case['case_id']}")
    return {
        "case_id": case["case_id"],
        "result": "PASS",
        "genetic_adjustment": score.genetic_adjustment,
        "genetic_stored": genetic_stored,
    }


def main() -> int:
    output = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/original_plan/evidence/op093_op094_genetic_normalization_consent_smoke_v1.json"
    )
    output = output if output.is_absolute() else ROOT / output
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = [_run_case(case) for case in dataset["cases"]]
    if len(cases) != dataset["case_count"]:
        raise AssertionError("dataset_case_count_mismatch")
    report = {
        "schema_version": "op093_op094_genetic_normalization_consent_smoke_v1",
        "requirements": ["OP-093", "OP-094"],
        "result": "PASS",
        "dataset": {
            "path": DATASET_PATH.relative_to(ROOT).as_posix(),
            "schema_version": dataset["schema_version"],
            "case_count": dataset["case_count"],
            "sha256": _git_blob_sha256(DATASET_PATH),
        },
        "checks": {
            "cases": cases,
            "variant_provenance_preserved": True,
            "unsupported_or_incomplete_variants_fail_closed": True,
            "recommendation_consent_gate_observed": True,
            "persistent_storage_consent_gate_observed": True,
            "production_genetic_provider_observed": False,
            "production_operation_observed": False,
        },
        "source_identity": {
            "commit": _source_commit(),
            "files": {
                path.relative_to(ROOT).as_posix(): _git_blob_sha256(path) for path in SOURCE_PATHS
            },
        },
        "stage_boundary": {
            "OP-093": (
                "Versioned local genetic-result normalization is implemented; "
                "no laboratory or provider integration is claimed."
            ),
            "OP-094": (
                "Recommendation and local persistence consent gates are implemented; "
                "no production operation is claimed."
            ),
        },
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
