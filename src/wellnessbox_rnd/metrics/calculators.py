from math import erf, sqrt
from statistics import mean


def recommendation_coverage_pct(
    required_ingredients: list[str],
    actual_ingredients: list[str],
) -> float | None:
    if not required_ingredients:
        return None
    required = set(required_ingredients)
    actual = set(actual_ingredients)
    return 100.0 * len(required & actual) / len(required)


def exact_match_pct(expected: str | None, actual: str | None) -> float | None:
    if expected is None:
        return None
    return 100.0 if expected == actual else 0.0


def subset_match_pct(required_items: list[str], actual_items: list[str]) -> float:
    required = set(required_items)
    actual = set(actual_items)
    if not required:
        return 100.0
    return 100.0 if required.issubset(actual) else 0.0


def explanation_term_coverage_pct(required_terms: list[str], actual_text: str) -> float | None:
    if not required_terms:
        return None
    haystack = actual_text.lower()
    present = sum(1 for term in required_terms if term.lower() in haystack)
    return 100.0 * present / len(required_terms)


def safety_reference_accuracy_pct(
    expected_status: str | None,
    actual_status: str,
    required_rule_ids: list[str],
    actual_rule_ids: list[str],
    required_excluded_ingredients: list[str],
    actual_excluded_ingredients: list[str],
) -> float | None:
    if expected_status is None and not required_rule_ids and not required_excluded_ingredients:
        return None

    components = [
        exact_match_pct(expected_status, actual_status) if expected_status is not None else 100.0,
        subset_match_pct(required_rule_ids, actual_rule_ids),
        subset_match_pct(required_excluded_ingredients, actual_excluded_ingredients),
    ]
    return mean(components)


def percentile_improvement_pp(z_pre: float, z_post: float) -> float:
    return 100.0 * (_normal_cdf(z_post) - _normal_cdf(z_pre))


def average_metric(values: list[float]) -> float | None:
    if not values:
        return None
    return mean(values)


def count_adverse_events(flags: list[bool]) -> int:
    return sum(1 for flag in flags if flag)


def sensor_genetic_integration_rate_pct(
    integration_records: list[dict[str, dict[str, int]]],
) -> float | None:
    attempted = 0
    success = 0
    for record in integration_records:
        for modality in record.values():
            attempted += modality.get("attempted", 0)
            success += modality.get("success", 0)
    if attempted == 0:
        return None
    return 100.0 * success / attempted


def integration_modality_rate_pct(
    integration_records: list[dict[str, dict[str, int]]],
    modality_name: str,
) -> float | None:
    attempted = 0
    success = 0
    for record in integration_records:
        modality = record.get(modality_name, {})
        attempted += modality.get("attempted", 0)
        success += modality.get("success", 0)
    if attempted == 0:
        return None
    return 100.0 * success / attempted


def integration_modality_breakdown(
    integration_records: list[dict[str, dict[str, int]]],
) -> dict[str, dict[str, float | int | None]]:
    breakdown: dict[str, dict[str, float | int | None]] = {}
    for modality_name in ("wearable", "cgm", "genetic"):
        attempted = 0
        success = 0
        for record in integration_records:
            modality = record.get(modality_name, {})
            attempted += modality.get("attempted", 0)
            success += modality.get("success", 0)
        score = None if attempted == 0 else 100.0 * success / attempted
        breakdown[modality_name] = {
            "attempted": attempted,
            "success": success,
            "score": score,
        }
    return breakdown


def metric_passed(score: float | None, comparison: str, target: float) -> bool | None:
    if score is None:
        return None
    if comparison == "min":
        return score >= target
    if comparison == "max":
        return score <= target
    if comparison == "positive":
        return score > target
    raise ValueError(f"Unsupported comparison: {comparison}")


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))
