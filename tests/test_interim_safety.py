from datetime import date

from wellnessbox_rnd.interim.safety import evaluate_safety


def test_emergency_and_hard_blocks_are_not_overridden() -> None:
    result = evaluate_safety(
        {
            "symptoms": ["chest pain"],
            "pregnant": True,
            "ingredients": ["omega3"],
            "medications": ["warfarin"],
        }
    )
    assert result.action == "STOP_AND_ESCALATE"
    assert result.hard_failure is True


def test_pregnancy_and_lactation_have_separate_replay_rule_ids() -> None:
    pregnancy = evaluate_safety({"pregnant": True})
    lactation = evaluate_safety({"lactating": True})

    assert {finding.rule_id for finding in pregnancy.findings} == {"SAFE-PREG-001"}
    assert {finding.rule_id for finding in lactation.findings} == {"SAFE-LACT-001"}


def test_condition_replay_separates_renal_hepatic_and_hemochromatosis_rules() -> None:
    result = evaluate_safety(
        {
            "conditions": ["kidney failure", "cirrhosis", "hemochromatosis"],
            "ingredients": ["iron"],
        }
    )

    assert {finding.rule_id for finding in result.findings} == {
        "SAFE-RENAL-001",
        "SAFE-HEPATIC-001",
        "SAFE-HEMO-001",
    }
    assert result.action == "BLOCK"

    renal_review = evaluate_safety({"conditions": ["chronic kidney disease"]})
    assert renal_review.action == "WARN"
    assert {finding.rule_id for finding in renal_review.findings} == {
        "SAFE-RENAL-REVIEW-001"
    }


def test_drug_interaction_replay_finding_keeps_reference_and_claim_ids() -> None:
    result = evaluate_safety(
        {"medications": ["warfarin"], "ingredients": ["omega3"]}
    )
    finding = next(item for item in result.findings if item.rule_id == "SAFE-DDI-001")

    assert finding.reference_ids == ("REF-NIH-ODS-OMEGA3-001",)
    assert finding.claim_ids == ("CLM-NIH-ODS-OMEGA3-WARFARIN-001",)


def test_drug_interaction_replay_accepts_coumadin_alias() -> None:
    result = evaluate_safety(
        {"medications": ["Coumadin"], "ingredients": ["omega3"]}
    )
    finding = next(item for item in result.findings if item.rule_id == "SAFE-DDI-001")

    assert finding.reference_ids == ("REF-NIH-ODS-OMEGA3-001",)
    assert finding.claim_ids == ("CLM-NIH-ODS-OMEGA3-WARFARIN-001",)


def test_drug_interaction_replay_does_not_reuse_evidence_for_other_pairs() -> None:
    result = evaluate_safety(
        {"medications": ["apixaban"], "ingredients": ["ginkgo"]}
    )

    assert all(finding.rule_id != "SAFE-DDI-001" for finding in result.findings)
    assert all(
        "CLM-NIH-ODS-OMEGA3-WARFARIN-001" not in finding.claim_ids
        for finding in result.findings
    )


def test_all_fourteen_safety_categories_are_exercised() -> None:
    result = evaluate_safety(
        {
            "symptoms": ["severe bleeding"],
            "pregnant": True,
            "age": 10,
            "conditions": ["kidney failure", "hemochromatosis"],
            "allergies": ["iron"],
            "ingredients": ["iron", "omega3"],
            "surgery_within_days": 4,
            "medications": ["warfarin"],
            "duplicate_ingredients": ["iron"],
            "above_ul": True,
            "requires_test": True,
            "test_available": False,
            "timing_conflict": True,
            "label_constraint_violation": True,
            "evidence_valid_until": "2025-01-01",
        },
        as_of=date(2026, 1, 1),
    )
    categories = {item.category for item in result.findings}
    assert len(categories) == 14


def test_temporal_replay_changes_only_when_source_expires() -> None:
    payload = {"evidence_valid_until": "2026-06-30"}
    assert evaluate_safety(payload, as_of=date(2026, 6, 30)).action == "PASS"
    assert evaluate_safety(payload, as_of=date(2026, 7, 1)).action == "BLOCK"


def test_300_scenario_replay_is_deterministic() -> None:
    scenarios = [{"age": 30 + index % 20, "above_ul": index % 17 == 0} for index in range(360)]
    first = [evaluate_safety(item) for item in scenarios]
    second = [evaluate_safety(item) for item in scenarios]
    assert first == second
    assert sum(item.hard_failure for item in first) == 22
