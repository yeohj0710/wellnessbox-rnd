"""KPI-6 약물이상반응 12개월 집계를 만든다.

측정 시점 기준 최근 12개월 창에서 엔진 추천 복용과 연결된 이상반응 보고 수를 센다.
같은 창의 엔진 추천 세션 수도 함께 센다. 노출이 없으면 0건은 통과가 아니라
`INSUFFICIENT_EXPOSURE`로 표시한다.

외부에서 운영해 온 사이트의 보고를 넣으려면 `--external-reports` 로 JSON을 준다.
그 파일의 각 보고에 `engine_recommended: true` 가 있어야 KPI-6에 포함된다.
지표 정의가 '엔진 추천 건강기능식품 복용으로 인한' 이상반응이기 때문이다.

    {"source_system": "<사이트 이름>",
     "reports": [{"reported_at": "2026-03-01T00:00:00Z", "engine_recommended": true}]}
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.governance.adverse_event_ledger import (  # noqa: E402
    build_adverse_event_report_v1,
    load_external_reports,
    read_operational_exposure,
    window_start,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = "etc/local_research_runtime/interim.sqlite3"
DEFAULT_OUTPUT = "artifacts/reports/kpi6_adverse_event_report_v1.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--external-reports", default=None)
    parser.add_argument("--measured-at", default=None, help="기본값은 지금")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    measured_at = args.measured_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    since = window_start(measured_at)

    exposure = read_operational_exposure(ROOT / args.database, since=since)
    external = load_external_reports(
        Path(args.external_reports) if args.external_reports else None
    )
    report = build_adverse_event_report_v1(
        measured_at=measured_at, exposure=exposure, external=external
    )

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps(
        {
            "status": report["status"],
            "report_path": str(output),
            "window_start": report["window_start"],
            "adverse_event_count": report["adverse_event_count"],
            "target_max_events": report["target_max_events"],
            "exposure": report["exposure"],
            "external_source": report["external_source"],
            "interpretation": report["interpretation"],
        },
        ensure_ascii=False, indent=2,
    ))
    return 0 if report["meets_target"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
