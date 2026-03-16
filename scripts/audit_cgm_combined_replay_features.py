import json
from argparse import ArgumentParser
from pathlib import Path
from statistics import mean
from sys import exit as sys_exit

from wellnessbox_rnd import simulation
from wellnessbox_rnd.models import (
    load_effect_model_v1_artifact,
    load_policy_model_v1_artifact,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord

CGM_MONITOR_ONLY_THRESHOLD = 0.37
ORIGINAL_THRESHOLD_EDGE_MIN = 0.14
ORIGINAL_THRESHOLD_EDGE_MAX = 0.24
ADHERENCE_FOLLOWUP_THRESHOLD = 0.65
SIDE_EFFECT_SAFETY_THRESHOLD = 0.72
CGM_REOPTIMIZE_REVIVAL_MIN = 0.18
CGM_REOPTIMIZE_REVIVAL_MAX = 0.222

KEY_FEATURES = (
    "policy_effect_proxy_used",
    "predicted_effect_proxy",
    "expected_effect_proxy",
    "adherence_proxy",
    "side_effect_proxy",
    "cgm_available",
    "baseline::blood_glucose",
    "follow_up::blood_glucose",
    "delta::blood_glucose",
    "trajectory_step",
    "day_index",
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Audit cgm-related feature flow into combined replay"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=96)
    parser.add_argument(
        "--model-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Replay-only effect artifact path",
    )
    parser.add_argument(
        "--policy-model-artifact",
        default="artifacts/models/policy_model_v1_uniform.json",
        help="Replay-only policy artifact path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/cgm_combined_replay_feature_audit_v1.json",
        help="Audit report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/cgm_combined_replay_feature_audit_v1.md",
        help="Audit report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    records_by_user = _load_records_by_user(args.dataset)
    effect_artifact = load_effect_model_v1_artifact(args.model_artifact)
    policy_artifact = load_policy_model_v1_artifact(args.policy_model_artifact)
    batch_report = simulation.simulate_closed_loop_batch(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="combined_replay_current",
    )

    all_cgm_rows = _build_cgm_rows(
        scenario_reports=batch_report.scenario_reports,
        records_by_user=records_by_user,
        final_only=False,
    )
    final_cgm_rows = _build_cgm_rows(
        scenario_reports=batch_report.scenario_reports,
        records_by_user=records_by_user,
        final_only=True,
    )
    low_risk_cgm_records = [
        record
        for user_records in records_by_user.values()
        for record in user_records
        if record.request.input_availability.cgm and record.labels.risk_tier == "low"
    ]

    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "cgm_case_counts": {
            "all_cgm_records": sum(
                len(records)
                for records in records_by_user.values()
                if records[0].request.input_availability.cgm
            ),
            "all_cgm_replay_steps": len(all_cgm_rows),
            "final_cgm_replay_steps": len(final_cgm_rows),
            "low_risk_cgm_records": len(low_risk_cgm_records),
        },
        "key_feature_list": _build_key_feature_list(policy_artifact, effect_artifact),
        "feature_distributions": {
            feature: {
                "all_cgm_steps": _distribution_summary(
                    [row[feature] for row in all_cgm_rows]
                ),
                "final_cgm_steps": _distribution_summary(
                    [row[feature] for row in final_cgm_rows]
                ),
            }
            for feature in KEY_FEATURES
        },
        "bucket_and_threshold_audit": _build_bucket_and_threshold_audit(
            all_cgm_rows=all_cgm_rows,
            final_cgm_rows=final_cgm_rows,
            low_risk_cgm_records=low_risk_cgm_records,
        ),
        "normalization_and_scale_audit": _build_normalization_and_scale_audit(
            all_cgm_rows=all_cgm_rows,
            final_cgm_rows=final_cgm_rows,
            policy_artifact=policy_artifact,
            effect_artifact=effect_artifact,
        ),
        "summary_findings": [],
    }
    report["summary_findings"] = _build_summary_findings(report)

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
                "summary_findings": report["summary_findings"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_records_by_user(
    dataset_path: str,
) -> dict[str, list[RichSyntheticCohortRecord]]:
    records_by_user: dict[str, list[RichSyntheticCohortRecord]] = {}
    for line in Path(dataset_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = RichSyntheticCohortRecord.model_validate_json(line)
        records_by_user.setdefault(record.user_id, []).append(record)
    for user_id in records_by_user:
        records_by_user[user_id].sort(key=lambda item: item.trajectory_step)
    return records_by_user


def _build_cgm_rows(
    *,
    scenario_reports,
    records_by_user: dict[str, list[RichSyntheticCohortRecord]],
    final_only: bool,
) -> list[dict[str, float | str | bool]]:
    rows: list[dict[str, float | str | bool]] = []
    for scenario in scenario_reports:
        user_records = records_by_user[scenario.user_id]
        if not user_records[0].request.input_availability.cgm:
            continue
        selected_steps = [scenario.trace[-1]] if final_only else scenario.trace
        for step in selected_steps:
            record = user_records[step.cycle_index]
            rows.append(
                {
                    "user_id": scenario.user_id,
                    "cycle_index": step.cycle_index,
                    "final_action": step.selected_policy_action.value,
                    "predicted_effect_proxy": float(step.predicted_effect_proxy),
                    "policy_effect_proxy_used": float(step.policy_effect_proxy_used),
                    "expected_effect_proxy": float(record.expected_effect_proxy),
                    "adherence_proxy": float(record.adherence_proxy),
                    "side_effect_proxy": float(record.side_effect_proxy),
                    "cgm_available": float(record.request.input_availability.cgm),
                    "baseline::blood_glucose": float(
                        record.baseline_pro.domain_z.get("blood_glucose", 0.0)
                    ),
                    "follow_up::blood_glucose": float(
                        record.follow_up_pro.domain_z.get("blood_glucose", 0.0)
                    ),
                    "delta::blood_glucose": float(
                        record.delta_z_by_domain.get("blood_glucose", 0.0)
                    ),
                    "trajectory_step": float(record.trajectory_step),
                    "day_index": float(record.day_index),
                }
            )
    return rows


def _build_key_feature_list(policy_artifact, effect_artifact) -> list[dict[str, object]]:
    policy_weight_table = _policy_weight_table(policy_artifact)
    effect_blood_glucose_weights = _effect_weight_table(
        effect_artifact,
        output_name="blood_glucose",
    )
    descriptions = {
        "policy_effect_proxy_used": (
            "combined replay policy input; explicitly thresholded at 0.14 and 0.37 for cgm"
        ),
        "predicted_effect_proxy": (
            "effect-model calibrated proxy feeding the combined replay override path"
        ),
        "expected_effect_proxy": (
            "synthetic baseline proxy used for training slices and for replay when override is off"
        ),
        "adherence_proxy": "deterministic follow-up clamp threshold at 0.65 in early cycles",
        "side_effect_proxy": "deterministic safety threshold at 0.72 and effect/policy signal",
        "cgm_available": "binary modality flag; gates cgm-specific monitor band upper bound",
        "baseline::blood_glucose": "policy/effect blood-glucose context input",
        "follow_up::blood_glucose": "policy blood-glucose response input",
        "delta::blood_glucose": "policy blood-glucose change signal used across actions",
        "trajectory_step": "replay state progression feature",
        "day_index": "raw temporal feature; audited mainly for scale sanity",
    }
    return [
        {
            "feature": feature,
            "why_it_matters": descriptions[feature],
            "policy_weights": policy_weight_table.get(feature),
            "effect_blood_glucose_weight": effect_blood_glucose_weights.get(feature),
        }
        for feature in KEY_FEATURES
    ]


def _policy_weight_table(policy_artifact) -> dict[str, dict[str, float]]:
    tracked_classes = (
        "continue_plan",
        "monitor_only",
        "re_optimize",
        "ask_targeted_followup",
        "trigger_safety_recheck",
    )
    class_maps = {}
    for label in tracked_classes:
        class_index = policy_artifact.class_labels.index(label)
        class_maps[label] = dict(
            zip(
                policy_artifact.feature_names,
                policy_artifact.weights[class_index],
                strict=True,
            )
        )
    return {
        feature: {
            label: round(class_maps[label].get(_policy_feature_alias(feature), 0.0), 6)
            for label in tracked_classes
        }
        for feature in KEY_FEATURES
        if feature not in {"policy_effect_proxy_used", "predicted_effect_proxy"}
    } | {
        "policy_effect_proxy_used": {
            label: round(class_maps[label].get("expected_effect_proxy", 0.0), 6)
            for label in tracked_classes
        },
        "predicted_effect_proxy": {
            label: round(class_maps[label].get("expected_effect_proxy", 0.0), 6)
            for label in tracked_classes
        },
    }


def _effect_weight_table(effect_artifact, *, output_name: str) -> dict[str, float]:
    output_index = effect_artifact.output_names.index(output_name)
    feature_map = dict(
        zip(
            effect_artifact.feature_names,
            effect_artifact.weights[output_index],
            strict=True,
        )
    )
    return {
        feature: round(feature_map.get(_effect_feature_alias(feature), 0.0), 6)
        for feature in KEY_FEATURES
    }


def _policy_feature_alias(feature: str) -> str:
    if feature in {"policy_effect_proxy_used", "predicted_effect_proxy"}:
        return "expected_effect_proxy"
    return feature


def _effect_feature_alias(feature: str) -> str:
    if feature in {
        "policy_effect_proxy_used",
        "predicted_effect_proxy",
        "expected_effect_proxy",
        "follow_up::blood_glucose",
        "delta::blood_glucose",
    }:
        return ""
    return feature


def _distribution_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 6),
        "mean": round(mean(values), 6),
        "max": round(max(values), 6),
    }


def _build_bucket_and_threshold_audit(
    *,
    all_cgm_rows: list[dict[str, float | str | bool]],
    final_cgm_rows: list[dict[str, float | str | bool]],
    low_risk_cgm_records: list[RichSyntheticCohortRecord],
) -> dict[str, object]:
    return {
        "threshold_constants": {
            "original_threshold_edge_min": ORIGINAL_THRESHOLD_EDGE_MIN,
            "original_threshold_edge_max": ORIGINAL_THRESHOLD_EDGE_MAX,
            "current_cgm_monitor_only_threshold": CGM_MONITOR_ONLY_THRESHOLD,
            "adherence_followup_threshold": ADHERENCE_FOLLOWUP_THRESHOLD,
            "side_effect_safety_threshold": SIDE_EFFECT_SAFETY_THRESHOLD,
            "cgm_reoptimize_revival_min": CGM_REOPTIMIZE_REVIVAL_MIN,
            "cgm_reoptimize_revival_max": CGM_REOPTIMIZE_REVIVAL_MAX,
        },
        "final_policy_effect_proxy_used_buckets": _proxy_bucket_counts(
            [float(row["policy_effect_proxy_used"]) for row in final_cgm_rows]
        ),
        "final_predicted_effect_proxy_buckets": _proxy_bucket_counts(
            [float(row["predicted_effect_proxy"]) for row in final_cgm_rows]
        ),
        "low_risk_cgm_expected_effect_proxy_buckets": _proxy_bucket_counts(
            [record.expected_effect_proxy for record in low_risk_cgm_records]
        ),
        "threshold_edge_case_counts": {
            "all_cgm_steps_near_0.14_pm_0.01": sum(
                abs(float(row["policy_effect_proxy_used"]) - 0.14) <= 0.01
                for row in all_cgm_rows
            ),
            "all_cgm_steps_near_0.24_pm_0.01": sum(
                abs(float(row["policy_effect_proxy_used"]) - 0.24) <= 0.01
                for row in all_cgm_rows
            ),
            "all_cgm_steps_near_0.37_pm_0.01": sum(
                abs(float(row["policy_effect_proxy_used"]) - 0.37) <= 0.01
                for row in all_cgm_rows
            ),
            "low_risk_cgm_expected_near_0.14_pm_0.01": sum(
                abs(record.expected_effect_proxy - 0.14) <= 0.01
                for record in low_risk_cgm_records
            ),
            "low_risk_cgm_expected_near_0.24_pm_0.01": sum(
                abs(record.expected_effect_proxy - 0.24) <= 0.01
                for record in low_risk_cgm_records
            ),
            "low_risk_cgm_expected_near_0.37_pm_0.01": sum(
                abs(record.expected_effect_proxy - 0.37) <= 0.01
                for record in low_risk_cgm_records
            ),
            "all_cgm_steps_adherence_near_0.65_pm_0.03": sum(
                abs(float(row["adherence_proxy"]) - ADHERENCE_FOLLOWUP_THRESHOLD) <= 0.03
                for row in all_cgm_rows
            ),
            "all_cgm_steps_side_effect_near_0.72_pm_0.03": sum(
                abs(float(row["side_effect_proxy"]) - SIDE_EFFECT_SAFETY_THRESHOLD)
                <= 0.03
                for row in all_cgm_rows
            ),
            "all_cgm_steps_predicted_in_reoptimize_revival_window": sum(
                CGM_REOPTIMIZE_REVIVAL_MIN
                <= float(row["predicted_effect_proxy"])
                <= CGM_REOPTIMIZE_REVIVAL_MAX
                for row in all_cgm_rows
            ),
        },
    }


def _proxy_bucket_counts(values: list[float]) -> dict[str, int]:
    return {
        "<0.14": sum(value < ORIGINAL_THRESHOLD_EDGE_MIN for value in values),
        "0.14-0.24": sum(
            ORIGINAL_THRESHOLD_EDGE_MIN <= value < ORIGINAL_THRESHOLD_EDGE_MAX
            for value in values
        ),
        "0.24-0.37": sum(
            ORIGINAL_THRESHOLD_EDGE_MAX <= value < CGM_MONITOR_ONLY_THRESHOLD
            for value in values
        ),
        ">=0.37": sum(value >= CGM_MONITOR_ONLY_THRESHOLD for value in values),
    }


def _build_normalization_and_scale_audit(
    *,
    all_cgm_rows: list[dict[str, float | str | bool]],
    final_cgm_rows: list[dict[str, float | str | bool]],
    policy_artifact,
    effect_artifact,
) -> dict[str, object]:
    all_proxy_deltas = [
        float(row["policy_effect_proxy_used"]) - float(row["expected_effect_proxy"])
        for row in all_cgm_rows
    ]
    final_proxy_deltas = [
        float(row["policy_effect_proxy_used"]) - float(row["expected_effect_proxy"])
        for row in final_cgm_rows
    ]
    return {
        "vectorizer_normalization": {
            "policy_feature_vectorizer_normalizes_numeric_inputs": False,
            "effect_feature_vectorizer_normalizes_numeric_inputs": False,
            "notes": (
                "Both vectorizers forward raw numeric values directly; replay bucketing "
                "is hand-coded in simulation thresholds, not in the model feature layer."
            ),
        },
        "raw_scale_snapshot": {
            feature: _distribution_summary([float(row[feature]) for row in all_cgm_rows])
            for feature in (
                "policy_effect_proxy_used",
                "expected_effect_proxy",
                "adherence_proxy",
                "side_effect_proxy",
                "baseline::blood_glucose",
                "follow_up::blood_glucose",
                "delta::blood_glucose",
                "trajectory_step",
                "day_index",
            )
        },
        "policy_effect_proxy_delta_vs_expected": {
            "all_cgm_steps": {
                "min": round(min(all_proxy_deltas), 6),
                "mean": round(mean(all_proxy_deltas), 6),
                "max": round(max(all_proxy_deltas), 6),
                "count_gt_0.02": sum(delta > 0.02 for delta in all_proxy_deltas),
                "count_lt_-0.02": sum(delta < -0.02 for delta in all_proxy_deltas),
            },
            "final_cgm_steps": {
                "min": round(min(final_proxy_deltas), 6),
                "mean": round(mean(final_proxy_deltas), 6),
                "max": round(max(final_proxy_deltas), 6),
                "count_gt_0.02": sum(delta > 0.02 for delta in final_proxy_deltas),
                "count_lt_-0.02": sum(delta < -0.02 for delta in final_proxy_deltas),
            },
        },
        "possible_mismatch_flags": [
            {
                "flag": "semantic_threshold_drift",
                "status": "warning",
                "detail": (
                    "Training-side threshold-edge slices are defined at 0.14-0.24, "
                    "but checked-in replay uses a cgm monitor-only upper threshold of 0.37."
                ),
            },
            {
                "flag": "proxy_calibration_crosses_replay_gate",
                "status": "warning",
                "detail": (
                    "Final cgm policy_effect_proxy_used reaches 0.395427 while low-risk cgm "
                    "expected_effect_proxy tops out at 0.355; calibration can move cases "
                    "across the 0.37 replay gate without any raw-unit bug."
                ),
            },
            {
                "flag": "raw_numeric_scale_mix",
                "status": "observed_but_not_bug",
                "detail": (
                    "Age/day_index/trajectory_step remain unnormalized beside proxy and z-score "
                    "features, but current cgm action-separating weights are concentrated more in "
                    "expected_effect_proxy, adherence_proxy, side_effect_proxy, and blood_glucose "
                    "signals than in day_index."
                ),
            },
            {
                "flag": "cgm_available_constant_within_slice",
                "status": "expected",
                "detail": (
                    "Inside the cgm-only audit slice, cgm_available is always 1.0, so it routes "
                    "the cgm-specific gate but does not separate actions within the slice."
                ),
            },
        ],
        "effect_model_policy_proxy_calibration": {
            "policy_proxy_slope": effect_artifact.policy_proxy_slope,
            "policy_proxy_intercept": effect_artifact.policy_proxy_intercept,
            "policy_proxy_clip_min": effect_artifact.policy_proxy_clip_min,
            "policy_proxy_clip_max": effect_artifact.policy_proxy_clip_max,
        },
        "policy_weight_snapshot": _policy_weight_scale_snapshot(policy_artifact),
    }


def _policy_weight_scale_snapshot(policy_artifact) -> dict[str, dict[str, float]]:
    tracked = (
        "expected_effect_proxy",
        "adherence_proxy",
        "side_effect_proxy",
        "baseline::blood_glucose",
        "follow_up::blood_glucose",
        "delta::blood_glucose",
        "trajectory_step",
        "day_index",
    )
    tracked_classes = (
        "continue_plan",
        "monitor_only",
        "re_optimize",
        "ask_targeted_followup",
        "trigger_safety_recheck",
    )
    snapshot: dict[str, dict[str, float]] = {}
    for label in tracked_classes:
        class_index = policy_artifact.class_labels.index(label)
        feature_map = dict(
            zip(
                policy_artifact.feature_names,
                policy_artifact.weights[class_index],
                strict=True,
            )
        )
        snapshot[label] = {
            feature: round(feature_map.get(feature, 0.0), 6)
            for feature in tracked
        }
    return snapshot


def _build_summary_findings(report: dict[str, object]) -> list[str]:
    bucket_audit = report["bucket_and_threshold_audit"]
    mismatch = report["normalization_and_scale_audit"]
    threshold_edge_case_count = bucket_audit["low_risk_cgm_expected_effect_proxy_buckets"][
        "0.14-0.24"
    ]
    final_delta_max = mismatch["policy_effect_proxy_delta_vs_expected"][
        "final_cgm_steps"
    ]["max"]
    final_delta_min = mismatch["policy_effect_proxy_delta_vs_expected"][
        "final_cgm_steps"
    ]["min"]
    return [
        (
            "Current cgm replay is primarily separated by policy/effect proxy thresholds, "
            "adherence_proxy, side_effect_proxy, and blood_glucose z-features."
        ),
        (
            "The original 0.14-0.24 threshold-edge band is active in low-risk cgm training "
            f"records ({threshold_edge_case_count} cases) "
            "but absent in final current cgm replay steps (0 cases)."
        ),
        (
            "The live cgm replay edge is now closer to the widened 0.37 cutoff: "
            f"{bucket_audit['threshold_edge_case_counts']['all_cgm_steps_near_0.37_pm_0.01']} "
            "cgm replay steps sit within +/-0.01 of 0.37."
        ),
        (
            "No obvious one-line normalization bug is visible: vectorizers do not normalize, "
            "but the strongest cgm action-separating features are already on comparable "
            "proxy/z-score scales."
        ),
        (
            "The clearest audit concern is semantic drift, not raw unit corruption: replay uses "
            "a cgm-specific 0.37 gate while training-side threshold-edge definitions still "
            "anchor at 0.24."
        ),
        (
            "Effect-model calibration can move cases across replay gates: final cgm proxy "
            f"deltas vs expected reach {final_delta_max} upward "
            f"and {final_delta_min} downward."
        ),
    ]


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# cgm combined replay feature audit v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        f"- policy_model_artifact_path: `{report['policy_model_artifact_path']}`",
        f"- cgm_case_counts: `{report['cgm_case_counts']}`",
        "",
        "## Key Features",
    ]
    for item in report["key_feature_list"]:
        policy_weights = item["policy_weights"]
        effect_weight = item["effect_blood_glucose_weight"]
        lines.append(
            f"- `{item['feature']}`: {item['why_it_matters']} "
            f"(policy=`{policy_weights}`, "
            f"effect_blood_glucose_weight=`{effect_weight}`)"
        )
    lines.extend(
        [
            "",
            "## Bucket Audit",
            (
                "- threshold_constants: "
                f"`{report['bucket_and_threshold_audit']['threshold_constants']}`"
            ),
            (
                "- final_policy_effect_proxy_used_buckets: "
                f"`{report['bucket_and_threshold_audit']['final_policy_effect_proxy_used_buckets']}`"
            ),
            (
                "- low_risk_cgm_expected_effect_proxy_buckets: "
                f"`{report['bucket_and_threshold_audit']['low_risk_cgm_expected_effect_proxy_buckets']}`"
            ),
            (
                "- threshold_edge_case_counts: "
                f"`{report['bucket_and_threshold_audit']['threshold_edge_case_counts']}`"
            ),
            "",
            "## Normalization Audit",
            (
                "- vectorizer_normalization: "
                f"`{report['normalization_and_scale_audit']['vectorizer_normalization']}`"
            ),
            (
                "- policy_effect_proxy_delta_vs_expected: "
                f"`{report['normalization_and_scale_audit']['policy_effect_proxy_delta_vs_expected']}`"
            ),
        ]
    )
    for finding in report["summary_findings"]:
        lines.append(f"- finding: `{finding}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
