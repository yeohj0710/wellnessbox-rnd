from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineDistributionV1,
    PROBaselineScoreObservationV1,
    PROStandardizedScoreV1,
    build_pro_baseline_distribution_v1,
    load_pro_instrument_scoring_contract_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "data/contracts/pro_instrument_scoring_v1.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op051_op052_versioned_pro_scoring_smoke_v1.json"
)
SOURCE_PATHS = [
    "data/contracts/pro_instrument_scoring_v1.json",
    "scripts/run_versioned_pro_scoring_baseline_percentile_smoke.py",
    "src/wellnessbox_rnd/interim/contracts.py",
    "src/wellnessbox_rnd/metrics/__init__.py",
    "src/wellnessbox_rnd/metrics/calculators.py",
    "src/wellnessbox_rnd/metrics/pro_scoring.py",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify versioned PRO raw scores and baseline health percentiles."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(SOURCE_PATHS):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(
            (PROJECT_ROOT / relative_path).read_bytes().replace(b"\r\n", b"\n")
        )
        digest.update(b"\0")
    return digest.hexdigest()


def _git_source_commit() -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *SOURCE_PATHS],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _contract_sha256() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _score(instrument: str, item_scores: list[object]):
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": instrument,
            "item_scores": item_scores,
        }
    )


def _score_for_raw(instrument: str, raw_score: int):
    contract = load_pro_instrument_scoring_contract_v1()
    definition = next(
        item for item in contract.instruments if item.instrument == instrument
    )
    raw_min, raw_max = definition.raw_score_range
    if not raw_min <= raw_score <= raw_max:
        raise ValueError(f"raw_score_out_of_range::{instrument}::{raw_score}")
    item_min, item_max = definition.item_score_range
    remaining = raw_score
    scored_values = [item_min] * definition.item_count
    for index in range(definition.item_count):
        scored_values[index] = min(item_max, remaining)
        remaining -= scored_values[index]
    original_values = scored_values.copy()
    for position in definition.reverse_scored_positions:
        original_values[position - 1] = (
            item_min + item_max - scored_values[position - 1]
        )
    score = _score(instrument, original_values)
    if score.raw_score != raw_score:
        raise RuntimeError(
            f"raw_score_fixture_mismatch::{instrument}::{score.raw_score}::{raw_score}"
        )
    return score


def _baseline(score) -> PROBaselineScoreObservationV1:
    return PROBaselineScoreObservationV1(
        schema_version="pro_baseline_score_observation_v1",
        observation_role="BASELINE",
        score=score,
    )


def _expect_rejection(label: str, operation: Callable[[], object]) -> bool:
    try:
        operation()
    except (TypeError, ValueError):
        return True
    raise RuntimeError(f"fail_closed_check_accepted::{label}")


def _distribution_case(instrument: str, raw_scores: list[int]) -> dict[str, object]:
    scores = [_score_for_raw(instrument, raw_score) for raw_score in raw_scores]
    distribution = build_pro_baseline_distribution_v1(
        [_baseline(score) for score in scores],
        cohort_id=f"op052-{instrument.lower()}-synthetic-baseline",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    standardized = [
        standardize_pro_instrument_score_v1(score, distribution)
        for score in scores
    ]
    if [item.health_z_score for item in standardized] != [1.0, 0.0, -1.0]:
        raise RuntimeError(f"unexpected_health_z_scores::{instrument}")
    if [item.health_percentile for item in standardized] != [
        84.134475,
        50.0,
        15.865525,
    ]:
        raise RuntimeError(f"unexpected_health_percentiles::{instrument}")
    return {
        "distribution": distribution.model_dump(mode="json"),
        "standardized_scores": [item.model_dump(mode="json") for item in standardized],
    }


def main() -> int:
    args = _args()
    contract = load_pro_instrument_scoring_contract_v1()
    canonical_scores = {
        "PSQI": _score("PSQI", [1, 2, 1, 1, 1, 0, 1]),
        "ISI": _score("ISI", [2, 2, 1, 2, 1, 1, 1]),
        "PSS10": _score("PSS10", [2, 2, 2, 3, 3, 2, 3, 3, 2, 2]),
    }
    if {key: value.raw_score for key, value in canonical_scores.items()} != {
        "PSQI": 7,
        "ISI": 10,
        "PSS10": 16,
    }:
        raise RuntimeError("canonical_raw_scores_changed")
    if canonical_scores["PSS10"].scored_item_values != [
        2,
        2,
        2,
        1,
        1,
        2,
        1,
        1,
        2,
        2,
    ]:
        raise RuntimeError("pss10_reverse_scoring_changed")

    distributions = {
        "PSQI": _distribution_case("PSQI", [6, 9, 12]),
        "ISI": _distribution_case("ISI", [7, 14, 21]),
        "PSS10": _distribution_case("PSS10", [10, 20, 30]),
    }

    with tempfile.TemporaryDirectory(prefix="op051-op052-") as temporary_directory:
        forged_contract_path = Path(temporary_directory) / "forged-contract.json"
        forged_contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        forged_contract["instruments"][2]["reverse_scored_positions"] = [4, 5, 7]
        forged_contract_path.write_text(
            json.dumps(forged_contract),
            encoding="utf-8",
        )
        contract_drift_rejected = _expect_rejection(
            "contract_drift",
            lambda: load_pro_instrument_scoring_contract_v1(forged_contract_path),
        )
        forged_contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        forged_contract["instruments"][0]["limitation"] = (
            "Clinically validated for production diagnosis."
        )
        forged_contract_path.write_text(
            json.dumps(forged_contract),
            encoding="utf-8",
        )
        limitation_drift_rejected = _expect_rejection(
            "limitation_drift",
            lambda: load_pro_instrument_scoring_contract_v1(forged_contract_path),
        )

    distribution_payload = distributions["PSQI"]["distribution"].copy()
    distribution_payload["baseline_mean"] = 999.0
    psqi_six = _score_for_raw("PSQI", 6)
    psqi_twelve = _score_for_raw("PSQI", 12)
    valid_observation = _baseline(psqi_six)
    forged_score = psqi_six.model_copy(update={"raw_score": 20})
    forged_observation = valid_observation.model_copy(update={"score": forged_score})
    follow_up_observation = valid_observation.model_copy(
        update={"observation_role": "FOLLOW_UP"}
    )
    valid_distribution = build_pro_baseline_distribution_v1(
        [valid_observation, _baseline(psqi_twelve)],
        cohort_id="op052-model-instance-boundary",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    forged_distribution = valid_distribution.model_copy(
        update={"baseline_mean": 999.0}
    )
    standardized_payload = standardize_pro_instrument_score_v1(
        psqi_six,
        valid_distribution,
    ).model_dump(mode="json")
    standardized_payload["instrument_scoring_version"] = "evil"
    fail_closed_checks = {
        "boolean_item_rejected": _expect_rejection(
            "boolean_item", lambda: _score("ISI", [0, 0, 0, 0, 0, 0, True])
        ),
        "contract_drift_rejected": contract_drift_rejected,
        "contract_limitation_drift_rejected": limitation_drift_rejected,
        "float_item_rejected": _expect_rejection(
            "float_item", lambda: _score("ISI", [0, 0, 0, 0, 0, 0, 1.0])
        ),
        "forged_distribution_rejected": _expect_rejection(
            "forged_distribution",
            lambda: PROBaselineDistributionV1.model_validate(distribution_payload),
        ),
        "follow_up_observation_rejected": _expect_rejection(
            "follow_up_observation",
            lambda: build_pro_baseline_distribution_v1(
                [follow_up_observation, _baseline(psqi_twelve)],
                cohort_id="op052-follow-up-rejected",
                data_class="SYNTHETIC_OUTCOME_PROXY",
            ),
        ),
        "model_instance_distribution_rejected": _expect_rejection(
            "model_instance_distribution",
            lambda: standardize_pro_instrument_score_v1(
                psqi_six,
                forged_distribution,
            ),
        ),
        "model_instance_score_rejected": _expect_rejection(
            "model_instance_score",
            lambda: build_pro_baseline_distribution_v1(
                [forged_observation, _baseline(psqi_twelve)],
                cohort_id="op052-forged-score-rejected",
                data_class="SYNTHETIC_OUTCOME_PROXY",
            ),
        ),
        "noncanonical_standardized_output_rejected": _expect_rejection(
            "noncanonical_standardized_output",
            lambda: PROStandardizedScoreV1.model_validate(standardized_payload),
        ),
        "out_of_range_item_rejected": _expect_rejection(
            "out_of_range_item", lambda: _score("PSQI", [0, 0, 0, 0, 0, 0, 4])
        ),
        "unknown_instrument_rejected": _expect_rejection(
            "unknown_instrument", lambda: _score("UNKNOWN", [0] * 7)
        ),
        "wrong_item_count_rejected": _expect_rejection(
            "wrong_item_count", lambda: _score("PSS10", [0] * 9)
        ),
        "zero_spread_rejected": _expect_rejection(
            "zero_spread",
            lambda: build_pro_baseline_distribution_v1(
                [
                    _baseline(_score_for_raw("PSQI", 9)),
                    _baseline(_score_for_raw("PSQI", 9)),
                ],
                cohort_id="op052-zero-spread",
                data_class="SYNTHETIC_OUTCOME_PROXY",
            ),
        ),
    }
    if not all(fail_closed_checks.values()):
        raise RuntimeError("one_or_more_fail_closed_checks_failed")

    report = {
        "schema_version": "op051_op052_versioned_pro_scoring_smoke_v1",
        "requirement_stages": {"OP-051": "IMPLEMENTED", "OP-052": "IMPLEMENTED"},
        "contract": {
            "schema_version": contract.schema_version,
            "contract_version": contract.contract_version,
            "standardization_version": contract.standardization.version,
            "rounding_method": contract.standardization.rounding_method,
            "operation_order": contract.standardization.operation_order,
            "instrument_order": [item.instrument for item in contract.instruments],
            "contract_sha256": _contract_sha256(),
        },
        "canonical_raw_scores": {
            key: value.model_dump(mode="json")
            for key, value in canonical_scores.items()
        },
        "baseline_standardization_cases": distributions,
        "fail_closed_checks": fail_closed_checks,
        "evidence_boundary": {
            "data_class": "SYNTHETIC_OUTCOME_PROXY",
            "baseline_cohort_role_fixed": True,
            "instrument_text_included": False,
            "production_data_used": False,
            "service_integration_proven": False,
            "clinical_interpretation_proven": False,
            "production_operation_proven": False,
        },
        "source_identity": {
            "commit": _git_source_commit(),
            "source_paths": sorted(SOURCE_PATHS),
            "source_sha256": _source_sha256(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema_version": report["schema_version"],
                "requirement_stages": report["requirement_stages"],
                "contract": report["contract"],
                "raw_scores": {
                    key: value.raw_score for key, value in canonical_scores.items()
                },
                "fail_closed_checks": fail_closed_checks,
                "evidence_boundary": report["evidence_boundary"],
                "source_identity": report["source_identity"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
