from pathlib import Path

from wellnessbox_rnd.evals.learned_runtime_boundary_audit import (
    build_learned_runtime_boundary_audit,
    render_learned_runtime_boundary_audit_markdown,
    write_learned_runtime_boundary_audit_files,
)


def test_build_learned_runtime_boundary_audit_proves_no_core_promotion() -> None:
    audit = build_learned_runtime_boundary_audit(
        sample_request_path="data/samples/api_recommend_start_plan_request_v1.json",
    )

    recommendation_path = audit["runtime_recommendation_path"]
    safety_path = audit["safety_path"]
    optimizer_path = audit["optimizer_path"]
    inference_api_path = audit["inference_api_path"]
    chat_boundary = audit["chat_openai_boundary"]
    verdict = audit["replay_only_boundary_verdict"]
    matrix = audit["core_dependency_matrix"]

    assert audit["audit_name"] == "learned_runtime_boundary_audit_v1"
    assert (
        audit["overall_assessment"]["learned_artifact_core_dependency_promoted"] is False
    )
    assert audit["validation_issues"] == []
    assert verdict == {
        "status": "replay_only_boundary_preserved",
        "core_path_count": 4,
        "promoted_core_path_count": 0,
        "all_core_paths_preserved": True,
        "chat_optional_only": True,
    }
    assert matrix == {
        "runtime_recommendation_path": {
            "core_dependency_promoted": False,
            "proof_headline": (
                "recommend() defaults learned reranking off and baseline responses stay "
                "deterministic_baseline_v1 without learned rule refs."
            ),
        },
        "safety_path": {
            "core_dependency_promoted": False,
            "proof_headline": (
                "assess_safety() consumes only normalized intake and safety rules stay "
                "deterministic."
            ),
        },
        "optimizer_path": {
            "core_dependency_promoted": False,
            "proof_headline": (
                "optional learned reranking exits early when flag/path are absent, and "
                "missing-artifact calls match baseline selection."
            ),
        },
        "inference_api_path": {
            "core_dependency_promoted": False,
            "proof_headline": (
                "the public recommend route forwards payload only and returns "
                "deterministic_baseline_v1 without learned rule refs."
            ),
        },
    }
    assert recommendation_path["core_dependency_promoted"] is False
    assert recommendation_path["evidence"]["recommend_signature_defaults"] == {
        "enable_learned_reranking": False,
        "learned_efficacy_artifact_path": None,
    }
    assert recommendation_path["evidence"]["baseline_engine_mode"] == "deterministic_baseline_v1"
    assert recommendation_path["evidence"]["baseline_contains_learned_rule_ref"] is False
    assert recommendation_path["evidence"]["baseline_limitation_codes"] == [
        "demo_catalog_only",
        "deterministic_baseline_only",
        "no_llm_core_decision",
    ]
    assert safety_path["core_dependency_promoted"] is False
    assert safety_path["evidence"]["assess_safety_parameter_names"] == ["intake"]
    assert safety_path["evidence"]["imports_model_modules"] is False
    assert safety_path["evidence"]["imports_chat_modules"] is False
    assert optimizer_path["core_dependency_promoted"] is False
    assert optimizer_path["evidence"]["select_signature_defaults"] == {
        "enable_learned_reranking": False,
        "learned_efficacy_artifact_path": None,
    }
    assert optimizer_path["evidence"]["baseline_vs_missing_path_same_selection"] is True
    assert optimizer_path["evidence"]["baseline_vs_missing_file_same_selection"] is True
    assert optimizer_path["evidence"]["source_contains_optional_guards"] is True
    assert inference_api_path["core_dependency_promoted"] is False
    assert inference_api_path["evidence"]["route_parameter_names"] == ["payload"]
    assert inference_api_path["evidence"]["route_calls_recommend_without_learned_args"] is True
    assert inference_api_path["evidence"]["api_smoke_status_code"] == 200
    assert inference_api_path["evidence"]["api_smoke_engine_mode"] == "deterministic_baseline_v1"
    assert inference_api_path["evidence"]["api_smoke_contains_learned_rule_ref"] is False
    assert chat_boundary["optional_chat_only"] is True
    assert chat_boundary["evidence"]["chat_adapter_allow_live_api_default"] is False
    assert (
        chat_boundary["evidence"]["chat_fallback_provider_when_live_disabled"]
        == "deterministic_template_fallback"
    )
    assert (
        chat_boundary["evidence"]["chat_fallback_reason_when_live_disabled"]
        == "live_api_disabled"
    )
    assert chat_boundary["evidence"]["core_runtime_imports_chat_modules"] == {
        "recommendation_service": False,
        "safety_service": False,
        "optimizer_service": False,
        "inference_route": False,
    }


def test_write_learned_runtime_boundary_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = build_learned_runtime_boundary_audit(
        sample_request_path="data/samples/api_recommend_start_plan_request_v1.json",
    )

    json_path = tmp_path / "learned_runtime_boundary_audit_v1.json"
    md_path = tmp_path / "learned_runtime_boundary_audit_v1.md"
    write_learned_runtime_boundary_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )
    markdown = render_learned_runtime_boundary_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "## Replay-Only Boundary Verdict" in markdown
    assert "## runtime_recommendation_path" in markdown
    assert "## chat_openai_boundary" in markdown
    assert "learned_artifact_core_dependency_promoted: `False`" in markdown
