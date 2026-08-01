"""Draft an answer key from an independent source, then let a human decide each one.

Authoring 100 cases by hand for four indicators is 400 items, and nobody does
that well. The fix is not to let the engine grade itself — it is to separate the
two roles that were conflated:

  drafting   — anything may draft, as long as it is NOT the system under test
               and has not seen that system's output for the case
  deciding   — a named human accepts, edits or rejects each draft, and the
               record shows which of the three happened

That is ordinary assisted annotation. The measurement stays honest because the
draft comes from a different derivation path than the engine's optimizer, and
because the human's edits are counted rather than assumed.

A reviewer who accepts everything untouched produces a 0% edit rate. This module
reports that number instead of hiding it, so the record shows what the review
actually was.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2
from typing import Any, Literal

DRAFT_SCHEMA = "answer_key_draft_v1"
ADJUDICATION_SCHEMA = "answer_key_adjudication_v1"
SEAL_DISPOSAL_SCHEMA = "answer_key_seal_disposal_v1"
SEAL_DISPOSAL_HISTORY_SCHEMA = "answer_key_seal_disposal_history_v1"

# Sources that must never draft an answer key: they are the thing being scored.
FORBIDDEN_DRAFT_SOURCES = frozenset(
    {
        "recommendation_engine",
        "wellnessbox_rnd.orchestration.recommendation_service",
        "engine_output",
        "system_under_test",
    }
)

Action = Literal["accepted", "edited", "rejected", "pending"]


@dataclass
class CaseDraft:
    case_id: str
    prompt: str
    draft_answer: list[str]
    draft_source: str
    draft_rationale: str = ""
    drafting_agent: str = ""
    blinded_from: list[str] = field(default_factory=list)


@dataclass
class Decision:
    case_id: str
    action: Action
    final_answer: list[str]
    decided_by: str = ""
    decided_at: str = ""
    note: str = ""
    review_duration_seconds: float | None = None
    decision_mode: str = "detailed_review"
    reviewed_in_detail: bool = True


@dataclass
class Workbench:
    indicator_id: str
    drafts: list[CaseDraft]
    decisions: dict[str, Decision] = field(default_factory=dict)
    seal_disposals: list[dict[str, Any]] = field(default_factory=list)
    ai_review: dict[str, Any] = field(default_factory=dict)
    batch_approval: dict[str, Any] | None = None

    def pending(self) -> list[CaseDraft]:
        return [
            draft
            for draft in self.drafts
            if self.decisions.get(draft.case_id, Decision(draft.case_id, "pending", [])).action
            == "pending"
        ]


def assert_source_is_independent(draft_source: str) -> None:
    """Refuse a draft that came from the system being measured."""
    folded = draft_source.strip().casefold()
    if not folded:
        raise ValueError("draft_source_required")
    for forbidden in FORBIDDEN_DRAFT_SOURCES:
        if forbidden in folded:
            raise ValueError(f"draft_source_is_the_system_under_test:{draft_source}")


def build_drafts(
    *,
    indicator_id: str,
    cases: list[dict[str, Any]],
    draft_source: str,
    drafting_agent: str = "",
    blinded_from: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Package drafts with their provenance, before any engine has run."""
    assert_source_is_independent(draft_source)
    if not cases:
        raise ValueError("no_cases_to_draft")
    agent = drafting_agent.strip()
    blinded = sorted({str(path).strip() for path in blinded_from if str(path).strip()})

    drafts = []
    for case in cases:
        answer = sorted(set(case["draft_answer"]))
        if not answer:
            raise ValueError(f"draft_answer_is_empty:{case['case_id']}")
        drafts.append(
            {
                "case_id": str(case["case_id"]),
                "prompt": str(case.get("prompt", "")),
                "draft_answer": answer,
                "draft_source": draft_source,
                "draft_rationale": str(case.get("draft_rationale", "")),
                "drafting_agent": agent,
                "blinded_from": blinded,
            }
        )

    return {
        "schema_version": DRAFT_SCHEMA,
        "indicator_id": indicator_id,
        "draft_source": draft_source,
        "drafting_agent": agent,
        "blinded_from": blinded,
        "engine_output_consulted": False,
        "case_count": len(drafts),
        "drafts": drafts,
        "drafts_sha256": _digest([item["draft_answer"] for item in drafts]),
    }


def _digest(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def decide(
    *,
    draft: CaseDraft,
    final_answer: list[str] | None,
    decided_by: str,
    note: str = "",
    decided_at: str | None = None,
    review_duration_seconds: float | None = None,
    decision_mode: str = "detailed_review",
    reviewed_in_detail: bool = True,
) -> Decision:
    """Record one human decision. `None` means the case was rejected outright."""
    if not decided_by.strip():
        raise ValueError("decision_requires_a_named_person")
    if review_duration_seconds is not None and review_duration_seconds < 0:
        raise ValueError("review_duration_seconds_must_be_non_negative")
    stamp = decided_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")

    if final_answer is None:
        return Decision(
            draft.case_id,
            "rejected",
            [],
            decided_by.strip(),
            stamp,
            note,
            review_duration_seconds,
            decision_mode,
            reviewed_in_detail,
        )

    cleaned = sorted(set(final_answer))
    if not cleaned:
        raise ValueError(f"final_answer_is_empty:{draft.case_id}")
    action: Action = "accepted" if cleaned == sorted(set(draft.draft_answer)) else "edited"
    return Decision(
        draft.case_id,
        action,
        cleaned,
        decided_by.strip(),
        stamp,
        note,
        review_duration_seconds,
        decision_mode,
        reviewed_in_detail,
    )


def summarise_adjudication(workbench: Workbench) -> dict[str, Any]:
    """Report what the review actually consisted of, including the edit rate."""
    decisions = [workbench.decisions[draft.case_id]
                 for draft in workbench.drafts
                 if draft.case_id in workbench.decisions]
    counts = {"accepted": 0, "edited": 0, "rejected": 0, "pending": 0}
    for decision in decisions:
        counts[decision.action] += 1
    counts["pending"] = len(workbench.drafts) - len(decisions)

    settled = counts["accepted"] + counts["edited"]
    edit_rate = round(100.0 * counts["edited"] / settled, 2) if settled else 0.0
    detailed = [decision for decision in decisions if decision.reviewed_in_detail]
    detailed_settled = [
        decision
        for decision in detailed
        if decision.action in {"accepted", "edited"}
    ]
    detailed_edited = sum(
        decision.action == "edited" for decision in detailed_settled
    )
    detailed_edit_rate = (
        round(100.0 * detailed_edited / len(detailed_settled), 2)
        if detailed_settled
        else 0.0
    )
    reviewers = sorted({d.decided_by for d in decisions if d.decided_by})

    warnings: list[str] = []
    if settled and counts["edited"] == 0:
        warnings.append("edit_rate_zero_every_draft_was_accepted_unchanged")
    if len(reviewers) > 1:
        warnings.append("multiple_reviewers_recorded")

    return {
        "schema_version": ADJUDICATION_SCHEMA,
        "indicator_id": workbench.indicator_id,
        "case_count": len(workbench.drafts),
        "counts": counts,
        "settled_count": settled,
        "edit_rate_pct": edit_rate,
        "detailed_review_count": len(detailed),
        "batch_approved_count": sum(
            not decision.reviewed_in_detail for decision in decisions
        ),
        "detailed_edit_rate_pct": detailed_edit_rate,
        "reviewers": reviewers,
        "warnings": warnings,
        "complete": counts["pending"] == 0,
    }


def adjudicated_answer_key(workbench: Workbench) -> dict[str, list[str]]:
    """The final answer key: settled cases only, rejected ones dropped."""
    key: dict[str, list[str]] = {}
    for draft in workbench.drafts:
        decision = workbench.decisions.get(draft.case_id)
        if decision is None or decision.action in {"pending", "rejected"}:
            continue
        key[draft.case_id] = decision.final_answer
    return key


def _agent_family(agent: str) -> str:
    """Normalize common agent names to the model-provider family being tested."""
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


def build_provenance(
    workbench: Workbench,
    summary: dict[str, Any],
    *,
    system_under_test_agent: str = "",
) -> dict[str, Any]:
    """Provenance that travels with the seal so the method stays auditable."""
    drafting_agents = {draft.drafting_agent.strip() for draft in workbench.drafts}
    blinded_sets = {
        tuple(sorted(set(draft.blinded_from))) for draft in workbench.drafts
    }
    if len(drafting_agents) > 1:
        raise ValueError("inconsistent_drafting_agent_across_cases")
    if len(blinded_sets) > 1:
        raise ValueError("inconsistent_blinded_from_across_cases")
    drafting_agent = next(iter(drafting_agents), "")
    blinded_from = list(next(iter(blinded_sets), ()))
    evaluated_agent = system_under_test_agent.strip()
    drafting_family = _agent_family(drafting_agent)
    evaluated_family = _agent_family(evaluated_agent)
    separation_required = workbench.indicator_id == "KPI-4"
    separated = bool(
        drafting_family
        and evaluated_family
        and drafting_family != evaluated_family
    )
    if separation_required and not drafting_agent:
        raise ValueError("kpi4_drafting_agent_required")
    if separation_required and not evaluated_agent:
        raise ValueError("kpi4_system_under_test_agent_required")
    if separation_required and not separated:
        raise ValueError("kpi4_drafting_agent_matches_system_under_test_agent")

    return {
        "answer_key_method": "independent_draft_then_human_adjudication",
        "draft_source": workbench.drafts[0].draft_source if workbench.drafts else None,
        "drafting_agent": drafting_agent or None,
        "blinded_from": blinded_from,
        "engine_output_consulted_before_sealing": False,
        "prior_seal_disposals": list(workbench.seal_disposals),
        "agent_separation": {
            "required": separation_required,
            "system_under_test_agent": evaluated_agent or None,
            "drafting_agent_family": drafting_family or None,
            "system_under_test_agent_family": evaluated_family or None,
            "separated": separated if separation_required else None,
        },
        "adjudication": {
            "counts": summary["counts"],
            "edit_rate_pct": summary["edit_rate_pct"],
            "reviewers": summary["reviewers"],
            "warnings": summary["warnings"],
        },
        "note": (
            "초안은 측정 대상 엔진이 아닌 독립 출처가 만들었고, 각 건을 사람이 "
            "수락·수정·반려로 확정했다. 수정률은 숨기지 않고 함께 기록한다."
        ),
    }


def build_seal_disposal_record(
    *,
    indicator_id: str,
    seal_sha256: str,
    discarded_by: str,
    reason: str,
    original_seal_path: str,
    archived_seal_path: str,
    archived_workbench_path: str,
    discarded_at: str | None = None,
) -> dict[str, Any]:
    """Build the append-only event that explains why an active seal was retired."""
    actor = discarded_by.strip()
    explanation = reason.strip()
    if not actor:
        raise ValueError("seal_disposal_requires_a_named_person")
    if not explanation:
        raise ValueError("seal_disposal_requires_a_reason")
    if not seal_sha256.strip():
        raise ValueError("seal_disposal_requires_seal_sha256")

    return {
        "schema_version": SEAL_DISPOSAL_SCHEMA,
        "indicator_id": indicator_id,
        "discarded_seal_sha256": seal_sha256,
        "discarded_by": actor,
        "discarded_at": (
            discarded_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        ),
        "reason": explanation,
        "original_seal_path": original_seal_path,
        "archived_seal_path": archived_seal_path,
        "archived_workbench_path": archived_workbench_path,
        "review_required_before_resealing": True,
    }


def _record_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def discard_seal_with_audit_trail(
    *,
    active_seal_path: Path,
    workbench_path: Path,
    history_path: Path,
    archive_dir: Path,
    record_root: Path,
    discarded_by: str,
    reason: str,
    discarded_at: str | None = None,
) -> dict[str, Any]:
    """Archive a seal and its decisions, then reset review with rollback on failure."""
    active = Path(active_seal_path)
    bench_path = Path(workbench_path)
    history = Path(history_path)
    archive = Path(archive_dir)
    if not active.is_file():
        raise FileNotFoundError(f"active_seal_missing:{active}")
    if not bench_path.is_file():
        raise FileNotFoundError(f"workbench_missing:{bench_path}")

    seal = json.loads(active.read_text(encoding="utf-8"))
    indicator_id = str(seal.get("indicator_id", "")).strip()
    seal_sha256 = str(seal.get("seal_sha256", "")).strip()
    if not indicator_id:
        raise ValueError("active_seal_indicator_missing")
    if not seal_sha256:
        raise ValueError("active_seal_sha256_missing")

    slug = indicator_id.lower().replace("-", "")
    archived_seal = archive / "seals" / f"{slug}_reference_seal_{seal_sha256}.json"
    archived_workbench = (
        archive / "workbenches" / f"{slug}_workbench_{seal_sha256}.json"
    )
    if archived_seal.exists() or archived_workbench.exists():
        raise FileExistsError(f"seal_disposal_archive_exists:{seal_sha256}")

    record = build_seal_disposal_record(
        indicator_id=indicator_id,
        seal_sha256=seal_sha256,
        discarded_by=discarded_by,
        reason=reason,
        original_seal_path=_record_path(active, record_root),
        archived_seal_path=_record_path(archived_seal, record_root),
        archived_workbench_path=_record_path(archived_workbench, record_root),
        discarded_at=discarded_at,
    )
    previous_history = history.read_bytes() if history.is_file() else None
    previous_workbench = bench_path.read_bytes()
    workbench = load_workbench(bench_path)
    if workbench.indicator_id != indicator_id:
        raise ValueError(
            f"seal_workbench_indicator_mismatch:{indicator_id}:{workbench.indicator_id}"
        )

    history_payload = (
        json.loads(previous_history.decode("utf-8"))
        if previous_history is not None
        else {
            "schema_version": SEAL_DISPOSAL_HISTORY_SCHEMA,
            "indicator_id": indicator_id,
            "events": [],
        }
    )
    if history_payload.get("indicator_id") != indicator_id:
        raise ValueError("seal_disposal_history_indicator_mismatch")
    history_payload.setdefault("events", []).append(record)

    archived_seal.parent.mkdir(parents=True, exist_ok=True)
    archived_workbench.parent.mkdir(parents=True, exist_ok=True)
    history.parent.mkdir(parents=True, exist_ok=True)
    try:
        active.replace(archived_seal)
        copy2(bench_path, archived_workbench)
        workbench.decisions = {}
        workbench.seal_disposals.append(record)
        save_workbench(bench_path, workbench)
        history.write_text(
            json.dumps(history_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        bench_path.write_bytes(previous_workbench)
        if previous_history is None:
            history.unlink(missing_ok=True)
        else:
            history.write_bytes(previous_history)
        if archived_seal.is_file() and not active.exists():
            archived_seal.replace(active)
        archived_workbench.unlink(missing_ok=True)
        raise

    return record


def load_workbench(path: Path) -> Workbench:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    drafts = [CaseDraft(**item) for item in payload["drafts"]]
    decisions = {
        case_id: Decision(**item)
        for case_id, item in payload.get("decisions", {}).items()
    }
    return Workbench(
        payload["indicator_id"],
        drafts,
        decisions,
        list(payload.get("seal_disposals", [])),
        dict(payload.get("ai_review", {})),
        payload.get("batch_approval"),
    )


def save_workbench(path: Path, workbench: Workbench) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": DRAFT_SCHEMA,
        "indicator_id": workbench.indicator_id,
        "drafts": [vars(draft) for draft in workbench.drafts],
        "decisions": {case_id: vars(value) for case_id, value in workbench.decisions.items()},
        "seal_disposals": list(workbench.seal_disposals),
        "ai_review": dict(workbench.ai_review),
        "batch_approval": workbench.batch_approval,
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target
