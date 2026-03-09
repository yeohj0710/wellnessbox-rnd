from collections import Counter
from pathlib import Path

import pytest

from wellnessbox_rnd.evals.runner import (
    load_eval_cases,
    render_markdown_report,
    run_eval,
    write_report_files,
)


def test_run_eval_returns_expected_summary_keys() -> None:
    report = run_eval("data/frozen_eval/frozen_eval_v1.jsonl")
    integration_details = report["summary"]["sensor_genetic_integration_rate_pct"]["details"]
    cases = load_eval_cases("data/frozen_eval/frozen_eval_v1.jsonl")
    attempted_breakdown = {
        key: value["score"]
        for key, value in integration_details["modality_breakdown"].items()
        if value["score"] is not None
    }

    assert report["case_count"] == len(cases)
    assert "recommendation_coverage_pct" in report["summary"]
    assert "sensor_genetic_integration_rate_pct" in report["summary"]
    assert integration_details["bottleneck_modality"] == min(
        attempted_breakdown, key=attempted_breakdown.get
    )
    assert integration_details["modality_breakdown"]["wearable"]["score"] == pytest.approx(
        92.91338582677166
    )
    assert integration_details["modality_breakdown"]["cgm"]["score"] == pytest.approx(
        70.83333333333333
    )
    assert integration_details["modality_breakdown"]["genetic"]["score"] == pytest.approx(
        94.20289855072464
    )
    assert "case_results" in report


def test_primary_eval_dataset_has_broader_category_and_modality_coverage() -> None:
    cases = load_eval_cases("data/frozen_eval/frozen_eval_v1.jsonl")
    category_counts = Counter(case.category for case in cases)

    assert category_counts["safety_warning"] >= 10
    assert category_counts["missing_context"] >= 18
    assert category_counts["integration_mixed"] == 2
    assert category_counts["genetic_supported"] >= 15
    assert category_counts["review_no_candidates"] >= 20
    assert category_counts["safety_blocked"] >= 13
    assert category_counts["parser_limit"] >= 19

    attempted_case_counts = {"wearable": 0, "cgm": 0, "genetic": 0}
    for case in cases:
        for modality, observation in case.integration.items():
            if observation.attempted:
                attempted_case_counts[modality] += 1

    assert attempted_case_counts["wearable"] >= 127
    assert attempted_case_counts["cgm"] >= 48
    assert attempted_case_counts["genetic"] >= 138


def test_write_report_files_creates_json_and_markdown() -> None:
    report = run_eval("data/frozen_eval/frozen_eval_v1.jsonl")
    json_path = Path("artifacts/test_reports/eval_report.json")
    md_path = Path("artifacts/test_reports/eval_report.md")

    write_report_files(report, json_path, md_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "metric summary" in render_markdown_report(report)
    assert "integration diagnostics" in render_markdown_report(report)
