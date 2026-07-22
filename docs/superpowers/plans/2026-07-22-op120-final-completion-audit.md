# OP-120 Final Completion Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OP-001~120의 required stage, 외부 검증, 장문 보고서, canonical evidence, 전체 검증, 독립 최종 검토가 모두 입증될 때만 READY를 반환하는 fail-closed 최종 감사기를 만든다.

**Architecture:** manifest와 실제 repository evidence를 직접 감사하고, OP별 보고서 120개와 별도 최종 검증·독립 검토 영수증을 요구한다. 누락이나 낮은 단계는 구조화된 blocker로 기록한다. 현재 상태에서는 READY를 만들지 않고 실제 gap을 canonical BLOCKED evidence로 고정한다.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, JSON, GitHub Actions

---

### Task 1: 최종 감사 계약과 실패 테스트

**Files:**
- Create: `src/wellnessbox_rnd/governance/final_completion_audit.py`
- Create: `tests/test_final_completion_audit.py`

- [ ] **Step 1: 실패 테스트 작성** — 낮은 claimed stage, 미검증 EXTERNAL, 보고서 누락, validation receipt 누락, independent review receipt 누락을 각각 BLOCKED로 확인한다.
- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_final_completion_audit.py -q`가 모듈 부재로 실패하는지 확인한다.
- [ ] **Step 3: 최소 구현** — 실제 manifest·evidence audit·보고서·영수증을 읽는 엄격한 감사기를 구현한다.
- [ ] **Step 4: READY 양성 테스트** — 모든 stage와 외부 증거, 120개 보고서, 두 영수증을 갖춘 fixture만 READY인지 확인한다.

### Task 2: 현재 최종 감사 입력 정책과 canonical BLOCKED evidence

**Files:**
- Create: `data/original_plan/op120_final_audit_policy_v1.json`
- Create: `data/original_plan/op120_final_audit_cases_v1.json`
- Create: `scripts/run_final_completion_audit.py`
- Create: `data/original_plan/evidence/op120_final_completion_audit_v1.json`

- [ ] **Step 1: 정책 작성** — requirement 120건, 보고서 120개, Critical/Important 0, CI success와 source commit 일치를 요구한다.
- [ ] **Step 2: current-state audit** — 현재 stage gap, 외부 gap, 보고서 누락, 영수증 누락을 BLOCKED로 산출한다.
- [ ] **Step 3: canonical source identity** — audited source가 HEAD blob과 동일하지 않으면 runner를 거부한다.
- [ ] **Step 4: 8건 oracle** — expected blocker 집계와 observed 결과를 완전 일치 비교한다.

### Task 3: manifest·보고서·CI 연결

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Create: `docs/original_plan/research_reports/OP-120.md`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: requirement audit/completion tests
- Modify: `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`

- [ ] **Step 1: OP-120 IMPLEMENTED 등록** — 감사기 구현만 증거로 연결하고 OPERATED 완료는 주장하지 않는다.
- [ ] **Step 2: completion 수치 갱신** — `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`를 고정한다.
- [ ] **Step 3: CI fail-closed replay** — BLOCKED가 현재 기대 상태임을 검증하고 evidence diff를 차단한다.
- [ ] **Step 4: 독립 검토와 전체 검증** — Critical/Important 0, focused tests, Ruff, audit, completion check, GitHub Actions를 확인한다.
