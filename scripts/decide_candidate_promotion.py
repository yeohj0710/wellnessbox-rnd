"""Fail closed on safety regression, then record replace-or-keep with rollback.

Takes the baseline and candidate frozen-eval reports, the approved-draft
manifest, and the training gate status. Exits non-zero when any safety metric
gets worse, so a regression cannot pass silently.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

from wellnessbox_rnd.training.candidate_promotion import (
    build_candidate_promotion_decision_v1,
    evaluate_safety_regression_v1,
    write_json,
)

DEFAULT_MANIFEST = "data/original_plan/final_session/approved_draft_dataset_manifest_v1.json"
DEFAULT_DECISION = "data/original_plan/final_session/candidate_promotion_decision_v1.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--candidate-report", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--current-artifact", default=None)
    parser.add_argument("--dataset-manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--training-gate-status", default="no_go_keep_training_blocked")
    parser.add_argument("--decided-by", required=True, help="Named person making the call")
    parser.add_argument("--tolerance", type=float, default=0.0)
    parser.add_argument("--output", default=DEFAULT_DECISION)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    baseline = json.loads(Path(args.baseline_report).read_text(encoding="utf-8"))
    candidate = json.loads(Path(args.candidate_report).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.dataset_manifest).read_text(encoding="utf-8"))

    regression = evaluate_safety_regression_v1(baseline, candidate, tolerance=args.tolerance)
    decision = build_candidate_promotion_decision_v1(
        dataset_manifest=manifest,
        regression=regression,
        candidate_artifact_path=args.candidate_artifact,
        current_artifact_path=args.current_artifact,
        decided_at=datetime.now(UTC).isoformat(),
        decided_by=args.decided_by,
        training_gate_status=args.training_gate_status,
    )
    decision["safety_regression_detail"] = regression
    path = write_json(args.output, decision)

    print(json.dumps(
        {
            "decision": decision["decision"],
            "blockers": decision["blockers"],
            "regressed_metrics": regression["regressed_metrics"],
            "decision_path": str(path),
        },
        ensure_ascii=False,
        indent=2,
    ))
    if regression["safety_regressed"]:
        return 1
    return 0 if decision["decision"] == "replace_with_candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
