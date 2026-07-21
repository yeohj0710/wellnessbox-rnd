from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.chat.answering import (
    generate_bounded_template_answer,
    verify_bounded_template_answer,
)
from wellnessbox_rnd.chat.retrieval import (
    ChatQaEvalCase,
    RetrievalChunk,
    RetrievalCorpusManifest,
    evaluate_retrieval_hit_rate,
    extract_question_entities,
    retrieve_relevant_chunks,
)
from wellnessbox_rnd.knowledge.runtime_db import load_runtime_knowledge_db


def test_retrieve_relevant_chunks_hits_anticoagulant_claim() -> None:
    manifest = RetrievalCorpusManifest(
        manifest_version="test",
        chunk_count=2,
        chunks=[
            RetrievalChunk(
                chunk_id="chunk::CLM-KNOWLEDGE-ANTICOAG-001",
                reference_id="REF-KNOWLEDGE-ANTICOAG-001",
                claim_id="CLM-KNOWLEDGE-ANTICOAG-001",
                source_title="Supplement Interaction Notes",
                source_type="interaction_reference",
                page_or_section="glucosamine chondroitin and anticoagulants",
                reference_uri="data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md",
                license_status="APPROVED_INTERNAL",
                effective_at="2026-01-01T00:00:00Z",
                line_start=10,
                line_end=12,
                normalized_claim_type="drug_interaction",
                text=(
                    "Glucosamine or chondroitin used with warfarin or Coumadin can "
                    "increase anticoagulant effect and bleeding risk."
                ),
                excerpt=(
                    "Glucosamine and chondroitin should be treated as a "
                    "bleeding-risk interaction."
                ),
                keywords=["drug_interaction", "bleeding_risk", "glucosamine", "warfarin"],
                ingredient_keys=["glucosamine", "chondroitin"],
                medication_keys=["warfarin", "coumadin"],
                domain_keys=["drug_interaction", "bleeding_risk"],
            ),
            RetrievalChunk(
                chunk_id="chunk::CLM-MC-CITATION-002",
                reference_id="REF-MC-CITATION-001",
                claim_id="CLM-MC-CITATION-002",
                source_title="WellnessBox R&D Master Context",
                source_type="master_context",
                page_or_section="17.4 citation structure",
                reference_uri="docs/context/master_context.md",
                license_status="APPROVED_INTERNAL",
                effective_at="2026-01-01T00:00:00Z",
                line_start=20,
                line_end=22,
                normalized_claim_type="citation_schema",
                text=(
                    "Structured citations should include ref_id, source_title, "
                    "source_type, page_or_section, claim_text, and "
                    "normalized_claim_type."
                ),
                excerpt="The canonical citation payload needs stable structure.",
                keywords=["citation_schema", "ref_id", "source_title"],
                ingredient_keys=[],
                medication_keys=[],
                domain_keys=["citations"],
            ),
        ],
    )

    results = retrieve_relevant_chunks(
        manifest,
        query="What should counseling say about glucosamine with warfarin?",
        top_k=2,
    )

    assert results
    assert results[0].chunk_id == "chunk::CLM-KNOWLEDGE-ANTICOAG-001"


def test_evaluate_retrieval_hit_rate_reports_top_hits() -> None:
    manifest = RetrievalCorpusManifest(
        manifest_version="test",
        chunk_count=1,
        chunks=[
            RetrievalChunk(
                chunk_id="chunk::CLM-MC-CITATION-002",
                reference_id="REF-MC-CITATION-001",
                claim_id="CLM-MC-CITATION-002",
                source_title="WellnessBox R&D Master Context",
                source_type="master_context",
                page_or_section="17.4 citation structure",
                reference_uri="docs/context/master_context.md",
                license_status="APPROVED_INTERNAL",
                effective_at="2026-01-01T00:00:00Z",
                line_start=20,
                line_end=22,
                normalized_claim_type="citation_schema",
                text=(
                    "Structured citations should include ref_id, source_title, "
                    "source_type, page_or_section, claim_text, and "
                    "normalized_claim_type."
                ),
                excerpt="Stable citation fields are required for verifier-ready output.",
                keywords=["citation_schema", "ref_id", "source_title", "claim_text"],
                ingredient_keys=[],
                medication_keys=[],
                domain_keys=["citations", "knowledge_base"],
            )
        ],
    )
    cases = [
        ChatQaEvalCase(
            case_id="chat-qa::CLM-MC-CITATION-002",
            question=(
                "What citation fields should a counseling answer preserve "
                "for verifier-ready output?"
            ),
            scope="supplement_counseling",
            answer_template_key="citation_schema_summary",
            expected_chunk_ids=["chunk::CLM-MC-CITATION-002"],
            expected_reference_ids=["REF-MC-CITATION-001"],
            expected_claim_ids=["CLM-MC-CITATION-002"],
            expected_terms=["ref_id", "source_title", "claim_text"],
        )
    ]

    report = evaluate_retrieval_hit_rate(manifest, cases, top_k=3)

    assert report["case_count"] == 1
    assert report["top1_hit_rate_pct"] == 100.0
    assert report["topk_hit_rate_pct"] == 100.0


def test_generate_bounded_template_answer_preserves_citation_linkage() -> None:
    manifest = RetrievalCorpusManifest(
        manifest_version="test",
        chunk_count=1,
        chunks=[
            RetrievalChunk(
                chunk_id="chunk::CLM-KNOWLEDGE-ANTICOAG-001",
                reference_id="REF-KNOWLEDGE-ANTICOAG-001",
                claim_id="CLM-KNOWLEDGE-ANTICOAG-001",
                source_title="Supplement Interaction Notes",
                source_type="interaction_reference",
                page_or_section="glucosamine chondroitin and anticoagulants",
                reference_uri="data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md",
                license_status="APPROVED_INTERNAL",
                effective_at="2026-01-01T00:00:00Z",
                line_start=10,
                line_end=12,
                normalized_claim_type="drug_interaction",
                text=(
                    "Glucosamine or chondroitin used with warfarin or Coumadin can "
                    "increase anticoagulant effect and bleeding risk."
                ),
                excerpt=(
                    "Glucosamine and chondroitin should be treated as a "
                    "bleeding-risk interaction."
                ),
                keywords=["drug_interaction", "bleeding_risk", "glucosamine", "warfarin"],
                ingredient_keys=["glucosamine", "chondroitin"],
                medication_keys=["warfarin", "coumadin"],
                domain_keys=["drug_interaction", "bleeding_risk"],
            )
        ],
    )

    answer = generate_bounded_template_answer(
        manifest,
        query="What should counseling say about glucosamine with warfarin?",
        answer_template_key="interaction_warning",
    )
    verification = verify_bounded_template_answer(
        answer,
        expected_reference_ids=["REF-KNOWLEDGE-ANTICOAG-001"],
        expected_claim_ids=["CLM-KNOWLEDGE-ANTICOAG-001"],
        expected_terms=["glucosamine", "warfarin"],
        expected_status="supported",
    )

    assert answer.status == "supported"
    assert answer.citations[0].reference_id == "REF-KNOWLEDGE-ANTICOAG-001"
    assert verification.passed is True


def test_generate_bounded_template_answer_handles_out_of_scope_query() -> None:
    manifest = RetrievalCorpusManifest(
        manifest_version="test",
        chunk_count=1,
        chunks=[
            RetrievalChunk(
                chunk_id="chunk::CLM-MC-ACTION-001",
                reference_id="REF-MC-ACTION-001",
                claim_id="CLM-MC-ACTION-001",
                source_title="WellnessBox R&D Master Context",
                source_type="master_context",
                page_or_section="autonomous closed-loop action policy",
                reference_uri="docs/context/master_context.md",
                license_status="APPROVED_INTERNAL",
                effective_at="2026-01-01T00:00:00Z",
                line_start=20,
                line_end=22,
                normalized_claim_type="action_space_constraint",
                text=(
                    "Runtime next_action must stay inside the system-owned "
                    "action space."
                ),
                excerpt="The action space remains system-owned.",
                keywords=["action_space", "policy"],
                ingredient_keys=[],
                medication_keys=[],
                domain_keys=["action_space", "policy"],
            )
        ],
    )

    answer = generate_bounded_template_answer(
        manifest,
        query="What is the weather in Seoul today?",
    )
    verification = verify_bounded_template_answer(
        answer,
        expected_status="out_of_scope",
    )

    assert answer.status == "out_of_scope"
    assert answer.citations == []
    assert verification.passed is True


def test_generate_bounded_template_answer_suppresses_unsupported_claim() -> None:
    manifest = RetrievalCorpusManifest(
        manifest_version="test",
        chunk_count=1,
        chunks=[
            RetrievalChunk(
                chunk_id="chunk::CLM-KNOWLEDGE-ANTICOAG-001",
                reference_id="REF-KNOWLEDGE-ANTICOAG-001",
                claim_id="CLM-KNOWLEDGE-ANTICOAG-001",
                source_title="Supplement Interaction Notes",
                source_type="interaction_reference",
                page_or_section="glucosamine chondroitin and anticoagulants",
                reference_uri="data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md",
                license_status="APPROVED_INTERNAL",
                effective_at="2026-01-01T00:00:00Z",
                line_start=10,
                line_end=12,
                normalized_claim_type="drug_interaction",
                text=(
                    "Glucosamine or chondroitin used with warfarin or Coumadin can "
                    "increase anticoagulant effect and bleeding risk."
                ),
                excerpt=(
                    "Glucosamine and chondroitin should be treated as a "
                    "bleeding-risk interaction."
                ),
                keywords=["drug_interaction", "bleeding_risk", "glucosamine", "warfarin"],
                ingredient_keys=["glucosamine", "chondroitin"],
                medication_keys=["warfarin", "coumadin"],
                domain_keys=["drug_interaction", "bleeding_risk"],
            )
        ],
    )

    answer = generate_bounded_template_answer(
        manifest,
        query="Does glucosamine cure diabetes?",
    )
    verification = verify_bounded_template_answer(
        answer,
        expected_status="unsupported",
    )

    assert answer.status == "unsupported"
    assert answer.citations == []
    assert verification.passed is True


def test_retrieval_chunk_requires_valid_source_date_and_line_range() -> None:
    payload = {
        "chunk_id": "chunk::claim",
        "reference_id": "reference",
        "claim_id": "claim",
        "source_title": "Source",
        "source_type": "official",
        "page_or_section": "section",
        "reference_uri": "https://example.test/source",
        "license_status": "OPEN",
        "effective_at": "2026-01-01T00:00:00",
        "line_start": 3,
        "line_end": 2,
        "normalized_claim_type": "goal_evidence",
        "text": "Evidence text",
        "excerpt": "Evidence excerpt",
    }
    with pytest.raises(ValidationError, match="retrieval_effective_at_timezone_required"):
        RetrievalChunk.model_validate(payload)
    payload["effective_at"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValidationError, match="retrieval_line_range_invalid"):
        RetrievalChunk.model_validate(payload)


def test_retrieval_manifest_rejects_declared_count_mismatch() -> None:
    with pytest.raises(ValidationError, match="retrieval_chunk_count_mismatch"):
        RetrievalCorpusManifest(manifest_version="test", chunk_count=1, chunks=[])


def test_retrieval_filters_retired_passage_at_query_time() -> None:
    chunk = RetrievalChunk(
        chunk_id="chunk::retired",
        reference_id="reference",
        claim_id="claim",
        source_title="Source",
        source_type="official",
        page_or_section="section",
        reference_uri="https://example.test/source",
        license_status="OPEN",
        effective_at="2025-01-01T00:00:00Z",
        retired_at="2026-01-01T00:00:00Z",
        line_start=1,
        line_end=2,
        normalized_claim_type="goal_evidence",
        text="magnesium sleep evidence",
        excerpt="magnesium sleep",
    )
    manifest = RetrievalCorpusManifest(
        manifest_version="test", chunk_count=1, chunks=[chunk]
    )
    assert retrieve_relevant_chunks(
        manifest,
        query="magnesium sleep",
        as_of=datetime(2025, 6, 1, tzinfo=UTC),
    )
    assert not retrieve_relevant_chunks(
        manifest,
        query="magnesium sleep",
        as_of=datetime(2026, 6, 1, tzinfo=UTC),
    )


def test_extract_question_entities_uses_runtime_aliases_and_urgent_signals() -> None:
    result = extract_question_entities(
        "수면과 혈당이 걱정됩니다. 오메가3를 와파린과 먹는데 지금 출혈이 있어요.",
        load_runtime_knowledge_db(),
    )

    assert result.health_goals == ["blood_glucose", "sleep_support"]
    assert result.ingredient_keys == ["omega3"]
    assert result.medication_keys == ["warfarin"]
    assert result.risk_signal_keys == ["active_bleeding"]
    assert result.urgent_risk_detected is True
    assert {match.matched_text for match in result.matches} >= {
        "수면",
        "혈당",
        "오메가3",
        "와파린",
        "출혈",
    }


def test_extract_question_entities_avoids_substring_false_positive() -> None:
    result = extract_question_entities(
        "The zincography article is unrelated to supplements.",
        load_runtime_knowledge_db(),
    )
    assert result.ingredient_keys == []
    assert result.matches == []
