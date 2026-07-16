from __future__ import annotations

import csv
import re
from io import StringIO
from typing import Any

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import NormalizedSensorGeneticSnapshot


class SensorFileSchemaValidationResult(BaseModel):
    format_name: str
    passed: bool
    detected_fields: list[str] = Field(default_factory=list)
    failure_types: list[str] = Field(default_factory=list)
    accepted_aliases: dict[str, list[str]] = Field(default_factory=dict)


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
}
GENE_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "genetic_tag_source": ("phenotypes", "risk_flags", "markers", "gene_markers"),
}


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

    mean_glucose_mg_dl, time_in_range_pct, post_meal_spike_concern, cgm_notes = (
        _normalize_cgm_payload(cgm_payload or {})
    )
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

    genetic_tags, genetic_notes = _normalize_genetic_payload(genetic_payload or {})
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
        post_meal_spike_concern=post_meal_spike_concern,
        genetic_tags=genetic_tags,
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
        if _first_present(row, "avg_glucose") is not None and _first_present(
            row, "avg_glucose_unit", "glucose_unit"
        ) is None:
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

    _validate_required_alias_groups(
        row=payload,
        alias_groups=GENE_ALIAS_GROUPS,
        issues=issues,
        prefix="gene_profile",
    )
    present_value = _first_present(payload, *GENE_ALIAS_GROUPS["genetic_tag_source"])
    if present_value is not None and not isinstance(present_value, (str, list)):
        issues.append("invalid_value_type::gene_profile::genetic_tag_source")

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
) -> tuple[float | None, float | None, bool, list[str]]:
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
    return mean_glucose_mg_dl, time_in_range_pct, post_meal_spike_concern, notes


def _normalize_genetic_payload(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    raw_values: list[str] = []
    for key in ("phenotypes", "risk_flags", "markers", "gene_markers"):
        raw_value = payload.get(key)
        if raw_value is None:
            continue
        raw_values.extend(_as_string_list(raw_value))
    normalized = sorted({_slugify(value) for value in raw_values if _slugify(value)})
    if normalized:
        notes.append("genetic_tags_normalized_to_snake_case")
    return normalized, notes


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


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
    "NormalizedSensorGeneticSnapshot",
    "SensorFileSchemaValidationResult",
    "normalize_sensor_genetic_payloads",
    "validate_cgm_summary_csv_schema",
    "validate_gene_profile_json_schema",
    "validate_wearable_summary_csv_schema",
]
