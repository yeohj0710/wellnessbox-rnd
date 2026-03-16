from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas import (
    build_recommendation_set_contract_v1,
    summarize_recommendation_set_contract_v1,
    write_recommendation_set_contract_report_v1,
)
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build a recommendation set contract example")
    parser.add_argument(
        "--request-json",
        default="data/samples/api_recommend_start_plan_request_v1.json",
        help="Representative recommendation fixture path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/recommendation_set_contract_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/recommendation_set_contract_v1.md",
        help="Output markdown report path",
    )
    parser.add_argument(
        "--example-json",
        default="artifacts/reports/recommendation_set_example_v1.json",
        help="Output example contract JSON path",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    request_path = Path(args.request_json)
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    request = RecommendationRequest.model_validate(payload)
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    report = summarize_recommendation_set_contract_v1(
        contract,
        request_fixture_path=request_path,
    )
    write_recommendation_set_contract_report_v1(
        report,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
        output_example_json_path=args.example_json,
    )
    print(
        json.dumps(
            {
                "report_json": args.report_json,
                "report_md": args.report_md,
                "example_json": args.example_json,
                "issue_count": report["issue_count"],
                "selected_count": report["selected_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
