from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.evals.recommendation_replay_compare import (
    RecommendationReplayCaseComparison,
    RecommendationReplayComparisonReport,
    build_recommendation_replay_comparison,
)
from wellnessbox_rnd.models import (
    load_efficacy_model_artifact,
    validate_efficacy_model_artifact_for_runtime,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(RND_ROOT.parent / "wellnessbox"))
).resolve()
DATASET_PATH = RND_ROOT / "data/frozen_eval/frozen_eval_v1.jsonl"
ARTIFACT_PATH = (
    RND_ROOT / "data/original_plan/fixtures/op049_learned_replay_artifact_v1.json"
)


@pytest.fixture(scope="module")
def replay_report() -> RecommendationReplayComparisonReport:
    return build_recommendation_replay_comparison(
        dataset_path=DATASET_PATH,
        learned_artifact_path=ARTIFACT_PATH,
    )


def test_replay_fixture_is_valid_but_explicitly_replay_only() -> None:
    artifact = load_efficacy_model_artifact(ARTIFACT_PATH)

    assert validate_efficacy_model_artifact_for_runtime(artifact) == []
    assert artifact.cohort_version == "original_plan_op049_replay_fixture_v1"


def test_paired_frozen_replay_compares_every_case_and_preserves_safety(
    replay_report: RecommendationReplayComparisonReport,
) -> None:
    assert replay_report.case_count == 256
    assert replay_report.learned_applied_case_count == 12
    assert replay_report.deterministic_fallback_case_count == 244
    assert replay_report.selection_changed_case_count == 4
    assert replay_report.rank_or_score_changed_case_count == 5
    assert replay_report.response_status_changed_case_count == 0
    assert replay_report.next_action_changed_case_count == 0
    assert replay_report.safety_changed_case_count == 0
    assert any(
        item.selection_changed and item.learned_applied
        for item in replay_report.cases
    )
    assert all(
        item.learned_applied or not item.selection_changed
        for item in replay_report.cases
    )


def test_replay_comparison_schemas_reject_forged_deltas(
    replay_report: RecommendationReplayComparisonReport,
) -> None:
    payload = replay_report.model_dump(mode="json")
    payload["selection_changed_case_count"] += 1
    with pytest.raises(ValidationError, match="selection_changed_case_count mismatch"):
        RecommendationReplayComparisonReport.model_validate(payload)

    unchanged = next(item for item in replay_report.cases if not item.learned_applied)
    case_payload = unchanged.model_dump(mode="json")
    case_payload["selection_changed"] = True
    with pytest.raises(ValidationError, match="selection_changed does not match"):
        RecommendationReplayCaseComparison.model_validate(case_payload)


def test_service_product_match_contract_covers_mapped_ingredient_contract() -> None:
    rnd_mapping = json.loads(
        (RND_ROOT / "data/contracts/wellnessbox_ingredient_identifier_map_v1.json").read_text(
            encoding="utf-8"
        )
    )
    service_mapping = json.loads(
        (SERVICE_ROOT / "contracts/wb-rnd/ingredient-identifier-map-v1.json").read_text(
            encoding="utf-8"
        )
    )
    product_mapping = json.loads(
        (SERVICE_ROOT / "contracts/wb-rnd/product-candidate-match-v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert rnd_mapping == service_mapping
    mapped_service_ids = {
        item["service_ingredient_id"] for item in service_mapping["mappings"]
    }
    product_service_ids = {
        item["service_ingredient_id"] for item in product_mapping["mappings"]
    }
    assert product_mapping["schema_version"] == "wb_rnd_product_candidate_match_v1"
    assert product_service_ids == mapped_service_ids
    assert all(item["match_terms"] for item in product_mapping["mappings"])
