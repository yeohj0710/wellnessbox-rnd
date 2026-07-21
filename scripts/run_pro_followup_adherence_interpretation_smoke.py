from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from wellnessbox_rnd.interim.data_lake import ExecutionLedger
from wellnessbox_rnd.interim.data_mutation import DataMutationLedger
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_followup import (
    PROFollowUpEffectInterpretationV1,
    PROFollowUpEventV1,
    interpret_pro_followup_effect_v1,
    load_pro_followup_interpretation_contract_v1,
)
from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineScoreObservationV1,
    build_pro_baseline_distribution_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "data/contracts/pro_followup_interpretation_v1.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op053_op054_pro_followup_interpretation_smoke_v1.json"
)
SOURCE_PATHS = [
    "data/contracts/pro_followup_interpretation_v1.json",
    "data/contracts/pro_instrument_scoring_v1.json",
    "scripts/run_pro_followup_adherence_interpretation_smoke.py",
    "src/wellnessbox_rnd/interim/contracts.py",
    "src/wellnessbox_rnd/interim/data_lake.py",
    "src/wellnessbox_rnd/interim/data_mutation.py",
    "src/wellnessbox_rnd/interim/store.py",
    "src/wellnessbox_rnd/metrics/__init__.py",
    "src/wellnessbox_rnd/metrics/calculators.py",
    "src/wellnessbox_rnd/metrics/pro_followup.py",
    "src/wellnessbox_rnd/metrics/pro_scoring.py",
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
]
SUBJECT_ID = "usr_1234567890abcdef1234567890abcdef"
SCHEDULED_DAYS = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": None,
}
ACTUAL_DAYS = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": 35,
}
OBSERVED_AT = {
    "pre_intake": "2026-01-01T00:00:00Z",
    "week_2": "2026-01-15T00:00:00Z",
    "week_4": "2026-01-29T00:00:00Z",
    "discontinuation": "2026-02-05T00:00:00Z",
}


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify local PRO follow-up persistence and bounded interpretation."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(SOURCE_PATHS):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(
            (PROJECT_ROOT / relative_path).read_bytes().replace(b"\r\n", b"\n")
        )
        digest.update(b"\0")
    return digest.hexdigest()


def _git_source_commit() -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *SOURCE_PATHS],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _contract_sha256() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _request(request_id: str) -> RecommendationRequest:
    return RecommendationRequest.model_validate(
        {
            "request_id": request_id,
            "plan_id": "plan_op053_001",
            "source_profile": {
                "schema_version": "wellnessbox.chat.UserProfile.v1",
                "subject_id": SUBJECT_ID,
                "profile": {"age": 41, "sex": "female", "goals": ["sleep"]},
            },
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "data_source_consents": {
                "survey": {
                    "use_for_recommendation": True,
                    "allow_persistent_storage": True,
                },
                "nhis": {},
                "wearable": {},
                "cgm": {},
                "genetic": {},
            },
        }
    )


def _record_execution(store: InterimStore, request_id: str):
    request = _request(request_id)
    return ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )


def _psqi_score(raw_score: int):
    values = [0] * 7
    remaining = raw_score
    for index in range(7):
        values[index] = min(3, remaining)
        remaining -= values[index]
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": "PSQI",
            "item_scores": values,
        }
    )


def _distribution(*, cohort_id: str = "op052-psqi-baseline"):
    return build_pro_baseline_distribution_v1(
        [
            PROBaselineScoreObservationV1(
                schema_version="pro_baseline_score_observation_v1",
                observation_role="BASELINE",
                score=_psqi_score(raw_score),
            )
            for raw_score in (6, 9, 12)
        ],
        cohort_id=cohort_id,
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )


def _event_payload(
    timepoint: str,
    raw_score: int,
    *,
    plan_id: str = "plan_op053_001",
    planned: int = 14,
    taken: int = 14,
    adverse_events: list[dict[str, object]] | None = None,
    distribution_cohort_id: str = "op052-psqi-baseline",
) -> dict[str, object]:
    score = _psqi_score(raw_score)
    standardized = standardize_pro_instrument_score_v1(
        score,
        _distribution(cohort_id=distribution_cohort_id),
    )
    adherence = None
    if timepoint != "pre_intake":
        missed = planned - taken
        adherence = {
            "planned_dose_count": planned,
            "taken_dose_count": taken,
            "missed_dose_count": missed,
            "adherence_rate": round(taken / planned, 6),
        }
    return {
        "schema_version": "versioned_pro_followup_event_v1",
        "assessment_id": f"assessment_{timepoint}",
        "plan_id": plan_id,
        "data_class": "SYNTHETIC_OUTCOME_PROXY",
        "timepoint": timepoint,
        "scheduled_day_index": SCHEDULED_DAYS[timepoint],
        "actual_day_index": ACTUAL_DAYS[timepoint],
        "observed_at": OBSERVED_AT[timepoint],
        "instrument_scores": [score.model_dump(mode="json")],
        "standardized_scores": [standardized.model_dump(mode="json")],
        "adherence": adherence,
        "adverse_events": adverse_events or [],
        "discontinuation_reason": (
            "user_stopped_plan" if timepoint == "discontinuation" else None
        ),
    }


def _expect_rejection(label: str, operation: Callable[[], object]) -> bool:
    try:
        operation()
    except (TypeError, ValueError):
        return True
    raise RuntimeError(f"fail_closed_check_accepted::{label}")


def _interpretation_summary(
    baseline: dict[str, object],
    follow_up: dict[str, object],
) -> dict[str, object]:
    interpretation = interpret_pro_followup_effect_v1(baseline, follow_up)
    return {
        "observed_change_status": interpretation.observed_change_status,
        "mean_health_z_change": interpretation.mean_health_z_change,
        "adherence_rate": interpretation.adherence_rate,
        "missed_dose_count": interpretation.missed_dose_count,
        "adverse_event_count": interpretation.adverse_event_count,
        "serious_adverse_event_present": (
            interpretation.serious_adverse_event_present
        ),
        "interpretation_status": interpretation.interpretation_status,
        "interpretation_reason_codes": interpretation.interpretation_reason_codes,
        "benefit_interpretation_allowed": (
            interpretation.benefit_interpretation_allowed
        ),
        "causal_effect_claim_allowed": interpretation.causal_effect_claim_allowed,
        "effect_claim_scope": interpretation.effect_claim_scope,
    }


def main() -> int:
    args = _args()
    contract = load_pro_followup_interpretation_contract_v1()
    baseline = _event_payload("pre_intake", 10)
    with tempfile.TemporaryDirectory(prefix="op053-op054-") as temporary_directory:
        store = InterimStore(Path(temporary_directory) / "followup.sqlite3")
        store.migrate()
        trace = _record_execution(store, "op053-smoke-main")
        ledger = ExecutionLedger(store)
        persisted = []
        first_event_id = None
        for timepoint, raw_score in (
            ("pre_intake", 10),
            ("week_2", 8),
            ("week_4", 7),
            ("discontinuation", 7),
        ):
            result = ledger.append_event(
                execution_id=trace.execution_id,
                event_type="followup_evaluation",
                source="survey",
                idempotency_key=f"pro-{timepoint}",
                payload=_event_payload(timepoint, raw_score),
            )
            if first_event_id is None:
                first_event_id = result.event.event_id
            persisted.append(
                {
                    "timepoint": result.event.payload["timepoint"],
                    "payload_sha256": result.event.payload_sha256,
                    "payload_state": result.event.payload_state.value,
                }
            )
        stored_followups = [
            event
            for event in ledger.get_trace(trace.execution_id).events
            if event.event_type.value == "followup_evaluation"
            and event.payload.get("schema_version")
            == "versioned_pro_followup_event_v1"
        ]
        if len(stored_followups) != 4:
            raise RuntimeError("all_four_pro_timepoints_were_not_persisted")

        out_of_order_trace = _record_execution(store, "op053-smoke-order")
        out_of_order_rejected = _expect_rejection(
            "out_of_order",
            lambda: ledger.append_event(
                execution_id=out_of_order_trace.execution_id,
                event_type="followup_evaluation",
                source="survey",
                idempotency_key="week-2-first",
                payload=_event_payload("week_2", 8),
            ),
        )
        strict_payload_wrong_event_type_rejected = _expect_rejection(
            "strict_payload_wrong_event_type",
            lambda: ledger.append_event(
                execution_id=out_of_order_trace.execution_id,
                event_type="conversation",
                source="survey",
                idempotency_key="strict-pro-as-conversation",
                payload=_event_payload("week_2", 8),
            ),
        )
        invalid_correction = _event_payload("pre_intake", 10)
        invalid_correction["scheduled_day_index"] = 999
        assert first_event_id is not None
        invalid_correction_rejected = _expect_rejection(
            "invalid_correction",
            lambda: DataMutationLedger(store).apply(
                profile_id=SUBJECT_ID,
                target_type="execution_event",
                target_event_id=first_event_id,
                operation="correction",
                idempotency_key="invalid-pro-correction",
                replacement_payload=invalid_correction,
            ),
        )
        generic_trace = _record_execution(store, "op053-smoke-generic")
        generic_followup = ledger.append_event(
            execution_id=generic_trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="legacy-generic-followup",
            payload={
                "assessment_id": "legacy_assessment",
                "plan_id": "legacy_plan",
                "status": "received",
            },
        )
        generic_followup_preserved = generic_followup.event.payload == {
            "assessment_id": "legacy_assessment",
            "plan_id": "legacy_plan",
            "status": "received",
        }
        generic_to_pro_correction_rejected = _expect_rejection(
            "generic_to_pro_correction",
            lambda: DataMutationLedger(store).apply(
                profile_id=SUBJECT_ID,
                target_type="execution_event",
                target_event_id=generic_followup.event.event_id,
                operation="correction",
                idempotency_key="generic-to-pro",
                replacement_payload=_event_payload("week_2", 8),
            ),
        )

        changed_contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        changed_contract["adherence"]["minimum_interpretable_rate"] = 0.5
        changed_contract_path = Path(temporary_directory) / "changed-contract.json"
        changed_contract_path.write_text(
            json.dumps(changed_contract),
            encoding="utf-8",
        )
        contract_drift_rejected = _expect_rejection(
            "contract_drift",
            lambda: load_pro_followup_interpretation_contract_v1(
                changed_contract_path
            ),
        )

    interpretation_cases = {
        "fully_adherent": _interpretation_summary(
            baseline,
            _event_payload("week_2", 7),
        ),
        "missed_doses": _interpretation_summary(
            baseline,
            _event_payload("week_2", 7, planned=14, taken=12),
        ),
        "low_adherence": _interpretation_summary(
            baseline,
            _event_payload("week_2", 7, planned=14, taken=10),
        ),
        "nonserious_adverse_event": _interpretation_summary(
            baseline,
            _event_payload(
                "week_2",
                7,
                adverse_events=[
                    {
                        "adverse_event_id": "ae_mild_001",
                        "severity": "mild",
                        "relatedness": "possible",
                        "ongoing": False,
                    }
                ],
            ),
        ),
        "serious_adverse_event": _interpretation_summary(
            baseline,
            _event_payload(
                "week_2",
                7,
                adverse_events=[
                    {
                        "adverse_event_id": "ae_serious_001",
                        "severity": "serious",
                        "relatedness": "unknown",
                        "ongoing": True,
                    }
                ],
            ),
        ),
    }
    expected_statuses = {
        "fully_adherent": "observed_change_interpretable",
        "missed_doses": "limited_by_missed_doses",
        "low_adherence": "limited_by_low_adherence",
        "nonserious_adverse_event": "safety_context_required",
        "serious_adverse_event": "safety_escalation_required",
    }
    if {
        key: value["interpretation_status"]
        for key, value in interpretation_cases.items()
    } != expected_statuses:
        raise RuntimeError("interpretation_statuses_changed")
    if len(
        {
            value["mean_health_z_change"]
            for value in interpretation_cases.values()
        }
    ) != 1:
        raise RuntimeError("context_changed_the_observed_numeric_effect")

    missing_schema = _event_payload("pre_intake", 10)
    missing_schema.pop("schema_version")
    duplicate_assessment = _event_payload("week_2", 7)
    duplicate_assessment["assessment_id"] = baseline["assessment_id"]
    reversed_observation_time = _event_payload("week_2", 7)
    reversed_observation_time["observed_at"] = "2025-12-31T00:00:00Z"
    changed_output = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload("week_2", 7),
    ).model_dump(mode="json")
    changed_output["mean_health_z_change"] = 999.0
    fail_closed_checks = {
        "contract_drift_rejected": contract_drift_rejected,
        "duplicate_assessment_rejected": _expect_rejection(
            "duplicate_assessment",
            lambda: interpret_pro_followup_effect_v1(
                baseline,
                duplicate_assessment,
            ),
        ),
        "cross_distribution_rejected": _expect_rejection(
            "cross_distribution",
            lambda: interpret_pro_followup_effect_v1(
                baseline,
                _event_payload(
                    "week_2",
                    7,
                    distribution_cohort_id="different-baseline",
                ),
            ),
        ),
        "cross_plan_rejected": _expect_rejection(
            "cross_plan",
            lambda: interpret_pro_followup_effect_v1(
                baseline,
                _event_payload("week_2", 7, plan_id="plan_other"),
            ),
        ),
        "invalid_correction_rejected": invalid_correction_rejected,
        "generic_followup_preserved": generic_followup_preserved,
        "generic_to_pro_correction_rejected": (
            generic_to_pro_correction_rejected
        ),
        "missing_schema_rejected": _expect_rejection(
            "missing_schema",
            lambda: PROFollowUpEventV1.model_validate(missing_schema),
        ),
        "out_of_order_rejected": out_of_order_rejected,
        "output_mutation_rejected": _expect_rejection(
            "output_mutation",
            lambda: PROFollowUpEffectInterpretationV1.model_validate(changed_output),
        ),
        "reversed_observation_time_rejected": _expect_rejection(
            "reversed_observation_time",
            lambda: interpret_pro_followup_effect_v1(
                baseline,
                reversed_observation_time,
            ),
        ),
        "strict_payload_wrong_event_type_rejected": (
            strict_payload_wrong_event_type_rejected
        ),
    }
    if not all(fail_closed_checks.values()):
        raise RuntimeError("one_or_more_fail_closed_checks_failed")

    report = {
        "schema_version": "op053_op054_pro_followup_interpretation_smoke_v1",
        "requirement_stages": {"OP-053": "IMPLEMENTED", "OP-054": "IMPLEMENTED"},
        "required_stage_boundary": {
            "OP-053": "OPERATED",
            "OP-054": "IMPLEMENTED",
        },
        "contract": {
            "schema_version": contract.schema_version,
            "contract_version": contract.contract_version,
            "event_schema_version": contract.event_schema_version,
            "policy_kind": contract.policy_kind,
            "source_refs": contract.source_refs,
            "limitation": contract.limitation,
            "contract_sha256": _contract_sha256(),
            "timepoint_order": contract.timepoint_order,
            "scheduled_day_index_by_timepoint": (
                contract.scheduled_day_index_by_timepoint
            ),
            "minimum_interpretable_adherence_rate": (
                contract.adherence.minimum_interpretable_rate
            ),
            "interpretation_priority": contract.interpretation_priority,
            "effect_claim_scope": contract.effect_claim_scope,
        },
        "local_persistence": {
            "database": "temporary_local_sqlite",
            "existing_table": "execution_events",
            "event_type": "followup_evaluation",
            "persisted_event_count": len(persisted),
            "persisted_events": persisted,
            "ordered_timepoints": [item["timepoint"] for item in persisted],
        },
        "interpretation_cases": interpretation_cases,
        "fail_closed_checks": fail_closed_checks,
        "evidence_boundary": {
            "event_data_class": "SYNTHETIC_OUTCOME_PROXY",
            "score_distribution_data_class": "SYNTHETIC_OUTCOME_PROXY",
            "local_persistence_proven": True,
            "production_data_used": False,
            "production_operation_proven": False,
            "op053_operated_stage_proven": False,
            "service_integration_proven": False,
            "clinical_interpretation_proven": False,
            "causal_effect_claim_allowed": False,
        },
        "source_identity": {
            "commit": _git_source_commit(),
            "source_paths": sorted(SOURCE_PATHS),
            "source_sha256": _source_sha256(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema_version": report["schema_version"],
                "requirement_stages": report["requirement_stages"],
                "required_stage_boundary": report["required_stage_boundary"],
                "contract": report["contract"],
                "local_persistence": report["local_persistence"],
                "interpretation_statuses": expected_statuses,
                "fail_closed_checks": fail_closed_checks,
                "evidence_boundary": report["evidence_boundary"],
                "source_identity": report["source_identity"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
