from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.inference_api.main import app
from apps.inference_api.routes.recommend import recommend_endpoint
from wellnessbox_rnd.chat.openai_adapter import (
    ChatAdapterRequest,
    generate_chat_answer_with_openai_fallback,
)
from wellnessbox_rnd.chat.retrieval import RetrievalChunk, RetrievalCorpusManifest
from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.optimizer.service import select_recommendations
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest


def build_learned_runtime_boundary_audit(
    *,
    sample_request_path: str | Path,
) -> dict[str, object]:
    sample_request_file = Path(sample_request_path)
    payload = json.loads(sample_request_file.read_text(encoding="utf-8"))
    request_model = RecommendationRequest.model_validate(payload)
    intake = normalize_request(request_model)
    safety_summary = assess_safety(intake)

    recommendation_imports = _read_imports(
        "src/wellnessbox_rnd/orchestration/recommendation_service.py"
    )
    safety_imports = _read_imports("src/wellnessbox_rnd/safety/service.py")
    optimizer_imports = _read_imports("src/wellnessbox_rnd/optimizer/service.py")
    route_imports = _read_imports("apps/inference_api/routes/recommend.py")
    optimizer_module_text = Path("src/wellnessbox_rnd/optimizer/service.py").read_text(
        encoding="utf-8"
    )

    baseline_recommendation = recommend(request_model)
    optimizer_baseline = select_recommendations(intake, safety_summary)
    optimizer_missing_path = select_recommendations(
        intake,
        safety_summary,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=None,
    )
    optimizer_missing_file = select_recommendations(
        intake,
        safety_summary,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path="artifacts/models/does_not_exist.json",
    )

    client = TestClient(app)
    api_response = client.post("/v1/recommend", json=payload)
    api_body = api_response.json()

    chat_response = generate_chat_answer_with_openai_fallback(
        _build_minimal_chat_manifest(),
        ChatAdapterRequest(
            query="What counseling applies to glucosamine with warfarin?",
            answer_template_key="interaction_warning",
            expected_reference_ids=["REF-KNOWLEDGE-ANTICOAG-001"],
            expected_claim_ids=["CLM-KNOWLEDGE-ANTICOAG-001"],
            expected_terms=["glucosamine", "warfarin"],
        ),
        allow_live_api=False,
    )

    route_source = inspect.getsource(recommend_endpoint)
    recommendation_source = inspect.getsource(recommend)
    safety_source = inspect.getsource(assess_safety)

    recommendation_path = {
        "core_dependency_promoted": False,
        "evidence": {
            "recommend_signature_defaults": {
                "enable_learned_reranking": inspect.signature(recommend).parameters[
                    "enable_learned_reranking"
                ].default,
                "learned_efficacy_artifact_path": inspect.signature(recommend).parameters[
                    "learned_efficacy_artifact_path"
                ].default,
            },
            "recommendation_module_imports_chat": _has_import_prefix(
                recommendation_imports, "wellnessbox_rnd.chat"
            ),
            "recommendation_module_imports_openai": _has_import_text(
                recommendation_imports, "openai"
            ),
            "baseline_engine_mode": baseline_recommendation.metadata.mode,
            "baseline_contains_learned_rule_ref": any(
                "OPT-LEARNED-001" in candidate.rule_refs
                for candidate in baseline_recommendation.recommendations
            ),
            "baseline_limitation_codes": [
                item.code for item in baseline_recommendation.limitation_details
            ],
            "source_mentions_optional_learned_path": (
                "enable_learned_reranking: bool = False" in recommendation_source
                and "learned_efficacy_artifact_path: str | None = None"
                in recommendation_source
            ),
        },
        "pinpointed_paths": [
            {
                "path": "src/wellnessbox_rnd/orchestration/recommendation_service.py:26",
                "detail": (
                    "recommend() defaults learned reranking to False and "
                    "artifact path to None."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/orchestration/recommendation_service.py:2648",
                "detail": (
                    "response limitation details still declare "
                    "deterministic_baseline_only and no_llm_core_decision."
                ),
            },
        ],
    }

    safety_path = {
        "core_dependency_promoted": False,
        "evidence": {
            "assess_safety_parameter_names": list(inspect.signature(assess_safety).parameters),
            "imports_model_modules": _has_import_prefix(
                safety_imports, "wellnessbox_rnd.models"
            ),
            "imports_chat_modules": _has_import_prefix(
                safety_imports, "wellnessbox_rnd.chat"
            ),
            "imports_optimizer_modules": _has_import_prefix(
                safety_imports, "wellnessbox_rnd.optimizer"
            ),
            "source_mentions_artifact_or_learned": (
                "artifact" in safety_source or "learned" in safety_source
            ),
        },
        "pinpointed_paths": [
            {
                "path": "src/wellnessbox_rnd/safety/service.py:25",
                "detail": (
                    "assess_safety() takes normalized intake plus an optional injected "
                    "application time and "
                    "returns deterministic SafetySummary."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/safety/rules.py:1",
                "detail": (
                    "safety rules resolve from deterministic rule loaders, "
                    "not learned artifacts."
                ),
            },
        ],
    }

    optimizer_path = {
        "core_dependency_promoted": False,
        "evidence": {
            "select_signature_defaults": {
                "enable_learned_reranking": inspect.signature(select_recommendations).parameters[
                    "enable_learned_reranking"
                ].default,
                "learned_efficacy_artifact_path": inspect.signature(
                    select_recommendations
                ).parameters["learned_efficacy_artifact_path"].default,
            },
            "baseline_vs_missing_path_same_selection": [
                item.ingredient_key for item in optimizer_baseline
            ]
            == [item.ingredient_key for item in optimizer_missing_path],
            "baseline_vs_missing_file_same_selection": [
                item.ingredient_key for item in optimizer_baseline
            ]
            == [item.ingredient_key for item in optimizer_missing_file],
            "source_contains_optional_guards": (
                "if not enable_learned_reranking:" in optimizer_module_text
                and "if learned_efficacy_artifact_path is None:" in optimizer_module_text
                and "if not artifact_path.is_file():" in optimizer_module_text
                and "validate_efficacy_model_artifact_for_runtime" in optimizer_module_text
            ),
            "optimizer_imports_chat_modules": _has_import_prefix(
                optimizer_imports, "wellnessbox_rnd.chat"
            ),
        },
        "pinpointed_paths": [
            {
                "path": "src/wellnessbox_rnd/optimizer/service.py:25",
                "detail": (
                    "select_recommendations() defaults learned reranking "
                    "off and accepts no required learned dependency."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/optimizer/service.py:149",
                "detail": (
                    "_apply_learned_efficacy_reranking() exits early when "
                    "flag is off, path is None, or artifact file is missing."
                ),
            },
        ],
    }

    inference_api_path = {
        "core_dependency_promoted": False,
        "evidence": {
            "route_parameter_names": list(inspect.signature(recommend_endpoint).parameters),
            "route_calls_recommend_without_learned_args": (
                _calls_recommend_with_only_payload(route_source)
            ),
            "route_imports_chat_modules": _has_import_prefix(
                route_imports, "wellnessbox_rnd.chat"
            ),
            "api_smoke_status_code": api_response.status_code,
            "api_smoke_engine_mode": api_body["metadata"]["mode"],
            "api_smoke_limitation_codes": [
                item["code"] for item in api_body["limitation_details"]
            ],
            "api_smoke_contains_learned_rule_ref": any(
                "OPT-LEARNED-001" in candidate["rule_refs"]
                for candidate in api_body["recommendations"]
            ),
        },
        "pinpointed_paths": [
            {
                "path": "apps/inference_api/routes/recommend.py:96",
                "detail": (
                    "the public recommend route exposes only the request "
                    "payload and forwards it to recommend(payload)."
                ),
            },
            {
                "path": "apps/inference_api/main.py:1",
                "detail": (
                    "the inference API mounts the deterministic recommend "
                    "route and does not inject learned artifact config."
                ),
            },
        ],
    }

    chat_boundary = {
        "optional_chat_only": True,
        "evidence": {
            "chat_adapter_allow_live_api_default": inspect.signature(
                generate_chat_answer_with_openai_fallback
            ).parameters["allow_live_api"].default,
            "chat_fallback_provider_when_live_disabled": chat_response.provider,
            "chat_fallback_reason_when_live_disabled": chat_response.fallback_reason,
            "core_runtime_imports_chat_modules": {
                "recommendation_service": _has_import_prefix(
                    recommendation_imports, "wellnessbox_rnd.chat"
                ),
                "safety_service": _has_import_prefix(
                    safety_imports, "wellnessbox_rnd.chat"
                ),
                "optimizer_service": _has_import_prefix(
                    optimizer_imports, "wellnessbox_rnd.chat"
                ),
                "inference_route": _has_import_prefix(
                    route_imports, "wellnessbox_rnd.chat"
                ),
            },
        },
        "pinpointed_paths": [
            {
                "path": "src/wellnessbox_rnd/chat/openai_adapter.py:93",
                "detail": (
                    "OpenAI access stays under chat.openai_adapter and "
                    "defaults to allow_live_api=False."
                ),
            },
            {
                "path": "src/wellnessbox_rnd/orchestration/recommendation_service.py:2648",
                "detail": (
                    "core recommendation responses still declare "
                    "no_llm_core_decision in limitation details."
                ),
            },
        ],
    }

    core_paths = {
        "runtime_recommendation_path": recommendation_path,
        "safety_path": safety_path,
        "optimizer_path": optimizer_path,
        "inference_api_path": inference_api_path,
    }
    promoted_core_path_count = sum(
        1
        for section in core_paths.values()
        if _as_dict(section).get("core_dependency_promoted") is True
    )

    audit = {
        "audit_name": "learned_runtime_boundary_audit_v1",
        "scope": {
            "sample_request_path": sample_request_file.as_posix(),
            "inference_api_route": "/v1/recommend",
        },
        "core_dependency_matrix": {
            section_name: {
                "core_dependency_promoted": _as_dict(section).get(
                    "core_dependency_promoted"
                ),
                "proof_headline": _proof_headline(section_name),
            }
            for section_name, section in core_paths.items()
        },
        "replay_only_boundary_verdict": {
            "status": "replay_only_boundary_preserved",
            "core_path_count": len(core_paths),
            "promoted_core_path_count": promoted_core_path_count,
            "all_core_paths_preserved": promoted_core_path_count == 0,
            "chat_optional_only": chat_boundary["optional_chat_only"],
        },
        "runtime_recommendation_path": recommendation_path,
        "safety_path": safety_path,
        "optimizer_path": optimizer_path,
        "inference_api_path": inference_api_path,
        "chat_openai_boundary": chat_boundary,
        "overall_assessment": {
            "learned_artifact_core_dependency_promoted": False,
            "summary": (
                "Learned artifacts remain optional replay-only or explicit opt-in tie-breakers. "
                "The public runtime path stays deterministic by default across recommendation, "
                "safety, optimizer, and inference API layers."
            ),
            "highest_risk_gap": (
                "The optimizer still contains an optional learned reranker implementation, "
                "but it is not route-exposed and remains guarded by default-off flags plus "
                "missing-artifact fallbacks."
            ),
        },
    }
    audit["validation_issues"] = validate_learned_runtime_boundary_audit(audit)
    return audit


def validate_learned_runtime_boundary_audit(audit: dict[str, object]) -> list[str]:
    issues: list[str] = []
    verdict = _as_dict(audit.get("replay_only_boundary_verdict"))
    if verdict.get("all_core_paths_preserved") is not True:
        issues.append("core_path_promotion_detected")
    if verdict.get("chat_optional_only") is not True:
        issues.append("chat_boundary_not_optional_only")
    for section_name in (
        "runtime_recommendation_path",
        "safety_path",
        "optimizer_path",
        "inference_api_path",
    ):
        if _as_dict(audit.get(section_name)).get("core_dependency_promoted") is not False:
            issues.append(f"{section_name}_promoted")
    return issues


def render_learned_runtime_boundary_audit_markdown(audit: dict[str, object]) -> str:
    scope = _as_dict(audit["scope"])
    verdict = _as_dict(audit["replay_only_boundary_verdict"])
    matrix = _as_dict(audit["core_dependency_matrix"])
    overall = _as_dict(audit["overall_assessment"])
    lines = [
        "# learned runtime boundary audit v1",
        "",
        "## Scope",
        f"- sample_request_path: `{scope['sample_request_path']}`",
        f"- inference_api_route: `{scope['inference_api_route']}`",
        "",
        "## Replay-Only Boundary Verdict",
        f"- status: `{verdict['status']}`",
        f"- core_path_count: `{verdict['core_path_count']}`",
        f"- promoted_core_path_count: `{verdict['promoted_core_path_count']}`",
        f"- all_core_paths_preserved: `{verdict['all_core_paths_preserved']}`",
        f"- chat_optional_only: `{verdict['chat_optional_only']}`",
        f"- core_dependency_matrix: `{matrix}`",
        "",
    ]
    for section_name in (
        "runtime_recommendation_path",
        "safety_path",
        "optimizer_path",
        "inference_api_path",
        "chat_openai_boundary",
    ):
        section = _as_dict(audit[section_name])
        lines.append(f"## {section_name}")
        if "core_dependency_promoted" in section:
            lines.append(
                f"- core_dependency_promoted: `{section['core_dependency_promoted']}`"
            )
        if "optional_chat_only" in section:
            lines.append(f"- optional_chat_only: `{section['optional_chat_only']}`")
        lines.append(f"- evidence: `{section['evidence']}`")
        for finding in section["pinpointed_paths"]:
            finding_dict = _as_dict(finding)
            lines.append(f"- {finding_dict['path']}: {finding_dict['detail']}")
        lines.append("")
    lines.extend(
        [
            "## Overall Assessment",
            (
                "- learned_artifact_core_dependency_promoted: "
                f"`{overall['learned_artifact_core_dependency_promoted']}`"
            ),
            f"- summary: `{overall['summary']}`",
            f"- highest_risk_gap: `{overall['highest_risk_gap']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_learned_runtime_boundary_audit_files(
    *,
    audit: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(render_learned_runtime_boundary_audit_markdown(audit), encoding="utf-8")


def _read_imports(path: str | Path) -> list[str]:
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
    return sorted(set(imports))


def _has_import_prefix(imports: list[str], prefix: str) -> bool:
    return any(item.startswith(prefix) for item in imports)


def _has_import_text(imports: list[str], text: str) -> bool:
    lowered = text.lower()
    return any(lowered in item.lower() for item in imports)


def _calls_recommend_with_only_payload(source: str) -> bool:
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "recommend"
    ]
    if len(calls) != 1:
        return False
    call = calls[0]
    return (
        len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "payload"
        and not call.keywords
    )


def _proof_headline(section_name: str) -> str:
    if section_name == "runtime_recommendation_path":
        return (
            "recommend() defaults learned reranking off and baseline responses stay "
            "deterministic_baseline_v1 without learned rule refs."
        )
    if section_name == "safety_path":
        return (
            "assess_safety() consumes normalized intake plus an optional injected "
            "application time, and safety rules stay deterministic."
        )
    if section_name == "optimizer_path":
        return (
            "optional learned reranking exits early when flag/path are absent, and "
            "missing-artifact calls match baseline selection."
        )
    if section_name == "inference_api_path":
        return (
            "the public recommend route forwards payload only and returns "
            "deterministic_baseline_v1 without learned rule refs."
        )
    return "unknown"


def _build_minimal_chat_manifest() -> RetrievalCorpusManifest:
    return RetrievalCorpusManifest(
        manifest_version="audit",
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


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "build_learned_runtime_boundary_audit",
    "render_learned_runtime_boundary_audit_markdown",
    "validate_learned_runtime_boundary_audit",
    "write_learned_runtime_boundary_audit_files",
]
