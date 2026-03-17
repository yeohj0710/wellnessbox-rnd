from __future__ import annotations

import argparse

from wellnessbox_rnd.evals.effect_training_revisit_freshness_audit import (
    build_effect_training_revisit_freshness_audit,
    load_json_artifact,
    write_effect_training_revisit_freshness_audit_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the effect-training revisit freshness audit artifact."
    )
    parser.add_argument(
        "--stability-decision",
        default="artifacts/reports/effect_training_revisit_stability_decision_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/effect_training_revisit_freshness_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/effect_training_revisit_freshness_audit_v1.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stability_decision = load_json_artifact(args.stability_decision)
    audit = build_effect_training_revisit_freshness_audit(
        stability_decision=stability_decision,
        stability_decision_path=args.stability_decision,
    )
    write_effect_training_revisit_freshness_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )


if __name__ == "__main__":
    main()
