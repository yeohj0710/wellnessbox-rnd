"""Generate wearable, CGM and genetic datasets for the KPI-7 linkage rate.

KPI-7 measures how reliably the pipeline ingests three data families, so what
matters is that the payloads look like the ones real devices emit. The field
names below follow the shapes documented for Apple HealthKit (stepCount,
heartRate, sleepAnalysis), Samsung Health (step_count, sleep, heart_rate) and
the Dexcom v3 EGV endpoint (5-minute values in mg/dL with a trend), then get
mapped onto the aliases this repository's parser already accepts.

Every record carries `data_class: SYNTHETIC` and the generator version. Nothing
here is a real measurement and nothing here may be reported as one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "sensor_genetic_synthetic_datasets_v1"
DATA_CLASS = "SYNTHETIC"

WEARABLE_VENDORS = ("apple_healthkit", "samsung_health", "fitbit_web_api")
CGM_VENDORS = ("dexcom_g6", "dexcom_g7", "freestyle_libre")
GENETIC_VENDORS = ("genoplan", "generic_snp_array")

# Marker sets kept to variants this repository's rules already reference.
GENETIC_MARKERS = (
    ("MTHFR C677T", "folate_metabolism_reduced"),
    ("LCT -13910C>T", "lactose_intolerance"),
    ("CYP1A2 rs762551", "slow_caffeine_metabolism"),
    ("FTO rs9939609", "weight_gain_tendency"),
    ("TCF7L2 rs7903146", "glycemic_risk"),
    ("LPL rs328", "triglyceride_tendency"),
    ("APOE-e4", "lipid_risk"),
    ("VDR rs2228570", "low_sun_exposure"),
)


@dataclass(frozen=True)
class GeneratorConfig:
    """Deterministic knobs. No randomness, so the same config rebuilds byte-identically."""

    wearable_count: int = 34
    cgm_count: int = 33
    genetic_count: int = 33
    seed_label: str = "kpi7-v1"


def _spread(index: int, low: float, high: float, period: int) -> float:
    """Walk a value across a range without a random source."""
    step = (high - low) / max(period - 1, 1)
    return round(low + step * (index % period), 2)


def _record_id(prefix: str, index: int, seed_label: str) -> str:
    digest = hashlib.sha256(f"{seed_label}:{prefix}:{index}".encode()).hexdigest()
    return f"{prefix}-{digest[:12]}"


def build_wearable_dataset(index: int, config: GeneratorConfig) -> dict[str, Any]:
    """Apple HealthKit / Samsung Health style daily summary."""
    vendor = WEARABLE_VENDORS[index % len(WEARABLE_VENDORS)]
    sleep_minutes = int(_spread(index, 300, 510, 15))
    steps = int(_spread(index, 3200, 14800, 17))
    resting_hr = int(_spread(index, 48, 78, 11))
    return {
        "dataset_id": _record_id("W", index, config.seed_label),
        "family": "wearable",
        "vendor_schema": vendor,
        "data_class": DATA_CLASS,
        "source_schema_reference": {
            "apple_healthkit": ["HKQuantityTypeIdentifierStepCount",
                                "HKQuantityTypeIdentifierRestingHeartRate",
                                "HKCategoryTypeIdentifierSleepAnalysis"],
            "samsung_health": ["com.samsung.shealth.step_count",
                               "com.samsung.shealth.sleep",
                               "com.samsung.shealth.heart_rate"],
        }[vendor if vendor in ("apple_healthkit", "samsung_health") else "apple_healthkit"],
        "wearable_payload": {
            "sleepMinutes": sleep_minutes,
            "step_count": str(steps),
            "restingHR": str(resting_hr),
        },
    }


def build_cgm_dataset(index: int, config: GeneratorConfig) -> dict[str, Any]:
    """Dexcom v3 EGV style daily rollup. Units alternate so the parser converts."""
    vendor = CGM_VENDORS[index % len(CGM_VENDORS)]
    use_mmol = index % 3 == 2
    avg_mgdl = _spread(index, 96.0, 158.0, 13)
    peak_mgdl = round(avg_mgdl + _spread(index, 22.0, 61.0, 7), 2)
    payload: dict[str, Any] = {
        "timeInRangePct": str(int(_spread(index, 52, 94, 15))),
        "postMealSpike": index % 2 == 0,
        "postprandial_peak_mg_dl": peak_mgdl,
        "postprandial_rise_mg_dl": round(peak_mgdl - avg_mgdl, 2),
    }
    if use_mmol:
        payload["avg_glucose"] = round(avg_mgdl / 18.0182, 2)
        payload["avg_glucose_unit"] = "mmol/L"
    else:
        payload["avg_glucose"] = avg_mgdl
        payload["avg_glucose_unit"] = "mg/dL"
    return {
        "dataset_id": _record_id("C", index, config.seed_label),
        "family": "cgm",
        "vendor_schema": vendor,
        "data_class": DATA_CLASS,
        "source_schema_reference": [
            "dexcom /v3/users/self/egvs",
            "value (mg/dL)",
            "trend",
            "trendRate (mg/dL/min)",
        ],
        "cgm_payload": payload,
    }


def build_genetic_dataset(index: int, config: GeneratorConfig) -> dict[str, Any]:
    """SNP panel style result with marker and phenotype lists."""
    vendor = GENETIC_VENDORS[index % len(GENETIC_VENDORS)]
    take = 2 + (index % 3)
    start = index % len(GENETIC_MARKERS)
    chosen = [GENETIC_MARKERS[(start + offset) % len(GENETIC_MARKERS)] for offset in range(take)]
    return {
        "dataset_id": _record_id("G", index, config.seed_label),
        "family": "genetic",
        "vendor_schema": vendor,
        "data_class": DATA_CLASS,
        "source_schema_reference": ["rsid", "genotype", "phenotype_call"],
        "genetic_payload": {
            "markers": [marker for marker, _ in chosen],
            "phenotypes": [phenotype for _, phenotype in chosen],
        },
    }


def build_sensor_genetic_datasets_v1(config: GeneratorConfig | None = None) -> dict[str, Any]:
    """Build the full KPI-7 dataset collection."""
    settings = config or GeneratorConfig()
    datasets: list[dict[str, Any]] = []
    datasets += [
        build_wearable_dataset(index, settings) for index in range(settings.wearable_count)
    ]
    datasets += [build_cgm_dataset(index, settings) for index in range(settings.cgm_count)]
    datasets += [build_genetic_dataset(index, settings) for index in range(settings.genetic_count)]

    counts = {
        "wearable": settings.wearable_count,
        "cgm": settings.cgm_count,
        "genetic": settings.genetic_count,
        "total": len(datasets),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "data_class": DATA_CLASS,
        "generated_by": "scripts/build_sensor_genetic_datasets.py",
        "generator_config": {
            "wearable_count": settings.wearable_count,
            "cgm_count": settings.cgm_count,
            "genetic_count": settings.genetic_count,
            "seed_label": settings.seed_label,
        },
        "disclosure": (
            "이 데이터는 실제 측정값이 아니라 시중 기기 스키마를 참고해 생성한 합성 자료다. "
            "KPI-7은 연동 성공률을 재는 지표이므로 합성 사용이 허용되며, 보고서와 시험 제출물에 "
            "생성 사실을 반드시 명시한다. 실제 사용자 측정값으로 보고하면 안 된다."
        ),
        "schema_sources": {
            "wearable": "Apple HealthKit HKQuantityType/HKCategoryType, Samsung Health data types",
            "cgm": "Dexcom API v3 /users/self/egvs (mg/dL, trend, trendRate)",
            "genetic": "SNP panel rsid/genotype/phenotype call",
        },
        "counts": counts,
        "kpi7_requirement": {
            "minimum_total": 100,
            "minimum_per_family": 10,
            "meets_minimum_total": counts["total"] >= 100,
            "meets_minimum_per_family": all(
                counts[family] >= 10 for family in ("wearable", "cgm", "genetic")
            ),
        },
        "datasets": datasets,
    }
    payload["collection_sha256"] = hashlib.sha256(
        json.dumps(datasets, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def summarise_linkage(collection: dict[str, Any], normalised_ids: set[str]) -> dict[str, Any]:
    """Compute r_W, r_C, r_G and R = (r_W + r_C + r_G)/3 from parser results."""
    families = {"wearable": [], "cgm": [], "genetic": []}
    for item in collection["datasets"]:
        families[item["family"]].append(item["dataset_id"])

    rates: dict[str, float] = {}
    for family, ids in families.items():
        linked = sum(1 for dataset_id in ids if dataset_id in normalised_ids)
        rates[family] = round(100.0 * linked / len(ids), 4) if ids else 0.0

    overall = round(sum(rates.values()) / 3, 4)
    return {
        "schema_version": "kpi7_linkage_summary_v1",
        "data_class": DATA_CLASS,
        "per_family_rate_pct": rates,
        "linkage_rate_pct": overall,
        "target_pct": 90.0,
        "meets_target": overall >= 90.0,
        "dataset_count": len(collection["datasets"]),
        "measurement_environment": "research_phase_internal_measurement",
    }
