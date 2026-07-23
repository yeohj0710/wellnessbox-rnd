from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from wellnessbox_rnd.interim.next_action import decide_next_action
from wellnessbox_rnd.interim.workflow_contract import ClosedLoopState

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/original_plan/closed_loop_next_action_scenarios_v1.json"
DEFAULT_EVIDENCE = (
    ROOT / "data/original_plan/evidence/op071_op080_closed_loop_next_action_policy_v1.json"
)


def _templates() -> list[tuple[str, dict[str, object], str]]:
    common = {
        "adverse_event": False,
        "ingredient_intolerance": False,
        "dose_related_issue": False,
        "safety_review_required": False,
        "followup_submitted": True,
        "measurement_complete": True,
        "ambiguous": False,
        "score_delta": 1.0,
    }
    return [
        ("adverse", common | {"adverse_event": True}, "stop_and_escalate"),
        ("intolerance", common | {"ingredient_intolerance": True}, "replace"),
        ("dose", common | {"dose_related_issue": True}, "reduce"),
        ("safety", common | {"safety_review_required": True}, "request_safety_review"),
        ("followup", common | {"followup_submitted": False}, "request_followup"),
        ("measurement", common | {"measurement_complete": False}, "request_measurement"),
        ("ambiguous", common | {"ambiguous": True}, "hold_for_review"),
        ("improved", common | {"score_delta": 0.01}, "maintain"),
        ("unchanged", common | {"score_delta": 0.0}, "reoptimize"),
        ("worsened", common | {"score_delta": -0.01}, "reoptimize"),
    ]


def build_cases() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for template_name, event, expected in _templates():
        for variant in range(13):
            varied = event | {
                "days_since_start": 7 + variant,
                "risk_tier": ("low", "moderate", "high")[variant % 3],
                "case_variant": variant,
            }
            cases.append(
                {
                    "case_id": f"NA-{template_name}-{variant + 1:02d}",
                    "state": "FOLLOWUP_ACTIVE",
                    "event": varied,
                    "expected_action": expected,
                }
            )
    return cases


def evaluate(cases: list[dict[str, object]]) -> dict[str, object]:
    rows = []
    correct = 0
    for case in cases:
        decision = decide_next_action(
            state=ClosedLoopState(str(case["state"])),
            event=dict(case["event"]),
        )
        matched = decision.action.value == case["expected_action"]
        correct += int(matched)
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_action": case["expected_action"],
                "actual_action": decision.action.value,
                "rule_id": decision.rule_id,
                "correct": matched,
            }
        )
    accuracy = 100.0 * correct / len(cases)
    return {
        "schema_version": "closed_loop_next_action_policy_evidence_v1",
        "case_count": len(cases),
        "correct_count": correct,
        "next_action_accuracy_pct": accuracy,
        "target_accuracy_pct": 80.0,
        "passed": len(cases) >= 100 and accuracy >= 80.0,
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    cases = build_cases()
    dataset = {
        "schema_version": "closed_loop_next_action_scenarios_v1",
        "source": "docs/context/master_context.md#15.3",
        "case_count": len(cases),
        "cases": cases,
    }
    serialized = json.dumps(dataset, ensure_ascii=False, indent=2) + "\n"
    args.cases.parent.mkdir(parents=True, exist_ok=True)
    args.cases.write_text(serialized, encoding="utf-8")
    evidence = evaluate(cases) | {
        "dataset_path": args.cases.relative_to(ROOT).as_posix(),
        "dataset_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "policy_path": "data/original_plan/closed_loop_next_action_policy_v1.json",
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary_keys = ("case_count", "correct_count", "next_action_accuracy_pct", "passed")
    print(json.dumps({key: evidence[key] for key in summary_keys}))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
