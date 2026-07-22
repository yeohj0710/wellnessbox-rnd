import json
import subprocess
import sys

import pytest

from wellnessbox_rnd.domain.sensor_parser import (
    normalize_cgm_summary_csv,
    normalize_sensor_genetic_payloads,
    normalize_wearable_csv,
)


def test_normalize_generic_wearable_csv_preserves_daily_activity_heart_and_sleep() -> None:
    records = normalize_wearable_csv(
        "date,steps,resting_hr,sleep_minutes\n2026-07-20,8000,61,420\n2026-07-21,9100,59,450\n"
    )

    assert [record.date.isoformat() for record in records] == ["2026-07-20", "2026-07-21"]
    assert records[0].model_dump(mode="json") == {
        "date": "2026-07-20",
        "steps": 8000,
        "resting_heart_rate_bpm": 61.0,
        "sleep_hours": 7.0,
        "source_format": "generic_wearable_csv",
        "source_row_count": 1,
        "normalization_notes": [
            "wearable_sleep_minutes_converted_to_hours",
            "wearable_steps_string_coerced_to_int",
            "wearable_resting_hr_string_coerced_to_int",
        ],
    }


def test_normalize_apple_health_csv_aggregates_supported_records_and_deduplicates() -> None:
    csv_text = (
        "type,startDate,endDate,value,unit\n"
        "HKQuantityTypeIdentifierStepCount,2026-07-21T08:00:00+09:00,2026-07-21T08:10:00+09:00,3000,count\n"
        "HKQuantityTypeIdentifierStepCount,2026-07-21T12:00:00+09:00,2026-07-21T12:10:00+09:00,2500,count\n"
        "HKQuantityTypeIdentifierRestingHeartRate,2026-07-21T07:00:00+09:00,2026-07-21T07:01:00+09:00,60,count/min\n"
        "HKCategoryTypeIdentifierSleepAnalysis,2026-07-21T00:00:00+09:00,2026-07-21T07:30:00+09:00,HKCategoryValueSleepAnalysisAsleep,\n"
        "HKCategoryTypeIdentifierSleepAnalysis,2026-07-21T01:00:00+09:00,2026-07-21T03:00:00+09:00,HKCategoryValueSleepAnalysisAsleepDeep,\n"
        "HKQuantityTypeIdentifierStepCount,2026-07-21T12:00:00+09:00,2026-07-21T12:10:00+09:00,2500,count\n"
    )

    records = normalize_wearable_csv(csv_text)

    assert len(records) == 1
    assert records[0].steps == 5500
    assert records[0].resting_heart_rate_bpm == 60.0
    assert records[0].sleep_hours == 7.5
    assert records[0].source_row_count == 5
    assert records[0].source_format == "apple_health_csv"


def test_normalize_cgm_daily_summary_preserves_glucose_postprandial_and_fixed_tir() -> None:
    records = normalize_cgm_summary_csv(
        "date,avg_glucose,glucose_unit,post_meal_peak,post_meal_rise,time_in_range_70_180_pct\n"
        "2026-07-21,6.8,mmol/L,8.9,2.1,78\n"
    )

    assert records[0].mean_glucose_mg_dl == 122.4
    assert records[0].postprandial_peak_mg_dl == 160.2
    assert records[0].postprandial_rise_mg_dl == 37.8
    assert records[0].time_in_range_pct == 78.0
    assert records[0].time_in_range_low_mg_dl == 70.0
    assert records[0].time_in_range_high_mg_dl == 180.0


def test_cgm_explicit_mg_dl_mean_ignores_generic_mmol_unit() -> None:
    records = normalize_cgm_summary_csv(
        "date,mean_glucose_mg_dl,glucose_unit,postprandial_rise_mg_dl,time_in_range_70_180_pct\n"
        "2026-07-21,120,mmol/L,30,78\n"
    )

    assert records[0].mean_glucose_mg_dl == 120.0


def test_generic_cgm_tir_requires_explicit_standard_bounds() -> None:
    with pytest.raises(ValueError, match="generic_cgm_time_in_range_bounds_required"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_pct\n"
            "2026-07-21,120,30,78\n"
        )

    records = normalize_cgm_summary_csv(
        "date,mean_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_pct,time_in_range_low_mg_dl,time_in_range_high_mg_dl\n"
        "2026-07-21,120,30,78,70,180\n"
    )

    assert records[0].time_in_range_pct == 78.0


def test_cgm_csv_rejects_conflicting_mean_and_tir_aliases() -> None:
    with pytest.raises(ValueError, match="conflicting_cgm_mean_glucose_aliases"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,avg_glucose,glucose_unit,postprandial_rise_mg_dl,time_in_range_70_180_pct\n"
            "2026-07-21,120,8.0,mmol/L,30,78\n"
        )

    with pytest.raises(ValueError, match="conflicting_cgm_time_in_range_aliases"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_70_180_pct,time_in_range_pct,time_in_range_low_mg_dl,time_in_range_high_mg_dl\n"
            "2026-07-21,120,30,78,79,70,180\n"
        )


@pytest.mark.parametrize(
    ("header", "row", "error"),
    [
        (
            "mean_glucose_mg_dl,avg_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_70_180_pct",
            "120,240,30,78",
            "conflicting_cgm_mean_glucose_aliases",
        ),
        (
            "mean_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_70_180_pct,timeInRange70To180Pct",
            "120,30,78,42",
            "conflicting_cgm_time_in_range_aliases",
        ),
        (
            "mean_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_pct,timeInRangePct,time_in_range_low_mg_dl,time_in_range_high_mg_dl",
            "120,30,78,42,70,180",
            "conflicting_cgm_time_in_range_aliases",
        ),
        (
            "mean_glucose_mg_dl,postprandial_peak_mg_dl,post_meal_peak_mg_dl,time_in_range_70_180_pct",
            "120,160,300,78",
            "conflicting_cgm_postprandial_peak_aliases",
        ),
        (
            "mean_glucose_mg_dl,postprandial_rise_mg_dl,post_meal_rise_mg_dl,time_in_range_70_180_pct",
            "120,30,60,78",
            "conflicting_cgm_postprandial_rise_aliases",
        ),
    ],
)
def test_cgm_csv_rejects_conflicts_inside_alias_groups(
    header: str, row: str, error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        normalize_cgm_summary_csv(f"date,{header}\n2026-07-21,{row}\n")


def test_cgm_csv_compares_explicit_and_generic_postprandial_units() -> None:
    equivalent = normalize_cgm_summary_csv(
        "date,mean_glucose_mg_dl,glucose_unit,postprandial_peak_mg_dl,post_meal_peak,time_in_range_70_180_pct\n"
        "2026-07-21,120,mmol/L,160.2,8.9,78\n"
    )
    assert equivalent[0].postprandial_peak_mg_dl == 160.2

    with pytest.raises(ValueError, match="conflicting_cgm_postprandial_peak_aliases"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,glucose_unit,postprandial_peak_mg_dl,post_meal_peak,time_in_range_70_180_pct\n"
            "2026-07-21,120,mmol/L,160,20,78\n"
        )
    with pytest.raises(ValueError, match="conflicting_cgm_postprandial_rise_aliases"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,glucose_unit,postprandial_rise_mg_dl,post_meal_rise,time_in_range_70_180_pct\n"
            "2026-07-21,120,mmol/L,30,10,78\n"
        )


@pytest.mark.parametrize(
    ("record_type", "unit", "error"),
    [
        ("HKQuantityTypeIdentifierStepCount", "km", "unsupported_apple_health_step_unit"),
        (
            "HKQuantityTypeIdentifierRestingHeartRate",
            "meters",
            "unsupported_apple_health_resting_heart_rate_unit",
        ),
    ],
)
def test_apple_health_rejects_units_that_change_metric_semantics(
    record_type: str, unit: str, error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        normalize_wearable_csv(
            "type,startDate,endDate,value,unit\n"
            f"{record_type},2026-07-21T08:00:00+09:00,"
            f"2026-07-21T08:10:00+09:00,12,{unit}\n"
        )


def test_daily_sensor_csv_rejects_duplicate_dates_and_nonstandard_tir_bounds() -> None:
    with pytest.raises(ValueError, match="duplicate_wearable_daily_summary_date"):
        normalize_wearable_csv(
            "date,steps,resting_hr,sleep_hours\n2026-07-21,8000,60,7\n2026-07-21,9000,59,8\n"
        )
    with pytest.raises(ValueError, match="bounds_mismatch"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,postprandial_rise_mg_dl,time_in_range_70_180_pct,time_in_range_low_mg_dl,time_in_range_high_mg_dl\n"
            "2026-07-21,120,30,78,80,140\n"
        )
    with pytest.raises(ValueError, match="postprandial_metric_required"):
        normalize_cgm_summary_csv(
            "date,mean_glucose_mg_dl,time_in_range_70_180_pct\n2026-07-21,120,78\n"
        )


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


def test_standardized_cgm_tir_alias_records_ada_range_bounds() -> None:
    snapshot = normalize_sensor_genetic_payloads(cgm_payload={"time_in_range_70_180_pct": 68.0})

    assert snapshot.time_in_range_pct == 68.0
    assert snapshot.time_in_range_low_mg_dl == 70.0
    assert snapshot.time_in_range_high_mg_dl == 180.0


def test_conflicting_cgm_tir_aliases_fail_closed() -> None:
    with pytest.raises(ValueError, match="conflicting_cgm_time_in_range_aliases"):
        normalize_sensor_genetic_payloads(
            cgm_payload={
                "time_in_range_pct": 10.0,
                "time_in_range_70_180_pct": 90.0,
            }
        )
    with pytest.raises(ValueError, match="bounds_mismatch"):
        normalize_sensor_genetic_payloads(
            cgm_payload={
                "time_in_range_70_180_pct": 90.0,
                "time_in_range_low_mg_dl": 80.0,
                "time_in_range_high_mg_dl": 140.0,
            }
        )
    with pytest.raises(ValueError, match="bounds_invalid"):
        normalize_sensor_genetic_payloads(
            cgm_payload={
                "time_in_range_70_180_pct": 90.0,
                "time_in_range_low_mg_dl": "bad",
                "time_in_range_high_mg_dl": 180.0,
            }
        )


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
