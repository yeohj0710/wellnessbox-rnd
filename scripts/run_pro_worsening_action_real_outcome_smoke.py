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
    "op059_op060_pro_action_real_outcome_smoke_v1.json"
)
TOKEN = "op059-op060-local-token"
RND_SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "data/contracts/pro_runtime_reference_baselines_v1.json",
    "scripts/run_pro_worsening_action_real_outcome_smoke.py",
    "src/wellnessbox_rnd/interim/data_lake.py",
    "src/wellnessbox_rnd/interim/contracts.py",
    "src/wellnessbox_rnd/metrics/__init__.py",
    "src/wellnessbox_rnd/metrics/pro_actions.py",
    "src/wellnessbox_rnd/metrics/pro_followup.py",
    "src/wellnessbox_rnd/metrics/pro_runtime.py",
    "src/wellnessbox_rnd/metrics/pro_scoring.py",
    "src/wellnessbox_rnd/orchestration/pro_plan_service.py",
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
    "src/wellnessbox_rnd/schemas/next_action_state_machine.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/pro/effects/route.ts",
    "app/api/tips/pro/plans/route.ts",
    "components/tips/ProStudySimulation.tsx",
    "lib/server/wb-rnd-interim-client.ts",
    "lib/server/wb-rnd-interim-route.ts",
    "lib/server/wb-rnd-profile-adapter.ts",
    "lib/server/route-auth.ts",
    "lib/server/wb-rnd-interim-safety-authority.ts",
    "lib/server/wb-rnd-product-candidates.ts",
    "lib/tips/pro-study-engine.ts",
    "lib/tips/pro-study-rnd-client.ts",
    "scripts/qa/check-tips-pro-correction-route.cts",
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
    if root == SERVICE_ROOT:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
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


def _service_call(
    temp: Path,
    environment: dict[str, str],
    action: str,
    body: dict,
) -> dict:
    input_path = temp / f"service-{len(list(temp.glob('service-*.json')))}.json"
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
    cases = [
        ("maintain", "REAL_WORLD_OUTCOME", 10, [], "worsening_confounded_maintain"),
        (
            "reduce",
            "REAL_WORLD_OUTCOME",
            14,
            [
                {
                    "adverse_event_id": "ae_mild",
                    "severity": "mild",
                    "relatedness": "unknown",
                    "ongoing": False,
                }
            ],
            "adverse_event_reduce",
        ),
        (
            "stop",
            "REAL_WORLD_OUTCOME",
            14,
            [
                {
                    "adverse_event_id": "ae_serious",
                    "severity": "serious",
                    "relatedness": "unknown",
                    "ongoing": True,
                }
            ],
            "serious_adverse_event_stop",
        ),
        (
            "re_optimize",
            "REAL_WORLD_OUTCOME",
            14,
            [],
            "interpretable_worsening_re_optimize",
        ),
        (
            "re_optimize",
            "SYNTHETIC_OUTCOME_PROXY",
            14,
            [],
            "interpretable_worsening_re_optimize",
        ),
    ]
    observed: dict[str, dict[str, object]] = {}
    paired_semantic_sha256: dict[str, str] = {}
    with TemporaryDirectory(prefix="op059-op060-") as directory:
        temp = Path(directory)
        port = 18759
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update(
            {
                "WB_RND_INTERIM_DATABASE": str(temp / "interim.sqlite3"),
                "WB_RND_INTERIM_INTERNAL_TOKEN": TOKEN,
                "WB_RND_INTERIM_ENABLED": "1",
                "WB_RND_INTERIM_BASE_URL": base_url,
                "WB_RND_INTERIM_TOKEN": TOKEN,
                "WB_RND_INTERIM_PSEUDONYM_SALT": "op059-op060-local-salt",
                "WB_RND_CODE_COMMIT": "op059-op060-smoke",
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
            paired_results: dict[str, dict[str, object]] = {}
            for index, (
                expected_action,
                data_class,
                taken,
                adverse_events,
                expected_reason,
            ) in enumerate(cases):
                enrollment_semantic = {
                    "profile": {
                        "age": 41,
                        "sex": "female",
                        "goals": ["sleep quality"],
                    },
                    "baseline": {
                        "instrument": "PSQI",
                        "item_scores": _psqi_items(10),
                    },
                    "observedAt": "2026-01-01T00:00:00Z",
                    "consentAccepted": True,
                }
                enrolled = _service_call(
                    temp,
                    environment,
                    "enroll",
                    {
                        "requestId": f"pro_{index + 1:032x}",
                        **enrollment_semantic,
                        "dataClass": data_class,
                    },
                )
                followup_semantic = {
                    "timepoint": "week_2",
                    "answers": {
                        "instrument": "PSQI",
                        "item_scores": _psqi_items(12),
                    },
                    "observedAt": "2026-01-15T00:00:00Z",
                    "actualDayIndex": 14,
                    "plannedDoseCount": 14,
                    "takenDoseCount": taken,
                    "adverseEvents": adverse_events,
                }
                followed = _service_call(
                    temp,
                    environment,
                    "followup",
                    {
                        "executionId": enrolled["execution_id"],
                        "planId": enrolled["plan_id"],
                        **followup_semantic,
                    },
                )
                decision = followed["action_decision"]
                assert decision["action"] == expected_action
                assert decision["reason_code"] == expected_reason
                assert followed["interpretation"]["baseline_event"]["data_class"] == data_class
                assert followed["interpretation"]["follow_up_event"]["data_class"] == data_class
                result = {
                    "reason_code": decision["reason_code"],
                    "next_action": decision["next_action"],
                    "projected_workflow_state": decision["projected_workflow_state"],
                    "data_class": followed["interpretation"]["follow_up_event"]["data_class"],
                }
                if expected_action == "re_optimize":
                    paired_results[data_class] = result
                    paired_semantic_sha256[data_class] = hashlib.sha256(
                        json.dumps(
                            {
                                "enrollment": enrollment_semantic,
                                "followup": followup_semantic,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                if data_class == "REAL_WORLD_OUTCOME":
                    observed[expected_action] = result
        finally:
            server.terminate()
            server.wait(timeout=10)

    return {
        "schema_version": "op059_op060_pro_action_real_outcome_smoke_v1",
        "source": {
            "combined_sha256": _source_sha256(),
            "wellnessbox_rnd_commit": _source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": _source_commit(SERVICE_ROOT, SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": RND_SOURCE_PATHS,
            "wellnessbox_paths": SERVICE_SOURCE_PATHS,
        },
        "cases": {
            "authenticated_real_world_enrollments": 4,
            "authenticated_real_world_followups": 4,
            "authenticated_synthetic_pair_enrollments": 1,
            "authenticated_synthetic_pair_followups": 1,
            "exact_action_count": len(observed),
            "actions": observed,
            "data_class_pair": paired_results,
            "data_class_pair_semantic_input_sha256": paired_semantic_sha256,
        },
        "checks": {
            "existing_service_helper_used": True,
            "existing_rnd_plan_api_used": True,
            "same_semantic_payload_except_transport_id_and_data_class": (
                set(paired_results) == {"REAL_WORLD_OUTCOME", "SYNTHETIC_OUTCOME_PROXY"}
                and len(set(paired_semantic_sha256.values())) == 1
                and {
                    key: value
                    for key, value in paired_results["REAL_WORLD_OUTCOME"].items()
                    if key != "data_class"
                }
                == {
                    key: value
                    for key, value in paired_results["SYNTHETIC_OUTCOME_PROXY"].items()
                    if key != "data_class"
                }
            ),
            "all_real_world_events_preserved_data_class": True,
            "all_four_worsening_actions_observed": sorted(observed)
            == ["maintain", "re_optimize", "reduce", "stop"],
            "causal_effect_claim_allowed": False,
        },
        "evidence_boundary": {
            "op059_proven_stage": "INTEGRATED",
            "op059_required_stage": "INTEGRATED",
            "op060_proven_stage": "INTEGRATED",
            "op060_required_stage": "INTEGRATED",
            "localhost_two_process_integration_proven": True,
            "real_world_outcome_contract_proven": True,
            "production_data_used": False,
            "production_operation_proven": False,
            "production_deployment_proven": False,
            "causal_effect_proven": False,
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
