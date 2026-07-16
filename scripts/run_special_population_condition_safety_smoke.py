from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.interim.safety import evaluate_safety
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)

CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "pregnancy",
        "input": {"pregnant": True},
        "expected_status": "needs_review",
        "expected_rule_ids": ["SAFETY-PREG-001"],
    },
    {
        "case_id": "lactation",
        "input": {"lactating": True},
        "expected_status": "needs_review",
        "expected_rule_ids": ["SAFETY-LACT-001"],
    },
    {
        "case_id": "pregnancy_and_lactation",
        "input": {"pregnant": True, "lactating": True},
        "expected_status": "needs_review",
        "expected_rule_ids": ["SAFETY-PREG-001", "SAFETY-LACT-001"],
    },
    {
        "case_id": "renal_review",
        "input": {"conditions": ["kidney disease"]},
        "expected_status": "needs_review",
        "expected_rule_ids": ["SAFETY-RENAL-001"],
    },
    {
        "case_id": "severe_renal_block",
        "input": {"conditions": ["kidney failure"]},
        "expected_status": "blocked",
        "expected_rule_ids": ["SAFETY-RENAL-SEVERE-001"],
    },
    {
        "case_id": "hepatic_review_block",
        "input": {"conditions": ["cirrhosis"]},
        "expected_status": "blocked",
        "expected_rule_ids": ["SAFETY-HEPATIC-001"],
    },
    {
        "case_id": "hemochromatosis_contraindication",
        "input": {"conditions": ["hemochromatosis"]},
        "expected_status": "needs_review",
        "expected_rule_ids": ["SAFETY-HEMO-001"],
    },
    {
        "case_id": "unmatched_condition",
        "input": {"conditions": ["seasonal allergies"]},
        "expected_status": "ok",
        "expected_rule_ids": [],
    },
)


def _recommendation_result(case: dict[str, Any]) -> dict[str, Any]:
    payload = case["input"]
    request = RecommendationRequest(
        request_id=f"op033-op034-{case['case_id']}",
        user_profile=UserProfile(
            age=32,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=bool(payload.get("pregnant")),
            lactating=bool(payload.get("lactating")),
        ),
        goals=[RecommendationGoal.GENERAL_WELLNESS],
        conditions=list(payload.get("conditions", [])),
    )
    summary = assess_safety(normalize_request(request))
    result = {
        "status": summary.status.value,
        "rule_ids": [rule.rule_id for rule in summary.rule_refs],
        "excluded_ingredients": summary.excluded_ingredients,
    }
    if result["status"] != case["expected_status"]:
        raise AssertionError(f"unexpected status for {case['case_id']}: {result}")
    if result["rule_ids"] != case["expected_rule_ids"]:
        raise AssertionError(f"unexpected rules for {case['case_id']}: {result}")
    return result


def _interim_result(case: dict[str, Any]) -> dict[str, Any]:
    payload = dict(case["input"])
    if case["case_id"] == "hemochromatosis_contraindication":
        payload["ingredients"] = ["iron"]
    decision = evaluate_safety(payload)
    return {
        "action": decision.action,
        "rule_ids": [finding.rule_id for finding in decision.findings],
    }


def build_evidence() -> dict[str, Any]:
    return {
        "schema_version": "op033_op034_special_population_condition_safety_smoke_v1",
        "requirements": ["OP-033", "OP-034"],
        "contains_health_identifiers": False,
        "policy_sources": [
            {
                "source_id": "NIH-NCCIH-ASHWAGANDHA",
                "url": "https://www.nccih.nih.gov/health/ashwagandha",
                "supports": ["pregnancy", "lactation"],
            },
            {
                "source_id": "NIH-ODS-MAGNESIUM-HP",
                "url": "https://ods.od.nih.gov/factsheets/Magnesium-HealthProfessional/",
                "supports": ["renal_impairment"],
            },
            {
                "source_id": "NIH-ODS-IRON-HP",
                "url": "https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/",
                "supports": ["hemochromatosis"],
            },
        ],
        "cases": [
            {
                "case_id": case["case_id"],
                "recommendation_path": _recommendation_result(case),
                "interim_replay_path": _interim_result(case),
            }
            for case in CASES
        ],
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_path = (
        root
        / "data"
        / "original_plan"
        / "evidence"
        / "op033_op034_special_population_condition_safety_smoke_v1.json"
    )
    rendered = json.dumps(build_evidence(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rendered_bytes = rendered.encode("utf-8")
    output_path.write_bytes(rendered_bytes)
    digest = hashlib.sha256(rendered_bytes).hexdigest()
    if hashlib.sha256(output_path.read_bytes()).hexdigest() != digest:
        raise AssertionError("written evidence hash does not match rendered evidence")
    print(f"Evidence: {output_path}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
