from pathlib import Path

from wellnessbox_rnd.ingestion.reference_ingestion import (
    ingest_reference_directory,
    parse_reference_markdown,
    summarize_ingestion,
    validate_knowledge_artifact,
)


def test_parse_reference_markdown_extracts_metadata_and_claims() -> None:
    document = parse_reference_markdown(
        Path("data/raw_references/master_context_citation_structure.md")
    )

    assert document.metadata.reference_id == "REF-MC-CITATION-001"
    assert [claim.claim_id for claim in document.claims] == [
        "CLM-MC-CITATION-001",
        "CLM-MC-CITATION-002",
    ]
    assert document.claims[0].citation_span.excerpt.startswith(
        "This sample reference normalizes citation requirements"
    )


def test_ingest_reference_directory_builds_rule_and_evidence_artifacts() -> None:
    artifact = ingest_reference_directory("data/raw_references")

    assert validate_knowledge_artifact(artifact) == []
    assert len(artifact.references) == 3
    assert len(artifact.parsed_claims) == 5
    assert any(rule.rule_id == "KB-SAFETY-ANTICOAG-001" for rule in artifact.rule_candidates)
    assert any(
        evidence.ingredient_key == "glucosamine"
        and evidence.domain_key == "drug_interaction"
        and "warfarin" in evidence.medication_keys
        for evidence in artifact.ingredient_domain_evidence
    )


def test_summarize_ingestion_reports_expected_counts() -> None:
    artifact = ingest_reference_directory("data/raw_references")

    summary = summarize_ingestion(artifact)

    assert summary.reference_count == 3
    assert summary.claim_count == 5
    assert summary.rule_candidate_count == 5
    assert summary.source_type_counts == {
        "interaction_reference": 1,
        "master_context": 2,
    }
