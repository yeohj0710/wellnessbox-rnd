"""Atomically replace all rejected KPI cases after both review rounds finish."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_final_review_package import (  # noqa: E402
    STAGING_PATH as FIRST_STAGING_PATH,
)
from scripts.build_kpi_replacement_final_review_package import (  # noqa: E402
    build_workbenches,
)
from scripts.build_kpi_second_replacement_handoff import (  # noqa: E402
    CANDIDATES_PATH as SECOND_CANDIDATES_PATH,
)
from scripts.build_kpi_second_replacement_handoff import (  # noqa: E402
    SECOND_DIR,
)
from scripts.import_kpi_replacement_final_review import (  # noqa: E402
    DECISIONS_PATH as FIRST_DECISIONS_PATH,
)
from scripts.import_kpi_second_replacement_final_review import (  # noqa: E402
    DECISIONS_PATH as SECOND_DECISIONS_PATH,
)
from scripts.import_kpi_second_replacement_response import (  # noqa: E402
    STAGING_PATH as SECOND_STAGING_PATH,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    _review_digest,
    build_adaptive_review_plan,
    build_blind_ai_review_packet,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    CaseDraft,
    Workbench,
    decide,
    load_workbench,
    save_workbench,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    load_registry as load_identity_registry,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    registered_reviewer_identity_references,
    reviewer_identity_reference,
)

INDICATORS = ("KPI-1", "KPI-4", "KPI-5")
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
REPORT_PATH = SECOND_DIR / "kpi_replacement_application_v1.json"
EXPECTED_REPLACEMENT_COUNTS = {"KPI-1": 49, "KPI-4": 7, "KPI-5": 9}


def bind_composite_packet_record(
    record: dict[str, Any], workbench: Workbench
) -> dict[str, Any]:
    """Bind a merged response to its distinct historical request packets."""
    if not record:
        return record
    provenance = record.get("case_provenance", {})
    original_packet = str(record.get("packet_sha256", ""))
    groups: dict[str, list[str]] = {}
    prompts = {draft.case_id: draft.prompt for draft in workbench.drafts}
    for case_id in record.get("cases", {}):
        packet_sha256 = str(
            provenance.get(case_id, {}).get("packet_sha256", original_packet)
        )
        if not packet_sha256:
            raise ValueError(f"composite_packet_source_missing:{case_id}")
        groups.setdefault(packet_sha256, []).append(case_id)
    segments = []
    for packet_sha256, raw_case_ids in sorted(groups.items()):
        case_ids = sorted(raw_case_ids)
        segments.append(
            {
                "packet_sha256": packet_sha256,
                "case_count": len(case_ids),
                "case_ids": case_ids,
                "case_prompts_sha256": _review_digest(
                    {
                        case_id: {"prompt": prompts[case_id]}
                        for case_id in case_ids
                    }
                ),
            }
        )
    expected = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=list(record.get("required_blinded_from", [])),
    )
    record["packet_segments"] = segments
    record["composite_packet_sha256"] = expected["packet_sha256"]
    return record


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def _workbench_path(indicator_id: str) -> Path:
    return WORKBENCH_DIR / f"{_slug(indicator_id)}_workbench_v1.json"


def _reviewer(identity_ref: str) -> tuple[str, set[str], set[str]]:
    registry = load_identity_registry(ROOT)
    eligible = [
        entry
        for entry in registry.get("registered_reviewers", [])
        if entry.get("may_review_h005") is True
    ]
    trusted_refs = registered_reviewer_identity_references(
        {**registry, "registered_reviewers": eligible}
    )
    trusted_names = {
        str(entry.get("name", "")).strip()
        for entry in eligible
        if str(entry.get("name", "")).strip()
    }
    for entry in eligible:
        if reviewer_identity_reference(entry) == identity_ref:
            return str(entry["name"]), trusted_refs, trusted_names
    raise ValueError("replacement_reviewer_identity_not_registered")


def _second_workbench() -> Workbench:
    candidates = _read_json(SECOND_CANDIDATES_PATH)
    drafts = [CaseDraft(**deepcopy(item)) for item in candidates.get("cases", [])]
    if len(drafts) != 2:
        raise ValueError("second_replacement_candidate_count_changed")
    staging = _read_json(SECOND_STAGING_PATH)
    if staging.get("status") != "READY_FOR_FINAL_REVIEW_PACKAGE":
        raise ValueError("second_replacement_staging_not_ready")
    return Workbench(
        "KPI-1",
        drafts,
        ai_review=deepcopy(staging["validated_record"]),
    )


def _decision_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in payload.get("decisions", []):
        case_id = str(item.get("case_id", "")).strip()
        if not case_id or case_id in result:
            raise ValueError(f"replacement_decision_case_invalid:{case_id}")
        result[case_id] = item
    return result


def _replacement_inputs() -> tuple[
    dict[str, list[CaseDraft]],
    dict[str, dict[str, dict[str, Any]]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    first_staging = _read_json(FIRST_STAGING_PATH)
    first_workbenches = build_workbenches(first_staging)
    second_workbench = _second_workbench()
    first_payload = _read_json(FIRST_DECISIONS_PATH)
    second_payload = _read_json(SECOND_DECISIONS_PATH)
    if first_payload.get("replacement_required_count") != 2:
        raise ValueError("first_replacement_reject_count_changed")
    if second_payload.get("status") != "READY_TO_APPLY_ALL_REPLACEMENTS":
        raise ValueError("second_replacement_decisions_not_ready")
    if second_payload.get("replacement_required_count") != 0:
        raise ValueError("second_replacement_contains_reject")
    first_decisions = _decision_map(first_payload)
    second_decisions = _decision_map(second_payload)

    drafts: dict[str, list[CaseDraft]] = {}
    reviews: dict[str, dict[str, dict[str, Any]]] = {}
    primaries: dict[str, dict[str, Any]] = {}
    for indicator_id in INDICATORS:
        workbench = first_workbenches[indicator_id]
        accepted = [
            deepcopy(draft)
            for draft in workbench.drafts
            if first_decisions[draft.case_id]["decision"] != "REJECT"
        ]
        review_cases = {
            draft.case_id: deepcopy(workbench.ai_review["cases"][draft.case_id])
            for draft in accepted
        }
        if indicator_id == "KPI-1":
            accepted.extend(deepcopy(second_workbench.drafts))
            review_cases.update(deepcopy(second_workbench.ai_review["cases"]))
        drafts[indicator_id] = accepted
        reviews[indicator_id] = review_cases
        primaries[indicator_id] = deepcopy(workbench.primary_ai_draft)
    all_decisions = {**first_decisions, **second_decisions}
    return drafts, reviews, primaries, all_decisions


def _merge_case_record(
    record: dict[str, Any],
    *,
    removed_ids: set[str],
    added_cases: dict[str, dict[str, Any]],
    source_record: dict[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(record)
    cases = {
        case_id: deepcopy(item)
        for case_id, item in record.get("cases", {}).items()
        if case_id not in removed_ids
    }
    cases.update(deepcopy(added_cases))
    merged["cases"] = cases
    merged["case_count"] = len(cases)
    merged["cases_sha256"] = _review_digest(cases)
    provenance = dict(merged.get("case_provenance", {}))
    for case_id in added_cases:
        provenance[case_id] = {
            "schema_version": source_record.get("schema_version"),
            "agent": source_record.get(
                "reviewing_agent", source_record.get("drafting_agent", "")
            ),
            "agent_family": source_record.get(
                "reviewing_agent_family",
                source_record.get("drafting_agent_family", ""),
            ),
            "source": source_record.get(
                "review_source", source_record.get("response_source", "")
            ),
            "packet_sha256": source_record.get("packet_sha256", ""),
            "engine_output_consulted": source_record.get(
                "engine_output_consulted", False
            ),
        }
    merged["case_provenance"] = provenance
    return merged


def build_applied_workbenches() -> tuple[dict[str, Workbench], dict[str, Any]]:
    replacements, replacement_reviews, replacement_primaries, decisions = (
        _replacement_inputs()
    )
    first_staging = _read_json(FIRST_STAGING_PATH)
    second_staging = _read_json(SECOND_STAGING_PATH)
    first_payload = _read_json(FIRST_DECISIONS_PATH)
    second_payload = _read_json(SECOND_DECISIONS_PATH)
    identity_ref = str(first_payload.get("reviewer_identity_ref", ""))
    if identity_ref != second_payload.get("reviewer_identity_ref"):
        raise ValueError("replacement_decision_identity_mismatch")
    reviewer_name, trusted_refs, trusted_names = _reviewer(identity_ref)

    applied: dict[str, Workbench] = {}
    mappings: dict[str, list[dict[str, Any]]] = {}
    for indicator_id in INDICATORS:
        current = load_workbench(_workbench_path(indicator_id))
        rejected_drafts = [
            draft
            for draft in current.drafts
            if current.decisions.get(draft.case_id)
            and current.decisions[draft.case_id].action == "rejected"
        ]
        if len(rejected_drafts) != EXPECTED_REPLACEMENT_COUNTS[indicator_id]:
            raise ValueError(f"{indicator_id}:original_reject_count_changed")
        new_drafts = replacements[indicator_id]
        if len(new_drafts) != len(rejected_drafts):
            raise ValueError(f"{indicator_id}:replacement_count_mismatch")
        removed_ids = {draft.case_id for draft in rejected_drafts}
        kept_drafts = [draft for draft in current.drafts if draft.case_id not in removed_ids]
        kept_decisions = {
            case_id: decision
            for case_id, decision in current.decisions.items()
            if case_id not in removed_ids
        }
        mapping: list[dict[str, Any]] = []
        for rejected, replacement in zip(rejected_drafts, new_drafts, strict=True):
            item = decisions[replacement.case_id]
            choice = str(item["decision"])
            if choice == "REJECT":
                raise ValueError(f"replacement_case_rejected:{replacement.case_id}")
            decision = decide(
                draft=replacement,
                final_answer=list(item["final_answer"]),
                decided_by=reviewer_name,
                decided_at=str(item["decided_at"]),
                note=(
                    f"offline_replacement_review_choice:{choice}"
                    + (f"; {item['note']}" if item.get("note") else "")
                ),
                review_duration_seconds=float(item["review_duration_seconds"]),
                reviewer_identity_ref=identity_ref,
                trusted_reviewer_identity_refs=trusted_refs,
                trusted_reviewer_names=trusted_names,
            )
            kept_decisions[replacement.case_id] = decision
            mapping.append(
                {
                    "rejected_case_id": rejected.case_id,
                    "replacement_case_id": replacement.case_id,
                    "submitted_decision": choice,
                    "stored_action": decision.action,
                }
            )
        current.drafts = [*kept_drafts, *new_drafts]
        current.decisions = kept_decisions

        first_source = first_staging["responses"][indicator_id]["validated_record"]
        added_review_cases = replacement_reviews[indicator_id]
        if indicator_id == "KPI-1":
            first_ids = {
                case_id for case_id in added_review_cases if not case_id.startswith("kpi1-repl2-")
            }
            second_ids = set(added_review_cases) - first_ids
            current.ai_review = _merge_case_record(
                current.ai_review,
                removed_ids=removed_ids,
                added_cases={case_id: added_review_cases[case_id] for case_id in first_ids},
                source_record=first_source,
            )
            current.ai_review = _merge_case_record(
                current.ai_review,
                removed_ids=set(),
                added_cases={case_id: added_review_cases[case_id] for case_id in second_ids},
                source_record=second_staging["validated_record"],
            )
        else:
            current.ai_review = _merge_case_record(
                current.ai_review,
                removed_ids=removed_ids,
                added_cases=added_review_cases,
                source_record=(
                    first_staging["responses"][indicator_id]
                    .get("openai_second_opinion", {})
                    .get("validated_record", first_source)
                ),
            )
        if indicator_id == "KPI-4":
            primary_source = first_source
            current.primary_ai_draft = _merge_case_record(
                current.primary_ai_draft,
                removed_ids=removed_ids,
                added_cases=replacement_primaries[indicator_id]["cases"],
                source_record=primary_source,
            )
            bind_composite_packet_record(current.primary_ai_draft, current)
        bind_composite_packet_record(current.ai_review, current)
        current.batch_approval = None
        if len(current.drafts) != 100 or len(current.decisions) != 100:
            raise ValueError(f"{indicator_id}:applied_case_count_invalid")
        if len({draft.case_id for draft in current.drafts}) != 100:
            raise ValueError(f"{indicator_id}:applied_case_ids_not_unique")
        kept_prompts = {draft.prompt for draft in kept_drafts}
        replacement_prompts = {draft.prompt for draft in new_drafts}
        if len(replacement_prompts) != len(new_drafts):
            raise ValueError(f"{indicator_id}:replacement_prompts_not_unique")
        if kept_prompts & replacement_prompts:
            raise ValueError(f"{indicator_id}:replacement_prompt_reuses_kept_case")
        original_unique_prompt_count = len(
            {
                draft.prompt
                for draft in load_workbench(
                    _workbench_path(indicator_id)
                ).drafts
            }
        )
        if len({draft.prompt for draft in current.drafts}) < original_unique_prompt_count:
            raise ValueError(f"{indicator_id}:replacement_reduces_prompt_uniqueness")
        plan = build_adaptive_review_plan(current)
        if plan.get("status") != "READY_TO_SEAL":
            raise ValueError(
                f"{indicator_id}:replacement_application_not_seal_ready:"
                f"{plan.get('status')}:{plan.get('reason')}"
            )
        applied[indicator_id] = current
        mappings[indicator_id] = mapping

    report = {
        "schema_version": "kpi_replacement_application_v1",
        "status": "APPLIED_ALL_REPLACEMENTS",
        "reviewer_identity_ref": identity_ref,
        "qualification_stage": "pharmacist_candidate_preliminary_safety_review",
        "source_decision_sha256": {
            "first_round": first_payload["source_zip_sha256"],
            "second_round": second_payload["source_zip_sha256"],
        },
        "replacement_counts": EXPECTED_REPLACEMENT_COUNTS,
        "mappings": mappings,
        "workbench_case_counts": {indicator_id: 100 for indicator_id in INDICATORS},
        "rejected_case_count_after_application": 0,
    }
    return applied, report


def apply_all() -> dict[str, Any]:
    workbenches, report = build_applied_workbenches()
    paths = {_workbench_path(indicator_id) for indicator_id in INDICATORS}
    paths.add(REPORT_PATH)
    previous = {path: path.read_bytes() if path.is_file() else None for path in paths}
    try:
        for indicator_id, workbench in workbenches.items():
            save_workbench(_workbench_path(indicator_id), workbench)
        REPORT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        for path, content in previous.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        _, report = build_applied_workbenches()
        if args.apply:
            report = apply_all()
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
