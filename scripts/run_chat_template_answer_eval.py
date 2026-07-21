import json
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.chat import (
    BoundedKnowledgeScope,
    generate_bounded_template_answer,
    load_approved_counseling_scope,
    load_chat_qa_eval_cases,
    load_retrieval_corpus_manifest,
    verify_bounded_template_answer,
)

ANSWER_TIME = datetime(2026, 7, 21, tzinfo=UTC)


def _build_scope(manifest) -> BoundedKnowledgeScope:
    del manifest
    return load_approved_counseling_scope()


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Run bounded template-answer and verifier eval for counseling retrieval"
    )
    parser.add_argument(
        "--corpus-manifest-json",
        default="artifacts/retrieval/chat_retrieval_corpus_manifest_v1.json",
        help="Retrieval corpus manifest JSON path",
    )
    parser.add_argument(
        "--qa-dataset-jsonl",
        default="artifacts/datasets/chat_qa_dataset_d_v1.jsonl",
        help="QA dataset D JSONL path",
    )
    parser.add_argument(
        "--eval-report-json",
        default="artifacts/reports/chat_template_answer_eval_v1.json",
        help="Template-answer eval JSON path",
    )
    parser.add_argument(
        "--eval-report-md",
        default="artifacts/reports/chat_template_answer_eval_v1.md",
        help="Template-answer eval markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = load_retrieval_corpus_manifest(args.corpus_manifest_json)
    scope = _build_scope(manifest)
    qa_cases = load_chat_qa_eval_cases(args.qa_dataset_jsonl)

    supported_reports: list[dict[str, object]] = []
    pass_count = 0
    citation_pass_count = 0
    expected_terms_pass_count = 0
    for case in qa_cases:
        answer = generate_bounded_template_answer(
            manifest,
            query=case.question,
            scope=scope,
            as_of=ANSWER_TIME,
            answer_template_key=case.answer_template_key,
        )
        verification = verify_bounded_template_answer(
            answer,
            manifest=manifest,
            scope=scope,
            as_of=ANSWER_TIME,
            expected_reference_ids=case.expected_reference_ids,
            expected_claim_ids=case.expected_claim_ids,
            expected_terms=case.expected_terms,
            expected_status="supported",
        )
        pass_count += int(verification.passed)
        citation_pass_count += int(verification.citation_linkage_ok)
        expected_terms_pass_count += int(verification.expected_terms_ok)
        supported_reports.append(
            {
                "case_id": case.case_id,
                "status": answer.status,
                "answer_template_key": answer.answer_template_key,
                "answer_text": answer.answer_text,
                "citation_reference_ids": [citation.reference_id for citation in answer.citations],
                "citation_claim_ids": [citation.claim_id for citation in answer.citations],
                "verification_passed": verification.passed,
                "issues": verification.issues,
            }
        )

    probes = [
        {
            "probe_id": "probe::out_of_scope",
            "query": "What is the weather in Seoul today?",
            "expected_status": "out_of_scope",
        },
        {
            "probe_id": "probe::unsupported_claim",
            "query": "Does glucosamine cure diabetes?",
            "expected_status": "unsupported",
        },
    ]
    probe_reports: list[dict[str, object]] = []
    out_of_scope_probe_passed = False
    unsupported_probe_passed = False
    for probe in probes:
        answer = generate_bounded_template_answer(
            manifest, query=probe["query"], scope=scope, as_of=ANSWER_TIME
        )
        verification = verify_bounded_template_answer(
            answer,
            manifest=manifest,
            scope=scope,
            as_of=ANSWER_TIME,
            expected_status=probe["expected_status"],
        )
        if probe["probe_id"] == "probe::out_of_scope":
            out_of_scope_probe_passed = verification.passed
        if probe["probe_id"] == "probe::unsupported_claim":
            unsupported_probe_passed = verification.passed
        probe_reports.append(
            {
                "probe_id": probe["probe_id"],
                "status": answer.status,
                "answer_text": answer.answer_text,
                "verification_passed": verification.passed,
                "issues": verification.issues,
            }
        )

    case_count = len(qa_cases)
    report = {
        "case_count": case_count,
        "supported_answer_pass_rate_pct": round((pass_count / case_count) * 100.0, 2)
        if case_count
        else 0.0,
        "citation_linkage_pass_rate_pct": round(
            (citation_pass_count / case_count) * 100.0, 2
        )
        if case_count
        else 0.0,
        "expected_terms_pass_rate_pct": round(
            (expected_terms_pass_count / case_count) * 100.0, 2
        )
        if case_count
        else 0.0,
        "out_of_scope_probe_passed": out_of_scope_probe_passed,
        "unsupported_claim_probe_passed": unsupported_probe_passed,
        "corpus_manifest_path": args.corpus_manifest_json,
        "qa_dataset_path": args.qa_dataset_jsonl,
        "cases": supported_reports,
        "probes": probe_reports,
    }

    eval_json_path = Path(args.eval_report_json)
    eval_md_path = Path(args.eval_report_md)
    eval_json_path.parent.mkdir(parents=True, exist_ok=True)
    eval_md_path.parent.mkdir(parents=True, exist_ok=True)
    eval_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    eval_md_path.write_text(_render_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# chat template answer eval v1",
        "",
        f"- corpus_manifest_path: `{report['corpus_manifest_path']}`",
        f"- qa_dataset_path: `{report['qa_dataset_path']}`",
        f"- case_count: `{report['case_count']}`",
        f"- supported_answer_pass_rate_pct: `{report['supported_answer_pass_rate_pct']}`",
        f"- citation_linkage_pass_rate_pct: `{report['citation_linkage_pass_rate_pct']}`",
        f"- expected_terms_pass_rate_pct: `{report['expected_terms_pass_rate_pct']}`",
        f"- out_of_scope_probe_passed: `{report['out_of_scope_probe_passed']}`",
        f"- unsupported_claim_probe_passed: `{report['unsupported_claim_probe_passed']}`",
        "",
        "## Cases",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['case_id']}`: status=`{case['status']}`, "
            f"passed=`{case['verification_passed']}`, issues=`{case['issues']}`"
        )
    lines.append("")
    lines.append("## Probes")
    for probe in report["probes"]:
        lines.append(
            f"- `{probe['probe_id']}`: status=`{probe['status']}`, "
            f"passed=`{probe['verification_passed']}`, issues=`{probe['issues']}`"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
