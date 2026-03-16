from __future__ import annotations

import csv
import re
from io import StringIO
from typing import Any

from pydantic import BaseModel, Field


class NormalizedSensorGeneticSnapshot(BaseModel):
    wearable_available: bool = False
    cgm_available: bool = False
    genetic_available: bool = False
    sleep_hours: float | None = None
    steps: int | None = None
    resting_heart_rate: int | None = None
    mean_glucose_mg_dl: float | None = None
    time_in_range_pct: float | None = None
    post_meal_spike_concern: bool = False
    genetic_tags: list[str] = Field(default_factory=list)
    normalization_notes: list[str] = Field(default_factory=list)


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
    "time_in_range_summary": ("time_in_range_pct", "timeInRangePct"),
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
    sleep_hours = _coerce_float(_first_present(payload, "sleep_hours", "sleepHours"))
    if sleep_hours is None:
        sleep_minutes = _coerce_float(
            _first_present(payload, "sleep_minutes", "sleepMinutes", "sleep_duration_minutes")
        )
        if sleep_minutes is not None:
            sleep_hours = round(sleep_minutes / 60.0, 2)
            notes.append("wearable_sleep_minutes_converted_to_hours")

    raw_steps = _first_present(payload, "steps", "step_count", "daily_steps")
    steps = _coerce_int(raw_steps)
    if steps is not None and isinstance(raw_steps, str):
        notes.append("wearable_steps_string_coerced_to_int")

    resting_hr = _coerce_int(
        _first_present(payload, "resting_heart_rate", "restingHR", "resting_hr")
    )
    if resting_hr is not None and isinstance(
        _first_present(payload, "resting_heart_rate", "restingHR", "resting_hr"), str
    ):
        notes.append("wearable_resting_hr_string_coerced_to_int")

    return sleep_hours, steps, resting_hr, notes


def _normalize_cgm_payload(
    payload: dict[str, Any],
) -> tuple[float | None, float | None, bool, list[str]]:
    notes: list[str] = []
    mean_glucose_mg_dl = _coerce_float(
        _first_present(payload, "mean_glucose_mg_dl", "avg_glucose_mg_dl")
    )
    if mean_glucose_mg_dl is None:
        mmol_value = _coerce_float(
            _first_present(payload, "mean_glucose_mmol_l", "avg_glucose_mmol_l")
        )
        if mmol_value is None:
            avg_glucose = _coerce_float(_first_present(payload, "avg_glucose"))
            avg_unit = _normalize_unit(_first_present(payload, "avg_glucose_unit", "glucose_unit"))
            if avg_glucose is not None and avg_unit == "mmol/l":
                mmol_value = avg_glucose
            elif avg_glucose is not None and avg_unit == "mg/dl":
                mean_glucose_mg_dl = avg_glucose
        if mmol_value is not None:
            mean_glucose_mg_dl = round(mmol_value * 18.0, 1)
            notes.append("cgm_mmol_l_converted_to_mg_dl")

    time_in_range_pct = _coerce_float(
        _first_present(payload, "time_in_range_pct", "timeInRangePct")
    )
    if time_in_range_pct is not None and isinstance(
        _first_present(payload, "time_in_range_pct", "timeInRangePct"), str
    ):
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
        return float(normalized)
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
