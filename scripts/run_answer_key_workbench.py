"""정답 초안을 AI가 만들고, 사람이 한 건씩 확정한다.

100건을 맨손으로 쓰는 대신 이렇게 나눈다.

  draft   독립 출처(엔진이 아님)가 초안 100건을 만든다
  review  사람이 한 건씩 수락·수정·반려로 확정한다. Enter만 누르면 수락이다
  seal    확정된 정답을 봉인한다. 그다음에 엔진을 돌린다

초안 출처가 측정 대상 엔진이면 거부한다. 수정률은 기록에 남는다. 전부 그대로
수락하면 수정률 0%가 그대로 보인다.

사용법:
  python scripts/run_answer_key_workbench.py draft  --indicator KPI-1
  python scripts/run_answer_key_workbench.py review --indicator KPI-1 --by 권혁찬
  python scripts/run_answer_key_workbench.py seal   --indicator KPI-1
  python scripts/run_answer_key_workbench.py status --indicator KPI-1
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.evals.answer_key_drafters import (  # noqa: E402
    DRAFT_SOURCE,
    draft_cases,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    CaseDraft,
    Workbench,
    adjudicated_answer_key,
    build_drafts,
    build_provenance,
    decide,
    load_workbench,
    save_workbench,
    summarise_adjudication,
)
from wellnessbox_rnd.evals.reference_standard import (  # noqa: E402
    load_contract,
    seal_reference_standard,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
SEAL_DIR = ROOT / "data/original_plan/kpi/seals"
BAR = "─" * 68


def slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def workbench_path(indicator_id: str) -> Path:
    return WORKBENCH_DIR / f"{slug(indicator_id)}_workbench_v1.json"


def seal_path(indicator_id: str) -> Path:
    return SEAL_DIR / f"{slug(indicator_id)}_reference_seal_v1.json"


def say(message: str = "") -> None:
    print(message, flush=True)


def cmd_draft(args) -> int:
    target = workbench_path(args.indicator)
    if target.is_file() and not args.overwrite:
        say(f"이미 초안이 있습니다: {target}")
        say("다시 만들려면 --overwrite 를 붙이세요. 기존 판단 기록도 함께 사라집니다.")
        return 2

    if args.cases:
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        source = args.draft_source or "external_draft_file"
    else:
        cases = draft_cases(args.indicator, ROOT, case_count=args.count)
        source = args.draft_source or DRAFT_SOURCE

    packaged = build_drafts(indicator_id=args.indicator, cases=cases, draft_source=source)
    workbench = Workbench(
        args.indicator, [CaseDraft(**item) for item in packaged["drafts"]], {}
    )
    save_workbench(target, workbench)

    say(json.dumps(
        {
            "status": "READY",
            "workbench_path": str(target),
            "case_count": packaged["case_count"],
            "draft_source": source,
            "next": (
                "python scripts/run_answer_key_workbench.py review "
                f"--indicator {args.indicator} --by <이름>"
            ),
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


def cmd_review(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}. 먼저 draft 를 실행하세요.")
        return 2
    workbench = load_workbench(target)
    pending = workbench.pending()
    if not pending:
        say("남은 건이 없습니다. seal 로 넘어가세요.")
        return 0

    say(BAR)
    say(f" {args.indicator} 정답 확정  —  남은 {len(pending)}건 / 전체 {len(workbench.drafts)}건")
    say(BAR)
    say("Enter = 초안 그대로 수락 | e = 수정 | r = 반려 | q = 저장하고 종료")
    say("수정은 성분을 쉼표로 구분해 입력합니다. 예: omega3, vitaminD, magnesium")

    for position, draft in enumerate(pending, start=1):
        say()
        say(f"[{position}/{len(pending)}] {draft.case_id}")
        say(f"  상황: {draft.prompt}")
        say(f"  초안: {', '.join(draft.draft_answer)}")
        if draft.draft_rationale:
            say(f"  근거: {draft.draft_rationale}")
        try:
            answer = input("  > ").strip()
        except EOFError:
            answer = "q"

        if answer.lower() == "q":
            break
        if answer.lower() == "r":
            note = input("  반려 사유: ").strip()
            workbench.decisions[draft.case_id] = decide(
                draft=draft, final_answer=None, decided_by=args.by, note=note
            )
            save_workbench(target, workbench)
            continue
        if answer.lower() == "e":
            edited = input("  수정할 성분(쉼표 구분): ").strip()
            final = [item.strip() for item in edited.split(",") if item.strip()]
            if not final:
                say("  빈 값이라 건너뜁니다.")
                continue
        else:
            final = list(draft.draft_answer)

        workbench.decisions[draft.case_id] = decide(
            draft=draft, final_answer=final, decided_by=args.by
        )
        save_workbench(target, workbench)

    summary = summarise_adjudication(workbench)
    say()
    say(BAR)
    say(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["warnings"]:
        say()
        say("주의: " + ", ".join(summary["warnings"]))
    return 0


def cmd_status(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(json.dumps({"status": "NOT_STARTED", "workbench_path": str(target)},
                       ensure_ascii=False, indent=2))
        return 2
    summary = summarise_adjudication(load_workbench(target))
    say(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["complete"] else 2


def cmd_seal(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    workbench = load_workbench(target)
    summary = summarise_adjudication(workbench)
    if not summary["complete"]:
        say(json.dumps(
            {"status": "BLOCKED", "reason": "adjudication_incomplete",
             "pending": summary["counts"]["pending"]},
            ensure_ascii=False, indent=2,
        ))
        return 2

    destination = seal_path(args.indicator)
    if destination.is_file():
        say(json.dumps(
            {"status": "BLOCKED", "reason": "seal_already_exists", "path": str(destination)},
            ensure_ascii=False, indent=2,
        ))
        return 2

    reviewers = summary["reviewers"]
    if len(reviewers) != 1:
        say(json.dumps(
            {"status": "BLOCKED", "reason": "expected_exactly_one_reviewer",
             "reviewers": reviewers},
            ensure_ascii=False, indent=2,
        ))
        return 2

    seal = seal_reference_standard(
        indicator_id=args.indicator,
        cases=adjudicated_answer_key(workbench),
        sealed_by=reviewers[0],
        sealed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        contract=load_contract(ROOT),
    )
    seal["provenance"] = build_provenance(workbench, summary)
    write_json(destination, seal)

    say(json.dumps(
        {
            "status": "READY" if seal["meets_minimum_sample"] else "BELOW_MINIMUM_SAMPLE",
            "seal_path": str(destination),
            "case_count": seal["case_count"],
            "minimum_sample_count": seal["minimum_sample_count"],
            "edit_rate_pct": summary["edit_rate_pct"],
            "warnings": summary["warnings"],
            "seal_sha256": seal["seal_sha256"],
        },
        ensure_ascii=False, indent=2,
    ))
    return 0 if seal["meets_minimum_sample"] else 2


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft", help="독립 출처로 초안을 만든다")
    draft.add_argument("--indicator", required=True)
    draft.add_argument("--count", type=int, default=100)
    draft.add_argument("--cases", default=None, help="외부 초안 파일 경로")
    draft.add_argument("--draft-source", default=None)
    draft.add_argument("--overwrite", action="store_true")
    draft.set_defaults(func=cmd_draft)

    review = sub.add_parser("review", help="한 건씩 확정한다")
    review.add_argument("--indicator", required=True)
    review.add_argument("--by", required=True, help="확정하는 사람 이름")
    review.set_defaults(func=cmd_review)

    status = sub.add_parser("status", help="진행 상황만 본다")
    status.add_argument("--indicator", required=True)
    status.set_defaults(func=cmd_status)

    seal = sub.add_parser("seal", help="확정된 정답을 봉인한다")
    seal.add_argument("--indicator", required=True)
    seal.set_defaults(func=cmd_seal)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
