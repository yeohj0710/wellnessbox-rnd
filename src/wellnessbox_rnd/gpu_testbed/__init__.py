"""CPU/CUDA bulk-inference testbed for replay-only learned artifacts."""

from wellnessbox_rnd.gpu_testbed.pipeline import (
    InferenceBenchmarkConfig,
    InferenceTestbedResult,
    benchmark_inference,
    run_inference_testbed,
    verify_output_manifest,
)

__all__ = [
    "InferenceBenchmarkConfig",
    "InferenceTestbedResult",
    "benchmark_inference",
    "run_inference_testbed",
    "verify_output_manifest",
]
