from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    model_validator,
)

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.metrics.calculators import percentile_improvement_pp
from wellnessbox_rnd.schemas.pro_events import (
    BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1,
    BaselineFollowUpPROEventV1,
    build_baseline_followup_pro_event_v1,
    validate_baseline_followup_pro_event_v1,
)
from wellnessbox_rnd.schemas.recommendation import RecommendationGoal
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord

PRO_FORM_SCHEMA_VERSION_V1 = "pro_form_schema_v1"
PRO_SCORE_ORIENTATION_V1 = "lower_is_better_for_problem_score"
PRO_Z_SCORE_TRANSFORM_VERSION_V1 = "pro_zscore_transform_v1"
PRO_Z_SCORE_NORM_VERSION_V1 = "pro_zscore_norm_v1"
PRO_IMPROVEMENT_SUMMARY_VERSION_V1 = "pro_improvement_summary_v1"
PRO_DEFAULT_PROBLEM_SCORE_MEAN_V1 = 2.0
PRO_DEFAULT_PROBLEM_SCORE_STD_V1 = 1.0
PRO_Z_SCORE_STD_FLOOR = 1e-6
PRO_IMPROVEMENT_DELTA_TOLERANCE = 1e-6
PRO_INSTRUMENT_RESPONSE_SCHEMA_VERSION_V1 = "pro_instrument_response_v1"
PRO_INSTRUMENT_SCORE_SCHEMA_VERSION_V1 = "pro_instrument_score_v1"
PRO_BASELINE_SCORE_OBSERVATION_SCHEMA_VERSION_V1 = (
    "pro_baseline_score_observation_v1"
)
PRO_INSTRUMENT_CONTRACT_SCHEMA_VERSION_V1 = "pro_instrument_scoring_contract_v1"
PRO_INSTRUMENT_CONTRACT_VERSION_V1 = "2026-07-17.1"
PRO_BASELINE_DISTRIBUTION_SCHEMA_VERSION_V1 = "pro_baseline_distribution_v1"
PRO_BASELINE_STANDARDIZATION_VERSION_V1 = "pro_baseline_health_percentile_v1"
PRO_STANDARDIZED_SCORE_SCHEMA_VERSION_V1 = "pro_standardized_score_v1"
DEFAULT_PRO_INSTRUMENT_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/contracts/pro_instrument_scoring_v1.json"
)

PROInstrumentIdV1 = Literal["PSQI", "ISI", "PSS10"]
PROInstrumentInputKindV1 = Literal["component_scores", "item_scores"]


class PROInstrumentDefinitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    instrument: PROInstrumentIdV1
    input_kind: PROInstrumentInputKindV1
    item_count: int = Field(strict=True, ge=1)
    item_score_range: tuple[StrictInt, StrictInt]
    reverse_scored_positions: tuple[StrictInt, ...]
    raw_score_range: tuple[StrictInt, StrictInt]
    lower_is_better: Literal[True]
    scoring_version: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)
    limitation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_definition(self) -> PROInstrumentDefinitionV1:
        item_min, item_max = self.item_score_range
        if item_min < 0 or item_max <= item_min:
            raise ValueError("invalid item score range")
        if self.raw_score_range != (
            self.item_count * item_min,
            self.item_count * item_max,
        ):
            raise ValueError("raw score range does not match item contract")
        if len(set(self.reverse_scored_positions)) != len(
            self.reverse_scored_positions
        ) or any(
            position < 1 or position > self.item_count
            for position in self.reverse_scored_positions
        ):
            raise ValueError("invalid reverse-scored positions")
        if len(set(self.source_ids)) != len(self.source_ids) or len(
            set(self.source_urls)
        ) != len(self.source_urls):
            raise ValueError("duplicate instrument source metadata")
        if any(not value.strip() for value in self.source_ids) or any(
            not value.startswith("https://") for value in self.source_urls
        ):
            raise ValueError("invalid instrument source metadata")
        return self


class PROBaselineStandardizationContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    version: Literal["pro_baseline_health_percentile_v1"]
    baseline_only: Literal[True]
    minimum_sample_count: Literal[2]
    mean_method: Literal["arithmetic_mean"]
    standard_deviation_method: Literal["sample_standard_deviation_ddof_1"]
    z_score_orientation: Literal["higher_is_better_health_score"]
    percentile_method: Literal["standard_normal_cdf_times_100"]
    rounding_method: Literal["python_round_half_to_even"]
    mean_precision_decimal_places: Literal[6]
    standard_deviation_precision_decimal_places: Literal[6]
    z_score_precision_decimal_places: Literal[6]
    percentile_precision_decimal_places: Literal[6]
    operation_order: Literal[
        "raw_scores->mean_and_sample_std->round_statistics->health_z->round_z->"
        "normal_cdf_times_100->round_percentile"
    ]
    formula: Literal[
        "health_z=(baseline_mean-raw_problem_score)/baseline_sample_std"
    ]


class PROInstrumentScoringContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    schema_version: Literal["pro_instrument_scoring_contract_v1"]
    contract_version: Literal["2026-07-17.1"]
    instruments: list[PROInstrumentDefinitionV1] = Field(min_length=3, max_length=3)
    standardization: PROBaselineStandardizationContractV1


class PROInstrumentResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    schema_version: Literal["pro_instrument_response_v1"]
    instrument: PROInstrumentIdV1
    item_scores: list[StrictInt]


class PROInstrumentScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    schema_version: Literal["pro_instrument_score_v1"] = (
        PRO_INSTRUMENT_SCORE_SCHEMA_VERSION_V1
    )
    contract_version: Literal["2026-07-17.1"]
    instrument: PROInstrumentIdV1
    input_kind: PROInstrumentInputKindV1
    scoring_version: str = Field(min_length=1)
    original_item_values: list[StrictInt]
    scored_item_values: list[StrictInt]
    item_score_range: tuple[StrictInt, StrictInt]
    reverse_scored_positions: list[StrictInt]
    raw_score: int = Field(strict=True, ge=0)
    raw_score_range: tuple[StrictInt, StrictInt]
    lower_is_better: Literal[True]
    source_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_score_trace(self) -> PROInstrumentScoreV1:
        if len(self.original_item_values) != len(self.scored_item_values):
            raise ValueError("original and scored item counts differ")
        item_min, item_max = self.item_score_range
        if any(
            value < item_min or value > item_max
            for value in [*self.original_item_values, *self.scored_item_values]
        ):
            raise ValueError("score trace contains an out-of-range item")
        reverse_positions = set(self.reverse_scored_positions)
        expected_scored = [
            item_min + item_max - value if index in reverse_positions else value
            for index, value in enumerate(self.original_item_values, start=1)
        ]
        if self.scored_item_values != expected_scored:
            raise ValueError("scored item values do not match reverse-scoring trace")
        if self.raw_score != sum(self.scored_item_values):
            raise ValueError("raw score does not match scored item values")
        if not self.raw_score_range[0] <= self.raw_score <= self.raw_score_range[1]:
            raise ValueError("raw score is outside the instrument range")
        expected = _EXPECTED_PRO_INSTRUMENT_CONTRACT_V1[self.instrument]
        canonical_values = {
            "input_kind": expected["input_kind"],
            "item_score_range": expected["item_score_range"],
            "reverse_scored_positions": list(expected["reverse_scored_positions"]),
            "raw_score_range": expected["raw_score_range"],
            "lower_is_better": expected["lower_is_better"],
            "scoring_version": expected["scoring_version"],
            "source_ids": expected["source_ids"],
        }
        if any(
            getattr(self, field_name) != expected_value
            for field_name, expected_value in canonical_values.items()
        ) or len(self.original_item_values) != expected["item_count"]:
            raise ValueError("score trace does not match the canonical instrument contract")
        return self


class PROBaselineScoreObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    schema_version: Literal["pro_baseline_score_observation_v1"]
    observation_role: Literal["BASELINE"]
    score: PROInstrumentScoreV1


class PROBaselineDistributionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    schema_version: Literal["pro_baseline_distribution_v1"] = (
        PRO_BASELINE_DISTRIBUTION_SCHEMA_VERSION_V1
    )
    standardization_version: Literal["pro_baseline_health_percentile_v1"] = (
        PRO_BASELINE_STANDARDIZATION_VERSION_V1
    )
    cohort_role: Literal["BASELINE"] = "BASELINE"
    contract_version: Literal["2026-07-17.1"]
    instrument: PROInstrumentIdV1
    instrument_scoring_version: str = Field(min_length=1)
    cohort_id: str = Field(min_length=1, pattern=r".*\S.*")
    data_class: DataClass
    sample_count: int = Field(strict=True, ge=2)
    sorted_baseline_raw_scores: list[StrictInt] = Field(min_length=2)
    baseline_mean: float = Field(allow_inf_nan=False)
    baseline_sample_std: float = Field(gt=0.0, allow_inf_nan=False)
    source_scores_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_distribution(self) -> PROBaselineDistributionV1:
        expected_instrument = _EXPECTED_PRO_INSTRUMENT_CONTRACT_V1[self.instrument]
        if self.instrument_scoring_version != expected_instrument["scoring_version"]:
            raise ValueError("baseline distribution uses a noncanonical scoring version")
        if self.sorted_baseline_raw_scores != sorted(
            self.sorted_baseline_raw_scores
        ):
            raise ValueError("baseline scores must be sorted")
        if self.sample_count != len(self.sorted_baseline_raw_scores):
            raise ValueError("sample_count does not match baseline scores")
        raw_min, raw_max = expected_instrument["raw_score_range"]
        if any(
            value < raw_min or value > raw_max
            for value in self.sorted_baseline_raw_scores
        ):
            raise ValueError("baseline score is outside the instrument range")
        expected_mean = round(statistics.fmean(self.sorted_baseline_raw_scores), 6)
        expected_std = round(statistics.stdev(self.sorted_baseline_raw_scores), 6)
        if abs(self.baseline_mean - expected_mean) > 1e-6:
            raise ValueError("baseline_mean does not match source scores")
        if abs(self.baseline_sample_std - expected_std) > 1e-6:
            raise ValueError("baseline_sample_std does not match source scores")
        expected_hash = _baseline_source_sha256(
            contract_version=self.contract_version,
            instrument=self.instrument,
            instrument_scoring_version=self.instrument_scoring_version,
            cohort_id=self.cohort_id,
            data_class=self.data_class,
            sorted_raw_scores=self.sorted_baseline_raw_scores,
        )
        if self.source_scores_sha256 != expected_hash:
            raise ValueError("source_scores_sha256 does not match distribution identity")
        return self


class PROStandardizedScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    schema_version: Literal["pro_standardized_score_v1"] = (
        PRO_STANDARDIZED_SCORE_SCHEMA_VERSION_V1
    )
    standardization_version: Literal["pro_baseline_health_percentile_v1"] = (
        PRO_BASELINE_STANDARDIZATION_VERSION_V1
    )
    contract_version: Literal["2026-07-17.1"]
    instrument: PROInstrumentIdV1
    instrument_scoring_version: str = Field(min_length=1)
    raw_score: int = Field(strict=True, ge=0)
    baseline_distribution: PROBaselineDistributionV1
    health_z_score: float = Field(allow_inf_nan=False)
    health_percentile: float = Field(ge=0.0, le=100.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_standardized_score(self) -> PROStandardizedScoreV1:
        expected = _EXPECTED_PRO_INSTRUMENT_CONTRACT_V1[self.instrument]
        if self.instrument_scoring_version != expected["scoring_version"]:
            raise ValueError("standardized score uses a noncanonical scoring version")
        raw_min, raw_max = expected["raw_score_range"]
        if not raw_min <= self.raw_score <= raw_max:
            raise ValueError("standardized raw score is outside the instrument range")
        distribution = self.baseline_distribution
        if distribution.instrument != self.instrument:
            raise ValueError("standardized score instrument does not match distribution")
        if distribution.instrument_scoring_version != self.instrument_scoring_version:
            raise ValueError("standardized score version does not match distribution")
        expected_z = round(
            (distribution.baseline_mean - self.raw_score)
            / distribution.baseline_sample_std,
            6,
        )
        if abs(self.health_z_score - expected_z) > 1e-6:
            raise ValueError("health_z_score does not match baseline formula")
        if abs(self.health_percentile - _z_to_percentile(expected_z)) > 1e-6:
            raise ValueError("health_percentile does not match standard normal CDF")
        return self


_EXPECTED_PRO_INSTRUMENT_CONTRACT_V1 = {
    "PSQI": {
        "input_kind": "component_scores",
        "item_count": 7,
        "item_score_range": (0, 3),
        "reverse_scored_positions": (),
        "raw_score_range": (0, 21),
        "lower_is_better": True,
        "scoring_version": "psqi_component_sum_v1",
        "source_ids": ["PSQI-BUYSSE-1989"],
        "source_urls": [
            "https://www.sleep.pitt.edu/sites/default/files/assets/"
            "Instrument%20Materials/PSQI-Article.pdf"
        ],
        "limitation": (
            "Input is the seven derived PSQI component scores. This contract does not "
            "reproduce or derive the licensed 19 self-rated items."
        ),
    },
    "ISI": {
        "input_kind": "item_scores",
        "item_count": 7,
        "item_score_range": (0, 4),
        "reverse_scored_positions": (),
        "raw_score_range": (0, 28),
        "lower_is_better": True,
        "scoring_version": "isi_item_sum_v1",
        "source_ids": ["ISI-MORIN-BASTIEN-2001"],
        "source_urls": [
            "https://eprovide.mapi-trust.org/instruments/insomnia-severity-index"
        ],
        "limitation": (
            "The instrument text is not reproduced. Use only an authorized "
            "questionnaire version and supply seven scored item values."
        ),
    },
    "PSS10": {
        "input_kind": "item_scores",
        "item_count": 10,
        "item_score_range": (0, 4),
        "reverse_scored_positions": (4, 5, 7, 8),
        "raw_score_range": (0, 40),
        "lower_is_better": True,
        "scoring_version": "pss10_reverse_4_5_7_8_sum_v1",
        "source_ids": ["PSS-COHEN-1983-1988"],
        "source_urls": [
            "https://www.cmu.edu/dietrich/psychology/stress-immunity-disease-lab/"
            "scales/html/pss.html"
        ],
        "limitation": (
            "The item text is not reproduced. Supply ten scored responses in official "
            "item order."
        ),
    },
}


def load_pro_instrument_scoring_contract_v1(
    path: str | Path = DEFAULT_PRO_INSTRUMENT_CONTRACT_PATH,
) -> PROInstrumentScoringContractV1:
    try:
        contract = PROInstrumentScoringContractV1.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_pro_instrument_contract::{exc}") from exc
    if [item.instrument for item in contract.instruments] != ["PSQI", "ISI", "PSS10"]:
        raise ValueError("invalid_pro_instrument_contract::instrument_order_or_coverage")
    for definition in contract.instruments:
        expected = _EXPECTED_PRO_INSTRUMENT_CONTRACT_V1[definition.instrument]
        actual = {
            field_name: getattr(definition, field_name) for field_name in expected
        }
        if actual != expected:
            raise ValueError(
                f"invalid_pro_instrument_contract::{definition.instrument}::scoring_drift"
            )
    return contract


def score_pro_instrument_response_v1(
    response: PROInstrumentResponseV1 | dict[str, object],
    *,
    contract_path: str | Path = DEFAULT_PRO_INSTRUMENT_CONTRACT_PATH,
) -> PROInstrumentScoreV1:
    response_model = PROInstrumentResponseV1.model_validate(response)
    contract = load_pro_instrument_scoring_contract_v1(contract_path)
    definition = next(
        item for item in contract.instruments if item.instrument == response_model.instrument
    )
    if len(response_model.item_scores) != definition.item_count:
        raise ValueError(
            "invalid_pro_instrument_response::item_count::"
            f"{response_model.instrument}::{len(response_model.item_scores)}"
        )
    item_min, item_max = definition.item_score_range
    if any(
        value < item_min or value > item_max for value in response_model.item_scores
    ):
        raise ValueError(
            f"invalid_pro_instrument_response::item_range::{response_model.instrument}"
        )
    reverse_positions = set(definition.reverse_scored_positions)
    scored_values = [
        item_min + item_max - value if index in reverse_positions else value
        for index, value in enumerate(response_model.item_scores, start=1)
    ]
    return PROInstrumentScoreV1(
        contract_version=contract.contract_version,
        instrument=definition.instrument,
        input_kind=definition.input_kind,
        scoring_version=definition.scoring_version,
        original_item_values=response_model.item_scores,
        scored_item_values=scored_values,
        item_score_range=definition.item_score_range,
        reverse_scored_positions=list(definition.reverse_scored_positions),
        raw_score=sum(scored_values),
        raw_score_range=definition.raw_score_range,
        lower_is_better=definition.lower_is_better,
        source_ids=definition.source_ids,
    )


def build_pro_baseline_distribution_v1(
    observations: list[PROBaselineScoreObservationV1 | dict[str, object]],
    *,
    cohort_id: str,
    data_class: DataClass | str,
) -> PROBaselineDistributionV1:
    if len(observations) < 2:
        raise ValueError("baseline_distribution_requires_at_least_two_scores")
    contract = load_pro_instrument_scoring_contract_v1()
    observation_models = [
        PROBaselineScoreObservationV1.model_validate(observation)
        for observation in observations
    ]
    score_models = [observation.score for observation in observation_models]
    for score in score_models:
        _validate_instrument_score_against_contract(score, contract)
    identities = {
        (score.contract_version, score.instrument, score.scoring_version)
        for score in score_models
    }
    if len(identities) != 1:
        raise ValueError("baseline_distribution_requires_one_instrument_and_version")
    sorted_scores = sorted(score.raw_score for score in score_models)
    sample_std = round(statistics.stdev(sorted_scores), 6)
    if sample_std <= PRO_Z_SCORE_STD_FLOOR:
        raise ValueError("baseline_distribution_requires_nonzero_spread")
    contract_version, instrument, scoring_version = identities.pop()
    source_hash = _baseline_source_sha256(
        contract_version=contract_version,
        instrument=instrument,
        instrument_scoring_version=scoring_version,
        cohort_id=cohort_id,
        data_class=data_class,
        sorted_raw_scores=sorted_scores,
    )
    return PROBaselineDistributionV1(
        contract_version=contract_version,
        instrument=instrument,
        instrument_scoring_version=scoring_version,
        cohort_id=cohort_id,
        data_class=data_class,
        sample_count=len(sorted_scores),
        sorted_baseline_raw_scores=sorted_scores,
        baseline_mean=round(statistics.fmean(sorted_scores), 6),
        baseline_sample_std=sample_std,
        source_scores_sha256=source_hash,
    )


def standardize_pro_instrument_score_v1(
    score: PROInstrumentScoreV1 | dict[str, object],
    distribution: PROBaselineDistributionV1 | dict[str, object],
) -> PROStandardizedScoreV1:
    score_model = PROInstrumentScoreV1.model_validate(score)
    distribution_model = PROBaselineDistributionV1.model_validate(distribution)
    contract = load_pro_instrument_scoring_contract_v1()
    _validate_instrument_score_against_contract(score_model, contract)
    if score_model.instrument != distribution_model.instrument:
        raise ValueError("pro_standardization_instrument_mismatch")
    if (
        score_model.contract_version != distribution_model.contract_version
        or score_model.scoring_version
        != distribution_model.instrument_scoring_version
    ):
        raise ValueError("pro_standardization_scoring_version_mismatch")
    health_z = round(
        (distribution_model.baseline_mean - score_model.raw_score)
        / distribution_model.baseline_sample_std,
        6,
    )
    return PROStandardizedScoreV1(
        contract_version=score_model.contract_version,
        instrument=score_model.instrument,
        instrument_scoring_version=score_model.scoring_version,
        raw_score=score_model.raw_score,
        baseline_distribution=distribution_model,
        health_z_score=health_z,
        health_percentile=_z_to_percentile(health_z),
    )


def _validate_instrument_score_against_contract(
    score: PROInstrumentScoreV1,
    contract: PROInstrumentScoringContractV1,
) -> None:
    definition = next(
        item for item in contract.instruments if item.instrument == score.instrument
    )
    expected = {
        "contract_version": contract.contract_version,
        "input_kind": definition.input_kind,
        "scoring_version": definition.scoring_version,
        "item_score_range": definition.item_score_range,
        "reverse_scored_positions": list(definition.reverse_scored_positions),
        "raw_score_range": definition.raw_score_range,
        "lower_is_better": definition.lower_is_better,
        "source_ids": definition.source_ids,
    }
    actual = {field_name: getattr(score, field_name) for field_name in expected}
    if actual != expected or len(score.original_item_values) != definition.item_count:
        raise ValueError("pro_instrument_score_contract_mismatch")


def _baseline_source_sha256(
    *,
    contract_version: str,
    instrument: str,
    instrument_scoring_version: str,
    cohort_id: str,
    data_class: DataClass | str,
    sorted_raw_scores: list[int],
) -> str:
    payload = {
        "cohort_id": cohort_id,
        "cohort_role": "BASELINE",
        "contract_version": contract_version,
        "data_class": data_class,
        "instrument": instrument,
        "instrument_scoring_version": instrument_scoring_version,
        "sorted_baseline_raw_scores": sorted_raw_scores,
        "standardization_version": PRO_BASELINE_STANDARDIZATION_VERSION_V1,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class PROItemSchemaV1(BaseModel):
    item_key: str
    prompt_label: str
    response_min: int = Field(default=0, ge=0)
    response_max: int = Field(default=4, ge=0)


class PRODomainFormSchemaV1(BaseModel):
    domain_key: RecommendationGoal
    display_name: str
    baseline_form_key: str
    follow_up_form_key: str
    score_orientation: Literal["lower_is_better_for_problem_score"] = (
        PRO_SCORE_ORIENTATION_V1
    )
    items: list[PROItemSchemaV1] = Field(min_length=1)


class PROFormSchemaV1(BaseModel):
    schema_version: str = PRO_FORM_SCHEMA_VERSION_V1
    timepoints: tuple[Literal["baseline"], Literal["follow_up"]] = ("baseline", "follow_up")
    domains: list[PRODomainFormSchemaV1] = Field(min_length=1)


class PROFormResponseV1(BaseModel):
    schema_version: str = PRO_FORM_SCHEMA_VERSION_V1
    timepoint: Literal["baseline", "follow_up"]
    domain_item_scores: dict[str, dict[str, int]] = Field(default_factory=dict)


class PRODomainNormV1(BaseModel):
    domain_key: RecommendationGoal
    norm_version: str = PRO_Z_SCORE_NORM_VERSION_V1
    problem_score_mean: float = PRO_DEFAULT_PROBLEM_SCORE_MEAN_V1
    problem_score_std: float = Field(default=PRO_DEFAULT_PROBLEM_SCORE_STD_V1, gt=0.0)
    score_orientation: Literal["lower_is_better_for_problem_score"] = (
        PRO_SCORE_ORIENTATION_V1
    )


class PROZScoreSnapshotV1(BaseModel):
    transform_version: str = PRO_Z_SCORE_TRANSFORM_VERSION_V1
    norm_version: str = PRO_Z_SCORE_NORM_VERSION_V1
    timepoint: Literal["baseline", "follow_up"]
    domain_problem_scores: dict[str, float] = Field(default_factory=dict)
    domain_z: dict[str, float] = Field(default_factory=dict)
    aggregate_z: float
    domain_percentile: dict[str, float] = Field(default_factory=dict)
    aggregate_percentile: float | None = None

    @model_validator(mode="after")
    def populate_percentiles(self) -> PROZScoreSnapshotV1:
        self.domain_percentile = {
            domain_key: _z_to_percentile(z_value)
            for domain_key, z_value in self.domain_z.items()
        }
        self.aggregate_percentile = _z_to_percentile(self.aggregate_z)
        return self


class PROImprovementSummaryV1(BaseModel):
    summary_version: str = PRO_IMPROVEMENT_SUMMARY_VERSION_V1
    baseline_timepoint: Literal["baseline"]
    follow_up_timepoint: Literal["follow_up"]
    baseline_aggregate_z: float = 0.0
    follow_up_aggregate_z: float = 0.0
    baseline_aggregate_percentile: float = 50.0
    follow_up_aggregate_percentile: float = 50.0
    aggregate_delta_z: float
    aggregate_delta_pp: float = 0.0
    domain_delta_z: dict[str, float] = Field(default_factory=dict)
    improved_domain_count: int = Field(ge=0)
    worsened_domain_count: int = Field(ge=0)
    unchanged_domain_count: int = Field(ge=0)
    net_status: Literal["net_improvement", "net_worsening", "no_material_change"]


def build_default_pro_form_schema_v1() -> PROFormSchemaV1:
    return PROFormSchemaV1(
        domains=[
            _domain_schema(
                RecommendationGoal.STRESS_SUPPORT,
                "Stress support",
                [
                    ("perceived_stress_load", "How heavy did your stress feel?"),
                    ("tension_burden", "How tense did your body feel?"),
                    ("calm_recovery_delay", "How hard was it to settle down?"),
                    ("stress_resilience_drop", "How much did stress affect your function?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.SLEEP_SUPPORT,
                "Sleep support",
                [
                    ("sleep_latency_burden", "How hard was it to fall asleep?"),
                    ("nighttime_awakenings", "How disruptive were nighttime awakenings?"),
                    ("sleep_duration_shortfall", "How short did your sleep feel?"),
                    ("wake_refreshment_deficit", "How unrefreshed did you feel on waking?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.IMMUNITY_SUPPORT,
                "Immunity support",
                [
                    ("infection_susceptibility", "How vulnerable did you feel to illness?"),
                    ("recovery_delay", "How slow was recovery from minor illness?"),
                    (
                        "sore_throat_nasal_burden",
                        "How much upper-respiratory discomfort was present?",
                    ),
                    ("immune_fatigue_burden", "How much fatigue followed immune stress?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.ENERGY_SUPPORT,
                "Energy support",
                [
                    ("morning_fatigue", "How fatigued did you feel in the morning?"),
                    ("afternoon_energy_crash", "How strong was your afternoon energy crash?"),
                    ("activity_tolerance_drop", "How limited was your activity tolerance?"),
                    ("daylong_fatigue_burden", "How heavy did daily fatigue feel?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.GUT_HEALTH,
                "Gut health",
                [
                    ("bloating_burden", "How much bloating bothered you?"),
                    ("abdominal_discomfort", "How much abdominal discomfort was present?"),
                    ("bowel_irregularity", "How irregular was your digestion?"),
                    ("meal_tolerance_drop", "How difficult was it to tolerate meals?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.BONE_JOINT,
                "Bone and joint",
                [
                    ("joint_stiffness", "How much joint stiffness was present?"),
                    ("pain_burden", "How much pain limited you?"),
                    ("mobility_drop", "How reduced did your mobility feel?"),
                    ("load_tolerance_drop", "How hard was it to tolerate physical load?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.HEART_HEALTH,
                "Heart health",
                [
                    ("exertion_intolerance", "How limited were you during exertion?"),
                    ("resting_recovery_delay", "How slow was your recovery after effort?"),
                    ("palpitation_burden", "How much did palpitations bother you?"),
                    ("chest_discomfort_burden", "How much chest discomfort was present?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.BLOOD_GLUCOSE,
                "Blood glucose",
                [
                    ("post_meal_crash", "How strong was your post-meal crash?"),
                    (
                        "carb_tolerance_drop",
                        "How poorly did you tolerate carbohydrate-heavy meals?",
                    ),
                    ("hunger_instability", "How unstable did your hunger feel?"),
                    ("glucose_symptom_burden", "How much did glucose swings affect you?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.GENERAL_WELLNESS,
                "General wellness",
                [
                    ("overall_wellbeing_drop", "How reduced did overall wellbeing feel?"),
                    ("daily_function_drop", "How limited was daily function?"),
                    ("recovery_quality_drop", "How poor was your recovery quality?"),
                    ("resilience_drop", "How reduced did your general resilience feel?"),
                ],
            ),
        ]
    )


def validate_pro_form_response_v1(
    response: PROFormResponseV1 | dict[str, object],
    schema: PROFormSchemaV1,
) -> list[str]:
    issues: list[str] = []
    response_model = (
        response
        if isinstance(response, PROFormResponseV1)
        else PROFormResponseV1.model_validate(response)
    )
    domain_map = {domain.domain_key.value: domain for domain in schema.domains}

    for domain_key, item_scores in response_model.domain_item_scores.items():
        if domain_key not in domain_map:
            issues.append(f"unknown_domain::{domain_key}")
            continue
        item_map = {item.item_key: item for item in domain_map[domain_key].items}
        for item_key, score in item_scores.items():
            if item_key not in item_map:
                issues.append(f"unknown_item::{domain_key}::{item_key}")
                continue
            item_schema = item_map[item_key]
            if not item_schema.response_min <= score <= item_schema.response_max:
                issues.append(f"score_out_of_range::{domain_key}::{item_key}::{score}")
        missing_items = sorted(set(item_map) - set(item_scores))
        for item_key in missing_items:
            issues.append(f"missing_item::{domain_key}::{item_key}")

    missing_domains = sorted(set(domain_map) - set(response_model.domain_item_scores))
    for domain_key in missing_domains:
        issues.append(f"missing_domain::{domain_key}")

    return issues


def build_default_pro_domain_norms_v1(
    schema: PROFormSchemaV1 | None = None,
) -> dict[str, PRODomainNormV1]:
    schema_model = schema or build_default_pro_form_schema_v1()
    return {
        domain.domain_key.value: PRODomainNormV1(domain_key=domain.domain_key)
        for domain in schema_model.domains
    }


def validate_pro_domain_norms_v1(
    norms: dict[str, PRODomainNormV1] | dict[str, dict[str, object]],
    schema: PROFormSchemaV1,
) -> list[str]:
    issues: list[str] = []
    norm_models: dict[str, PRODomainNormV1] = {}
    for domain_key, norm in norms.items():
        try:
            norm_models[domain_key] = (
                norm if isinstance(norm, PRODomainNormV1) else PRODomainNormV1.model_validate(norm)
            )
        except ValidationError as exc:
            for error in exc.errors():
                if error["loc"] == ("problem_score_std",):
                    issues.append(f"invalid_norm_std::{domain_key}::{norm.get('problem_score_std')}")
                else:
                    issues.append(f"invalid_norm::{domain_key}::{error['loc'][0]}")
    schema_domains = {domain.domain_key.value for domain in schema.domains}
    norm_domains = set(norm_models)

    for domain_key in sorted(schema_domains - norm_domains):
        issues.append(f"missing_norm::{domain_key}")
    for domain_key in sorted(norm_domains - schema_domains):
        issues.append(f"unknown_norm::{domain_key}")

    for domain_key in sorted(schema_domains & norm_domains):
        norm = norm_models[domain_key]
        if norm.problem_score_std <= PRO_Z_SCORE_STD_FLOOR:
            issues.append(f"invalid_norm_std::{domain_key}::{norm.problem_score_std}")
        if norm.score_orientation != PRO_SCORE_ORIENTATION_V1:
            issues.append(f"unsupported_orientation::{domain_key}::{norm.score_orientation}")

    return issues


def transform_pro_response_to_zscores_v1(
    response: PROFormResponseV1 | dict[str, object],
    *,
    schema: PROFormSchemaV1 | None = None,
    norms: dict[str, PRODomainNormV1] | dict[str, dict[str, object]] | None = None,
) -> PROZScoreSnapshotV1:
    schema_model = schema or build_default_pro_form_schema_v1()
    response_model = (
        response
        if isinstance(response, PROFormResponseV1)
        else PROFormResponseV1.model_validate(response)
    )
    response_issues = validate_pro_form_response_v1(response_model, schema_model)
    if response_issues:
        raise ValueError("invalid_pro_form_response::" + "|".join(response_issues))

    norm_models = {
        domain_key: (
            norm if isinstance(norm, PRODomainNormV1) else PRODomainNormV1.model_validate(norm)
        )
        for domain_key, norm in (norms or build_default_pro_domain_norms_v1(schema_model)).items()
    }
    norm_issues = validate_pro_domain_norms_v1(norm_models, schema_model)
    if norm_issues:
        raise ValueError("invalid_pro_domain_norms::" + "|".join(norm_issues))

    domain_problem_scores: dict[str, float] = {}
    domain_z: dict[str, float] = {}
    for domain in schema_model.domains:
        domain_key = domain.domain_key.value
        item_scores = response_model.domain_item_scores[domain_key]
        problem_score = round(sum(item_scores.values()) / len(item_scores), 6)
        norm = norm_models[domain_key]
        z_value = round((norm.problem_score_mean - problem_score) / norm.problem_score_std, 6)
        domain_problem_scores[domain_key] = problem_score
        domain_z[domain_key] = z_value

    aggregate_z = round(sum(domain_z.values()) / len(domain_z), 6)
    return PROZScoreSnapshotV1(
        timepoint=response_model.timepoint,
        domain_problem_scores=domain_problem_scores,
        domain_z=domain_z,
        aggregate_z=aggregate_z,
    )


def _summarize_pro_improvement_from_snapshots_v1(
    *,
    baseline_snapshot: PROZScoreSnapshotV1 | dict[str, object] | object,
    follow_up_snapshot: PROZScoreSnapshotV1 | dict[str, object] | object,
) -> PROImprovementSummaryV1:
    baseline_timepoint = _read_snapshot_value(baseline_snapshot, "timepoint")
    follow_up_timepoint = _read_snapshot_value(follow_up_snapshot, "timepoint")
    if baseline_timepoint != "baseline":
        raise ValueError(f"invalid_baseline_timepoint::{baseline_timepoint}")
    if follow_up_timepoint != "follow_up":
        raise ValueError(f"invalid_follow_up_timepoint::{follow_up_timepoint}")

    baseline_domain_z = dict(_read_snapshot_value(baseline_snapshot, "domain_z"))
    follow_up_domain_z = dict(_read_snapshot_value(follow_up_snapshot, "domain_z"))
    if set(baseline_domain_z) != set(follow_up_domain_z):
        raise ValueError("domain_mismatch::baseline_vs_follow_up")

    domain_delta_z: dict[str, float] = {}
    improved_domain_count = 0
    worsened_domain_count = 0
    unchanged_domain_count = 0
    for domain_key in sorted(baseline_domain_z):
        delta = round(follow_up_domain_z[domain_key] - baseline_domain_z[domain_key], 6)
        domain_delta_z[domain_key] = delta
        if delta > PRO_IMPROVEMENT_DELTA_TOLERANCE:
            improved_domain_count += 1
        elif delta < -PRO_IMPROVEMENT_DELTA_TOLERANCE:
            worsened_domain_count += 1
        else:
            unchanged_domain_count += 1

    baseline_aggregate_z = _read_snapshot_value(baseline_snapshot, "aggregate_z")
    follow_up_aggregate_z = _read_snapshot_value(follow_up_snapshot, "aggregate_z")
    baseline_aggregate_percentile = _read_snapshot_percentile(
        baseline_snapshot,
        "aggregate_percentile",
        z_value=baseline_aggregate_z,
    )
    follow_up_aggregate_percentile = _read_snapshot_percentile(
        follow_up_snapshot,
        "aggregate_percentile",
        z_value=follow_up_aggregate_z,
    )
    aggregate_delta_z = round(
        follow_up_aggregate_z - baseline_aggregate_z,
        6,
    )
    aggregate_delta_pp = round(
        follow_up_aggregate_percentile - baseline_aggregate_percentile,
        6,
    )
    if aggregate_delta_z > PRO_IMPROVEMENT_DELTA_TOLERANCE:
        net_status = "net_improvement"
    elif aggregate_delta_z < -PRO_IMPROVEMENT_DELTA_TOLERANCE:
        net_status = "net_worsening"
    else:
        net_status = "no_material_change"

    return PROImprovementSummaryV1(
        baseline_timepoint="baseline",
        follow_up_timepoint="follow_up",
        baseline_aggregate_z=baseline_aggregate_z,
        follow_up_aggregate_z=follow_up_aggregate_z,
        baseline_aggregate_percentile=baseline_aggregate_percentile,
        follow_up_aggregate_percentile=follow_up_aggregate_percentile,
        aggregate_delta_z=aggregate_delta_z,
        aggregate_delta_pp=aggregate_delta_pp,
        domain_delta_z=domain_delta_z,
        improved_domain_count=improved_domain_count,
        worsened_domain_count=worsened_domain_count,
        unchanged_domain_count=unchanged_domain_count,
        net_status=net_status,
    )


def coerce_baseline_followup_pro_event_v1(
    event: BaselineFollowUpPROEventV1 | dict[str, object] | object,
) -> BaselineFollowUpPROEventV1:
    event_model = (
        event
        if isinstance(event, BaselineFollowUpPROEventV1)
        else (
            build_baseline_followup_pro_event_v1(event)
            if _looks_like_record_payload(event)
            else BaselineFollowUpPROEventV1.model_validate(event)
        )
    )
    event_issues = validate_baseline_followup_pro_event_v1(event_model)
    if event_issues:
        raise ValueError("invalid_baseline_followup_pro_event::" + "|".join(event_issues))
    return event_model


def summarize_pro_improvement_from_normalized_event_v1(
    event: BaselineFollowUpPROEventV1 | dict[str, object],
) -> PROImprovementSummaryV1:
    event_model = (
        event
        if isinstance(event, BaselineFollowUpPROEventV1)
        else BaselineFollowUpPROEventV1.model_validate(event)
    )
    event_issues = validate_baseline_followup_pro_event_v1(event_model)
    if event_issues:
        raise ValueError("invalid_baseline_followup_pro_event::" + "|".join(event_issues))
    return _summarize_pro_improvement_from_snapshots_v1(
        baseline_snapshot=event_model.baseline,
        follow_up_snapshot=event_model.follow_up,
    )


def summarize_pro_improvement_from_event_v1(
    event: BaselineFollowUpPROEventV1 | dict[str, object] | object,
) -> PROImprovementSummaryV1:
    event_model = coerce_baseline_followup_pro_event_v1(event)
    return summarize_pro_improvement_from_normalized_event_v1(
        event_model.model_dump(mode="json")
    )


def validate_pro_improvement_summary_from_normalized_event_v1(
    *,
    event: BaselineFollowUpPROEventV1 | dict[str, object],
    summary: PROImprovementSummaryV1 | dict[str, object],
) -> list[str]:
    summary_model = (
        summary
        if isinstance(summary, PROImprovementSummaryV1)
        else PROImprovementSummaryV1.model_validate(summary)
    )
    expected = summarize_pro_improvement_from_normalized_event_v1(event)
    issues: list[str] = []

    if (
        abs(summary_model.aggregate_delta_z - expected.aggregate_delta_z)
        > PRO_IMPROVEMENT_DELTA_TOLERANCE
    ):
        issues.append(
            "aggregate_delta_mismatch::"
            f"{expected.aggregate_delta_z}::{summary_model.aggregate_delta_z}"
        )
    if (
        abs(summary_model.aggregate_delta_pp - expected.aggregate_delta_pp)
        > PRO_IMPROVEMENT_DELTA_TOLERANCE
    ):
        issues.append(
            "aggregate_delta_pp_mismatch::"
            f"{expected.aggregate_delta_pp}::{summary_model.aggregate_delta_pp}"
        )
    if (
        abs(summary_model.baseline_aggregate_z - expected.baseline_aggregate_z)
        > PRO_IMPROVEMENT_DELTA_TOLERANCE
    ):
        issues.append(
            "baseline_aggregate_z_mismatch::"
            f"{expected.baseline_aggregate_z}::{summary_model.baseline_aggregate_z}"
        )
    if (
        abs(summary_model.follow_up_aggregate_z - expected.follow_up_aggregate_z)
        > PRO_IMPROVEMENT_DELTA_TOLERANCE
    ):
        issues.append(
            "follow_up_aggregate_z_mismatch::"
            f"{expected.follow_up_aggregate_z}::{summary_model.follow_up_aggregate_z}"
        )
    if (
        abs(
            summary_model.baseline_aggregate_percentile
            - expected.baseline_aggregate_percentile
        )
        > PRO_IMPROVEMENT_DELTA_TOLERANCE
    ):
        issues.append(
            "baseline_aggregate_percentile_mismatch::"
            f"{expected.baseline_aggregate_percentile}::"
            f"{summary_model.baseline_aggregate_percentile}"
        )
    if (
        abs(
            summary_model.follow_up_aggregate_percentile
            - expected.follow_up_aggregate_percentile
        )
        > PRO_IMPROVEMENT_DELTA_TOLERANCE
    ):
        issues.append(
            "follow_up_aggregate_percentile_mismatch::"
            f"{expected.follow_up_aggregate_percentile}::"
            f"{summary_model.follow_up_aggregate_percentile}"
        )
    if summary_model.domain_delta_z != expected.domain_delta_z:
        issues.append("domain_delta_mismatch")
    if summary_model.improved_domain_count != expected.improved_domain_count:
        issues.append(
            "improved_domain_count_mismatch::"
            f"{expected.improved_domain_count}::{summary_model.improved_domain_count}"
        )
    if summary_model.worsened_domain_count != expected.worsened_domain_count:
        issues.append(
            "worsened_domain_count_mismatch::"
            f"{expected.worsened_domain_count}::{summary_model.worsened_domain_count}"
        )
    if summary_model.unchanged_domain_count != expected.unchanged_domain_count:
        issues.append(
            "unchanged_domain_count_mismatch::"
            f"{expected.unchanged_domain_count}::{summary_model.unchanged_domain_count}"
        )
    if summary_model.net_status != expected.net_status:
        issues.append(
            "net_status_mismatch::"
            f"{expected.net_status}::{summary_model.net_status}"
        )
    return issues


def validate_pro_improvement_summary_from_event_v1(
    *,
    event: BaselineFollowUpPROEventV1 | dict[str, object] | object,
    summary: PROImprovementSummaryV1 | dict[str, object],
) -> list[str]:
    event_model = coerce_baseline_followup_pro_event_v1(event)
    return validate_pro_improvement_summary_from_normalized_event_v1(
        event=event_model.model_dump(mode="json"),
        summary=summary,
    )


def summarize_pro_form_contract_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    dataset_path: str | Path,
) -> dict[str, object]:
    schema = build_default_pro_form_schema_v1()
    norms = build_default_pro_domain_norms_v1(schema)
    domain_keys = [domain.domain_key.value for domain in schema.domains]
    baseline_domain_coverage_pct = {
        domain_key: _domain_coverage_pct(records, domain_key, timepoint="baseline")
        for domain_key in domain_keys
    }
    follow_up_domain_coverage_pct = {
        domain_key: _domain_coverage_pct(records, domain_key, timepoint="follow_up")
        for domain_key in domain_keys
    }
    all_baseline_present = sum(
        1
        for record in records
        if all(domain_key in record.baseline_pro.domain_z for domain_key in domain_keys)
    )
    all_follow_up_present = sum(
        1
        for record in records
        if all(domain_key in record.follow_up_pro.domain_z for domain_key in domain_keys)
    )
    sample_mid_response = PROFormResponseV1(
        timepoint="baseline",
        domain_item_scores={
            domain.domain_key.value: {item.item_key: 2 for item in domain.items}
            for domain in schema.domains
        },
    )
    sample_improved_response = PROFormResponseV1(
        timepoint="follow_up",
        domain_item_scores={
            domain.domain_key.value: {
                item.item_key: (1 if domain.domain_key == RecommendationGoal.SLEEP_SUPPORT else 2)
                for item in domain.items
            }
            for domain in schema.domains
        },
    )
    sample_mid_z = transform_pro_response_to_zscores_v1(
        sample_mid_response,
        schema=schema,
        norms=norms,
    )
    sample_improved_z = transform_pro_response_to_zscores_v1(
        sample_improved_response,
        schema=schema,
        norms=norms,
    )
    sample_improvement_event = BaselineFollowUpPROEventV1(
        record_id="sample_pro_improvement_event",
        user_id="sample_user",
        cohort_version="pro_scoring_contract_v1_sample",
        trajectory_step=0,
        day_index=0,
        recommendation_goals=[RecommendationGoal.SLEEP_SUPPORT],
        follow_up_next_action="continue_plan",
        adverse_event=False,
        baseline={
            "timepoint": sample_mid_z.timepoint,
            "aggregate_z": sample_mid_z.aggregate_z,
            "domain_z": sample_mid_z.domain_z,
        },
        follow_up={
            "timepoint": sample_improved_z.timepoint,
            "aggregate_z": sample_improved_z.aggregate_z,
            "domain_z": sample_improved_z.domain_z,
        },
        delta_z_by_domain={
            domain_key: round(
                sample_improved_z.domain_z[domain_key] - sample_mid_z.domain_z[domain_key],
                6,
            )
            for domain_key in domain_keys
        },
    )
    sample_improvement_summary = summarize_pro_improvement_from_event_v1(
        sample_improvement_event
    )
    event_summaries: list[PROImprovementSummaryV1] = []
    invalid_event_summary_record_ids: list[str] = []
    for record in records:
        try:
            event_summaries.append(summarize_pro_improvement_from_event_v1(record))
        except ValueError:
            invalid_event_summary_record_ids.append(record.record_id)
    improved_case_count = sum(
        1 for summary in event_summaries if summary.net_status == "net_improvement"
    )
    worsened_case_count = sum(
        1 for summary in event_summaries if summary.net_status == "net_worsening"
    )
    unchanged_case_count = sum(
        1 for summary in event_summaries if summary.net_status == "no_material_change"
    )
    mean_aggregate_delta_z = round(
        sum(summary.aggregate_delta_z for summary in event_summaries) / len(event_summaries),
        6,
    ) if event_summaries else 0.0
    mean_aggregate_delta_pp = round(
        sum(summary.aggregate_delta_pp for summary in event_summaries) / len(event_summaries),
        6,
    ) if event_summaries else 0.0
    mean_domain_delta_z_by_domain = {
        domain_key: round(
            sum(summary.domain_delta_z[domain_key] for summary in event_summaries)
            / len(event_summaries),
            6,
        )
        if event_summaries
        else 0.0
        for domain_key in domain_keys
    }
    return {
        "contract_id": "pro_scoring_contract_v1",
        "schema_version": schema.schema_version,
        "dataset_path": str(dataset_path),
        "case_count": len(records),
        "user_count": len({record.user_id for record in records}),
        "timepoints": list(schema.timepoints),
        "domain_count": len(schema.domains),
        "domain_item_counts": {
            domain.domain_key.value: len(domain.items) for domain in schema.domains
        },
        "score_orientation": PRO_SCORE_ORIENTATION_V1,
        "zscore_transform": {
            "transform_version": PRO_Z_SCORE_TRANSFORM_VERSION_V1,
            "norm_version": PRO_Z_SCORE_NORM_VERSION_V1,
            "formula": "(problem_score_mean - domain_problem_score) / problem_score_std",
            "problem_score_definition": "mean of raw item scores within a domain",
            "aggregate_definition": "mean of domain z scores across all schema domains",
            "default_norms": {
                domain_key: norm.model_dump(mode="json") for domain_key, norm in norms.items()
            },
            "sample_transforms": {
                "mid_problem_score_zero_z": sample_mid_z.model_dump(mode="json"),
                "sleep_improvement_plus_one_z": sample_improved_z.model_dump(mode="json"),
            },
        },
        "improvement_metric": {
            "summary_version": PRO_IMPROVEMENT_SUMMARY_VERSION_V1,
            "formula": "follow_up_z - baseline_z",
            "aggregate_definition": "follow_up.aggregate_z - baseline.aggregate_z",
            "shared_event_schema_version": BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1,
            "shared_event_adapter": "summarize_pro_improvement_from_event_v1",
            "direct_normalized_event_adapter": (
                "summarize_pro_improvement_from_normalized_event_v1"
            ),
            "shared_event_unifier": "coerce_baseline_followup_pro_event_v1",
            "shared_event_validator": "validate_pro_improvement_summary_from_event_v1",
            "direct_normalized_event_validator": (
                "validate_pro_improvement_summary_from_normalized_event_v1"
            ),
            "single_path_status": {
                "event_adapter_only_public_entrypoint": True,
                "normalized_event_direct_compute_path": True,
                "direct_normalized_event_internal_only": True,
                "package_public_summary_entrypoint": (
                    "summarize_pro_improvement_from_event_v1"
                ),
                "package_public_validator_entrypoint": (
                    "validate_pro_improvement_summary_from_event_v1"
                ),
                "snapshot_pair_entrypoint_internal_only": True,
                "record_or_event_payloads_unified_by": "coerce_baseline_followup_pro_event_v1",
            },
            "net_status_rule": {
                "improvement": f"aggregate_delta_z > {PRO_IMPROVEMENT_DELTA_TOLERANCE}",
                "worsening": f"aggregate_delta_z < -{PRO_IMPROVEMENT_DELTA_TOLERANCE}",
                "no_material_change": (
                    f"abs(aggregate_delta_z) <= {PRO_IMPROVEMENT_DELTA_TOLERANCE}"
                ),
            },
            "sample_summary": sample_improvement_summary.model_dump(mode="json"),
            "synthetic_dataset_summary": {
                "improved_case_count": improved_case_count,
                "worsened_case_count": worsened_case_count,
                "unchanged_case_count": unchanged_case_count,
                "mean_aggregate_delta_z": mean_aggregate_delta_z,
                "mean_aggregate_delta_pp": mean_aggregate_delta_pp,
                "mean_domain_delta_z_by_domain": mean_domain_delta_z_by_domain,
            },
            "shared_event_path_proof": {
                "valid_case_count": len(event_summaries),
                "invalid_case_count": len(invalid_event_summary_record_ids),
                "invalid_record_ids": sorted(invalid_event_summary_record_ids),
                "example_summary": (
                    event_summaries[0].model_dump(mode="json")
                    if event_summaries
                    else None
                ),
            },
        },
        "synthetic_alignment": {
            "baseline_domain_coverage_pct": baseline_domain_coverage_pct,
            "follow_up_domain_coverage_pct": follow_up_domain_coverage_pct,
            "all_schema_domains_present_baseline_case_count": all_baseline_present,
            "all_schema_domains_present_follow_up_case_count": all_follow_up_present,
        },
        "sample_form_stub": {
            "baseline": _build_empty_form_stub(schema, timepoint="baseline"),
            "follow_up": _build_empty_form_stub(schema, timepoint="follow_up"),
        },
    }


def summarize_pro_improvement_summary_contract_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    dataset_path: str | Path,
) -> dict[str, object]:
    events = [coerce_baseline_followup_pro_event_v1(record) for record in records]
    summaries: list[PROImprovementSummaryV1] = []
    invalid_record_ids: list[str] = []
    same_structure_case_count = 0
    delta_pp_consistent_case_count = 0

    for event in events:
        try:
            summary = summarize_pro_improvement_from_event_v1(event)
            summaries.append(summary)
        except ValueError:
            invalid_record_ids.append(event.record_id)
            continue

        baseline_keys = set(event.baseline.model_dump(mode="json"))
        follow_up_keys = set(event.follow_up.model_dump(mode="json"))
        if baseline_keys == follow_up_keys:
            same_structure_case_count += 1

        expected_delta_pp = round(
            event.follow_up.aggregate_percentile - event.baseline.aggregate_percentile,
            6,
        )
        if abs(summary.aggregate_delta_pp - expected_delta_pp) <= PRO_IMPROVEMENT_DELTA_TOLERANCE:
            delta_pp_consistent_case_count += 1

    improved_case_count = sum(
        1 for summary in summaries if summary.net_status == "net_improvement"
    )
    worsened_case_count = sum(
        1 for summary in summaries if summary.net_status == "net_worsening"
    )
    unchanged_case_count = sum(
        1 for summary in summaries if summary.net_status == "no_material_change"
    )
    mean_aggregate_delta_z = round(
        sum(summary.aggregate_delta_z for summary in summaries) / len(summaries),
        6,
    ) if summaries else 0.0
    mean_aggregate_delta_pp = round(
        sum(summary.aggregate_delta_pp for summary in summaries) / len(summaries),
        6,
    ) if summaries else 0.0
    example_event = events[0].model_dump(mode="json") if events else None
    example_summary = summaries[0].model_dump(mode="json") if summaries else None

    return {
        "contract_id": "pro_improvement_summary_contract_v1",
        "dataset_path": str(dataset_path),
        "case_count": len(records),
        "user_count": len({record.user_id for record in records}),
        "shared_event_schema_version": BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1,
        "summary_version": PRO_IMPROVEMENT_SUMMARY_VERSION_V1,
        "normalized_snapshot_fields": [
            "timepoint",
            "aggregate_z",
            "aggregate_percentile",
            "domain_z",
            "domain_percentile",
        ],
        "path_status": {
            "derived_directly_from_shared_event_contract": True,
            "baseline_follow_up_same_normalized_structure_case_count": same_structure_case_count,
            "event_to_summary_valid_case_count": len(summaries),
            "event_to_summary_invalid_case_count": len(invalid_record_ids),
            "frozen_eval_compatible": True,
            "frozen_eval_metric": "efficacy_improvement_pp",
        },
        "consistency_checks": {
            "zscore_to_percentile_formula": "percentile = 100 * NormalCDF(z)",
            "aggregate_delta_z_formula": "follow_up.aggregate_z - baseline.aggregate_z",
            "aggregate_delta_pp_formula": (
                "follow_up.aggregate_percentile - baseline.aggregate_percentile"
            ),
            "delta_pp_matches_percentile_diff_case_count": delta_pp_consistent_case_count,
            "delta_pp_matches_percentile_diff_all_valid_cases": (
                delta_pp_consistent_case_count == len(summaries)
            ),
        },
        "synthetic_dataset_summary": {
            "improved_case_count": improved_case_count,
            "worsened_case_count": worsened_case_count,
            "unchanged_case_count": unchanged_case_count,
            "mean_aggregate_delta_z": mean_aggregate_delta_z,
            "mean_aggregate_delta_pp": mean_aggregate_delta_pp,
            "invalid_record_ids": sorted(invalid_record_ids),
        },
        "example_event": example_event,
        "example_summary": example_summary,
    }


def write_pro_form_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_pro_form_contract_markdown_v1(report), encoding="utf-8")


def write_pro_improvement_summary_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_pro_improvement_summary_contract_markdown_v1(report),
        encoding="utf-8",
    )


def render_pro_form_contract_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# pro scoring contract v1",
        "",
        f"- dataset_path: {report['dataset_path']}",
        f"- case_count: {report['case_count']}",
        f"- user_count: {report['user_count']}",
        f"- schema_version: {report['schema_version']}",
        f"- domain_count: {report['domain_count']}",
        f"- timepoints: {report['timepoints']}",
        f"- score_orientation: {report['score_orientation']}",
        "",
        "## z-score transform",
        "",
        f"- transform_version: {report['zscore_transform']['transform_version']}",
        f"- norm_version: {report['zscore_transform']['norm_version']}",
        f"- formula: `{report['zscore_transform']['formula']}`",
        f"- problem_score_definition: {report['zscore_transform']['problem_score_definition']}",
        f"- aggregate_definition: {report['zscore_transform']['aggregate_definition']}",
        "",
        "| domain | norm_mean | norm_std |",
        "| --- | --- | --- |",
    ]
    for domain_key, norm in report["zscore_transform"]["default_norms"].items():
        lines.append(
            f"| {domain_key} | {norm['problem_score_mean']} | {norm['problem_score_std']} |"
        )

    lines.extend(
        [
            "",
            "## z-score examples",
            "",
            "- mid_problem_score_zero_z.aggregate_z: "
            f"{report['zscore_transform']['sample_transforms']['mid_problem_score_zero_z']['aggregate_z']}",
            "- sleep_improvement_plus_one_z.aggregate_z: "
            f"{report['zscore_transform']['sample_transforms']['sleep_improvement_plus_one_z']['aggregate_z']}",
            "- sleep_improvement_plus_one_z.sleep_support: "
            f"{report['zscore_transform']['sample_transforms']['sleep_improvement_plus_one_z']['domain_z']['sleep_support']}",
            "",
            "## improvement metric",
            "",
            f"- summary_version: {report['improvement_metric']['summary_version']}",
            f"- formula: `{report['improvement_metric']['formula']}`",
            f"- aggregate_definition: {report['improvement_metric']['aggregate_definition']}",
            "- shared_event_schema_version: "
            f"{report['improvement_metric']['shared_event_schema_version']}",
            f"- shared_event_adapter: {report['improvement_metric']['shared_event_adapter']}",
            "- direct_normalized_event_adapter: "
            f"{report['improvement_metric']['direct_normalized_event_adapter']}",
            f"- shared_event_unifier: {report['improvement_metric']['shared_event_unifier']}",
            f"- shared_event_validator: {report['improvement_metric']['shared_event_validator']}",
            "- direct_normalized_event_validator: "
            f"{report['improvement_metric']['direct_normalized_event_validator']}",
            "- single_path_status: "
            f"{report['improvement_metric']['single_path_status']}",
            f"- sample_summary.aggregate_delta_z: "
            f"{report['improvement_metric']['sample_summary']['aggregate_delta_z']}",
            f"- sample_summary.net_status: "
            f"{report['improvement_metric']['sample_summary']['net_status']}",
            f"- synthetic improved_case_count: "
            f"{report['improvement_metric']['synthetic_dataset_summary']['improved_case_count']}",
            f"- synthetic worsened_case_count: "
            f"{report['improvement_metric']['synthetic_dataset_summary']['worsened_case_count']}",
            f"- synthetic unchanged_case_count: "
            f"{report['improvement_metric']['synthetic_dataset_summary']['unchanged_case_count']}",
            f"- synthetic mean_aggregate_delta_z: "
            f"{report['improvement_metric']['synthetic_dataset_summary']['mean_aggregate_delta_z']}",
            f"- shared_event_path valid_case_count: "
            f"{report['improvement_metric']['shared_event_path_proof']['valid_case_count']}",
            f"- shared_event_path invalid_case_count: "
            f"{report['improvement_metric']['shared_event_path_proof']['invalid_case_count']}",
            "",
            "## domain item counts",
            "",
            "| domain | item_count |",
            "| --- | --- |",
        ]
    )
    for domain_key, item_count in report["domain_item_counts"].items():
        lines.append(f"| {domain_key} | {item_count} |")

    lines.extend(["", "## synthetic alignment", ""])
    lines.append(
        "- all_schema_domains_present_baseline_case_count: "
        f"{report['synthetic_alignment']['all_schema_domains_present_baseline_case_count']}"
    )
    lines.append(
        "- all_schema_domains_present_follow_up_case_count: "
        f"{report['synthetic_alignment']['all_schema_domains_present_follow_up_case_count']}"
    )
    lines.extend(["", "| domain | baseline_pct | follow_up_pct |", "| --- | --- | --- |"])
    for domain_key in report["domain_item_counts"]:
        lines.append(
            "| "
            f"{domain_key} | "
            f"{report['synthetic_alignment']['baseline_domain_coverage_pct'][domain_key]} | "
            f"{report['synthetic_alignment']['follow_up_domain_coverage_pct'][domain_key]} |"
        )

    lines.extend(
        [
            "",
            "## sample form stub",
            "",
            "- baseline domains: "
            f"{sorted(report['sample_form_stub']['baseline']['domain_item_scores'])}",
            "- follow_up domains: "
            f"{sorted(report['sample_form_stub']['follow_up']['domain_item_scores'])}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_pro_improvement_summary_contract_markdown_v1(report: dict[str, object]) -> str:
    path_status = report["path_status"]
    consistency_checks = report["consistency_checks"]
    dataset_summary = report["synthetic_dataset_summary"]
    example_summary = report["example_summary"]
    lines = [
        "# pro improvement summary contract v1",
        "",
        f"- dataset_path: {report['dataset_path']}",
        f"- case_count: {report['case_count']}",
        f"- user_count: {report['user_count']}",
        f"- shared_event_schema_version: {report['shared_event_schema_version']}",
        f"- summary_version: {report['summary_version']}",
        "",
        "## path status",
        "",
        "- derived_directly_from_shared_event_contract: "
        f"{path_status['derived_directly_from_shared_event_contract']}",
        "- baseline_follow_up_same_normalized_structure_case_count: "
        f"{path_status['baseline_follow_up_same_normalized_structure_case_count']}",
        f"- event_to_summary_valid_case_count: {path_status['event_to_summary_valid_case_count']}",
        "- event_to_summary_invalid_case_count: "
        f"{path_status['event_to_summary_invalid_case_count']}",
        f"- frozen_eval_compatible: {path_status['frozen_eval_compatible']}",
        f"- frozen_eval_metric: {path_status['frozen_eval_metric']}",
        "",
        "## consistency checks",
        "",
        f"- zscore_to_percentile_formula: `{consistency_checks['zscore_to_percentile_formula']}`",
        f"- aggregate_delta_z_formula: `{consistency_checks['aggregate_delta_z_formula']}`",
        f"- aggregate_delta_pp_formula: `{consistency_checks['aggregate_delta_pp_formula']}`",
        "- delta_pp_matches_percentile_diff_case_count: "
        f"{consistency_checks['delta_pp_matches_percentile_diff_case_count']}",
        "- delta_pp_matches_percentile_diff_all_valid_cases: "
        f"{consistency_checks['delta_pp_matches_percentile_diff_all_valid_cases']}",
        "",
        "## dataset summary",
        "",
        f"- improved_case_count: {dataset_summary['improved_case_count']}",
        f"- worsened_case_count: {dataset_summary['worsened_case_count']}",
        f"- unchanged_case_count: {dataset_summary['unchanged_case_count']}",
        f"- mean_aggregate_delta_z: {dataset_summary['mean_aggregate_delta_z']}",
        f"- mean_aggregate_delta_pp: {dataset_summary['mean_aggregate_delta_pp']}",
        f"- invalid_record_ids: {dataset_summary['invalid_record_ids']}",
        "",
        "## normalized snapshot fields",
        "",
        f"- {report['normalized_snapshot_fields']}",
        "",
        "## example summary",
        "",
        f"- baseline_aggregate_z: {example_summary['baseline_aggregate_z']}",
        f"- follow_up_aggregate_z: {example_summary['follow_up_aggregate_z']}",
        "- baseline_aggregate_percentile: "
        f"{example_summary['baseline_aggregate_percentile']}",
        "- follow_up_aggregate_percentile: "
        f"{example_summary['follow_up_aggregate_percentile']}",
        f"- aggregate_delta_z: {example_summary['aggregate_delta_z']}",
        f"- aggregate_delta_pp: {example_summary['aggregate_delta_pp']}",
        f"- net_status: {example_summary['net_status']}",
    ]
    return "\n".join(lines) + "\n"


def _domain_schema(
    domain_key: RecommendationGoal,
    display_name: str,
    items: list[tuple[str, str]],
) -> PRODomainFormSchemaV1:
    return PRODomainFormSchemaV1(
        domain_key=domain_key,
        display_name=display_name,
        baseline_form_key=f"pro::{domain_key.value}::baseline_v1",
        follow_up_form_key=f"pro::{domain_key.value}::follow_up_v1",
        items=[
            PROItemSchemaV1(item_key=item_key, prompt_label=prompt_label)
            for item_key, prompt_label in items
        ],
    )


def _build_empty_form_stub(
    schema: PROFormSchemaV1,
    *,
    timepoint: Literal["baseline", "follow_up"],
) -> dict[str, object]:
    return PROFormResponseV1(
        timepoint=timepoint,
        domain_item_scores={
            domain.domain_key.value: {item.item_key: 0 for item in domain.items}
            for domain in schema.domains
        },
    ).model_dump(mode="json")


def _domain_coverage_pct(
    records: list[RichSyntheticCohortRecord],
    domain_key: str,
    *,
    timepoint: Literal["baseline", "follow_up"],
) -> float:
    if not records:
        return 0.0
    present_count = sum(
        1
        for record in records
        if domain_key
        in (
            record.baseline_pro.domain_z
            if timepoint == "baseline"
            else record.follow_up_pro.domain_z
        )
    )
    return round(100.0 * present_count / len(records), 3)


def _read_snapshot_value(snapshot: PROZScoreSnapshotV1 | dict[str, object] | object, key: str):
    if isinstance(snapshot, dict):
        return snapshot[key]
    return getattr(snapshot, key)


def _read_snapshot_percentile(
    snapshot: PROZScoreSnapshotV1 | dict[str, object] | object,
    key: str,
    *,
    z_value: float,
) -> float:
    if isinstance(snapshot, dict):
        percentile = snapshot.get(key)
    else:
        percentile = getattr(snapshot, key, None)
    if percentile is None:
        return _z_to_percentile(z_value)
    return round(float(percentile), 6)


def _z_to_percentile(z_value: float) -> float:
    return round(percentile_improvement_pp(z_pre=0.0, z_post=z_value) + 50.0, 6)


def _looks_like_record_payload(payload: object) -> bool:
    if isinstance(payload, dict):
        required_keys = {
            "record_id",
            "user_id",
            "baseline_pro",
            "follow_up_pro",
            "delta_z_by_domain",
        }
        return required_keys <= set(payload)
    return all(
        hasattr(payload, key)
        for key in (
            "record_id",
            "user_id",
            "baseline_pro",
            "follow_up_pro",
            "delta_z_by_domain",
        )
    )


__all__ = [
    "PRO_BASELINE_DISTRIBUTION_SCHEMA_VERSION_V1",
    "PRO_BASELINE_SCORE_OBSERVATION_SCHEMA_VERSION_V1",
    "PRO_BASELINE_STANDARDIZATION_VERSION_V1",
    "PRO_IMPROVEMENT_SUMMARY_VERSION_V1",
    "PRO_INSTRUMENT_CONTRACT_SCHEMA_VERSION_V1",
    "PRO_INSTRUMENT_CONTRACT_VERSION_V1",
    "PRO_INSTRUMENT_RESPONSE_SCHEMA_VERSION_V1",
    "PRO_INSTRUMENT_SCORE_SCHEMA_VERSION_V1",
    "PRO_STANDARDIZED_SCORE_SCHEMA_VERSION_V1",
    "PROBaselineDistributionV1",
    "PROBaselineScoreObservationV1",
    "PROBaselineStandardizationContractV1",
    "PRODomainNormV1",
    "PRODomainFormSchemaV1",
    "PROFormResponseV1",
    "PROFormSchemaV1",
    "PROImprovementSummaryV1",
    "PROInstrumentDefinitionV1",
    "PROInstrumentResponseV1",
    "PROInstrumentScoreV1",
    "PROInstrumentScoringContractV1",
    "PROItemSchemaV1",
    "PROStandardizedScoreV1",
    "PROZScoreSnapshotV1",
    "PRO_FORM_SCHEMA_VERSION_V1",
    "PRO_SCORE_ORIENTATION_V1",
    "PRO_Z_SCORE_NORM_VERSION_V1",
    "PRO_Z_SCORE_TRANSFORM_VERSION_V1",
    "build_default_pro_domain_norms_v1",
    "build_default_pro_form_schema_v1",
    "build_pro_baseline_distribution_v1",
    "coerce_baseline_followup_pro_event_v1",
    "load_pro_instrument_scoring_contract_v1",
    "render_pro_improvement_summary_contract_markdown_v1",
    "render_pro_form_contract_markdown_v1",
    "score_pro_instrument_response_v1",
    "standardize_pro_instrument_score_v1",
    "summarize_pro_form_contract_v1",
    "summarize_pro_improvement_summary_contract_v1",
    "summarize_pro_improvement_from_event_v1",
    "summarize_pro_improvement_from_normalized_event_v1",
    "transform_pro_response_to_zscores_v1",
    "validate_pro_improvement_summary_from_event_v1",
    "validate_pro_improvement_summary_from_normalized_event_v1",
    "validate_pro_domain_norms_v1",
    "validate_pro_form_response_v1",
    "write_pro_improvement_summary_contract_report_v1",
    "write_pro_form_contract_report_v1",
]
