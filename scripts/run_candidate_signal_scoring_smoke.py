from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from pydantic import ValidationError

from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.domain.intake import (
    calculate_normalized_input_sha256_v1,
    normalize_request,
)
from wellnessbox_rnd.efficacy.service import score_candidate
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.knowledge.candidate_signals import (
    load_candidate_signal_registry,
    validate_candidate_signal_registry,
)
from wellnessbox_rnd.knowledge.runtime_db import (
    RuntimeKnowledgeDB,
    build_runtime_knowledge_db,
    validate_runtime_knowledge_db,
)
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    DataSourceConsents,
    InputAvailability,
    NormalizedSensorGeneticSnapshot,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op043_op044_candidate_signal_scoring_smoke_v1.json"
)
SOURCE_PATHS = [
    "data/rules/candidate_signal_scoring_rules_v1.json",
    "src/wellnessbox_rnd/knowledge/candidate_signals.py",
    "src/wellnessbox_rnd/knowledge/runtime_db.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
    "src/wellnessbox_rnd/schemas/recommendation_contracts.py",
    "src/wellnessbox_rnd/domain/intake.py",
    "src/wellnessbox_rnd/domain/sensor_parser.py",
    "src/wellnessbox_rnd/efficacy/service.py",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify evidence-linked candidate signals and numeric observations."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _request(
    goals: list[RecommendationGoal],
    **updates: object,
) -> RecommendationRequest:
    return RecommendationRequest(
        user_profile=UserProfile(
            age=41,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=False,
        ),
        goals=goals,
        **updates,
    )


def _score(ingredient_key: str, request: RecommendationRequest):
    return score_candidate(
        get_catalog_index()[ingredient_key],
        normalize_request(request),
        safety_review=False,
    )


def _consents(*sources: str) -> DataSourceConsents:
    return DataSourceConsents.model_validate(
        {
            "survey": {"use_for_recommendation": True},
            **{
                source: {"use_for_recommendation": True}
                for source in sources
            },
        }
    )


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for relative_path in SOURCE_PATHS:
        path = PROJECT_ROOT / relative_path
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def main() -> None:
    args = _args()
    artifact = KnowledgeBaseArtifact.model_validate_json(
        (PROJECT_ROOT / "data/knowledge/reference_knowledge_base_v1.json").read_text(
            encoding="utf-8"
        )
    )
    registry = load_candidate_signal_registry()
    registry_issues = validate_candidate_signal_registry(
        registry,
        reference_artifact=artifact,
    )
    if registry_issues:
        raise RuntimeError(f"candidate_signal_registry_invalid:{registry_issues}")
    runtime_db = build_runtime_knowledge_db()
    repeated_runtime_db = build_runtime_knowledge_db()
    stored_runtime_db = RuntimeKnowledgeDB.model_validate_json(
        (PROJECT_ROOT / "data/knowledge/runtime_knowledge_db_v1.json").read_text(
            encoding="utf-8"
        )
    )
    if validate_runtime_knowledge_db(runtime_db):
        raise RuntimeError("runtime_db_invalid")
    runtime_payload = runtime_db.model_dump(mode="json")
    if repeated_runtime_db.model_dump(mode="json") != runtime_payload:
        raise RuntimeError("runtime_builder_nondeterministic")
    if stored_runtime_db.model_dump(mode="json") != runtime_payload:
        raise RuntimeError("stored_runtime_db_stale")

    symptom_lifestyle = _score(
        "soluble_fiber",
        _request(
            [RecommendationGoal.BLOOD_GLUCOSE],
            symptoms=["post_meal_spike_concern"],
            lifestyle={"activity_level": "sedentary"},
        ),
    )
    laboratory = _score(
        "soluble_fiber",
        _request(
            [RecommendationGoal.BLOOD_GLUCOSE],
            laboratory_observations=[
                {
                    "code": "hba1c",
                    "value": 6.1,
                    "unit": "%",
                    "reference_range": {"low": 4.0, "high": 5.6},
                    "measured_at": "2026-07-16T00:00:00Z",
                }
            ],
        ),
    )
    dietary = _score(
        "vitamin_b_complex",
        _request(
            [RecommendationGoal.ENERGY_SUPPORT],
            dietary_patterns=["vegan"],
        ),
    )
    wearable_request = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        input_availability=InputAvailability(wearable=True),
        data_source_consents=_consents("wearable"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=5.5,
        ),
    )
    wearable = _score("magnesium_glycinate", wearable_request)
    cgm_request = _request(
        [RecommendationGoal.BLOOD_GLUCOSE],
        conditions=["type 2 diabetes"],
        input_availability=InputAvailability(cgm=True),
        data_source_consents=_consents("cgm"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            cgm_available=True,
            mean_glucose_mg_dl=148.0,
            time_in_range_pct=55.0,
            time_in_range_low_mg_dl=70.0,
            time_in_range_high_mg_dl=180.0,
        ),
    )
    cgm = _score("soluble_fiber", cgm_request)
    wrong_range_request = cgm_request.model_copy(
        update={
            "sensor_genetic_snapshot": cgm_request.sensor_genetic_snapshot.model_copy(
                update={
                    "time_in_range_low_mg_dl": 80.0,
                    "time_in_range_high_mg_dl": 140.0,
                }
            )
        }
    )
    pregnant_cgm_request = cgm_request.model_copy(
        update={
            "user_profile": cgm_request.user_profile.model_copy(
                update={"pregnant": True}
            )
        }
    )
    wrong_range_cgm = _score("soluble_fiber", wrong_range_request)
    pregnant_cgm = _score("soluble_fiber", pregnant_cgm_request)
    genetic = _score(
        "omega3",
        _request(
            [RecommendationGoal.HEART_HEALTH],
            input_availability=InputAvailability(genetic=True),
            data_source_consents=_consents("genetic"),
            sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
                genetic_available=True,
                genetic_tags=["lpl_triglyceride_risk"],
            ),
        ),
    )

    denied_consents = DataSourceConsents.model_validate(
        {
            "survey": {"use_for_recommendation": True},
            "wearable": {"use_for_recommendation": False},
        }
    )
    denied_low = wearable_request.model_copy(
        update={"data_source_consents": denied_consents}
    )
    denied_high = denied_low.model_copy(
        update={
            "sensor_genetic_snapshot": NormalizedSensorGeneticSnapshot(
                wearable_available=True,
                sleep_hours=8.0,
            )
        }
    )
    denied_low_intake = normalize_request(denied_low)
    denied_high_intake = normalize_request(denied_high)
    if calculate_normalized_input_sha256_v1(
        denied_low_intake
    ) != calculate_normalized_input_sha256_v1(denied_high_intake):
        raise RuntimeError("denied_sensor_value_changed_normalized_hash")
    denied_score = score_candidate(
        get_catalog_index()["magnesium_glycinate"],
        denied_low_intake,
        safety_review=False,
    )
    explicit_sensor_consent_required = False
    try:
        _request(
            [RecommendationGoal.SLEEP_SUPPORT],
            input_availability=InputAvailability(wearable=True),
            sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
                wearable_available=True,
                sleep_hours=5.5,
            ),
        )
    except ValidationError:
        explicit_sensor_consent_required = True

    cases = {
        "symptom_lifestyle": {
            "symptom_alignment": symptom_lifestyle.symptom_alignment,
            "lifestyle_alignment": symptom_lifestyle.lifestyle_alignment,
        },
        "laboratory": {
            "laboratory_alignment": laboratory.laboratory_alignment,
            "signal": next(
                signal.model_dump(mode="json")
                for signal in laboratory.applied_signals
                if signal.source == "laboratory"
            ),
        },
        "dietary_pattern": {
            "dietary_alignment": dietary.dietary_alignment,
            "signal": next(
                signal.model_dump(mode="json")
                for signal in dietary.applied_signals
                if signal.source == "dietary_pattern"
            ),
        },
        "wearable": {
            "wearable_adjustment": wearable.wearable_adjustment,
            "signal": next(
                signal.model_dump(mode="json")
                for signal in wearable.applied_signals
                if signal.source == "wearable"
            ),
        },
        "cgm": {
            "cgm_adjustment": cgm.cgm_adjustment,
            "time_in_range_mg_dl": [70.0, 180.0],
            "wrong_range_adjustment": wrong_range_cgm.cgm_adjustment,
            "pregnant_adjustment": pregnant_cgm.cgm_adjustment,
            "signal": next(
                signal.model_dump(mode="json")
                for signal in cgm.applied_signals
                if signal.source == "cgm"
            ),
        },
        "genetic": {
            "genetic_adjustment": genetic.genetic_adjustment,
            "signal": next(
                signal.model_dump(mode="json")
                for signal in genetic.applied_signals
                if signal.source == "genetic"
            ),
        },
        "consent_denied": {
            "wearable_adjustment": denied_score.wearable_adjustment,
            "explicit_sensor_consent_required": explicit_sensor_consent_required,
            "effective_wearable": denied_low_intake.effective_input_availability.wearable,
            "normalized_value": (
                denied_low_intake.sensor_genetic_snapshot.sleep_hours
                if denied_low_intake.sensor_genetic_snapshot is not None
                else None
            ),
            "hash_stable_across_denied_values": True,
        },
    }
    expected_points = {
        "symptom": 8.0,
        "lifestyle": 6.0,
        "laboratory": 4.0,
        "dietary": 3.0,
        "wearable": 3.0,
        "cgm": 3.0,
        "cgm_wrong_range": 0.0,
        "cgm_pregnant": 0.0,
        "genetic": 4.0,
        "denied_wearable": 0.0,
    }
    observed_points = {
        "symptom": symptom_lifestyle.symptom_alignment,
        "lifestyle": symptom_lifestyle.lifestyle_alignment,
        "laboratory": laboratory.laboratory_alignment,
        "dietary": dietary.dietary_alignment,
        "wearable": wearable.wearable_adjustment,
        "cgm": cgm.cgm_adjustment,
        "cgm_wrong_range": wrong_range_cgm.cgm_adjustment,
        "cgm_pregnant": pregnant_cgm.cgm_adjustment,
        "genetic": genetic.genetic_adjustment,
        "denied_wearable": denied_score.wearable_adjustment,
    }
    if observed_points != expected_points:
        raise RuntimeError(
            f"candidate_signal_points_mismatch:{observed_points}!={expected_points}"
        )
    if not explicit_sensor_consent_required:
        raise RuntimeError("sensor_snapshot_accepted_without_explicit_consent")

    report = {
        "schema_version": "op043_op044_candidate_signal_scoring_smoke_v1",
        "requirement_stages": {"OP-043": "IMPLEMENTED", "OP-044": "IMPLEMENTED"},
        "scoring_version": registry.scoring_version,
        "score_meaning": registry.score_meaning,
        "rule_count": len(registry.all_rules()),
        "cases": cases,
        "checks": [
            "symptom_points_auditable",
            "laboratory_reference_range_status_scored",
            "lifestyle_points_auditable",
            "dietary_pattern_points_evidence_linked",
            "wearable_value_converted_to_bounded_points",
            "cgm_value_requires_standard_70_180_range_and_nonpregnant_diabetes_context",
            "genetic_tag_converted_to_bounded_points",
            "denied_sensor_values_excluded_from_score_and_hash",
            "sensor_snapshot_requires_explicit_consent_contract",
            "stored_runtime_matches_deterministic_fresh_builder",
        ],
        "source_identity": {
            "commit": _git_commit(),
            "source_sha256": _source_sha256(),
        },
        "production_operation_proven": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
