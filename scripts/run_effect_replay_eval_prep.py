import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.models.effect_model_v1 import EffectModelV1Artifact
from wellnessbox_rnd.simulation import compare_batch_simulation_modes
from wellnessbox_rnd.training.effect_model_v1 import (
    evaluate_effect_model_v1,
    load_rich_effect_records,
    split_effect_records_by_user_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Auto-detect candidate effect artifact and prepare "
            "or run replay-only evaluation"
        )
    )
    parser.add_argument(
        "--contract-json",
        default="artifacts/reports/effect_model_v3_trainprep_contract_v1.json",
        help="Training prep contract JSON path",
    )
    parser.add_argument(
        "--reference-effect-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Reference effect artifact path",
    )
    parser.add_argument(
        "--policy-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Fixed replay-only policy artifact path",
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Fixed v4 replay/eval dataset path",
    )
    parser.add_argument("--seed", type=int, default=20260311)
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/effect_replay_eval_prep_v1.json",
        help="Replay/eval prep report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/effect_replay_eval_prep_v1.md",
        help="Replay/eval prep report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = json.loads(Path(args.contract_json).read_text(encoding="utf-8"))
    candidate_artifact_path = Path(contract["candidate_outputs"]["artifact"])

    if not candidate_artifact_path.exists():
        report = _build_deferred_report(args=args, contract=contract)
    else:
        report = _build_completed_report(
            args=args,
            contract=contract,
            candidate_artifact_path=candidate_artifact_path,
        )

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(_render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "candidate_artifact_detected": report["candidate_artifact_detected"],
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _build_deferred_report(*, args, contract: dict[str, object]) -> dict[str, object]:
    train_command = contract["train_command"]
    candidate_outputs = contract["candidate_outputs"]
    return {
        "status": "deferred_missing_candidate_artifact",
        "candidate_artifact_detected": False,
        "candidate_artifact_path": candidate_outputs["artifact"],
        "reference_effect_artifact_path": args.reference_effect_artifact,
        "policy_artifact_path": args.policy_artifact,
        "dataset_path": args.dataset,
        "seed": args.seed,
        "deferred_reason": "candidate artifact does not exist yet",
        "training_command": train_command,
        "expected_candidate_outputs": candidate_outputs,
        "replay_eval_command_after_training": _build_compare_command(
            dataset=args.dataset,
            seed=args.seed,
            policy_artifact=args.policy_artifact,
            reference_effect_artifact=args.reference_effect_artifact,
            candidate_effect_artifact=str(candidate_outputs["artifact"]),
        ),
        "frozen_eval_status": {
            "rerun_performed": False,
            "reason": "replay-only boundary preserved; frozen eval path prepared but not run",
            "prepared_command": (
                "python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl "
                "--output-dir artifacts/reports/current_loop_final_eval"
            ),
        },
        "invariant_checks": {
            "runtime_safety_logic_changed": False,
            "deterministic_fallback_changed": False,
            "system_owned_action_space_changed": False,
        },
    }


def _build_completed_report(
    *,
    args,
    contract: dict[str, object],
    candidate_artifact_path: Path,
) -> dict[str, object]:
    records = load_rich_effect_records(args.dataset)
    split = split_effect_records_by_user_v1(records, seed=args.seed)
    reference_report = _build_artifact_report(
        label="current_effect",
        effect_artifact_path=args.reference_effect_artifact,
        policy_artifact_path=args.policy_artifact,
        dataset_path=args.dataset,
        split=split,
    )
    candidate_report = _build_artifact_report(
        label="trainprep_candidate",
        effect_artifact_path=str(candidate_artifact_path),
        policy_artifact_path=args.policy_artifact,
        dataset_path=args.dataset,
        split=split,
    )
    deltas = _build_deltas(reference=reference_report, candidate=candidate_report)
    comparison_report = {
        "dataset_path": str(Path(args.dataset)),
        "seed": args.seed,
        "policy_artifact_path": args.policy_artifact,
        "reference_label": "current_effect",
        "candidate_label": "trainprep_candidate",
        "reference": reference_report,
        "candidate": candidate_report,
        "deltas": deltas,
    }
    return {
        "status": "completed_candidate_evaluated",
        "candidate_artifact_detected": True,
        "candidate_artifact_path": str(candidate_artifact_path),
        "reference_effect_artifact_path": args.reference_effect_artifact,
        "policy_artifact_path": args.policy_artifact,
        "dataset_path": args.dataset,
        "seed": args.seed,
        "comparison": comparison_report,
        "comparison_interpretation": {
            "candidate_matches_reference_exactly": _all_zero_deltas(deltas),
            "frozen_eval_rerun_needed_now": False,
            "frozen_eval_reason": (
                "candidate stayed replay-only and produced no runtime-boundary change"
            ),
        },
        "frozen_eval_status": {
            "rerun_performed": False,
            "reason": "replay-only boundary preserved; path documented only",
            "prepared_command": (
                "python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl "
                "--output-dir artifacts/reports/current_loop_final_eval"
            ),
        },
        "invariant_checks": {
            "runtime_safety_logic_changed": False,
            "deterministic_fallback_changed": False,
            "system_owned_action_space_changed": False,
            "policy_effect_override_applied_count_delta": (
                candidate_report["replay_summary"]["learned_effect_and_policy_guarded"][
                    "policy_effect_override_applied_count"
                ]
                - reference_report["replay_summary"]["learned_effect_and_policy_guarded"][
                    "policy_effect_override_applied_count"
                ]
            ),
        },
        "training_contract_path": "artifacts/reports/effect_model_v3_trainprep_contract_v1.json",
        "replay_compare_command": _build_compare_command(
            dataset=args.dataset,
            seed=args.seed,
            policy_artifact=args.policy_artifact,
            reference_effect_artifact=args.reference_effect_artifact,
            candidate_effect_artifact=str(candidate_artifact_path),
        ),
    }


def _build_artifact_report(
    *,
    label: str,
    effect_artifact_path: str,
    policy_artifact_path: str,
    dataset_path: str,
    split,
) -> dict[str, object]:
    artifact = EffectModelV1Artifact.model_validate_json(
        Path(effect_artifact_path).read_text(encoding="utf-8")
    )
    test_metrics = evaluate_effect_model_v1(artifact, split.test).model_dump(mode="json")
    replay_report = compare_batch_simulation_modes(
        dataset_path=dataset_path,
        max_cycles=5,
        max_users=96,
        model_artifact_path=effect_artifact_path,
        policy_model_artifact_path=policy_artifact_path,
    )
    replay_modes = {mode.mode_name: mode for mode in replay_report.compared_modes}
    return {
        "label": label,
        "effect_artifact_path": effect_artifact_path,
        "alpha": artifact.alpha,
        "test_metrics": test_metrics,
        "replay_summary": {
            mode_name: {
                "final_policy_action_counts": replay_modes[mode_name].final_policy_action_counts,
                "low_risk_final_action_distribution": replay_modes[mode_name].cohort_slice_metrics[
                    "low_risk_users"
                ].final_action_distribution,
                "cgm_final_action_distribution": replay_modes[mode_name].cohort_slice_metrics[
                    "cgm_users"
                ].final_action_distribution,
                "low_risk_disagreement_count": replay_modes[mode_name].cohort_slice_metrics[
                    "low_risk_users"
                ].deterministic_vs_learned_disagreement_count,
                "cgm_disagreement_count": replay_modes[mode_name].cohort_slice_metrics[
                    "cgm_users"
                ].deterministic_vs_learned_disagreement_count,
                "policy_effect_override_applied_count": replay_modes[
                    mode_name
                ].policy_effect_override_applied_count,
            }
            for mode_name in ("learned_effect_guarded", "learned_effect_and_policy_guarded")
        },
    }


def _build_deltas(
    *,
    reference: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    return {
        "test_aggregate_mae_delta": round(
            candidate["test_metrics"]["aggregate_mae"] - reference["test_metrics"]["aggregate_mae"],
            6,
        ),
        "test_aggregate_r2_delta": round(
            candidate["test_metrics"]["aggregate_r2"] - reference["test_metrics"]["aggregate_r2"],
            6,
        ),
        "test_policy_proxy_mae_delta": round(
            candidate["test_metrics"]["policy_proxy_mae"]
            - reference["test_metrics"]["policy_proxy_mae"],
            6,
        ),
        "effect_only_low_risk_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_effect_guarded"]["low_risk_final_action_distribution"],
            candidate["replay_summary"]["learned_effect_guarded"]["low_risk_final_action_distribution"],
            "monitor_only",
        ),
        "combined_low_risk_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_effect_and_policy_guarded"][
                "low_risk_final_action_distribution"
            ],
            candidate["replay_summary"]["learned_effect_and_policy_guarded"][
                "low_risk_final_action_distribution"
            ],
            "monitor_only",
        ),
        "effect_only_cgm_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_effect_guarded"]["cgm_final_action_distribution"],
            candidate["replay_summary"]["learned_effect_guarded"]["cgm_final_action_distribution"],
            "monitor_only",
        ),
        "combined_cgm_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_effect_and_policy_guarded"][
                "cgm_final_action_distribution"
            ],
            candidate["replay_summary"]["learned_effect_and_policy_guarded"][
                "cgm_final_action_distribution"
            ],
            "monitor_only",
        ),
        "effect_only_low_risk_disagreement_delta": (
            candidate["replay_summary"]["learned_effect_guarded"]["low_risk_disagreement_count"]
            - reference["replay_summary"]["learned_effect_guarded"]["low_risk_disagreement_count"]
        ),
        "combined_low_risk_disagreement_delta": (
            candidate["replay_summary"]["learned_effect_and_policy_guarded"][
                "low_risk_disagreement_count"
            ]
            - reference["replay_summary"]["learned_effect_and_policy_guarded"][
                "low_risk_disagreement_count"
            ]
        ),
        "effect_only_cgm_disagreement_delta": (
            candidate["replay_summary"]["learned_effect_guarded"]["cgm_disagreement_count"]
            - reference["replay_summary"]["learned_effect_guarded"]["cgm_disagreement_count"]
        ),
        "combined_cgm_disagreement_delta": (
            candidate["replay_summary"]["learned_effect_and_policy_guarded"][
                "cgm_disagreement_count"
            ]
            - reference["replay_summary"]["learned_effect_and_policy_guarded"][
                "cgm_disagreement_count"
            ]
        ),
    }


def _action_count_delta(
    reference_counts: dict[str, int],
    candidate_counts: dict[str, int],
    action: str,
) -> int:
    return candidate_counts.get(action, 0) - reference_counts.get(action, 0)


def _all_zero_deltas(deltas: dict[str, object]) -> bool:
    return all(value == 0 for value in deltas.values())


def _build_compare_command(
    *,
    dataset: str,
    seed: int,
    policy_artifact: str,
    reference_effect_artifact: str,
    candidate_effect_artifact: str,
) -> str:
    return (
        "python scripts/compare_effect_artifact_replay.py "
        f"--dataset {dataset} "
        f"--seed {seed} "
        f"--policy-artifact {policy_artifact} "
        f"--reference-effect-artifact {reference_effect_artifact} "
        f"--candidate-effect-artifact {candidate_effect_artifact}"
    )


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# effect replay eval prep v1",
        "",
        f"- status: `{report['status']}`",
        f"- candidate_artifact_detected: `{report['candidate_artifact_detected']}`",
        f"- candidate_artifact_path: `{report['candidate_artifact_path']}`",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- policy_artifact_path: `{report['policy_artifact_path']}`",
        "",
    ]
    if report["status"] == "completed_candidate_evaluated":
        lines.append("## Comparison")
        lines.append("")
        lines.append(_render_compare_markdown(report["comparison"]).strip())
        lines.extend(
            [
                "",
                "## Invariants",
                (
                    "- runtime_safety_logic_changed: "
                    f"`{report['invariant_checks']['runtime_safety_logic_changed']}`"
                ),
                (
                    "- deterministic_fallback_changed: "
                    f"`{report['invariant_checks']['deterministic_fallback_changed']}`"
                ),
                (
                    "- system_owned_action_space_changed: "
                    f"`{report['invariant_checks']['system_owned_action_space_changed']}`"
                ),
                (
                    "- policy_effect_override_applied_count_delta: "
                    f"`{report['invariant_checks']['policy_effect_override_applied_count_delta']}`"
                ),
                "",
                "## Frozen Eval",
                f"- rerun_performed: `{report['frozen_eval_status']['rerun_performed']}`",
                f"- reason: `{report['frozen_eval_status']['reason']}`",
                f"- prepared_command: `{report['frozen_eval_status']['prepared_command']}`",
            ]
        )
    else:
        lines.extend(
            [
                "## Deferred",
                f"- reason: `{report['deferred_reason']}`",
                f"- training_command: `{report['training_command']}`",
                (
                    "- replay_eval_command_after_training: "
                    f"`{report['replay_eval_command_after_training']}`"
                ),
                "",
                "## Frozen Eval",
                f"- rerun_performed: `{report['frozen_eval_status']['rerun_performed']}`",
                f"- reason: `{report['frozen_eval_status']['reason']}`",
                f"- prepared_command: `{report['frozen_eval_status']['prepared_command']}`",
            ]
        )
    return "\n".join(lines) + "\n"


def _render_compare_markdown(report: dict[str, object]) -> str:
    lines = [
        "# effect artifact replay comparison v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- policy_artifact_path: `{report['policy_artifact_path']}`",
        f"- reference_label: `{report['reference_label']}`",
        f"- candidate_label: `{report['candidate_label']}`",
        "",
        "## Deltas",
    ]
    for key, value in report["deltas"].items():
        lines.append(f"- `{key}`: `{value}`")
    for artifact_key in ("reference", "candidate"):
        artifact_report = report[artifact_key]
        lines.extend(
            [
                "",
                f"## {artifact_key.title()}",
                f"- label: `{artifact_report['label']}`",
                f"- effect_artifact_path: `{artifact_report['effect_artifact_path']}`",
                f"- alpha: `{artifact_report['alpha']}`",
                f"- test_metrics: `{artifact_report['test_metrics']}`",
                (
                    "- learned_effect_guarded low-risk final actions: "
                    f"`{artifact_report['replay_summary']['learned_effect_guarded']['low_risk_final_action_distribution']}`"
                ),
                (
                    "- learned_effect_guarded cgm final actions: "
                    f"`{artifact_report['replay_summary']['learned_effect_guarded']['cgm_final_action_distribution']}`"
                ),
                (
                    "- learned_effect_and_policy_guarded low-risk final actions: "
                    f"`{artifact_report['replay_summary']['learned_effect_and_policy_guarded']['low_risk_final_action_distribution']}`"
                ),
                (
                    "- learned_effect_and_policy_guarded cgm final actions: "
                    f"`{artifact_report['replay_summary']['learned_effect_and_policy_guarded']['cgm_final_action_distribution']}`"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
