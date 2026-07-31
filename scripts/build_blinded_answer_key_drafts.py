"""Write KPI-3 and KPI-4 answer-key drafts that do not copy the engine's tables.

Replaces the drafts the 2026-07-31 audit rejected. Feed the result in with:

  python scripts/run_answer_key_workbench.py draft --indicator KPI-4 \\
      --cases data/original_plan/kpi/drafts/kpi4_blinded_cases_v1.json \\
      --draft-source health_checker_reference_extract_v1@blinded_drafters \\
      --drafting-agent codex --blinded-from-registry --overwrite

KPI-3 drafts carry no answer. The reviewer supplies every one, so each case
records as an edit rather than an acceptance.

Usage:
  python scripts/build_blinded_answer_key_drafts.py
  python scripts/build_blinded_answer_key_drafts.py --indicator KPI-4
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.blinded_drafters import (  # noqa: E402
    BLINDED_FROM,
    DRAFT_SOURCES,
    DRAFTERS,
    KPI3_UNDECIDED,
    draft_cases,
)

OUTPUT_DIR = ROOT / "data/original_plan/kpi/drafts"


def output_path(indicator_id: str) -> Path:
    slug = indicator_id.lower().replace("-", "")
    return OUTPUT_DIR / f"{slug}_blinded_cases_v1.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--indicator",
        action="append",
        choices=sorted(DRAFTERS),
        help="생략하면 지원하는 지표를 모두 만든다",
    )
    parser.add_argument("--count", type=int, default=100, help="지표별 사례 수")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    indicators = args.indicator or sorted(DRAFTERS)
    results = []

    for indicator_id in indicators:
        cases = draft_cases(indicator_id, ROOT, case_count=args.count)
        target = output_path(indicator_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        distinct_prompts = len({case["prompt"] for case in cases})
        distinct_answers = len({tuple(sorted(case["draft_answer"])) for case in cases})
        reviewer_supplied = all(
            case["draft_answer"] == [KPI3_UNDECIDED] for case in cases
        )
        results.append(
            {
                "indicator_id": indicator_id,
                "path": str(target),
                "draft_source": DRAFT_SOURCES[indicator_id],
                "case_count": len(cases),
                "distinct_prompt_count": distinct_prompts,
                "distinct_answer_count": distinct_answers,
                "answers_supplied_by_reviewer": reviewer_supplied,
                "meets_minimum_sample": len(cases) >= 100 and distinct_prompts >= 100,
            }
        )

    print(json.dumps(
        {
            "status": "READY",
            "blinded_from": list(BLINDED_FROM),
            "outputs": results,
        },
        ensure_ascii=False, indent=2,
    ))
    return 0 if all(item["meets_minimum_sample"] for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
