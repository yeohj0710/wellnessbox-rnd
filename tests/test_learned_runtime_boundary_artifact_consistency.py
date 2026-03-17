import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_learned_runtime_boundary_artifact_is_self_consistent() -> None:
    audit = _load_json("artifacts/reports/learned_runtime_boundary_audit_v1.json")

    verdict = audit["replay_only_boundary_verdict"]
    matrix = audit["core_dependency_matrix"]
    overall = audit["overall_assessment"]

    core_path_names = (
        "runtime_recommendation_path",
        "safety_path",
        "optimizer_path",
        "inference_api_path",
    )
    promoted_count_from_sections = sum(
        1
        for name in core_path_names
        if audit[name]["core_dependency_promoted"] is True
    )
    promoted_count_from_matrix = sum(
        1
        for name in core_path_names
        if matrix[name]["core_dependency_promoted"] is True
    )

    assert verdict["core_path_count"] == len(core_path_names)
    assert verdict["promoted_core_path_count"] == promoted_count_from_sections
    assert verdict["promoted_core_path_count"] == promoted_count_from_matrix
    assert verdict["all_core_paths_preserved"] is (
        promoted_count_from_sections == 0
    )
    assert overall["learned_artifact_core_dependency_promoted"] is (
        promoted_count_from_sections > 0
    )
    assert verdict["chat_optional_only"] is audit["chat_openai_boundary"]["optional_chat_only"]

    for name in core_path_names:
        assert matrix[name]["core_dependency_promoted"] is audit[name]["core_dependency_promoted"]
        assert isinstance(matrix[name]["proof_headline"], str)
        assert matrix[name]["proof_headline"]
