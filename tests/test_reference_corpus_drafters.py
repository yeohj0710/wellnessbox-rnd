"""The reference-corpus drafts must stay independent and context-sensitive.

Two properties carry the measurement. The draft must not come from a file the
engine also reads, or KPI-1 and KPI-5 score the engine against itself. And the
answer must move when the case's medication moves, or the answer key silently
penalises an engine that adjusts for the medication.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wellnessbox_rnd.evals.answer_key_workbench import assert_source_is_independent
from wellnessbox_rnd.evals.reference_corpus_drafters import (
    DRAFT_SOURCE,
    draft_cases,
    draft_kpi1_cases,
    draft_kpi5_cases,
    load_extract,
)

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "data/knowledge/external/health_checker_reference_extract_v1.json"

pytestmark = pytest.mark.skipif(
    not EXTRACT.is_file(),
    reason="reference extract not built; run scripts/build_health_checker_reference_extract.py",
)


def test_extract_declares_independence_from_the_engine() -> None:
    extract = load_extract(ROOT)
    assert extract["independence"]["shared_evidence_with_engine"] is False
    assert extract["source"]["artifact_sha256"]
    assert extract["content_sha256"]


def test_draft_source_is_not_the_system_under_test() -> None:
    assert_source_is_independent(DRAFT_SOURCE)


def test_draft_source_is_not_the_engine_safety_rule_file() -> None:
    """KPI-5 must not answer with a value read out of the engine's own rules."""
    engine_rules = json.loads((ROOT / "data/rules/safety_rules.json").read_text(encoding="utf-8"))
    registered_ids = {
        rule.get("metadata", {}).get("rule_id")
        for group in engine_rules.values()
        if isinstance(group, list)
        for rule in group
        if isinstance(rule, dict)
    }
    answers = {item for case in draft_kpi5_cases(ROOT) for item in case["draft_answer"]}
    assert not (answers & registered_ids)


def test_kpi1_reaches_the_minimum_sample() -> None:
    cases = draft_kpi1_cases(ROOT, case_count=100)
    assert len(cases) == 100
    assert len({case["case_id"] for case in cases}) == 100
    assert all(case["draft_answer"] for case in cases)


def test_kpi1_answers_vary_far_more_than_the_priors_draft() -> None:
    """The priors draft produced 7 distinct answers across 100 cases."""
    cases = draft_kpi1_cases(ROOT, case_count=100)
    distinct = {tuple(sorted(case["draft_answer"])) for case in cases}
    assert len(distinct) > 40


def test_kpi1_medication_context_changes_the_answer() -> None:
    extract = load_extract(ROOT)
    base_by_target = {
        case["target"]: set(case["mapped_ingredients"])
        for case in extract["recommendation_cases"]
    }
    cases = draft_kpi1_cases(ROOT, case_count=100)

    changed = 0
    for case in cases:
        if "복용약 없음" in case["prompt"]:
            continue
        target = case["prompt"].split("판정 「")[1].split("」")[0]
        if set(case["draft_answer"]) - base_by_target.get(target, set()):
            changed += 1
    assert changed > 0


def test_kpi1_cases_without_medication_match_the_source_recommendation() -> None:
    extract = load_extract(ROOT)
    base_by_target = {
        case["target"]: sorted(case["mapped_ingredients"])
        for case in extract["recommendation_cases"]
    }
    for case in draft_kpi1_cases(ROOT, case_count=100):
        if "복용약 없음" not in case["prompt"]:
            continue
        target = case["prompt"].split("판정 「")[1].split("」")[0]
        assert case["draft_answer"] == base_by_target[target]


def test_every_case_cites_a_page() -> None:
    for case in draft_kpi1_cases(ROOT, case_count=100):
        assert " p" in case["draft_rationale"]
    for case in draft_kpi5_cases(ROOT, case_count=100):
        assert " p" in case["draft_rationale"]


def test_special_population_pairs_are_flagged_for_the_reviewer() -> None:
    flagged = [
        case
        for case in draft_kpi1_cases(ROOT, case_count=100)
        if "검토자 확인 필요" in case["draft_rationale"]
    ]
    for case in flagged:
        assert "복용약 없음" not in case["prompt"]


def test_kpi5_reaches_the_minimum_sample() -> None:
    cases = draft_kpi5_cases(ROOT, case_count=100)
    assert len(cases) == 100
    assert len({case["case_id"] for case in cases}) == 100


def test_draft_cases_rejects_an_unsupported_indicator() -> None:
    with pytest.raises(KeyError):
        draft_cases("KPI-2", ROOT)


def test_drafts_are_reproducible() -> None:
    assert draft_kpi1_cases(ROOT, case_count=40) == draft_kpi1_cases(ROOT, case_count=40)
    assert draft_kpi5_cases(ROOT, case_count=40) == draft_kpi5_cases(ROOT, case_count=40)
