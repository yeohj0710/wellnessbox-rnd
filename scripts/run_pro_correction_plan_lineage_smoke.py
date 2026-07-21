from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")).resolve()
DEFAULT_OUTPUT = RND_ROOT / (
    "data/original_plan/evidence/"
    "op057_op058_pro_correction_plan_lineage_smoke_v1.json"
)
TOKEN = "op057-op058-local-token"
RND_SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "data/contracts/pro_runtime_reference_baselines_v1.json",
    "scripts/run_pro_correction_plan_lineage_smoke.py",
    "src/wellnessbox_rnd/interim/data_lake.py",
    "src/wellnessbox_rnd/interim/data_mutation.py",
    "src/wellnessbox_rnd/metrics/pro_correction.py",
    "src/wellnessbox_rnd/metrics/pro_followup.py",
    "src/wellnessbox_rnd/metrics/pro_runtime.py",
    "src/wellnessbox_rnd/metrics/pro_scoring.py",
    "src/wellnessbox_rnd/orchestration/pro_plan_service.py",
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/pro/effects/route.ts",
    "app/api/tips/pro/plans/route.ts",
    "components/tips/ProStudySimulation.tsx",
    "lib/server/wb-rnd-interim-client.ts",
    "lib/server/wb-rnd-interim-route.ts",
    "lib/server/wb-rnd-profile-adapter.ts",
    "lib/tips/pro-study-engine.ts",
    "lib/tips/pro-study-rnd-client.ts",
    "scripts/qa/check-tips-pro-study-rnd-client.cts",
    "scripts/qa/run-tips-pro-correction-client.cts",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for root_name, root, paths in (
        ("wellnessbox-rnd", RND_ROOT, RND_SOURCE_PATHS),
        ("wellnessbox", SERVICE_ROOT, SERVICE_SOURCE_PATHS),
    ):
        for relative in sorted(paths):
            digest.update(f"{root_name}/{relative}".encode())
            digest.update(b"\0")
            digest.update((root / relative).read_bytes().replace(b"\r\n", b"\n"))
            digest.update(b"\0")
    return digest.hexdigest()


def _source_commit(root: Path, paths: list[str]) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _wait_for_server(base_url: str, process: subprocess.Popen[str]) -> None:
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("local_rnd_server_exited")
        try:
            if httpx.get(f"{base_url}/health", timeout=0.2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.05)
    raise RuntimeError("local_rnd_server_not_ready")


def _psqi_items(raw_score: int) -> list[int]:
    remaining = raw_score
    values: list[int] = []
    for _ in range(7):
        value = min(3, remaining)
        values.append(value)
        remaining -= value
    if remaining:
        raise ValueError("raw_score_out_of_psqi_range")
    return values


def _service_call(temp: Path, environment: dict[str, str], action: str, body: dict) -> dict:
    input_path = temp / f"service-{action}-{len(list(temp.glob('service-*.json')))}.json"
    input_path.write_text(json.dumps({"action": action, "body": body}), encoding="utf-8")
    result = subprocess.run(
        [
            "node",
            "--conditions=react-server",
            "--import",
            "tsx",
            "scripts/qa/run-tips-pro-correction-client.cts",
            str(input_path),
        ],
        cwd=SERVICE_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op057-op058-") as directory:
        temp = Path(directory)
        port = 18757
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update(
            {
                "WB_RND_INTERIM_DATABASE": str(temp / "interim.sqlite3"),
                "WB_RND_INTERIM_INTERNAL_TOKEN": TOKEN,
                "WB_RND_INTERIM_ENABLED": "1",
                "WB_RND_INTERIM_BASE_URL": base_url,
                "WB_RND_INTERIM_TOKEN": TOKEN,
                "WB_RND_INTERIM_PSEUDONYM_SALT": "op057-op058-local-pseudonym-salt",
                "WB_RND_CODE_COMMIT": "op057-op058-smoke",
            }
        )
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.inference_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=RND_ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            _wait_for_server(base_url, server)
            enrolled = _service_call(
                temp,
                environment,
                "enroll",
                {
                    "profile": {
                        "name": "통합 테스터",
                        "age": 41,
                        "sex": "female",
                        "goals": ["sleep quality"],
                    },
                    "baseline": {"instrument": "PSQI", "item_scores": _psqi_items(10)},
                    "observedAt": "2026-01-01T00:00:00Z",
                    "consentAccepted": True,
                },
            )
            followup_body = {
                "executionId": enrolled["execution_id"],
                "planId": enrolled["plan_id"],
                "timepoint": "week_2",
                "answers": {"instrument": "PSQI", "item_scores": _psqi_items(8)},
                "observedAt": "2026-01-15T00:00:00Z",
                "actualDayIndex": 14,
                "plannedDoseCount": 14,
                "takenDoseCount": 13,
                "adverseEvents": [],
            }
            original = _service_call(temp, environment, "followup", followup_body)
            followup_body["answers"] = {"instrument": "PSQI", "item_scores": _psqi_items(7)}
            corrected = _service_call(temp, environment, "correction", followup_body)
            subprocess.run(
                ["npm", "run", "qa:tips:pro-study-rnd"],
                cwd=SERVICE_ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            trace_response = httpx.get(
                f"{base_url}/v1/interim/executions/{enrolled['execution_id']}",
                headers={"x-wb-rnd-token": TOKEN},
                timeout=20.0,
            )
            trace_response.raise_for_status()
            trace = trace_response.json()
        finally:
            server.terminate()
            server.wait(timeout=10)

    events = trace["events"]
    recommendation = next(item for item in events if item["event_type"] == "recommendation")
    optimization = next(item for item in events if item["event_type"] == "optimization")
    followups = [item for item in events if item["event_type"] == "followup_evaluation"]
    plan_id = enrolled["plan_id"]
    assert original["operation"] == "created"
    assert corrected["operation"] == "corrected"
    assert original["raw_score"] == 8 and corrected["raw_score"] == 7
    assert recommendation["payload"]["plan_id"] == plan_id
    assert optimization["payload"]["plan_id"] == plan_id
    assert all(item["payload"]["plan_id"] == plan_id for item in followups)
    assert followups[-1]["payload_state"] == "CORRECTED"
    assert corrected["lineage"]["selected_ingredient_keys"] == optimization[
        "payload"
    ]["selected_ingredient_keys"]
    return {
        "schema_version": "op057_op058_pro_correction_plan_lineage_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(SERVICE_ROOT, SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "authenticated_service_enrollment": 1,
            "authenticated_service_followup_create": 1,
            "authenticated_service_followup_correction": 1,
            "stored_strict_pro_events": len(followups),
            "baseline_raw_score": 10,
            "original_raw_score": 8,
            "corrected_raw_score": 7,
            "recalculated_immediately": corrected["recalculated_immediately"],
            "stored_payload_state": followups[-1]["payload_state"],
        },
        "lineage": {
            "plan_id": plan_id,
            "selected_ingredient_keys": corrected["lineage"]["selected_ingredient_keys"],
            "recommendation_event_has_plan_id": True,
            "optimization_event_has_plan_id": True,
            "all_pro_events_share_plan_id": True,
            "recommendation_and_effect_share_execution": True,
            "causal_effect_claim_allowed": False,
        },
        "evidence_boundary": {
            "service_to_rnd_local_http_proven": True,
            "authenticated_service_helpers_proven": True,
            "actual_ui_client_binding_proven": True,
            "browser_render_proven": False,
            "production_deployment_proven": False,
            "production_operation_proven": False,
            "real_world_outcome_used": False,
            "op057_proven_stage": "INTEGRATED",
            "op057_required_stage": "INTEGRATED",
            "op058_proven_stage": "INTEGRATED",
            "op058_required_stage": "OPERATED",
        },
    }


def main() -> None:
    arguments = _args()
    result = run_smoke()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
