from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wellnessbox_rnd.chat.retrieval import (
    BoundedKnowledgeScope,
    RetrievalChunk,
    RetrievalCorpusManifest,
    RetrievalResult,
    extract_question_entities,
    load_approved_counseling_scope,
    retrieve_bounded_chunks,
)
from wellnessbox_rnd.chat.verifier import (
    CounselingAnswerVerifierPolicy,
    load_counseling_answer_verifier_policy,
    require_repository_approved_policy,
)
from wellnessbox_rnd.knowledge.runtime_db import RuntimeKnowledgeDB, load_runtime_knowledge_db


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    reference_id: str
    claim_id: str
    source_title: str
    source_type: str
    page_or_section: str
    reference_uri: str
    effective_at: datetime
    retired_at: datetime | None = None
    active_at_answer_time: bool


class AnswerUncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    level: Literal["low", "moderate", "high"]
    reasons: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_reasons(self) -> AnswerUncertainty:
        if self.reasons != sorted(set(self.reasons)):
            raise ValueError("answer_uncertainty_reasons_must_be_sorted_unique")
        return self


class ChatTemplateAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str
    status: Literal["supported", "unsupported", "out_of_scope", "safety_escalation"]
    answer_template_key: str
    answer_text: str
    citations: list[AnswerCitation] = Field(default_factory=list)
    used_chunk_ids: list[str] = Field(default_factory=list)
    evidence_only: bool = True
    top_result_score: float = 0.0
    rationale: str
    knowledge_scope_id: str
    answered_at: datetime
    uncertainty: AnswerUncertainty
    safety_policy_id: str | None = None
    detected_urgent_risk_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_answer_time(self) -> ChatTemplateAnswer:
        if self.answered_at.tzinfo is None or self.answered_at.utcoffset() is None:
            raise ValueError("chat_answer_time_timezone_required")
        if len(self.used_chunk_ids) != len(set(self.used_chunk_ids)):
            raise ValueError("chat_answer_duplicate_used_chunk_id")
        citation_ids = [citation.chunk_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("chat_answer_duplicate_citation_chunk_id")
        if set(citation_ids) != set(self.used_chunk_ids):
            raise ValueError("chat_answer_citation_used_chunk_bijection_required")
        if self.detected_urgent_risk_keys != sorted(set(self.detected_urgent_risk_keys)):
            raise ValueError("chat_answer_urgent_risk_keys_must_be_sorted_unique")
        if self.status == "safety_escalation":
            if not self.safety_policy_id or not self.detected_urgent_risk_keys:
                raise ValueError("chat_answer_safety_escalation_trace_required")
            if self.citations or self.used_chunk_ids:
                raise ValueError("chat_answer_safety_escalation_must_not_cite")
        elif self.safety_policy_id is not None or self.detected_urgent_risk_keys:
            raise ValueError("chat_answer_safety_trace_only_for_escalation")
        return self


class ChatAnswerVerification(BaseModel):
    status_ok: bool
    citation_linkage_ok: bool
    expected_reference_ids_ok: bool
    expected_claim_ids_ok: bool
    expected_terms_ok: bool
    out_of_scope_handled_ok: bool
    unsupported_claim_suppressed_ok: bool
    safety_boundary_ok: bool
    answer_grounding_ok: bool
    required_risk_coverage_ok: bool
    forbidden_expression_ok: bool
    emergency_precedence_ok: bool
    verifier_policy_ok: bool
    knowledge_scope_ok: bool
    evidence_validity_ok: bool
    uncertainty_ok: bool
    passed: bool
    issues: list[str] = Field(default_factory=list)


def generate_bounded_template_answer(
    manifest: RetrievalCorpusManifest,
    *,
    query: str,
    scope: BoundedKnowledgeScope,
    as_of: datetime,
    answer_template_key: str | None = None,
    top_k: int = 5,
    min_score: float = 2.0,
    runtime_db: RuntimeKnowledgeDB | None = None,
    verifier_policy: CounselingAnswerVerifierPolicy | None = None,
) -> ChatTemplateAnswer:
    runtime_db = runtime_db or load_runtime_knowledge_db()
    policy = require_repository_approved_policy(
        verifier_policy or load_counseling_answer_verifier_policy()
    )
    entities = extract_question_entities(query, runtime_db)
    urgent_keys = sorted(
        set(entities.risk_signal_keys) & set(policy.urgent_risk_keys)
        if entities.urgent_risk_detected
        else set()
    )
    if urgent_keys:
        return ChatTemplateAnswer(
            query=query,
            status="safety_escalation",
            answer_template_key="urgent_safety_guidance",
            answer_text=policy.emergency_guidance_text,
            rationale="urgent_risk_precedes_retrieval_and_recommendation",
            knowledge_scope_id=scope.scope_id,
            answered_at=as_of,
            uncertainty=AnswerUncertainty(
                level="high", reasons=["urgent_symptom_requires_emergency_evaluation"]
            ),
            safety_policy_id=policy.policy_id,
            detected_urgent_risk_keys=urgent_keys,
        )
    results = retrieve_bounded_chunks(manifest, scope=scope, query=query, top_k=top_k, as_of=as_of)
    query_tokens = _tokenize(query)
    if not results:
        return ChatTemplateAnswer(
            query=query,
            status="out_of_scope",
            answer_template_key=answer_template_key or "out_of_scope",
            answer_text=(
                "I do not have in-scope evidence for that counseling question. "
                "I can only answer bounded supplement counseling questions "
                "grounded in local references."
            ),
            rationale="no_retrieval_hit",
            knowledge_scope_id=scope.scope_id,
            answered_at=as_of,
            uncertainty=_build_uncertainty(status="out_of_scope", chunks=[]),
        )

    chunk_by_id = {chunk.chunk_id: chunk for chunk in manifest.chunks}
    selected_result, selected_chunk = _select_supported_candidate(
        results=results,
        chunk_by_id=chunk_by_id,
        query_tokens=query_tokens,
        answer_template_key=answer_template_key,
        min_score=min_score,
    )

    if selected_result is None or selected_chunk is None:
        status = "unsupported" if _looks_in_scope(query_tokens, manifest) else "out_of_scope"
        rationale = (
            "in_scope_but_not_supported" if status == "unsupported" else "out_of_scope_query"
        )
        return ChatTemplateAnswer(
            query=query,
            status=status,
            answer_template_key=answer_template_key or "unsupported",
            answer_text=(
                "I do not have citation-backed evidence in the local "
                "counseling corpus to support that claim, "
                "so I cannot state it as true."
                if status == "unsupported"
                else "I do not have in-scope evidence for that counseling question. "
                "I can only answer bounded supplement counseling questions "
                "grounded in local references."
            ),
            top_result_score=results[0].score,
            rationale=rationale,
            knowledge_scope_id=scope.scope_id,
            answered_at=as_of,
            uncertainty=_build_uncertainty(status=status, chunks=[]),
        )

    template_key = answer_template_key or _template_key_for_chunk(selected_chunk)
    citations = [_build_citation(selected_chunk, as_of=as_of)]
    return ChatTemplateAnswer(
        query=query,
        status="supported",
        answer_template_key=template_key,
        answer_text=_render_template_answer(template_key, selected_chunk),
        citations=citations,
        used_chunk_ids=[selected_chunk.chunk_id],
        top_result_score=selected_result.score,
        rationale=f"supported_by::{selected_chunk.claim_id}",
        knowledge_scope_id=scope.scope_id,
        answered_at=as_of,
        uncertainty=_build_uncertainty(status="supported", chunks=[selected_chunk]),
    )


def verify_bounded_template_answer(
    answer: ChatTemplateAnswer,
    *,
    manifest: RetrievalCorpusManifest,
    scope: BoundedKnowledgeScope,
    as_of: datetime,
    expected_reference_ids: list[str] | None = None,
    expected_claim_ids: list[str] | None = None,
    expected_terms: list[str] | None = None,
    expected_status: str | None = None,
    runtime_db: RuntimeKnowledgeDB | None = None,
    verifier_policy: CounselingAnswerVerifierPolicy | None = None,
) -> ChatAnswerVerification:
    issues: list[str] = []
    normalized_text = answer.answer_text.lower()
    expected_reference_ids = expected_reference_ids or []
    expected_claim_ids = expected_claim_ids or []
    expected_terms = expected_terms or []
    runtime_db = runtime_db or load_runtime_knowledge_db()
    try:
        policy = require_repository_approved_policy(
            verifier_policy or load_counseling_answer_verifier_policy()
        )
        verifier_policy_ok = answer.safety_policy_id in {None, policy.policy_id}
    except ValueError:
        policy = load_counseling_answer_verifier_policy()
        verifier_policy_ok = False
    if not verifier_policy_ok:
        issues.append("verifier_policy_mismatch")

    status_ok = expected_status is None or answer.status == expected_status
    if not status_ok:
        issues.append(f"unexpected_status::{answer.status}")

    citation_linkage_ok = all(
        citation.chunk_id in answer.used_chunk_ids and citation.reference_id and citation.claim_id
        for citation in answer.citations
    )
    if answer.status == "supported" and not answer.citations:
        citation_linkage_ok = False
    if not citation_linkage_ok:
        issues.append("citation_linkage_failed")

    found_reference_ids = {citation.reference_id for citation in answer.citations}
    expected_reference_ids_ok = set(expected_reference_ids).issubset(found_reference_ids)
    if expected_reference_ids and not expected_reference_ids_ok:
        issues.append("missing_expected_reference_ids")

    found_claim_ids = {citation.claim_id for citation in answer.citations}
    expected_claim_ids_ok = set(expected_claim_ids).issubset(found_claim_ids)
    if expected_claim_ids and not expected_claim_ids_ok:
        issues.append("missing_expected_claim_ids")

    expected_terms_ok = all(term.lower() in normalized_text for term in expected_terms)
    if expected_terms and not expected_terms_ok:
        issues.append("missing_expected_terms")

    out_of_scope_handled_ok = True
    if answer.status == "out_of_scope":
        out_of_scope_handled_ok = not answer.citations and "in-scope evidence" in normalized_text
    if not out_of_scope_handled_ok:
        issues.append("out_of_scope_handling_failed")

    unsupported_claim_suppressed_ok = True
    if answer.status == "unsupported":
        unsupported_claim_suppressed_ok = (
            not answer.citations and "cannot state it as true" in normalized_text
        )
    if not unsupported_claim_suppressed_ok:
        issues.append("unsupported_claim_not_suppressed")

    safety_boundary_ok = "manual review" not in normalized_text and "handoff" not in normalized_text
    if not safety_boundary_ok:
        issues.append("safety_boundary_violated")

    entities = extract_question_entities(answer.query, runtime_db)
    urgent_keys = sorted(
        set(entities.risk_signal_keys) & set(policy.urgent_risk_keys)
        if entities.urgent_risk_detected
        else set()
    )
    forbidden_expression_ok = not any(
        expression in normalized_text for expression in policy.forbidden_expressions
    )
    if not forbidden_expression_ok:
        issues.append("forbidden_expression_detected")

    emergency_precedence_ok = True
    if urgent_keys:
        emergency_precedence_ok = (
            answer.status == "safety_escalation"
            and answer.answer_text == policy.emergency_guidance_text
            and answer.detected_urgent_risk_keys == urgent_keys
            and answer.safety_policy_id == policy.policy_id
            and not answer.citations
            and not answer.used_chunk_ids
            and not any(
                expression in normalized_text for expression in policy.recommendation_expressions
            )
        )
    elif answer.status == "safety_escalation":
        emergency_precedence_ok = False
    if not emergency_precedence_ok:
        issues.append("emergency_safety_precedence_failed")

    knowledge_scope_ok = answer.knowledge_scope_id == scope.scope_id and answer.answered_at == as_of
    try:
        knowledge_scope_ok = knowledge_scope_ok and (
            scope == load_approved_counseling_scope(scope.scope_id)
        )
    except ValueError:
        knowledge_scope_ok = False
    if len(answer.used_chunk_ids) != len(set(answer.used_chunk_ids)):
        knowledge_scope_ok = False
    allowed_sources = set(scope.allowed_source_types)
    allowed_claims = set(scope.allowed_claim_types)
    allowed_references = set(scope.allowed_reference_ids)
    chunk_by_id = {chunk.chunk_id: chunk for chunk in manifest.chunks}
    selected_chunks: list[RetrievalChunk] = []
    for chunk_id in answer.used_chunk_ids:
        chunk = chunk_by_id.get(chunk_id)
        if chunk is None:
            knowledge_scope_ok = False
            continue
        selected_chunks.append(chunk)
        if (
            chunk.source_type not in allowed_sources
            or chunk.normalized_claim_type not in allowed_claims
            or chunk.reference_id not in allowed_references
        ):
            knowledge_scope_ok = False
    if not knowledge_scope_ok:
        issues.append("knowledge_scope_mismatch")

    answer_grounding_ok = True
    if answer.status == "supported":
        answer_grounding_ok = len(
            selected_chunks
        ) == 1 and answer.answer_text == _render_template_answer(
            answer.answer_template_key, selected_chunks[0]
        )
    elif answer.status == "unsupported":
        answer_grounding_ok = (
            not answer.citations
            and not answer.used_chunk_ids
            and answer.answer_text
            == (
                "I do not have citation-backed evidence in the local counseling corpus "
                "to support that claim, so I cannot state it as true."
            )
        )
    elif answer.status == "out_of_scope":
        answer_grounding_ok = (
            not answer.citations
            and not answer.used_chunk_ids
            and answer.answer_text
            == (
                "I do not have in-scope evidence for that counseling question. "
                "I can only answer bounded supplement counseling questions "
                "grounded in local references."
            )
        )
    elif answer.status == "safety_escalation":
        answer_grounding_ok = answer.answer_text == policy.emergency_guidance_text
    if not answer_grounding_ok:
        issues.append("unsupported_or_unapproved_answer_text")

    required_risk_coverage_ok = True
    if answer.status == "supported" and any(
        chunk.normalized_claim_type == "drug_interaction" for chunk in selected_chunks
    ):
        required_risk_coverage_ok = all(
            term in normalized_text for term in policy.interaction_risk_terms
        )
    if not required_risk_coverage_ok:
        issues.append("required_risk_omitted")

    evidence_validity_ok = True
    citations_by_chunk = {citation.chunk_id: citation for citation in answer.citations}
    if len(citations_by_chunk) != len(answer.citations):
        evidence_validity_ok = False
    for chunk in selected_chunks:
        citation = citations_by_chunk.get(chunk.chunk_id)
        expected_active = chunk.effective_at <= as_of and (
            chunk.retired_at is None or chunk.retired_at > as_of
        )
        if (
            citation is None
            or citation.model_dump() != _build_citation(chunk, as_of=as_of).model_dump()
            or not expected_active
        ):
            evidence_validity_ok = False
    if answer.status != "supported" and (answer.citations or answer.used_chunk_ids):
        evidence_validity_ok = False
    if not evidence_validity_ok:
        issues.append("answer_evidence_validity_mismatch")

    expected_uncertainty = (
        AnswerUncertainty(level="high", reasons=["urgent_symptom_requires_emergency_evaluation"])
        if answer.status == "safety_escalation"
        else _build_uncertainty(status=answer.status, chunks=selected_chunks)
    )
    uncertainty_ok = answer.uncertainty == expected_uncertainty
    if not uncertainty_ok:
        issues.append("answer_uncertainty_mismatch")

    passed = all(
        [
            status_ok,
            citation_linkage_ok,
            expected_reference_ids_ok,
            expected_claim_ids_ok,
            expected_terms_ok,
            out_of_scope_handled_ok,
            unsupported_claim_suppressed_ok,
            safety_boundary_ok,
            answer_grounding_ok,
            required_risk_coverage_ok,
            forbidden_expression_ok,
            emergency_precedence_ok,
            verifier_policy_ok,
            knowledge_scope_ok,
            evidence_validity_ok,
            uncertainty_ok,
        ]
    )

    return ChatAnswerVerification(
        status_ok=status_ok,
        citation_linkage_ok=citation_linkage_ok,
        expected_reference_ids_ok=expected_reference_ids_ok,
        expected_claim_ids_ok=expected_claim_ids_ok,
        expected_terms_ok=expected_terms_ok,
        out_of_scope_handled_ok=out_of_scope_handled_ok,
        unsupported_claim_suppressed_ok=unsupported_claim_suppressed_ok,
        safety_boundary_ok=safety_boundary_ok,
        answer_grounding_ok=answer_grounding_ok,
        required_risk_coverage_ok=required_risk_coverage_ok,
        forbidden_expression_ok=forbidden_expression_ok,
        emergency_precedence_ok=emergency_precedence_ok,
        verifier_policy_ok=verifier_policy_ok,
        knowledge_scope_ok=knowledge_scope_ok,
        evidence_validity_ok=evidence_validity_ok,
        uncertainty_ok=uncertainty_ok,
        passed=passed,
        issues=issues,
    )


def _select_supported_candidate(
    *,
    results: list[RetrievalResult],
    chunk_by_id: dict[str, RetrievalChunk],
    query_tokens: set[str],
    answer_template_key: str | None,
    min_score: float,
) -> tuple[RetrievalResult | None, RetrievalChunk | None]:
    preferred_claim_types = _preferred_claim_types_for_template(answer_template_key)
    ranked_candidates: list[tuple[int, float, RetrievalResult, RetrievalChunk]] = []
    for result in results:
        chunk = chunk_by_id[result.chunk_id]
        if not _candidate_is_supported(
            chunk=chunk,
            query_tokens=query_tokens,
            answer_template_key=answer_template_key,
            score=result.score,
            min_score=min_score,
        ):
            continue
        preference = 1 if chunk.normalized_claim_type in preferred_claim_types else 0
        ranked_candidates.append((preference, result.score, result, chunk))

    if not ranked_candidates:
        return None, None
    ranked_candidates.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            item[2].chunk_id,
        )
    )
    _, _, result, chunk = ranked_candidates[0]
    return result, chunk


def _candidate_is_supported(
    *,
    chunk: RetrievalChunk,
    query_tokens: set[str],
    answer_template_key: str | None,
    score: float,
    min_score: float,
) -> bool:
    if score < min_score:
        return False
    template_key = answer_template_key or _template_key_for_chunk(chunk)
    if template_key == "interaction_warning":
        has_ingredient = any(token in chunk.ingredient_keys for token in query_tokens)
        has_medication = any(token in chunk.medication_keys for token in query_tokens)
        return has_ingredient and has_medication
    if template_key == "citation_requirement_summary":
        return "citation" in query_tokens or "reference" in query_tokens or "ids" in query_tokens
    if template_key == "citation_schema_summary":
        return "citation" in query_tokens or "ref" in query_tokens or "source" in query_tokens
    if template_key == "safety_recheck_summary":
        return "safety" in query_tokens or "risk" in query_tokens or "high" in query_tokens
    if template_key == "action_space_summary":
        return "action" in query_tokens or "space" in query_tokens or "autonomous" in query_tokens
    return True


def _preferred_claim_types_for_template(answer_template_key: str | None) -> set[str]:
    mapping = {
        "interaction_warning": {"drug_interaction"},
        "citation_requirement_summary": {"citation_requirement"},
        "citation_schema_summary": {"citation_schema"},
        "safety_recheck_summary": {"safety_recheck_policy"},
        "action_space_summary": {"action_space_constraint"},
    }
    return mapping.get(answer_template_key or "", set())


def _template_key_for_chunk(chunk: RetrievalChunk) -> str:
    mapping = {
        "drug_interaction": "interaction_warning",
        "citation_requirement": "citation_requirement_summary",
        "citation_schema": "citation_schema_summary",
        "safety_recheck_policy": "safety_recheck_summary",
        "action_space_constraint": "action_space_summary",
    }
    return mapping.get(chunk.normalized_claim_type, "evidence_summary")


def _build_citation(chunk: RetrievalChunk, *, as_of: datetime) -> AnswerCitation:
    return AnswerCitation(
        chunk_id=chunk.chunk_id,
        reference_id=chunk.reference_id,
        claim_id=chunk.claim_id,
        source_title=chunk.source_title,
        source_type=chunk.source_type,
        page_or_section=chunk.page_or_section,
        reference_uri=chunk.reference_uri,
        effective_at=chunk.effective_at,
        retired_at=chunk.retired_at,
        active_at_answer_time=chunk.effective_at <= as_of
        and (chunk.retired_at is None or chunk.retired_at > as_of),
    )


def _build_uncertainty(
    *,
    status: Literal["supported", "unsupported", "out_of_scope"],
    chunks: list[RetrievalChunk],
) -> AnswerUncertainty:
    if status == "out_of_scope":
        return AnswerUncertainty(level="high", reasons=["no_allowed_in_scope_evidence_retrieved"])
    if status == "unsupported":
        return AnswerUncertainty(
            level="high", reasons=["allowed_corpus_does_not_support_requested_claim"]
        )
    claim_types = {chunk.normalized_claim_type for chunk in chunks}
    reasons = {"bounded_to_cited_passages_not_individualized_clinical_certainty"}
    high_types = {"inconclusive_goal_evidence", "null_goal_evidence_without_deficiency"}
    moderate_types = {
        "limited_goal_evidence",
        "mixed_goal_evidence",
        "candidate_prior_policy",
        "candidate_signal_policy",
        "safety_recheck_policy",
        "action_space_constraint",
    }
    if claim_types & high_types:
        level = "high"
        reasons.add("cited_claim_is_inconclusive_or_null_in_bounded_population")
    elif claim_types & moderate_types:
        level = "moderate"
        reasons.add("cited_claim_is_limited_mixed_or_policy_scoped")
    else:
        level = "low"
    return AnswerUncertainty(level=level, reasons=sorted(reasons))


def _render_template_answer(template_key: str, chunk: RetrievalChunk) -> str:
    if template_key == "interaction_warning":
        ingredient_text = " or ".join(chunk.ingredient_keys)
        medication_text = " or ".join(chunk.medication_keys)
        return (
            f"{ingredient_text.title()} with {medication_text.title()} should be "
            "treated as a drug interaction. The bounded counseling answer "
            "should say this combination can increase anticoagulant effect "
            "and bleeding risk."
        )
    if template_key == "citation_requirement_summary":
        return (
            "The counseling answer should keep reference_ids and citation "
            "linkage so the response stays evidence-backed and verifier-ready."
        )
    if template_key == "citation_schema_summary":
        return (
            "The citation payload should preserve ref_id, source_title, "
            "source_type, page_or_section, claim_text, and "
            "normalized_claim_type."
        )
    if template_key == "safety_recheck_summary":
        return (
            "When safety risk rises, the bounded counseling path should route "
            "to trigger_safety_recheck as a system action."
        )
    if template_key == "action_space_summary":
        return (
            "The counseling module should stay inside the system-owned action "
            "space and avoid non-system actions."
        )
    return chunk.text


def _looks_in_scope(query_tokens: set[str], manifest: RetrievalCorpusManifest) -> bool:
    corpus_tokens: set[str] = set()
    for chunk in manifest.chunks:
        corpus_tokens |= _tokenize(
            " ".join(
                [
                    chunk.normalized_claim_type,
                    chunk.text,
                    " ".join(chunk.keywords),
                    " ".join(chunk.ingredient_keys),
                    " ".join(chunk.medication_keys),
                    " ".join(chunk.domain_keys),
                ]
            )
        )
    return bool(query_tokens & corpus_tokens)


def _tokenize(text: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    stopwords = {
        "and",
        "are",
        "can",
        "does",
        "for",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "or",
        "should",
        "say",
        "the",
        "to",
        "today",
        "what",
        "when",
        "why",
        "with",
    }
    return {token for token in normalized.split() if len(token) >= 2 and token not in stopwords}


__all__ = [
    "AnswerCitation",
    "AnswerUncertainty",
    "ChatAnswerVerification",
    "ChatTemplateAnswer",
    "generate_bounded_template_answer",
    "verify_bounded_template_answer",
]
