from __future__ import annotations

import copy
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Any

import torch
from torch import Tensor, nn

from wellnessbox_rnd.models.effect_model_v1 import (
    EffectFeatureVectorizerV1,
    EffectModelV1Artifact,
    build_effect_feature_dict_v1,
    load_effect_model_v1_artifact,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord
from wellnessbox_rnd.training.effect_model_v1 import load_rich_effect_records

MANIFEST_SCHEMA_VERSION = "gpu_inference_output_manifest_v1"
METRICS_SCHEMA_VERSION = "gpu_inference_metrics_v1"
FLOAT32_EQUIVALENCE_ATOL = 1e-4
SAMPLE_ROW_COUNT = 16


@dataclass(frozen=True)
class InferenceBenchmarkConfig:
    dataset_path: Path
    artifact_path: Path
    output_dir: Path
    devices: tuple[str, ...] = ("cpu", "cuda")
    batch_size: int = 262_144
    iterations: int = 40
    warmup: int = 3
    require_cuda: bool = True
    seed: int = 20260713
    provider: str = "local"
    estimated_max_cost_krw: float = 0.0

    def __post_init__(self) -> None:
        unsupported = set(self.devices) - {"cpu", "cuda"}
        if unsupported:
            raise ValueError(f"unsupported devices: {sorted(unsupported)}")
        if not self.devices:
            raise ValueError("devices must not be empty")
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.iterations < 1:
            raise ValueError("iterations must be positive")
        if self.warmup < 0:
            raise ValueError("warmup must be non-negative")
        if self.estimated_max_cost_krw < 0:
            raise ValueError("estimated_max_cost_krw must be non-negative")


@dataclass(frozen=True)
class DeviceBenchmarkResult:
    device: str
    device_name: str
    batch_size: int
    iterations: int
    warmup: int
    processed_rows: int
    elapsed_seconds: float
    rows_per_second: float
    transfer_seconds: float
    output_checksum: float


@dataclass(frozen=True)
class InferenceTestbedResult:
    output_dir: Path
    metrics_path: Path
    model_path: Path
    predictions_path: Path
    events_path: Path
    log_path: Path
    manifest_path: Path


class TorchEffectLinear(nn.Module):
    """Float32 Torch equivalent of the existing multi-output ridge artifact."""

    def __init__(self, artifact: EffectModelV1Artifact) -> None:
        super().__init__()
        input_count = len(artifact.feature_names)
        output_count = len(artifact.output_names)
        if input_count == 0 or output_count == 0:
            raise ValueError("artifact must define non-empty feature and output names")
        if len(artifact.weights) != output_count or len(artifact.intercepts) != output_count:
            raise ValueError("artifact output, weight, and intercept counts must match")
        if any(len(row) != input_count for row in artifact.weights):
            raise ValueError("every artifact weight row must match feature count")

        self.linear = nn.Linear(input_count, output_count)
        with torch.no_grad():
            self.linear.weight.copy_(torch.tensor(artifact.weights, dtype=torch.float32))
            self.linear.bias.copy_(torch.tensor(artifact.intercepts, dtype=torch.float32))

    def forward(self, features: Tensor) -> Tensor:
        return self.linear(features)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _write_json_atomic(path: Path, payload: object) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _synchronize(device: str) -> None:
    if device == "cuda":
        torch.cuda.synchronize()


def build_feature_tensor(
    artifact: EffectModelV1Artifact,
    records: list[RichSyntheticCohortRecord],
) -> Tensor:
    if not records:
        raise ValueError("dataset contains no records")
    feature_rows = [build_effect_feature_dict_v1(record) for record in records]
    matrix = EffectFeatureVectorizerV1(artifact.feature_names).transform(feature_rows)
    return torch.tensor(matrix, dtype=torch.float32).contiguous()


def build_torch_effect_model(artifact: EffectModelV1Artifact) -> TorchEffectLinear:
    return TorchEffectLinear(artifact).eval()


def build_benchmark_batch(features: Tensor, batch_size: int) -> Tensor:
    if features.ndim != 2 or features.shape[0] == 0:
        raise ValueError("features must be a non-empty rank-2 tensor")
    repeats = ceil(batch_size / features.shape[0])
    return features.repeat((repeats, 1))[:batch_size].contiguous()


def _device_name(device: str) -> str:
    if device == "cuda":
        return torch.cuda.get_device_name(0)
    return platform.processor() or "CPU"


def benchmark_inference(
    model: nn.Module,
    features: Tensor,
    *,
    device: str,
    iterations: int,
    warmup: int,
) -> tuple[DeviceBenchmarkResult, Tensor]:
    if device not in {"cpu", "cuda"}:
        raise ValueError(f"unsupported device: {device}")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is false")
    if iterations < 1 or warmup < 0:
        raise ValueError("iterations must be positive and warmup must be non-negative")

    transfer_started = perf_counter()
    device_model = copy.deepcopy(model).to(device).eval()
    device_features = features.to(device)
    _synchronize(device)
    transfer_seconds = perf_counter() - transfer_started

    with torch.inference_mode():
        output = device_model(device_features)
        for _ in range(warmup):
            output = device_model(device_features)
        _synchronize(device)
        started = perf_counter()
        for _ in range(iterations):
            output = device_model(device_features)
        _synchronize(device)
        elapsed_seconds = perf_counter() - started

    sample = output[: min(SAMPLE_ROW_COUNT, output.shape[0])].detach().cpu()
    processed_rows = int(features.shape[0]) * iterations
    result = DeviceBenchmarkResult(
        device=device,
        device_name=_device_name(device),
        batch_size=int(features.shape[0]),
        iterations=iterations,
        warmup=warmup,
        processed_rows=processed_rows,
        elapsed_seconds=round(elapsed_seconds, 9),
        rows_per_second=round(processed_rows / elapsed_seconds, 3),
        transfer_seconds=round(transfer_seconds, 9),
        output_checksum=round(float(sample.double().sum().item()), 9),
    )
    return result, sample


def _environment_payload() -> dict[str, object]:
    cuda_available = torch.cuda.is_available()
    payload: dict[str, object] = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": cuda_available,
        "cuda_device_count": torch.cuda.device_count() if cuda_available else 0,
        "cpu_thread_count": torch.get_num_threads(),
    }
    if cuda_available:
        properties = torch.cuda.get_device_properties(0)
        payload["cuda_device_name"] = properties.name
        payload["cuda_total_memory_bytes"] = properties.total_memory
        payload["cuda_capability"] = list(torch.cuda.get_device_capability(0))
    return payload


def _event(name: str, **details: object) -> dict[str, object]:
    return {"timestamp": _utc_now(), "event": name, **details}


def _save_torchscript(model: nn.Module, path: Path) -> None:
    scripted = torch.jit.script(copy.deepcopy(model).cpu().eval())
    temporary = path.with_name(f".{path.name}.tmp")
    torch.jit.save(scripted, str(temporary))
    temporary.replace(path)


def _write_predictions(
    path: Path,
    records: list[RichSyntheticCohortRecord],
    output_names: list[str],
    sample: Tensor,
) -> None:
    lines = []
    for index, values in enumerate(sample.tolist()):
        record = records[index % len(records)]
        payload = {
            "record_id": record.record_id,
            "user_id": record.user_id,
            "predictions": dict(zip(output_names, values, strict=True)),
        }
        lines.append(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    _write_text_atomic(path, "\n".join(lines) + "\n")


def _write_manifest(output_dir: Path, path: Path) -> None:
    files = []
    for candidate in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if candidate.is_file() and candidate != path and not candidate.name.startswith("."):
            files.append(
                {
                    "path": candidate.name,
                    "bytes": candidate.stat().st_size,
                    "sha256": _sha256(candidate),
                }
            )
    _write_json_atomic(path, {"schema_version": MANIFEST_SCHEMA_VERSION, "files": files})


def verify_output_manifest(path: str | Path) -> list[str]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("unsupported manifest schema")
    for item in payload.get("files", []):
        name = item.get("path")
        if not isinstance(name, str) or Path(name).name != name:
            errors.append(f"unsafe manifest path: {name!r}")
            continue
        candidate = manifest_path.parent / name
        if not candidate.is_file():
            errors.append(f"missing file: {name}")
            continue
        if candidate.stat().st_size != item.get("bytes"):
            errors.append(f"size mismatch: {name}")
        if _sha256(candidate) != item.get("sha256"):
            errors.append(f"sha256 mismatch: {name}")
    return errors


def _correctness_payload(samples: dict[str, Tensor]) -> dict[str, object]:
    if "cpu" not in samples or "cuda" not in samples:
        return {
            "comparison_status": "cpu_only" if "cpu" in samples else "single_device",
            "float32_absolute_tolerance": FLOAT32_EQUIVALENCE_ATOL,
            "max_abs_diff": None,
        }
    max_abs_diff = float(torch.max(torch.abs(samples["cpu"] - samples["cuda"])).item())
    if max_abs_diff > FLOAT32_EQUIVALENCE_ATOL:
        raise RuntimeError(
            "CPU/CUDA output mismatch: "
            f"max_abs_diff={max_abs_diff} > {FLOAT32_EQUIVALENCE_ATOL}"
        )
    return {
        "comparison_status": "matched",
        "float32_absolute_tolerance": FLOAT32_EQUIVALENCE_ATOL,
        "max_abs_diff": max_abs_diff,
    }


def _performance_payload(
    results: dict[str, DeviceBenchmarkResult],
) -> tuple[dict[str, dict[str, Any]], float | None]:
    payload = {device: asdict(result) for device, result in results.items()}
    speedup = None
    if "cpu" in results and "cuda" in results:
        speedup = round(
            results["cuda"].rows_per_second / results["cpu"].rows_per_second,
            4,
        )
    return payload, speedup


def run_inference_testbed(config: InferenceBenchmarkConfig) -> InferenceTestbedResult:
    if config.require_cuda and "cuda" not in config.devices:
        raise ValueError("require_cuda=True requires 'cuda' in devices")
    if not config.dataset_path.is_file():
        raise FileNotFoundError(f"dataset not found: {config.dataset_path}")
    if not config.artifact_path.is_file():
        raise FileNotFoundError(f"artifact not found: {config.artifact_path}")
    if config.require_cuda and not torch.cuda.is_available():
        raise RuntimeError("CUDA required but torch.cuda.is_available() is false")

    torch.manual_seed(config.seed)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    events = [_event("run_started", provider=config.provider)]

    artifact = load_effect_model_v1_artifact(config.artifact_path)
    records = load_rich_effect_records(config.dataset_path)
    features = build_feature_tensor(artifact, records)
    benchmark_batch = build_benchmark_batch(features, config.batch_size)
    model = build_torch_effect_model(artifact)
    unique_user_count = len({record.user_id for record in records})
    events.append(
        _event(
            "dataset_loaded",
            source_record_count=len(records),
            unique_user_count=unique_user_count,
            feature_count=features.shape[1],
        )
    )

    results: dict[str, DeviceBenchmarkResult] = {}
    samples: dict[str, Tensor] = {}
    for device in config.devices:
        if device == "cuda" and not torch.cuda.is_available():
            events.append(_event("device_skipped", device=device, reason="cuda_unavailable"))
            continue
        result, sample = benchmark_inference(
            model,
            benchmark_batch,
            device=device,
            iterations=config.iterations,
            warmup=config.warmup,
        )
        results[device] = result
        samples[device] = sample
        events.append(
            _event(
                "device_benchmark_completed",
                device=device,
                elapsed_seconds=result.elapsed_seconds,
                rows_per_second=result.rows_per_second,
            )
        )

    if not samples:
        raise RuntimeError("no requested inference device is available")

    correctness = _correctness_payload(samples)
    performance, speedup = _performance_payload(results)
    completed_at = _utc_now()
    events.append(
        _event(
            "run_completed",
            comparison_status=correctness["comparison_status"],
            cuda_speedup_vs_cpu=speedup,
        )
    )

    metrics_path = config.output_dir / "metrics.json"
    model_path = config.output_dir / "model_torchscript.pt"
    predictions_path = config.output_dir / "predictions_sample.jsonl"
    events_path = config.output_dir / "events.jsonl"
    log_path = config.output_dir / "run.log"
    manifest_path = config.output_dir / "manifest.json"

    metrics = {
        "schema_version": METRICS_SCHEMA_VERSION,
        "started_at": started_at,
        "completed_at": completed_at,
        "provider": config.provider,
        "estimated_max_cost_krw_vat_excluded": config.estimated_max_cost_krw,
        "configuration": {
            "devices": list(config.devices),
            "batch_size": config.batch_size,
            "iterations": config.iterations,
            "warmup": config.warmup,
            "require_cuda": config.require_cuda,
            "seed": config.seed,
        },
        "environment": _environment_payload(),
        "dataset": {
            "path": str(config.dataset_path),
            "sha256": _sha256(config.dataset_path),
            "source_record_count": len(records),
            "unique_user_count": unique_user_count,
            "benchmark_batch_rows": int(benchmark_batch.shape[0]),
            "feature_count": int(benchmark_batch.shape[1]),
        },
        "model": {
            "source_path": str(config.artifact_path),
            "source_sha256": _sha256(config.artifact_path),
            "model_name": artifact.model_name,
            "cohort_version": artifact.cohort_version,
            "output_count": len(artifact.output_names),
            "output_names": artifact.output_names,
            "torch_conversion": "single_float32_linear_layer",
        },
        "performance": performance,
        "cuda_speedup_vs_cpu": speedup,
        "correctness": correctness,
        "runtime_boundary": {
            "trained_new_model": False,
            "promoted_to_runtime": False,
            "artifact_status": "existing_replay_only_held_candidate",
            "deterministic_safety_changed": False,
        },
    }

    _save_torchscript(model, model_path)
    preferred_sample = samples["cpu"] if "cpu" in samples else next(iter(samples.values()))
    _write_predictions(predictions_path, records, artifact.output_names, preferred_sample)
    _write_json_atomic(metrics_path, metrics)
    _write_text_atomic(
        events_path,
        "\n".join(json.dumps(item, ensure_ascii=False) for item in events) + "\n",
    )
    log_lines = [
        f"started_at={started_at}",
        f"completed_at={completed_at}",
        f"provider={config.provider}",
        f"source_records={len(records)}",
        f"unique_users={unique_user_count}",
        f"benchmark_batch_rows={config.batch_size}",
    ]
    for device, result in results.items():
        log_lines.append(
            f"{device}_elapsed_seconds={result.elapsed_seconds} "
            f"{device}_rows_per_second={result.rows_per_second}"
        )
    log_lines.extend(
        [
            f"cuda_speedup_vs_cpu={speedup}",
            f"comparison_status={correctness['comparison_status']}",
            "trained_new_model=false",
            "promoted_to_runtime=false",
        ]
    )
    _write_text_atomic(log_path, "\n".join(log_lines) + "\n")
    _write_manifest(config.output_dir, manifest_path)

    manifest_errors = verify_output_manifest(manifest_path)
    if manifest_errors:
        raise RuntimeError(f"output manifest verification failed: {manifest_errors}")

    return InferenceTestbedResult(
        output_dir=config.output_dir,
        metrics_path=metrics_path,
        model_path=model_path,
        predictions_path=predictions_path,
        events_path=events_path,
        log_path=log_path,
        manifest_path=manifest_path,
    )


def print_result_summary(result: InferenceTestbedResult) -> None:
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    summary = {
        "output_dir": str(result.output_dir),
        "manifest_verified": verify_output_manifest(result.manifest_path) == [],
        "provider": metrics["provider"],
        "source_record_count": metrics["dataset"]["source_record_count"],
        "unique_user_count": metrics["dataset"]["unique_user_count"],
        "cuda_speedup_vs_cpu": metrics["cuda_speedup_vs_cpu"],
        "correctness": metrics["correctness"],
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
