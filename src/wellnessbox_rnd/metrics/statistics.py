from __future__ import annotations

import math
import random
import statistics
from collections.abc import Sequence


def linear_percentile(values: Sequence[float], quantile: float) -> float:
    checked = _checked_values(values)
    if not math.isfinite(quantile) or not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile_must_be_finite_between_zero_and_one")
    ordered = sorted(checked)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def deterministic_bootstrap_mean_ci(
    values: Sequence[float],
    *,
    confidence_level: float = 0.95,
    iterations: int = 3_000,
    seed: int = 20_260_710,
) -> tuple[float, float]:
    checked = _checked_values(values)
    if not math.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level_must_be_between_zero_and_one")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations_must_be_a_positive_integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed_must_be_an_integer")
    rng = random.Random(seed)
    estimates = [
        statistics.mean(rng.choice(checked) for _ in checked)
        for _ in range(iterations)
    ]
    tail_probability = (1.0 - confidence_level) / 2.0
    return (
        linear_percentile(estimates, tail_probability),
        linear_percentile(estimates, 1.0 - tail_probability),
    )


def _checked_values(values: Sequence[float]) -> list[float]:
    if not values:
        raise ValueError("values_required")
    checked = [float(value) for value in values]
    if any(not math.isfinite(value) for value in checked):
        raise ValueError("values_must_be_finite")
    return checked


__all__ = ["deterministic_bootstrap_mean_ci", "linear_percentile"]
