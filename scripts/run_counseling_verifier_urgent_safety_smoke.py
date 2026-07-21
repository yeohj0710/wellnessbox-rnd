from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from wellnessbox_rnd.chat.openai_adapter import (  # noqa: E402
    ChatAdapterRequest,
    generate_chat_answer_with_openai_fallback,
)
from wellnessbox_rnd.chat.retrieval import (  # noqa: E402
    RetrievalCorpusManifest,
    load_approved_counseling_scope,
)
from wellnessbox_rnd.chat.verifier import (  # noqa: E402
    load_counseling_answer_verifier_policy,
)

DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/op085_op086_counseling_verifier_urgent_safety_smoke_v1.json"
)
CLAIMS_PATH = ROOT / "data/parsed_references/reference_claims_v1.jsonl"
REFERENCES_PATH = ROOT / "data/knowledge/reference_knowledge_base_v1.json"
AS_OF = datetime(2026, 7, 21, 15, 0, tzinfo=UTC)
SOURCE_PATHS = (
    "scripts/build_chat_retrieval_assets.py",
    "scripts/run_counseling_verifier_urgent_safety_smoke.py",
    "src/wellnessbox_rnd/chat/__init__.py",
    "src/wellnessbox_rnd/chat/answering.py",
    "src/wellnessbox_rnd/chat/openai_adapter.py",
    "src/wellnessbox_rnd/chat/retrieval.py",
    "src/wellnessbox_rnd/chat/verifier.py",
    "tests/test_chat_openai_adapter.py",
    "tests/test_chat_retrieval.py",
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


def _build() -> dict[str, object]:
    claims = _load_claim_rows(CLAIMS_PATH)
    references = _load_reference_rows(REFERENCES_PATH)
    chunks = [_build_chunk_from_claim(claim, references) for claim in claims]
    manifest = RetrievalCorpusManifest(
        manifest_version="op085_op086_counseling_verifier_manifest_v1",
        chunk_count=len(chunks),
        chunks=chunks,
    )
    scope = load_approved_counseling_scope()
    policy = load_counseling_answer_verifier_policy()

    supported = generate_bounded_template_answer(
        manifest,
        query="What should counseling say about glucosamine with warfarin?",
        scope=scope,
        as_of=AS_OF,
        answer_template_key="interaction_warning",
    )
    supported_verification = verify_bounded_template_answer(
        supported, manifest=manifest, scope=scope, as_of=AS_OF
    )
    if not supported_verification.passed:
        raise RuntimeError(f"supported_answer_failed::{supported_verification.issues}")

    urgent = generate_bounded_template_answer(
        manifest,
        query="I have chest pain after taking a supplement. What should I take?",
        scope=scope,
        as_of=AS_OF,
    )
    urgent_verification = verify_bounded_template_answer(
        urgent, manifest=manifest, scope=scope, as_of=AS_OF
    )
    if not urgent_verification.passed or urgent.status != "safety_escalation":
        raise RuntimeError(f"urgent_answer_failed::{urgent_verification.issues}")
    adapter_urgent = generate_chat_answer_with_openai_fallback(
        manifest,
        ChatAdapterRequest(
            query=urgent.query,
            knowledge_scope=scope,
            as_of=AS_OF,
        ),
        allow_live_api=True,
    )
    if adapter_urgent.attempted_live_call or adapter_urgent.evidence_chunk_ids:
        raise RuntimeError("urgent_answer_did_not_precede_provider_and_retrieval")

    negated = generate_bounded_template_answer(
        manifest,
        query="No chest pain is present. Explain citation requirements.",
        scope=scope,
        as_of=AS_OF,
        answer_template_key="citation_requirement_summary",
    )
    contrast = generate_bounded_template_answer(
        manifest,
        query="No bleeding, but I have chest pain. What supplement should I take?",
        scope=scope,
        as_of=AS_OF,
    )
    if negated.status == "safety_escalation" or contrast.status != "safety_escalation":
        raise RuntimeError("urgent_negation_or_clause_boundary_failed")
    common_urgent_questions = [
        "My chest hurts after taking this supplement. What should I take?",
        "I feel pressure in my chest after taking this supplement.",
        "I have severe chest discomfort after taking this supplement.",
        "I am having trouble breathing after taking this supplement.",
        "It is hard to breathe after taking this supplement.",
    ]
    common_urgent_statuses = [
        generate_bounded_template_answer(manifest, query=question, scope=scope, as_of=AS_OF).status
        for question in common_urgent_questions
    ]
    if any(status != "safety_escalation" for status in common_urgent_statuses):
        raise RuntimeError("common_urgent_expression_not_escalated")

    original_cwd = Path.cwd()
    service_evidence_root = Path(
        os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(ROOT.parent / "wellnessbox"))
    )
    if not service_evidence_root.is_dir():
        raise RuntimeError("wellnessbox_evidence_root_missing")
    try:
        os.chdir(service_evidence_root)
        outside_cwd_policy = load_counseling_answer_verifier_policy()
    finally:
        os.chdir(original_cwd)
    if outside_cwd_policy != policy:
        raise RuntimeError("verifier_policy_cwd_identity_mismatch")

    mutations = {
        "unsupported_claim": supported.model_copy(
            update={"answer_text": supported.answer_text + " It is guaranteed to work."}
        ),
        "risk_omission": supported.model_copy(
            update={"answer_text": "Glucosamine with warfarin should be treated cautiously."}
        ),
        "forbidden_diagnosis": supported.model_copy(
            update={"answer_text": "I diagnose you with a bleeding disorder."}
        ),
        "delayed_emergency": urgent.model_copy(
            update={"answer_text": "Wait and see before seeking emergency care."}
        ),
        "urgent_recommendation": urgent.model_copy(
            update={"answer_text": policy.emergency_guidance_text + " I recommend magnesium."}
        ),
        "unrelated_query": supported.model_copy(update={"query": "Does glucosamine cure cancer?"}),
    }
    mutation_results: dict[str, object] = {}
    for name, answer in mutations.items():
        result = verify_bounded_template_answer(answer, manifest=manifest, scope=scope, as_of=AS_OF)
        if result.passed:
            raise RuntimeError(f"tampered_answer_not_blocked::{name}")
        mutation_results[name] = {"blocked": True, "issues": result.issues}

    forged_policy = policy.model_copy(update={"policy_id": "forged-policy"})
    forged_result = verify_bounded_template_answer(
        supported,
        manifest=manifest,
        scope=scope,
        as_of=AS_OF,
        verifier_policy=forged_policy,
    )
    if forged_result.passed or "verifier_policy_mismatch" not in forged_result.issues:
        raise RuntimeError("forged_verifier_policy_not_blocked")

    return {
        "schema_version": "op085_op086_counseling_verifier_urgent_safety_smoke_v1",
        "generated_at": AS_OF.isoformat(),
        "corpus": {"passage_count": len(chunks), "source_count": len(references)},
        "policy": policy.model_dump(mode="json"),
        "verified_cases": {
            "supported_interaction": supported_verification.model_dump(mode="json"),
            "urgent_safety": {
                "status": urgent.status,
                "answer_text": urgent.answer_text,
                "detected_urgent_risk_keys": urgent.detected_urgent_risk_keys,
                "verification": urgent_verification.model_dump(mode="json"),
                "provider_call_attempted": adapter_urgent.attempted_live_call,
                "retrieval_evidence_count": len(adapter_urgent.evidence_chunk_ids),
            },
            "negated_urgent_not_escalated": negated.status != "safety_escalation",
            "contrast_clause_escalated": contrast.status == "safety_escalation",
            "common_urgent_phrasings": [
                {"question": question, "status": status}
                for question, status in zip(
                    common_urgent_questions, common_urgent_statuses, strict=True
                )
            ],
            "policy_loaded_from_service_cwd": outside_cwd_policy == policy,
        },
        "negative_probes": mutation_results
        | {"forged_policy": {"blocked": True, "issues": forged_result.issues}},
        "stage_boundaries": {
            "claimed_stage": "IMPLEMENTED",
            "wellnessbox_service_integration_proven": False,
            "deployment_proven": False,
            "production_operation_proven": False,
            "external_validation_proven": False,
            "live_llm_inference_used": False,
            "model_training_performed": False,
            "frozen_dataset_changed": False,
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
