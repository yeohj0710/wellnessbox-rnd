import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.chat import (
    ChatAdapterRequest,
    generate_chat_answer_with_openai_fallback,
    load_chat_qa_eval_cases,
    load_openai_chat_adapter_config_from_env,
    load_retrieval_corpus_manifest,
)
from wellnessbox_rnd.chat.openai_adapter import (
    CHAT_OPENAI_BASE_URL_ENV_VAR,
    CHAT_OPENAI_MODEL_ENV_VAR,
    CHAT_OPENAI_TIMEOUT_ENV_VAR,
    OPENAI_API_KEY_ENV_VAR,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Run bounded OpenAI chat adapter smoke with deterministic fallback"
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
        "--report-json",
        default="artifacts/reports/chat_openai_adapter_smoke_v1.json",
        help="Adapter smoke JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/chat_openai_adapter_smoke_v1.md",
        help="Adapter smoke markdown path",
    )
    parser.add_argument(
        "--allow-live-api",
        action="store_true",
        help="Attempt a real OpenAI Responses API call when OPENAI_API_KEY is present",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = load_retrieval_corpus_manifest(args.corpus_manifest_json)
    qa_case = load_chat_qa_eval_cases(args.qa_dataset_jsonl)[0]
    adapter_request = ChatAdapterRequest(
        query=qa_case.question,
        answer_template_key=qa_case.answer_template_key,
        expected_reference_ids=qa_case.expected_reference_ids,
        expected_claim_ids=qa_case.expected_claim_ids,
        expected_terms=qa_case.expected_terms,
    )
    config = load_openai_chat_adapter_config_from_env()
    adapter_response = generate_chat_answer_with_openai_fallback(
        manifest,
        adapter_request,
        allow_live_api=args.allow_live_api,
    )
    preflight = _build_preflight(
        config=config,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        allow_live_api=args.allow_live_api,
    )
    report = {
        "case_id": qa_case.case_id,
        "allow_live_api": args.allow_live_api,
        "provider": adapter_response.provider,
        "fallback_reason": adapter_response.fallback_reason,
        "attempted_live_call": adapter_response.attempted_live_call,
        "verification_passed": adapter_response.verification.passed,
        "answer_status": adapter_response.answer.status,
        "preflight": preflight,
        "config": {
            "env_vars": [
                OPENAI_API_KEY_ENV_VAR,
                CHAT_OPENAI_MODEL_ENV_VAR,
                CHAT_OPENAI_BASE_URL_ENV_VAR,
                CHAT_OPENAI_TIMEOUT_ENV_VAR,
            ],
            "api_key_present": config.api_key_present,
            "model": config.model,
            "base_url": config.base_url,
            "timeout_seconds": config.timeout_seconds,
            "corpus_manifest_path": args.corpus_manifest_json,
            "qa_dataset_path": args.qa_dataset_jsonl,
        },
        "answer": adapter_response.answer.model_dump(),
        "verification": adapter_response.verification.model_dump(),
    }
    report_json_path = Path(args.report_json)
    report_md_path = Path(args.report_md)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _render_markdown(report: dict[str, object]) -> str:
    preflight = report["preflight"]
    runtime_boundary = preflight["runtime_boundary"]
    config = report["config"]
    verification = report["verification"]
    lines = [
        "# chat openai adapter smoke v1",
        "",
        f"- case_id: `{report['case_id']}`",
        f"- allow_live_api: `{report['allow_live_api']}`",
        f"- provider: `{report['provider']}`",
        f"- fallback_reason: `{report['fallback_reason']}`",
        f"- attempted_live_call: `{report['attempted_live_call']}`",
        f"- verification_passed: `{report['verification_passed']}`",
        f"- answer_status: `{report['answer_status']}`",
        "",
        "## Preflight",
        f"- readiness_status: `{preflight['readiness_status']}`",
        f"- missing_env_vars: `{preflight['missing_env_vars']}`",
        f"- exact_live_command: `{preflight['exact_live_command']}`",
        f"- expected_artifacts: `{preflight['expected_artifacts']}`",
        "- recommendation_runtime_affected: "
        f"`{runtime_boundary['recommendation_runtime_affected']}`",
        f"- safety_runtime_affected: `{runtime_boundary['safety_runtime_affected']}`",
        f"- optimizer_runtime_affected: `{runtime_boundary['optimizer_runtime_affected']}`",
        f"- chat_only_boundary: `{runtime_boundary['chat_only_boundary']}`",
        "",
        "## Config",
        f"- env_vars: `{config['env_vars']}`",
        f"- api_key_present: `{config['api_key_present']}`",
        f"- model: `{config['model']}`",
        f"- base_url: `{config['base_url']}`",
        f"- timeout_seconds: `{config['timeout_seconds']}`",
        f"- corpus_manifest_path: `{config['corpus_manifest_path']}`",
        f"- qa_dataset_path: `{config['qa_dataset_path']}`",
        "",
        "## Verification",
        f"- passed: `{verification['passed']}`",
        f"- issues: `{verification['issues']}`",
    ]
    return "\n".join(lines) + "\n"


def _build_preflight(
    *,
    config,
    report_json_path: str,
    report_md_path: str,
    allow_live_api: bool,
) -> dict[str, object]:
    missing_env_vars = [] if config.api_key_present else [OPENAI_API_KEY_ENV_VAR]
    exact_live_command = (
        "python scripts/run_chat_openai_adapter_smoke.py --allow-live-api "
        f"--report-json {report_json_path} --report-md {report_md_path}"
    )
    return {
        "readiness_status": (
            "ready_for_live_smoke"
            if allow_live_api and config.api_key_present
            else "deferred_missing_env" if allow_live_api else "fallback_only_local_check"
        ),
        "missing_env_vars": missing_env_vars,
        "exact_live_command": exact_live_command,
        "expected_artifacts": [report_json_path, report_md_path],
        "runtime_boundary": {
            "chat_only_boundary": True,
            "recommendation_runtime_affected": False,
            "safety_runtime_affected": False,
            "optimizer_runtime_affected": False,
        },
    }


if __name__ == "__main__":
    sys_exit(main())
