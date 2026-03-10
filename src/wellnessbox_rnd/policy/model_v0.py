from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from wellnessbox_rnd.models.policy_model_v0 import (
    PolicyFeatureVectorizer,
    PolicyModelArtifact,
    build_policy_feature_dict,
    predict_policy_action,
    predict_policy_scores,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import NextAction
from wellnessbox_rnd.synthetic.longitudinal import SyntheticCohortRecord


class PolicyTrainingRow(BaseModel):
    record_id: str
    user_id: str
    follow_up_step: int
    next_action: str
    deterministic_next_action: str
    feature_row: dict[str, float]


class PolicyEvaluationMetrics(BaseModel):
    raw_accuracy: float
    guarded_accuracy: float
    deterministic_accuracy: float
    majority_baseline_accuracy: float


@dataclass(frozen=True)
class PolicySplitResult:
    train: list[SyntheticCohortRecord]
    val: list[SyntheticCohortRecord]
    test: list[SyntheticCohortRecord]


def split_policy_records_by_user(
    records: list[SyntheticCohortRecord],
    *,
    seed: int,
) -> PolicySplitResult:
    grouped: dict[str, list[SyntheticCohortRecord]] = {}
    for record in records:
        grouped.setdefault(record.user_id, []).append(record)

    buckets: dict[str, list[SyntheticCohortRecord]] = {"train": [], "val": [], "test": []}
    for user_id in sorted(grouped):
        digest = hashlib.sha256(f"{seed}:{user_id}".encode()).digest()[0]
        ratio = digest / 255.0
        split_name = "train" if ratio < 0.6 else "val" if ratio < 0.8 else "test"
        buckets[split_name].extend(grouped[user_id])

    return PolicySplitResult(
        train=sorted(buckets["train"], key=lambda item: item.record_id),
        val=sorted(buckets["val"], key=lambda item: item.record_id),
        test=sorted(buckets["test"], key=lambda item: item.record_id),
    )


def build_policy_training_rows(
    records: list[SyntheticCohortRecord],
) -> list[PolicyTrainingRow]:
    rows: list[PolicyTrainingRow] = []
    for record in records:
        deterministic_action = recommend(record.request).next_action.value
        rows.append(
            PolicyTrainingRow(
                record_id=record.record_id,
                user_id=record.user_id,
                follow_up_step=record.follow_up_step,
                next_action=record.labels.next_action.value,
                deterministic_next_action=deterministic_action,
                feature_row=build_policy_feature_dict(record),
            )
        )
    return rows


def fit_policy_model(
    train_records: list[SyntheticCohortRecord],
    val_records: list[SyntheticCohortRecord],
    *,
    seed: int,
    alpha_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 5.0, 10.0),
) -> tuple[PolicyModelArtifact, dict[str, PolicyEvaluationMetrics]]:
    train_rows = [build_policy_feature_dict(record) for record in train_records]
    vectorizer = PolicyFeatureVectorizer.fit(train_rows)
    class_labels = sorted({record.labels.next_action.value for record in train_records})

    x_train = np.asarray(vectorizer.transform(train_rows), dtype=float)
    y_train = _build_label_matrix(train_records, class_labels)

    best_artifact: PolicyModelArtifact | None = None
    best_val_metrics: PolicyEvaluationMetrics | None = None
    best_train_metrics: PolicyEvaluationMetrics | None = None

    for alpha in alpha_grid:
        weights, intercepts = _fit_multiclass_ridge(x_train, y_train, alpha=alpha)
        artifact = PolicyModelArtifact(
            cohort_version=train_records[0].cohort_version if train_records else "unknown",
            seed=seed,
            alpha=alpha,
            class_labels=class_labels,
            feature_names=vectorizer.feature_names,
            intercepts=[round(float(value), 8) for value in intercepts],
            weights=[
                [round(float(weight), 8) for weight in class_weights]
                for class_weights in weights
            ],
        )
        train_metrics = evaluate_policy_model(artifact, train_records)
        val_metrics = evaluate_policy_model(artifact, val_records)
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


def evaluate_policy_model(
    artifact: PolicyModelArtifact,
    records: list[SyntheticCohortRecord],
) -> PolicyEvaluationMetrics:
    actual = [record.labels.next_action.value for record in records]
    raw_predictions = [predict_policy_action(artifact, record).value for record in records]
    deterministic_predictions = [
        recommend(record.request).next_action.value for record in records
    ]
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
    majority_label = max(
        sorted(set(actual)),
        key=lambda label: actual.count(label),
    ) if actual else NextAction.START_PLAN.value
    majority_predictions = [majority_label] * len(actual)

    return PolicyEvaluationMetrics(
        raw_accuracy=round(_accuracy(actual, raw_predictions), 6),
        guarded_accuracy=round(_accuracy(actual, guarded_predictions), 6),
        deterministic_accuracy=round(_accuracy(actual, deterministic_predictions), 6),
        majority_baseline_accuracy=round(_accuracy(actual, majority_predictions), 6),
    )


def apply_policy_guard(
    *,
    predicted_action: NextAction,
    deterministic_action: NextAction,
) -> NextAction:
    if _action_rank(predicted_action) < _action_rank(deterministic_action):
        return deterministic_action
    return predicted_action


def render_policy_training_report(
    *,
    artifact: PolicyModelArtifact,
    split: PolicySplitResult,
    train_metrics: PolicyEvaluationMetrics,
    val_metrics: PolicyEvaluationMetrics,
    test_metrics: PolicyEvaluationMetrics,
    test_records: list[SyntheticCohortRecord],
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
            label: _top_weight_features(artifact, label)
            for label in artifact.class_labels
        },
        "sample_predictions": [
            {
                "record_id": record.record_id,
                "actual": record.labels.next_action.value,
                "raw_predicted": predict_policy_action(artifact, record).value,
                "guarded_predicted": apply_policy_guard(
                    predicted_action=predict_policy_action(artifact, record),
                    deterministic_action=recommend(record.request).next_action,
                ).value,
                "deterministic_predicted": recommend(record.request).next_action.value,
                "scores": predict_policy_scores(artifact, record),
            }
            for record in test_records[:5]
        ],
    }


def render_policy_training_markdown(report: dict[str, object]) -> str:
    lines = [
        "# policy model v0 evaluation",
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


def write_policy_training_outputs(
    *,
    artifact: PolicyModelArtifact,
    report: dict[str, object],
    policy_rows: list[PolicyTrainingRow],
    artifact_path: str | Path,
    report_json_path: str | Path,
    report_md_path: str | Path,
    split_json_path: str | Path,
    dataset_jsonl_path: str | Path,
    split: PolicySplitResult,
) -> None:
    artifact_target = Path(artifact_path)
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    split_json_target = Path(split_json_path)
    dataset_jsonl_target = Path(dataset_jsonl_path)
    for path in (
        artifact_target,
        report_json_target,
        report_md_target,
        split_json_target,
        dataset_jsonl_target,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    artifact_target.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(
        render_policy_training_markdown(report),
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


def load_policy_training_rows(path: str | Path) -> list[PolicyTrainingRow]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(PolicyTrainingRow.model_validate_json(line))
    return rows


def _build_label_matrix(
    records: list[SyntheticCohortRecord],
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
    correct = sum(
        1 for truth, guess in zip(actual, predicted, strict=True) if truth == guess
    )
    return correct / len(actual)


def _action_rank(action: NextAction) -> int:
    ranks = {
        NextAction.START_PLAN: 0,
        NextAction.CONTINUE_PLAN: 0,
        NextAction.MONITOR_ONLY: 0,
        NextAction.RE_OPTIMIZE: 0,
        NextAction.ASK_TARGETED_FOLLOWUP: 1,
        NextAction.COLLECT_MORE_INPUT: 1,
        NextAction.REDUCE_OR_STOP: 2,
        NextAction.TRIGGER_SAFETY_RECHECK: 2,
        NextAction.BLOCKED: 3,
    }
    return ranks[action]


def _top_weight_features(
    artifact: PolicyModelArtifact,
    label: str,
    *,
    limit: int = 8,
) -> list[dict[str, float | str]]:
    class_index = artifact.class_labels.index(label)
    pairs = list(zip(artifact.feature_names, artifact.weights[class_index], strict=True))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    return [
        {"feature": name, "weight": round(weight, 6)}
        for name, weight in pairs[:limit]
    ]
