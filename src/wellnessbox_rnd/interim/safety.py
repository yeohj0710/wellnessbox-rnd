from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from enum import IntEnum
from typing import Any

from wellnessbox_rnd.interim.store import InterimStore


class SafetyRank(IntEnum):
    PASS = 0
    WARN = 1
    BLOCK = 2
    STOP_AND_ESCALATE = 3


@dataclass(frozen=True)
class SafetyFinding:
    rule_id: str
    category: str
    action: str
    reason: str


@dataclass(frozen=True)
class SafetyDecision:
    action: str
    findings: tuple[SafetyFinding, ...]

    @property
    def hard_failure(self) -> bool:
        return self.action in {"BLOCK", "STOP_AND_ESCALATE"}


def _finding(rule: str, category: str, action: str, reason: str) -> SafetyFinding:
    return SafetyFinding(rule, category, action, reason)


def evaluate_safety(
    payload: dict[str, Any],
    *,
    as_of: date | None = None,
    store: InterimStore | None = None,
) -> SafetyDecision:
    """Deterministic, non-overridable safety decision for interim and replay paths."""

    findings: list[SafetyFinding] = []
    symptoms = {str(x).lower() for x in payload.get("symptoms", [])}
    conditions = {str(x).lower() for x in payload.get("conditions", [])}
    medications = {str(x).lower() for x in payload.get("medications", [])}
    allergies = {str(x).lower() for x in payload.get("allergies", [])}
    ingredients = {str(x).lower() for x in payload.get("ingredients", [])}
    duplicates = {str(x).lower() for x in payload.get("duplicate_ingredients", [])}
    age = int(payload.get("age", 18))

    if symptoms & {"chest pain", "anaphylaxis", "suicidal ideation", "severe bleeding"}:
        findings.append(
            _finding("SAFE-EMERGENCY-001", "emergency", "STOP_AND_ESCALATE", "emergency_symptom")
        )
    if payload.get("pregnant"):
        findings.append(
            _finding("SAFE-PREG-001", "pregnancy", "BLOCK", "pregnancy_restriction")
        )
    if payload.get("lactating"):
        findings.append(
            _finding("SAFE-LACT-001", "lactation", "BLOCK", "lactation_restriction")
        )
    if age < 14 or age > 85:
        findings.append(_finding("SAFE-AGE-001", "age", "BLOCK", "age_outside_validated_range"))
    if conditions & {"kidney failure", "dialysis"}:
        findings.append(
            _finding("SAFE-RENAL-001", "kidney", "BLOCK", "severe_renal_impairment")
        )
    elif conditions & {"kidney disease", "chronic kidney disease"}:
        findings.append(
            _finding(
                "SAFE-RENAL-REVIEW-001",
                "kidney",
                "WARN",
                "renal_review_required",
            )
        )
    if conditions & {"liver failure", "cirrhosis"}:
        findings.append(
            _finding("SAFE-HEPATIC-001", "liver", "BLOCK", "hepatic_impairment")
        )
    if allergies & ingredients:
        findings.append(
            _finding("SAFE-ALLERGY-001", "allergy", "STOP_AND_ESCALATE", "allergen_match")
        )
    if payload.get("surgery_within_days", 999) <= 14:
        findings.append(_finding("SAFE-SURGERY-001", "surgery", "BLOCK", "perioperative_window"))
    if medications & {"warfarin", "apixaban", "rivaroxaban"} and ingredients & {"omega3", "ginkgo"}:
        findings.append(
            _finding("SAFE-DDI-001", "drug_interaction", "BLOCK", "anticoagulant_interaction")
        )
    if "hemochromatosis" in conditions and ingredients & {"iron", "vitamin c", "vitamin_c"}:
        findings.append(
            _finding("SAFE-HEMO-001", "condition_caution", "BLOCK", "hemochromatosis_conflict")
        )
    if duplicates:
        findings.append(_finding("SAFE-DUP-001", "duplicate", "BLOCK", "duplicate_ingredient"))
    if payload.get("above_ul"):
        findings.append(
            _finding("SAFE-UL-001", "upper_limit", "BLOCK", "tolerable_upper_limit_exceeded")
        )
    if payload.get("requires_test") and not payload.get("test_available"):
        findings.append(
            _finding("SAFE-TEST-001", "test_before_recommend", "BLOCK", "required_test_missing")
        )
    if payload.get("timing_conflict"):
        findings.append(
            _finding("SAFE-TIMING-001", "timing", "WARN", "administration_timing_conflict")
        )
    if payload.get("label_constraint_violation"):
        findings.append(_finding("SAFE-LABEL-001", "label_constraint", "BLOCK", "label_constraint"))
    if payload.get("evidence_valid_until"):
        valid_until = date.fromisoformat(str(payload["evidence_valid_until"])[:10])
        if (as_of or date.today()) > valid_until:
            findings.append(_finding("SAFE-STALE-001", "stale_source", "BLOCK", "evidence_expired"))

    if store is not None:
        instant = (as_of or date.today()).isoformat()
        for row in store.rows(
            """
            select sr.rule_id, sr.action, sr.predicate_json
            from safety_rules sr
            where sr.review_status='ACTIVE' and substr(sr.valid_from,1,10) <= ?
              and (sr.valid_to is null or substr(sr.valid_to,1,10) >= ?)
              and not exists (
                select 1 from json_each(sr.evidence_ids_json) ids
                left join evidence_passages ep on ep.evidence_id=ids.value
                left join source_registry src on src.source_id=ep.source_id
                where ep.approved_for_safety != 1 or src.retired_at is not null
                   or src.metadata_json like '%\"quarantined\":true%'
              )
            """,
            (instant, instant),
        ):
            predicate = json.loads(row["predicate_json"])
            if predicate and all(payload.get(key) == value for key, value in predicate.items()):
                findings.append(
                    _finding(
                        str(row["rule_id"]), "versioned_rule", str(row["action"]), "active_rule"
                    )
                )

    action = max(
        (finding.action for finding in findings), key=lambda item: SafetyRank[item], default="PASS"
    )
    return SafetyDecision(action=action, findings=tuple(findings))
