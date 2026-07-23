import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.interim.knowledge_lineage import KnowledgeLineageRegistry
from wellnessbox_rnd.interim.store import SCHEMA_VERSION, InterimStore

ROOT = Path(__file__).parents[1]
LINEAGE_EVIDENCE_PATH = (
    ROOT / "data/original_plan/evidence/op023_op024_knowledge_lineage_smoke_v1.json"
)


def test_canonical_knowledge_lineage_evidence_matches_current_sources() -> None:
    evidence = json.loads(LINEAGE_EVIDENCE_PATH.read_text(encoding="utf-8"))
    artifact = KnowledgeBaseArtifact.model_validate_json(
        (ROOT / "data/knowledge/reference_knowledge_base_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["database_schema_version"] == SCHEMA_VERSION
    assert evidence["source_count"] == len(artifact.references)
    assert evidence["passage_count"] == len(artifact.parsed_claims)
    assert evidence["claim_count"] == len(artifact.parsed_claims)
    assert evidence["rule_count"] == len(artifact.rule_candidates)
    assert evidence["claim_rule_link_count"] == len(artifact.rule_candidates)
    assert evidence["checks"]["database_schema_version_matches_current"] is True
    assert evidence["checks"]["canonical_artifact_counts_match"] is True


def test_reference_artifact_sync_persists_complete_claim_rule_chain(tmp_path) -> None:
    store = InterimStore(tmp_path / "knowledge-lineage.sqlite3")
    store.migrate()
    registry = KnowledgeLineageRegistry(store)

    first = registry.sync_reference_artifact()
    second = registry.sync_reference_artifact()

    assert first == second
    assert first.source_count == 19
    assert first.passage_count == 24
    assert first.claim_count == 24
    assert first.rule_count == 5
    assert first.claim_rule_link_count == 5
    row = store.rows(
        """
        select src.source_id, src.source_tier, src.canonical_uri, src.license_status,
               src.effective_at, src.retired_at, src.metadata_json,
               ep.page_or_section, ep.line_start, ep.line_end,
               ep.metadata_json as passage_metadata_json,
               kc.claim_id, kr.rule_id
        from claim_rule_links link
        join knowledge_claims kc on kc.claim_id=link.claim_id
        join knowledge_rules kr on kr.rule_id=link.rule_id
        join evidence_passages ep on ep.evidence_id=kc.evidence_id
        join source_registry src on src.source_id=ep.source_id
        where kr.rule_id='KB-SAFETY-ANTICOAG-001'
        """
    )[0]
    assert row["source_id"] == "REF-KNOWLEDGE-ANTICOAG-001"
    assert row["source_tier"] == "interaction_reference"
    assert row["canonical_uri"] == (
        "data/raw_references/supplement_warfarin_interaction.md"
    )
    assert row["license_status"] == "APPROVED_INTERNAL"
    assert row["effective_at"] == "2026-03-10T00:00:00Z"
    assert row["retired_at"] is None
    assert "content_checksum" in row["metadata_json"]
    assert (
        "data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md"
        in row["metadata_json"]
    )
    assert "CLM-KNOWLEDGE-ANTICOAG-001" in row["passage_metadata_json"]
    assert row["page_or_section"] == "glucosamine chondroitin and anticoagulants"
    assert (row["line_start"], row["line_end"]) == (13, 33)
    assert row["claim_id"] == "CLM-KNOWLEDGE-ANTICOAG-001"
    assert row["rule_id"] == "KB-SAFETY-ANTICOAG-001"


def test_changed_non_blocking_source_quarantines_linked_rules(tmp_path) -> None:
    store = InterimStore(tmp_path / "knowledge-quarantine.sqlite3")
    store.migrate()
    registry = KnowledgeLineageRegistry(store)
    registry.sync_reference_artifact()
    with store.transaction() as connection:
        connection.execute(
            "update source_registry set checksum='unexpected-change' "
            "where source_id='REF-MC-ACTION-001'"
        )

    registry.sync_reference_artifact()

    source_metadata = store.scalar(
        "select metadata_json from source_registry "
        "where source_id='REF-MC-ACTION-001'"
    )
    rule_statuses = {
        row[0]
        for row in store.rows(
            "select status from knowledge_rules where rule_id in (?, ?)",
            ("KB-ACTION-001", "KB-ACTION-002"),
        )
    }
    assert "content_changed_requires_review" in source_metadata
    assert rule_statuses == {"QUARANTINED"}


def _warfarin_glucosamine_payload(*, allow_storage: bool = True) -> dict[str, object]:
    return {
        "request_id": f"knowledge-lineage-{int(allow_storage)}",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": "usr_abcdef0123456789abcdef0123456789",
            "profile": {
                "age": 58,
                "sex": "male",
                "goals": ["heart_health"],
            },
        },
        "user_profile": {
            "age": 58,
            "biological_sex": "male",
            "pregnant": False,
        },
        "goals": ["heart_health"],
        "symptoms": ["low_activity_tolerance"],
        "conditions": [],
        "medications": [{"name": "warfarin", "dose": "5mg"}],
        "current_supplements": [{"name": "glucosamine"}],
        "lifestyle": {
            "sleep_hours": 7.0,
            "stress_level": 2,
            "activity_level": "lightly_active",
        },
        "input_availability": {
            "survey": True,
            "nhis": False,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "data_source_consents": {
            source: {
                "use_for_recommendation": source == "survey",
                "allow_persistent_storage": allow_storage if source == "survey" else False,
            }
            for source in ("survey", "nhis", "wearable", "cgm", "genetic")
        },
    }


def test_actual_recommendation_route_persists_rule_to_result_lineage(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "actual-route.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)

    recommendation = client.post(
        "/v1/recommend",
        json=_warfarin_glucosamine_payload(),
    )
    execution_id = recommendation.json()["execution_id"]
    trace = client.get(
        f"/v1/interim/executions/{execution_id}",
        headers={"x-wb-rnd-token": "test-token"},
    )

    assert recommendation.status_code == 200
    assert recommendation.json()["status"] == "blocked"
    assert trace.status_code == 200
    lineage = trace.json()["knowledge_lineage"]
    assert {item["output_type"] for item in lineage} == {
        "safety_rule",
        "recommendation_decision",
    }
    assert {item["execution_id"] for item in lineage} == {execution_id}
    assert {item["rule_id"] for item in lineage} == {"KB-SAFETY-ANTICOAG-001"}
    assert {item["claim_id"] for item in lineage} == {
        "CLM-KNOWLEDGE-ANTICOAG-001"
    }
    assert {item["source_id"] for item in lineage} == {
        "REF-KNOWLEDGE-ANTICOAG-001"
    }
    assert {item["source_uri"] for item in lineage} == {
        "data/raw_references/supplement_warfarin_interaction.md"
    }
    assert {item["upstream_reference_uri"] for item in lineage} == {
        "data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md"
    }
    assert {item["license_status"] for item in lineage} == {"APPROVED_INTERNAL"}
    assert {item["source_effective_at"] for item in lineage} == {
        "2026-03-10T00:00:00Z"
    }
    assert {item["source_retired_at"] for item in lineage} == {None}
    assert {(item["line_start"], item["line_end"]) for item in lineage} == {
        (13, 33)
    }


def test_actual_route_skips_result_lineage_when_storage_consent_is_denied(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "metadata-only.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)

    recommendation = client.post(
        "/v1/recommend",
        json=_warfarin_glucosamine_payload(allow_storage=False),
    )
    execution_id = recommendation.json()["execution_id"]
    trace = client.get(
        f"/v1/interim/executions/{execution_id}",
        headers={"x-wb-rnd-token": "test-token"},
    )

    assert recommendation.status_code == 200
    assert trace.status_code == 200
    assert trace.json()["knowledge_lineage"] == []
    assert InterimStore(database).scalar(
        "select count(*) from execution_knowledge_lineage"
    ) == 0
