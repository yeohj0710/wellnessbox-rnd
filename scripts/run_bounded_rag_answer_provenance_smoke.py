from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_chat_retrieval_assets import (  # noqa: E402
    _build_chunk_from_claim,
    _load_claim_rows,
    _load_reference_rows,
)
from wellnessbox_rnd.chat.answering import (  # noqa: E402
    generate_bounded_template_answer,
    verify_bounded_template_answer,
)
from wellnessbox_rnd.chat.retrieval import (  # noqa: E402
    BoundedKnowledgeScope,
    RetrievalCorpusManifest,
    load_approved_counseling_scope,
    retrieve_bounded_chunks,
)

DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/"
    "op083_op084_bounded_rag_answer_provenance_smoke_v1.json"
)
CLAIMS_PATH = ROOT / "data/parsed_references/reference_claims_v1.jsonl"
REFERENCES_PATH = ROOT / "data/knowledge/reference_knowledge_base_v1.json"
SCOPE_REGISTRY_PATH = ROOT / "data/knowledge/counseling_knowledge_scope_registry_v1.json"
AS_OF = datetime(2026, 7, 21, 13, 0, tzinfo=UTC)
SOURCE_PATHS = (
    "scripts/build_chat_retrieval_assets.py",
    "scripts/run_bounded_rag_answer_provenance_smoke.py",
    "scripts/run_chat_openai_adapter_smoke.py",
    "scripts/run_chat_template_answer_eval.py",
    "src/wellnessbox_rnd/chat/__init__.py",
    "src/wellnessbox_rnd/chat/answering.py",
    "src/wellnessbox_rnd/chat/openai_adapter.py",
    "src/wellnessbox_rnd/chat/retrieval.py",
    "src/wellnessbox_rnd/chat/verifier.py",
    "src/wellnessbox_rnd/evals/learned_runtime_boundary_audit.py",
    "tests/test_chat_openai_adapter.py",
    "tests/test_chat_retrieval.py",
    "tests/test_learned_runtime_boundary_audit.py",
)
DATA_PATHS = (
    "data/knowledge/counseling_answer_verifier_policy_v1.json",
    "data/knowledge/counseling_knowledge_scope_registry_v1.json",
    "data/knowledge/reference_knowledge_base_v1.json",
    "data/parsed_references/reference_claims_v1.jsonl",
)


def _hash_paths(paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((ROOT / relative).read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _last_commit(paths: tuple[str, ...]) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _build_scope(manifest: RetrievalCorpusManifest) -> BoundedKnowledgeScope:
    del manifest
    return load_approved_counseling_scope()


def _answer_case(
    manifest: RetrievalCorpusManifest,
    scope: BoundedKnowledgeScope,
    *,
    case_id: str,
    query: str,
    expected_status: str,
    answer_template_key: str | None = None,
) -> dict[str, object]:
    answer = generate_bounded_template_answer(
        manifest,
        query=query,
        scope=scope,
        as_of=AS_OF,
        answer_template_key=answer_template_key,
    )
    verification = verify_bounded_template_answer(
        answer,
        manifest=manifest,
        scope=scope,
        as_of=AS_OF,
        expected_status=expected_status,
    )
    if not verification.passed:
        raise RuntimeError(f"answer_case_failed::{case_id}::{verification.issues}")
    return {
        "case_id": case_id,
        "query": query,
        "status": answer.status,
        "knowledge_scope_id": answer.knowledge_scope_id,
        "answered_at": answer.answered_at.isoformat(),
        "used_chunk_ids": answer.used_chunk_ids,
        "citation_reference_ids": [item.reference_id for item in answer.citations],
        "citation_claim_ids": [item.claim_id for item in answer.citations],
        "citation_effective_dates": [
            item.effective_at.isoformat() for item in answer.citations
        ],
        "all_citations_active_at_answer_time": all(
            item.active_at_answer_time for item in answer.citations
        ),
        "uncertainty": answer.uncertainty.model_dump(mode="json"),
        "verification": verification.model_dump(mode="json"),
    }


def _build() -> dict[str, object]:
    claims = _load_claim_rows(CLAIMS_PATH)
    references = _load_reference_rows(REFERENCES_PATH)
    chunks = [_build_chunk_from_claim(claim, references) for claim in claims]
    manifest = RetrievalCorpusManifest(
        manifest_version="op083_op084_bounded_rag_manifest_v1",
        chunk_count=len(chunks),
        chunks=chunks,
    )
    scope = _build_scope(manifest)
    cases = [
        _answer_case(
            manifest,
            scope,
            case_id="supported_interaction",
            query="What should counseling say about glucosamine with warfarin?",
            expected_status="supported",
            answer_template_key="interaction_warning",
        ),
        _answer_case(
            manifest,
            scope,
            case_id="mixed_evidence_uncertainty",
            query="What does the evidence say about magnesium and insomnia?",
            expected_status="supported",
        ),
        _answer_case(
            manifest,
            scope,
            case_id="unsupported_cure_claim",
            query="Does glucosamine cure diabetes?",
            expected_status="unsupported",
            answer_template_key="interaction_warning",
        ),
        _answer_case(
            manifest,
            scope,
            case_id="out_of_scope_weather",
            query="Explain a quadratic topology theorem.",
            expected_status="out_of_scope",
        ),
    ]
    if cases[1]["uncertainty"]["level"] != "moderate":
        raise RuntimeError("mixed_evidence_uncertainty_not_preserved")

    base = chunks[0]
    disallowed = base.model_copy(
        update={
            "chunk_id": "chunk::DISALLOWED-SOURCE",
            "claim_id": "CLM-DISALLOWED-SOURCE",
            "source_type": "unreviewed_external_blog",
            "text": "glucosamine warfarin interaction",
        }
    )
    disallowed_reference = base.model_copy(
        update={
            "chunk_id": "chunk::DISALLOWED-REFERENCE",
            "reference_id": "REF-DISALLOWED-REFERENCE",
            "claim_id": "CLM-DISALLOWED-REFERENCE",
            "text": "glucosamine warfarin interaction",
        }
    )
    disallowed_claim = base.model_copy(
        update={
            "chunk_id": "chunk::DISALLOWED-CLAIM",
            "claim_id": "CLM-DISALLOWED-CLAIM",
            "normalized_claim_type": "unreviewed_claim",
            "text": "glucosamine warfarin interaction",
        }
    )
    expanded = RetrievalCorpusManifest(
        manifest_version="scope-negative-probe",
        chunk_count=len(chunks) + 3,
        chunks=[*chunks, disallowed, disallowed_reference, disallowed_claim],
    )
    bounded_ids = {
        result.chunk_id
        for result in retrieve_bounded_chunks(
            expanded,
            scope=scope,
            query="glucosamine warfarin interaction",
            as_of=AS_OF,
            top_k=5,
        )
    }
    disallowed_source_blocked = disallowed.chunk_id not in bounded_ids
    disallowed_reference_blocked = disallowed_reference.chunk_id not in bounded_ids
    disallowed_claim_blocked = disallowed_claim.chunk_id not in bounded_ids
    if not all(
        [
            disallowed_source_blocked,
            disallowed_reference_blocked,
            disallowed_claim_blocked,
        ]
    ):
        raise RuntimeError("disallowed_scope_axis_entered_bounded_retrieval")

    forged_scope = scope.model_copy(
        update={
            "allowed_source_types": [*scope.allowed_source_types, "unreviewed_external_blog"],
            "allowed_claim_types": [*scope.allowed_claim_types, "unreviewed_claim"],
            "allowed_reference_ids": [
                *scope.allowed_reference_ids,
                "REF-DISALLOWED-REFERENCE",
            ],
        }
    )
    forged_scope_blocked = False
    try:
        retrieve_bounded_chunks(
            expanded,
            scope=forged_scope,
            query="glucosamine warfarin interaction",
            as_of=AS_OF,
        )
    except ValueError as exc:
        forged_scope_blocked = "content_not_repository_approved" in str(exc)
    if not forged_scope_blocked:
        raise RuntimeError("forged_repository_scope_not_blocked")

    retired = base.model_copy(
        update={
            "chunk_id": "chunk::RETIRED-PASSAGE",
            "claim_id": "CLM-RETIRED-PASSAGE",
            "retired_at": datetime(2026, 7, 1, tzinfo=UTC),
        }
    )
    retired_scope = scope.model_copy(
        update={"allowed_reference_ids": sorted({*scope.allowed_reference_ids})}
    )
    retired_manifest = RetrievalCorpusManifest(
        manifest_version="retired-negative-probe", chunk_count=1, chunks=[retired]
    )
    retired_passage_blocked = not retrieve_bounded_chunks(
        retired_manifest,
        scope=retired_scope,
        query=retired.text,
        as_of=AS_OF,
    )
    if not retired_passage_blocked:
        raise RuntimeError("retired_passage_entered_bounded_retrieval")

    future = base.model_copy(
        update={
            "chunk_id": "chunk::FUTURE-PASSAGE",
            "claim_id": "CLM-FUTURE-PASSAGE",
            "effective_at": datetime(2026, 8, 1, tzinfo=UTC),
        }
    )
    future_manifest = RetrievalCorpusManifest(
        manifest_version="future-negative-probe", chunk_count=1, chunks=[future]
    )
    future_passage_blocked = not retrieve_bounded_chunks(
        future_manifest,
        scope=scope,
        query=future.text,
        as_of=AS_OF,
    )
    if not future_passage_blocked:
        raise RuntimeError("future_passage_entered_bounded_retrieval")

    supported = generate_bounded_template_answer(
        manifest,
        query="glucosamine with warfarin",
        scope=scope,
        as_of=AS_OF,
        answer_template_key="interaction_warning",
    )
    forged = supported.model_copy(
        update={
            "citations": [
                supported.citations[0].model_copy(update={"active_at_answer_time": False})
            ]
        }
    )
    forged_verification = verify_bounded_template_answer(
        forged, manifest=manifest, scope=scope, as_of=AS_OF
    )
    tampered_validity_blocked = (
        not forged_verification.passed
        and "answer_evidence_validity_mismatch" in forged_verification.issues
    )
    if not tampered_validity_blocked:
        raise RuntimeError("tampered_answer_validity_not_blocked")

    duplicate_ids = supported.model_copy(
        update={
            "used_chunk_ids": [
                supported.used_chunk_ids[0],
                supported.used_chunk_ids[0],
            ]
        }
    )
    duplicate_verification = verify_bounded_template_answer(
        duplicate_ids, manifest=manifest, scope=scope, as_of=AS_OF
    )
    duplicate_provenance_blocked = not duplicate_verification.passed
    if not duplicate_provenance_blocked:
        raise RuntimeError("duplicate_provenance_not_blocked")

    return {
        "schema_version": "op083_op084_bounded_rag_answer_provenance_smoke_v1",
        "generated_from": {
            "claims_path": str(CLAIMS_PATH.relative_to(ROOT)).replace("\\", "/"),
            "references_path": str(REFERENCES_PATH.relative_to(ROOT)).replace("\\", "/"),
            "scope_registry_path": str(SCOPE_REGISTRY_PATH.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "as_of": AS_OF.isoformat(),
        },
        "knowledge_scope": scope.model_dump(mode="json"),
        "corpus": {
            "passage_count": len(chunks),
            "source_count": len(scope.allowed_reference_ids),
        },
        "answer_cases": cases,
        "negative_probes": {
            "disallowed_source_blocked": disallowed_source_blocked,
            "disallowed_reference_blocked": disallowed_reference_blocked,
            "disallowed_claim_type_blocked": disallowed_claim_blocked,
            "forged_repository_scope_blocked": forged_scope_blocked,
            "retired_passage_blocked": retired_passage_blocked,
            "future_passage_blocked": future_passage_blocked,
            "tampered_validity_blocked": tampered_validity_blocked,
            "duplicate_provenance_blocked": duplicate_provenance_blocked,
        },
        "stage_boundaries": {
            "claimed_stage": "IMPLEMENTED",
            "wellnessbox_service_integration_proven": False,
            "deployment_proven": False,
            "production_operation_proven": False,
            "external_validation_proven": False,
            "live_llm_inference_used": False,
        },
        "source_identity": {
            "source_commit": _last_commit(SOURCE_PATHS),
            "source_sha256": _hash_paths(SOURCE_PATHS),
            "data_sha256": _hash_paths(DATA_PATHS),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = _build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
