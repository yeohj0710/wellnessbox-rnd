from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from copy import deepcopy
from pathlib import Path

from wellnessbox_rnd.metrics.pro_followup import interpret_pro_followup_effect_v1
from wellnessbox_rnd.metrics.pro_group_effects import (
    PROGroupEffectSummaryV1,
    build_pro_group_effect_summary_v1,
    load_pro_group_effect_contract_v1,
)
from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineScoreObservationV1,
    build_pro_baseline_distribution_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "data/contracts/pro_group_effect_summary_v1.json"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op055_op056_pro_personal_group_uncertainty_smoke_v1.json"
)
SOURCE_PATHS = [
    "data/contracts/pro_group_effect_summary_v1.json",
    "scripts/run_pro_personal_group_uncertainty_smoke.py",
    "src/wellnessbox_rnd/interim/kpi.py",
    "src/wellnessbox_rnd/metrics/__init__.py",
    "src/wellnessbox_rnd/metrics/pro_followup.py",
    "src/wellnessbox_rnd/metrics/pro_group_effects.py",
    "src/wellnessbox_rnd/metrics/pro_scoring.py",
    "src/wellnessbox_rnd/metrics/statistics.py",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify separate personal and group PRO estimates with uncertainty."
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


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _psqi_score(raw_score: int):
    item_scores = [0] * 7
    remaining = raw_score
    for index in range(7):
        item_scores[index] = min(3, remaining)
        remaining -= item_scores[index]
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": "PSQI",
            "item_scores": item_scores,
        }
    )


def _distribution(*, cohort_id: str = "op055-psqi-baseline"):
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


def _event(
    member_index: int,
    *,
    timepoint: str,
    raw_score: int,
    plan_id: str | None = None,
    distribution_cohort_id: str = "op055-psqi-baseline",
) -> dict[str, object]:
    score = _psqi_score(raw_score)
    standardized = standardize_pro_instrument_score_v1(
        score,
        _distribution(cohort_id=distribution_cohort_id),
    )
    scheduled_day_by_timepoint = {
        "pre_intake": 0,
        "week_2": 14,
        "week_4": 28,
        "discontinuation": None,
    }
    actual_day_by_timepoint = {
        "pre_intake": 0,
        "week_2": 14,
        "week_4": 28,
        "discontinuation": 35,
    }
    observed_at_by_timepoint = {
        "pre_intake": "2026-01-01T00:00:00Z",
        "week_2": "2026-01-15T00:00:00Z",
        "week_4": "2026-01-29T00:00:00Z",
        "discontinuation": "2026-02-05T00:00:00Z",
    }
    is_baseline = timepoint == "pre_intake"
    return {
        "schema_version": "versioned_pro_followup_event_v1",
        "assessment_id": f"assessment_{member_index:03d}_{timepoint}",
        "plan_id": plan_id or f"plan_{member_index:03d}",
        "data_class": "SYNTHETIC_OUTCOME_PROXY",
        "timepoint": timepoint,
        "scheduled_day_index": scheduled_day_by_timepoint[timepoint],
        "actual_day_index": actual_day_by_timepoint[timepoint],
        "observed_at": observed_at_by_timepoint[timepoint],
        "instrument_scores": [score.model_dump(mode="json")],
        "standardized_scores": [standardized.model_dump(mode="json")],
        "adherence": (
            None
            if is_baseline
            else {
                "planned_dose_count": 14,
                "taken_dose_count": 14,
                "missed_dose_count": 0,
                "adherence_rate": 1.0,
            }
        ),
        "adverse_events": [],
        "discontinuation_reason": (
            "user_stopped_plan" if timepoint == "discontinuation" else None
        ),
    }


def _personal_effect(
    member_index: int,
    raw_score: int,
    *,
    plan_id: str | None = None,
    timepoint: str = "week_2",
    distribution_cohort_id: str = "op055-psqi-baseline",
):
    return interpret_pro_followup_effect_v1(
        _event(
            member_index,
            timepoint="pre_intake",
            raw_score=10,
            plan_id=plan_id,
            distribution_cohort_id=distribution_cohort_id,
        ),
        _event(
            member_index,
            timepoint=timepoint,
            raw_score=raw_score,
            plan_id=plan_id,
            distribution_cohort_id=distribution_cohort_id,
        ),
    )


def _is_rejected(action) -> bool:
    try:
        action()
    except (ValueError, TypeError):
        return True
    return False


def run_smoke() -> dict[str, object]:
    contract = load_pro_group_effect_contract_v1()
    personal_effects = [
        _personal_effect(index, 7 + (index % 3)) for index in range(100)
    ]
    personal_numeric_before = [
        item.mean_health_z_change for item in personal_effects
    ]
    summary = build_pro_group_effect_summary_v1(
        cohort_id="op055_sleep_week_2_n100",
        personal_effects=personal_effects,
    )
    reversed_summary = build_pro_group_effect_summary_v1(
        cohort_id="op055_sleep_week_2_n100",
        personal_effects=list(reversed(personal_effects)),
    )
    personal_numeric_after = [
        item.mean_health_z_change for item in summary.personal_effects
    ]
    expected_group_z_mean = round(statistics.mean(personal_numeric_before), 6)

    mutated = deepcopy(summary.model_dump(mode="json"))
    mutated["group_estimate"]["mean_health_z_change"] = 999.0
    rejection_checks = {
        "duplicate_plan_rejected": _is_rejected(
            lambda: build_pro_group_effect_summary_v1(
                cohort_id="duplicate-plan",
                personal_effects=[
                    _personal_effect(200, 7, plan_id="plan_duplicate"),
                    _personal_effect(201, 8, plan_id="plan_duplicate"),
                ],
            )
        ),
        "mixed_timepoint_rejected": _is_rejected(
            lambda: build_pro_group_effect_summary_v1(
                cohort_id="mixed-timepoint",
                personal_effects=[
                    _personal_effect(202, 7),
                    _personal_effect(203, 8, timepoint="week_4"),
                ],
            )
        ),
        "mixed_distribution_rejected": _is_rejected(
            lambda: build_pro_group_effect_summary_v1(
                cohort_id="mixed-distribution",
                personal_effects=[
                    _personal_effect(204, 7),
                    _personal_effect(
                        205,
                        8,
                        distribution_cohort_id="op055-different-baseline",
                    ),
                ],
            )
        ),
        "derived_output_mutation_rejected": _is_rejected(
            lambda: PROGroupEffectSummaryV1.model_validate(mutated)
        ),
    }
    checks = {
        "personal_group_fields_separate": (
            len(summary.personal_effects) == summary.group_estimate.sample_size == 100
        ),
        "personal_numeric_effects_unchanged": (
            personal_numeric_before == personal_numeric_after
        ),
        "group_mean_matches_personal_values": (
            summary.group_estimate.mean_health_z_change == expected_group_z_mean
        ),
        "order_independent": (
            summary.model_dump(mode="json")
            == reversed_summary.model_dump(mode="json")
        ),
        "confidence_intervals_present": (
            summary.group_estimate.mean_health_z_change_ci95.lower > 0
            and summary.group_estimate.mean_health_percentile_change_ci95.lower > 0
        ),
        "sample_target_met": summary.group_estimate.sample_size >= 100,
        "non_causal_boundary_fixed": not summary.causal_effect_claim_allowed,
        **rejection_checks,
    }
    if not all(checks.values()):
        raise RuntimeError(f"pro_personal_group_uncertainty_smoke_failed::{checks}")

    personal_payloads = [
        item.model_dump(mode="json") for item in summary.personal_effects
    ]
    return {
        "schema_version": "op055_op056_pro_personal_group_uncertainty_smoke_v1",
        "requirement_stages": {"OP-055": "IMPLEMENTED", "OP-056": "IMPLEMENTED"},
        "contract": {
            "schema_version": contract.schema_version,
            "contract_version": contract.contract_version,
            "contract_sha256": _contract_sha256(),
            "minimum_group_sample_size": contract.minimum_group_sample_size,
            "kpi_target_sample_size": contract.kpi_target_sample_size,
            "confidence_interval": contract.confidence_interval.model_dump(mode="json"),
        },
        "personal_effects": {
            "count": len(personal_payloads),
            "source_sha256": _canonical_sha256(personal_payloads),
            "first_plan_id": summary.personal_effects[0].baseline_event.plan_id,
            "last_plan_id": summary.personal_effects[-1].baseline_event.plan_id,
        },
        "group_estimate": summary.group_estimate.model_dump(mode="json"),
        "uncertainty_reason_codes": summary.uncertainty_reason_codes,
        "checks": checks,
        "evidence_boundary": {
            "data_class": "SYNTHETIC_OUTCOME_PROXY",
            "real_world_outcome_used": False,
            "production_operation_proven": False,
            "service_integration_proven": False,
            "causal_effect_claim_allowed": False,
        },
        "source_identity": {
            "commit": _git_source_commit(),
            "source_paths": sorted(SOURCE_PATHS),
            "source_sha256": _source_sha256(),
        },
    }


def main() -> int:
    args = _args()
    report = run_smoke()
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
                "personal_effects": report["personal_effects"],
                "group_estimate": report["group_estimate"],
                "checks": report["checks"],
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
