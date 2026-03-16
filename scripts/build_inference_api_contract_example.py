from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.inference_api.main import app
from wellnessbox_rnd.schemas.recommendation import RecommendationResponse


def main() -> None:
    parser = ArgumentParser(description="Build a deterministic inference API contract example")
    parser.add_argument(
        "--request-json",
        default="data/samples/api_recommend_structured_safety_block_request_v1.json",
        help="Representative request fixture path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/api_recommend_contract_example_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/api_recommend_contract_example_v1.md",
        help="Output Markdown report path",
    )
    args = parser.parse_args()

    request_path = Path(args.request_json)
    payload = json.loads(request_path.read_text(encoding="utf-8"))

    client = TestClient(app)
    response = client.post("/v1/recommend", json=payload)
    body = response.json()
    RecommendationResponse.model_validate(body)

    report = {
        "request_fixture_path": str(request_path),
        "status_code": response.status_code,
        "request_summary": {
            "goal_count": len(payload["goals"]),
            "current_supplement_count": len(payload["current_supplements"]),
            "primary_goal": payload["goals"][0],
        },
        "response_contract_summary": {
            "status": body["status"],
            "next_action": body["next_action"],
            "next_action_reason_code": body["next_action_rationale"]["reason_code"],
            "safety_rule_ids": [
                item["rule_id"] for item in body["safety_summary"]["rule_refs"]
            ],
            "safety_evidence_codes": [item["code"] for item in body["safety_evidence"]],
            "limitation_codes": [item["code"] for item in body["limitation_details"]],
            "recommendation_count": len(body["recommendations"]),
            "metadata_mode": body["metadata"]["mode"],
        },
        "request": payload,
        "response": body,
    }

    json_path = Path(args.report_json)
    md_path = Path(args.report_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


def render_markdown(report: dict[str, object]) -> str:
    summary = report["response_contract_summary"]
    lines = [
        "# inference api contract example v1",
        "",
        f"- request_fixture_path: `{report['request_fixture_path']}`",
        f"- status_code: `{report['status_code']}`",
        f"- status: `{summary['status']}`",
        f"- next_action: `{summary['next_action']}`",
        f"- next_action_reason_code: `{summary['next_action_reason_code']}`",
        f"- safety_rule_ids: `{summary['safety_rule_ids']}`",
        f"- safety_evidence_codes: `{summary['safety_evidence_codes']}`",
        f"- limitation_codes: `{summary['limitation_codes']}`",
        f"- recommendation_count: `{summary['recommendation_count']}`",
        f"- metadata_mode: `{summary['metadata_mode']}`",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
