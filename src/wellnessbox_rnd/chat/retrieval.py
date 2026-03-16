from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field


class RetrievalChunk(BaseModel):
    chunk_id: str
    reference_id: str
    claim_id: str
    source_title: str
    source_type: str
    page_or_section: str
    reference_uri: str
    normalized_claim_type: str
    text: str
    excerpt: str
    keywords: list[str] = Field(default_factory=list)
    ingredient_keys: list[str] = Field(default_factory=list)
    medication_keys: list[str] = Field(default_factory=list)
    domain_keys: list[str] = Field(default_factory=list)


class RetrievalCorpusManifest(BaseModel):
    manifest_version: str
    chunk_count: int
    chunks: list[RetrievalChunk] = Field(default_factory=list)


class ChatQaEvalCase(BaseModel):
    case_id: str
    question: str
    scope: str
    answer_template_key: str
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_reference_ids: list[str] = Field(default_factory=list)
    expected_claim_ids: list[str] = Field(default_factory=list)
    expected_terms: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    chunk_id: str
    score: float
    reference_id: str
    claim_id: str
    text: str


def load_retrieval_corpus_manifest(path: str | Path) -> RetrievalCorpusManifest:
    return RetrievalCorpusManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_chat_qa_eval_cases(path: str | Path) -> list[ChatQaEvalCase]:
    rows: list[ChatQaEvalCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(ChatQaEvalCase.model_validate_json(line))
    return rows


def retrieve_relevant_chunks(
    manifest: RetrievalCorpusManifest,
    *,
    query: str,
    top_k: int = 3,
) -> list[RetrievalResult]:
    query_tokens = _tokenize(query)
    scored: list[tuple[float, RetrievalChunk]] = []
    for chunk in manifest.chunks:
        score = _score_chunk(query_tokens, chunk)
        if score > 0.0:
            scored.append((score, chunk))
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].chunk_id,
        )
    )
    return [
        RetrievalResult(
            chunk_id=chunk.chunk_id,
            score=round(score, 6),
            reference_id=chunk.reference_id,
            claim_id=chunk.claim_id,
            text=chunk.text,
        )
        for score, chunk in scored[:top_k]
    ]


def evaluate_retrieval_hit_rate(
    manifest: RetrievalCorpusManifest,
    cases: list[ChatQaEvalCase],
    *,
    top_k: int = 3,
) -> dict[str, object]:
    case_reports: list[dict[str, object]] = []
    top1_hits = 0
    topk_hits = 0
    for case in cases:
        results = retrieve_relevant_chunks(manifest, query=case.question, top_k=top_k)
        retrieved_chunk_ids = [result.chunk_id for result in results]
        top1_hit = bool(
            retrieved_chunk_ids[:1] and retrieved_chunk_ids[0] in case.expected_chunk_ids
        )
        topk_hit = any(chunk_id in case.expected_chunk_ids for chunk_id in retrieved_chunk_ids)
        top1_hits += int(top1_hit)
        topk_hits += int(topk_hit)
        case_reports.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_chunk_ids": case.expected_chunk_ids,
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "top1_hit": top1_hit,
                "topk_hit": topk_hit,
            }
        )
    case_count = len(cases)
    return {
        "case_count": case_count,
        "top1_hit_rate_pct": round((top1_hits / case_count) * 100.0, 2) if case_count else 0.0,
        "topk_hit_rate_pct": round((topk_hits / case_count) * 100.0, 2) if case_count else 0.0,
        "cases": case_reports,
    }


def _score_chunk(query_tokens: set[str], chunk: RetrievalChunk) -> float:
    chunk_tokens = _tokenize(
        " ".join(
            [
                chunk.text,
                chunk.excerpt,
                chunk.source_title,
                chunk.page_or_section,
                " ".join(chunk.keywords),
                " ".join(chunk.ingredient_keys),
                " ".join(chunk.medication_keys),
                " ".join(chunk.domain_keys),
                chunk.normalized_claim_type,
            ]
        )
    )
    if not query_tokens or not chunk_tokens:
        return 0.0
    shared = query_tokens & chunk_tokens
    if not shared:
        return 0.0
    score = float(len(shared))
    if chunk.normalized_claim_type in query_tokens:
        score += 1.0
    if any(token in chunk.ingredient_keys for token in query_tokens):
        score += 1.0
    if any(token in chunk.medication_keys for token in query_tokens):
        score += 1.0
    return score


def _tokenize(text: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return {token for token in normalized.split() if len(token) >= 2}
