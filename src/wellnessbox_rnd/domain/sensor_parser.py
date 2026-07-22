from __future__ import annotations

import csv
import re
from datetime import date, datetime
from io import StringIO
from typing import Any, Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import (
    NormalizedGeneticVariant,
    NormalizedSensorGeneticSnapshot,
)


class SensorFileSchemaValidationResult(BaseModel):
    format_name: str
    passed: bool
    detected_fields: list[str] = Field(default_factory=list)
    failure_types: list[str] = Field(default_factory=list)
    accepted_aliases: dict[str, list[str]] = Field(default_factory=dict)


class NormalizedWearableDailySummary(BaseModel):
    date: date
    steps: int | None = Field(default=None, ge=0, le=200_000)
    resting_heart_rate_bpm: float | None = Field(default=None, ge=20, le=250)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    source_format: Literal["apple_health_csv", "generic_wearable_csv"]
    source_row_count: int = Field(ge=1)
    normalization_notes: list[str] = Field(default_factory=list)


class NormalizedCgmDailySummary(BaseModel):
    date: date
    mean_glucose_mg_dl: float = Field(ge=20, le=600)
    postprandial_peak_mg_dl: float | None = Field(default=None, ge=20, le=600)
    postprandial_rise_mg_dl: float | None = Field(default=None, ge=0, le=580)
    time_in_range_pct: float = Field(ge=0, le=100)
    time_in_range_low_mg_dl: float = Field(default=70, ge=20, le=600)
    time_in_range_high_mg_dl: float = Field(default=180, ge=20, le=600)
    source_row_count: int = Field(default=1, ge=1)
    normalization_notes: list[str] = Field(default_factory=list)


WEARABLE_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "sleep_summary": (
        "sleep_hours",
        "sleepHours",
        "sleep_minutes",
        "sleepMinutes",
        "sleep_duration_minutes",
    ),
    "step_summary": ("steps", "step_count", "daily_steps"),
    "resting_hr_summary": ("resting_heart_rate", "restingHR", "resting_hr"),
}
CGM_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "mean_glucose_summary": (
        "mean_glucose_mg_dl",
        "avg_glucose_mg_dl",
        "mean_glucose_mmol_l",
        "avg_glucose_mmol_l",
        "avg_glucose",
    ),
    "time_in_range_summary": (
        "time_in_range_pct",
        "timeInRangePct",
        "time_in_range_70_180_pct",
        "timeInRange70To180Pct",
    ),
    "postprandial_summary": (
        "postprandial_peak_mg_dl",
        "post_meal_peak_mg_dl",
        "postprandial_rise_mg_dl",
        "post_meal_rise_mg_dl",
    ),
}
GENE_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "genetic_tag_source": ("phenotypes", "risk_flags", "markers", "gene_markers"),
    "variant_source": ("variants", "variant_results", "genotypes"),
}

GENETIC_INTERPRETATION_ALIASES = {
    "increased_risk": "increased_risk",
    "high_risk": "increased_risk",
    "risk": "increased_risk",
    "typical": "typical",
    "normal": "typical",
    "average": "typical",
    "reduced_risk": "reduced_risk",
    "low_risk": "reduced_risk",
    "carrier": "carrier",
    "indeterminate": "indeterminate",
    "uncertain": "indeterminate",
    "vus": "indeterminate",
}


def normalize_wearable_csv(csv_text: str) -> list[NormalizedWearableDailySummary]:
    reader = csv.DictReader(StringIO(csv_text))
    headers = set(reader.fieldnames or [])
    rows = list(reader)
    if not headers or not rows:
        raise ValueError("wearable_csv_header_and_rows_required")
    if {"type", "startDate", "value"}.issubset(headers):
        return _normalize_apple_health_rows(rows)
    return _normalize_generic_wearable_rows(rows)


def normalize_cgm_summary_csv(csv_text: str) -> list[NormalizedCgmDailySummary]:
    reader = csv.DictReader(StringIO(csv_text))
    rows = list(reader)
    if not reader.fieldnames or not rows:
        raise ValueError("cgm_csv_header_and_rows_required")
    normalized: list[NormalizedCgmDailySummary] = []
    seen_dates: set[date] = set()
    for row in rows:
        observed_date = _parse_date(_first_present(row, "date", "day", "recorded_date"))
        if observed_date in seen_dates:
            raise ValueError("duplicate_cgm_daily_summary_date")
        seen_dates.add(observed_date)
        unit = _normalize_unit(_first_present(row, "glucose_unit", "avg_glucose_unit"))
        _require_consistent_numeric_aliases(
            row,
            ("mean_glucose_mg_dl", "avg_glucose_mg_dl"),
            error="conflicting_cgm_mean_glucose_aliases",
        )
        explicit_mean_mg_dl = _first_present(
            row, "mean_glucose_mg_dl", "avg_glucose_mg_dl"
        )
        generic_mean = _first_present(row, "avg_glucose")
        if explicit_mean_mg_dl is not None and generic_mean is not None:
            explicit_mean = _required_glucose_mg_dl(
                explicit_mean_mg_dl, unit="mg/dl", field="mean_glucose"
            )
            normalized_generic_mean = _required_glucose_mg_dl(
                generic_mean, unit=unit, field="mean_glucose"
            )
            if explicit_mean != normalized_generic_mean:
                raise ValueError("conflicting_cgm_mean_glucose_aliases")
        mean = _required_glucose_mg_dl(
            _first_present(row, "mean_glucose_mg_dl", "avg_glucose_mg_dl", "avg_glucose"),
            unit="mg/dl" if explicit_mean_mg_dl is not None else unit,
            field="mean_glucose",
        )
        peak_value = _first_present(
            row, "postprandial_peak_mg_dl", "post_meal_peak_mg_dl", "post_meal_peak"
        )
        _require_consistent_numeric_aliases(
            row,
            ("postprandial_peak_mg_dl", "post_meal_peak_mg_dl"),
            error="conflicting_cgm_postprandial_peak_aliases",
        )
        explicit_peak_mg_dl = _first_present(
            row, "postprandial_peak_mg_dl", "post_meal_peak_mg_dl"
        )
        generic_peak = _first_present(row, "post_meal_peak")
        if explicit_peak_mg_dl is not None and generic_peak is not None:
            if _required_glucose_mg_dl(
                explicit_peak_mg_dl, unit="mg/dl", field="postprandial_peak"
            ) != _required_glucose_mg_dl(
                generic_peak, unit=unit, field="postprandial_peak"
            ):
                raise ValueError("conflicting_cgm_postprandial_peak_aliases")
        rise_value = _first_present(
            row, "postprandial_rise_mg_dl", "post_meal_rise_mg_dl", "post_meal_rise"
        )
        _require_consistent_numeric_aliases(
            row,
            ("postprandial_rise_mg_dl", "post_meal_rise_mg_dl"),
            error="conflicting_cgm_postprandial_rise_aliases",
        )
        explicit_rise_mg_dl = _first_present(
            row, "postprandial_rise_mg_dl", "post_meal_rise_mg_dl"
        )
        generic_rise = _first_present(row, "post_meal_rise")
        if explicit_rise_mg_dl is not None and generic_rise is not None:
            if _required_glucose_mg_dl(
                explicit_rise_mg_dl, unit="mg/dl", field="postprandial_rise"
            ) != _required_glucose_mg_dl(
                generic_rise, unit=unit, field="postprandial_rise"
            ):
                raise ValueError("conflicting_cgm_postprandial_rise_aliases")
        peak = (
            None
            if peak_value is None
            else _required_glucose_mg_dl(
                peak_value,
                unit=(
                    "mg/dl"
                    if _first_present(row, "postprandial_peak_mg_dl", "post_meal_peak_mg_dl")
                    is not None
                    else unit
                ),
                field="postprandial_peak",
            )
        )
        rise = _coerce_float(rise_value)
        if rise_value is not None and rise is None:
            raise ValueError("invalid_cgm_postprandial_rise")
        rise_has_explicit_mg_dl = (
            _first_present(row, "postprandial_rise_mg_dl", "post_meal_rise_mg_dl") is not None
        )
        if rise is not None and unit == "mmol/l" and not rise_has_explicit_mg_dl:
            rise = round(rise * 18.0, 1)
        if peak is None and rise is None:
            raise ValueError("cgm_postprandial_metric_required")
        standardized_tir_value = _first_present(
            row, "time_in_range_70_180_pct", "timeInRange70To180Pct"
        )
        generic_tir_value = _first_present(row, "time_in_range_pct", "timeInRangePct")
        _require_consistent_numeric_aliases(
            row,
            ("time_in_range_70_180_pct", "timeInRange70To180Pct"),
            error="conflicting_cgm_time_in_range_aliases",
        )
        _require_consistent_numeric_aliases(
            row,
            ("time_in_range_pct", "timeInRangePct"),
            error="conflicting_cgm_time_in_range_aliases",
        )
        if standardized_tir_value is not None and generic_tir_value is not None:
            standardized_tir = _coerce_float(standardized_tir_value)
            generic_tir = _coerce_float(generic_tir_value)
            if standardized_tir != generic_tir:
                raise ValueError("conflicting_cgm_time_in_range_aliases")
        tir = _coerce_float(
            standardized_tir_value
            if standardized_tir_value is not None
            else generic_tir_value
        )
        if tir is None:
            raise ValueError("invalid_cgm_time_in_range")
        low = _coerce_float(row.get("time_in_range_low_mg_dl"))
        high = _coerce_float(row.get("time_in_range_high_mg_dl"))
        if standardized_tir_value is None and (low != 70.0 or high != 180.0):
            raise ValueError("generic_cgm_time_in_range_bounds_required")
        if low not in {None, 70.0} or high not in {None, 180.0}:
            raise ValueError("standardized_cgm_time_in_range_bounds_mismatch")
        normalized.append(
            NormalizedCgmDailySummary(
                date=observed_date,
                mean_glucose_mg_dl=mean,
                postprandial_peak_mg_dl=peak,
                postprandial_rise_mg_dl=rise,
                time_in_range_pct=tir,
                source_row_count=1,
                normalization_notes=(["cgm_mmol_l_converted_to_mg_dl"] if unit == "mmol/l" else []),
            )
        )
    return normalized


def _normalize_generic_wearable_rows(
    rows: list[dict[str, str]],
) -> list[NormalizedWearableDailySummary]:
    normalized: list[NormalizedWearableDailySummary] = []
    seen_dates: set[date] = set()
    for row in rows:
        observed_date = _parse_date(_first_present(row, "date", "day", "recorded_date"))
        if observed_date in seen_dates:
            raise ValueError("duplicate_wearable_daily_summary_date")
        seen_dates.add(observed_date)
        sleep, steps, resting_hr, notes = _normalize_wearable_payload(row)
        if sleep is None and steps is None and resting_hr is None:
            raise ValueError("wearable_daily_summary_has_no_metrics")
        normalized.append(
            NormalizedWearableDailySummary(
                date=observed_date,
                steps=steps,
                resting_heart_rate_bpm=resting_hr,
                sleep_hours=sleep,
                source_format="generic_wearable_csv",
                source_row_count=1,
                normalization_notes=notes,
            )
        )
    return normalized


def _normalize_apple_health_rows(
    rows: list[dict[str, str]],
) -> list[NormalizedWearableDailySummary]:
    grouped: dict[date, dict[str, Any]] = {}
    seen_records: set[tuple[str, str, str, str, str]] = set()
    for row in rows:
        record_type = str(row.get("type", "")).strip()
        start_text = str(row.get("startDate", "")).strip()
        end_text = str(row.get("endDate", "")).strip()
        value_text = str(row.get("value", "")).strip()
        unit = str(row.get("unit", "")).strip()
        identity = (record_type, start_text, end_text, value_text, unit)
        if identity in seen_records:
            continue
        seen_records.add(identity)
        start = _parse_datetime(start_text)
        bucket = grouped.setdefault(
            start.date(),
            {"steps": 0.0, "heart_rates": [], "sleep_intervals": [], "rows": 0},
        )
        if record_type.endswith("StepCount"):
            if unit.lower() != "count":
                raise ValueError("unsupported_apple_health_step_unit")
            value = _required_float(value_text, "apple_health_steps")
            bucket["steps"] += value
        elif record_type.endswith("RestingHeartRate"):
            if unit.lower() not in {"count/min", "bpm", "beats/min", "beats/minute"}:
                raise ValueError("unsupported_apple_health_resting_heart_rate_unit")
            bucket["heart_rates"].append(
                _required_float(value_text, "apple_health_resting_heart_rate")
            )
        elif record_type.endswith("SleepAnalysis") and "asleep" in value_text.lower():
            end = _parse_datetime(end_text)
            duration = (end - start).total_seconds() / 3600
            if duration <= 0 or duration > 24:
                raise ValueError("invalid_apple_health_sleep_interval")
            bucket["sleep_intervals"].append((start, end))
        else:
            continue
        bucket["rows"] += 1
    normalized: list[NormalizedWearableDailySummary] = []
    for observed_date in sorted(grouped):
        bucket = grouped[observed_date]
        if bucket["rows"] == 0:
            continue
        heart_rates = bucket["heart_rates"]
        sleep_hours = _merged_interval_hours(bucket["sleep_intervals"])
        normalized.append(
            NormalizedWearableDailySummary(
                date=observed_date,
                steps=round(bucket["steps"]) if bucket["steps"] else None,
                resting_heart_rate_bpm=(
                    round(sum(heart_rates) / len(heart_rates), 1) if heart_rates else None
                ),
                sleep_hours=round(sleep_hours, 2) if sleep_hours else None,
                source_format="apple_health_csv",
                source_row_count=bucket["rows"],
                normalization_notes=["apple_health_records_aggregated_by_start_date"],
            )
        )
    if not normalized:
        raise ValueError("apple_health_csv_has_no_supported_records")
    return normalized


def normalize_sensor_genetic_payloads(
    *,
    wearable_payload: dict[str, Any] | None = None,
    cgm_payload: dict[str, Any] | None = None,
    genetic_payload: dict[str, Any] | None = None,
) -> NormalizedSensorGeneticSnapshot:
    notes: list[str] = []

    wearable_sleep_hours, wearable_steps, resting_hr, wearable_notes = _normalize_wearable_payload(
        wearable_payload or {}
    )
    notes.extend(wearable_notes)

    (
        mean_glucose_mg_dl,
        time_in_range_pct,
        postprandial_peak_mg_dl,
        postprandial_rise_mg_dl,
        post_meal_spike_concern,
        cgm_notes,
    ) = _normalize_cgm_payload(cgm_payload or {})
    notes.extend(cgm_notes)
    cgm_input = cgm_payload or {}
    tir_aliases = (
        "time_in_range_pct",
        "timeInRangePct",
        "time_in_range_70_180_pct",
        "timeInRange70To180Pct",
    )
    supplied_tir_values = [
        _coerce_float(cgm_input[key])
        for key in tir_aliases
        if key in cgm_input and cgm_input[key] is not None
    ]
    if len(supplied_tir_values) > 1 and (
        any(value is None for value in supplied_tir_values)
        or len({value for value in supplied_tir_values if value is not None}) != 1
    ):
        raise ValueError("conflicting_cgm_time_in_range_aliases")
    standardized_tir = _first_present(
        cgm_input,
        "time_in_range_70_180_pct",
        "timeInRange70To180Pct",
    )
    if standardized_tir is not None:
        supplied_low = _coerce_float(cgm_input.get("time_in_range_low_mg_dl"))
        supplied_high = _coerce_float(cgm_input.get("time_in_range_high_mg_dl"))
        if (
            "time_in_range_low_mg_dl" in cgm_input
            and cgm_input["time_in_range_low_mg_dl"] is not None
            and supplied_low is None
        ) or (
            "time_in_range_high_mg_dl" in cgm_input
            and cgm_input["time_in_range_high_mg_dl"] is not None
            and supplied_high is None
        ):
            raise ValueError("standardized_cgm_time_in_range_bounds_invalid")
        if supplied_low not in {None, 70.0} or supplied_high not in {None, 180.0}:
            raise ValueError("standardized_cgm_time_in_range_bounds_mismatch")
        time_in_range_low_mg_dl = 70.0
        time_in_range_high_mg_dl = 180.0
    else:
        time_in_range_low_mg_dl = _coerce_float(
            _first_present(cgm_input, "time_in_range_low_mg_dl")
        )
        time_in_range_high_mg_dl = _coerce_float(
            _first_present(cgm_input, "time_in_range_high_mg_dl")
        )

    genetic_tags, genetic_variants, genetic_notes = _normalize_genetic_payload(
        genetic_payload or {}
    )
    notes.extend(genetic_notes)

    return NormalizedSensorGeneticSnapshot(
        wearable_available=bool(wearable_payload),
        cgm_available=bool(cgm_payload),
        genetic_available=bool(genetic_payload),
        sleep_hours=wearable_sleep_hours,
        steps=wearable_steps,
        resting_heart_rate=resting_hr,
        mean_glucose_mg_dl=mean_glucose_mg_dl,
        time_in_range_pct=time_in_range_pct,
        time_in_range_low_mg_dl=time_in_range_low_mg_dl,
        time_in_range_high_mg_dl=time_in_range_high_mg_dl,
        postprandial_peak_mg_dl=postprandial_peak_mg_dl,
        postprandial_rise_mg_dl=postprandial_rise_mg_dl,
        post_meal_spike_concern=post_meal_spike_concern,
        genetic_tags=genetic_tags,
        genetic_variants=genetic_variants,
        normalization_notes=notes,
    )


def validate_wearable_summary_csv_schema(csv_text: str) -> SensorFileSchemaValidationResult:
    rows, headers, issues = _parse_summary_csv(csv_text=csv_text, format_name="wearable_summary")
    if rows:
        row = rows[0]
        _validate_required_alias_groups(
            row=row,
            alias_groups=WEARABLE_ALIAS_GROUPS,
            issues=issues,
            prefix="wearable_summary",
        )
        _validate_numeric_field_group(
            row=row,
            alias_group=WEARABLE_ALIAS_GROUPS["sleep_summary"],
            issues=issues,
            prefix="wearable_summary",
            allow_float=True,
        )
        _validate_numeric_field_group(
            row=row,
            alias_group=WEARABLE_ALIAS_GROUPS["step_summary"],
            issues=issues,
            prefix="wearable_summary",
            allow_float=False,
        )
        _validate_numeric_field_group(
            row=row,
            alias_group=WEARABLE_ALIAS_GROUPS["resting_hr_summary"],
            issues=issues,
            prefix="wearable_summary",
            allow_float=False,
        )
    return SensorFileSchemaValidationResult(
        format_name="wearable_summary.csv",
        passed=not issues,
        detected_fields=headers,
        failure_types=issues,
        accepted_aliases={key: list(value) for key, value in WEARABLE_ALIAS_GROUPS.items()},
    )


def validate_cgm_summary_csv_schema(csv_text: str) -> SensorFileSchemaValidationResult:
    rows, headers, issues = _parse_summary_csv(csv_text=csv_text, format_name="cgm_summary")
    if rows:
        row = rows[0]
        _validate_required_alias_groups(
            row=row,
            alias_groups=CGM_ALIAS_GROUPS,
            issues=issues,
            prefix="cgm_summary",
        )
        _validate_numeric_field_group(
            row=row,
            alias_group=CGM_ALIAS_GROUPS["mean_glucose_summary"],
            issues=issues,
            prefix="cgm_summary",
            allow_float=True,
        )
        _validate_numeric_field_group(
            row=row,
            alias_group=CGM_ALIAS_GROUPS["time_in_range_summary"],
            issues=issues,
            prefix="cgm_summary",
            allow_float=True,
        )
        if (
            _first_present(row, "avg_glucose") is not None
            and _first_present(row, "avg_glucose_unit", "glucose_unit") is None
        ):
            issues.append("missing_unit::cgm_summary::avg_glucose")
    return SensorFileSchemaValidationResult(
        format_name="cgm_summary.csv",
        passed=not issues,
        detected_fields=headers,
        failure_types=issues,
        accepted_aliases={key: list(value) for key, value in CGM_ALIAS_GROUPS.items()},
    )


def validate_gene_profile_json_schema(payload: Any) -> SensorFileSchemaValidationResult:
    issues: list[str] = []
    if not isinstance(payload, dict):
        issues.append("invalid_payload_type::gene_profile::expected_object")
        return SensorFileSchemaValidationResult(
            format_name="gene_profile.json",
            passed=False,
            failure_types=issues,
            accepted_aliases={key: list(value) for key, value in GENE_ALIAS_GROUPS.items()},
        )

    if all(
        _first_present(payload, *aliases) is None
        for aliases in GENE_ALIAS_GROUPS.values()
    ):
        issues.append("missing_required_field::gene_profile::tag_or_variant_source")
    present_value = _first_present(payload, *GENE_ALIAS_GROUPS["genetic_tag_source"])
    if present_value is not None and not isinstance(present_value, (str, list)):
        issues.append("invalid_value_type::gene_profile::genetic_tag_source")
    try:
        _normalize_genetic_payload(payload)
    except (TypeError, ValueError) as error:
        issues.append(f"invalid_gene_profile::{error}")

    return SensorFileSchemaValidationResult(
        format_name="gene_profile.json",
        passed=not issues,
        detected_fields=sorted(payload),
        failure_types=issues,
        accepted_aliases={key: list(value) for key, value in GENE_ALIAS_GROUPS.items()},
    )


def _normalize_wearable_payload(
    payload: dict[str, Any],
) -> tuple[float | None, int | None, int | None, list[str]]:
    notes: list[str] = []
    raw_sleep_hours = _first_present(payload, "sleep_hours", "sleepHours")
    sleep_hours = _coerce_float(raw_sleep_hours)
    if raw_sleep_hours is not None and sleep_hours is None:
        notes.append("wearable_sleep_invalid_numeric_ignored")
    if sleep_hours is None:
        raw_sleep_minutes = _first_present(
            payload,
            "sleep_minutes",
            "sleepMinutes",
            "sleep_duration_minutes",
        )
        sleep_minutes = _coerce_float(raw_sleep_minutes)
        if raw_sleep_minutes is not None and sleep_minutes is None:
            notes.append("wearable_sleep_invalid_numeric_ignored")
        if sleep_minutes is not None:
            sleep_hours = round(sleep_minutes / 60.0, 2)
            notes.append("wearable_sleep_minutes_converted_to_hours")

    raw_steps = _first_present(payload, "steps", "step_count", "daily_steps")
    steps = _coerce_int(raw_steps)
    if raw_steps is not None and steps is None:
        notes.append("wearable_steps_invalid_numeric_ignored")
    elif steps is not None and isinstance(raw_steps, str):
        notes.append("wearable_steps_string_coerced_to_int")

    raw_resting_hr = _first_present(payload, "resting_heart_rate", "restingHR", "resting_hr")
    resting_hr = _coerce_int(raw_resting_hr)
    if raw_resting_hr is not None and resting_hr is None:
        notes.append("wearable_resting_hr_invalid_numeric_ignored")
    elif resting_hr is not None and isinstance(raw_resting_hr, str):
        notes.append("wearable_resting_hr_string_coerced_to_int")

    return sleep_hours, steps, resting_hr, notes


def _normalize_cgm_payload(
    payload: dict[str, Any],
) -> tuple[float | None, float | None, float | None, float | None, bool, list[str]]:
    notes: list[str] = []
    mean_glucose_mg_dl = _coerce_float(
        _first_present(payload, "mean_glucose_mg_dl", "avg_glucose_mg_dl")
    )
    if (
        _first_present(payload, "mean_glucose_mg_dl", "avg_glucose_mg_dl") is not None
        and mean_glucose_mg_dl is None
    ):
        notes.append("cgm_mean_glucose_invalid_numeric_ignored")
    if mean_glucose_mg_dl is None:
        raw_mmol_value = _first_present(payload, "mean_glucose_mmol_l", "avg_glucose_mmol_l")
        mmol_value = _coerce_float(raw_mmol_value)
        if raw_mmol_value is not None and mmol_value is None:
            notes.append("cgm_mean_glucose_invalid_numeric_ignored")
        if mmol_value is None:
            raw_avg_glucose = _first_present(payload, "avg_glucose")
            avg_glucose = _coerce_float(raw_avg_glucose)
            avg_unit = _normalize_unit(_first_present(payload, "avg_glucose_unit", "glucose_unit"))
            if raw_avg_glucose is not None and avg_glucose is None:
                notes.append("cgm_mean_glucose_invalid_numeric_ignored")
            if avg_glucose is not None and avg_unit == "mmol/l":
                mmol_value = avg_glucose
            elif avg_glucose is not None and avg_unit == "mg/dl":
                mean_glucose_mg_dl = avg_glucose
        if mmol_value is not None:
            mean_glucose_mg_dl = round(mmol_value * 18.0, 1)
            notes.append("cgm_mmol_l_converted_to_mg_dl")

    time_in_range_pct = _coerce_float(
        _first_present(
            payload,
            "time_in_range_pct",
            "timeInRangePct",
            "time_in_range_70_180_pct",
            "timeInRange70To180Pct",
        )
    )
    raw_time_in_range_pct = _first_present(
        payload,
        "time_in_range_pct",
        "timeInRangePct",
        "time_in_range_70_180_pct",
        "timeInRange70To180Pct",
    )
    if raw_time_in_range_pct is not None and time_in_range_pct is None:
        notes.append("cgm_time_in_range_invalid_numeric_ignored")
    elif time_in_range_pct is not None and isinstance(raw_time_in_range_pct, str):
        notes.append("cgm_time_in_range_string_coerced_to_float")

    post_meal_spike_concern = _coerce_bool(
        _first_present(payload, "post_meal_spike", "postMealSpike", "post_meal_spike_concern")
    )
    postprandial_peak_mg_dl = _coerce_float(
        _first_present(payload, "postprandial_peak_mg_dl", "post_meal_peak_mg_dl")
    )
    postprandial_rise_mg_dl = _coerce_float(
        _first_present(payload, "postprandial_rise_mg_dl", "post_meal_rise_mg_dl")
    )
    return (
        mean_glucose_mg_dl,
        time_in_range_pct,
        postprandial_peak_mg_dl,
        postprandial_rise_mg_dl,
        post_meal_spike_concern,
        notes,
    )


def _normalize_genetic_payload(
    payload: dict[str, Any],
) -> tuple[list[str], list[NormalizedGeneticVariant], list[str]]:
    notes: list[str] = []
    raw_values: list[str] = []
    for key in ("phenotypes", "risk_flags", "markers", "gene_markers"):
        raw_value = payload.get(key)
        if raw_value is None:
            continue
        raw_values.extend(_as_string_list(raw_value))
    normalized = sorted({_slugify(value) for value in raw_values if _slugify(value)})
    raw_variants = _single_consistent_alias_value(
        payload,
        GENE_ALIAS_GROUPS["variant_source"],
        error="conflicting_genetic_variant_sources",
    )
    if raw_variants is None:
        variants: list[NormalizedGeneticVariant] = []
    elif not isinstance(raw_variants, list):
        raise ValueError("genetic_variants_must_be_list")
    else:
        variants = [_normalize_genetic_variant(item) for item in raw_variants]
        variants.sort(key=lambda item: (item.gene_symbol, item.variant_id, item.tested_on))
        keys = [(item.gene_symbol, item.variant_id, item.tested_on) for item in variants]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate_genetic_variant")
    if normalized:
        notes.append("genetic_tags_normalized_to_snake_case")
    if variants:
        notes.append("genetic_variants_normalized_with_provenance")
    return normalized, variants, notes


def _normalize_genetic_variant(value: Any) -> NormalizedGeneticVariant:
    if not isinstance(value, dict):
        raise ValueError("genetic_variant_must_be_object")
    gene = _required_consistent_text_alias(
        value, ("gene_symbol", "gene"), field="gene_symbol"
    ).upper()
    variant_id = _required_consistent_text_alias(
        value, ("variant_id", "variant", "rsid"), field="variant_id"
    )
    variant_id = variant_id.lower() if re.fullmatch(r"RS\d+", variant_id, re.I) else variant_id
    genotype = _required_consistent_text_alias(
        value, ("genotype", "call", "result"), field="genotype"
    ).upper().replace("|", "/")
    if "/" in genotype:
        genotype = "/".join(sorted(part.strip() for part in genotype.split("/")))
    raw_interpretation = _slugify(
        _required_consistent_text_alias(
            value,
            ("interpretation", "classification", "risk_assessment"),
            field="interpretation",
        )
    )
    interpretation = GENETIC_INTERPRETATION_ALIASES.get(raw_interpretation)
    if interpretation is None:
        raise ValueError("unsupported_genetic_interpretation")
    criterion = _required_consistent_text_alias(
        value,
        ("interpretation_criterion", "criterion", "basis"),
        field="interpretation_criterion",
    )
    laboratory = _required_consistent_text_alias(
        value,
        ("testing_laboratory", "laboratory", "lab", "testing_lab"),
        field="testing_laboratory",
    )
    tested_on_raw = _required_consistent_text_alias(
        value,
        ("tested_on", "test_date", "collection_date"),
        field="tested_on",
    )
    try:
        tested_on = date.fromisoformat(tested_on_raw)
    except ValueError as error:
        raise ValueError("genetic_test_date_must_be_iso_date") from error
    return NormalizedGeneticVariant(
        gene_symbol=gene,
        variant_id=variant_id,
        genotype=genotype,
        interpretation=interpretation,
        interpretation_criterion=" ".join(criterion.split()),
        testing_laboratory=" ".join(laboratory.split()),
        tested_on=tested_on,
    )


def _single_consistent_alias_value(
    payload: dict[str, Any], aliases: tuple[str, ...], *, error: str
) -> Any:
    values = [payload[key] for key in aliases if key in payload and payload[key] is not None]
    if len(values) > 1 and any(value != values[0] for value in values[1:]):
        raise ValueError(error)
    return values[0] if values else None


def _required_consistent_text_alias(
    payload: dict[str, Any], aliases: tuple[str, ...], *, field: str
) -> str:
    values = [
        str(payload[key]).strip()
        for key in aliases
        if key in payload and payload[key] is not None and str(payload[key]).strip()
    ]
    if not values:
        raise ValueError(f"genetic_variant_{field}_required")
    normalized = [" ".join(value.split()) for value in values]
    if any(value.casefold() != normalized[0].casefold() for value in normalized[1:]):
        raise ValueError(f"conflicting_genetic_variant_{field}_aliases")
    return normalized[0]


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _require_consistent_numeric_aliases(
    payload: dict[str, Any], aliases: tuple[str, ...], *, error: str
) -> None:
    values = [
        _coerce_float(payload[alias])
        for alias in aliases
        if alias in payload and payload[alias] is not None
    ]
    if len(values) > 1 and any(value != values[0] for value in values[1:]):
        raise ValueError(error)


def _parse_date(value: Any) -> date:
    if value is None or not str(value).strip():
        raise ValueError("sensor_daily_summary_date_required")
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as error:
        raise ValueError("sensor_daily_summary_date_invalid") from error


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    for candidate in (normalized, normalized.replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("timezone_required")
            return parsed
        except ValueError:
            continue
    raise ValueError("apple_health_datetime_invalid_or_timezone_missing")


def _merged_interval_hours(intervals: list[tuple[datetime, datetime]]) -> float:
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    merged: list[tuple[datetime, datetime]] = []
    for start, end in ordered:
        if not merged or start >= merged[-1][1]:
            merged.append((start, end))
        else:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
    return sum((end - start).total_seconds() for start, end in merged) / 3600


def _required_float(value: Any, field: str) -> float:
    parsed = _coerce_float(value)
    if parsed is None:
        raise ValueError(f"invalid_numeric_value::{field}")
    return parsed


def _required_glucose_mg_dl(value: Any, *, unit: str | None, field: str) -> float:
    parsed = _required_float(value, field)
    if unit in {None, "mg/dl"}:
        return parsed
    if unit == "mmol/l":
        return round(parsed * 18.0, 1)
    raise ValueError(f"unsupported_glucose_unit::{unit}")


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _coerce_int(value: Any) -> int | None:
    coerced = _coerce_float(value)
    if coerced is None:
        return None
    return int(round(coerced))


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _normalize_unit(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized


def _parse_summary_csv(
    *,
    csv_text: str,
    format_name: str,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    issues: list[str] = []
    try:
        reader = csv.DictReader(StringIO(csv_text))
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    except csv.Error:
        return [], [], [f"invalid_csv::{format_name}"]

    if not headers:
        issues.append(f"missing_header::{format_name}")
    if not rows:
        issues.append(f"missing_rows::{format_name}")
    elif len(rows) != 1:
        issues.append(f"unexpected_row_count::{format_name}::{len(rows)}")
    return rows, headers, issues


def _validate_required_alias_groups(
    *,
    row: dict[str, Any],
    alias_groups: dict[str, tuple[str, ...]],
    issues: list[str],
    prefix: str,
) -> None:
    for group_name, aliases in alias_groups.items():
        if _first_present(row, *aliases) is None:
            issues.append(f"missing_required_field::{prefix}::{group_name}")


def _validate_numeric_field_group(
    *,
    row: dict[str, Any],
    alias_group: tuple[str, ...],
    issues: list[str],
    prefix: str,
    allow_float: bool,
) -> None:
    value = _first_present(row, *alias_group)
    if value is None:
        return
    try:
        parsed = float(str(value).strip().replace(",", ""))
    except ValueError:
        issues.append(f"invalid_numeric_value::{prefix}::{alias_group[0]}::{value}")
        return
    if not allow_float and not parsed.is_integer():
        issues.append(f"invalid_integer_value::{prefix}::{alias_group[0]}::{value}")


__all__ = [
    "NormalizedCgmDailySummary",
    "NormalizedSensorGeneticSnapshot",
    "NormalizedWearableDailySummary",
    "SensorFileSchemaValidationResult",
    "normalize_cgm_summary_csv",
    "normalize_sensor_genetic_payloads",
    "normalize_wearable_csv",
    "validate_cgm_summary_csv_schema",
    "validate_gene_profile_json_schema",
    "validate_wearable_summary_csv_schema",
]
