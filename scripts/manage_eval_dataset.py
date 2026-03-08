import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.evals.dataset_tools import (
    build_eval_case_skeleton,
    load_and_validate_eval_cases,
    summarize_eval_cases,
    validate_eval_cases,
    write_eval_cases_jsonl,
)
from wellnessbox_rnd.evals.runner import load_eval_cases


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Scaffold, validate, and summarize frozen eval datasets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary", help="Print dataset coverage summary as JSON")
    summary_parser.add_argument(
        "--dataset",
        default="data/frozen_eval/frozen_eval_v1.jsonl",
        help="Path to JSONL eval dataset",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate dataset invariants")
    validate_parser.add_argument(
        "--dataset",
        default="data/frozen_eval/frozen_eval_v1.jsonl",
        help="Path to JSONL eval dataset",
    )

    scaffold_parser = subparsers.add_parser("scaffold", help="Create a new eval case skeleton")
    scaffold_parser.add_argument("--case-id", required=True, help="Stable eval case identifier")
    scaffold_parser.add_argument("--category", required=True, help="Scenario coverage category")
    scaffold_parser.add_argument("--description", required=True, help="Human-readable case summary")
    scaffold_parser.add_argument(
        "--goal",
        action="append",
        dest="goals",
        required=True,
        help="Recommendation goal. Repeat to add multiple goals.",
    )
    scaffold_parser.add_argument(
        "--required-ingredient",
        action="append",
        default=[],
        help="Required ingredient coverage target. Repeat to add multiple items.",
    )
    scaffold_parser.add_argument(
        "--explanation-term",
        action="append",
        default=[],
        help="Expected explanation proxy term. Repeat to add multiple terms.",
    )
    scaffold_parser.add_argument(
        "--expected-status",
        default="ok",
        choices=["ok", "needs_review", "blocked"],
        help="Expected deterministic status",
    )
    scaffold_parser.add_argument(
        "--expected-next-action",
        default="start_plan",
        choices=[
            "start_plan",
            "collect_more_input",
            "needs_human_review",
            "do_not_recommend",
        ],
        help="Expected deterministic next action",
    )
    scaffold_parser.add_argument(
        "--dataset",
        default="data/frozen_eval/frozen_eval_v1.jsonl",
        help="Target JSONL dataset path when --append is used",
    )
    scaffold_parser.add_argument(
        "--append",
        action="store_true",
        help="Append the scaffolded case to the dataset and rewrite sorted JSONL",
    )

    return parser


def run_summary(dataset_path: str) -> int:
    cases, issues = load_and_validate_eval_cases(dataset_path)
    payload = {
        "dataset_path": str(Path(dataset_path)),
        "summary": summarize_eval_cases(cases),
        "validation_issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def run_validate(dataset_path: str) -> int:
    _, issues = load_and_validate_eval_cases(dataset_path)
    if issues:
        payload = {"dataset_path": dataset_path, "issues": issues}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"dataset_path": dataset_path, "issues": []}, ensure_ascii=False, indent=2))
    return 0


def run_scaffold(args) -> int:
    case = build_eval_case_skeleton(
        case_id=args.case_id,
        category=args.category,
        description=args.description,
        goals=args.goals,
        required_ingredients=args.required_ingredient,
        expected_status=args.expected_status,
        expected_next_action=args.expected_next_action,
        required_explanation_terms=args.explanation_term,
    )

    if not args.append:
        print(json.dumps(case, ensure_ascii=False, indent=2))
        return 0

    dataset_path = Path(args.dataset)
    existing_cases = []
    if dataset_path.exists():
        existing_cases = [
            json.loads(line)
            for line in dataset_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    merged_cases = [item for item in existing_cases if item["case_id"] != args.case_id]
    merged_cases.append(case)
    write_eval_cases_jsonl(merged_cases, dataset_path)

    issues = validate_eval_cases(load_eval_cases(dataset_path))
    if issues:
        payload = {"dataset_path": str(dataset_path), "issues": issues}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    payload = {
        "dataset_path": str(dataset_path),
        "case_count": len(merged_cases),
        "case_id": args.case_id,
        "appended": True,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "summary":
        status = run_summary(args.dataset)
    elif args.command == "validate":
        status = run_validate(args.dataset)
    else:
        status = run_scaffold(args)

    sys_exit(status)


if __name__ == "__main__":
    main()
