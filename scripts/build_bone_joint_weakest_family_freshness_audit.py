from __future__ import annotations

import argparse

from wellnessbox_rnd.evals.bone_joint_weakest_family_freshness_audit import (
    build_bone_joint_weakest_family_freshness_audit,
    load_json_artifact,
    write_bone_joint_weakest_family_freshness_audit_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the bone_joint weakest-family freshness audit artifact."
    )
    parser.add_argument(
        "--bone-joint-decision",
        default="artifacts/reports/bone_joint_weakest_family_decision_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/bone_joint_weakest_family_freshness_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/bone_joint_weakest_family_freshness_audit_v1.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bone_joint_decision = load_json_artifact(args.bone_joint_decision)
    audit = build_bone_joint_weakest_family_freshness_audit(
        bone_joint_decision=bone_joint_decision,
        bone_joint_decision_path=args.bone_joint_decision,
    )
    write_bone_joint_weakest_family_freshness_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )


if __name__ == "__main__":
    main()
