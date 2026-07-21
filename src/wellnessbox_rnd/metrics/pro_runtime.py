from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineScoreObservationV1,
    PROInstrumentScoreV1,
    PROStandardizedScoreV1,
    build_pro_baseline_distribution_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)

DEFAULT_PRO_RUNTIME_REFERENCE_PATH = Path(
    "data/contracts/pro_runtime_reference_baselines_v1.json"
)
_EXPECTED_INSTRUMENTS = ("PSQI", "ISI", "PSS10")


def load_pro_runtime_reference_v1(
    path: str | Path = DEFAULT_PRO_RUNTIME_REFERENCE_PATH,
) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "pro_runtime_reference_baselines_v1":
        raise ValueError("invalid_pro_runtime_reference::schema_version")
    if payload.get("contract_version") != "2026-07-21.1":
        raise ValueError("invalid_pro_runtime_reference::contract_version")
    if payload.get("data_class") != "SYNTHETIC_OUTCOME_PROXY":
        raise ValueError("invalid_pro_runtime_reference::data_class")
    instruments = payload.get("instruments")
    if not isinstance(instruments, list) or tuple(
        item.get("instrument") for item in instruments if isinstance(item, dict)
    ) != _EXPECTED_INSTRUMENTS:
        raise ValueError("invalid_pro_runtime_reference::instrument_order_or_coverage")
    return payload


def score_and_standardize_runtime_pro_v1(
    instrument: str,
    item_scores: list[int],
    *,
    reference_path: str | Path = DEFAULT_PRO_RUNTIME_REFERENCE_PATH,
) -> tuple[PROInstrumentScoreV1, PROStandardizedScoreV1]:
    reference = load_pro_runtime_reference_v1(reference_path)
    definition = next(
        (item for item in reference["instruments"] if item["instrument"] == instrument),
        None,
    )
    if definition is None:
        raise ValueError(f"unsupported_runtime_pro_instrument::{instrument}")
    score = score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": instrument,
            "item_scores": item_scores,
        }
    )
    reference_scores = [
        score_pro_instrument_response_v1(
            {
                "schema_version": "pro_instrument_response_v1",
                "instrument": instrument,
                "item_scores": values,
            }
        )
        for values in definition["item_score_sets"]
    ]
    distribution = build_pro_baseline_distribution_v1(
        [
            PROBaselineScoreObservationV1(
                schema_version="pro_baseline_score_observation_v1",
                observation_role="BASELINE",
                score=item,
            )
            for item in reference_scores
        ],
        cohort_id=definition["cohort_id"],
        data_class=reference["data_class"],
    )
    return score, standardize_pro_instrument_score_v1(score, distribution)


__all__ = [
    "DEFAULT_PRO_RUNTIME_REFERENCE_PATH",
    "load_pro_runtime_reference_v1",
    "score_and_standardize_runtime_pro_v1",
]
