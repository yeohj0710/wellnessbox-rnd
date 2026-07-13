from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.gpu_testbed.pipeline import (
    InferenceBenchmarkConfig,
    print_result_summary,
    run_inference_testbed,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Benchmark existing replay-only effect-model inference on CPU and CUDA"
    )
    parser.add_argument(
        "--data",
        "--dataset",
        dest="dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Synthetic JSONL input path; Cloud GPU Runner passes CGR_DATA_FILE here",
    )
    parser.add_argument(
        "--artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Existing effect model JSON artifact; no retraining is performed",
    )
    parser.add_argument(
        "--output",
        default="artifacts/gpu_testbed/latest",
        help="Output directory for model, metrics, logs, samples, and manifest",
    )
    parser.add_argument(
        "--devices",
        default="cpu,cuda",
        help="Comma-separated device list: cpu, cuda, or cpu,cuda",
    )
    parser.add_argument("--batch-size", type=int, default=262_144)
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="Fail instead of skipping CUDA when no CUDA device is available",
    )
    parser.add_argument("--provider", default="local")
    parser.add_argument("--estimated-max-cost-krw", type=float, default=0.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    devices = tuple(item.strip().lower() for item in args.devices.split(",") if item.strip())
    config = InferenceBenchmarkConfig(
        dataset_path=Path(args.dataset).resolve(),
        artifact_path=Path(args.artifact).resolve(),
        output_dir=Path(args.output).resolve(),
        devices=devices,
        batch_size=args.batch_size,
        iterations=args.iterations,
        warmup=args.warmup,
        require_cuda=args.require_cuda,
        seed=args.seed,
        provider=args.provider,
        estimated_max_cost_krw=args.estimated_max_cost_krw,
    )
    result = run_inference_testbed(config)
    print_result_summary(result)
    return 0


if __name__ == "__main__":
    sys_exit(main())
