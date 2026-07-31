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
from typing import Any, Literal

DRAFT_SCHEMA = "answer_key_draft_v1"
ADJUDICATION_SCHEMA = "answer_key_adjudication_v1"

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


@dataclass
class Decision:
    case_id: str
    action: Action
    final_answer: list[str]
    decided_by: str = ""
    decided_at: str = ""
    note: str = ""


@dataclass
class Workbench:
    indicator_id: str
    drafts: list[CaseDraft]
    decisions: dict[str, Decision] = field(default_factory=dict)

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
) -> dict[str, Any]:
    """Package drafts with their provenance, before any engine has run."""
    assert_source_is_independent(draft_source)
    if not cases:
        raise ValueError("no_cases_to_draft")

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
            }
        )

    return {
        "schema_version": DRAFT_SCHEMA,
        "indicator_id": indicator_id,
        "draft_source": draft_source,
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
) -> Decision:
    """Record one human decision. `None` means the case was rejected outright."""
    if not decided_by.strip():
        raise ValueError("decision_requires_a_named_person")
    stamp = decided_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")

    if final_answer is None:
        return Decision(draft.case_id, "rejected", [], decided_by.strip(), stamp, note)

    cleaned = sorted(set(final_answer))
    if not cleaned:
        raise ValueError(f"final_answer_is_empty:{draft.case_id}")
    action: Action = "accepted" if cleaned == sorted(set(draft.draft_answer)) else "edited"
    return Decision(draft.case_id, action, cleaned, decided_by.strip(), stamp, note)


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


def build_provenance(workbench: Workbench, summary: dict[str, Any]) -> dict[str, Any]:
    """Provenance that travels with the seal so the method stays auditable."""
    return {
        "answer_key_method": "independent_draft_then_human_adjudication",
        "draft_source": workbench.drafts[0].draft_source if workbench.drafts else None,
        "engine_output_consulted_before_sealing": False,
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


def load_workbench(path: Path) -> Workbench:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    drafts = [CaseDraft(**item) for item in payload["drafts"]]
    decisions = {
        case_id: Decision(**item)
        for case_id, item in payload.get("decisions", {}).items()
    }
    return Workbench(payload["indicator_id"], drafts, decisions)


def save_workbench(path: Path, workbench: Workbench) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": DRAFT_SCHEMA,
        "indicator_id": workbench.indicator_id,
        "drafts": [vars(draft) for draft in workbench.drafts],
        "decisions": {case_id: vars(value) for case_id, value in workbench.decisions.items()},
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target
