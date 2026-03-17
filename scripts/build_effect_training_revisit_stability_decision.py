from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.effect_training_revisit_stability_decision import (
    build_effect_training_revisit_stability_decision,
    load_json_artifact,
    write_effect_training_revisit_stability_decision_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a decision artifact for whether the current replay-only evidence "
            "materially changes the existing defer-new-training decision."
        )
    )
    parser.add_argument(
        "--prior-revisit-decision",
        default="artifacts/reports/effect_training_revisit_decision_v1.json",
        help="Prior effect-training revisit decision JSON path",
    )
    parser.add_argument(
        "--baseline-candidate-summary",
        default="artifacts/reports/baseline_candidate_kpi_summary_v1.json",
        help="Baseline/candidate KPI summary JSON path",
    )
    parser.add_argument(
        "--replay-split-audit",
        default="artifacts/reports/policy_proxy_replay_split_audit_v1.json",
        help="Replay split audit JSON path",
    )
    parser.add_argument(
        "--non-cgm-diagnostic",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        help="Non-CGM threshold-cross diagnostic JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/effect_training_revisit_stability_decision_v1.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/effect_training_revisit_stability_decision_v1.md",
        help="Output markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = build_effect_training_revisit_stability_decision(
        prior_revisit_decision=load_json_artifact(args.prior_revisit_decision),
        prior_revisit_decision_path=args.prior_revisit_decision,
        baseline_candidate_summary=load_json_artifact(args.baseline_candidate_summary),
        baseline_candidate_summary_path=args.baseline_candidate_summary,
        replay_split_audit=load_json_artifact(args.replay_split_audit),
        replay_split_audit_path=args.replay_split_audit,
        non_cgm_diagnostic=load_json_artifact(args.non_cgm_diagnostic),
        non_cgm_diagnostic_path=args.non_cgm_diagnostic,
    )
    write_effect_training_revisit_stability_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
