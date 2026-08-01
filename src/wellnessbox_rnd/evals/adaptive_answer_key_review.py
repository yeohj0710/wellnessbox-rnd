"""Reduce detailed human review without pretending AI approval was human review.

Every measured case still receives two answers from different provider-family
agents. A person reviews disagreements, risk flags, and a deterministic sample
of agreements. The remaining agreements may be accepted only through a later,
explicit human batch approval recorded separately from detailed review.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wellnessbox_rnd.evals.answer_key_workbench import Workbench

AI_REVIEW_SCHEMA = "independent_ai_answer_review_v1"
AI_REVIEW_PACKET_SCHEMA = "blind_ai_answer_review_packet_v1"
INITIAL_AGREEMENT_SAMPLE = 5
EXPANDED_AGREEMENT_SAMPLE = 20
MIN_AI_CONFIDENCE = 0.8
KPI3_ACTION_VOCABULARY = (
    "hold_for_review",
    "maintain",
    "reduce",
    "replace",
    "reoptimize",
    "request_followup",
    "request_measurement",
    "request_safety_review",
    "stop_and_escalate",
)


def agent_family(agent: str) -> str:
    """Normalize familiar agent names to their model-provider family."""
    folded = agent.strip().casefold()
    families = {
        "openai": ("openai", "chatgpt", "codex", "gpt-", "o1", "o3", "o4"),
        "anthropic": ("anthropic", "claude"),
        "google": ("google", "gemini", "bard"),
        "meta": ("meta", "llama"),
        "human": ("human", "사람"),
    }
    for family, markers in families.items():
        if any(marker in folded for marker in markers):
            return family
    return folded


def _clean_answer(value: Any, *, case_id: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"ai_review_answer_must_be_a_list:{case_id}")
    answer = sorted({str(item).strip() for item in value if str(item).strip()})
    if not answer:
        raise ValueError(f"ai_review_answer_is_empty:{case_id}")
    return answer


def _review_digest(cases: dict[str, dict[str, Any]]) -> str:
    canonical = json.dumps(
        cases,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _payload_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_blind_ai_review_packet(
    workbench: Workbench,
    *,
    required_blinded_from: list[str],
) -> dict[str, Any]:
    """Export questions without the primary answers, rationale or engine data."""
    blinded = sorted(
        {
            str(path).strip()
            for path in required_blinded_from
            if str(path).strip()
        }
    )
    if not blinded:
        raise ValueError("ai_review_required_blinded_from_missing")
    cases = [
        {"case_id": draft.case_id, "prompt": draft.prompt}
        for draft in sorted(workbench.drafts, key=lambda item: item.case_id)
    ]
    vocabulary = (
        list(KPI3_ACTION_VOCABULARY)
        if workbench.indicator_id == "KPI-3"
        else sorted(
            {
                token
                for draft in workbench.drafts
                for token in draft.draft_answer
                if token.strip()
            }
        )
    )
    payload = {
        "schema_version": AI_REVIEW_PACKET_SCHEMA,
        "indicator_id": workbench.indicator_id,
        "case_count": len(cases),
        "answer_vocabulary": vocabulary,
        "required_blinded_from": blinded,
        "omitted_fields": [
            "draft_answer",
            "draft_rationale",
            "engine_logic",
            "engine_output",
        ],
        "instructions": (
            "각 사례를 독립적으로 판단해 proposed_answer, confidence, flags, "
            "rationale을 반환한다. 1차 초안·근거·엔진 입력·엔진 출력은 보지 않는다."
        ),
        "cases": cases,
    }
    return {**payload, "packet_sha256": _payload_digest(payload)}


def register_independent_ai_review(
    workbench: Workbench,
    *,
    reviewing_agent: str,
    review_source: str,
    blinded_from: list[str],
    required_blinded_from: list[str],
    packet_sha256: str,
    engine_output_consulted: bool,
    cases: list[dict[str, Any]],
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Validate and attach a complete blind second opinion."""
    reviewer = reviewing_agent.strip()
    if not reviewer:
        raise ValueError("ai_reviewing_agent_required")
    source = review_source.strip()
    if not source:
        raise ValueError("ai_review_source_required")
    from wellnessbox_rnd.evals.answer_key_workbench import (
        assert_source_is_independent,
    )

    assert_source_is_independent(source)
    if engine_output_consulted:
        raise ValueError("ai_review_consulted_engine_output")
    required = sorted(
        {
            str(path).strip()
            for path in required_blinded_from
            if str(path).strip()
        }
    )
    expected_packet = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=required,
    )
    if packet_sha256.strip() != expected_packet["packet_sha256"]:
        raise ValueError("ai_review_packet_sha256_mismatch")
    blind_paths = sorted({str(path).strip() for path in blinded_from if str(path).strip()})
    if not blind_paths:
        raise ValueError("ai_review_blinded_from_required")
    missing_blind_paths = sorted(set(required) - set(blind_paths))
    if missing_blind_paths:
        raise ValueError(
            "ai_review_missing_blinded_paths:" + ",".join(missing_blind_paths)
        )

    drafting_agents = {draft.drafting_agent.strip() for draft in workbench.drafts}
    if len(drafting_agents) != 1 or not next(iter(drafting_agents), ""):
        raise ValueError("one_drafting_agent_required_for_ai_review")
    drafting_agent = next(iter(drafting_agents))
    if agent_family(drafting_agent) == agent_family(reviewer):
        raise ValueError("ai_review_agent_matches_drafting_agent_family")

    expected_ids = {draft.case_id for draft in workbench.drafts}
    received: dict[str, dict[str, Any]] = {}
    for item in cases:
        case_id = str(item.get("case_id", "")).strip()
        if not case_id:
            raise ValueError("ai_review_case_id_required")
        if case_id in received:
            raise ValueError(f"duplicate_ai_review_case:{case_id}")
        try:
            confidence = float(item.get("confidence"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"ai_review_confidence_invalid:{case_id}") from exc
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"ai_review_confidence_out_of_range:{case_id}")
        raw_flags = item.get("flags", [])
        if not isinstance(raw_flags, list):
            raise ValueError(f"ai_review_flags_must_be_a_list:{case_id}")
        received[case_id] = {
            "proposed_answer": _clean_answer(
                item.get("proposed_answer"),
                case_id=case_id,
            ),
            "confidence": confidence,
            "flags": sorted(
                {str(flag).strip() for flag in raw_flags if str(flag).strip()}
            ),
        }

    received_ids = set(received)
    if received_ids != expected_ids:
        missing = sorted(expected_ids - received_ids)
        extra = sorted(received_ids - expected_ids)
        raise ValueError(
            "ai_review_case_set_mismatch:"
            f"missing={','.join(missing)}:extra={','.join(extra)}"
        )

    review = {
        "schema_version": AI_REVIEW_SCHEMA,
        "reviewing_agent": reviewer,
        "reviewing_agent_family": agent_family(reviewer),
        "drafting_agent": drafting_agent,
        "drafting_agent_family": agent_family(drafting_agent),
        "review_source": source,
        "blinded_from": blind_paths,
        "required_blinded_from": required,
        "packet_sha256": packet_sha256.strip(),
        "engine_output_consulted": False,
        "reviewed_at": (
            reviewed_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        ),
        "case_count": len(received),
        "cases": received,
        "cases_sha256": _review_digest(received),
    }
    workbench.ai_review = review
    workbench.batch_approval = None
    return review


def _sample(indicator_id: str, case_ids: list[str], count: int) -> list[str]:
    ranked = sorted(
        case_ids,
        key=lambda case_id: hashlib.sha256(
            f"{indicator_id}:{case_id}".encode()
        ).hexdigest(),
    )
    return ranked[: min(count, len(ranked))]


def _is_detailed_decision(decision: Any) -> bool:
    return bool(
        decision is not None
        and decision.action in {"accepted", "edited", "rejected"}
        and getattr(decision, "reviewed_in_detail", True)
    )


def _sample_corrections(
    workbench: Workbench,
    sample_ids: list[str],
    review_cases: dict[str, dict[str, Any]],
) -> list[str]:
    corrected: list[str] = []
    for case_id in sample_ids:
        decision = workbench.decisions.get(case_id)
        if not _is_detailed_decision(decision):
            continue
        agreed_answer = review_cases[case_id]["proposed_answer"]
        if decision.action == "rejected" or sorted(decision.final_answer) != agreed_answer:
            corrected.append(case_id)
    return sorted(corrected)


def build_adaptive_review_plan(workbench: Workbench) -> dict[str, Any]:
    """Return the smallest honest detailed-review set for the current evidence."""
    review = getattr(workbench, "ai_review", {}) or {}
    review_cases = review.get("cases", {})
    draft_by_id = {draft.case_id: draft for draft in workbench.drafts}
    if set(review_cases) != set(draft_by_id):
        return {
            "status": "BLOCKED",
            "reason": "complete_independent_ai_review_required",
            "case_count": len(draft_by_id),
            "ai_review_case_count": len(review_cases),
        }

    agreement_ids: list[str] = []
    disagreement_ids: list[str] = []
    flagged_ids: list[str] = []
    for case_id, draft in draft_by_id.items():
        item = review_cases[case_id]
        proposed = sorted(item.get("proposed_answer", []))
        if proposed == sorted(draft.draft_answer):
            agreement_ids.append(case_id)
        else:
            disagreement_ids.append(case_id)
        if item.get("flags") or float(item.get("confidence", 0.0)) < MIN_AI_CONFIDENCE:
            flagged_ids.append(case_id)

    sample_pool = sorted(set(agreement_ids) - set(flagged_ids))
    initial_sample = _sample(
        workbench.indicator_id,
        sample_pool,
        INITIAL_AGREEMENT_SAMPLE,
    )
    corrected = _sample_corrections(workbench, initial_sample, review_cases)
    escalation = "initial_sample"
    sample_target = INITIAL_AGREEMENT_SAMPLE
    sampled = initial_sample

    if len(corrected) >= 2:
        escalation = "full_agreement_review"
        sample_target = len(sample_pool)
        sampled = sample_pool
    elif len(corrected) == 1:
        escalation = "expanded_sample"
        sample_target = EXPANDED_AGREEMENT_SAMPLE
        sampled = _sample(
            workbench.indicator_id,
            sample_pool,
            EXPANDED_AGREEMENT_SAMPLE,
        )
        corrected = _sample_corrections(workbench, sampled, review_cases)
        if len(corrected) >= 2:
            escalation = "full_agreement_review"
            sample_target = len(sample_pool)
            sampled = sample_pool
            corrected = _sample_corrections(workbench, sampled, review_cases)

    required = sorted(set(disagreement_ids) | set(flagged_ids) | set(sampled))
    pending = [
        case_id
        for case_id in required
        if not _is_detailed_decision(workbench.decisions.get(case_id))
    ]
    rejected = [
        case_id
        for case_id in required
        if (
            (decision := workbench.decisions.get(case_id)) is not None
            and decision.action == "rejected"
        )
    ]
    batch_eligible = sorted(
        set(agreement_ids)
        - set(required)
        - set(workbench.decisions)
    )
    if pending:
        status = "REVIEW_REQUIRED"
        reason = "required_detailed_review_pending"
    elif rejected:
        status = "BLOCKED"
        reason = "rejected_cases_require_replacement"
    elif batch_eligible:
        status = "READY_FOR_BATCH_APPROVAL"
        reason = ""
    else:
        status = "READY_TO_SEAL"
        reason = ""

    return {
        "status": status,
        "reason": reason,
        "case_count": len(draft_by_id),
        "agreement_count": len(agreement_ids),
        "disagreement_count": len(disagreement_ids),
        "flagged_count": len(flagged_ids),
        "disagreement_ids": sorted(disagreement_ids),
        "flagged_ids": sorted(flagged_ids),
        "sample_target_count": min(sample_target, len(sample_pool)),
        "sampled_agreement_ids": sampled,
        "sample_correction_count": len(corrected),
        "sample_correction_ids": corrected,
        "escalation": escalation,
        "required_detail_ids": required,
        "pending_required_detail_ids": pending,
        "rejected_ids": sorted(rejected),
        "batch_eligible_ids": batch_eligible,
        "detailed_review_count": sum(
            1 for decision in workbench.decisions.values() if _is_detailed_decision(decision)
        ),
    }


def approve_consensus_batch(
    workbench: Workbench,
    *,
    approved_by: str,
    confirmation: str,
    approved_at: str | None = None,
) -> dict[str, Any]:
    """Turn untouched AI agreements into explicit, non-detailed human decisions."""
    approver = approved_by.strip()
    if not approver:
        raise ValueError("consensus_batch_approver_required")
    expected_confirmation = f"{workbench.indicator_id} AI 합의안 일괄 승인"
    if confirmation.strip() != expected_confirmation:
        raise ValueError("consensus_batch_confirmation_mismatch")

    plan = build_adaptive_review_plan(workbench)
    if plan["status"] != "READY_FOR_BATCH_APPROVAL":
        raise ValueError(plan.get("reason") or "consensus_batch_not_ready")
    detailed_reviewers = {
        decision.decided_by
        for decision in workbench.decisions.values()
        if _is_detailed_decision(decision) and decision.decided_by
    }
    if detailed_reviewers and detailed_reviewers != {approver}:
        raise ValueError("batch_approver_must_match_detailed_reviewer")

    from wellnessbox_rnd.evals.answer_key_workbench import Decision

    stamp = approved_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    draft_by_id = {draft.case_id: draft for draft in workbench.drafts}
    batch_ids = list(plan["batch_eligible_ids"])
    for case_id in batch_ids:
        draft = draft_by_id[case_id]
        workbench.decisions[case_id] = Decision(
            case_id=case_id,
            action="accepted",
            final_answer=sorted(set(draft.draft_answer)),
            decided_by=approver,
            decided_at=stamp,
            note="AI 합의안 일괄 승인; 개별 상세 검토 아님",
            review_duration_seconds=None,
            decision_mode="ai_consensus_batch_approval",
            reviewed_in_detail=False,
        )

    review = workbench.ai_review
    approval = {
        "schema_version": "ai_consensus_batch_approval_v1",
        "indicator_id": workbench.indicator_id,
        "approved_by": approver,
        "approved_at": stamp,
        "confirmation": expected_confirmation,
        "ai_review_cases_sha256": review.get("cases_sha256"),
        "packet_sha256": review.get("packet_sha256"),
        "required_detail_ids": list(plan["required_detail_ids"]),
        "sampled_agreement_ids": list(plan["sampled_agreement_ids"]),
        "sample_correction_count": plan["sample_correction_count"],
        "batch_approved_ids": batch_ids,
        "batch_approved_count": len(batch_ids),
    }
    workbench.batch_approval = approval
    return approval


def audit_adaptive_review(
    workbench: Workbench,
    *,
    required_blinded_from: list[str],
) -> dict[str, Any]:
    """Fail closed when a claimed AI-consensus approval is stale or incomplete."""
    review = workbench.ai_review or {}
    if not review:
        if any(
            not decision.reviewed_in_detail
            or decision.decision_mode == "ai_consensus_batch_approval"
            for decision in workbench.decisions.values()
        ):
            return {
                "used": False,
                "verdict": "FAIL",
                "reason": "batch_decision_without_ai_review",
                "batch_approved_count": 0,
            }
        return {
            "used": False,
            "verdict": "PASS",
            "reason": "",
            "batch_approved_count": 0,
        }

    def fail(reason: str) -> dict[str, Any]:
        return {
            "used": True,
            "verdict": "FAIL",
            "reason": reason,
            "batch_approved_count": sum(
                not decision.reviewed_in_detail
                for decision in workbench.decisions.values()
            ),
        }

    required = sorted(
        {
            str(path).strip()
            for path in required_blinded_from
            if str(path).strip()
        }
    )
    if review.get("engine_output_consulted") is not False:
        return fail("ai_review_engine_output_boundary_invalid")
    missing = sorted(set(required) - set(review.get("blinded_from", [])))
    if missing:
        return fail("ai_review_missing_blinded_paths:" + ",".join(missing))
    expected_packet = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=required,
    )
    if review.get("packet_sha256") != expected_packet["packet_sha256"]:
        return fail("ai_review_packet_sha256_mismatch")
    review_cases = review.get("cases", {})
    if set(review_cases) != {draft.case_id for draft in workbench.drafts}:
        return fail("complete_independent_ai_review_required")
    if review.get("cases_sha256") != _review_digest(review_cases):
        return fail("ai_review_cases_digest_mismatch")
    if agent_family(review.get("reviewing_agent", "")) == agent_family(
        review.get("drafting_agent", "")
    ):
        return fail("ai_review_agent_matches_drafting_agent_family")

    plan = build_adaptive_review_plan(workbench)
    if any(
        (
            decision.decision_mode == "ai_consensus_batch_approval"
            and decision.reviewed_in_detail
        )
        or (
            decision.decision_mode != "ai_consensus_batch_approval"
            and not decision.reviewed_in_detail
        )
        for decision in workbench.decisions.values()
    ):
        return fail("decision_mode_detail_flag_mismatch")
    batch_decisions = {
        case_id: decision
        for case_id, decision in workbench.decisions.items()
        if not decision.reviewed_in_detail
    }
    if not batch_decisions:
        return {
            "used": True,
            "verdict": "PASS",
            "reason": "",
            "reviewing_agent": review.get("reviewing_agent"),
            "agreement_count": plan.get("agreement_count", 0),
            "disagreement_count": plan.get("disagreement_count", 0),
            "required_detail_count": len(plan.get("required_detail_ids", [])),
            "batch_approved_count": 0,
        }

    approval = workbench.batch_approval or {}
    if approval.get("ai_review_cases_sha256") != review.get("cases_sha256"):
        return fail("batch_approval_ai_review_digest_mismatch")
    if approval.get("packet_sha256") != review.get("packet_sha256"):
        return fail("batch_approval_packet_digest_mismatch")
    if set(approval.get("batch_approved_ids", [])) != set(batch_decisions):
        return fail("batch_approval_case_set_mismatch")
    if plan.get("status") != "READY_TO_SEAL":
        return fail("adaptive_review_not_ready_to_seal")
    if set(approval.get("required_detail_ids", [])) != set(
        plan.get("required_detail_ids", [])
    ):
        return fail("batch_approval_required_detail_set_mismatch")

    draft_by_id = {draft.case_id: draft for draft in workbench.drafts}
    approver = approval.get("approved_by")
    for case_id, decision in batch_decisions.items():
        if (
            decision.action != "accepted"
            or decision.decision_mode != "ai_consensus_batch_approval"
            or decision.decided_by != approver
            or sorted(decision.final_answer)
            != sorted(draft_by_id[case_id].draft_answer)
        ):
            return fail(f"batch_decision_invalid:{case_id}")

    return {
        "used": True,
        "verdict": "PASS",
        "reason": "",
        "reviewing_agent": review.get("reviewing_agent"),
        "agreement_count": plan["agreement_count"],
        "disagreement_count": plan["disagreement_count"],
        "required_detail_count": len(plan["required_detail_ids"]),
        "batch_approved_count": len(batch_decisions),
        "escalation": plan["escalation"],
    }
