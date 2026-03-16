import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Audit post-manual backlog status across training, replay eval, "
            "chat, and OpenAI adapter artifacts"
        )
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/post_manual_catchup_status_v1.json",
        help="Catch-up audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/post_manual_catchup_status_v1.md",
        help="Catch-up audit markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    statuses = {
        "training": _audit_training_status(),
        "replay_eval": _audit_replay_eval_status(),
        "chat_smoke": _audit_chat_smoke_status(),
        "openai_adapter": _audit_openai_adapter_status(),
    }
    summary = {
        "success_count": sum(
            1 for item in statuses.values() if item["classification"] == "success"
        ),
        "failure_count": sum(
            1 for item in statuses.values() if item["classification"] == "failure"
        ),
        "missing_count": sum(
            1 for item in statuses.values() if item["classification"] == "missing"
        ),
    }
    report = {
        "statuses": statuses,
        "summary": summary,
    }
    report_json_path = Path(args.report_json)
    report_md_path = Path(args.report_md)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _audit_training_status() -> dict[str, object]:
    artifact_path = Path("artifacts/models/effect_model_v3_trainprep_candidate.json")
    eval_path = Path("artifacts/reports/effect_model_v3_trainprep_candidate_eval.json")
    if artifact_path.exists() and eval_path.exists():
        return {
            "classification": "success",
            "status": "candidate_training_artifacts_present",
            "artifact_paths": [str(artifact_path), str(eval_path)],
        }
    return {
        "classification": "missing",
        "status": "candidate_training_artifacts_missing",
        "artifact_paths": [str(artifact_path), str(eval_path)],
    }


def _audit_replay_eval_status() -> dict[str, object]:
    path = Path("artifacts/reports/effect_replay_eval_prep_v1.json")
    if not path.exists():
        return {
            "classification": "missing",
            "status": "replay_eval_report_missing",
            "artifact_paths": [str(path)],
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = payload.get("status")
    classification = "success" if status == "completed_candidate_evaluated" else "failure"
    return {
        "classification": classification,
        "status": status,
        "artifact_paths": [str(path)],
    }


def _audit_chat_smoke_status() -> dict[str, object]:
    path = Path("artifacts/reports/chat_template_answer_eval_v1.json")
    if not path.exists():
        return {
            "classification": "missing",
            "status": "chat_template_eval_missing",
            "artifact_paths": [str(path)],
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    passed = (
        payload.get("supported_answer_pass_rate_pct") == 100.0
        and payload.get("citation_linkage_pass_rate_pct") == 100.0
        and payload.get("expected_terms_pass_rate_pct") == 100.0
        and payload.get("out_of_scope_probe_passed") is True
        and payload.get("unsupported_claim_probe_passed") is True
    )
    return {
        "classification": "success" if passed else "failure",
        "status": "chat_template_eval_verified" if passed else "chat_template_eval_regressed",
        "artifact_paths": [str(path)],
    }


def _audit_openai_adapter_status() -> dict[str, object]:
    local_path = Path("artifacts/reports/chat_openai_adapter_smoke_v1.json")
    live_path = Path("artifacts/reports/chat_openai_adapter_smoke_live_v1.json")
    result: dict[str, object] = {
        "artifact_paths": [str(local_path), str(live_path)],
    }
    if not local_path.exists():
        result.update(
            {
                "classification": "missing",
                "status": "adapter_local_smoke_missing",
            }
        )
        return result
    local_payload = json.loads(local_path.read_text(encoding="utf-8"))
    result["local_status"] = local_payload.get("provider")
    if not live_path.exists():
        result.update(
            {
                "classification": "missing",
                "status": "adapter_live_smoke_missing",
            }
        )
        return result
    live_payload = json.loads(live_path.read_text(encoding="utf-8"))
    live_provider = live_payload.get("provider")
    fallback_reason = live_payload.get("fallback_reason")
    attempted_live_call = live_payload.get("attempted_live_call")
    verification_passed = live_payload.get("verification_passed")
    if live_provider == "openai_responses_api" and verification_passed:
        classification = "success"
        status = "adapter_live_verified"
    else:
        classification = "failure"
        status = f"adapter_live_not_verified::{fallback_reason or 'unknown'}"
    result.update(
        {
            "classification": classification,
            "status": status,
            "live_provider": live_provider,
            "fallback_reason": fallback_reason,
            "attempted_live_call": attempted_live_call,
            "verification_passed": verification_passed,
        }
    )
    return result


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# post manual catch-up status v1",
        "",
        f"- success_count: `{report['summary']['success_count']}`",
        f"- failure_count: `{report['summary']['failure_count']}`",
        f"- missing_count: `{report['summary']['missing_count']}`",
        "",
        "## Statuses",
    ]
    for name, status in report["statuses"].items():
        lines.append(
            f"- `{name}`: classification=`{status['classification']}`, status=`{status['status']}`"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
