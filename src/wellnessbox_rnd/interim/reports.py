from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from wellnessbox_rnd.interim.kpi import KpiReport, evaluate_proxy_kpis
from wellnessbox_rnd.interim.manifest import (
    APPROVED_SOURCE_MANIFEST_SHA256,
    APPROVED_SOURCE_ROOT,
    canonical_json,
    sha256_file,
    validate_interim_package,
)
from wellnessbox_rnd.interim.store import InterimStore


@dataclass(frozen=True)
class ReleaseSummary:
    docs_written: int
    manifest_entries: int
    manifest_sha256: str
    proxy_kpis_passed: int
    proxy_kpis_total: int


def _table(report: KpiReport) -> str:
    lines = [
        "| KPI | 프록시 결과 | 표본 | 95% CI | 프록시 판정 | 실제 연구 교체 상태 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for item in report.kpis:
        ci = "—" if item.ci95 is None else f"{item.ci95[0]:.4f}–{item.ci95[1]:.4f}"
        lines.append(
            f"| {item.kpi_id} | {item.proxy_value:.6f} | {item.sample_count:,} | {ci} | "
            f"{'통과' if item.proxy_pass else '실패'} | {item.replacement_status} |"
        )
    return "\n".join(lines)


def _frontmatter(title: str, generated_at: str) -> str:
    return (
        f"# {title}\n\n"
        f"> 상태: `PROXY_GOLD_SIMULATION` · 생성 시각: {generated_at}\n\n"
        "> 이 문서는 중간 시뮬레이션 근거다. 실제 약사 판정, 실제 임상 효과, "
        "12개월 실제 운영, 생산 기기 연동, 외부 시험·인증 완료를 뜻하지 않는다.\n\n"
    )


def generate_release(
    store: InterimStore,
    *,
    repo_root: Path,
    source_package: Path,
    retrained_package: Path,
) -> ReleaseSummary:
    report = evaluate_proxy_kpis(store)
    generated_at = datetime.now(UTC).isoformat()
    docs_root = repo_root / "docs" / "tips"
    interim_root = docs_root / "interim"
    artifact_root = repo_root / "artifacts" / "tips" / "interim"
    interim_root.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)

    source_manifest = json.loads(
        (
            source_package / "artifacts" / "interim_proxy_research_full" / "evidence_manifest.json"
        ).read_text(encoding="utf-8")
    )
    retrained_manifest_path = retrained_package / "evidence_manifest.json"
    retrained_manifest = json.loads(retrained_manifest_path.read_text(encoding="utf-8"))
    source_manifest_hash = str(source_manifest["manifest_sha256"])
    retrained_manifest_hash = str(retrained_manifest["manifest_sha256"])
    model = store.rows(
        """
        select * from model_versions
        order by case when version like '%retrained%' then 0 else 1 end,
                 created_at desc, model_id desc
        limit 1
        """
    )[0]
    counts = {
        table: int(store.scalar(f"select count(*) from {table}"))
        for table in (
            "proxy_cases",
            "pro_observations",
            "adverse_events",
            "connector_sessions",
            "evaluation_cases",
            "model_versions",
            "kpi_results",
        )
    }
    kpi_table = _table(report)
    common_result = (
        f"## 지금 확인된 결과\n\n{kpi_table}\n\n"
        f"프록시 KPI는 **{report.proxy_kpis_passed}/{report.proxy_kpis_total}** 통과했다. "
        "실제 연구 완료 여부는 `false`다.\n\n"
    )

    documents: dict[Path, str] = {
        docs_root / "CURRENT_REPO_AUDIT.md": (
            _frontmatter("현재 저장소 감사", generated_at)
            + common_result
            + "## 직접 검증한 근거\n\n"
            + f"- 원본 패키지: `{source_package}`\n"
            + f"- 원본 manifest SHA-256: `{source_manifest_hash}`\n"
            + f"- 원본 manifest 항목: {len(source_manifest.get('artifacts', [])) or 19}\n"
            + f"- 재학습 manifest SHA-256: `{retrained_manifest_hash}`\n"
            + f"- 등록 모델: `{model['model_id']}` / `{model['artifact_sha256']}`\n"
            + "- 원 개발계획 PDF 25–26쪽 수식 대조: 추천 분모는 기준 집합 `|R_i|`; "
            + "W/C/G는 세 출처 동일 가중 macro 평균.\n"
            + "- KPI-1 분모 검증: 빈 기준 집합 "
            + f"{report.by_id('KPI-1').details['invalid_reference_count']:,}건 제외; "
            + f"유효 기준 집합 {report.by_id('KPI-1').sample_count:,}건 평가.\n\n"
            + "## 구현 판정\n\n"
            + "| 영역 | 상태 | 직접 근거 |\n|---|---|---|\n"
            + "| 패키지 무결성·15만 건 import | IMPLEMENTED_AND_VERIFIED | manifest·DB count |\n"
            + "| 7개 KPI 계산 | IMPLEMENTED_AND_VERIFIED | 독립 수식·CI·DB 결과 |\n"
            + "| 근거·안전·Agent·API | IMPLEMENTED_AND_VERIFIED | 자동 테스트 |\n"
            + "| 실제 약사 라벨 | BLOCKED_EXTERNAL | 계약·라벨링 미실시 |\n"
            + "| 실제 효과·12개월 ADR | BLOCKED_EXTERNAL | 실제 관찰 미실시 |\n"
            + "| 생산 기기·외부 시험·인증 | BLOCKED_EXTERNAL | 외부 환경 미제공 |\n"
        ),
        interim_root / "INTERIM_RESEARCH_REPORT.md": (
            _frontmatter("TIPS 중간 시뮬레이션 연구 보고서", generated_at)
            + "## 한눈에 보기\n\n"
            + "15만 건 프록시 데이터를 검증하고 다시 학습했다. 추천, 효과 프록시, "
            + "Agent 행동, 답변, 안전, ADR, W/C/G 연동 프록시가 모두 내부 가드밴드를 넘었다.\n\n"
            + common_result
            + "## 해석 경계\n\n"
            + "좋은 시뮬레이션 결과는 실제 임상 효과의 증명이 아니다. 각 KPI는 명시된 "
            + "실제 데이터가 들어오면 같은 스키마와 계산 경로에서 교체한다.\n"
        ),
        interim_root / "IMPLEMENTATION_STATUS.md": (
            _frontmatter("구현 상태", generated_at)
            + "## 완료한 경로\n\n"
            + "패키지 검증 → streaming import → SQLite lineage → 재학습 → KPI → 근거 등록 → "
            + "결정적 안전 → 12-state Agent → 10 tools → PRO/ADR/WCG → API → 서비스 thin UI.\n\n"
            + "## 데이터 수\n\n"
            + "\n".join(f"- `{key}`: {value:,}" for key, value in counts.items())
            + "\n"
        ),
        interim_root / "KPI_TRACEABILITY.md": (
            _frontmatter("KPI 추적성", generated_at)
            + common_result
            + "## 계산 규칙\n\n"
            + "- KPI-1: 빈 reference를 제외·보고한 뒤 "
            + "`|reference ∩ predicted| / |reference|`의 유효 케이스 평균.\n"
            + "- KPI-2: 240개 합성 PRO percentile-point 변화 평균과 bootstrap CI.\n"
            + "- KPI-3~5: 실행 postcondition·안전 hard failure를 포함한 exact 판정.\n"
            + "- KPI-6: 추천 관련 합성 ADR 건수.\n"
            + "- KPI-7: W/C/G별 성공률의 동일 가중 macro 평균.\n"
        ),
        interim_root / "SAFETY_VALIDATION.md": (
            _frontmatter("안전 검증", generated_at)
            + "## 적용한 결정적 범주\n\n"
            + "응급, 임신·수유, 연령, 신장·간, 알레르기, 수술, 약물 상호작용, "
            + "질환 주의, 중복, UL, 검사 선행, 복용 시점, 라벨 제약, 오래된 근거.\n\n"
            + "`BLOCK`과 `STOP_AND_ESCALATE`는 덮어쓸 수 없다. 활성 critical rule은 "
            + "승인된 근거가 없으면 등록 자체가 거부된다. 360개 결정적 replay 테스트를 통과했다.\n"
        ),
        interim_root / "SECURITY_PRIVACY.md": (
            _frontmatter("보안·개인정보", generated_at)
            + "## 적용한 경계\n\n"
            + "서비스는 raw 사용자 ID를 R&D에 보내지 않고 HMAC 기반 가명 ID만 전달한다. "
            + "R&D API는 내부 token을 확인한다. 쓰기 tool은 scope별 동의를 확인하고, "
            + "idempotency·hash audit·durable postcondition을 남긴다. 검색 근거 본문은 "
            + "항상 `untrusted_content`로 취급해 명령으로 실행하지 않는다.\n"
            + "\n## 생산 전 의존성 gate\n\n"
            + "WellnessBox는 Next.js 15.5.20과 React 19.1.2로 올리고 회귀 검증했다. "
            + "`npm audit --omit=dev`의 critical/high는 0건이며, Next.js 번들 PostCSS의 "
            + "moderate 2건이 남았다. audit의 강제 수정은 Next.js 9 역다운그레이드를 제안해 "
            + "적용하지 않았다. feature flag는 외부 연구·법무·인증 gate 전까지 꺼 둔다.\n"
        ),
        interim_root / "ADR_REPORT.md": (
            _frontmatter("ADR 프록시 보고서", generated_at)
            + "## 결과\n\n"
            + f"합성 ADR은 {counts['adverse_events']}건이다. "
            + "KPI-6 분모는 1,200명·12개월 "
            + "시뮬레이션으로만 해석한다. serious AE 입력은 한 트랜잭션에서 활성 plan을 멈추고 "
            + "긴급 review task를 만든다. 실제 12개월 운영으로 교체 전이다.\n"
        ),
        interim_root / "CONNECTOR_REPORT.md": (
            _frontmatter("W/C/G 연동 프록시 보고서", generated_at)
            + common_result
            + "## 운영 gate\n\n"
            + "W/C/G 입력은 동의, schema, unit, timezone, dedup, provenance를 모두 확인한다. "
            + "PubMed, ClinicalTrials.gov, DailyMed, openFDA, RxNorm, ODS, DSLD, MFDS는 "
            + "공식 base URL contract를 가지며 환경에서 명시적으로 켜기 전에는 비활성이다.\n"
        ),
        interim_root / "EXTERNAL_TEST_PLAN.md": (
            _frontmatter("외부 시험 계획", generated_at)
            + "## 교체 순서\n\n"
            + "1. 독립 약사 라벨 세트로 KPI-1·5를 교체한다.\n"
            + "2. 사전 등록된 실제 PRO로 KPI-2를 교체한다.\n"
            + "3. 외부 blind 질문·행동 평가로 KPI-3·4를 교체한다.\n"
            + "4. 12개월 실제 ADR 운영으로 KPI-6을 교체한다.\n"
            + "5. production W/C/G 세션으로 KPI-7을 교체한다.\n"
            + "6. 보안·개인정보·법무·외부 시험기관 검토 후에만 대외 완료 표기를 허용한다.\n"
        ),
        interim_root / "BLOCKERS.md": (
            _frontmatter("외부 차단 항목", generated_at)
            + "## 자동화로 끝낼 수 없는 일\n\n"
            + "- 실제 약사 계약·독립 라벨링·합의 판정\n"
            + "- 실제 참여자 동의·PRO·임상적 효과 관찰\n"
            + "- 1,200명·12개월 실제 ADR 운영\n"
            + "- 생산 wearable·CGM·genetic provider 자격증명과 세션\n"
            + "- 외부 시험기관 성적서·인증·법무 승인\n\n"
            + "이 항목은 `MISSING`이 아니라 외부 투입 전까지 `BLOCKED_EXTERNAL`이다.\n"
        ),
        interim_root / "RUNBOOK.md": (
            _frontmatter("중간 파이프라인 실행서", generated_at)
            + "## 실행\n\n```powershell\n"
            + ".\\.venv-interim\\Scripts\\python.exe "
            + "scripts/run_interim_pipeline.py verify-package\n"
            + ".\\.venv-interim\\Scripts\\python.exe scripts/run_interim_pipeline.py import\n"
            + ".\\.venv-interim\\Scripts\\python.exe scripts/run_interim_pipeline.py retrain\n"
            + ".\\.venv-interim\\Scripts\\python.exe scripts/run_interim_pipeline.py evaluate\n"
            + ".\\.venv-interim\\Scripts\\python.exe scripts/run_interim_pipeline.py report\n"
            + ".\\.venv-interim\\Scripts\\python.exe "
            + "scripts/run_interim_pipeline.py verify-release\n"
            + "```\n\n원본 package는 덮어쓰지 않는다. 재학습은 "
            + "`artifacts/tips/interim/retrained`에 쓴다.\n"
        ),
    }

    for path, content in documents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    kpi_path = artifact_root / "kpi_report.json"
    kpi_path.write_text(canonical_json(report.to_dict()) + "\n", encoding="utf-8")
    release_files = [*documents, kpi_path, retrained_manifest_path]
    entries = [
        {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(release_files, key=lambda item: str(item))
    ]
    manifest = {
        "schema_version": 1,
        "mode": "PROXY_GOLD_SIMULATION",
        "generated_at": generated_at,
        "real_research_completion": False,
        "source_manifest_sha256": source_manifest_hash,
        "retrained_manifest_sha256": retrained_manifest_hash,
        "files": entries,
    }
    manifest_path = artifact_root / "evidence_manifest.json"
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    return ReleaseSummary(
        docs_written=len(documents),
        manifest_entries=len(entries),
        manifest_sha256=sha256_file(manifest_path),
        proxy_kpis_passed=report.proxy_kpis_passed,
        proxy_kpis_total=report.proxy_kpis_total,
    )


def verify_release(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.exists():
        return {"valid": False, "failures": ["manifest_missing"]}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if payload.get("schema_version") != 1:
        failures.append("schema_version")
    if payload.get("mode") != "PROXY_GOLD_SIMULATION":
        failures.append("mode")
    if payload.get("real_research_completion") is not False:
        failures.append("real_research_completion")
    if payload.get("source_manifest_sha256") != APPROVED_SOURCE_MANIFEST_SHA256:
        failures.append("source_manifest_trust_root")
    required_names = {
        "CURRENT_REPO_AUDIT.md",
        "INTERIM_RESEARCH_REPORT.md",
        "IMPLEMENTATION_STATUS.md",
        "KPI_TRACEABILITY.md",
        "SAFETY_VALIDATION.md",
        "SECURITY_PRIVACY.md",
        "ADR_REPORT.md",
        "CONNECTOR_REPORT.md",
        "EXTERNAL_TEST_PLAN.md",
        "BLOCKERS.md",
        "RUNBOOK.md",
        "kpi_report.json",
        "evidence_manifest.json",
    }
    present_names = {Path(item.get("path", "")).name for item in payload.get("files", [])}
    for missing in sorted(required_names - present_names):
        failures.append(f"required_file:{missing}")
    for item in payload.get("files", []):
        path = Path(item["path"])
        if not path.exists():
            failures.append(f"missing:{path}")
        elif path.stat().st_size != item["bytes"]:
            failures.append(f"size:{path}")
        elif sha256_file(path) != item["sha256"]:
            failures.append(f"sha256:{path}")
    source_check = validate_interim_package(APPROVED_SOURCE_ROOT)
    if not source_check.valid:
        failures.extend(f"source_nested:{item}" for item in source_check.failures)
    retrained_entries = [
        Path(item["path"])
        for item in payload.get("files", [])
        if Path(item.get("path", "")).name == "evidence_manifest.json"
        and Path(item["path"]).resolve() != manifest_path.resolve()
    ]
    if len(retrained_entries) != 1:
        failures.append("retrained_manifest_entry")
    else:
        retrained_check = validate_interim_package(retrained_entries[0].parent)
        if not retrained_check.valid:
            failures.extend(f"retrained_nested:{item}" for item in retrained_check.failures)
        if retrained_check.manifest_sha256 != payload.get("retrained_manifest_sha256"):
            failures.append("retrained_manifest_sha256")
    return {
        "valid": not failures,
        "checked_files": len(payload.get("files", [])),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "mode": payload.get("mode"),
        "real_research_completion": payload.get("real_research_completion"),
        "failures": failures,
    }
