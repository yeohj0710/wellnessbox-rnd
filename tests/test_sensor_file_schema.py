import json
import subprocess
import sys
from pathlib import Path

from wellnessbox_rnd.domain.sensor_parser import (
    validate_cgm_summary_csv_schema,
    validate_gene_profile_json_schema,
    validate_wearable_summary_csv_schema,
)


def test_validate_sensor_file_schemas_accept_valid_sample_fixtures() -> None:
    wearable_result = validate_wearable_summary_csv_schema(
        Path("data/samples/wearable_summary_v1.csv").read_text(encoding="utf-8")
    )
    cgm_result = validate_cgm_summary_csv_schema(
        Path("data/samples/cgm_summary_v1.csv").read_text(encoding="utf-8")
    )
    gene_result = validate_gene_profile_json_schema(
        json.loads(Path("data/samples/gene_profile_v1.json").read_text(encoding="utf-8"))
    )

    assert wearable_result.passed is True
    assert cgm_result.passed is True
    assert gene_result.passed is True


def test_validate_sensor_file_schemas_flag_missing_and_type_issues() -> None:
    wearable_result = validate_wearable_summary_csv_schema("sleep_hours,restingHR\n6.5,58\n")
    cgm_result = validate_cgm_summary_csv_schema("avg_glucose,timeInRangePct\n6.8,78\n")
    gene_result = validate_gene_profile_json_schema({"markers": {"apoe": "e4"}})

    assert "missing_required_field::wearable_summary::step_summary" in wearable_result.failure_types
    assert "missing_unit::cgm_summary::avg_glucose" in cgm_result.failure_types
    assert "invalid_value_type::gene_profile::genetic_tag_source" in gene_result.failure_types


def test_build_sensor_genetic_file_schema_report_writes_expected_summary(tmp_path) -> None:
    report_json = tmp_path / "sensor_file_schema.json"
    report_md = tmp_path / "sensor_file_schema.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_sensor_genetic_file_schema_report.py",
            "--report-json",
            str(report_json),
            "--report-md",
            str(report_md),
        ],
        capture_output=True,
        check=False,
        cwd="C:/dev/wellnessbox-rnd",
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["valid_fixture_results"]["wearable_summary_csv"]["passed"] is True
    assert payload["valid_fixture_results"]["cgm_summary_csv"]["passed"] is True
    assert payload["valid_fixture_results"]["gene_profile_json"]["passed"] is True
    assert (
        payload["failure_type_examples"]["cgm_missing_unit_for_avg_glucose"]["failure_types"]
        == ["missing_unit::cgm_summary::avg_glucose"]
    )
