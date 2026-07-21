from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wellnessbox_rnd.knowledge.runtime_db import RuntimeKnowledgeDB


class RetrievalChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    reference_id: str
    claim_id: str
    source_title: str
    source_type: str
    page_or_section: str
    reference_uri: str
    parsed_source_uri: str
    license_status: str = Field(min_length=2)
    effective_at: datetime
    retired_at: datetime | None = None
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    normalized_claim_type: str
    text: str
    excerpt: str
    keywords: list[str] = Field(default_factory=list)
    ingredient_keys: list[str] = Field(default_factory=list)
    medication_keys: list[str] = Field(default_factory=list)
    domain_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_lineage(self) -> RetrievalChunk:
        if self.effective_at.tzinfo is None or self.effective_at.utcoffset() is None:
            raise ValueError("retrieval_effective_at_timezone_required")
        if self.retired_at is not None:
            if self.retired_at.tzinfo is None or self.retired_at.utcoffset() is None:
                raise ValueError("retrieval_retired_at_timezone_required")
            if self.retired_at <= self.effective_at:
                raise ValueError("retrieval_retired_at_must_follow_effective_at")
        if self.line_end < self.line_start:
            raise ValueError("retrieval_line_range_invalid")
        return self


class RetrievalCorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: str
    chunk_count: int
    chunks: list[RetrievalChunk] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_manifest(self) -> RetrievalCorpusManifest:
        if self.chunk_count != len(self.chunks):
            raise ValueError("retrieval_chunk_count_mismatch")
        identities = [chunk.chunk_id for chunk in self.chunks]
        if len(identities) != len(set(identities)):
            raise ValueError("retrieval_duplicate_chunk_id")
        return self


class BoundedKnowledgeScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_id: str = Field(min_length=1)
    allowed_source_types: list[str] = Field(min_length=1)
    allowed_claim_types: list[str] = Field(min_length=1)
    allowed_reference_ids: list[str] = Field(min_length=1)
    max_results: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_allowlists(self) -> BoundedKnowledgeScope:
        for field_name in (
            "allowed_source_types",
            "allowed_claim_types",
            "allowed_reference_ids",
        ):
            values = getattr(self, field_name)
            if values != sorted(set(values)):
                raise ValueError(f"knowledge_scope_{field_name}_must_be_sorted_unique")
            if any(not value.strip() for value in values):
                raise ValueError(f"knowledge_scope_{field_name}_blank")
        return self


class QuestionEntityKind(StrEnum):
    HEALTH_GOAL = "health_goal"
    INGREDIENT = "ingredient"
    MEDICATION = "medication"
    RISK_SIGNAL = "risk_signal"


class QuestionEntityMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: QuestionEntityKind
    canonical_key: str
    matched_text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    negated: bool = False


class QuestionEntityExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["question_entity_extraction_v1"] = (
        "question_entity_extraction_v1"
    )
    question: str = Field(min_length=1, max_length=2000)
    health_goals: list[str]
    ingredient_keys: list[str]
    medication_keys: list[str]
    risk_signal_keys: list[str]
    urgent_risk_detected: bool
    matches: list[QuestionEntityMatch]

    @model_validator(mode="after")
    def validate_trace_reconciliation(self) -> QuestionEntityExtraction:
        expected = {
            kind: sorted(
                {match.canonical_key for match in self.matches if match.kind == kind}
            )
            for kind in QuestionEntityKind
        }
        supplied = {
            QuestionEntityKind.HEALTH_GOAL: self.health_goals,
            QuestionEntityKind.INGREDIENT: self.ingredient_keys,
            QuestionEntityKind.MEDICATION: self.medication_keys,
            QuestionEntityKind.RISK_SIGNAL: self.risk_signal_keys,
        }
        if supplied != expected:
            raise ValueError("question_entity_aggregate_trace_mismatch")
        urgent_keys = set(_URGENT_RISK_ALIASES)
        expected_urgent = any(
            match.kind == QuestionEntityKind.RISK_SIGNAL
            and match.canonical_key in urgent_keys
            and not match.negated
            for match in self.matches
        )
        if self.urgent_risk_detected != expected_urgent:
            raise ValueError("question_entity_urgent_trace_mismatch")
        for match in self.matches:
            if match.end > len(self.question):
                raise ValueError("question_entity_match_range_invalid")
            if self.question[match.start : match.end] != match.matched_text:
                raise ValueError("question_entity_match_text_mismatch")
        return self


_GOAL_ALIASES = {
    "stress_support": ("stress", "anxiety", "스트레스", "긴장"),
    "sleep_support": ("sleep", "insomnia", "수면", "불면"),
    "immunity_support": ("immunity", "immune", "면역"),
    "energy_support": ("energy", "fatigue", "에너지", "피로"),
    "gut_health": ("gut health", "digestion", "장 건강", "소화"),
    "bone_joint": ("bone", "joint", "뼈", "관절"),
    "heart_health": ("heart health", "cardiovascular", "심혈관", "심장 건강"),
    "blood_glucose": ("blood glucose", "blood sugar", "혈당"),
    "general_wellness": ("general wellness", "wellness", "전반적 건강"),
}
_INGREDIENT_ALIASES = {
    "omega3": ("오메가3", "오메가-3"),
    "vitamin_d3": ("비타민 d3", "비타민d3", "콜레칼시페롤"),
    "vitamin_c": ("비타민 c", "비타민c"),
    "magnesium_glycinate": ("마그네슘 글리시네이트", "마그네슘 비스글리시네이트"),
    "probiotics": ("프로바이오틱스", "유산균"),
    "zinc": ("아연",),
    "iron": ("철분",),
}
_MEDICATION_ALIASES = {"warfarin": ("와파린",), "coumadin": ("쿠마딘",)}
_CONDITION_ALIASES = {
    "kidney disease": ("kidney disease", "신장질환", "신장 질환", "콩팥병"),
    "kidney failure": ("kidney failure", "신부전",),
    "liver failure": ("liver failure", "간부전",),
    "cirrhosis": ("cirrhosis", "간경변",),
    "pregnancy": ("pregnancy", "pregnant", "임신",),
    "lactation": ("lactation", "breastfeeding", "수유",),
}
_URGENT_RISK_ALIASES = {
    "active_bleeding": (
        "active bleeding",
        "bleeding now",
        "출혈",
        "피가 멈추지",
        "피가 나",
        "피를 토",
    ),
    "chest_pain": ("chest pain", "chest pressure", "가슴 통증", "가슴 압박", "흉통"),
    "difficulty_breathing": (
        "difficulty breathing",
        "shortness of breath",
        "cannot breathe",
        "can't breathe",
        "호흡곤란",
        "숨이 차",
        "숨을 못 쉬",
    ),
    "anaphylaxis": (
        "anaphylaxis",
        "throat swelling",
        "아나필락시스",
        "목이 붓",
        "혀가 붓",
    ),
}


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
    as_of: datetime | None = None,
) -> list[RetrievalResult]:
    query_tokens = _tokenize(query)
    scored: list[tuple[float, RetrievalChunk]] = []
    for chunk in manifest.chunks:
        if as_of is not None:
            if as_of.tzinfo is None or as_of.utcoffset() is None:
                raise ValueError("retrieval_as_of_timezone_required")
            if chunk.effective_at > as_of:
                continue
            if chunk.retired_at is not None and chunk.retired_at <= as_of:
                continue
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


def retrieve_bounded_chunks(
    manifest: RetrievalCorpusManifest,
    *,
    scope: BoundedKnowledgeScope,
    query: str,
    as_of: datetime,
    top_k: int = 3,
) -> list[RetrievalResult]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("bounded_retrieval_as_of_timezone_required")
    if top_k < 1 or top_k > scope.max_results:
        raise ValueError("bounded_retrieval_top_k_outside_scope")
    allowed_sources = set(scope.allowed_source_types)
    allowed_claims = set(scope.allowed_claim_types)
    allowed_references = set(scope.allowed_reference_ids)
    scoped_chunks = [
        chunk
        for chunk in manifest.chunks
        if chunk.source_type in allowed_sources
        and chunk.normalized_claim_type in allowed_claims
        and chunk.reference_id in allowed_references
    ]
    scoped_manifest = RetrievalCorpusManifest(
        manifest_version=f"{manifest.manifest_version}::{scope.scope_id}",
        chunk_count=len(scoped_chunks),
        chunks=scoped_chunks,
    )
    return retrieve_relevant_chunks(
        scoped_manifest,
        query=query,
        top_k=top_k,
        as_of=as_of,
    )


def extract_question_entities(
    question: str,
    runtime_db: RuntimeKnowledgeDB,
) -> QuestionEntityExtraction:
    if not question.strip():
        raise ValueError("question_text_required")
    alias_records: list[tuple[QuestionEntityKind, str, str]] = []
    for key, aliases in _GOAL_ALIASES.items():
        alias_records.extend((QuestionEntityKind.HEALTH_GOAL, key, alias) for alias in aliases)
    ingredient_aliases: dict[str, set[str]] = {}
    for item in runtime_db.ingredient_aliases:
        ingredient_aliases.setdefault(item.ingredient_key, set()).update(
            {item.alias, item.ingredient_key.replace("_", " ")}
        )
    for key, aliases in _INGREDIENT_ALIASES.items():
        if key in ingredient_aliases:
            ingredient_aliases[key].update(aliases)
    for key, aliases in ingredient_aliases.items():
        alias_records.extend((QuestionEntityKind.INGREDIENT, key, alias) for alias in aliases)
    medication_keys = {item.medication_key for item in runtime_db.medications}
    for key in medication_keys:
        aliases = {key, *_MEDICATION_ALIASES.get(key, ())}
        alias_records.extend((QuestionEntityKind.MEDICATION, key, alias) for alias in aliases)
    condition_keys = {item.condition_key for item in runtime_db.conditions}
    for key in condition_keys:
        aliases = {key, *_CONDITION_ALIASES.get(key, ())}
        alias_records.extend((QuestionEntityKind.RISK_SIGNAL, key, alias) for alias in aliases)
    for key, aliases in _URGENT_RISK_ALIASES.items():
        alias_records.extend((QuestionEntityKind.RISK_SIGNAL, key, alias) for alias in aliases)

    matches: list[QuestionEntityMatch] = []
    occupied: set[tuple[QuestionEntityKind, int, int]] = set()
    for kind, key, alias in sorted(
        alias_records, key=lambda row: (-len(row[2]), row[0].value, row[1], row[2])
    ):
        if not alias.strip():
            continue
        escaped_alias = re.escape(alias)
        if re.fullmatch(r"[A-Za-z0-9 _-]+", alias):
            expression = rf"(?<!\w){escaped_alias}(?!\w)"
        else:
            expression = escaped_alias
        pattern = re.compile(expression, re.IGNORECASE)
        for found in pattern.finditer(question):
            identity = (kind, found.start(), found.end())
            if identity in occupied:
                continue
            occupied.add(identity)
            matches.append(
                QuestionEntityMatch(
                    kind=kind,
                    canonical_key=key,
                    matched_text=question[found.start() : found.end()],
                    start=found.start(),
                    end=found.end(),
                    negated=_is_negated(question, found.start(), found.end()),
                )
            )
    matches.sort(key=lambda item: (item.start, item.end, item.kind.value, item.canonical_key))
    values = {
        kind: sorted({match.canonical_key for match in matches if match.kind == kind})
        for kind in QuestionEntityKind
    }
    urgent_keys = set(_URGENT_RISK_ALIASES)
    return QuestionEntityExtraction(
        question=question,
        health_goals=values[QuestionEntityKind.HEALTH_GOAL],
        ingredient_keys=values[QuestionEntityKind.INGREDIENT],
        medication_keys=values[QuestionEntityKind.MEDICATION],
        risk_signal_keys=values[QuestionEntityKind.RISK_SIGNAL],
        urgent_risk_detected=any(
            match.kind == QuestionEntityKind.RISK_SIGNAL
            and match.canonical_key in urgent_keys
            and not match.negated
            for match in matches
        ),
        matches=matches,
    )


def _is_negated(question: str, start: int, end: int) -> bool:
    before = question[max(0, start - 32) : start].casefold()
    after = question[end : min(len(question), end + 32)].casefold()
    before_negation = re.search(
        r"(?:\bno\b|\bwithout\b|\bden(?:y|ies|ied)\b)\s+"
        r"(?:(?:current|any|active)\s+)?$",
        before,
    )
    after_negation = re.search(
        r"^\s*(?:(?:is|are|was|were)\s+)?"
        r"(?:absent|denied|negative|not\s+present)\b"
        r"|^\s*(?:은|는|이|가)?\s*(?:없(?:습니다|어요|다|음|고|지만)?|아닙니다)",
        after,
    )
    return before_negation is not None or after_negation is not None


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
