from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel

from wellnessbox_rnd.models.effect_model_v1 import (
    EffectFeatureVectorizerV1,
    EffectModelV1Artifact,
    build_effect_feature_dict_v1,
    predict_aggregate_delta_v1,
    predict_domain_deltas_v1,
)

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord


class EffectEvaluationMetricsV1(BaseModel):
    mean_domain_mae: float
    mean_domain_rmse: float
    aggregate_mae: float
    aggregate_rmse: float
    aggregate_r2: float
    zero_baseline_mean_domain_mae: float
    zero_baseline_aggregate_mae: float
    domain_mae: dict[str, float]


@dataclass(frozen=True)
class EffectSplitResultV1:
    train: list[RichSyntheticCohortRecord]
    val: list[RichSyntheticCohortRecord]
    test: list[RichSyntheticCohortRecord]


def load_rich_effect_records(
    path: str | Path,
) -> list[RichSyntheticCohortRecord]:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord

    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(RichSyntheticCohortRecord.model_validate_json(line))
    return rows


def split_effect_records_by_user_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
) -> EffectSplitResultV1:
    grouped: dict[str, list[RichSyntheticCohortRecord]] = {}
    for record in records:
        grouped.setdefault(record.user_id, []).append(record)

    buckets: dict[str, list[RichSyntheticCohortRecord]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    for user_id in sorted(grouped):
        digest = hashlib.sha256(f"{seed}:{user_id}".encode()).digest()[0]
        ratio = digest / 255.0
        split_name = "train" if ratio < 0.6 else "val" if ratio < 0.8 else "test"
        buckets[split_name].extend(grouped[user_id])

    return EffectSplitResultV1(
        train=sorted(buckets["train"], key=lambda item: item.record_id),
        val=sorted(buckets["val"], key=lambda item: item.record_id),
        test=sorted(buckets["test"], key=lambda item: item.record_id),
    )


def fit_effect_model_v1(
    train_records: list[RichSyntheticCohortRecord],
    val_records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
    alpha_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 5.0, 10.0),
) -> tuple[EffectModelV1Artifact, dict[str, EffectEvaluationMetricsV1]]:
    train_rows = [build_effect_feature_dict_v1(record) for record in train_records]
    vectorizer = EffectFeatureVectorizerV1.fit(train_rows)
    output_names = sorted(train_records[0].delta_z_by_domain) if train_records else []

    x_train = np.asarray(vectorizer.transform(train_rows), dtype=float)
    y_train = _build_target_matrix(train_records, output_names)

    best_artifact: EffectModelV1Artifact | None = None
    best_val_metrics: EffectEvaluationMetricsV1 | None = None
    best_train_metrics: EffectEvaluationMetricsV1 | None = None

    for alpha in alpha_grid:
        weights, intercepts = _fit_multitarget_ridge(x_train, y_train, alpha=alpha)
        artifact = EffectModelV1Artifact(
            cohort_version=train_records[0].cohort_version if train_records else "unknown",
            seed=seed,
            alpha=alpha,
            feature_names=vectorizer.feature_names,
            output_names=output_names,
            intercepts=[round(float(value), 8) for value in intercepts],
            weights=[
                [round(float(weight), 8) for weight in output_weights]
                for output_weights in weights
            ],
        )
        train_metrics = evaluate_effect_model_v1(artifact, train_records)
        val_metrics = evaluate_effect_model_v1(artifact, val_records)
        if (
            best_val_metrics is None
            or val_metrics.aggregate_mae < best_val_metrics.aggregate_mae
        ):
            best_artifact = artifact
            best_val_metrics = val_metrics
            best_train_metrics = train_metrics

    assert best_artifact is not None
    assert best_val_metrics is not None
    assert best_train_metrics is not None
    return best_artifact, {"train": best_train_metrics, "val": best_val_metrics}


def evaluate_effect_model_v1(
    artifact: EffectModelV1Artifact,
    records: list[RichSyntheticCohortRecord],
) -> EffectEvaluationMetricsV1:
    actual_matrix = np.asarray(
        [
            [record.delta_z_by_domain[output_name] for output_name in artifact.output_names]
            for record in records
        ],
        dtype=float,
    )
    predicted_matrix = np.asarray(
        [
            [
                predict_domain_deltas_v1(artifact, record)[output_name]
                for output_name in artifact.output_names
            ]
            for record in records
        ],
        dtype=float,
    )
    zero_matrix = np.zeros_like(actual_matrix)

    domain_mae = {
        output_name: round(
            _mae(actual_matrix[:, index], predicted_matrix[:, index]),
            6,
        )
        for index, output_name in enumerate(artifact.output_names)
    }
    actual_aggregate = (
        actual_matrix.mean(axis=1) if len(actual_matrix) else np.asarray([], dtype=float)
    )
    predicted_aggregate = np.asarray(
        [predict_aggregate_delta_v1(artifact, record) for record in records],
        dtype=float,
    )
    zero_aggregate = np.zeros_like(actual_aggregate)

    return EffectEvaluationMetricsV1(
        mean_domain_mae=round(
            float(np.mean(np.abs(actual_matrix - predicted_matrix))) if len(actual_matrix) else 0.0,
            6,
        ),
        mean_domain_rmse=round(
            float(sqrt(np.mean((actual_matrix - predicted_matrix) ** 2)))
            if len(actual_matrix)
            else 0.0,
            6,
        ),
        aggregate_mae=round(_mae(actual_aggregate, predicted_aggregate), 6),
        aggregate_rmse=round(_rmse(actual_aggregate, predicted_aggregate), 6),
        aggregate_r2=round(_r2(actual_aggregate, predicted_aggregate), 6),
        zero_baseline_mean_domain_mae=round(
            float(np.mean(np.abs(actual_matrix - zero_matrix))) if len(actual_matrix) else 0.0,
            6,
        ),
        zero_baseline_aggregate_mae=round(
            _mae(actual_aggregate, zero_aggregate),
            6,
        ),
        domain_mae=domain_mae,
    )


def build_effect_feature_schema_v1(
    artifact: EffectModelV1Artifact,
) -> dict[str, object]:
    prefix_counts: dict[str, int] = {}
    for feature_name in artifact.feature_names:
        prefix = feature_name.split("::", 1)[0] if "::" in feature_name else "scalar"
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    return {
        "model_name": artifact.model_name,
        "target_name": artifact.target_name,
        "cohort_version": artifact.cohort_version,
        "feature_count": len(artifact.feature_names),
        "output_names": artifact.output_names,
        "feature_prefix_counts": dict(sorted(prefix_counts.items())),
        "feature_names": artifact.feature_names,
    }


def render_effect_training_report_v1(
    *,
    artifact: EffectModelV1Artifact,
    split: EffectSplitResultV1,
    train_metrics: EffectEvaluationMetricsV1,
    val_metrics: EffectEvaluationMetricsV1,
    test_metrics: EffectEvaluationMetricsV1,
    test_records: list[RichSyntheticCohortRecord],
) -> dict[str, object]:
    return {
        "model_name": artifact.model_name,
        "cohort_version": artifact.cohort_version,
        "seed": artifact.seed,
        "alpha": artifact.alpha,
        "feature_count": len(artifact.feature_names),
        "output_names": artifact.output_names,
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
        "top_output_features": {
            output_name: _top_weight_features(artifact, output_name)
            for output_name in artifact.output_names
        },
        "sample_predictions": [
            {
                "record_id": record.record_id,
                "actual_domain_delta": record.delta_z_by_domain,
                "predicted_domain_delta": predict_domain_deltas_v1(artifact, record),
                "actual_aggregate_delta": round(
                    sum(record.delta_z_by_domain.values()) / len(record.delta_z_by_domain),
                    6,
                ),
                "predicted_aggregate_delta": predict_aggregate_delta_v1(artifact, record),
            }
            for record in test_records[:5]
        ],
    }


def render_effect_training_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# effect model v1 evaluation",
        "",
        f"- model_name: `{report['model_name']}`",
        f"- cohort_version: `{report['cohort_version']}`",
        f"- seed: `{report['seed']}`",
        f"- alpha: `{report['alpha']}`",
        f"- feature_count: `{report['feature_count']}`",
        f"- output_names: `{', '.join(report['output_names'])}`",
        "",
        "## Split Sizes",
    ]
    for key, value in report["split_record_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Metrics"])
    for split_name, metrics in report["metrics"].items():
        lines.append(
            f"- `{split_name}`: "
            f"mean_domain_mae=`{metrics['mean_domain_mae']}`, "
            f"aggregate_mae=`{metrics['aggregate_mae']}`, "
            f"aggregate_rmse=`{metrics['aggregate_rmse']}`, "
            f"aggregate_r2=`{metrics['aggregate_r2']}`, "
            f"zero_baseline_aggregate_mae=`{metrics['zero_baseline_aggregate_mae']}`"
        )
    return "\n".join(lines) + "\n"


def render_effect_feature_schema_markdown_v1(schema: dict[str, object]) -> str:
    lines = [
        "# effect model v1 feature schema",
        "",
        f"- model_name: `{schema['model_name']}`",
        f"- cohort_version: `{schema['cohort_version']}`",
        f"- target_name: `{schema['target_name']}`",
        f"- feature_count: `{schema['feature_count']}`",
        f"- output_names: `{', '.join(schema['output_names'])}`",
        "",
        "## Feature Prefix Counts",
    ]
    for key, value in schema["feature_prefix_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Feature Names"])
    for feature_name in schema["feature_names"]:
        lines.append(f"- `{feature_name}`")
    return "\n".join(lines) + "\n"


def write_effect_training_outputs_v1(
    *,
    artifact: EffectModelV1Artifact,
    report: dict[str, object],
    feature_schema: dict[str, object],
    artifact_path: str | Path,
    report_json_path: str | Path,
    report_md_path: str | Path,
    split_json_path: str | Path,
    feature_schema_json_path: str | Path,
    feature_schema_md_path: str | Path,
    split: EffectSplitResultV1,
) -> None:
    artifact_target = Path(artifact_path)
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    split_json_target = Path(split_json_path)
    feature_schema_json_target = Path(feature_schema_json_path)
    feature_schema_md_target = Path(feature_schema_md_path)
    for path in (
        artifact_target,
        report_json_target,
        report_md_target,
        split_json_target,
        feature_schema_json_target,
        feature_schema_md_target,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    artifact_target.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(
        render_effect_training_markdown_v1(report),
        encoding="utf-8",
    )
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
    feature_schema_json_target.write_text(
        json.dumps(feature_schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    feature_schema_md_target.write_text(
        render_effect_feature_schema_markdown_v1(feature_schema),
        encoding="utf-8",
    )


def _build_target_matrix(
    records: list[RichSyntheticCohortRecord],
    output_names: list[str],
) -> np.ndarray:
    return np.asarray(
        [
            [record.delta_z_by_domain[output_name] for output_name in output_names]
            for record in records
        ],
        dtype=float,
    )


def _fit_multitarget_ridge(
    x: np.ndarray,
    y: np.ndarray,
    *,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray]:
    x_bias = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    regularizer = np.eye(x_bias.shape[1]) * alpha
    regularizer[0, 0] = 0.0
    solution = np.linalg.pinv(x_bias.T @ x_bias + regularizer) @ x_bias.T @ y
    intercepts = solution[0]
    weights = solution[1:].T
    return weights, intercepts


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    return float(np.mean(np.abs(actual - predicted)))


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    return float(sqrt(np.mean((actual - predicted) ** 2)))


def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    baseline = np.mean(actual)
    denom = np.sum((actual - baseline) ** 2)
    if denom == 0:
        return 0.0
    numer = np.sum((actual - predicted) ** 2)
    return float(1.0 - (numer / denom))


def _top_weight_features(
    artifact: EffectModelV1Artifact,
    output_name: str,
    *,
    limit: int = 8,
) -> list[dict[str, float | str]]:
    output_index = artifact.output_names.index(output_name)
    pairs = list(zip(artifact.feature_names, artifact.weights[output_index], strict=True))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    return [
        {"feature": name, "weight": round(weight, 6)}
        for name, weight in pairs[:limit]
    ]
