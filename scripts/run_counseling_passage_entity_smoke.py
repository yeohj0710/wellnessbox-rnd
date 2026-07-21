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
from wellnessbox_rnd.chat.retrieval import (  # noqa: E402
    RetrievalCorpusManifest,
    extract_question_entities,
    retrieve_relevant_chunks,
)
from wellnessbox_rnd.knowledge.runtime_db import load_runtime_knowledge_db  # noqa: E402

DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/"
    "op081_op082_counseling_passage_entity_smoke_v1.json"
)
CLAIMS_PATH = ROOT / "data/parsed_references/reference_claims_v1.jsonl"
REFERENCES_PATH = ROOT / "data/knowledge/reference_knowledge_base_v1.json"
RUNTIME_DB_PATH = ROOT / "data/knowledge/runtime_knowledge_db_v1.json"
SOURCE_PATHS = (
    "scripts/build_chat_retrieval_assets.py",
    "scripts/run_counseling_passage_entity_smoke.py",
    "src/wellnessbox_rnd/chat/__init__.py",
    "src/wellnessbox_rnd/chat/retrieval.py",
    "src/wellnessbox_rnd/knowledge/runtime_db.py",
    "src/wellnessbox_rnd/evals/learned_runtime_boundary_audit.py",
    "tests/test_chat_retrieval.py",
    "tests/test_chat_openai_adapter.py",
    "tests/test_learned_runtime_boundary_audit.py",
)
DATA_PATHS = (
    "data/knowledge/reference_knowledge_base_v1.json",
    "data/knowledge/runtime_knowledge_db_v1.json",
    "data/parsed_references/reference_claims_v1.jsonl",
)
AS_OF = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
QUESTIONS = (
    "수면과 혈당이 걱정됩니다. 오메가3를 와파린과 먹는데 지금 출혈이 있어요.",
    "Can I use glucosamine with Coumadin for joint health?",
    "신장 질환이 있는데 비타민D3와 마그네슘 글리시네이트를 같이 먹어도 되나요?",
    "I have chest pain and difficulty breathing after taking zinc.",
    "프로바이오틱스가 장 건강과 전반적 건강에 도움이 되나요?",
    "흉통은 없습니다.",
    "No bleeding, but I have chest pain.",
    "숨이 차고 혀가 붓습니다.",
    "The zincography article is unrelated to supplements.",
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


def _build() -> dict[str, object]:
    claims = _load_claim_rows(CLAIMS_PATH)
    references = _load_reference_rows(REFERENCES_PATH)
    chunks = [_build_chunk_from_claim(claim, references) for claim in claims]
    manifest = RetrievalCorpusManifest(
        manifest_version="op081_counseling_passage_manifest_v1",
        chunk_count=len(chunks),
        chunks=chunks,
    )
    active_results = [
        result.chunk_id
        for result in retrieve_relevant_chunks(
            manifest,
            query="glucosamine warfarin bleeding risk",
            top_k=3,
            as_of=AS_OF,
        )
    ]
    if not active_results:
        raise RuntimeError("dated_passage_retrieval_empty")
    if not all(
        chunk.license_status
        and chunk.effective_at.tzinfo is not None
        and chunk.line_end >= chunk.line_start
        for chunk in chunks
    ):
        raise RuntimeError("passage_lineage_incomplete")

    runtime_db = load_runtime_knowledge_db()
    entity_cases = [
        extract_question_entities(question, runtime_db).model_dump(mode="json")
        for question in QUESTIONS
    ]
    first = entity_cases[0]
    if first["ingredient_keys"] != ["omega3"] or first["medication_keys"] != [
        "warfarin"
    ]:
        raise RuntimeError("korean_entity_contract_failed")
    if first["urgent_risk_detected"] is not True:
        raise RuntimeError("urgent_risk_signal_not_detected")
    if entity_cases[5]["urgent_risk_detected"] is not False:
        raise RuntimeError("negated_urgent_signal_escalated")
    if entity_cases[6]["urgent_risk_detected"] is not True:
        raise RuntimeError("contrast_clause_urgent_signal_suppressed")
    if entity_cases[7]["urgent_risk_detected"] is not True:
        raise RuntimeError("korean_urgent_variant_not_detected")
    if entity_cases[-1]["ingredient_keys"]:
        raise RuntimeError("entity_substring_false_positive")

    reference_ids = {chunk.reference_id for chunk in chunks}
    retired_count = sum(chunk.retired_at is not None for chunk in chunks)
    return {
        "schema_version": "op081_op082_counseling_passage_entity_smoke_v1",
        "generated_from": {
            "claims_path": str(CLAIMS_PATH.relative_to(ROOT)).replace("\\", "/"),
            "references_path": str(REFERENCES_PATH.relative_to(ROOT)).replace("\\", "/"),
            "runtime_db_path": str(RUNTIME_DB_PATH.relative_to(ROOT)).replace("\\", "/"),
            "as_of": AS_OF.isoformat(),
        },
        "op081_passage_index": {
            "passage_count": len(chunks),
            "unique_source_count": len(reference_ids),
            "all_source_titles_present": all(bool(chunk.source_title) for chunk in chunks),
            "all_source_uris_present": all(bool(chunk.reference_uri) for chunk in chunks),
            "all_parsed_source_uris_present": all(
                bool(chunk.parsed_source_uri) for chunk in chunks
            ),
            "all_source_spans_identity_verified": True,
            "all_license_statuses_present": all(bool(chunk.license_status) for chunk in chunks),
            "all_effective_dates_timezone_aware": all(
                chunk.effective_at.tzinfo is not None for chunk in chunks
            ),
            "all_line_ranges_valid": all(chunk.line_end >= chunk.line_start for chunk in chunks),
            "retired_passage_count": retired_count,
            "dated_retrieval_chunk_ids": active_results,
        },
        "op082_question_entities": {
            "case_count": len(entity_cases),
            "cases": entity_cases,
            "urgent_case_count": sum(
                bool(case["urgent_risk_detected"]) for case in entity_cases
            ),
            "false_positive_case_is_empty": not entity_cases[-1]["matches"],
        },
        "stage_boundary": {
            "claimed_stage": "IMPLEMENTED",
            "production_operation_proven": False,
            "wellnessbox_service_integration_proven": False,
            "external_validation_proven": False,
            "llm_entity_inference_used": False,
        },
        "source_identity": {
            "commit": _last_commit(SOURCE_PATHS),
            "source_paths": list(SOURCE_PATHS),
            "source_sha256": _hash_paths(SOURCE_PATHS),
            "data_paths": list(DATA_PATHS),
            "data_sha256": _hash_paths(DATA_PATHS),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = _build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
