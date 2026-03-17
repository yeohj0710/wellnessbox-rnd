from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib import request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a provider-agnostic smoke test against the staging inference API.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--health-path", default="/health")
    parser.add_argument("--recommend-path", default="/v1/recommend")
    parser.add_argument(
        "--request-json",
        default="data/samples/api_recommend_start_plan_request_v1.json",
    )
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    return parser.parse_args()


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _http_json(
    *,
    url: str,
    method: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    encoded_payload = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        encoded_payload = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    http_request = request.Request(
        url=url,
        method=method,
        headers=headers,
        data=encoded_payload,
    )
    with request.urlopen(http_request, timeout=timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    health_status, health_body = _http_json(
        url=f"{base_url}{args.health_path}",
        method="GET",
        payload=None,
        timeout_seconds=args.timeout_seconds,
    )
    _require(health_status == 200, f"health_status_unexpected:{health_status}")
    _require(health_body.get("status") == "ok", "health_payload_missing_ok_status")
    _require(health_body.get("runtime_status") == "ready", "health_runtime_not_ready")

    recommend_payload = _read_json(args.request_json)
    recommend_status, recommend_body = _http_json(
        url=f"{base_url}{args.recommend_path}",
        method="POST",
        payload=recommend_payload,
        timeout_seconds=args.timeout_seconds,
    )
    _require(recommend_status == 200, f"recommend_status_unexpected:{recommend_status}")
    _require(recommend_body.get("status") == "ok", "recommend_payload_missing_ok_status")
    _require(recommend_body.get("next_action") == "start_plan", "recommend_next_action_changed")
    _require(
        recommend_body.get("next_action_rationale", {}).get("reason_code") == "start_plan_ready",
        "recommend_reason_code_changed",
    )
    _require(
        recommend_body.get("metadata", {}).get("mode") == "deterministic_baseline_v1",
        "recommend_mode_changed",
    )
    _require(
        len(recommend_body.get("recommendations", [])) >= 1,
        "recommendations_missing",
    )

    print(
        json.dumps(
            {
                "base_url": base_url,
                "health": {
                    "status_code": health_status,
                    "status": health_body.get("status"),
                    "runtime_status": health_body.get("runtime_status"),
                },
                "recommend": {
                    "status_code": recommend_status,
                    "status": recommend_body.get("status"),
                    "next_action": recommend_body.get("next_action"),
                    "recommendation_count": len(recommend_body.get("recommendations", [])),
                    "mode": recommend_body.get("metadata", {}).get("mode"),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
