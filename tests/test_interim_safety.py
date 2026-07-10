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
