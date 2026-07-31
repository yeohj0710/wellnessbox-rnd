"""Draft KPI answer keys from a published work the engine has never read.

`answer_key_drafters` derives its drafts from files inside this repository. That
is enough for KPI-3 and KPI-4, where the answer is a policy decision the project
itself defines. It is weaker for KPI-1 and KPI-5, where the answer is supposed to
be what a pharmacist would independently conclude:

  KPI-1  the priors-based draft answers from `goal_ingredient_priors_v1`, the
         same evidence layer the recommender scores on, and the answer does not
         change when the case says the patient takes warfarin or is pregnant.
  KPI-5  the safety draft answers with the registered value from
         `data/rules/safety_rules.json`, which is the engine's own rule file, so
         the engine reproduces it by construction.

This module drafts from `health_checker_reference_extract_v1` instead — a
structured extract of `건강상담 Checker`, a pharmacist counseling work the project
owner authored and published before this engine existed. Its evidence layer does
not intersect the engine's knowledge base, every item carries a page citation,
and the drug tables make the answer move with the case: a patient on Furosemide
gets the minerals that loop diuretics deplete, and one on Levothyroxine gets the
work's own four-hour separation note rather than a silent exclusion.

The drafts remain drafts. A named human still accepts, edits or rejects each one
through `run_answer_key_workbench.py`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXTRACT_PATH = "data/knowledge/external/health_checker_reference_extract_v1.json"
DRAFT_SOURCE = "health_checker_reference_extract_v1"

# Ages are fixed per position so a regenerated draft set is byte-identical.
AGE_BANDS: tuple[int, ...] = (28, 34, 41, 47, 53, 58, 64, 69, 72, 76)

# Crossing states with drugs mechanically can pair a paediatric or pregnancy
# state with an adult medication. Those pairs are left in — deciding them is the
# reviewer's job, not this module's — but they are marked so the reviewer sees
# which ones to look at rather than having to notice on their own.
SPECIAL_POPULATION_AREAS: frozenset[str] = frozenset({"38-pregnancy-lactation", "43-children"})


def load_extract(root: Path) -> dict[str, Any]:
    path = Path(root) / EXTRACT_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"reference_extract_missing:{path}. "
            "먼저 scripts/build_health_checker_reference_extract.py 를 실행하세요."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _context_answer(
    base: list[str], context: dict[str, Any] | None
) -> tuple[list[str], list[str]]:
    """Fold a medication context into the answer and say why it changed."""
    if context is None:
        return sorted(set(base)), []

    added: list[str] = []
    notes: list[str] = []
    for item in context["affected_ingredients"]:
        key = item["rnd_ingredient_key"]
        if key not in base:
            added.append(key)
        if item["kind"] == "absorption_interaction":
            notes.append(f"{key}: 흡수 간섭 — {item['counseling']} (p{item['source']['page']})")
        else:
            notes.append(f"{key}: 고갈 보충 — {item['counseling']} (p{item['source']['page']})")

    return sorted(set(base) | set(added)), notes


def draft_kpi1_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """Cross the work's judged states with its own drug tables.

    The answer for a case is the ingredient set the work recommends for that
    judged state, plus what the stated medication depletes. Two cases with the
    same state and different medications therefore have different answers, which
    is the property the priors-based draft lacks.
    """
    extract = load_extract(root)
    cases = extract["recommendation_cases"]
    contexts = extract["medication_contexts"]
    if not cases:
        raise ValueError("no_recommendation_cases_in_extract")

    # A `None` context keeps plain cases in the mix alongside the medication ones.
    context_cycle: list[dict[str, Any] | None] = [None, *contexts]
    drafted: list[dict[str, Any]] = []
    index = 0

    while len(drafted) < case_count and index < case_count * 8:
        # Both cycles advance every step. Their lengths are coprime here, so 100
        # draws give 100 distinct state-medication pairs instead of repeating the
        # first context for the whole set.
        case = cases[index % len(cases)]
        context = context_cycle[index % len(context_cycle)]
        answer, notes = _context_answer(case["mapped_ingredients"], context)
        if not answer:
            index += 1
            continue

        medication = context["drug"] if context else "없음"
        age = AGE_BANDS[index % len(AGE_BANDS)]
        rationale = [
            f"{case['area_title']} · 원문 판정 「{case['target']}」의 권장 성분 "
            f"({case['source']['file']} p{case['source']['page']})",
        ]
        rationale.extend(notes)
        if context is not None and case["area_id"] in SPECIAL_POPULATION_AREAS:
            rationale.append(
                f"검토자 확인 필요: 소아·임신 영역과 성인 약물({context['drug']}) 조합"
            )
        if case["out_of_catalog_nutrients"]:
            rationale.append(
                "카탈로그에 없어 채점에서 제외한 원문 성분: "
                + ", ".join(case["out_of_catalog_nutrients"])
            )

        drafted.append(
            {
                "case_id": f"kpi1-ref-{len(drafted) + 1:03}",
                "prompt": (
                    f"영역 {case['area_title']} / 판정 「{case['target']}」 / "
                    f"나이 {age} / 복용약 {medication}"
                ),
                "draft_answer": answer,
                "draft_rationale": " · ".join(rationale),
            }
        )
        index += 1

    return drafted


def draft_kpi5_cases(root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    """One rule per case: which ingredient does this drug affect, and how.

    The reference value comes from the work's drug tables, not from
    `safety_rules.json`, so the engine cannot satisfy the case by echoing its own
    registered value back.
    """
    extract = load_extract(root)
    contexts = extract["medication_contexts"]
    if not contexts:
        raise ValueError("no_medication_contexts_in_extract")

    rules: list[dict[str, Any]] = []
    for context in contexts:
        for item in context["affected_ingredients"]:
            rules.append({"drug": context["drug"], **item})
    if not rules:
        raise ValueError("no_medication_rules_in_extract")

    drafted: list[dict[str, Any]] = []
    index = 0
    while len(drafted) < case_count and index < case_count * 4:
        rule = rules[index % len(rules)]
        # Alternate the asked field so the set covers label and evidence, which is
        # what KPI-5 scores: `1(l_r = l_ref ∧ f_r = f_ref)`.
        ask_label = (index // len(rules)) % 2 == 0
        if ask_label:
            prompt = f"{rule['drug']} 복용자에게 {rule['rnd_ingredient_key']} 는 어떤 관계인가?"
            answer = [rule["kind"], rule["rnd_ingredient_key"]]
        else:
            prompt = f"{rule['drug']} 와 {rule['rnd_ingredient_key']} 관계의 근거 쪽수는?"
            answer = [f"p{rule['source']['page']}", rule["book_nutrient"]]

        drafted.append(
            {
                "case_id": f"kpi5-ref-{len(drafted) + 1:03}",
                "prompt": prompt,
                "draft_answer": answer,
                "draft_rationale": (
                    f"{rule['counseling']} "
                    f"({rule['source']['file']} p{rule['source']['page']})"
                ),
            }
        )
        index += 1

    return drafted


DRAFTERS = {"KPI-1": draft_kpi1_cases, "KPI-5": draft_kpi5_cases}


def draft_cases(indicator_id: str, root: Path, *, case_count: int = 100) -> list[dict[str, Any]]:
    if indicator_id not in DRAFTERS:
        raise KeyError(
            f"no_reference_corpus_drafter_for_indicator:{indicator_id}. "
            "이 출처는 KPI-1과 KPI-5만 만든다."
        )
    return DRAFTERS[indicator_id](root, case_count=case_count)
