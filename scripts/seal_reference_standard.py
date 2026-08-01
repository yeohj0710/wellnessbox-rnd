"""약사가 만든 정답을 엔진 실행 전에 봉인하고, 나중에 대조한다.

KPI-1·3·4·5는 사람이 만든 정답과 엔진 출력을 비교한다. 정답을 엔진 출력을 보고
만들면 점수가 자동으로 100%에 수렴해 측정이 무의미해진다. 이 명령은 정답을 먼저
확정해 지문 값으로 봉인하고, 대조 단계에서 봉인이 그대로인지 확인한다.

봉인 후 정답을 고치면 지문이 달라져 대조가 거부된다. 그래서 내부 인력만으로도
유효한 측정 순서를 증명할 수 있다.

사용법:
  python scripts/seal_reference_standard.py seal --indicator KPI-1 \\
      --cases data/original_plan/kpi/kpi1_reference_cases.json --by 권혁찬
  python scripts/seal_reference_standard.py compare --indicator KPI-1 \\
      --engine-output artifacts/kpi/kpi1_engine_output.json
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    audit_sealing_readiness,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    adjudicated_answer_key,
    build_provenance,
    load_workbench,
    summarise_adjudication,
)
from wellnessbox_rnd.evals.reference_standard import (  # noqa: E402
    canonical_digest,
    load_contract,
    score_against_seal,
    seal_reference_standard,
    verify_seal,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
SEAL_DIR = ROOT / "data/original_plan/kpi/seals"
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
COMPARISON_DIR = ROOT / "artifacts/kpi"


def seal_path(indicator_id: str) -> Path:
    return SEAL_DIR / f"{indicator_id.lower().replace('-', '')}_reference_seal_v1.json"


def workbench_path(indicator_id: str) -> Path:
    name = f"{indicator_id.lower().replace('-', '')}_workbench_v1.json"
    return WORKBENCH_DIR / name


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    seal = sub.add_parser("seal", help="정답을 봉인한다. 엔진 실행 전에 한다")
    seal.add_argument("--indicator", required=True)
    seal.add_argument("--cases", required=True, help="사례별 정답 JSON 경로")
    seal.add_argument("--by", required=True, help="정답을 만든 사람 이름")
    seal.add_argument(
        "--system-under-test-id",
        "--system-under-test-agent",
        dest="system_under_test_id",
        default="",
        help="측정 대상 엔진의 고유 ID. 초안 작성 주체와 같을 수 없습니다.",
    )

    check = sub.add_parser("verify", help="봉인이 그대로인지 확인한다")
    check.add_argument("--indicator", required=True)

    compare = sub.add_parser("compare", help="봉인된 정답과 엔진 출력을 대조한다")
    compare.add_argument("--indicator", required=True)
    compare.add_argument("--engine-output", required=True)
    compare.add_argument("--output", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = load_contract(ROOT)
    target = seal_path(args.indicator)

    if args.command == "seal":
        if target.is_file():
            print(json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": "seal_already_exists",
                    "path": str(target),
                    "note": "이미 봉인된 정답이 있습니다. 다시 봉인하려면 "
                            "기존 파일을 먼저 보존 이동하세요.",
                },
                ensure_ascii=False, indent=2,
            ))
            return 2
        integrity = audit_sealing_readiness(ROOT, args.indicator)
        if integrity["status"] != "READY":
            print(json.dumps(integrity, ensure_ascii=False, indent=2))
            return 2

        workbench = load_workbench(workbench_path(args.indicator))
        summary = summarise_adjudication(workbench)
        canonical_cases = adjudicated_answer_key(workbench)
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        if canonical_digest(cases) != canonical_digest(canonical_cases):
            print(json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": "cases_do_not_match_adjudicated_workbench",
                    "indicator_id": args.indicator,
                    "workbench_path": str(workbench_path(args.indicator)),
                },
                ensure_ascii=False, indent=2,
            ))
            return 2
        if summary["reviewers"] != [args.by.strip()]:
            print(json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": "sealer_does_not_match_workbench_reviewer",
                    "sealed_by": args.by.strip(),
                    "reviewers": summary["reviewers"],
                },
                ensure_ascii=False, indent=2,
            ))
            return 2
        try:
            provenance = build_provenance(
                workbench,
                summary,
                system_under_test_id=args.system_under_test_id,
            )
        except ValueError as exc:
            print(json.dumps(
                {"status": "BLOCKED", "reason": str(exc)},
                ensure_ascii=False,
                indent=2,
            ))
            return 2
        seal = seal_reference_standard(
            indicator_id=args.indicator,
            cases=cases,
            sealed_by=args.by,
            sealed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            contract=contract,
        )
        seal["provenance"] = provenance
        seal["provenance"]["integrity_audit"] = integrity["integrity_audit"]
        write_json(target, seal)
        print(json.dumps(
            {
                "status": "READY",
                "seal_path": str(target),
                "case_count": seal["case_count"],
                "meets_minimum_sample": seal["meets_minimum_sample"],
                "minimum_sample_count": seal["minimum_sample_count"],
                "seal_sha256": seal["seal_sha256"],
            },
            ensure_ascii=False, indent=2,
        ))
        return 0 if seal["meets_minimum_sample"] else 2

    if not target.is_file():
        print(json.dumps(
            {"status": "BLOCKED", "reason": "seal_not_found", "path": str(target)},
            ensure_ascii=False, indent=2,
        ))
        return 2
    seal = json.loads(target.read_text(encoding="utf-8"))

    if args.command == "verify":
        check = verify_seal(seal)
        print(json.dumps(check, ensure_ascii=False, indent=2))
        return 0 if check["seal_intact"] else 1

    engine_output = json.loads(Path(args.engine_output).read_text(encoding="utf-8"))
    try:
        comparison = score_against_seal(seal=seal, engine_output=engine_output)
    except ValueError as exc:
        print(json.dumps(
            {
                "status": "BLOCKED",
                "reason": str(exc),
                "seal_path": str(target),
                "note": "봉인 이후 정답이 바뀌었습니다. 엔진 출력을 보고 정답을 고치면 "
                        "측정이 무효이므로 채점하지 않습니다.",
            },
            ensure_ascii=False, indent=2,
        ))
        return 1
    output = Path(args.output) if args.output else (
        COMPARISON_DIR / f"{args.indicator.lower().replace('-', '')}_comparison_v1.json"
    )
    write_json(output, comparison)
    print(json.dumps(
        {
            "status": "READY",
            "comparison_path": str(output),
            "mean_score_pct": comparison["mean_score_pct"],
            "case_count": comparison["case_count"],
            "meets_minimum_sample": comparison["meets_minimum_sample"],
            "measurement_environment": comparison["measurement_environment"],
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
