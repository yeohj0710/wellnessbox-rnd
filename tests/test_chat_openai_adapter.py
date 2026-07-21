from io import BytesIO
from urllib import error

from wellnessbox_rnd.chat.openai_adapter import (
    CHAT_OPENAI_BASE_URL_ENV_VAR,
    CHAT_OPENAI_MODEL_ENV_VAR,
    CHAT_OPENAI_TIMEOUT_ENV_VAR,
    OPENAI_API_KEY_ENV_VAR,
    ChatAdapterRequest,
    generate_chat_answer_with_openai_fallback,
    load_openai_chat_adapter_config_from_env,
)
from wellnessbox_rnd.chat.retrieval import RetrievalChunk, RetrievalCorpusManifest


def _build_manifest() -> RetrievalCorpusManifest:
    return RetrievalCorpusManifest(
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


def test_openai_adapter_uses_deterministic_fallback_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    manifest = _build_manifest()
    adapter_request = ChatAdapterRequest(
        query="What should counseling say about glucosamine with warfarin?",
        answer_template_key="interaction_warning",
        expected_reference_ids=["REF-KNOWLEDGE-ANTICOAG-001"],
        expected_claim_ids=["CLM-KNOWLEDGE-ANTICOAG-001"],
        expected_terms=["glucosamine", "warfarin"],
    )

    response = generate_chat_answer_with_openai_fallback(
        manifest,
        adapter_request,
        allow_live_api=True,
    )

    assert response.provider == "deterministic_template_fallback"
    assert response.fallback_reason == "missing_api_key"
    assert response.verification.passed is True


def test_openai_adapter_returns_mocked_verified_answer(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    manifest = _build_manifest()
    adapter_request = ChatAdapterRequest(
        query="What should counseling say about glucosamine with warfarin?",
        answer_template_key="interaction_warning",
        expected_reference_ids=["REF-KNOWLEDGE-ANTICOAG-001"],
        expected_claim_ids=["CLM-KNOWLEDGE-ANTICOAG-001"],
        expected_terms=["glucosamine", "warfarin"],
    )

    def _mock_call_openai_responses_api(**_kwargs) -> dict[str, object]:
        return {
            "output_text": (
                '{"status":"supported","answer_text":"Glucosamine with warfarin '
                'should be treated as a drug interaction.","used_chunk_ids":'
                '["chunk::CLM-KNOWLEDGE-ANTICOAG-001"]}'
            )
        }

    monkeypatch.setattr(
        "wellnessbox_rnd.chat.openai_adapter._call_openai_responses_api",
        _mock_call_openai_responses_api,
    )

    response = generate_chat_answer_with_openai_fallback(
        manifest,
        adapter_request,
        allow_live_api=True,
    )

    assert response.provider == "openai_responses_api"
    assert response.verification.passed is True
    assert response.answer.citations[0].reference_id == "REF-KNOWLEDGE-ANTICOAG-001"


def test_openai_adapter_falls_back_when_mocked_answer_fails_verification(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    manifest = _build_manifest()
    adapter_request = ChatAdapterRequest(
        query="What should counseling say about glucosamine with warfarin?",
        answer_template_key="interaction_warning",
        expected_reference_ids=["REF-KNOWLEDGE-ANTICOAG-001"],
        expected_claim_ids=["CLM-KNOWLEDGE-ANTICOAG-001"],
        expected_terms=["glucosamine", "warfarin"],
    )

    def _mock_call_openai_responses_api(**_kwargs) -> dict[str, object]:
        return {
            "output_text": (
                '{"status":"supported","answer_text":"Unsupported freeform text.",'
                '"used_chunk_ids":[]}'
            )
        }

    monkeypatch.setattr(
        "wellnessbox_rnd.chat.openai_adapter._call_openai_responses_api",
        _mock_call_openai_responses_api,
    )

    response = generate_chat_answer_with_openai_fallback(
        manifest,
        adapter_request,
        allow_live_api=True,
    )

    assert response.provider == "deterministic_template_fallback"
    assert response.fallback_reason == "openai_call_failed"
    assert response.verification.passed is True
    assert response.live_failure is not None
    assert response.live_failure.failure_stage == "response_parse"
    assert response.live_failure.exception_class == "ValueError"


def test_openai_adapter_captures_http_error_details(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    manifest = _build_manifest()
    adapter_request = ChatAdapterRequest(
        query="What should counseling say about glucosamine with warfarin?",
        answer_template_key="interaction_warning",
        expected_reference_ids=["REF-KNOWLEDGE-ANTICOAG-001"],
        expected_claim_ids=["CLM-KNOWLEDGE-ANTICOAG-001"],
        expected_terms=["glucosamine", "warfarin"],
    )

    def _mock_call_openai_responses_api(**_kwargs) -> dict[str, object]:
        raise error.HTTPError(
            url="https://api.openai.com/v1/responses",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":{"message":"bad api key"}}'),
        )

    monkeypatch.setattr(
        "wellnessbox_rnd.chat.openai_adapter._call_openai_responses_api",
        _mock_call_openai_responses_api,
    )

    response = generate_chat_answer_with_openai_fallback(
        manifest,
        adapter_request,
        allow_live_api=True,
    )

    assert response.provider == "deterministic_template_fallback"
    assert response.fallback_reason == "openai_call_failed"
    assert response.live_failure is not None
    assert response.live_failure.failure_stage == "http_request"
    assert response.live_failure.exception_class == "HTTPError"
    assert response.live_failure.status_code == 401
    assert "bad api key" in (response.live_failure.response_body_excerpt or "")


def test_openai_adapter_config_uses_defaults_and_missing_key_state(monkeypatch) -> None:
    monkeypatch.delenv(OPENAI_API_KEY_ENV_VAR, raising=False)
    monkeypatch.delenv(CHAT_OPENAI_MODEL_ENV_VAR, raising=False)
    monkeypatch.delenv(CHAT_OPENAI_BASE_URL_ENV_VAR, raising=False)
    monkeypatch.setenv(CHAT_OPENAI_TIMEOUT_ENV_VAR, "not-a-float")

    config = load_openai_chat_adapter_config_from_env()

    assert config.api_key_present is False
    assert config.model == "gpt-5-mini"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.timeout_seconds == 20.0
