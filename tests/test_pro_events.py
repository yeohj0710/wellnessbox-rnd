import json
from pathlib import Path

from wellnessbox_rnd.schemas.pro_events import (
    build_baseline_followup_pro_event_v1,
    summarize_baseline_followup_pro_event_contract_v1,
    validate_baseline_followup_pro_event_v1,
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


def test_build_baseline_followup_pro_event_v1_preserves_core_fields() -> None:
    record = _load_payloads(limit=1)[0]

    event = build_baseline_followup_pro_event_v1(record)

    assert event.record_id == record["record_id"]
    assert event.user_id == record["user_id"]
    assert event.trajectory_step == record["trajectory_step"]
    assert event.baseline.timepoint == "baseline"
    assert event.follow_up.timepoint == "follow_up"
    assert event.baseline.aggregate_percentile is not None
    assert event.follow_up.aggregate_percentile is not None
    assert set(event.baseline.domain_percentile) == set(event.baseline.domain_z)
    assert set(event.follow_up.domain_percentile) == set(event.follow_up.domain_z)
    assert event.follow_up_next_action == record["labels"]["next_action"]
    assert set(event.delta_z_by_domain) == set(record["delta_z_by_domain"])


def test_validate_baseline_followup_pro_event_v1_flags_delta_mismatch() -> None:
    record = _load_payloads(limit=1)[0]
    event = build_baseline_followup_pro_event_v1(record)
    first_domain = next(iter(event.delta_z_by_domain))
    event.delta_z_by_domain[first_domain] += 0.5

    issues = validate_baseline_followup_pro_event_v1(event)

    assert any(issue.startswith(f"delta_mismatch::{first_domain}::") for issue in issues)


def test_summarize_baseline_followup_pro_event_contract_v1_matches_v4_records() -> None:
    records = _load_payloads(limit=24)

    summary = summarize_baseline_followup_pro_event_contract_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )

    assert summary["case_count"] == len(records)
    assert summary["valid_case_count"] == len(records)
    assert summary["invalid_case_count"] == 0
    assert summary["domain_count"] == 9
    assert summary["connected_flows"]["pro_scoring"] == [
        "baseline.aggregate_z",
        "baseline.aggregate_percentile",
        "follow_up.aggregate_z",
        "follow_up.aggregate_percentile",
        "delta_z_by_domain",
    ]
