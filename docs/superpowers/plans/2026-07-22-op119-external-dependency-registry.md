# OP-119 External Dependency Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 외부 요구사항마다 책임 역할, 필수 입력, 교체 계약, 현재 차단 사유를 기계 검증 가능한 원장과 canonical evidence로 고정한다.

**Architecture:** manifest의 `required_stage=EXTERNAL` 항목을 authoritative 목록으로 사용한다. 엄격한 Pydantic 스키마가 원장을 읽고, 검증기가 manifest·신뢰 루트·참조 파일과 1:1 대응 및 차단 상태를 확인한다. 승인되지 않은 외부 입력은 만들지 않고 현재 빈 신뢰 루트를 `BLOCKED`로 기록한다.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, JSON, GitHub Actions

---

### Task 1: 엄격한 외부 의존성 원장 계약

**Files:**
- Create: `src/wellnessbox_rnd/governance/external_dependency_registry.py`
- Create: `tests/test_external_dependency_registry.py`

- [ ] **Step 1: 실패 테스트 작성** — 외부 requirement 누락, 빈 책임 역할, 참조 파일 누락, manifest 교체 계약 불일치, 빈 신뢰 루트와 READY 상태를 각각 거부하는 테스트를 작성한다.
- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_external_dependency_registry.py -q`를 실행해 import 실패를 확인한다.
- [ ] **Step 3: 최소 구현** — 엄격한 Pydantic 모델과 `audit_external_dependency_registry_v1`을 구현한다.
- [ ] **Step 4: 통과 확인** — 같은 pytest 명령에서 모든 사례가 통과하는지 확인한다.

### Task 2: OP-039 외부 의존성 원장

**Files:**
- Create: `data/original_plan/op119_external_dependency_registry_v1.json`
- Test: `tests/test_external_dependency_registry.py`

- [ ] **Step 1: 원장 작성** — OP-039 책임 역할, 외부 공급 역할, 데이터셋·증명서·검증 영수증·동결 coverage protocol 입력, 신뢰 루트 2개, 차단 사유를 기록한다.
- [ ] **Step 2: 원장 검증** — manifest의 EXTERNAL 집합 `{OP-039}`와 replacement contract 집합이 정확히 일치하는지 확인한다.

### Task 3: canonical evidence와 CI gate

**Files:**
- Create: `scripts/run_external_dependency_registry_smoke.py`
- Create: `data/original_plan/evidence/op119_external_dependency_registry_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`

- [ ] **Step 1: runner 작성** — 원장 감사 결과, 차단 원인, 파일 hash, source commit을 deterministic JSON으로 생성한다.
- [ ] **Step 2: 재생 검증** — runner 실행 뒤 `git diff --exit-code`로 evidence 재현성을 확인한다.
- [ ] **Step 3: CI 연결** — workflow가 runner와 evidence diff를 실행하도록 추가한다.

### Task 4: manifest, 보고서, handoff

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Create: `docs/original_plan/research_reports/OP-119.md`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: OP-119를 IMPLEMENTED로 연결** — 원장·검증기·canonical evidence만 evidence로 등록한다.
- [ ] **Step 2: 수치 갱신** — 예상 상태 `76 COMPLETE / 42 PARTIAL / 1 PENDING / 1 EXTERNAL / 0 CONTRADICTED`를 테스트한다.
- [ ] **Step 3: 경계 기록** — 외부 데이터·승인·검증 영수증이 없어 OP-039는 계속 EXTERNAL이며 운영 완료를 주장하지 않는다고 기록한다.
- [ ] **Step 4: 전체 검증** — focused pytest, Ruff, audit, completion check, 독립 검토, GitHub Actions를 통과시킨다.
