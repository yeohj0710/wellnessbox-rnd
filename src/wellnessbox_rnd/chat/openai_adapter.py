from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Literal
from urllib import error, request

from pydantic import BaseModel, Field

from wellnessbox_rnd.chat.answering import (
    ChatAnswerVerification,
    ChatTemplateAnswer,
    _build_citation,
    _build_uncertainty,
    _render_template_answer,
    generate_bounded_template_answer,
    verify_bounded_template_answer,
)
from wellnessbox_rnd.chat.retrieval import (
    BoundedKnowledgeScope,
    RetrievalChunk,
    RetrievalCorpusManifest,
    retrieve_bounded_chunks,
)

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
CHAT_OPENAI_MODEL_ENV_VAR = "WELLNESSBOX_CHAT_OPENAI_MODEL"
CHAT_OPENAI_BASE_URL_ENV_VAR = "WELLNESSBOX_CHAT_OPENAI_BASE_URL"
CHAT_OPENAI_TIMEOUT_ENV_VAR = "WELLNESSBOX_CHAT_OPENAI_TIMEOUT_SECONDS"

DEFAULT_CHAT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_CHAT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_CHAT_OPENAI_TIMEOUT_SECONDS = 20.0


class ChatAdapterRequest(BaseModel):
    query: str
    knowledge_scope: BoundedKnowledgeScope
    as_of: datetime
    answer_template_key: str | None = None
    expected_reference_ids: list[str] = Field(default_factory=list)
    expected_claim_ids: list[str] = Field(default_factory=list)
    expected_terms: list[str] = Field(default_factory=list)
    top_k: int = 3
    min_score: float = 2.0


class OpenAIChatAdapterConfig(BaseModel):
    api_key_env_var: str = OPENAI_API_KEY_ENV_VAR
    model_env_var: str = CHAT_OPENAI_MODEL_ENV_VAR
    base_url_env_var: str = CHAT_OPENAI_BASE_URL_ENV_VAR
    timeout_env_var: str = CHAT_OPENAI_TIMEOUT_ENV_VAR
    api_key_present: bool
    model: str = DEFAULT_CHAT_OPENAI_MODEL
    base_url: str = DEFAULT_CHAT_OPENAI_BASE_URL
    timeout_seconds: float = DEFAULT_CHAT_OPENAI_TIMEOUT_SECONDS


class ChatAdapterLiveFailure(BaseModel):
    failure_stage: Literal["http_request", "response_parse"]
    exception_class: str
    exception_message: str
    status_code: int | None = None
    response_body_excerpt: str | None = None


class ChatAdapterResponse(BaseModel):
    provider: Literal["openai_responses_api", "deterministic_template_fallback"]
    fallback_reason: str | None = None
    attempted_live_call: bool = False
    model: str | None = None
    answer: ChatTemplateAnswer
    verification: ChatAnswerVerification
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    evidence_reference_ids: list[str] = Field(default_factory=list)
    live_failure: ChatAdapterLiveFailure | None = None


def load_openai_chat_adapter_config_from_env() -> OpenAIChatAdapterConfig:
    api_key = os.getenv(OPENAI_API_KEY_ENV_VAR, "").strip()
    model = os.getenv(CHAT_OPENAI_MODEL_ENV_VAR, DEFAULT_CHAT_OPENAI_MODEL).strip()
    base_url = os.getenv(CHAT_OPENAI_BASE_URL_ENV_VAR, DEFAULT_CHAT_OPENAI_BASE_URL).strip()
    timeout_raw = os.getenv(
        CHAT_OPENAI_TIMEOUT_ENV_VAR,
        str(DEFAULT_CHAT_OPENAI_TIMEOUT_SECONDS),
    ).strip()
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = DEFAULT_CHAT_OPENAI_TIMEOUT_SECONDS
    return OpenAIChatAdapterConfig(
        api_key_present=bool(api_key),
        model=model or DEFAULT_CHAT_OPENAI_MODEL,
        base_url=base_url or DEFAULT_CHAT_OPENAI_BASE_URL,
        timeout_seconds=timeout_seconds,
    )


def generate_chat_answer_with_openai_fallback(
    manifest: RetrievalCorpusManifest,
    adapter_request: ChatAdapterRequest,
    *,
    allow_live_api: bool = False,
) -> ChatAdapterResponse:
    config = load_openai_chat_adapter_config_from_env()
    fallback = _build_deterministic_fallback(manifest, adapter_request)
    if fallback.answer.status == "safety_escalation":
        return ChatAdapterResponse(
            provider="deterministic_template_fallback",
            fallback_reason="urgent_safety_precedence",
            attempted_live_call=False,
            model=None,
            answer=fallback.answer,
            verification=fallback.verification,
        )
    evidence_results = retrieve_bounded_chunks(
        manifest,
        scope=adapter_request.knowledge_scope,
        query=adapter_request.query,
        top_k=adapter_request.top_k,
        as_of=adapter_request.as_of,
    )
    evidence_chunks = [
        next(chunk for chunk in manifest.chunks if chunk.chunk_id == result.chunk_id)
        for result in evidence_results
    ]
    evidence_chunk_ids = [chunk.chunk_id for chunk in evidence_chunks]
    evidence_reference_ids = [chunk.reference_id for chunk in evidence_chunks]

    if not allow_live_api:
        return ChatAdapterResponse(
            provider="deterministic_template_fallback",
            fallback_reason="live_api_disabled",
            attempted_live_call=False,
            model=config.model,
            answer=fallback.answer,
            verification=fallback.verification,
            evidence_chunk_ids=evidence_chunk_ids,
            evidence_reference_ids=evidence_reference_ids,
        )

    if not config.api_key_present:
        return ChatAdapterResponse(
            provider="deterministic_template_fallback",
            fallback_reason="missing_api_key",
            attempted_live_call=False,
            model=config.model,
            answer=fallback.answer,
            verification=fallback.verification,
            evidence_chunk_ids=evidence_chunk_ids,
            evidence_reference_ids=evidence_reference_ids,
        )

    try:
        response_json = _call_openai_responses_api(
            config=config,
            adapter_request=adapter_request,
            evidence_chunks=evidence_chunks,
        )
    except error.HTTPError as exc:
        return ChatAdapterResponse(
            provider="deterministic_template_fallback",
            fallback_reason="openai_call_failed",
            attempted_live_call=True,
            model=config.model,
            answer=fallback.answer,
            verification=fallback.verification,
            evidence_chunk_ids=evidence_chunk_ids,
            evidence_reference_ids=evidence_reference_ids,
            live_failure=_build_live_failure_details("http_request", exc),
        )
    except (error.URLError, TimeoutError) as exc:
        return ChatAdapterResponse(
            provider="deterministic_template_fallback",
            fallback_reason="openai_call_failed",
            attempted_live_call=True,
            model=config.model,
            answer=fallback.answer,
            verification=fallback.verification,
            evidence_chunk_ids=evidence_chunk_ids,
            evidence_reference_ids=evidence_reference_ids,
            live_failure=_build_live_failure_details("http_request", exc),
        )
    try:
        answer = _parse_openai_answer(
            response_json=response_json,
            evidence_chunks=evidence_chunks,
            adapter_request=adapter_request,
        )
        verification = verify_bounded_template_answer(
            answer,
            manifest=manifest,
            scope=adapter_request.knowledge_scope,
            as_of=adapter_request.as_of,
            expected_reference_ids=adapter_request.expected_reference_ids,
            expected_claim_ids=adapter_request.expected_claim_ids,
            expected_terms=adapter_request.expected_terms,
        )
        if not verification.passed:
            return ChatAdapterResponse(
                provider="deterministic_template_fallback",
                fallback_reason="verification_failed",
                attempted_live_call=True,
                model=config.model,
                answer=fallback.answer,
                verification=fallback.verification,
                evidence_chunk_ids=evidence_chunk_ids,
                evidence_reference_ids=evidence_reference_ids,
            )
        return ChatAdapterResponse(
            provider="openai_responses_api",
            attempted_live_call=True,
            model=config.model,
            answer=answer,
            verification=verification,
            evidence_chunk_ids=evidence_chunk_ids,
            evidence_reference_ids=evidence_reference_ids,
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return ChatAdapterResponse(
            provider="deterministic_template_fallback",
            fallback_reason="openai_call_failed",
            attempted_live_call=True,
            model=config.model,
            answer=fallback.answer,
            verification=fallback.verification,
            evidence_chunk_ids=evidence_chunk_ids,
            evidence_reference_ids=evidence_reference_ids,
            live_failure=_build_live_failure_details("response_parse", exc),
        )


def _build_deterministic_fallback(
    manifest: RetrievalCorpusManifest,
    adapter_request: ChatAdapterRequest,
) -> ChatAdapterResponse:
    answer = generate_bounded_template_answer(
        manifest,
        query=adapter_request.query,
        scope=adapter_request.knowledge_scope,
        as_of=adapter_request.as_of,
        answer_template_key=adapter_request.answer_template_key,
        top_k=adapter_request.top_k,
        min_score=adapter_request.min_score,
    )
    verification = verify_bounded_template_answer(
        answer,
        manifest=manifest,
        scope=adapter_request.knowledge_scope,
        as_of=adapter_request.as_of,
        expected_reference_ids=adapter_request.expected_reference_ids,
        expected_claim_ids=adapter_request.expected_claim_ids,
        expected_terms=adapter_request.expected_terms,
    )
    return ChatAdapterResponse(
        provider="deterministic_template_fallback",
        answer=answer,
        verification=verification,
    )


def _call_openai_responses_api(
    *,
    config: OpenAIChatAdapterConfig,
    adapter_request: ChatAdapterRequest,
    evidence_chunks: list[RetrievalChunk],
) -> dict[str, object]:
    api_key = os.getenv(OPENAI_API_KEY_ENV_VAR, "").strip()
    evidence_block = "\n\n".join(
        [
            (
                f"chunk_id: {chunk.chunk_id}\n"
                f"reference_id: {chunk.reference_id}\n"
                f"claim_id: {chunk.claim_id}\n"
                f"text: {chunk.text}\n"
                f"excerpt: {chunk.excerpt}"
            )
            for chunk in evidence_chunks
        ]
    )
    payload = {
        "model": config.model,
        "input": (
            "You are a bounded counseling answer generator. Use only the provided evidence chunks. "
            "Never invent unsupported claims. If the query is out of scope, return out_of_scope. "
            "If the query is in scope but unsupported by the provided evidence, "
            "return unsupported. "
            "If supported, return supported and only cite chunk_ids from the evidence list.\n\n"
            f"answer_template_key: {adapter_request.answer_template_key or 'auto'}\n"
            f"query: {adapter_request.query}\n\n"
            f"evidence:\n{evidence_block}"
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bounded_chat_answer",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["supported", "unsupported", "out_of_scope"],
                        },
                        "used_chunk_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["status", "used_chunk_ids"],
                },
            }
        },
    }
    http_request = request.Request(
        f"{config.base_url.rstrip('/')}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(http_request, timeout=config.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_openai_answer(
    *,
    response_json: dict[str, object],
    evidence_chunks: list[RetrievalChunk],
    adapter_request: ChatAdapterRequest,
) -> ChatTemplateAnswer:
    output_text = response_json.get("output_text")
    if not isinstance(output_text, str):
        raise ValueError("missing_output_text")
    payload = json.loads(output_text)
    status = payload["status"]
    used_chunk_ids = payload["used_chunk_ids"]
    if status not in {"supported", "unsupported", "out_of_scope"}:
        raise ValueError("invalid_status")
    if not isinstance(used_chunk_ids, list) or any(
        not isinstance(chunk_id, str) for chunk_id in used_chunk_ids
    ):
        raise ValueError("invalid_used_chunk_ids")
    if len(used_chunk_ids) != len(set(used_chunk_ids)):
        raise ValueError("duplicate_used_chunk_ids")
    allowed_chunks = {chunk.chunk_id: chunk for chunk in evidence_chunks}
    if any(chunk_id not in allowed_chunks for chunk_id in used_chunk_ids):
        raise ValueError("unapproved_used_chunk_id")
    valid_chunk_ids = list(used_chunk_ids)
    citations = []
    if status == "supported":
        if len(valid_chunk_ids) != 1:
            raise ValueError("supported_without_evidence")
        citations = [
            _build_citation(allowed_chunks[chunk_id], as_of=adapter_request.as_of).model_dump()
            for chunk_id in valid_chunk_ids
        ]
        selected_chunk = allowed_chunks[valid_chunk_ids[0]]
        template_key = adapter_request.answer_template_key or "evidence_summary"
        answer_text = _render_template_answer(template_key, selected_chunk)
    elif valid_chunk_ids:
        raise ValueError("non_supported_answer_must_not_use_evidence")
    elif status == "unsupported":
        answer_text = (
            "I do not have citation-backed evidence in the local counseling corpus "
            "to support that claim, so I cannot state it as true."
        )
    else:
        answer_text = (
            "I do not have in-scope evidence for that counseling question. "
            "I can only answer bounded supplement counseling questions "
            "grounded in local references."
        )
    return ChatTemplateAnswer(
        query=adapter_request.query,
        status=status,
        answer_template_key=adapter_request.answer_template_key
        or ("unsupported" if status == "unsupported" else "out_of_scope"),
        answer_text=answer_text,
        citations=citations,
        used_chunk_ids=valid_chunk_ids,
        evidence_only=True,
        rationale="openai_responses_api",
        knowledge_scope_id=adapter_request.knowledge_scope.scope_id,
        answered_at=adapter_request.as_of,
        uncertainty=_build_uncertainty(
            status=status,
            chunks=[allowed_chunks[chunk_id] for chunk_id in valid_chunk_ids],
        ),
    )


def _build_live_failure_details(
    failure_stage: Literal["http_request", "response_parse"],
    exc: Exception,
) -> ChatAdapterLiveFailure:
    status_code = getattr(exc, "code", None)
    response_body_excerpt = None
    if isinstance(exc, error.HTTPError):
        try:
            response_body_excerpt = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            response_body_excerpt = None
    return ChatAdapterLiveFailure(
        failure_stage=failure_stage,
        exception_class=exc.__class__.__name__,
        exception_message=str(exc)[:300],
        status_code=status_code if isinstance(status_code, int) else None,
        response_body_excerpt=response_body_excerpt,
    )


__all__ = [
    "CHAT_OPENAI_BASE_URL_ENV_VAR",
    "CHAT_OPENAI_MODEL_ENV_VAR",
    "CHAT_OPENAI_TIMEOUT_ENV_VAR",
    "DEFAULT_CHAT_OPENAI_BASE_URL",
    "DEFAULT_CHAT_OPENAI_MODEL",
    "DEFAULT_CHAT_OPENAI_TIMEOUT_SECONDS",
    "OPENAI_API_KEY_ENV_VAR",
    "ChatAdapterRequest",
    "ChatAdapterResponse",
    "ChatAdapterLiveFailure",
    "OpenAIChatAdapterConfig",
    "generate_chat_answer_with_openai_fallback",
    "load_openai_chat_adapter_config_from_env",
]
