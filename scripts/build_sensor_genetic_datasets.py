"""KPI-7용 웨어러블·연속혈당·유전자 합성 데이터셋 100개를 만든다.

시중 기기 스키마(Apple HealthKit, Samsung Health, Dexcom v3 EGV, SNP 패널)를
참고해 필드 모양을 맞췄다. 실제 측정값이 아니며 모든 레코드에
`data_class: SYNTHETIC`이 붙는다.

생성 뒤 저장소 파서를 실제로 통과시켜 연동율 R = (r_W + r_C + r_G)/3 을 계산한다.
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.domain.sensor_parser import (  # noqa: E402
    normalize_sensor_genetic_payloads,
)
from wellnessbox_rnd.synthetic.sensor_genetic_datasets import (  # noqa: E402
    GeneratorConfig,
    build_sensor_genetic_datasets_v1,
    summarise_linkage,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = "data/synthetic/sensor_genetic_datasets_v1.json"
DEFAULT_SUMMARY = "artifacts/reports/kpi7_linkage_summary_v1.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--wearable-count", type=int, default=34)
    parser.add_argument("--cgm-count", type=int, default=33)
    parser.add_argument("--genetic-count", type=int, default=33)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY)
    return parser


AVAILABILITY_FLAG = {
    "wearable": "wearable_available",
    "cgm": "cgm_available",
    "genetic": "genetic_available",
}


def linked_dataset_ids(collection: dict) -> set[str]:
    """Keep the datasets the parser actually recognised for their own family.

    The parser always returns a snapshot, so a successful call is not proof of
    linkage. The per-family availability flag is.
    """
    linked: set[str] = set()
    for item in collection["datasets"]:
        try:
            snapshot = normalize_sensor_genetic_payloads(
                wearable_payload=item.get("wearable_payload"),
                cgm_payload=item.get("cgm_payload"),
                genetic_payload=item.get("genetic_payload"),
            )
        except Exception:  # noqa: BLE001 - a parser failure means the dataset did not link
            continue
        if getattr(snapshot, AVAILABILITY_FLAG[item["family"]], False):
            linked.add(item["dataset_id"])
    return linked


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    collection = build_sensor_genetic_datasets_v1(
        GeneratorConfig(
            wearable_count=args.wearable_count,
            cgm_count=args.cgm_count,
            genetic_count=args.genetic_count,
        )
    )
    summary = summarise_linkage(collection, linked_dataset_ids(collection))

    write_json(ROOT / args.output, collection)
    write_json(ROOT / args.summary_output, summary)

    print(json.dumps(
        {
            "status": "READY" if summary["meets_target"] else "BELOW_TARGET",
            "dataset_path": args.output,
            "summary_path": args.summary_output,
            "counts": collection["counts"],
            "kpi7_requirement": collection["kpi7_requirement"],
            "per_family_rate_pct": summary["per_family_rate_pct"],
            "linkage_rate_pct": summary["linkage_rate_pct"],
            "target_pct": summary["target_pct"],
            "data_class": collection["data_class"],
        },
        ensure_ascii=False, indent=2,
    ))
    return 0 if summary["meets_target"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
