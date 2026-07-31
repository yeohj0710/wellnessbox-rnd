"""Write KPI-1 and KPI-5 answer-key drafts from the independent reference corpus.

The existing workbench already accepts an external draft file, so this script
only produces the file. Feed it in with:

  python scripts/run_answer_key_workbench.py draft --indicator KPI-1 \\
      --cases data/original_plan/kpi/drafts/kpi1_reference_corpus_cases_v1.json \\
      --draft-source health_checker_reference_extract_v1 --overwrite

Usage:
  python scripts/build_reference_corpus_answer_key_drafts.py
  python scripts/build_reference_corpus_answer_key_drafts.py --indicator KPI-5
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.reference_corpus_drafters import (  # noqa: E402
    DRAFT_SOURCE,
    DRAFTERS,
    draft_cases,
)

OUTPUT_DIR = ROOT / "data/original_plan/kpi/drafts"


def output_path(indicator_id: str) -> Path:
    slug = indicator_id.lower().replace("-", "")
    return OUTPUT_DIR / f"{slug}_reference_corpus_cases_v1.json"


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
        distinct = len({tuple(sorted(case["draft_answer"])) for case in cases})
        results.append(
            {
                "indicator_id": indicator_id,
                "path": str(target),
                "case_count": len(cases),
                "distinct_answer_count": distinct,
                "meets_minimum_sample": len(cases) >= 100,
            }
        )

    print(json.dumps(
        {"status": "READY", "draft_source": DRAFT_SOURCE, "outputs": results},
        ensure_ascii=False, indent=2,
    ))
    return 0 if all(item["meets_minimum_sample"] for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
