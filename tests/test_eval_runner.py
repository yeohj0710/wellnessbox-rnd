from pathlib import Path

from wellnessbox_rnd.evals.runner import render_markdown_report, run_eval, write_report_files


def test_run_eval_returns_expected_summary_keys() -> None:
    report = run_eval("data/frozen_eval/sample_cases.jsonl")

    assert report["case_count"] == 5
    assert "recommendation_coverage_pct" in report["summary"]
    assert "sensor_genetic_integration_rate_pct" in report["summary"]
    assert "case_results" in report


def test_write_report_files_creates_json_and_markdown(tmp_path: Path) -> None:
    report = run_eval("data/frozen_eval/sample_cases.jsonl")
    json_path = tmp_path / "eval_report.json"
    md_path = tmp_path / "eval_report.md"

    write_report_files(report, json_path, md_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "metric summary" in render_markdown_report(report)

