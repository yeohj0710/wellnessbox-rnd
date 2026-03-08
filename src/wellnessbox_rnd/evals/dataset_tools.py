import json
from collections import Counter
from pathlib import Path

from wellnessbox_rnd.evals.runner import EvalCase, load_eval_cases
from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationStatus,
)

KNOWN_INTEGRATION_MODALITIES = ("wearable", "cgm", "genetic")


def build_eval_case_skeleton(
    *,
    case_id: str,
    category: str,
    description: str,
    goals: list[str],
    required_ingredients: list[str] | None = None,
    expected_status: str = RecommendationStatus.OK.value,
    expected_next_action: str = NextAction.START_PLAN.value,
    required_explanation_terms: list[str] | None = None,
    synthetic: bool = True,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "synthetic": synthetic,
        "category": category,
        "description": description,
        "request": {
            "request_id": case_id,
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": goals,
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        },
        "expected": {
            "recommendation_reference": {
                "required_ingredients": required_ingredients or [],
            },
            "expected_status": expected_status,
            "expected_next_action": expected_next_action,
            "required_rule_ids": [],
            "required_excluded_ingredients": [],
            "required_explanation_terms": required_explanation_terms
            or ["deterministic baseline"],
            "minimum_explanation_term_coverage": 100.0,
        },
        "follow_up": None,
        "integration": {
            modality: {"attempted": 0, "success": 0}
            for modality in KNOWN_INTEGRATION_MODALITIES
        },
        "adverse_event_reported": False,
    }


def summarize_eval_cases(cases: list[EvalCase]) -> dict[str, object]:
    category_counts = Counter(case.category for case in cases)
    next_action_counts = Counter(
        case.expected.expected_next_action.value
        for case in cases
        if case.expected.expected_next_action is not None
    )
    modality_attempted_case_counts = {modality: 0 for modality in KNOWN_INTEGRATION_MODALITIES}
    modality_attempted_totals = {modality: 0 for modality in KNOWN_INTEGRATION_MODALITIES}
    modality_success_totals = {modality: 0 for modality in KNOWN_INTEGRATION_MODALITIES}

    for case in cases:
        for modality in KNOWN_INTEGRATION_MODALITIES:
            observation = case.integration.get(modality)
            if observation is None:
                continue
            modality_attempted_totals[modality] += observation.attempted
            modality_success_totals[modality] += observation.success
            if observation.attempted > 0:
                modality_attempted_case_counts[modality] += 1

    return {
        "case_count": len(cases),
        "synthetic_case_count": sum(case.synthetic for case in cases),
        "follow_up_case_count": sum(case.follow_up is not None for case in cases),
        "category_counts": dict(sorted(category_counts.items())),
        "expected_next_action_counts": dict(sorted(next_action_counts.items())),
        "integration_attempted_case_counts": modality_attempted_case_counts,
        "integration_totals": {
            modality: {
                "attempted": modality_attempted_totals[modality],
                "success": modality_success_totals[modality],
            }
            for modality in KNOWN_INTEGRATION_MODALITIES
        },
    }


def validate_eval_cases(cases: list[EvalCase]) -> list[str]:
    issues: list[str] = []
    if not cases:
        return ["dataset is empty"]

    case_ids = [case.case_id for case in cases]
    duplicates = sorted(case_id for case_id, count in Counter(case_ids).items() if count > 1)
    if duplicates:
        issues.append(f"duplicate case_id values: {', '.join(duplicates)}")

    if case_ids != sorted(case_ids):
        issues.append("case_id ordering is not sorted lexicographically")

    for case in cases:
        if case.request.request_id != case.case_id:
            issues.append(
                f"{case.case_id}: request.request_id must match case_id for deterministic tracing"
            )
        if not 0.0 <= case.expected.minimum_explanation_term_coverage <= 100.0:
            issues.append(
                f"{case.case_id}: minimum_explanation_term_coverage must be between 0 and 100"
            )
        if (
            case.expected.minimum_explanation_term_coverage > 0
            and not case.expected.required_explanation_terms
        ):
            issues.append(
                f"{case.case_id}: required_explanation_terms cannot be empty when coverage > 0"
            )
        for modality, observation in case.integration.items():
            if modality not in KNOWN_INTEGRATION_MODALITIES:
                issues.append(f"{case.case_id}: unknown integration modality '{modality}'")
            if observation.success > observation.attempted:
                issues.append(
                    f"{case.case_id}: integration.{modality}.success cannot exceed attempted"
                )

    return issues


def load_and_validate_eval_cases(dataset_path: str | Path) -> tuple[list[EvalCase], list[str]]:
    cases = load_eval_cases(dataset_path)
    return cases, validate_eval_cases(cases)


def write_eval_cases_jsonl(cases: list[dict[str, object]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(case, ensure_ascii=False, separators=(",", ":"))
        for case in sorted(cases, key=lambda item: str(item["case_id"]))
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
