import json
import subprocess
import sys

from wellnessbox_rnd.domain.sensor_parser import normalize_sensor_genetic_payloads


def test_normalize_sensor_genetic_payloads_converts_wearable_and_cgm_units() -> None:
    snapshot = normalize_sensor_genetic_payloads(
        wearable_payload={
            "sleepMinutes": 390,
            "step_count": "8450",
            "restingHR": "58",
        },
        cgm_payload={
            "avg_glucose": 6.8,
            "avg_glucose_unit": "mmol/L",
            "timeInRangePct": "78",
            "postMealSpike": True,
        },
    )

    assert snapshot.wearable_available is True
    assert snapshot.cgm_available is True
    assert snapshot.sleep_hours == 6.5
    assert snapshot.steps == 8450
    assert snapshot.resting_heart_rate == 58
    assert snapshot.mean_glucose_mg_dl == 122.4
    assert snapshot.time_in_range_pct == 78.0
    assert snapshot.post_meal_spike_concern is True
    assert "wearable_sleep_minutes_converted_to_hours" in snapshot.normalization_notes
    assert "cgm_mmol_l_converted_to_mg_dl" in snapshot.normalization_notes


def test_normalize_sensor_genetic_payloads_normalizes_genetic_tags() -> None:
    snapshot = normalize_sensor_genetic_payloads(
        genetic_payload={
            "phenotypes": [" Low Sun Exposure ", "glycemic-risk"],
            "markers": ["MTHFR C677T", "APOE-e4"],
        }
    )

    assert snapshot.genetic_available is True
    assert snapshot.genetic_tags == [
        "apoe_e4",
        "glycemic_risk",
        "low_sun_exposure",
        "mthfr_c677t",
    ]
    assert "genetic_tags_normalized_to_snake_case" in snapshot.normalization_notes


def test_normalize_sensor_genetic_payloads_ignores_malformed_numeric_values() -> None:
    snapshot = normalize_sensor_genetic_payloads(
        wearable_payload={
            "sleepHours": "unknown",
            "daily_steps": "n/a",
            "restingHR": "fifty-eight",
        },
        cgm_payload={
            "avg_glucose": "bad",
            "avg_glucose_unit": "mg/dL",
            "timeInRangePct": "?",
            "postMealSpike": "not-sure",
        },
    )

    assert snapshot.sleep_hours is None
    assert snapshot.steps is None
    assert snapshot.resting_heart_rate is None
    assert snapshot.mean_glucose_mg_dl is None
    assert snapshot.time_in_range_pct is None
    assert snapshot.post_meal_spike_concern is False
    assert "wearable_sleep_invalid_numeric_ignored" in snapshot.normalization_notes
    assert "wearable_steps_invalid_numeric_ignored" in snapshot.normalization_notes
    assert "wearable_resting_hr_invalid_numeric_ignored" in snapshot.normalization_notes
    assert "cgm_mean_glucose_invalid_numeric_ignored" in snapshot.normalization_notes
    assert "cgm_time_in_range_invalid_numeric_ignored" in snapshot.normalization_notes


def test_build_sensor_genetic_parser_report_writes_expected_summary(tmp_path) -> None:
    report_json = tmp_path / "parser_smoke.json"
    report_md = tmp_path / "parser_smoke.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_sensor_genetic_parser_report.py",
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
    assert payload["case_count"] == 4
    assert payload["wearable_case_count"] == 2
    assert payload["cgm_case_count"] == 2
    assert payload["genetic_case_count"] == 1
    assert payload["failure_contract_version"] == "sensor_genetic_parser_failure_contract_v1"
    assert payload["supported_failure_types"] == [
        "cgm_mean_glucose_invalid_numeric_ignored",
        "cgm_time_in_range_invalid_numeric_ignored",
        "wearable_resting_hr_invalid_numeric_ignored",
        "wearable_sleep_invalid_numeric_ignored",
        "wearable_steps_invalid_numeric_ignored",
    ]
    assert payload["supported_failure_taxonomy"] == [
        {
            "failure_type": "cgm_mean_glucose_invalid_numeric_ignored",
            "stage": "parser_normalization_fallback",
            "modality": "cgm",
            "family": "invalid_numeric_ignored",
            "field": "mean_glucose",
        },
        {
            "failure_type": "cgm_time_in_range_invalid_numeric_ignored",
            "stage": "parser_normalization_fallback",
            "modality": "cgm",
            "family": "invalid_numeric_ignored",
            "field": "time_in_range",
        },
        {
            "failure_type": "wearable_resting_hr_invalid_numeric_ignored",
            "stage": "parser_normalization_fallback",
            "modality": "wearable",
            "family": "invalid_numeric_ignored",
            "field": "resting_hr",
        },
        {
            "failure_type": "wearable_sleep_invalid_numeric_ignored",
            "stage": "parser_normalization_fallback",
            "modality": "wearable",
            "family": "invalid_numeric_ignored",
            "field": "sleep",
        },
        {
            "failure_type": "wearable_steps_invalid_numeric_ignored",
            "stage": "parser_normalization_fallback",
            "modality": "wearable",
            "family": "invalid_numeric_ignored",
            "field": "steps",
        },
    ]
