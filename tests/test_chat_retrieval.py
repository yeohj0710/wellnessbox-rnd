import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.build_chat_retrieval_assets import _build_chunk_from_claim, _load_reference_rows
from wellnessbox_rnd.chat.answering import (
    generate_bounded_template_answer,
    verify_bounded_template_answer,
)
from wellnessbox_rnd.chat.retrieval import (
    BoundedKnowledgeScope,
    ChatQaEvalCase,
    QuestionEntityExtraction,
    RetrievalChunk,
    RetrievalCorpusManifest,
    evaluate_retrieval_hit_rate,
    extract_question_entities,
    retrieve_bounded_chunks,
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
                parsed_source_uri="data/raw_references/supplement_overdose_and_drug_interactions_expert.md",
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
                parsed_source_uri="data/raw_references/master_context_citation_structure.md",
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
                parsed_source_uri="data/raw_references/master_context_citation_structure.md",
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
                parsed_source_uri="data/raw_references/supplement_overdose_and_drug_interactions_expert.md",
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
                parsed_source_uri="data/raw_references/master_context_action_space.md",
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
                parsed_source_uri="data/raw_references/supplement_overdose_and_drug_interactions_expert.md",
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
        "parsed_source_uri": "data/raw_references/example.md",
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
        parsed_source_uri="data/raw_references/example.md",
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


def test_bounded_retrieval_enforces_all_scope_allowlists_and_validity() -> None:
    allowed = RetrievalChunk(
        chunk_id="chunk::allowed",
        reference_id="reference-allowed",
        claim_id="claim-allowed",
        source_title="Allowed source",
        source_type="clinical_guideline",
        page_or_section="section",
        reference_uri="https://example.test/allowed",
        parsed_source_uri="data/raw_references/allowed.md",
        license_status="OPEN",
        effective_at="2025-01-01T00:00:00Z",
        line_start=1,
        line_end=2,
        normalized_claim_type="drug_interaction",
        text="glucosamine warfarin interaction",
        excerpt="interaction",
    )
    disallowed = allowed.model_copy(
        update={
            "chunk_id": "chunk::disallowed",
            "reference_id": "reference-disallowed",
            "claim_id": "claim-disallowed",
            "source_type": "unreviewed_blog",
        }
    )
    retired = allowed.model_copy(
        update={
            "chunk_id": "chunk::retired",
            "claim_id": "claim-retired",
            "retired_at": datetime(2026, 1, 1, tzinfo=UTC),
        }
    )
    manifest = RetrievalCorpusManifest(
        manifest_version="test", chunk_count=3, chunks=[allowed, disallowed, retired]
    )
    scope = BoundedKnowledgeScope(
        scope_id="counseling-v1",
        allowed_source_types=["clinical_guideline"],
        allowed_claim_types=["drug_interaction"],
        allowed_reference_ids=["reference-allowed"],
        max_results=2,
    )

    results = retrieve_bounded_chunks(
        manifest,
        scope=scope,
        query="glucosamine warfarin",
        as_of=datetime(2026, 6, 1, tzinfo=UTC),
        top_k=2,
    )

    assert [result.chunk_id for result in results] == ["chunk::allowed"]


def test_bounded_retrieval_rejects_naive_time_and_excess_top_k() -> None:
    scope = BoundedKnowledgeScope(
        scope_id="counseling-v1",
        allowed_source_types=["clinical_guideline"],
        allowed_claim_types=["drug_interaction"],
        allowed_reference_ids=["reference-allowed"],
        max_results=1,
    )
    manifest = RetrievalCorpusManifest(manifest_version="test", chunk_count=0, chunks=[])
    with pytest.raises(ValueError, match="bounded_retrieval_as_of_timezone_required"):
        retrieve_bounded_chunks(
            manifest,
            scope=scope,
            query="query",
            as_of=datetime(2026, 1, 1),
        )
    with pytest.raises(ValueError, match="bounded_retrieval_top_k_outside_scope"):
        retrieve_bounded_chunks(
            manifest,
            scope=scope,
            query="query",
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
            top_k=2,
        )


def test_bounded_scope_rejects_unsorted_or_duplicate_allowlists() -> None:
    with pytest.raises(ValidationError, match="must_be_sorted_unique"):
        BoundedKnowledgeScope(
            scope_id="bad",
            allowed_source_types=["b", "a"],
            allowed_claim_types=["claim"],
            allowed_reference_ids=["reference"],
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


def test_extract_question_entities_does_not_infer_specific_ingredient_subtype() -> None:
    result = extract_question_entities(
        "비타민 D와 마그네슘에 대해 알려주세요.", load_runtime_knowledge_db()
    )
    assert result.ingredient_keys == []


@pytest.mark.parametrize(
    ("question", "expected_key"),
    [
        ("I cannot breathe after taking this.", "difficulty_breathing"),
        ("숨이 차고 가슴 압박이 있습니다.", "difficulty_breathing"),
        ("피가 멈추지 않고 계속 납니다.", "active_bleeding"),
        ("혀가 붓고 호흡곤란이 있습니다.", "anaphylaxis"),
    ],
)
def test_extract_question_entities_covers_urgent_expression_variants(
    question: str, expected_key: str
) -> None:
    result = extract_question_entities(question, load_runtime_knowledge_db())
    assert expected_key in result.risk_signal_keys
    assert result.urgent_risk_detected is True


@pytest.mark.parametrize(
    "question",
    [
        "No chest pain is present.",
        "No difficulty breathing is present.",
        "흉통은 없습니다.",
        "출혈은 없고 숨도 차지 않습니다.",
    ],
)
def test_extract_question_entities_does_not_escalate_explicit_negation(
    question: str,
) -> None:
    result = extract_question_entities(question, load_runtime_knowledge_db())
    assert result.risk_signal_keys
    assert result.urgent_risk_detected is False
    assert all(match.negated for match in result.matches if match.kind == "risk_signal")


@pytest.mark.parametrize(
    "question",
    [
        "No bleeding, but I have chest pain.",
        "I deny bleeding but have chest pain.",
        "출혈은 없지만 흉통이 있습니다.",
    ],
)
def test_negation_does_not_cross_contrast_clause_into_urgent_signal(
    question: str,
) -> None:
    result = extract_question_entities(question, load_runtime_knowledge_db())
    chest = [match for match in result.matches if match.canonical_key == "chest_pain"]
    assert chest and chest[0].negated is False
    assert result.urgent_risk_detected is True


def test_negation_does_not_cross_coordinated_proposition() -> None:
    result = extract_question_entities(
        "No bleeding and I have chest pain.", load_runtime_knowledge_db()
    )
    chest = [match for match in result.matches if match.canonical_key == "chest_pain"]
    assert chest and chest[0].negated is False
    assert result.urgent_risk_detected is True


def test_question_entity_contract_rejects_forged_urgent_summary() -> None:
    valid = extract_question_entities("I have chest pain.", load_runtime_knowledge_db())
    with pytest.raises(ValidationError, match="question_entity_urgent_trace_mismatch"):
        QuestionEntityExtraction.model_validate(
            valid.model_dump() | {"urgent_risk_detected": False}
        )


def test_build_chunk_rejects_tampered_claim_lineage() -> None:
    references = _load_reference_rows("data/knowledge/reference_knowledge_base_v1.json")
    claim = json.loads(
        Path("data/parsed_references/reference_claims_v1.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    claim["citation_span"]["line_start"] = 1
    claim["citation_span"]["line_end"] = 2
    with pytest.raises(ValueError, match="claim_source_span_identity_mismatch"):
        _build_chunk_from_claim(claim, references)
