"""Decide whether a candidate artifact may replace the current runtime model.

The frozen-eval comparison script only reports differences. H-003 needs a step
that actually fails when safety gets worse, and a record of what to roll back
to when a replacement is later withdrawn. Both live here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "candidate_safety_regression_v1"
DECISION_SCHEMA_VERSION = "candidate_promotion_decision_v1"

SAFETY_METRICS: tuple[tuple[str, str], ...] = (
    ("safety_reference_accuracy_pct", "higher_is_better"),
    ("adverse_event_count_yearly", "lower_is_better"),
    ("recommendation_coverage_pct", "higher_is_better"),
    ("next_action_accuracy_pct", "higher_is_better"),
)


def _score(report: dict[str, Any], metric: str) -> float | None:
    entry = report.get("summary", {}).get(metric)
    if not isinstance(entry, dict):
        return None
    score = entry.get("score")
    return float(score) if isinstance(score, int | float) else None


def _passed(report: dict[str, Any], metric: str) -> bool | None:
    entry = report.get("summary", {}).get(metric)
    return entry.get("passed") if isinstance(entry, dict) else None


def evaluate_safety_regression_v1(
    baseline_report: dict[str, Any],
    candidate_report: dict[str, Any],
    *,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Compare the two frozen-eval reports and fail closed on any safety loss."""
    if baseline_report.get("case_count") != candidate_report.get("case_count"):
        raise ValueError("frozen_eval_case_count_mismatch")

    metrics: list[dict[str, Any]] = []
    regressions: list[str] = []
    for metric, direction in SAFETY_METRICS:
        before = _score(baseline_report, metric)
        after = _score(candidate_report, metric)
        if before is None or after is None:
            metrics.append(
                {"metric": metric, "direction": direction, "status": "metric_missing"}
            )
            regressions.append(metric)
            continue
        delta = after - before
        worsened = delta < -tolerance if direction == "higher_is_better" else delta > tolerance
        newly_failing = _passed(baseline_report, metric) is True and _passed(
            candidate_report, metric
        ) is not True
        if worsened or newly_failing:
            regressions.append(metric)
        metrics.append(
            {
                "metric": metric,
                "direction": direction,
                "baseline_score": before,
                "candidate_score": after,
                "delta": delta,
                "baseline_passed": _passed(baseline_report, metric),
                "candidate_passed": _passed(candidate_report, metric),
                "regressed": bool(worsened or newly_failing),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED" if regressions else "READY",
        "safety_regressed": bool(regressions),
        "tolerance": tolerance,
        "case_count": candidate_report.get("case_count"),
        "regressed_metrics": regressions,
        "metrics": metrics,
    }


def _file_digest(path: str | Path | None) -> str | None:
    if path is None:
        return None
    target = Path(path)
    return hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None


def build_candidate_promotion_decision_v1(
    *,
    dataset_manifest: dict[str, Any],
    regression: dict[str, Any],
    candidate_artifact_path: str | Path,
    current_artifact_path: str | Path | None,
    decided_at: str,
    decided_by: str,
    training_gate_status: str,
) -> dict[str, Any]:
    """Record replace-or-keep with the exact artifact to roll back to."""
    if not decided_by.strip():
        raise ValueError("promotion_decision_requires_named_decider")

    gate_open = training_gate_status == "go"
    blockers: list[str] = []
    if not gate_open:
        blockers.append(f"training_gate_not_open:{training_gate_status}")
    if regression.get("safety_regressed"):
        blockers.append("safety_regression_detected")
    if not dataset_manifest.get("included_drafts"):
        blockers.append("approved_draft_dataset_is_empty")

    decision = "keep_current_model" if blockers else "replace_with_candidate"
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "decision": decision,
        "blockers": blockers,
        "decided_at": decided_at,
        "decided_by": decided_by.strip(),
        "training_gate_status": training_gate_status,
        "dataset": {
            "dataset_sha256": dataset_manifest.get("dataset_sha256"),
            "included_count": len(dataset_manifest.get("included_drafts", [])),
            "draft_ledger_sha256": dataset_manifest.get("source", {}).get("draft_ledger_sha256"),
        },
        "safety_regression": {
            "status": regression.get("status"),
            "regressed_metrics": regression.get("regressed_metrics", []),
        },
        "candidate_artifact": {
            "path": str(candidate_artifact_path),
            "sha256": _file_digest(candidate_artifact_path),
        },
        "rollback": {
            "restore_artifact_path": str(current_artifact_path) if current_artifact_path else None,
            "restore_artifact_sha256": _file_digest(current_artifact_path),
            "instruction": (
                "교체를 되돌릴 때는 restore_artifact_path의 파일을 그대로 복원하고 "
                "restore_artifact_sha256과 대조한 뒤 고정 평가를 다시 실행한다."
            ),
        },
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target
