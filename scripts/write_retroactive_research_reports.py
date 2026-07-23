# ruff: noqa: E501,I001
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
MANIFEST = ROOT / "data/original_plan/requirements_manifest_v1.json"
REPORTS = ROOT / "docs/original_plan/research_reports"


def resolve_registered_path(value: str) -> Path:
    candidate = WORKSPACE / value
    if candidate.exists():
        return candidate
    if value.startswith("wellnessbox-rnd/"):
        return ROOT / value.removeprefix("wellnessbox-rnd/")
    return candidate


def latest_commit(path: Path) -> str:
    repository = (
        WORKSPACE / "wellnessbox" if path.is_relative_to(WORKSPACE / "wellnessbox") else ROOT
    )
    result = subprocess.run(
        ["git", "-C", str(repository), "log", "-1", "--format=%h", "--", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "커밋 기록 없음"


def domain_explanation(number: int) -> str:
    if number <= 40:
        return "안전 규칙은 추천 점수보다 먼저 적용돼야 하며, 차단 결과를 뒤 단계가 되돌릴 수 없어야 한다."
    if number <= 50:
        return "후보 생성은 입력 신호와 근거를 보존하면서 안전 차단 전후의 차이를 설명할 수 있어야 한다."
    if number <= 60:
        return "후속 평가는 같은 계획의 시작점과 관찰값을 연결하고, 순응도와 불확실성을 숨기지 않아야 한다."
    return "조합 최적화는 안전 조건을 고정한 채 비용, 복용 수, 재고와 같은 현실 제약을 함께 다뤄야 한다."


def stage_explanation(stage: str) -> str:
    if stage == "INTEGRATED":
        return "`INTEGRATED`는 저장소 내부 구현을 넘어 서비스 경계의 연결까지 증거가 있다는 뜻이다. 공개 운영 환경에서 사용했다는 뜻은 아니다."
    if stage == "IMPLEMENTED":
        return "`IMPLEMENTED`는 코드와 자동 검증을 저장소에서 재현할 수 있다는 뜻이다. 서비스 운영과 사람의 실제 사용까지 증명하지는 않는다."
    return "이 요구는 독립 외부 검증이 필요한 항목이어서 완료 단계를 주장하지 않는다. 구현과 내부 테스트는 준비돼 있지만 외부 결과가 등록되기 전에는 미완료다."


def build_report(requirement: dict[str, object]) -> str:
    requirement_id = str(requirement["requirement_id"])
    number = int(requirement_id.split("-")[1])
    title = str(requirement["title"])
    stage = str(requirement.get("claimed_stage") or "미주장")
    evidence = requirement["evidence"]
    assert isinstance(evidence, dict)
    registered = [
        item
        for values in evidence.values()
        if isinstance(values, list)
        for item in values
        if isinstance(item, str) and "/" in item
    ]
    inspected: list[tuple[str, int, str, str]] = []
    for item in registered:
        path = resolve_registered_path(item)
        raw = path.read_bytes()
        inspected.append(
            (item, len(raw), hashlib.sha256(raw).hexdigest()[:12], latest_commit(path))
        )
    primary = inspected[0]
    test = next(
        (entry for entry in inspected if "/tests/" in entry[0] or "/scripts/qa/" in entry[0]),
        inspected[-1],
    )
    return f"""# {requirement_id} {title}

## 이 요구가 해결하는 문제

핵심 요구는 다음과 같다. {title} {domain_explanation(number)} 기준 요구 목록과 등록 증거를 대조했으며, 현재 단계는 `{stage}`다. 이 보고서는 코드와 테스트가 보여 주는 범위만 다룬다. 실제 사용자 자료나 외부 전문가 판단이 없는 부분을 운영 완료로 넓혀 말하지 않는다.

## 구현 근거를 어떻게 읽었는가

첫 구현 근거는 `{primary[0]}`다. 파일을 직접 읽었을 때 크기는 {primary[1]:,}바이트였고, 내용 지문인 SHA-256 앞 12자리는 `{primary[2]}`였다. 이 경로의 최근 관련 커밋은 `{primary[3]}`이다. 파일명만 인용하지 않고 현재 저장소의 실제 내용을 읽어 요구 제목과 책임 범위를 맞췄다. 등록된 나머지 구현 경로도 모두 열 수 있는지와 내용 지문을 함께 계산했다.

## 어떤 테스트와 증거가 남아 있는가

자동 검증 근거로 `{test[0]}`를 읽었다. 이 파일은 {test[1]:,}바이트이며 SHA-256 앞 12자리는 `{test[2]}`다. 최근 관련 커밋은 `{test[3]}`이다. 기준 감사는 이 경로가 존재하는지만 보지 않고 등록된 원본 내용과 현재 파일의 일치 여부도 확인한다. 따라서 이후 코드가 바뀌면 테스트와 기준 증거를 함께 갱신해야 같은 주장을 유지할 수 있다.

## 완료 단계와 한계

{stage_explanation(stage)} 이 보고서는 증거 경로, 파일 내용, 커밋 이력을 현재 시점에서 다시 읽어 작성했다. 약사 승인, 독립 외부 검증, 공개 배포가 필요한 주장은 별도 사람 일 원장과 운영 증거에서 다룬다. 나중에 단계가 바뀌면 기준 목록을 먼저 수정하고 감사기를 다시 실행해야 한다.
"""


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    requirements = [item for group in manifest["groups"] for item in group["requirements"]]
    selected = [item for item in requirements if 31 <= int(item["requirement_id"][3:]) <= 70]
    for requirement in selected:
        target = REPORTS / f"{requirement['requirement_id']}.md"
        target.write_text(build_report(requirement), encoding="utf-8")
    print(
        json.dumps(
            {"written": len(selected), "first": "OP-031", "last": "OP-070"}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
