from __future__ import annotations

import argparse
import json
from pathlib import Path

from wellnessbox_rnd.runtime import validate_runtime_readiness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the bounded staging API deployment readiness report.",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/staging_api_deploy_readiness_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/staging_api_deploy_readiness_v1.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime_readiness = validate_runtime_readiness()
    task = (
        "make the current inference API deploy-ready for a generic always-on CPU "
        "staging server"
    )
    required_assets = {
        "dockerfile": Path("Dockerfile"),
        "dockerignore": Path(".dockerignore"),
        "env_example": Path(".env.example"),
        "startup_script": Path("scripts/start_inference_api.py"),
        "smoke_script": Path("scripts/run_staging_api_smoke.py"),
        "deployment_readme": Path("docs/deployment/staging_api.md"),
        "smoke_request_fixture": Path("data/samples/api_recommend_start_plan_request_v1.json"),
    }
    missing_assets = [
        name for name, path in required_assets.items() if not path.exists()
    ]

    payload = {
        "stage": "P1/P4",
        "task": task,
        "runtime_entrypoint": "apps.inference_api.main:app",
        "production_start_command": "python scripts/start_inference_api.py",
        "container_start_command": "python scripts/start_inference_api.py",
        "provider_agnostic": True,
        "deterministic_baseline_only": True,
        "runtime_readiness": runtime_readiness,
        "required_assets": {
            name: str(path) for name, path in required_assets.items()
        },
        "missing_assets": missing_assets,
        "deploy_ready": not missing_assets,
        "smoke_request_case_count": 1,
    }

    report_json_path = Path(args.report_json)
    report_md_path = Path(args.report_md)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report_md_path.write_text(
        "\n".join(
            [
                "# Staging API Deploy Readiness v1",
                "",
                f"- Stage: `{payload['stage']}`",
                f"- Task: `{payload['task']}`",
                f"- Runtime entrypoint: `{payload['runtime_entrypoint']}`",
                f"- Production start command: `{payload['production_start_command']}`",
                f"- Provider agnostic: `{payload['provider_agnostic']}`",
                f"- Deterministic baseline only: `{payload['deterministic_baseline_only']}`",
                f"- Deploy ready: `{payload['deploy_ready']}`",
                f"- Missing assets: `{len(missing_assets)}`",
                "",
                "## Runtime readiness",
                "",
                f"- runtime_status: `{runtime_readiness['runtime_status']}`",
                f"- knowledge_source: `{runtime_readiness['knowledge_source']}`",
                f"- ingredient_catalog_count: `{runtime_readiness['ingredient_catalog_count']}`",
                f"- interaction_rule_count: `{runtime_readiness['interaction_rule_count']}`",
                f"- reference_count: `{runtime_readiness['reference_count']}`",
                "",
                "## Required assets",
                "",
                *[
                    f"- `{name}`: `{path}`"
                    for name, path in payload["required_assets"].items()
                ],
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
