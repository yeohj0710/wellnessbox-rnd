from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel

from wellnessbox_rnd.models.policy_model_v1 import (
    PolicyFeatureVectorizerV1,
    PolicyModelV1Artifact,
    build_policy_feature_dict_v1,
    predict_policy_action_v1,
    predict_policy_scores_v1,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.policy.model_v0 import apply_policy_guard
from wellnessbox_rnd.schemas.recommendation import NextAction

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord


class PolicyTrainingRowV1(BaseModel):
    dataset_version: str = "policy_training_v1"
    record_id: str
    user_id: str
    trajectory_step: int
    day_index: int
    next_action: str
    deterministic_next_action: str
    safety_status: str
    risk_tier: str
    closed_loop_state: str
    feature_row: dict[str, float]


class PolicyEvaluationMetricsV1(BaseModel):
    raw_accuracy: float
    guarded_accuracy: float
    deterministic_accuracy: float
    majority_baseline_accuracy: float


@dataclass(frozen=True)
class PolicySplitResultV1:
    train: list[RichSyntheticCohortRecord]
    val: list[RichSyntheticCohortRecord]
    test: list[RichSyntheticCohortRecord]


def load_rich_synthetic_records(
    path: str | Path,
) -> list[RichSyntheticCohortRecord]:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord

    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(RichSyntheticCohortRecord.model_validate_json(line))
    return rows


def split_policy_records_by_user_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
) -> PolicySplitResultV1:
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

    return PolicySplitResultV1(
        train=sorted(buckets["train"], key=lambda item: item.record_id),
        val=sorted(buckets["val"], key=lambda item: item.record_id),
        test=sorted(buckets["test"], key=lambda item: item.record_id),
    )


def build_policy_training_rows_v1(
    records: list[RichSyntheticCohortRecord],
) -> list[PolicyTrainingRowV1]:
    rows: list[PolicyTrainingRowV1] = []
    for record in records:
        deterministic_action = recommend(record.request).next_action.value
        rows.append(
            PolicyTrainingRowV1(
                record_id=record.record_id,
                user_id=record.user_id,
                trajectory_step=record.trajectory_step,
                day_index=record.day_index,
                next_action=record.labels.next_action.value,
                deterministic_next_action=deterministic_action,
                safety_status=record.labels.safety_status.value,
                risk_tier=record.labels.risk_tier,
                closed_loop_state=record.labels.closed_loop_state,
                feature_row=build_policy_feature_dict_v1(record),
            )
        )
    return rows


def fit_policy_model_v1(
    train_records: list[RichSyntheticCohortRecord],
    val_records: list[RichSyntheticCohortRecord],
    *,
    seed: int,
    alpha_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 5.0, 10.0),
) -> tuple[PolicyModelV1Artifact, dict[str, PolicyEvaluationMetricsV1]]:
    train_rows = [build_policy_feature_dict_v1(record) for record in train_records]
    vectorizer = PolicyFeatureVectorizerV1.fit(train_rows)
    class_labels = sorted({record.labels.next_action.value for record in train_records})

    x_train = np.asarray(vectorizer.transform(train_rows), dtype=float)
    y_train = _build_label_matrix(train_records, class_labels)

    best_artifact: PolicyModelV1Artifact | None = None
    best_val_metrics: PolicyEvaluationMetricsV1 | None = None
    best_train_metrics: PolicyEvaluationMetricsV1 | None = None

    for alpha in alpha_grid:
        weights, intercepts = _fit_multiclass_ridge(x_train, y_train, alpha=alpha)
        artifact = PolicyModelV1Artifact(
            cohort_version=train_records[0].cohort_version if train_records else "unknown",
            seed=seed,
            alpha=alpha,
            class_labels=class_labels,
            feature_names=vectorizer.feature_names,
            intercepts=[round(float(value), 8) for value in intercepts],
            weights=[
                [round(float(weight), 8) for weight in class_weights] for class_weights in weights
            ],
        )
        train_metrics = evaluate_policy_model_v1(artifact, train_records)
        val_metrics = evaluate_policy_model_v1(artifact, val_records)
        if (
            best_val_metrics is None
            or val_metrics.guarded_accuracy > best_val_metrics.guarded_accuracy
        ):
            best_artifact = artifact
            best_val_metrics = val_metrics
            best_train_metrics = train_metrics

    assert best_artifact is not None
    assert best_val_metrics is not None
    assert best_train_metrics is not None
    return best_artifact, {"train": best_train_metrics, "val": best_val_metrics}


def evaluate_policy_model_v1(
    artifact: PolicyModelV1Artifact,
    records: list[RichSyntheticCohortRecord],
) -> PolicyEvaluationMetricsV1:
    actual = [record.labels.next_action.value for record in records]
    raw_predictions = [predict_policy_action_v1(artifact, record).value for record in records]
    deterministic_predictions = [recommend(record.request).next_action.value for record in records]
    guarded_predictions = [
        apply_policy_guard(
            predicted_action=NextAction(raw_prediction),
            deterministic_action=NextAction(deterministic_prediction),
        ).value
        for raw_prediction, deterministic_prediction in zip(
            raw_predictions,
            deterministic_predictions,
            strict=True,
        )
    ]
    majority_label = (
        max(
            sorted(set(actual)),
            key=lambda label: actual.count(label),
        )
        if actual
        else NextAction.CONTINUE_PLAN.value
    )
    majority_predictions = [majority_label] * len(actual)

    return PolicyEvaluationMetricsV1(
        raw_accuracy=round(_accuracy(actual, raw_predictions), 6),
        guarded_accuracy=round(_accuracy(actual, guarded_predictions), 6),
        deterministic_accuracy=round(_accuracy(actual, deterministic_predictions), 6),
        majority_baseline_accuracy=round(_accuracy(actual, majority_predictions), 6),
    )


def render_policy_training_report_v1(
    *,
    artifact: PolicyModelV1Artifact,
    split: PolicySplitResultV1,
    train_metrics: PolicyEvaluationMetricsV1,
    val_metrics: PolicyEvaluationMetricsV1,
    test_metrics: PolicyEvaluationMetricsV1,
    test_records: list[RichSyntheticCohortRecord],
) -> dict[str, object]:
    return {
        "model_name": artifact.model_name,
        "cohort_version": artifact.cohort_version,
        "seed": artifact.seed,
        "alpha": artifact.alpha,
        "feature_count": len(artifact.feature_names),
        "class_labels": artifact.class_labels,
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
        "top_class_features": {
            label: _top_weight_features(artifact, label) for label in artifact.class_labels
        },
        "sample_predictions": [
            {
                "record_id": record.record_id,
                "actual": record.labels.next_action.value,
                "raw_predicted": predict_policy_action_v1(artifact, record).value,
                "guarded_predicted": apply_policy_guard(
                    predicted_action=predict_policy_action_v1(artifact, record),
                    deterministic_action=recommend(record.request).next_action,
                ).value,
                "deterministic_predicted": recommend(record.request).next_action.value,
                "scores": predict_policy_scores_v1(artifact, record),
            }
            for record in test_records[:8]
        ],
    }


def render_policy_training_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# policy model v1 evaluation",
        "",
        f"- model_name: `{report['model_name']}`",
        f"- cohort_version: `{report['cohort_version']}`",
        f"- seed: `{report['seed']}`",
        f"- alpha: `{report['alpha']}`",
        f"- feature_count: `{report['feature_count']}`",
        f"- class_labels: `{', '.join(report['class_labels'])}`",
        "",
        "## Split Sizes",
    ]
    for key, value in report["split_record_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Metrics"])
    for split_name, metrics in report["metrics"].items():
        lines.append(
            f"- `{split_name}`: raw_accuracy=`{metrics['raw_accuracy']}`, "
            f"guarded_accuracy=`{metrics['guarded_accuracy']}`, "
            f"deterministic_accuracy=`{metrics['deterministic_accuracy']}`, "
            f"majority_baseline_accuracy=`{metrics['majority_baseline_accuracy']}`"
        )
    lines.extend(["", "## Top Class Features"])
    for label, items in report["top_class_features"].items():
        lines.append(f"`{label}`:")
        for item in items:
            lines.append(f"- `{item['feature']}`: `{item['weight']}`")
    return "\n".join(lines) + "\n"


def build_policy_feature_schema_v1(
    artifact: PolicyModelV1Artifact,
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
        "class_labels": artifact.class_labels,
        "feature_prefix_counts": dict(sorted(prefix_counts.items())),
        "feature_names": artifact.feature_names,
    }


def render_policy_feature_schema_markdown_v1(
    schema: dict[str, object],
) -> str:
    lines = [
        "# policy model v1 feature schema",
        "",
        f"- model_name: `{schema['model_name']}`",
        f"- cohort_version: `{schema['cohort_version']}`",
        f"- target_name: `{schema['target_name']}`",
        f"- feature_count: `{schema['feature_count']}`",
        f"- class_labels: `{', '.join(schema['class_labels'])}`",
        "",
        "## Feature Prefix Counts",
    ]
    for key, value in schema["feature_prefix_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Feature Names"])
    for feature_name in schema["feature_names"]:
        lines.append(f"- `{feature_name}`")
    return "\n".join(lines) + "\n"


def write_policy_training_outputs_v1(
    *,
    artifact: PolicyModelV1Artifact,
    report: dict[str, object],
    feature_schema: dict[str, object],
    policy_rows: list[PolicyTrainingRowV1],
    artifact_path: str | Path,
    report_json_path: str | Path,
    report_md_path: str | Path,
    split_json_path: str | Path,
    dataset_jsonl_path: str | Path,
    feature_schema_json_path: str | Path,
    feature_schema_md_path: str | Path,
    split: PolicySplitResultV1,
) -> None:
    artifact_target = Path(artifact_path)
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    split_json_target = Path(split_json_path)
    dataset_jsonl_target = Path(dataset_jsonl_path)
    feature_schema_json_target = Path(feature_schema_json_path)
    feature_schema_md_target = Path(feature_schema_md_path)
    for path in (
        artifact_target,
        report_json_target,
        report_md_target,
        split_json_target,
        dataset_jsonl_target,
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
        render_policy_training_markdown_v1(report),
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
    dataset_jsonl_target.write_text(
        "\n".join(row.model_dump_json() for row in policy_rows) + "\n",
        encoding="utf-8",
    )
    feature_schema_json_target.write_text(
        json.dumps(feature_schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    feature_schema_md_target.write_text(
        render_policy_feature_schema_markdown_v1(feature_schema),
        encoding="utf-8",
    )


def _build_label_matrix(
    records: list[RichSyntheticCohortRecord],
    class_labels: list[str],
) -> np.ndarray:
    label_to_index = {label: idx for idx, label in enumerate(class_labels)}
    matrix = np.zeros((len(records), len(class_labels)), dtype=float)
    for row_index, record in enumerate(records):
        matrix[row_index, label_to_index[record.labels.next_action.value]] = 1.0
    return matrix


def _fit_multiclass_ridge(
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


def _accuracy(actual: list[str], predicted: list[str]) -> float:
    if not actual:
        return 0.0
    correct = sum(1 for truth, guess in zip(actual, predicted, strict=True) if truth == guess)
    return correct / len(actual)


def _top_weight_features(
    artifact: PolicyModelV1Artifact,
    label: str,
    *,
    limit: int = 8,
) -> list[dict[str, float | str]]:
    class_index = artifact.class_labels.index(label)
    pairs = list(zip(artifact.feature_names, artifact.weights[class_index], strict=True))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    return [{"feature": name, "weight": round(weight, 6)} for name, weight in pairs[:limit]]
