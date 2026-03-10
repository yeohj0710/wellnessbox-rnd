from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from wellnessbox_rnd.models.efficacy_model_v0 import (
    EfficacyFeatureVectorizer,
    EfficacyModelArtifact,
    build_efficacy_feature_dict,
    predict_effect_proxy,
)
from wellnessbox_rnd.synthetic.longitudinal import SyntheticCohortRecord


class EvaluationMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float
    baseline_mae: float
    baseline_rmse: float
    baseline_r2: float


@dataclass(frozen=True)
class SplitResult:
    train: list[SyntheticCohortRecord]
    val: list[SyntheticCohortRecord]
    test: list[SyntheticCohortRecord]


def load_synthetic_records(path: str | Path) -> list[SyntheticCohortRecord]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(SyntheticCohortRecord.model_validate_json(line))
    return rows


def split_records_by_user(
    records: list[SyntheticCohortRecord],
    *,
    seed: int,
) -> SplitResult:
    grouped: dict[str, list[SyntheticCohortRecord]] = {}
    for record in records:
        grouped.setdefault(record.user_id, []).append(record)

    buckets: dict[str, list[SyntheticCohortRecord]] = {"train": [], "val": [], "test": []}
    for user_id in sorted(grouped):
        digest = hashlib.sha256(f"{seed}:{user_id}".encode()).digest()[0]
        ratio = digest / 255.0
        split_name = "train" if ratio < 0.6 else "val" if ratio < 0.8 else "test"
        buckets[split_name].extend(grouped[user_id])

    return SplitResult(
        train=sorted(buckets["train"], key=lambda item: item.record_id),
        val=sorted(buckets["val"], key=lambda item: item.record_id),
        test=sorted(buckets["test"], key=lambda item: item.record_id),
    )


def fit_efficacy_model(
    train_records: list[SyntheticCohortRecord],
    val_records: list[SyntheticCohortRecord],
    *,
    seed: int,
    alpha_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 5.0, 10.0),
) -> tuple[EfficacyModelArtifact, dict[str, EvaluationMetrics]]:
    train_rows = [build_efficacy_feature_dict(record) for record in train_records]
    vectorizer = EfficacyFeatureVectorizer.fit(train_rows)

    x_train = np.asarray(vectorizer.transform(train_rows), dtype=float)
    y_train = np.asarray([record.expected_effect_proxy for record in train_records], dtype=float)

    best_artifact: EfficacyModelArtifact | None = None
    best_metrics: EvaluationMetrics | None = None
    train_metrics: EvaluationMetrics | None = None

    for alpha in alpha_grid:
        weights, intercept = _fit_ridge_regression(x_train, y_train, alpha=alpha)
        candidate = EfficacyModelArtifact(
            cohort_version=train_records[0].cohort_version if train_records else "unknown",
            seed=seed,
            alpha=alpha,
            feature_names=vectorizer.feature_names,
            intercept=round(float(intercept), 8),
            weights=[round(float(weight), 8) for weight in weights],
        )
        candidate_train_metrics = evaluate_efficacy_model(candidate, train_records)
        candidate_val_metrics = evaluate_efficacy_model(candidate, val_records)
        if best_metrics is None or candidate_val_metrics.mae < best_metrics.mae:
            best_artifact = candidate
            best_metrics = candidate_val_metrics
            train_metrics = candidate_train_metrics

    assert best_artifact is not None
    assert best_metrics is not None
    assert train_metrics is not None
    return best_artifact, {"train": train_metrics, "val": best_metrics}


def evaluate_efficacy_model(
    artifact: EfficacyModelArtifact,
    records: list[SyntheticCohortRecord],
) -> EvaluationMetrics:
    actual = np.asarray([record.expected_effect_proxy for record in records], dtype=float)
    predicted = np.asarray(
        [predict_effect_proxy(artifact, record) for record in records],
        dtype=float,
    )
    baseline_prediction = np.full_like(
        actual,
        fill_value=float(actual.mean() if len(actual) else 0.0),
    )

    return EvaluationMetrics(
        mae=round(_mae(actual, predicted), 6),
        rmse=round(_rmse(actual, predicted), 6),
        r2=round(_r2(actual, predicted), 6),
        baseline_mae=round(_mae(actual, baseline_prediction), 6),
        baseline_rmse=round(_rmse(actual, baseline_prediction), 6),
        baseline_r2=round(_r2(actual, baseline_prediction), 6),
    )


def render_training_report(
    *,
    artifact: EfficacyModelArtifact,
    split: SplitResult,
    train_metrics: EvaluationMetrics,
    val_metrics: EvaluationMetrics,
    test_metrics: EvaluationMetrics,
) -> dict[str, object]:
    return {
        "model_name": artifact.model_name,
        "cohort_version": artifact.cohort_version,
        "seed": artifact.seed,
        "alpha": artifact.alpha,
        "feature_count": len(artifact.feature_names),
        "split_record_counts": {
            "train": len(split.train),
            "val": len(split.val),
            "test": len(split.test),
        },
        "metrics": {
            "train": train_metrics.model_dump(mode="json"),
            "val": val_metrics.model_dump(mode="json"),
            "test": test_metrics.model_dump(mode="json"),
        },
        "top_positive_features": _top_weight_features(artifact, descending=True),
        "top_negative_features": _top_weight_features(artifact, descending=False),
        "sample_predictions": [
            {
                "record_id": record.record_id,
                "actual": record.expected_effect_proxy,
                "predicted": predict_effect_proxy(artifact, record),
            }
            for record in split.test[:5]
        ],
    }


def render_training_markdown(report: dict[str, object]) -> str:
    lines = [
        "# efficacy model v0 evaluation",
        "",
        f"- model_name: `{report['model_name']}`",
        f"- cohort_version: `{report['cohort_version']}`",
        f"- seed: `{report['seed']}`",
        f"- alpha: `{report['alpha']}`",
        f"- feature_count: `{report['feature_count']}`",
        "",
        "## Split Sizes",
    ]
    for key, value in report["split_record_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Metrics"])
    for split_name, metrics in report["metrics"].items():
        lines.append(
            f"- `{split_name}`: "
            f"mae=`{metrics['mae']}`, rmse=`{metrics['rmse']}`, r2=`{metrics['r2']}`, "
            f"baseline_mae=`{metrics['baseline_mae']}`"
        )
    lines.extend(["", "## Top Positive Features"])
    for item in report["top_positive_features"]:
        lines.append(f"- `{item['feature']}`: `{item['weight']}`")
    lines.extend(["", "## Top Negative Features"])
    for item in report["top_negative_features"]:
        lines.append(f"- `{item['feature']}`: `{item['weight']}`")
    return "\n".join(lines) + "\n"


def write_training_outputs(
    *,
    artifact: EfficacyModelArtifact,
    report: dict[str, object],
    artifact_path: str | Path,
    report_json_path: str | Path,
    report_md_path: str | Path,
    split_json_path: str | Path,
    split: SplitResult,
) -> None:
    artifact_target = Path(artifact_path)
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    split_json_target = Path(split_json_path)
    for path in (
        artifact_target,
        report_json_target,
        report_md_target,
        split_json_target,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    artifact_target.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(render_training_markdown(report), encoding="utf-8")
    split_json_target.write_text(
        json.dumps(
            {
                "train_record_ids": [record.record_id for record in split.train],
                "val_record_ids": [record.record_id for record in split.val],
                "test_record_ids": [record.record_id for record in split.test],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _fit_ridge_regression(
    x: np.ndarray,
    y: np.ndarray,
    *,
    alpha: float,
) -> tuple[np.ndarray, float]:
    x_bias = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    regularizer = np.eye(x_bias.shape[1]) * alpha
    regularizer[0, 0] = 0.0
    solution = np.linalg.pinv(x_bias.T @ x_bias + regularizer) @ x_bias.T @ y
    intercept = solution[0]
    weights = solution[1:]
    return weights, intercept


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(sqrt(np.mean((actual - predicted) ** 2)))


def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    baseline = np.mean(actual)
    denom = np.sum((actual - baseline) ** 2)
    if denom == 0:
        return 0.0
    numer = np.sum((actual - predicted) ** 2)
    return float(1.0 - (numer / denom))


def _top_weight_features(
    artifact: EfficacyModelArtifact,
    *,
    descending: bool,
    limit: int = 8,
) -> list[dict[str, float | str]]:
    pairs = list(zip(artifact.feature_names, artifact.weights, strict=True))
    pairs.sort(key=lambda item: item[1], reverse=descending)
    return [
        {"feature": name, "weight": round(weight, 6)}
        for name, weight in pairs[:limit]
    ]
