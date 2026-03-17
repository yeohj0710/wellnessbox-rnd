import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_learned_runtime_boundary_hold_state_stays_current() -> None:
    audit = _load_json("artifacts/reports/learned_runtime_boundary_audit_v1.json")

    verdict = audit["replay_only_boundary_verdict"]
    matrix = audit["core_dependency_matrix"]
    runtime_path = audit["runtime_recommendation_path"]
    safety_path = audit["safety_path"]
    optimizer_path = audit["optimizer_path"]
    inference_api_path = audit["inference_api_path"]
    chat_boundary = audit["chat_openai_boundary"]
    overall = audit["overall_assessment"]

    assert verdict == {
        "status": "replay_only_boundary_preserved",
        "core_path_count": 4,
        "promoted_core_path_count": 0,
        "all_core_paths_preserved": True,
        "chat_optional_only": True,
    }
    assert audit["validation_issues"] == []
    assert overall["learned_artifact_core_dependency_promoted"] is False

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

    assert runtime_path["core_dependency_promoted"] is False
    assert runtime_path["evidence"]["baseline_engine_mode"] == "deterministic_baseline_v1"
    assert runtime_path["evidence"]["baseline_contains_learned_rule_ref"] is False

    assert safety_path["core_dependency_promoted"] is False
    assert safety_path["evidence"]["imports_model_modules"] is False
    assert safety_path["evidence"]["imports_chat_modules"] is False
    assert safety_path["evidence"]["imports_optimizer_modules"] is False

    assert optimizer_path["core_dependency_promoted"] is False
    assert optimizer_path["evidence"]["baseline_vs_missing_path_same_selection"] is True
    assert optimizer_path["evidence"]["baseline_vs_missing_file_same_selection"] is True

    assert inference_api_path["core_dependency_promoted"] is False
    assert inference_api_path["evidence"]["route_calls_recommend_without_learned_args"] is True
    assert inference_api_path["evidence"]["api_smoke_engine_mode"] == "deterministic_baseline_v1"
    assert inference_api_path["evidence"]["api_smoke_contains_learned_rule_ref"] is False

    assert chat_boundary["optional_chat_only"] is True
    assert chat_boundary["evidence"]["chat_adapter_allow_live_api_default"] is False
    assert chat_boundary["evidence"]["core_runtime_imports_chat_modules"] == {
        "recommendation_service": False,
        "safety_service": False,
        "optimizer_service": False,
        "inference_route": False,
    }
