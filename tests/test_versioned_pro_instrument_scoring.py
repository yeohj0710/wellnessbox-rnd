from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.metrics.pro_scoring import (
    PRO_BASELINE_STANDARDIZATION_VERSION_V1,
    PRO_INSTRUMENT_CONTRACT_VERSION_V1,
    PROBaselineDistributionV1,
    PROBaselineScoreObservationV1,
    PROInstrumentResponseV1,
    PROStandardizedScoreV1,
    build_pro_baseline_distribution_v1,
    load_pro_instrument_scoring_contract_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data/contracts/pro_instrument_scoring_v1.json"


def _score(instrument: str, item_scores: list[object]):
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": instrument,
            "item_scores": item_scores,
        }
    )


def _psqi_score(raw_score: int):
    assert 0 <= raw_score <= 21
    values = [0] * 7
    remaining = raw_score
    for index in range(7):
        values[index] = min(3, remaining)
        remaining -= values[index]
    return _score("PSQI", values)


def _baseline(score) -> PROBaselineScoreObservationV1:
    return PROBaselineScoreObservationV1(
        schema_version="pro_baseline_score_observation_v1",
        observation_role="BASELINE",
        score=score,
    )


def test_instrument_contract_fixes_three_scoring_algorithms() -> None:
    contract = load_pro_instrument_scoring_contract_v1()

    assert contract.schema_version == "pro_instrument_scoring_contract_v1"
    assert contract.contract_version == PRO_INSTRUMENT_CONTRACT_VERSION_V1
    assert contract.standardization.version == PRO_BASELINE_STANDARDIZATION_VERSION_V1
    assert [item.instrument for item in contract.instruments] == ["PSQI", "ISI", "PSS10"]
    by_id = {item.instrument: item for item in contract.instruments}
    assert by_id["PSQI"].input_kind == "component_scores"
    assert by_id["PSQI"].item_count == 7
    assert by_id["PSQI"].raw_score_range == (0, 21)
    assert by_id["ISI"].item_count == 7
    assert by_id["ISI"].raw_score_range == (0, 28)
    assert by_id["PSS10"].item_count == 10
    assert by_id["PSS10"].reverse_scored_positions == (4, 5, 7, 8)
    assert by_id["PSS10"].raw_score_range == (0, 40)
    assert contract.standardization.rounding_method == "python_round_half_to_even"
    assert contract.standardization.mean_precision_decimal_places == 6
    assert contract.standardization.standard_deviation_precision_decimal_places == 6
    assert contract.standardization.z_score_precision_decimal_places == 6
    assert contract.standardization.percentile_precision_decimal_places == 6


def test_raw_score_examples_match_existing_service_contract_examples() -> None:
    psqi = _score("PSQI", [1, 2, 1, 1, 1, 0, 1])
    isi = _score("ISI", [2, 2, 1, 2, 1, 1, 1])
    pss10 = _score("PSS10", [2, 2, 2, 3, 3, 2, 3, 3, 2, 2])

    assert psqi.raw_score == 7
    assert isi.raw_score == 10
    assert pss10.raw_score == 16
    assert pss10.scored_item_values == [2, 2, 2, 1, 1, 2, 1, 1, 2, 2]
    assert pss10.reverse_scored_positions == [4, 5, 7, 8]
    assert all(
        item.contract_version == PRO_INSTRUMENT_CONTRACT_VERSION_V1
        for item in (psqi, isi, pss10)
    )
    assert all(item.lower_is_better for item in (psqi, isi, pss10))
    assert all(item.source_ids for item in (psqi, isi, pss10))


def test_raw_score_boundaries_are_exact() -> None:
    assert _score("PSQI", [0] * 7).raw_score == 0
    assert _score("PSQI", [3] * 7).raw_score == 21
    assert _score("ISI", [0] * 7).raw_score == 0
    assert _score("ISI", [4] * 7).raw_score == 28
    assert _score("PSS10", [0, 0, 0, 4, 4, 0, 4, 4, 0, 0]).raw_score == 0
    assert _score("PSS10", [4, 4, 4, 0, 0, 4, 0, 0, 4, 4]).raw_score == 40


@pytest.mark.parametrize(
    ("instrument", "scores"),
    [
        ("PSQI", [0] * 6),
        ("ISI", [0] * 8),
        ("PSS10", [0] * 9),
        ("PSQI", [0, 0, 0, 0, 0, 0, 4]),
        ("ISI", [0, 0, 0, 0, 0, 0, -1]),
        ("PSS10", [0, 0, 0, 0, 0, 0, 0, 0, 0, 5]),
        ("ISI", [0, 0, 0, 0, 0, 0, 1.0]),
        ("ISI", [0, 0, 0, 0, 0, 0, True]),
    ],
)
def test_invalid_responses_fail_closed(instrument: str, scores: list[object]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        _score(instrument, scores)

    with pytest.raises(ValidationError):
        score_pro_instrument_response_v1(
            {
                "schema_version": "pro_instrument_response_v1",
                "instrument": instrument,
                "item_scores": scores,
                "unexpected": "field",
            }
        )


def test_unknown_instrument_and_contract_drift_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        _score("UNKNOWN", [0] * 7)

    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    pss10 = next(item for item in payload["instruments"] if item["instrument"] == "PSS10")
    pss10["reverse_scored_positions"] = [4, 5, 7]
    forged_path = tmp_path / "forged-contract.json"
    forged_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid_pro_instrument_contract"):
        load_pro_instrument_scoring_contract_v1(forged_path)

    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["instruments"][0]["source_urls"] = ["https://example.com/drift"]
    forged_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_pro_instrument_contract"):
        load_pro_instrument_scoring_contract_v1(forged_path)

    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["instruments"][0]["limitation"] = (
        "Clinically validated for production diagnosis."
    )
    forged_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_pro_instrument_contract"):
        load_pro_instrument_scoring_contract_v1(forged_path)


def test_model_instances_are_revalidated_at_every_public_boundary() -> None:
    response = PROInstrumentResponseV1(
        schema_version="pro_instrument_response_v1",
        instrument="ISI",
        item_scores=[0] * 7,
    )
    forged_response = response.model_copy(
        update={"item_scores": [0, 0, 0, 0, 0, 0, True]}
    )
    with pytest.raises(ValidationError):
        score_pro_instrument_response_v1(forged_response)

    valid_six = _psqi_score(6)
    forged_twenty = valid_six.model_copy(update={"raw_score": 20})
    forged_observation = _baseline(valid_six).model_copy(
        update={"score": forged_twenty}
    )
    with pytest.raises(ValidationError):
        build_pro_baseline_distribution_v1(
            [forged_observation, _baseline(_psqi_score(12))],
            cohort_id="forged-score",
            data_class="SYNTHETIC_OUTCOME_PROXY",
        )

    distribution = build_pro_baseline_distribution_v1(
        [_baseline(_psqi_score(6)), _baseline(_psqi_score(12))],
        cohort_id="forged-distribution",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    forged_distribution = distribution.model_copy(update={"baseline_mean": 999.0})
    with pytest.raises(ValidationError):
        standardize_pro_instrument_score_v1(_psqi_score(6), forged_distribution)


def test_baseline_distribution_uses_sample_statistics_and_is_order_independent() -> None:
    observations = [
        _baseline(_psqi_score(6)),
        _baseline(_psqi_score(9)),
        _baseline(_psqi_score(12)),
    ]

    first = build_pro_baseline_distribution_v1(
        observations,
        cohort_id="op052-psqi-baseline",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    reversed_order = build_pro_baseline_distribution_v1(
        list(reversed(observations)),
        cohort_id="op052-psqi-baseline",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )

    assert first == reversed_order
    assert first.sample_count == 3
    assert first.cohort_role == "BASELINE"
    assert first.data_class == DataClass.SYNTHETIC_OUTCOME_PROXY
    assert first.sorted_baseline_raw_scores == [6, 9, 12]
    assert first.baseline_mean == 9.0
    assert first.baseline_sample_std == 3.0
    assert len(first.source_scores_sha256) == 64


def test_health_z_and_percentile_use_the_same_baseline_distribution() -> None:
    distribution = build_pro_baseline_distribution_v1(
        [
            _baseline(_psqi_score(6)),
            _baseline(_psqi_score(9)),
            _baseline(_psqi_score(12)),
        ],
        cohort_id="op052-psqi-baseline",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )

    better = standardize_pro_instrument_score_v1(_psqi_score(6), distribution)
    center = standardize_pro_instrument_score_v1(_psqi_score(9), distribution)
    worse = standardize_pro_instrument_score_v1(_psqi_score(12), distribution)

    assert better.health_z_score == 1.0
    assert better.health_percentile == pytest.approx(84.134475, abs=1e-6)
    assert center.health_z_score == 0.0
    assert center.health_percentile == 50.0
    assert worse.health_z_score == -1.0
    assert worse.health_percentile == pytest.approx(15.865525, abs=1e-6)
    assert better.health_percentile > center.health_percentile > worse.health_percentile
    assert (
        better.baseline_distribution.source_scores_sha256
        == distribution.source_scores_sha256
    )


def test_distribution_and_transform_reject_incompatible_or_forged_inputs() -> None:
    with pytest.raises(ValueError, match="at_least_two"):
        build_pro_baseline_distribution_v1(
            [_baseline(_psqi_score(9))],
            cohort_id="too-small",
            data_class="SYNTHETIC_OUTCOME_PROXY",
        )
    with pytest.raises(ValueError, match="nonzero_spread"):
        build_pro_baseline_distribution_v1(
            [_baseline(_psqi_score(9)), _baseline(_psqi_score(9))],
            cohort_id="zero-spread",
            data_class="SYNTHETIC_OUTCOME_PROXY",
        )

    distribution = build_pro_baseline_distribution_v1(
        [_baseline(_psqi_score(6)), _baseline(_psqi_score(12))],
        cohort_id="valid",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    with pytest.raises(ValueError, match="instrument_mismatch"):
        standardize_pro_instrument_score_v1(_score("ISI", [1] * 7), distribution)

    forged = distribution.model_dump(mode="json")
    forged["baseline_mean"] = 999.0
    with pytest.raises(ValidationError, match="baseline_mean"):
        PROBaselineDistributionV1.model_validate(forged)

    non_baseline = distribution.model_dump(mode="json")
    non_baseline["cohort_role"] = "FOLLOW_UP"
    with pytest.raises(ValidationError):
        PROBaselineDistributionV1.model_validate(non_baseline)

    undeclared_data_class = distribution.model_dump(mode="json")
    undeclared_data_class["data_class"] = "UNDECLARED"
    with pytest.raises(ValidationError):
        PROBaselineDistributionV1.model_validate(undeclared_data_class)

    follow_up = _baseline(_psqi_score(6)).model_copy(
        update={"observation_role": "FOLLOW_UP"}
    )
    with pytest.raises(ValidationError):
        build_pro_baseline_distribution_v1(
            [follow_up, _baseline(_psqi_score(12))],
            cohort_id="non-baseline-input",
            data_class="SYNTHETIC_OUTCOME_PROXY",
        )


def test_output_models_reject_noncanonical_instrument_metadata() -> None:
    score = _psqi_score(6)
    forged_score = score.model_dump(mode="json")
    forged_score.update(
        {
            "input_kind": "item_scores",
            "item_score_range": [0, 4],
            "raw_score_range": [0, 28],
            "scoring_version": "evil",
            "source_ids": ["FAKE"],
        }
    )
    with pytest.raises(ValidationError, match="canonical instrument contract"):
        type(score).model_validate(forged_score)

    distribution = build_pro_baseline_distribution_v1(
        [_baseline(_psqi_score(6)), _baseline(_psqi_score(12))],
        cohort_id="canonical-output",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    standardized = standardize_pro_instrument_score_v1(score, distribution)
    forged_standardized = standardized.model_dump(mode="json")
    forged_standardized["instrument_scoring_version"] = "evil"
    with pytest.raises(ValidationError, match="noncanonical scoring version"):
        PROStandardizedScoreV1.model_validate(forged_standardized)

    forged_standardized = standardized.model_dump(mode="json")
    forged_standardized["baseline_distribution"]["source_scores_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="source_scores_sha256"):
        PROStandardizedScoreV1.model_validate(forged_standardized)


def test_metrics_package_exports_versioned_instrument_scoring_api() -> None:
    from wellnessbox_rnd import metrics

    assert metrics.PRO_INSTRUMENT_CONTRACT_VERSION_V1 == "2026-07-17.1"
    assert metrics.score_pro_instrument_response_v1 is score_pro_instrument_response_v1
    assert (
        metrics.standardize_pro_instrument_score_v1
        is standardize_pro_instrument_score_v1
    )
