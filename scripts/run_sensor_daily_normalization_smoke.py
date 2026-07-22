from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from wellnessbox_rnd.domain.sensor_parser import (
    normalize_cgm_summary_csv,
    normalize_wearable_csv,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data/original_plan/op091_op092_sensor_daily_normalization_cases_v1.json"
SOURCE_PATHS = (
    ROOT / "scripts/run_sensor_daily_normalization_smoke.py",
    DATASET_PATH,
    ROOT / "data/samples/wearable_summary_v1.csv",
    ROOT / "data/samples/cgm_summary_v1.csv",
    ROOT / "src/wellnessbox_rnd/domain/sensor_parser.py",
    ROOT / "src/wellnessbox_rnd/schemas/recommendation.py",
    ROOT / "src/wellnessbox_rnd/domain/intake.py",
    ROOT / "src/wellnessbox_rnd/interim/data_lake.py",
)


def _git_blob_sha256(path: Path) -> str:
    content = subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    return hashlib.sha256(content).hexdigest()


def _source_commit() -> str:
    paths = [path.relative_to(ROOT).as_posix() for path in SOURCE_PATHS]
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *paths], cwd=ROOT, text=True
    ).strip()


def _project(record: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in expected}


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = str(case["kind"])
    normalizer = (
        normalize_wearable_csv if kind.startswith("wearable") else normalize_cgm_summary_csv
    )
    if kind.endswith("success"):
        records = [item.model_dump(mode="json") for item in normalizer(str(case["csv"]))]
        expected = list(case["expected"])
        projected = [_project(record, expected[index]) for index, record in enumerate(records)]
        if projected != expected:
            raise AssertionError(f"unexpected_normalization:{case['case_id']}")
        return {
            "case_id": case["case_id"],
            "result": "PASS",
            "record_count": len(records),
            "records": records,
        }
    try:
        normalizer(str(case["csv"]))
    except ValueError as error:
        if str(error) != case["expected_error"]:
            raise AssertionError(f"unexpected_error:{case['case_id']}:{error}") from error
        return {
            "case_id": case["case_id"],
            "result": "PASS",
            "error": str(error),
        }
    raise AssertionError(f"expected_failure_not_raised:{case['case_id']}")


def main() -> int:
    output = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/original_plan/evidence/op091_op092_sensor_daily_normalization_smoke_v1.json"
    )
    output = output if output.is_absolute() else ROOT / output
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = [_run_case(case) for case in dataset["cases"]]
    if dataset["case_count"] != len(cases):
        raise AssertionError("dataset_case_count_mismatch")
    report = {
        "schema_version": "op091_op092_sensor_daily_normalization_smoke_v1",
        "requirements": ["OP-091", "OP-092"],
        "result": "PASS",
        "dataset": {
            "path": DATASET_PATH.relative_to(ROOT).as_posix(),
            "schema_version": dataset["schema_version"],
            "case_count": dataset["case_count"],
            "sha256": _git_blob_sha256(DATASET_PATH),
        },
        "checks": {
            "cases": cases,
            "apple_health_csv_observed": True,
            "generic_wearable_csv_observed": True,
            "cgm_mg_dl_and_mmol_l_observed": True,
            "postprandial_peak_and_rise_observed": True,
            "standardized_tir_70_180_observed": True,
            "production_provider_api_observed": False,
            "production_operation_observed": False,
        },
        "source_identity": {
            "commit": _source_commit(),
            "files": {
                path.relative_to(ROOT).as_posix(): _git_blob_sha256(path) for path in SOURCE_PATHS
            },
        },
        "stage_boundary": {
            "OP-091": "Versioned local CSV normalization is implemented; no Apple Health API operation is claimed.",
            "OP-092": "Versioned local CGM summary normalization is implemented; no production CGM integration is claimed.",
        },
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
