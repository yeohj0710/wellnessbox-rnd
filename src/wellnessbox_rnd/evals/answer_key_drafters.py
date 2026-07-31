"""Draft KPI answer keys from sources that are not the recommendation engine.

KPI-1 scores the engine's ingredient combination against the set a pharmacist
would pick. Drafting that set from `goal_ingredient_priors_v1.json` and the
ingredient catalog is a different derivation than the engine's path — the engine
runs intake normalisation, safety assessment, candidate filtering, efficacy
scoring and an optimiser on top of those same priors. The priors alone do not
reproduce the optimiser's output, so the comparison still measures something.

The drafts are a starting point for the reviewer, never the final answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PRIORS_PATH = "data/knowledge/goal_ingredient_priors_v1.json"
CATALOG_PATH = "data/catalog/ingredients.json"
DRAFT_SOURCE = "goal_ingredient_priors_v1+ingredient_catalog"

# Population and medication contexts the safety rules already recognise.
CONTEXTS: tuple[dict[str, Any], ...] = (
    {"label": "성인 일반", "medications": [], "conditions": []},
    {"label": "warfarin 복용", "medications": ["warfarin"], "conditions": []},
    {"label": "levothyroxine 복용", "medications": ["levothyroxine"], "conditions": []},
    {"label": "metformin 복용", "medications": ["metformin"], "conditions": []},
    {"label": "omeprazole 복용", "medications": ["omeprazole"], "conditions": []},
    {"label": "임신 중", "medications": [], "conditions": ["pregnancy"]},
    {"label": "수유 중", "medications": [], "conditions": ["lactation"]},
    {"label": "중증 신장질환", "medications": [], "conditions": ["severe_renal_impairment"]},
    {"label": "간질환", "medications": [], "conditions": ["hepatic_impairment"]},
    {"label": "혈색소침착증", "medications": [], "conditions": ["hemochromatosis"]},
)
AGE_BANDS = (24, 33, 41, 52, 58, 63, 67, 71)


def load_priors(root: Path) -> list[dict[str, Any]]:
    payload = json.loads((Path(root) / PRIORS_PATH).read_text(encoding="utf-8"))
    return [item for item in payload["records"] if isinstance(item, dict)]


def load_catalog(root: Path) -> list[dict[str, Any]]:
    payload = json.loads((Path(root) / CATALOG_PATH).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else payload.get("ingredients", [])


def goals_from_catalog(catalog: list[dict[str, Any]]) -> list[str]:
    goals: set[str] = set()
    for item in catalog:
        goals.update(item.get("supported_goals", []))
    return sorted(goals)


def ingredients_for_goal(
    goal: str,
    *,
    priors: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    limit: int = 4,
) -> list[str]:
    """Rank ingredients for a goal by prior score, falling back to the catalog."""
    scored = [
        (float(item.get("prior_score", 0.0)), str(item["ingredient_key"]))
        for item in priors
        if item.get("goal_key") == goal
        and item.get("evidence_direction") == "supports_candidate"
    ]
    if scored:
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [key for _, key in scored[:limit]]

    fallback = sorted(
        item["key"] for item in catalog if goal in item.get("supported_goals", [])
    )
    return fallback[:limit]


def draft_kpi1_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """Build KPI-1 cases by crossing goals with population and medication contexts."""
    priors = load_priors(root)
    catalog = load_catalog(root)
    goals = goals_from_catalog(catalog)
    if not goals:
        raise ValueError("no_goals_found_in_catalog")

    cases: list[dict[str, Any]] = []
    index = 0
    while len(cases) < case_count:
        goal = goals[index % len(goals)]
        context = CONTEXTS[(index // len(goals)) % len(CONTEXTS)]
        age = AGE_BANDS[index % len(AGE_BANDS)]
        answer = ingredients_for_goal(goal, priors=priors, catalog=catalog)
        if not answer:
            index += 1
            continue
        medications = ", ".join(context["medications"]) or "없음"
        conditions = ", ".join(context["conditions"]) or "없음"
        cases.append(
            {
                "case_id": f"kpi1-{len(cases) + 1:03}",
                "prompt": (
                    f"목표 {goal} / 나이 {age} / 복용약 {medications} / 상태 {conditions} "
                    f"({context['label']})"
                ),
                "draft_answer": answer,
                "draft_rationale": (
                    f"goal_ingredient_priors_v1의 {goal} 상위 근거 성분. "
                    "안전 규칙과 개인 상태는 검토자가 직접 반영한다."
                ),
            }
        )
        index += 1
        if index > case_count * len(CONTEXTS) * 4:
            break
    return cases


DRAFTERS = {"KPI-1": draft_kpi1_cases}


def draft_cases(indicator_id: str, root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    if indicator_id not in DRAFTERS:
        raise KeyError(
            f"no_drafter_for_indicator:{indicator_id}. "
            "다른 지표는 --cases 로 초안 파일을 직접 준다."
        )
    return DRAFTERS[indicator_id](root, case_count=case_count)
