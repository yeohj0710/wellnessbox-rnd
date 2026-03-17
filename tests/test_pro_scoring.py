import pytest
from pydantic import ValidationError

import wellnessbox_rnd.metrics.pro_scoring as pro_scoring
from wellnessbox_rnd.metrics.pro_scoring import (
    PROImprovementSummaryV1,
    build_default_pro_domain_norms_v1,
    build_default_pro_form_schema_v1,
    coerce_baseline_followup_pro_event_v1,
    summarize_pro_form_contract_v1,
    summarize_pro_improvement_from_event_v1,
    summarize_pro_improvement_from_normalized_event_v1,
    transform_pro_response_to_zscores_v1,
    validate_pro_domain_norms_v1,
    validate_pro_form_response_v1,
    validate_pro_improvement_summary_from_event_v1,
    validate_pro_improvement_summary_from_normalized_event_v1,
)
from wellnessbox_rnd.schemas.pro_events import build_baseline_followup_pro_event_v1
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import generate_rich_synthetic_cohort_v4


def test_build_default_pro_form_schema_v1_covers_expected_domains() -> None:
    schema = build_default_pro_form_schema_v1()

    assert schema.schema_version == "pro_form_schema_v1"
    assert schema.timepoints == ("baseline", "follow_up")
    assert [domain.domain_key.value for domain in schema.domains] == [
        "stress_support",
        "sleep_support",
        "immunity_support",
        "energy_support",
        "gut_health",
        "bone_joint",
        "heart_health",
        "blood_glucose",
        "general_wellness",
    ]
    assert all(len(domain.items) == 4 for domain in schema.domains)


def test_validate_pro_form_response_v1_flags_missing_and_unknown_keys() -> None:
    schema = build_default_pro_form_schema_v1()
    response = {
        "timepoint": "baseline",
        "domain_item_scores": {
            "stress_support": {
                "perceived_stress_load": 2,
                "tension_burden": 3,
                "calm_recovery_delay": 1,
                "stress_resilience_drop": 2,
                "unexpected_item": 4,
            },
            "unknown_domain": {"noise": 1},
        },
    }

    issues = validate_pro_form_response_v1(schema=schema, response=response)

    assert "unknown_domain::unknown_domain" in issues
    assert "unknown_item::stress_support::unexpected_item" in issues
    assert "missing_domain::sleep_support" in issues


def test_summarize_pro_form_contract_v1_matches_rich_synthetic_domain_coverage() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=602, user_count=24)

    summary = summarize_pro_form_contract_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )

    assert summary["case_count"] == len(records)
    assert summary["domain_count"] == 9
    assert (
        summary["synthetic_alignment"]["all_schema_domains_present_baseline_case_count"]
        == len(records)
    )
    assert (
        summary["synthetic_alignment"]["all_schema_domains_present_follow_up_case_count"]
        == len(records)
    )
    assert summary["synthetic_alignment"]["baseline_domain_coverage_pct"]["blood_glucose"] == 100.0
    assert summary["zscore_transform"]["transform_version"] == "pro_zscore_transform_v1"
    assert (
        summary["zscore_transform"]["sample_transforms"]["mid_problem_score_zero_z"][
            "aggregate_z"
        ]
        == 0.0
    )
    assert summary["improvement_metric"]["shared_event_schema_version"] == (
        "baseline_followup_pro_event_v1"
    )
    assert summary["improvement_metric"]["shared_event_adapter"] == (
        "summarize_pro_improvement_from_event_v1"
    )
    assert summary["improvement_metric"]["direct_normalized_event_adapter"] == (
        "summarize_pro_improvement_from_normalized_event_v1"
    )
    assert summary["improvement_metric"]["shared_event_unifier"] == (
        "coerce_baseline_followup_pro_event_v1"
    )
    assert summary["improvement_metric"]["direct_normalized_event_validator"] == (
        "validate_pro_improvement_summary_from_normalized_event_v1"
    )
    assert summary["improvement_metric"]["single_path_status"] == {
        "event_adapter_only_public_entrypoint": True,
        "normalized_event_direct_compute_path": True,
        "direct_normalized_event_internal_only": True,
        "package_public_summary_entrypoint": "summarize_pro_improvement_from_event_v1",
        "package_public_validator_entrypoint": (
            "validate_pro_improvement_summary_from_event_v1"
        ),
        "snapshot_pair_entrypoint_internal_only": True,
        "record_or_event_payloads_unified_by": "coerce_baseline_followup_pro_event_v1",
    }
    assert summary["improvement_metric"]["shared_event_path_proof"]["valid_case_count"] == len(
        records
    )
    assert summary["improvement_metric"]["shared_event_path_proof"]["invalid_case_count"] == 0


def test_transform_pro_response_to_zscores_v1_uses_default_problem_norms() -> None:
    schema = build_default_pro_form_schema_v1()
    response = {
        "timepoint": "follow_up",
        "domain_item_scores": {
            domain.domain_key.value: {
                item.item_key: (1 if domain.domain_key.value == "sleep_support" else 2)
                for item in domain.items
            }
            for domain in schema.domains
        },
    }

    transformed = transform_pro_response_to_zscores_v1(response, schema=schema)

    assert transformed.transform_version == "pro_zscore_transform_v1"
    assert transformed.norm_version == "pro_zscore_norm_v1"
    assert transformed.domain_problem_scores["sleep_support"] == 1.0
    assert transformed.domain_z["sleep_support"] == 1.0
    assert transformed.domain_z["stress_support"] == 0.0
    assert transformed.aggregate_z == round(1.0 / 9.0, 6)


def test_validate_pro_domain_norms_v1_flags_missing_unknown_and_bad_std() -> None:
    schema = build_default_pro_form_schema_v1()
    norms = build_default_pro_domain_norms_v1(schema)
    norms.pop("general_wellness")
    norms["unexpected_domain"] = {
        "domain_key": "stress_support",
        "problem_score_mean": 2.0,
        "problem_score_std": 1.0,
        "score_orientation": "lower_is_better_for_problem_score",
    }
    norms["sleep_support"] = {
        "domain_key": "sleep_support",
        "problem_score_mean": 2.0,
        "problem_score_std": 0.0,
        "score_orientation": "lower_is_better_for_problem_score",
    }

    issues = validate_pro_domain_norms_v1(norms=norms, schema=schema)

    assert "missing_norm::general_wellness" in issues
    assert "unknown_norm::unexpected_domain" in issues
    assert any(issue.startswith("invalid_norm_std::sleep_support::") for issue in issues)


def test_summarize_pro_improvement_from_event_v1_computes_deltas_and_status() -> None:
    schema = build_default_pro_form_schema_v1()
    baseline = transform_pro_response_to_zscores_v1(
        {
            "timepoint": "baseline",
            "domain_item_scores": {
                domain.domain_key.value: {item.item_key: 2 for item in domain.items}
                for domain in schema.domains
            },
        },
        schema=schema,
    )
    follow_up = transform_pro_response_to_zscores_v1(
        {
            "timepoint": "follow_up",
            "domain_item_scores": {
                domain.domain_key.value: {
                    item.item_key: (1 if domain.domain_key.value == "sleep_support" else 2)
                    for item in domain.items
                }
                for domain in schema.domains
            },
        },
        schema=schema,
    )
    event = {
        "record_id": "test-pro-event",
        "user_id": "test-user",
        "cohort_version": "test",
        "trajectory_step": 0,
        "day_index": 0,
        "recommendation_goals": ["sleep_support"],
        "follow_up_next_action": "continue_plan",
        "adverse_event": False,
        "baseline": baseline.model_dump(mode="json"),
        "follow_up": follow_up.model_dump(mode="json"),
        "delta_z_by_domain": {
            domain_key: round(
                follow_up.domain_z[domain_key] - baseline.domain_z[domain_key],
                6,
            )
            for domain_key in baseline.domain_z
        },
    }

    summary = summarize_pro_improvement_from_event_v1(event)

    assert summary.summary_version == "pro_improvement_summary_v1"
    assert summary.aggregate_delta_z == round(1.0 / 9.0, 6)
    assert summary.domain_delta_z["sleep_support"] == 1.0
    assert summary.improved_domain_count == 1
    assert summary.worsened_domain_count == 0
    assert summary.unchanged_domain_count == 8
    assert summary.net_status == "net_improvement"


def test_coerce_baseline_followup_pro_event_v1_unifies_record_and_event_payloads() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=608, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record)

    from_record = coerce_baseline_followup_pro_event_v1(record)
    from_event = coerce_baseline_followup_pro_event_v1(event.model_dump(mode="json"))

    assert from_record.model_dump(mode="json") == event.model_dump(mode="json")
    assert from_event.model_dump(mode="json") == event.model_dump(mode="json")


def test_summarize_pro_improvement_from_event_v1_uses_shared_event_path() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=603, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record)

    summary = summarize_pro_improvement_from_event_v1(event)

    assert summary.summary_version == "pro_improvement_summary_v1"
    assert summary.domain_delta_z == event.delta_z_by_domain
    assert summary.aggregate_delta_z == round(
        event.follow_up.aggregate_z - event.baseline.aggregate_z,
        6,
    )


def test_pro_improvement_summary_shared_contract_happy_path_is_consistent() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=612, user_count=1)[0]
    normalized_event = build_baseline_followup_pro_event_v1(record).model_dump(mode="json")

    from_record = summarize_pro_improvement_from_event_v1(record)
    from_event = summarize_pro_improvement_from_event_v1(normalized_event)
    from_direct_contract = summarize_pro_improvement_from_normalized_event_v1(normalized_event)

    assert from_record.model_dump(mode="json") == from_event.model_dump(mode="json")
    assert from_event.model_dump(mode="json") == from_direct_contract.model_dump(mode="json")
    assert (
        validate_pro_improvement_summary_from_event_v1(
            event=record,
            summary=from_direct_contract,
        )
        == []
    )
    assert (
        validate_pro_improvement_summary_from_normalized_event_v1(
            event=normalized_event,
            summary=from_record,
        )
        == []
    )


def test_summarize_pro_improvement_from_normalized_event_v1_requires_normalized_event() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=609, user_count=1)[0]

    with pytest.raises(ValidationError):
        summarize_pro_improvement_from_normalized_event_v1(record.model_dump(mode="json"))


def test_summarize_pro_improvement_from_event_v1_routes_through_direct_normalized_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = generate_rich_synthetic_cohort_v4(seed=610, user_count=1)[0]
    adapter_calls: list[str] = []

    def fake_direct_adapter(payload: object) -> PROImprovementSummaryV1:
        payload_dict = payload if isinstance(payload, dict) else payload.model_dump(mode="json")
        assert "baseline" in payload_dict
        assert "follow_up" in payload_dict
        assert "baseline_pro" not in payload_dict
        assert "follow_up_pro" not in payload_dict
        adapter_calls.append(payload_dict["record_id"])
        return PROImprovementSummaryV1(
            baseline_timepoint="baseline",
            follow_up_timepoint="follow_up",
            aggregate_delta_z=0.5,
            domain_delta_z=dict(payload_dict["delta_z_by_domain"]),
            improved_domain_count=1,
            worsened_domain_count=0,
            unchanged_domain_count=8,
            net_status="net_improvement",
        )

    monkeypatch.setattr(
        pro_scoring,
        "summarize_pro_improvement_from_normalized_event_v1",
        fake_direct_adapter,
    )

    summary = summarize_pro_improvement_from_event_v1(record)

    assert adapter_calls == [record.record_id]
    assert summary.aggregate_delta_z == 0.5


@pytest.mark.parametrize(
    ("mutate_payload", "expected_exception", "expected_match"),
    [
        (
            lambda payload: payload.pop("follow_up"),
            ValidationError,
            "follow_up",
        ),
        (
            lambda payload: payload["delta_z_by_domain"].__setitem__(
                "sleep_support",
                round(payload["delta_z_by_domain"]["sleep_support"] + 1.0, 6),
            ),
            ValueError,
            "invalid_baseline_followup_pro_event::",
        ),
    ],
)
def test_summarize_pro_improvement_from_normalized_event_v1_rejects_missing_or_drifted_contract(
    mutate_payload: object,
    expected_exception: type[Exception],
    expected_match: str,
) -> None:
    record = generate_rich_synthetic_cohort_v4(seed=613, user_count=1)[0]
    normalized_event = build_baseline_followup_pro_event_v1(record).model_dump(mode="json")

    mutate_payload(normalized_event)

    with pytest.raises(expected_exception, match=expected_match):
        summarize_pro_improvement_from_normalized_event_v1(normalized_event)


def test_summarize_pro_improvement_from_event_v1_rejects_missing_follow_up_field() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=605, user_count=1)[0]
    event_payload = build_baseline_followup_pro_event_v1(record).model_dump(mode="json")
    event_payload.pop("follow_up")

    with pytest.raises(Exception) as exc_info:
        summarize_pro_improvement_from_event_v1(event_payload)

    assert "follow_up" in str(exc_info.value)


def test_summarize_pro_improvement_from_event_v1_rejects_contract_drift() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=606, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record).model_copy(
        update={
            "delta_z_by_domain": {
                **record.delta_z_by_domain,
                "sleep_support": round(record.delta_z_by_domain["sleep_support"] + 1.0, 6),
            }
        }
    )

    with pytest.raises(ValueError, match="invalid_baseline_followup_pro_event::"):
        summarize_pro_improvement_from_event_v1(event)


def test_summarize_pro_form_contract_v1_uses_shared_event_adapter_without_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = generate_rich_synthetic_cohort_v4(seed=607, user_count=3)[:3]
    domain_keys = [domain.domain_key.value for domain in build_default_pro_form_schema_v1().domains]
    adapter_calls: list[str] = []

    def _summary(
        *,
        aggregate_delta_z: float,
        sleep_delta: float,
        net_status: str,
        improved_count: int,
        worsened_count: int,
        unchanged_count: int,
    ) -> PROImprovementSummaryV1:
        domain_delta_z = {domain_key: 0.0 for domain_key in domain_keys}
        domain_delta_z["sleep_support"] = sleep_delta
        return PROImprovementSummaryV1(
            baseline_timepoint="baseline",
            follow_up_timepoint="follow_up",
            aggregate_delta_z=aggregate_delta_z,
            domain_delta_z=domain_delta_z,
            improved_domain_count=improved_count,
            worsened_domain_count=worsened_count,
            unchanged_domain_count=unchanged_count,
            net_status=net_status,
        )

    def fake_adapter(payload: object) -> PROImprovementSummaryV1:
        if isinstance(payload, dict):
            record_id = payload["record_id"]
        else:
            record_id = payload.record_id
        adapter_calls.append(record_id)
        if record_id == "sample_pro_improvement_event":
            return _summary(
                aggregate_delta_z=0.111111,
                sleep_delta=1.0,
                net_status="net_improvement",
                improved_count=1,
                worsened_count=0,
                unchanged_count=8,
            )
        if record_id == records[0].record_id:
            return _summary(
                aggregate_delta_z=0.5,
                sleep_delta=0.5,
                net_status="net_improvement",
                improved_count=1,
                worsened_count=0,
                unchanged_count=8,
            )
        if record_id == records[1].record_id:
            return _summary(
                aggregate_delta_z=-0.25,
                sleep_delta=-0.25,
                net_status="net_worsening",
                improved_count=0,
                worsened_count=1,
                unchanged_count=8,
            )
        return _summary(
            aggregate_delta_z=0.0,
            sleep_delta=0.0,
            net_status="no_material_change",
            improved_count=0,
            worsened_count=0,
            unchanged_count=9,
        )

    def fail_internal_summary(*, baseline_snapshot: object, follow_up_snapshot: object) -> object:
        raise AssertionError(
            "internal snapshot summary bypassed shared event adapter path"
        )

    monkeypatch.setattr(pro_scoring, "summarize_pro_improvement_from_event_v1", fake_adapter)
    monkeypatch.setattr(
        pro_scoring,
        "_summarize_pro_improvement_from_snapshots_v1",
        fail_internal_summary,
    )

    summary = summarize_pro_form_contract_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )

    assert adapter_calls == [
        "sample_pro_improvement_event",
        *(record.record_id for record in records),
    ]
    assert summary["improvement_metric"]["sample_summary"]["aggregate_delta_z"] == 0.111111
    assert summary["improvement_metric"]["synthetic_dataset_summary"]["improved_case_count"] == 1
    assert summary["improvement_metric"]["synthetic_dataset_summary"]["worsened_case_count"] == 1
    assert summary["improvement_metric"]["synthetic_dataset_summary"]["unchanged_case_count"] == 1
    assert summary["improvement_metric"]["synthetic_dataset_summary"]["mean_aggregate_delta_z"] == (
        0.083333
    )


def test_metrics_module_package_boundary_keeps_single_public_pro_entry_path() -> None:
    import wellnessbox_rnd.metrics as metrics_module

    assert "summarize_pro_improvement_v1" not in metrics_module.__all__
    assert "summarize_pro_improvement_from_normalized_event_v1" not in metrics_module.__all__
    assert (
        "validate_pro_improvement_summary_from_normalized_event_v1"
        not in metrics_module.__all__
    )
    with pytest.raises(AttributeError):
        _ = metrics_module.summarize_pro_improvement_v1
    with pytest.raises(AttributeError):
        _ = metrics_module.summarize_pro_improvement_from_normalized_event_v1
    with pytest.raises(AttributeError):
        _ = metrics_module.validate_pro_improvement_summary_from_normalized_event_v1

    assert metrics_module.summarize_pro_improvement_from_event_v1 is not None
    assert metrics_module.validate_pro_improvement_summary_from_event_v1 is not None


def test_validate_pro_improvement_summary_from_event_v1_flags_summary_mismatch() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=604, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record)
    summary = summarize_pro_improvement_from_event_v1(event).model_copy(
        update={"aggregate_delta_z": 999.0}
    )

    issues = validate_pro_improvement_summary_from_event_v1(
        event=event,
        summary=summary,
    )

    assert any(issue.startswith("aggregate_delta_mismatch::") for issue in issues)


def test_validate_pro_improvement_summary_from_event_v1_uses_direct_contract_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = generate_rich_synthetic_cohort_v4(seed=614, user_count=1)[0]
    normalized_event = build_baseline_followup_pro_event_v1(record)
    seen_payloads: list[dict[str, object]] = []

    def fake_direct_validator(
        *,
        event: object,
        summary: object,
    ) -> list[str]:
        payload_dict = event if isinstance(event, dict) else event.model_dump(mode="json")
        assert "baseline" in payload_dict
        assert "follow_up" in payload_dict
        assert "baseline_pro" not in payload_dict
        assert "follow_up_pro" not in payload_dict
        seen_payloads.append(payload_dict)
        return ["direct_validator_only"]

    monkeypatch.setattr(
        pro_scoring,
        "validate_pro_improvement_summary_from_normalized_event_v1",
        fake_direct_validator,
    )

    issues = validate_pro_improvement_summary_from_event_v1(
        event=record,
        summary=PROImprovementSummaryV1(
            baseline_timepoint="baseline",
            follow_up_timepoint="follow_up",
            aggregate_delta_z=0.0,
            domain_delta_z={},
            improved_domain_count=0,
            worsened_domain_count=0,
            unchanged_domain_count=0,
            net_status="no_material_change",
        ),
    )

    assert issues == ["direct_validator_only"]
    assert [payload["record_id"] for payload in seen_payloads] == [normalized_event.record_id]


def test_validate_pro_improvement_summary_from_normalized_event_v1_flags_summary_mismatch() -> None:
    record = generate_rich_synthetic_cohort_v4(seed=611, user_count=1)[0]
    event = build_baseline_followup_pro_event_v1(record)
    summary = summarize_pro_improvement_from_normalized_event_v1(
        event.model_dump(mode="json")
    ).model_copy(update={"aggregate_delta_z": -999.0})

    issues = validate_pro_improvement_summary_from_normalized_event_v1(
        event=event.model_dump(mode="json"),
        summary=summary,
    )

    assert any(issue.startswith("aggregate_delta_mismatch::") for issue in issues)
