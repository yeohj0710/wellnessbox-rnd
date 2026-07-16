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
    assert document.metadata.source_type == "master_context"
    assert document.metadata.parsed_source_uri == (
        "data/raw_references/master_context_citation_structure.md"
    )
    assert document.metadata.license_status == "APPROVED_INTERNAL"
    assert document.metadata.effective_at == "2026-03-10T00:00:00Z"
    assert document.metadata.retired_at is None
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
    assert len(artifact.references) == 19
    assert {reference.license_status for reference in artifact.references} == {
        "APPROVED_INTERNAL",
        "OPEN_ACCESS_RESEARCH",
        "PUBLIC_GOVERNMENT",
    }
    assert all(reference.effective_at for reference in artifact.references)
    assert len(artifact.parsed_claims) == 24
    nih_reference = next(
        reference
        for reference in artifact.references
        if reference.reference_id == "REF-NIH-ODS-OMEGA3-001"
    )
    nih_claim = next(
        claim
        for claim in artifact.parsed_claims
        if claim.claim_id == "CLM-NIH-ODS-OMEGA3-WARFARIN-001"
    )
    assert nih_reference.effective_at == "2025-08-22T00:00:00Z"
    assert nih_claim.claim_text == (
        "Fish oil might prolong clotting time with warfarin, although most research "
        "found that 3–6 g/day did not significantly affect anticoagulant status; "
        "FDA-approved omega-3 pharmaceutical package inserts state that patients "
        "taking those products with anticoagulants should be monitored periodically "
        "for INR changes."
    )
    assert "FDA-approved omega-3 pharmaceutical package inserts" in (
        nih_claim.citation_span.excerpt
    )
    assert any(rule.rule_id == "KB-SAFETY-ANTICOAG-001" for rule in artifact.rule_candidates)
    assert any(
        evidence.ingredient_key == "glucosamine"
        and evidence.domain_key == "drug_interaction"
        and "warfarin" in evidence.medication_keys
        for evidence in artifact.ingredient_domain_evidence
    )
    assert any(
        evidence.ingredient_key == "omega3"
        and evidence.domain_key == "heart_health"
        and "CLM-NIH-ODS-OMEGA3-HEART-001" in evidence.claim_ids
        for evidence in artifact.ingredient_domain_evidence
    )


def test_summarize_ingestion_reports_expected_counts() -> None:
    artifact = ingest_reference_directory("data/raw_references")

    summary = summarize_ingestion(artifact)

    assert summary.reference_count == 19
    assert summary.claim_count == 24
    assert summary.rule_candidate_count == 5
    assert summary.source_type_counts == {
        "clinical_guideline": 1,
        "government_health_reference": 12,
        "interaction_reference": 1,
        "master_context": 4,
        "peer_reviewed_trial": 1,
    }
