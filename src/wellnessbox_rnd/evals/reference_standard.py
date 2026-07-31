"""Seal a human reference standard before the engine produces its answer.

KPI-1 scores the engine against `R_i`, the ingredient set the pharmacist group
derived. KPI-3, 4 and 5 work the same way against a pre-defined answer. If the
human answer is written after seeing the engine output, the score measures
nothing — the intersection converges on 100% by construction.

Sealing fixes that without needing anyone from outside. The reviewer writes the
answer first, seals it with a digest, and only then is the engine allowed to
run. The comparison step refuses to score unless the seal still matches, so a
later edit is detectable rather than silent.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEAL_SCHEMA = "reference_standard_seal_v1"
COMPARISON_SCHEMA = "reference_standard_comparison_v1"
CONTRACT_RELATIVE_PATH = "data/original_plan/contracts/kpi_measurement_contract_v1.json"


def canonical_digest(payload: Any) -> str:
    """Digest a reference standard so any later edit changes the value."""
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_contract(root: Path) -> dict[str, Any]:
    path = Path(root) / CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise FileNotFoundError(f"kpi_measurement_contract_missing:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def indicator(contract: dict[str, Any], indicator_id: str) -> dict[str, Any]:
    for item in contract.get("indicators", []):
        if item["id"] == indicator_id:
            return item
    raise KeyError(f"unknown_indicator:{indicator_id}")


def seal_reference_standard(
    *,
    indicator_id: str,
    cases: dict[str, list[str]],
    sealed_by: str,
    sealed_at: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Record the human answer and its digest before any engine output exists."""
    spec = indicator(contract, indicator_id)
    if not sealed_by.strip():
        raise ValueError("seal_requires_a_named_person")
    if not cases:
        raise ValueError("seal_requires_at_least_one_case")

    minimum = int(spec["minimum_sample"]["count"])
    normalised = {case_id: sorted(set(items)) for case_id, items in cases.items()}
    empty = sorted(case_id for case_id, items in normalised.items() if not items)
    if empty:
        raise ValueError(f"reference_standard_has_empty_cases:{empty}")

    return {
        "schema_version": SEAL_SCHEMA,
        "indicator_id": indicator_id,
        "indicator_name": spec["name"],
        "sealed_by": sealed_by.strip(),
        "sealed_at": sealed_at,
        "case_count": len(normalised),
        "minimum_sample_count": minimum,
        "meets_minimum_sample": len(normalised) >= minimum,
        "engine_output_seen_before_sealing": False,
        "cases": normalised,
        "seal_sha256": canonical_digest(normalised),
    }


def verify_seal(seal: dict[str, Any]) -> dict[str, Any]:
    """Re-derive the digest so an edit after sealing cannot pass unnoticed."""
    recomputed = canonical_digest(seal.get("cases", {}))
    intact = recomputed == seal.get("seal_sha256")
    return {
        "schema_version": "reference_standard_seal_check_v1",
        "status": "READY" if intact else "BLOCKED",
        "seal_intact": intact,
        "recorded_sha256": seal.get("seal_sha256"),
        "recomputed_sha256": recomputed,
    }


def score_against_seal(
    *,
    seal: dict[str, Any],
    engine_output: dict[str, list[str]],
) -> dict[str, Any]:
    """Score engine output against the sealed answer using the plan's formula."""
    check = verify_seal(seal)
    if not check["seal_intact"]:
        raise ValueError("reference_standard_seal_broken")

    reference: dict[str, list[str]] = seal["cases"]
    missing_cases = sorted(set(reference) - set(engine_output))
    extra_cases = sorted(set(engine_output) - set(reference))

    per_case: list[dict[str, Any]] = []
    for case_id in sorted(reference):
        expected = set(reference[case_id])
        actual = set(engine_output.get(case_id, []))
        overlap = expected & actual
        score = 100.0 * len(overlap) / len(expected) if expected else 0.0
        per_case.append(
            {
                "case_id": case_id,
                "reference_count": len(expected),
                "engine_count": len(actual),
                "matched_count": len(overlap),
                "score_pct": round(score, 4),
                "missing_from_engine": sorted(expected - actual),
            }
        )

    mean_score = sum(item["score_pct"] for item in per_case) / len(per_case) if per_case else 0.0
    return {
        "schema_version": COMPARISON_SCHEMA,
        "indicator_id": seal["indicator_id"],
        "sealed_by": seal["sealed_by"],
        "sealed_at": seal["sealed_at"],
        "seal_sha256": seal["seal_sha256"],
        "case_count": len(per_case),
        "minimum_sample_count": seal["minimum_sample_count"],
        "meets_minimum_sample": len(per_case) >= seal["minimum_sample_count"],
        "cases_missing_engine_output": missing_cases,
        "cases_not_in_reference": extra_cases,
        "mean_score_pct": round(mean_score, 4),
        "per_case": per_case,
        "measurement_environment": "research_phase_internal_measurement",
        "note": (
            "연구 기간의 내부 측정값이다. 연구를 마친 뒤 공인시험기관 최종 검증을 "
            "별도로 받는다."
        ),
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target
