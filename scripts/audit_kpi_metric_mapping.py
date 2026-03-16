import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.metrics.definitions import METRIC_DEFINITIONS


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Audit how current repo metric names and report values map to the "
            "official KPI semantics from master_context and original plan p.25~26"
        )
    )
    parser.add_argument(
        "--eval-report-json",
        default="artifacts/reports/current_loop_final_eval/eval_report.json",
        help="Current eval report JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/kpi_metric_mapping_audit_v1.json",
        help="Audit report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/kpi_metric_mapping_audit_v1.md",
        help="Audit report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    eval_report = json.loads(Path(args.eval_report_json).read_text(encoding="utf-8"))
    current_summary = eval_report["summary"]

    audit_rows = [_build_audit_row(metric_name, current_summary) for metric_name in METRIC_ORDER]
    report = {
        "eval_report_json": str(Path(args.eval_report_json)),
        "eval_case_count": eval_report["case_count"],
        "source_of_truth": {
            "master_context": "docs/context/master_context.md",
            "original_plan_pdf_pages_checked": [25, 26],
        },
        "summary": {
            "near_1_to_1_count": sum(
                1 for row in audit_rows if row["mapping_classification"] == "near_1_to_1"
            ),
            "proxy_count": sum(
                1
                for row in audit_rows
                if "proxy" in row["mapping_classification"]
                or row["mapping_classification"] == "proxy"
            ),
            "naming_mismatch_count": sum(
                1 for row in audit_rows if row["naming_mismatch"]
            ),
            "aggregation_mismatch_count": sum(
                1 for row in audit_rows if row["aggregation_mismatch"]
            ),
        },
        "metrics": audit_rows,
        "overall_findings": [
            (
                "`efficacy_improvement_pp` is the closest to a formula-level 1:1 KPI match; "
                "its main caveat is that the data source is synthetic frozen-eval follow-up pairs."
            ),
            (
                "`recommendation_coverage_pct` and `next_action_accuracy_pct` are not strict 1:1 "
                "matches because they relax exact-set accuracy and omit "
                "execution-success semantics."
            ),
            (
                "`explanation_quality_accuracy_pct` and "
                "`safety_reference_accuracy_pct` are explicit "
                "proxies for the official chat-answer and rule+reference accuracy KPIs."
            ),
            (
                "`sensor_genetic_integration_rate_pct` has the largest semantic gap: the repo name "
                "omits wearable, the implementation is pooled, and the original KPI is phrased as "
                "per-modality integration success."
            ),
        ],
    }

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


METRIC_ORDER = [
    "recommendation_coverage_pct",
    "efficacy_improvement_pp",
    "next_action_accuracy_pct",
    "explanation_quality_accuracy_pct",
    "safety_reference_accuracy_pct",
    "adverse_event_count_yearly",
    "sensor_genetic_integration_rate_pct",
]


AUDIT_NOTES = {
    "recommendation_coverage_pct": {
        "official_kpi_name_ko": "건강기능식품 추천 정확도",
        "official_semantics": (
            "사람이 만든 정답 성분 세트와 엔진 추천 성분 세트의 일치율"
        ),
        "repo_semantics": (
            "required ingredient set 대비 actual recommendation ingredient coverage"
        ),
        "mapping_classification": "proxy",
        "naming_mismatch": True,
        "aggregation_mismatch": False,
        "key_gap": (
            "현재 계산은 extra ingredient penalty가 없는 coverage라서 "
            "exact-set accuracy보다 느슨하다."
        ),
        "evidence": [
            "master_context.md lines 665-670",
            "original_plan.pdf p.25 recommendation accuracy row",
            "metrics/calculators.py recommendation_coverage_pct",
        ],
    },
    "efficacy_improvement_pp": {
        "official_kpi_name_ko": "엔진 추천 복용을 통한 실제 효과 측정치 개선도",
        "official_semantics": (
            "복용 전후 표준화 점수의 백분위 포인트 차이 평균이 양수인지"
        ),
        "repo_semantics": (
            "z_pre/z_post pair에 대해 percentile improvement pp를 계산한 후 case 평균"
        ),
        "mapping_classification": "near_1_to_1",
        "naming_mismatch": False,
        "aggregation_mismatch": False,
        "key_gap": (
            "공식 수식과 거의 같지만 실제 임상 follow-up이 아니라 "
            "synthetic frozen-eval pair를 사용한다."
        ),
        "evidence": [
            "master_context.md lines 672-677 and 731-739",
            "original_plan.pdf p.25~26 efficacy row and formula",
            "metrics/calculators.py percentile_improvement_pp",
        ],
    },
    "next_action_accuracy_pct": {
        "official_kpi_name_ko": "Closed-loop AI의 다음 수행 작업 판단 및 수행 정확도",
        "official_semantics": (
            "정답 next action을 맞히고 실제 수행 성공 플래그까지 포함한 정확도"
        ),
        "repo_semantics": (
            "expected_next_action과 actual next_action의 exact match"
        ),
        "mapping_classification": "proxy",
        "naming_mismatch": False,
        "aggregation_mismatch": False,
        "key_gap": (
            "현재 metric은 action judgment만 측정하고, 원문이 포함하는 "
            "execution success e_s는 반영하지 않는다."
        ),
        "evidence": [
            "master_context.md lines 679-685 and 745-751",
            "original_plan.pdf p.25~26 next action row and formula",
            "evals/runner.py next_action_accuracy_pct case metric",
        ],
    },
    "explanation_quality_accuracy_pct": {
        "official_kpi_name_ko": "상담 모듈(대화형 LLM)의 답변 정확도",
        "official_semantics": (
            "테스트 질문 세트에서 상담 모듈 답변 자체의 정답 일치율"
        ),
        "repo_semantics": (
            "required explanation terms가 decision/explanation text에 포함되는 coverage proxy"
        ),
        "mapping_classification": "proxy",
        "naming_mismatch": True,
        "aggregation_mismatch": False,
        "key_gap": (
            "현재 repo에는 독립 chat-module answer grader가 없어서 "
            "answer accuracy 대신 explanation-term coverage를 쓴다."
        ),
        "evidence": [
            "master_context.md lines 686-691 and 758-767",
            "original_plan.pdf p.25 상담 모듈 row",
            "metrics/calculators.py explanation_term_coverage_pct",
        ],
    },
    "safety_reference_accuracy_pct": {
        "official_kpi_name_ko": "안전 검증 엔진 제공 데이터 및 데이터 레이크 레퍼런스 정확도",
        "official_semantics": (
            "엔진 논리와 레퍼런스가 참조 규칙과 정확히 일치하는지"
        ),
        "repo_semantics": (
            "status exact match + required rule subset match + "
            "excluded ingredient subset match의 평균"
        ),
        "mapping_classification": "proxy",
        "naming_mismatch": False,
        "aggregation_mismatch": False,
        "key_gap": (
            "full logic/reference exact-match KPI를 현재는 status/rule/exclusion proxy로 근사한다."
        ),
        "evidence": [
            "master_context.md lines 693-699 and 769-780",
            "original_plan.pdf p.25~26 safety/reference row and formula",
            "metrics/calculators.py safety_reference_accuracy_pct",
        ],
    },
    "adverse_event_count_yearly": {
        "official_kpi_name_ko": "약물이상반응 보고 건수",
        "official_semantics": (
            "직전 12개월 누적 사용자 adverse event 보고 건수"
        ),
        "repo_semantics": (
            "frozen-eval dataset의 adverse_event_reported flag 합계"
        ),
        "mapping_classification": "proxy_data_source",
        "naming_mismatch": False,
        "aggregation_mismatch": False,
        "key_gap": (
            "metric name과 단위는 맞지만 실제 운영 12개월 집계가 아니라 "
            "synthetic eval dataset 합계다."
        ),
        "evidence": [
            "master_context.md lines 782-789",
            "original_plan.pdf p.25 adverse-event row",
            "metrics/calculators.py count_adverse_events",
        ],
    },
    "sensor_genetic_integration_rate_pct": {
        "official_kpi_name_ko": "바이오센서·유전자 데이터 연동율",
        "official_semantics": (
            "웨어러블/CGM/유전자 각 데이터셋의 성공적 연결 비율을 기준으로 보는 연동율"
        ),
        "repo_semantics": (
            "wearable+cgm+genetic attempted/success를 pooled success over attempted로 계산"
        ),
        "mapping_classification": "proxy_with_aggregation_mismatch",
        "naming_mismatch": True,
        "aggregation_mismatch": True,
        "key_gap": (
            "repo metric name은 wearable을 생략하고, 구현은 pooled ratio이며, "
            "현재 값도 runtime parser 성공률이 아니라 dataset observation "
            "proxy다."
        ),
        "evidence": [
            "master_context.md lines 791-804",
            "original_plan.pdf p.25~26 sensor/genetic row and formula",
            "metrics/calculators.py sensor_genetic_integration_rate_pct",
        ],
    },
}


def _build_audit_row(metric_name: str, current_summary: dict[str, object]) -> dict[str, object]:
    definition = METRIC_DEFINITIONS[metric_name]
    score_block = current_summary[metric_name]
    note = AUDIT_NOTES[metric_name]
    return {
        "metric_name": metric_name,
        "current_report_value": score_block["score"],
        "target": definition.target,
        "comparison": definition.comparison,
        "official_kpi_name_ko": note["official_kpi_name_ko"],
        "official_semantics": note["official_semantics"],
        "repo_semantics": note["repo_semantics"],
        "mapping_classification": note["mapping_classification"],
        "naming_mismatch": note["naming_mismatch"],
        "aggregation_mismatch": note["aggregation_mismatch"],
        "key_gap": note["key_gap"],
        "assumption": definition.assumption,
        "evidence": note["evidence"],
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# KPI metric mapping audit v1",
        "",
        f"- eval_report_json: `{report['eval_report_json']}`",
        f"- eval_case_count: `{report['eval_case_count']}`",
        (
            "- original_plan_pdf_pages_checked: "
            f"`{report['source_of_truth']['original_plan_pdf_pages_checked']}`"
        ),
        "",
        "## Summary",
        f"- `near_1_to_1_count`: `{report['summary']['near_1_to_1_count']}`",
        f"- `proxy_count`: `{report['summary']['proxy_count']}`",
        f"- `naming_mismatch_count`: `{report['summary']['naming_mismatch_count']}`",
        (
            "- `aggregation_mismatch_count`: "
            f"`{report['summary']['aggregation_mismatch_count']}`"
        ),
        "",
        "## Metrics",
    ]
    for row in report["metrics"]:
        lines.extend(
            [
                "",
                f"### {row['metric_name']}",
                f"- current_report_value: `{row['current_report_value']}`",
                f"- official_kpi_name_ko: `{row['official_kpi_name_ko']}`",
                f"- mapping_classification: `{row['mapping_classification']}`",
                f"- naming_mismatch: `{row['naming_mismatch']}`",
                f"- aggregation_mismatch: `{row['aggregation_mismatch']}`",
                f"- official_semantics: {row['official_semantics']}",
                f"- repo_semantics: {row['repo_semantics']}",
                f"- key_gap: {row['key_gap']}",
                f"- evidence: `{row['evidence']}`",
            ]
        )
    lines.extend(["", "## Overall Findings"])
    for finding in report["overall_findings"]:
        lines.append(f"- {finding}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
