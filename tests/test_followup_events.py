import json
from pathlib import Path

from wellnessbox_rnd.schemas.followup_events import (
    build_followup_transition_event_v1,
    summarize_followup_transition_event_contract_v1,
    validate_followup_transition_event_v1,
)

DATASET_PATH = Path("data/synthetic/synthetic_longitudinal_v4.jsonl")


def _load_payloads(limit: int) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for line in DATASET_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payloads.append(json.loads(line))
        if len(payloads) >= limit:
            break
    return payloads


def test_build_followup_transition_event_v1_preserves_core_fields() -> None:
    record = _load_payloads(limit=1)[0]

    event = build_followup_transition_event_v1(record)

    assert event.record_id == record["record_id"]
    assert event.user_id == record["user_id"]
    assert event.trajectory_step == record["trajectory_step"]
    assert event.next_action == record["labels"]["next_action"]
    assert event.reason_code == record["labels"]["reason_code"]
    assert event.closed_loop_state == record["labels"]["closed_loop_state"]


def test_validate_followup_transition_event_v1_flags_state_mismatch() -> None:
    record = _load_payloads(limit=1)[0]
    event = build_followup_transition_event_v1(record)
    event.closed_loop_state = "adjust_plan"

    issues = validate_followup_transition_event_v1(event)

    assert any(issue.startswith("closed_loop_state_mismatch::") for issue in issues)


def test_summarize_followup_transition_event_contract_v1_matches_v4_records() -> None:
    records = _load_payloads(limit=24)

    summary = summarize_followup_transition_event_contract_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )

    assert summary["case_count"] == len(records)
    assert summary["valid_case_count"] == len(records)
    assert summary["invalid_case_count"] == 0
    assert summary["connected_flows"]["follow_up_state_machine"] == [
        "trajectory_step",
        "day_index",
        "next_action",
        "closed_loop_state",
    ]
