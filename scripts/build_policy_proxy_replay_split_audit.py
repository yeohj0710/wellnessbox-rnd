from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.training.policy_proxy_replay_split_audit import (
    build_policy_proxy_replay_split_audit,
    load_effect_model_v1_artifact,
    load_json,
    write_policy_proxy_replay_split_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only calibrated-vs-neutralized candidate audit "
            "under the Dataset F supported/base-clone split"
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Synthetic longitudinal dataset path",
    )
    parser.add_argument(
        "--split-manifest",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        help="Candidate split manifest JSON path",
    )
    parser.add_argument(
        "--candidate-artifact",
        default="artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json",
        help="Candidate effect artifact path",
    )
    parser.add_argument(
        "--policy-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Policy artifact path for replay",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/policy_proxy_replay_split_audit_v1.json",
        help="Output audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/policy_proxy_replay_split_audit_v1.md",
        help="Output audit markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_policy_proxy_replay_split_audit(
        dataset_path=args.dataset,
        split_manifest=load_json(args.split_manifest),
        split_manifest_path=args.split_manifest,
        candidate_artifact=load_effect_model_v1_artifact(args.candidate_artifact),
        candidate_artifact_path=args.candidate_artifact,
        policy_artifact_path=args.policy_artifact,
    )
    write_policy_proxy_replay_split_audit_files(
        audit=audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
