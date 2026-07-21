from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineScoreObservationV1,
    build_pro_baseline_distribution_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.getenv("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")
).resolve()
DEFAULT_OUTPUT = (
    RND_ROOT
    / "data/original_plan/evidence/op057_op058_pro_correction_plan_lineage_smoke_v1.json"
)
TOKEN = "op057-op058-local-token"
SALT = "op057-op058-local-pseudonym-salt"
APP_USER_ID = "op057-service-user"
RND_SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "scripts/run_pro_correction_plan_lineage_smoke.py",
    "src/wellnessbox_rnd/interim/data_lake.py",
    "src/wellnessbox_rnd/interim/data_mutation.py",
    "src/wellnessbox_rnd/metrics/pro_correction.py",
    "src/wellnessbox_rnd/metrics/pro_followup.py",
    "src/wellnessbox_rnd/metrics/pro_scoring.py",
]
SERVICE_SOURCE_PATHS = [
    "app/api/tips/pro/effects/route.ts",
    "lib/server/wb-rnd-interim-client.ts",
    "lib/server/wb-rnd-interim-route.ts",
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
            identity = f"{root_name}/{relative}"
            digest.update(identity.encode())
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


def _profile_id() -> str:
    digest = hmac.new(SALT.encode(), APP_USER_ID.encode(), hashlib.sha256).hexdigest()
    return f"usr_{digest[:32]}"


def _recommendation_payload() -> dict[str, object]:
    sources = ("survey", "nhis", "wearable", "cgm", "genetic")
    return {
        "request_id": "op057-op058-smoke-request",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": _profile_id(),
            "profile": {"age": 41, "sex": "female", "goals": ["sleep"]},
        },
        "user_profile": {"age": 41, "biological_sex": "female", "pregnant": False},
        "goals": ["sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "allergies": [],
        "risk_flags": [],
        "medications": [],
        "current_supplements": [],
        "dietary_patterns": [],
        "laboratory_observations": [],
        "lifestyle": {
            "sleep_hours": 5.5,
            "stress_level": 3,
            "activity_level": "lightly_active",
            "smoker": False,
            "alcohol_per_week": 0,
        },
        "input_availability": {
            "survey": True,
            "nhis": False,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "data_source_consents": {
            source: {
                "use_for_recommendation": source == "survey",
                "allow_persistent_storage": source == "survey",
            }
            for source in sources
        },
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": [],
        },
    }


def _score(raw_score: int):
    remaining = raw_score
    items = []
    for _ in range(7):
        item = min(3, remaining)
        items.append(item)
        remaining -= item
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": "PSQI",
            "item_scores": items,
        }
    )


def _event(timepoint: str, raw_score: int) -> dict[str, object]:
    score = _score(raw_score)
    distribution = build_pro_baseline_distribution_v1(
        [
            PROBaselineScoreObservationV1(
                schema_version="pro_baseline_score_observation_v1",
                observation_role="BASELINE",
                score=_score(value),
            )
            for value in (6, 9, 12)
        ],
        cohort_id="op057-psqi-baseline",
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )
    standardized = standardize_pro_instrument_score_v1(score, distribution)
    baseline = timepoint == "pre_intake"
    return {
        "schema_version": "versioned_pro_followup_event_v1",
        "assessment_id": f"assessment_op057_{timepoint}",
        "plan_id": "plan_op057_service_001",
        "data_class": "SYNTHETIC_OUTCOME_PROXY",
        "timepoint": timepoint,
        "scheduled_day_index": 0 if baseline else 14,
        "actual_day_index": 0 if baseline else 14,
        "observed_at": "2026-01-01T00:00:00Z" if baseline else "2026-01-15T00:00:00Z",
        "instrument_scores": [score.model_dump(mode="json")],
        "standardized_scores": [standardized.model_dump(mode="json")],
        "adherence": (
            None
            if baseline
            else {
                "planned_dose_count": 14,
                "taken_dose_count": 13,
                "missed_dose_count": 1,
                "adherence_rate": 0.928571,
            }
        ),
        "adverse_events": [],
        "discontinuation_reason": None,
    }


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
                "WB_RND_INTERIM_PSEUDONYM_SALT": SALT,
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
            headers = {"x-wb-rnd-token": TOKEN}
            with httpx.Client(base_url=base_url, timeout=20.0) as client:
                recommendation = client.post("/v1/recommend", json=_recommendation_payload())
                recommendation.raise_for_status()
                execution_id = recommendation.json()["execution_id"]
                baseline = client.post(
                    f"/v1/interim/executions/{execution_id}/events",
                    headers=headers,
                    json={
                        "event_type": "followup_evaluation",
                        "source": "survey",
                        "idempotency_key": "op057-baseline",
                        "payload": _event("pre_intake", 10),
                    },
                )
                baseline.raise_for_status()
                original_follow_up = client.post(
                    f"/v1/interim/executions/{execution_id}/events",
                    headers=headers,
                    json={
                        "event_type": "followup_evaluation",
                        "source": "survey",
                        "idempotency_key": "op057-week-2",
                        "payload": _event("week_2", 8),
                    },
                )
                original_follow_up.raise_for_status()
                request_path = temp / "service-request.json"
                request_path.write_text(
                    json.dumps(
                        {
                            "execution_id": execution_id,
                            "target_event_id": original_follow_up.json()["event"]["event_id"],
                            "idempotency_key": "op057-user-correction",
                            "replacement_payload": _event("week_2", 7),
                        }
                    ),
                    encoding="utf-8",
                )
                service = subprocess.run(
                    [
                        "node",
                        "--conditions=react-server",
                        "--import",
                        "tsx",
                        "scripts/qa/run-tips-pro-correction-client.cts",
                        str(request_path),
                    ],
                    cwd=SERVICE_ROOT,
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                corrected = json.loads(service.stdout)
                trace = client.get(
                    f"/v1/interim/executions/{execution_id}", headers=headers
                )
                trace.raise_for_status()
        finally:
            server.terminate()
            server.wait(timeout=10)

    followups = [
        event
        for event in trace.json()["events"]
        if event["event_type"] == "followup_evaluation"
    ]
    assert corrected["recalculated_immediately"] is True
    assert corrected["interpretation"]["follow_up_event"]["instrument_scores"][0][
        "raw_score"
    ] == 7
    assert corrected["lineage"]["plan_id"] == "plan_op057_service_001"
    assert corrected["lineage"]["selected_ingredient_keys"]
    assert followups[-1]["payload_state"] == "CORRECTED"
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
            "authenticated_service_correction": 1,
            "stored_strict_pro_events": len(followups),
            "original_raw_score": 8,
            "corrected_raw_score": 7,
            "recalculated_immediately": True,
            "mutation_audit_recorded": corrected["mutation"]["deduplicated"] is False,
            "stored_payload_state": followups[-1]["payload_state"],
        },
        "lineage": {
            "plan_id": corrected["lineage"]["plan_id"],
            "selected_ingredient_keys": corrected["lineage"]["selected_ingredient_keys"],
            "recommendation_and_effect_share_execution": True,
            "recommendation_and_effect_share_plan_id": True,
            "causal_effect_claim_allowed": False,
        },
        "evidence_boundary": {
            "service_to_rnd_local_http_proven": True,
            "authenticated_service_route_proven": True,
            "real_user_input_contract_proven": True,
            "production_deployment_proven": False,
            "production_operation_proven": False,
            "real_world_outcome_used": False,
            "op057_proven_stage": "INTEGRATED",
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
