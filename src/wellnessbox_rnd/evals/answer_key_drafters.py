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




# ---------------------------------------------------------------- KPI-3

POLICY_PATH = "data/original_plan/closed_loop_next_action_policy_v1.json"
KPI3_PROFILE_VARIANTS: tuple[str, ...] = (
    "40대 수면 목표",
    "50대 심혈관 목표, warfarin 복용",
    "20대 에너지 목표",
    "60대 뼈·관절 목표, metformin 복용",
    "30대 장 건강 목표, omeprazole 복용",
    "40대 혈당 목표",
    "50대 면역 목표, levothyroxine 복용",
    "60대 인지 목표",
    "30대 피부 목표",
    "40대 체중 목표",
    "50대 간 건강 목표",
    "20대 스트레스 목표",
)


def load_next_action_rules(root: Path) -> list[dict[str, Any]]:
    payload = json.loads((Path(root) / POLICY_PATH).read_text(encoding="utf-8"))
    return sorted(payload["rules"], key=lambda item: int(item.get("priority", 999)))


def _describe_condition(condition: dict[str, Any]) -> str:
    """Render a rule's own trigger as the case's observed signal."""
    parts = []
    for key, value in condition.items():
        if key == "state":
            parts.append(f"상태 {value}")
        elif isinstance(value, dict):
            bound = ", ".join(f"{name} {bound}" for name, bound in value.items())
            parts.append(f"{key}({bound})")
        else:
            parts.append(f"{key}={value}")
    return " / ".join(parts)


def draft_kpi3_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """Enumerate each next-action rule across profile variants.

    The case states the observed signal; the draft answer is the action that
    rule prescribes. The reviewer decides whether that action is right for the
    profile, which is where the human judgment actually lives.
    """
    rules = load_next_action_rules(root)
    if not rules:
        raise ValueError("no_next_action_rules_found")
    cases: list[dict[str, Any]] = []
    index = 0
    while len(cases) < case_count:
        rule = rules[index % len(rules)]
        variant = KPI3_PROFILE_VARIANTS[(index // len(rules)) % len(KPI3_PROFILE_VARIANTS)]
        cases.append(
            {
                "case_id": f"kpi3-{len(cases) + 1:03}",
                "prompt": (
                    f"{variant} / 관찰 신호: {_describe_condition(rule.get('when', {}))} "
                    "— 다음 수행 작업은?"
                ),
                "draft_answer": [str(rule["action"])],
                "draft_rationale": (
                    f"{rule['rule_id']} 우선순위 {rule.get('priority')}, "
                    f"사유 코드 {rule.get('reason_code')}"
                ),
            }
        )
        index += 1
    return cases


# ---------------------------------------------------------------- KPI-4

KPI4_TEMPLATES: tuple[tuple[str, str], ...] = (
    (
        "{ingredient}을(를) {medication}과 같이 먹어도 되나요?",
        "상호작용 여부와 근거를 밝히고, 불확실하면 확정하지 않는다",
    ),
    ("{ingredient}은(는) 하루 최대 얼마까지 먹을 수 있나요?", "상한 수치와 근거 규칙을 제시한다"),
    (
        "임신 중에 {ingredient} 복용해도 되나요?",
        "특수집단 차단 규칙을 적용하고 전문가 상담을 안내한다",
    ),
    (
        "{ingredient} 먹고 속이 불편한데 계속 먹어야 하나요?",
        "이상반응 가능성을 알리고 중단·상담을 안내한다",
    ),
    ("{goal}에 도움이 되는 성분이 뭔가요?", "근거가 있는 성분만 제시하고 효과를 단정하지 않는다"),
)
KPI4_MEDICATIONS = ("warfarin", "levothyroxine", "metformin", "omeprazole")


def draft_kpi4_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """Build counselling questions from the catalog, with the answer criterion."""
    catalog = load_catalog(root)
    goals = goals_from_catalog(catalog)
    keys = [item["key"] for item in catalog]
    cases: list[dict[str, Any]] = []
    index = 0
    while len(cases) < case_count and index < case_count * 6:
        template, criterion = KPI4_TEMPLATES[index % len(KPI4_TEMPLATES)]
        question = template.format(
            ingredient=keys[index % len(keys)],
            medication=KPI4_MEDICATIONS[index % len(KPI4_MEDICATIONS)],
            goal=goals[index % len(goals)] if goals else "general",
        )
        cases.append(
            {
                "case_id": f"kpi4-{len(cases) + 1:03}",
                "prompt": question,
                "draft_answer": [criterion],
                "draft_rationale": (
                    "적절성 판정 기준 초안. "
                    "검토자가 사실성·적절성·완결성 기준으로 확정한다."
                ),
            }
        )
        index += 1
    return cases


# ---------------------------------------------------------------- KPI-5

SAFETY_RULES_PATH = "data/rules/safety_rules.json"
RULE_GROUPS = (
    "input_requirements",
    "risk_flag_rules",
    "allergy_rules",
    "medication_rules",
    "special_population_rules",
    "condition_rules",
    "dose_limits",
)


def load_safety_rules(root: Path) -> list[tuple[str, dict[str, Any]]]:
    payload = json.loads((Path(root) / SAFETY_RULES_PATH).read_text(encoding="utf-8"))
    rules: list[tuple[str, dict[str, Any]]] = []
    for group in RULE_GROUPS:
        for entry in payload.get(group, []):
            if isinstance(entry, dict) and entry.get("metadata", {}).get("rule_id"):
                rules.append((group, entry))
    return rules


def draft_kpi5_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """One case per rule, repeated across reference fields until the minimum is met."""
    rules = load_safety_rules(root)
    if not rules:
        raise ValueError("no_safety_rules_found")
    fields = ("rule_id", "severity", "excluded_ingredients", "reference_ids", "message")
    cases: list[dict[str, Any]] = []
    index = 0
    while len(cases) < case_count and index < case_count * 4:
        group, rule = rules[index % len(rules)]
        field = fields[(index // len(rules)) % len(fields)]
        metadata = rule.get("metadata", {})
        value = metadata.get(field, rule.get(field))
        if value is None or (isinstance(value, list) and not value):
            index += 1
            continue
        answer = value if isinstance(value, list) else [str(value)]
        cases.append(
            {
                "case_id": f"kpi5-{len(cases) + 1:03}",
                "prompt": f"{group} / {metadata['rule_id']} 의 {field} 참조값은?",
                "draft_answer": [str(item) for item in answer],
                "draft_rationale": (
                    f"safety_rules.json {group} 항목의 등록값. "
                    "검토자가 외부 근거와 대조한다."
                ),
            }
        )
        index += 1
    return cases


DRAFTERS = {
    "KPI-1": draft_kpi1_cases,
    "KPI-3": draft_kpi3_cases,
    "KPI-4": draft_kpi4_cases,
    "KPI-5": draft_kpi5_cases,
}


def draft_cases(indicator_id: str, root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    if indicator_id not in DRAFTERS:
        raise KeyError(
            f"no_drafter_for_indicator:{indicator_id}. "
            "다른 지표는 --cases 로 초안 파일을 직접 준다."
        )
    return DRAFTERS[indicator_id](root, case_count=case_count)
