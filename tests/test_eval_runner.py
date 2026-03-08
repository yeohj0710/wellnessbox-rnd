from collections import Counter
from pathlib import Path

from wellnessbox_rnd.evals.runner import (
    load_eval_cases,
    render_markdown_report,
    run_eval,
    write_report_files,
)


def test_run_eval_returns_expected_summary_keys() -> None:
    report = run_eval("data/frozen_eval/sample_cases.jsonl")
    integration_details = report["summary"]["sensor_genetic_integration_rate_pct"]["details"]

    assert report["case_count"] == 16
    assert "recommendation_coverage_pct" in report["summary"]
    assert "sensor_genetic_integration_rate_pct" in report["summary"]
    assert integration_details["bottleneck_modality"] in {"cgm", "genetic"}
    assert integration_details["modality_breakdown"]["wearable"]["score"] == 100.0
    assert integration_details["modality_breakdown"]["cgm"]["score"] == 50.0
    assert integration_details["modality_breakdown"]["genetic"]["score"] == 50.0
    assert "case_results" in report


def test_sample_eval_dataset_has_broader_category_and_modality_coverage() -> None:
    cases = load_eval_cases("data/frozen_eval/sample_cases.jsonl")
    category_counts = Counter(case.category for case in cases)

    assert category_counts["safety_warning"] >= 2
    assert category_counts["missing_context"] >= 4
    assert category_counts["integration_mixed"] == 1
    assert category_counts["duplicate_overlap"] == 1
    assert category_counts["catalog_alias"] == 2

    attempted_case_counts = {"wearable": 0, "cgm": 0, "genetic": 0}
    for case in cases:
        for modality, observation in case.integration.items():
            if observation.attempted:
                attempted_case_counts[modality] += 1

    assert attempted_case_counts["wearable"] >= 4
    assert attempted_case_counts["cgm"] >= 2
    assert attempted_case_counts["genetic"] >= 2


def test_write_report_files_creates_json_and_markdown() -> None:
    report = run_eval("data/frozen_eval/sample_cases.jsonl")
    json_path = Path("artifacts/test_reports/eval_report.json")
    md_path = Path("artifacts/test_reports/eval_report.md")

    write_report_files(report, json_path, md_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "metric summary" in render_markdown_report(report)
    assert "integration diagnostics" in render_markdown_report(report)
