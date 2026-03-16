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
    assert payload["case_count"] == 3
    assert payload["wearable_case_count"] == 1
    assert payload["cgm_case_count"] == 1
    assert payload["genetic_case_count"] == 1
