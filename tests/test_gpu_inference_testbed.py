from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from wellnessbox_rnd.gpu_testbed.pipeline import (
    InferenceBenchmarkConfig,
    benchmark_inference,
    build_feature_tensor,
    build_torch_effect_model,
    run_inference_testbed,
    verify_output_manifest,
)
from wellnessbox_rnd.models.effect_model_v1 import (
    EffectModelV1Artifact,
    load_effect_model_v1_artifact,
    predict_domain_deltas_v1,
)
from wellnessbox_rnd.training.effect_model_v1 import load_rich_effect_records

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "synthetic" / "synthetic_longitudinal_v4.jsonl"


def write_test_artifact(path: Path) -> Path:
    artifact = EffectModelV1Artifact(
        model_name="effect_model_test_fixture",
        cohort_version="synthetic_longitudinal_v4",
        seed=20260713,
        alpha=0.1,
        feature_names=["age", "baseline_aggregate_z"],
        output_names=["blood_glucose", "sleep_support"],
        intercepts=[0.1, -0.2],
        weights=[[0.01, 0.5], [-0.02, 0.25]],
    )
    path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_torch_model_matches_canonical_predictor(tmp_path: Path) -> None:
    artifact = load_effect_model_v1_artifact(write_test_artifact(tmp_path / "model.json"))
    records = load_rich_effect_records(DATASET)[:3]
    features = build_feature_tensor(artifact, records)
    model = build_torch_effect_model(artifact)

    actual = model(features).detach().numpy()
    expected = np.asarray(
        [
            list(predict_domain_deltas_v1(artifact, record).values())
            for record in records
        ],
        dtype=np.float32,
    )

    np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-5)


def test_cpu_benchmark_counts_all_rows(tmp_path: Path) -> None:
    artifact = load_effect_model_v1_artifact(write_test_artifact(tmp_path / "model.json"))
    records = load_rich_effect_records(DATASET)[:4]
    features = build_feature_tensor(artifact, records).repeat((8, 1))
    model = build_torch_effect_model(artifact)

    result, sample = benchmark_inference(
        model,
        features,
        device="cpu",
        iterations=3,
        warmup=1,
    )

    assert result.processed_rows == features.shape[0] * 3
    assert result.rows_per_second > 0
    assert result.elapsed_seconds > 0
    assert sample.shape == (min(16, features.shape[0]), len(artifact.output_names))


def test_run_writes_verified_output_contract(tmp_path: Path) -> None:
    artifact_path = write_test_artifact(tmp_path / "source_model.json")
    output_dir = tmp_path / "output"
    config = InferenceBenchmarkConfig(
        dataset_path=DATASET,
        artifact_path=artifact_path,
        output_dir=output_dir,
        devices=("cpu",),
        batch_size=64,
        iterations=2,
        warmup=1,
        require_cuda=False,
        provider="local",
        estimated_max_cost_krw=0.0,
    )

    result = run_inference_testbed(config)

    assert result.metrics_path == output_dir / "metrics.json"
    assert result.model_path == output_dir / "model_torchscript.pt"
    assert verify_output_manifest(output_dir / "manifest.json") == []
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["dataset"]["source_record_count"] > 0
    assert metrics["performance"]["cpu"]["processed_rows"] == 128
    assert metrics["correctness"]["comparison_status"] == "cpu_only"
    assert metrics["runtime_boundary"]["trained_new_model"] is False
    assert metrics["runtime_boundary"]["promoted_to_runtime"] is False


def test_require_cuda_rejects_cpu_only_device_list(tmp_path: Path) -> None:
    config = InferenceBenchmarkConfig(
        dataset_path=DATASET,
        artifact_path=write_test_artifact(tmp_path / "model.json"),
        output_dir=tmp_path,
        devices=("cpu",),
        batch_size=16,
        iterations=1,
        warmup=0,
        require_cuda=True,
    )

    try:
        run_inference_testbed(config)
    except ValueError as exc:
        assert str(exc) == "require_cuda=True requires 'cuda' in devices"
    else:
        raise AssertionError("run should reject a required CUDA device missing from devices")


def test_run_rejects_when_every_requested_device_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    config = InferenceBenchmarkConfig(
        dataset_path=DATASET,
        artifact_path=write_test_artifact(tmp_path / "model.json"),
        output_dir=tmp_path / "output",
        devices=("cuda",),
        batch_size=16,
        iterations=1,
        warmup=0,
        require_cuda=False,
    )

    try:
        run_inference_testbed(config)
    except RuntimeError as exc:
        assert str(exc) == "no requested inference device is available"
    else:
        raise AssertionError("run should fail when every requested device is unavailable")


def test_torchscript_output_is_loadable(tmp_path: Path) -> None:
    artifact_path = write_test_artifact(tmp_path / "source_model.json")
    output_dir = tmp_path / "output"
    config = InferenceBenchmarkConfig(
        dataset_path=DATASET,
        artifact_path=artifact_path,
        output_dir=output_dir,
        devices=("cpu",),
        batch_size=16,
        iterations=1,
        warmup=0,
        require_cuda=False,
    )
    run_inference_testbed(config)

    loaded = torch.jit.load(str(output_dir / "model_torchscript.pt"), map_location="cpu")
    output = loaded(torch.zeros((2, 2), dtype=torch.float32))

    assert output.shape == (2, 2)
