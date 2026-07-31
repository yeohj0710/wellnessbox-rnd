"""Audit every KPI answer key for source independence and real review.

Run this before sealing, and again before reporting a KPI number. It answers two
questions per indicator without anyone having to remember the history:

  이 정답이 엔진 자신의 파일에서 나왔는가
  기록된 검토가 실제로 사례를 읽을 시간이 있었는가

Usage:
  python scripts/audit_answer_key_integrity.py
  python scripts/audit_answer_key_integrity.py --json
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    audit_repository,
)
from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    drafter_source_index as build_drafter_source_index,
)


def drafter_source_index() -> dict[tuple[str, str], set[Path]]:
    """Compatibility wrapper for callers that audit this repository."""
    return build_drafter_source_index(ROOT)


def audit_all() -> dict[str, Any]:
    return audit_repository(ROOT)


def render(report: dict[str, Any]) -> None:
    mark = {"PASS": "OK  ", "FAIL": "FAIL", "REVIEW": "??  "}
    print("KPI 정답지 무결성 감사")
    print("─" * 68)
    for item in report["indicators"]:
        source = item["source_independence"]
        review = item["review_effort"]
        print(f"{mark[item['verdict']]} {item['indicator_id']}  ({item['case_count']}건)")
        print(f"       출처  {', '.join(item['draft_sources']) or '(없음)'}")
        if len(source.get("modules", [])) > 1:
            print(f"       모듈  {', '.join(Path(m).name for m in source['modules'])}")
        if source["reads_engine_logic"]:
            print(f"       엔진 파일 읽음  {', '.join(source['reads_engine_logic'])}")
        if source["reason"]:
            print(f"       → {source['reason']}")
        if review["decision_count"]:
            print(
                f"       검토  {review['decision_count']}건 / "
                f"{review['elapsed_seconds']}초 / 건당 {review['seconds_per_decision']}초 / "
                f"수정률 {review['edit_rate_pct']}%"
            )
        if review["reason"]:
            print(f"       → {review['reason']}")
        if item["seal_must_be_discarded"]:
            print("       ! 이 상태로 봉인돼 있다. 봉인을 폐기하고 다시 검토해야 한다.")
        print()
    print("─" * 68)
    print(
        f"통과 {report['passed']} / 실패 {report['failed']} / 확인필요 {report['needs_review']}"
        f"  →  {report['status']}"
    )
    if report["seals_to_discard"]:
        print(f"폐기해야 할 봉인: {', '.join(report['seals_to_discard'])}")


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="사람이 읽는 표 대신 JSON으로 낸다")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_all()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        render(report)
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
