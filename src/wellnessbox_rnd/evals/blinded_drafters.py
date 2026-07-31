"""Draft KPI-3 and KPI-4 answer keys without copying the engine's own tables.

The 2026-07-31 audit rejected the previous drafts for two different reasons, so
the two indicators need two different fixes.

KPI-4 — the previous draft asked 57 distinct questions (against a 100-question
minimum) and answered them with five hardcoded rubric strings repeated twenty
times each. It is fixed here the same way KPI-1 and KPI-5 were: the questions
and the answers both come from `health_checker_reference_extract_v1`, the
counseling work the project owner published before this engine existed. Each
answer names the ingredients the work supports for that goal plus the counseling
obligations the case triggers, and carries the page it came from. The answer
moves with the medication context, so a correct engine and a careless one score
differently.

KPI-3 — the previous draft took its answers from
`closed_loop_next_action_policy_v1.json`, which the engine itself loads at
`interim/next_action.py`, and built each question out of that same rule's `when`
clause. The engine reproduced it by construction. There is no external corpus
for closed-loop follow-up decisions, so this module does NOT invent one. It
generates the *situations* only — profile, history and observed signal, written
in clinical terms rather than in the policy's trigger syntax — and leaves the
action for the reviewer to supply. Every KPI-3 case therefore records as an
edit, because the human wrote the answer rather than approving one.

Blinding is a property of the derivation, not of who typed it. What matters is
that no answer here is read out of a file the engine also reads. The KPI-3
answers are not in this repository at all until a person puts them there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXTRACT_PATH = "data/knowledge/external/health_checker_reference_extract_v1.json"
DRAFT_SOURCE_KPI4 = "health_checker_reference_extract_v1@blinded_drafters"
DRAFT_SOURCE_KPI3 = "blinded_scenarios_reviewer_supplied_actions"

# Engine files that must not be read to produce these drafts. Recorded on the
# drafts so the claim is checkable rather than asserted in prose.
BLINDED_FROM: tuple[str, ...] = (
    "data/original_plan/closed_loop_next_action_policy_v1.json",
    "data/rules/safety_rules.json",
    "data/knowledge/goal_ingredient_priors_v1.json",
)

# Areas where the work's own guidance is to send the person to a professional.
SPECIAL_POPULATION_AREAS: frozenset[str] = frozenset({"38-pregnancy-lactation", "43-children"})

# The reviewer types one of these for KPI-3. Naming the vocabulary is not the
# same as handing over the mapping: which action fits which situation is the
# judgment being measured, and it is not written down here.
NEXT_ACTION_VOCABULARY: tuple[str, ...] = (
    "maintain",
    "reduce",
    "replace",
    "reoptimize",
    "hold_for_review",
    "request_followup",
    "request_measurement",
    "request_safety_review",
    "stop_and_escalate",
)

KPI3_UNDECIDED = "미정_검토자가_판단"

# Follow-up situations written from ordinary pharmaceutical care practice. None
# of these is a transcription of a policy trigger; they describe what a person
# reports or what an operator observes.
KPI3_SIGNALS: tuple[str, ...] = (
    "복용 2주차, 목표 지표에 변화가 없다",
    "복용 중 속쓰림과 메스꺼움을 호소한다",
    "복용 후 두드러기가 올라왔다고 보고했다",
    "후속 측정값을 제출하지 않아 경과를 확인할 수 없다",
    "목표 지표가 개선됐고 불편 호소는 없다",
    "다른 병원에서 새 처방약이 추가됐다",
    "복용 순응도가 절반에 못 미친다",
    "이전에 없던 알레르기 이력이 새로 확인됐다",
    "혈액검사 수치가 경계값에 걸쳐 있다",
    "본인이 성분을 바꾸고 싶다고 요청했다",
    "권장량을 넘겨 복용해 왔다고 뒤늦게 말했다",
    "복용 8주차인데 목표 지표가 오히려 나빠졌다",
)


def load_extract(root: Path) -> dict[str, Any]:
    path = Path(root) / EXTRACT_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"reference_extract_missing:{path}. "
            "먼저 scripts/build_health_checker_reference_extract.py 를 실행하세요."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _usable_cases(extract: dict[str, Any]) -> list[dict[str, Any]]:
    """Recommendation cases that map onto at least one catalog ingredient."""
    return [
        case
        for case in extract["recommendation_cases"]
        if case.get("mapped_ingredients")
    ]


def draft_kpi4_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """Counseling questions whose answers come from the published work.

    Every third case carries a medication context, which adds the obligations
    that context creates. That is what makes the answer set move: the same goal
    asked by someone on Levothyroxine is not the same answer.
    """
    extract = load_extract(root)
    cases = _usable_cases(extract)
    contexts = extract["medication_contexts"]
    if not cases:
        raise ValueError("no_usable_recommendation_cases")

    drafted: list[dict[str, Any]] = []
    for index in range(case_count):
        case = cases[index % len(cases)]
        context = contexts[(index // 3) % len(contexts)] if index % 3 == 0 else None

        answer = list(case["mapped_ingredients"])
        notes = [f"원문 권장 성분 ({case['source']['file']} p{case['source']['page']})"]

        if case["area_id"] in SPECIAL_POPULATION_AREAS:
            answer.append("advise_professional_consult")
            notes.append("특수집단 영역이라 전문가 상담 안내가 답변에 포함돼야 한다")

        if context is None:
            question = (
                f"「{case['area_title']}」에서 「{case['target']}」이 목표입니다. "
                "어떤 성분이 근거가 있나요?"
            )
        else:
            question = (
                f"{context['drug']} 복용 중입니다. 「{case['area_title']}」에서 "
                f"「{case['target']}」이 목표인데, 무엇을 어떻게 먹어야 하나요?"
            )
            for item in context["affected_ingredients"]:
                key = item["rnd_ingredient_key"]
                page = item["source"]["page"]
                if item["kind"] == "absorption_interaction":
                    answer.extend(["separate_dosing", key])
                    notes.append(f"{key}: 흡수 간섭이라 복용 간격 안내 필요 (p{page})")
                else:
                    answer.extend(["supplement_depleted_nutrient", key])
                    notes.append(f"{key}: {context['drug']} 고갈 성분 (p{page})")

        drafted.append(
            {
                "case_id": f"kpi4-{index + 1:03}",
                "prompt": question,
                "draft_answer": sorted(set(answer)),
                "draft_rationale": " · ".join(notes),
            }
        )
    return drafted


def draft_kpi3_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """Follow-up situations with the action deliberately left blank.

    The situation is built from the reference corpus and from ordinary practice
    signals. The answer is not supplied, because supplying it from anything in
    this repository is what invalidated the previous draft.
    """
    extract = load_extract(root)
    cases = _usable_cases(extract)
    contexts = extract["medication_contexts"]
    if not cases:
        raise ValueError("no_usable_recommendation_cases")

    drafted: list[dict[str, Any]] = []
    for index in range(case_count):
        case = cases[(index * 7) % len(cases)]
        signal = KPI3_SIGNALS[index % len(KPI3_SIGNALS)]
        context = contexts[(index // 4) % len(contexts)] if index % 4 == 0 else None

        taking = ", ".join(case["mapped_ingredients"])
        medication = f" / 복용약 {context['drug']}" if context else ""
        drafted.append(
            {
                "case_id": f"kpi3-{index + 1:03}",
                "prompt": (
                    f"목표 「{case['target']}」({case['area_title']}) / "
                    f"복용 중 {taking}{medication} / 관찰: {signal} "
                    "— 다음 수행 작업으로 무엇이 맞습니까?"
                ),
                "draft_answer": [KPI3_UNDECIDED],
                "draft_rationale": (
                    "이 지표의 정답은 저장소 안에 없다. 검토자가 다음 중 하나를 직접 입력한다: "
                    + ", ".join(NEXT_ACTION_VOCABULARY)
                    + f". (상황 출처: {case['source']['file']} p{case['source']['page']})"
                ),
            }
        )
    return drafted


DRAFTERS = {
    "KPI-3": draft_kpi3_cases,
    "KPI-4": draft_kpi4_cases,
}

DRAFT_SOURCES = {
    "KPI-3": DRAFT_SOURCE_KPI3,
    "KPI-4": DRAFT_SOURCE_KPI4,
}


def draft_cases(indicator_id: str, root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    if indicator_id not in DRAFTERS:
        raise KeyError(f"no_blinded_drafter_for_indicator:{indicator_id}")
    return DRAFTERS[indicator_id](root, case_count=case_count)
