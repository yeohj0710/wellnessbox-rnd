import json
import subprocess
import sys

from wellnessbox_rnd.evals.dataset_tools import (
    build_eval_case_skeleton,
    summarize_eval_cases,
    validate_eval_cases,
)
from wellnessbox_rnd.evals.runner import load_eval_cases


def test_build_eval_case_skeleton_uses_deterministic_defaults() -> None:
    case = build_eval_case_skeleton(
        case_id="eval-100",
        category="normal_recommendation",
        description="deterministic scaffold smoke test",
        goals=["sleep_support"],
        required_ingredients=["magnesium_glycinate"],
    )

    assert case["case_id"] == "eval-100"
    assert case["request"]["request_id"] == "eval-100"
    assert case["request"]["goals"] == ["sleep_support"]
    assert case["expected"]["recommendation_reference"]["required_ingredients"] == [
        "magnesium_glycinate"
    ]
    assert case["integration"]["wearable"] == {"attempted": 0, "success": 0}


def test_validate_eval_cases_flags_duplicate_ids_unsorted_order_and_request_mismatch() -> None:
    cases = load_eval_cases("data/frozen_eval/frozen_eval_v1.jsonl")
    broken_cases = [cases[1], cases[0]]
    broken_cases[0].request.request_id = "different-request-id"
    broken_cases.append(cases[0])

    issues = validate_eval_cases(broken_cases)

    assert any("duplicate case_id values" in issue for issue in issues)
    assert any("ordering is not sorted" in issue for issue in issues)
    assert any("request.request_id must match case_id" in issue for issue in issues)


def test_summarize_eval_cases_reports_current_dataset_coverage() -> None:
    cases = load_eval_cases("data/frozen_eval/frozen_eval_v1.jsonl")

    summary = summarize_eval_cases(cases)

    assert summary["case_count"] == len(cases)
    assert summary["case_count"] >= 246
    assert summary["category_counts"]["cgm_supported"] >= 3
    assert summary["category_counts"]["chronic_condition"] >= 7
    assert summary["category_counts"]["collect_more_input"] >= 4
    assert summary["category_counts"]["free_text_alias"] == 3
    assert summary["category_counts"]["genetic_supported"] >= 15
    assert summary["category_counts"]["parser_limit"] >= 19
    assert summary["category_counts"]["review_no_candidates"] >= 20
    assert summary["category_counts"]["safety_blocked"] >= 13
    assert summary["expected_next_action_counts"]["collect_more_input"] >= 19
    assert summary["expected_next_action_counts"]["needs_human_review"] >= 13
    assert summary["expected_next_action_counts"]["start_plan"] >= 211
    assert summary["integration_attempted_case_counts"]["cgm"] >= 48
    assert summary["integration_attempted_case_counts"]["wearable"] >= 127
    assert summary["integration_attempted_case_counts"]["genetic"] >= 138
    assert summary["integration_totals"]["cgm"]["attempted"] >= 48
    assert summary["integration_totals"]["cgm"]["success"] >= 30
    assert summary["integration_totals"]["wearable"]["attempted"] >= 127
    assert summary["integration_totals"]["wearable"]["success"] >= 118
    assert summary["integration_totals"]["genetic"]["attempted"] >= 138
    assert summary["integration_totals"]["genetic"]["success"] >= 130


def test_manage_eval_dataset_scaffold_append_writes_sorted_jsonl(tmp_path) -> None:
    dataset_path = tmp_path / "cases.jsonl"

    first = subprocess.run(
        [
            sys.executable,
            "scripts/manage_eval_dataset.py",
            "scaffold",
            "--case-id",
            "eval-002",
            "--category",
            "normal_recommendation",
            "--description",
            "second case",
            "--goal",
            "sleep_support",
            "--append",
            "--dataset",
            str(dataset_path),
        ],
        capture_output=True,
        check=False,
        cwd="C:/dev/wellnessbox-rnd",
        text=True,
    )
    assert first.returncode == 0, first.stderr

    second = subprocess.run(
        [
            sys.executable,
            "scripts/manage_eval_dataset.py",
            "scaffold",
            "--case-id",
            "eval-001",
            "--category",
            "normal_recommendation",
            "--description",
            "first case",
            "--goal",
            "stress_support",
            "--required-ingredient",
            "l_theanine",
            "--append",
            "--dataset",
            str(dataset_path),
        ],
        capture_output=True,
        check=False,
        cwd="C:/dev/wellnessbox-rnd",
        text=True,
    )
    assert second.returncode == 0, second.stderr

    lines = dataset_path.read_text(encoding="utf-8").splitlines()
    case_ids = [json.loads(line)["case_id"] for line in lines]
    assert case_ids == ["eval-001", "eval-002"]
