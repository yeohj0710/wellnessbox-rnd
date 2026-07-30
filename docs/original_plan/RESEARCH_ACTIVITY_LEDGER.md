# 시간순 연구활동 원장

이 문서는 공식 연구노트가 아니다. 사람이 공식 연구노트를 작성할 때 날짜, 실험, 실패, 수정, 검증 결과를 다시 확인할 수 있도록 저장소 기록을 시간순으로 묶은 원자료다. 과거 활동은 모두 커밋이나 파일에서 사후 복원했으므로 제목에 `[사후 재구성]`을 붙였다. 2026-07-27 보고서 품질 작업만 실행 중 기록으로 분리했다.

## 이 원장을 읽을 때 주의할 점

- 날짜는 커밋의 작성 시각 또는 JSON에 저장된 시각을 그대로 따른다. 커밋은 `+09:00`, 운영 영수증은 `Z` 표기를 유지했다.
- `IMPLEMENTED`, `INTEGRATED`, `OPERATED`, `EXTERNAL`은 서로 다른 증거 단계다. 로컬 테스트나 모의실험을 실제 운영으로 바꾸어 쓰지 않았다.
- `PROXY_GOLD_SIMULATION`, 합성 데이터, frozen eval은 실제 임상·운영 결과가 아니다.
- 과거 문서에 `독립 검토`라는 결과가 있어도 사람 이름이나 식별 가능한 검토자 기록이 없으면 아래 항목의 검토자는 `미검토`다.
- Git 작성자는 커밋 메타데이터의 `yeohj0710`이다. 이 원장의 과거 서술은 Codex가 자동으로 재구성했으며, 사람이 사실 검토했다는 뜻이 아니다.
- `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`는 시간이 지나며 덮어써졌다. 현재 파일에 없는 과거 상태는 해당 시점 커밋의 파일 내용을 `git show`로 확인했다.

## 확인한 근거 범위

- Git: `6ee1efcb5a5bf11478ae65a42ee187c4b79c916f`(2026-03-08)부터 이 원장 작성 시점의 2026-07-27 보고서 재작성 커밋까지의 `git log`, 주요 커밋의 `git show`, 현재 `git diff`와 `git status`.
- 진행 기록: `PROGRESS.md`, `SESSION_HANDOFF.md`, `NEXT_STEPS.md`, `docs/archive/PROGRESS-archive-1.md`, `docs/archive/SESSION_HANDOFF-archive-1.md`.
- 계획: `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md`, `docs/plans/2026-07-15-original-plan-completion-program.md`, `docs/plans/2026-07-15-safety-input-contract.md`, `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`, `docs/plans/2026-07-23-ai-draft-pharmacist-approval-program.md`.
- 증거: `data/original_plan/evidence/`의 현재 56개 파일과 `data/original_plan/final_session/operational_receipts/`의 15개 영수증, 최종 세션 상태·승인·외부 검토 파일.
- CI: `PROGRESS.md`에 남은 실행 번호와 GitHub Actions `Original plan evidence` 실행 기록을 대조했다.

## 시간순 기록

### [사후 재구성] 2026-03-08 17:17~19:16 +09:00 — R&D 저장소와 결정론적 기준선 구성

- **작업 일자·근거:** 2026-03-08. 커밋 `6ee1efc`, `e5ef1ec`.
- **작업 목적:** TIPS 연구개발 계획을 저장소 기준 문서로 옮기고, 웹 서비스와 분리된 Python/FastAPI R&D 엔진의 최소 실행 기준을 세우는 것이었다.
- **확인한 원자료와 구현 파일:** `docs/context/master_context.md`, `docs/01_architecture/`, `docs/02_eval/`, `apps/inference_api/`, `src/wellnessbox_rnd/safety/`, `src/wellnessbox_rnd/efficacy/`, `src/wellnessbox_rnd/optimizer/`, `src/wellnessbox_rnd/orchestration/`, `data/frozen_eval/sample_cases.jsonl`, `tests/`.
- **수행한 변경 또는 실험:** 건강 입력 정규화, 규칙 기반 안전 판정, 효과 점수, 후보 정렬, 추천 API, KPI 계산기와 평가 실행기를 한 저장소에 추가했다. 초기 frozen eval은 5건의 합성 seed였다.
- **실패와 수정:** 실행 실패의 상세 로그는 남아 있지 않다. 다만 당시 `PROGRESS.md`는 5건 평가가 KPI 판정용으로 너무 작고, 실제 `/survey` 흐름과 운영 관측이 연결되지 않았다고 명시했다.
- **테스트·검증 결과:** 커밋에는 API·평가·추천 기준선 테스트가 함께 추가됐다. 이 시점의 정확한 통과 건수와 CI 실행 번호는 확인되지 않는다.
- **그 시점의 미확인 사항:** 실제 제품 자료, 실제 사용자 데이터, 운영 배포, 외부 검증, 대규모 frozen eval은 확인되지 않았다.
- **다음 작업:** 평가 데이터 작성 절차를 자동화하고 frozen eval을 늘리며, 안전 규칙과 입력 계약을 구체화하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-08 22:31 +09:00 — 평가 데이터 작성 절차 고정

- **작업 일자·근거:** 2026-03-08. 커밋 `e6d288e`; 당시 `PROGRESS.md`.
- **작업 목적:** frozen eval을 늘리기 전에 JSONL 케이스의 생성·정렬·검사를 사람이 수동으로 맞추던 문제를 줄이는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/evals/dataset_tools.py`, `scripts/manage_eval_dataset.py`, `data/frozen_eval/frozen_eval_v1.jsonl`, `docs/02_eval/`.
- **수행한 변경 또는 실험:** 케이스 골격 생성, 요약, 고유 `case_id`, 정렬, 요청 ID 일치, 설명 범위, 연동 성공 수 상한을 검사하는 명령을 추가했다.
- **실패와 수정:** 평가 데이터가 16건으로 여전히 작고 `sensor_genetic_integration_rate_pct`가 75%에 머물렀다. 이 한계는 점수 보정으로 숨기지 않고 다음 데이터 확장 과제로 남겼다.
- **테스트·검증 결과:** `python -m ruff check .` 통과, `python -m pytest` 26건 통과, 데이터 검증 issue 0건. 16건 평가에서 7개 지표는 변경 전후 동일했다.
- **그 시점의 미확인 사항:** 작성 도구가 큰 데이터셋에서도 같은 오류를 막는지, 합성 케이스가 실제 입력 분포를 대표하는지는 확인되지 않았다.
- **다음 작업:** 실패 유형을 문서화하고 frozen eval을 확대하며 효과 점수를 개선하는 순서를 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-08 23:49 +09:00 — 유전자 신호의 제한적 결정론 처리

- **작업 일자·근거:** 2026-03-08. 커밋 `cfcd9e3`; 해당 커밋의 `PROGRESS.md`.
- **작업 목적:** 100건을 넘긴 frozen eval에서 가장 약한 유전자 입력이 추천 순위에 아무 영향도 주지 않는 문제를 좁은 규칙으로 보완하는 것이었다.
- **확인한 원자료와 구현 파일:** `data/frozen_eval/frozen_eval_v1.jsonl`, `src/wellnessbox_rnd/domain/intake.py`, `src/wellnessbox_rnd/efficacy/service.py`, `tests/test_recommendation_baseline.py`.
- **수행한 변경 또는 실험:** micronutrient, cardiometabolic, recovery 세 범주의 유전자 신호를 만들고 vitamin D, omega-3, magnesium 후보에 제한된 보너스를 부여했다. frozen eval은 116건에서 118건으로 늘었다.
- **실패와 수정:** 전체 유전자 연동률은 7.14%로 계속 낮았다. 전체 센서·유전자 지표도 32.90%에서 32.48%로 내려갔으므로 개선으로 과장하지 않았다.
- **테스트·검증 결과:** Ruff와 pytest 34건, 데이터 검증·요약·평가 실행이 통과했다. 추천 커버리지와 안전 지표는 그대로였다.
- **그 시점의 미확인 사항:** 유전자 태그의 임상 타당성, 실제 검사기관 입력, 운영 동의·보관 절차는 확인되지 않았다.
- **다음 작업:** CGM 입력 처리와 유전자 정규화를 더 구체적인 데이터 계약으로 바꾸는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-09 15:53~18:08 +09:00 — 250건 평가와 보수적 입력 보류선 확인

- **작업 일자·근거:** 2026-03-09. 커밋 `609098f`, `f5a87ec`; `f5a87ec:PROGRESS.md`.
- **작업 목적:** `collect_more_input_high_priority_missing_info` 사례를 더 줄일 수 있는지 확인하되, 안전상 필요한 입력 요구를 억지로 낮추지 않는 것이었다.
- **확인한 원자료와 구현 파일:** `data/frozen_eval/frozen_eval_v1.jsonl` 250건, `docs/context/master_context.md`, 평가 요약과 추천 입력 판정 코드.
- **수행한 변경 또는 실험:** 남은 `eval-003`, `eval-081`, `eval-106`을 기준 문서와 다시 대조했다. 이 세 사례는 설문·증상 또는 CGM 근거가 부족해 추천을 보류하는 현재의 보수적 하한으로 판정했다.
- **실패와 수정:** 세 사례를 안전하게 더 줄일 근거를 찾지 못했다. 코드를 느슨하게 바꾸지 않고 변경 없음으로 종료했다.
- **테스트·검증 결과:** 평가 기록상 다음 행동 정확도는 99.1935%에서 99.2%로 정리됐고, 추천 커버리지 100%, 연간 이상사례 0은 유지됐다. 검증 명령은 남아 있으나 pytest 통과 건수는 기록되지 않았다.
- **그 시점의 미확인 사항:** 합성 입력에서 정한 보류선이 실제 사용자 입력 부족을 얼마나 잘 반영하는지는 확인되지 않았다.
- **다음 작업:** CGM 34/48, 70.83%의 약한 구간을 별도 분석하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-10 13:06 +09:00 — 합성 종단자료와 학습 효과 점수의 제한적 연결

- **작업 일자·근거:** 2026-03-10. 커밋 `d49aea5`; 해당 커밋의 `PROGRESS.md`.
- **작업 목적:** 효과 모델 산출물을 안전 판정 뒤의 낮은 위험·근소한 점수 차 후보에만 적용해, 학습 결과가 결정론적 안전 경계를 넘지 못하도록 시험하는 것이었다.
- **확인한 원자료와 구현 파일:** `data/synthetic/synthetic_longitudinal_v1.jsonl`, `artifacts/models/efficacy_model_v0.json`, `src/wellnessbox_rnd/models/efficacy_model_v0.py`, `src/wellnessbox_rnd/orchestration/recommendation_service.py`, `src/wellnessbox_rnd/simulation/closed_loop_v0.py`.
- **수행한 변경 또는 실험:** opt-in 재정렬을 추가했다. `syn-user-009`에서 기본 vitamin D 후보가 학습 점수 사용 시 vitamin C로 바뀌었지만, 전체 상태 전이는 계속 보수 경로에 머물렀다.
- **실패와 수정:** 학습 결과를 기본 실행에 승격하지 않았다. 모델 파일이 없거나 고위험이면 결정론 경로로 돌아가도록 회귀 사례를 넣었다.
- **테스트·검증 결과:** 시뮬레이션, Ruff, pytest, 데이터 검증, 256건 frozen eval을 실행했다. 7개 공식 지표는 변경되지 않았다. 정확한 pytest 통과 건수는 기록되지 않았다.
- **그 시점의 미확인 사항:** 합성 자료에서 얻은 재정렬이 실제 사용자 결과를 개선하는지, 후보 변경이 장기 효과로 이어지는지는 확인되지 않았다.
- **다음 작업:** 여러 사용자에 대한 재생 비교와 근거 지식 연결이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-10 16:28~19:27 +09:00 — 다중 사용자 재생, 지식 DB, 효과 모델 v1

- **작업 일자·근거:** 2026-03-10. 커밋 `ec5c515`, `ea83c80`; 각 커밋의 `PROGRESS.md`.
- **작업 목적:** 단일 사례가 아니라 여러 합성 사용자에서 학습 정책과 결정론 정책을 비교하고, 출처가 있는 지식과 9개 목표별 효과 예측을 재현 가능한 산출물로 만드는 것이었다.
- **확인한 원자료와 구현 파일:** `data/raw_references/`, `data/parsed_references/`, `data/knowledge/runtime_knowledge_db_v1.json`, `data/synthetic/synthetic_longitudinal_v2.jsonl`, `src/wellnessbox_rnd/simulation/closed_loop_v0.py`, `src/wellnessbox_rnd/models/effect_model_v1.py`, `src/wellnessbox_rnd/training/effect_model_v1.py`.
- **수행한 변경 또는 실험:** 48명, 모드당 84단계의 batch replay를 만들고 결정론 모드와 guarded learned-policy 모드를 비교했다. 이어 480개 종단 레코드를 train 270, validation 105, test 105로 나눠 70개 특징·9개 출력의 effect model v1을 학습했다.
- **실패와 수정:** 학습 정책은 생성 규칙에서 나온 라벨을 그대로 재현해 두 모드의 최종 상태 차이가 0이었다. 이 결과를 운영 개선으로 해석하지 않고, 학습 정책은 시뮬레이션 안에만 유지했다.
- **테스트·검증 결과:** effect model v1 test aggregate MAE 0.021604, RMSE 0.03396, R² 0.812435; zero baseline MAE 0.0572. Ruff, pytest, 학습 스크립트, batch simulation과 256건 frozen eval을 실행했고 공식 지표는 그대로였다.
- **그 시점의 미확인 사항:** 생성 라벨과 학습 라벨의 순환성, 실제 데이터 일반화, 운영 환경의 성능과 안전은 확인되지 않았다.
- **다음 작업:** cohort별 재생, 학습·결정론 결과 비교, 합성 자료 다양화가 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-12 01:46~18:31 +09:00 — 합성자료 확장과 구조화 복용량 채택

- **작업 일자·근거:** 2026-03-12. 커밋 `a1f5c19`, `10f034b`, `166e967`; `166e967:PROGRESS.md`.
- **작업 목적:** 더 풍부한 종단자료와 효과 모델 변형을 만들고, 안전 용량 계산에 필요한 보충제 복용량을 유지되는 합성자료 경로에 넣는 것이었다.
- **확인한 원자료와 구현 파일:** `data/synthetic/synthetic_longitudinal_v3.jsonl`, `synthetic_longitudinal_v4.jsonl`, `src/wellnessbox_rnd/synthetic/rich_longitudinal_v3.py`, `rich_longitudinal_v4.py`, `src/wellnessbox_rnd/models/effect_model_v2.py`, `effect_model_v3.py`, `data/rules/safety_rules.json`.
- **수행한 변경 또는 실험:** effect model v2/v3 학습·비교 경로를 추가하고, v3 합성 레코드의 식별 가능한 단일 성분에만 정형 복용량을 채웠다. 480건 중 270건에 구조화 복용량이 기록됐다.
- **실패와 수정:** 모호한 상품명이나 용량 템플릿이 없는 경우 값은 만들지 않고 기존 입력을 보존했다. 용량 상한 규칙이 5개 성분뿐이라는 범위 제한도 그대로 남겼다.
- **테스트·검증 결과:** 합성 v3 전용 테스트와 전체 Ruff·pytest, 합성자료 재생성, 데이터 검증, frozen eval을 실행했다. 7개 공식 지표는 변경되지 않았다.
- **그 시점의 미확인 사항:** 실제 복용 스케줄, 복합제, 단위 변환, 장기 복용 자료의 정확성은 확인되지 않았다.
- **다음 작업:** 다른 입력 경로에도 구조화 용량을 적용하고 CGM 약한 구간을 줄이는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-13 23:55 +09:00 — 효과 재정렬 on/off 재생 진단

- **작업 일자·근거:** 2026-03-13. 커밋 `0797021`; 해당 커밋의 `PROGRESS.md`.
- **작업 목적:** CGM과 임계값 근처 사례의 실패가 효과 모델 자체인지, 효과 점수를 정책에 덮어쓰는 단계인지 구분하는 것이었다.
- **확인한 원자료와 구현 파일:** `data/synthetic/synthetic_longitudinal_v4.jsonl` 480건, `src/wellnessbox_rnd/simulation/closed_loop_v0.py`, `scripts/compare_combined_override_modes.py`, `tests/test_closed_loop_simulation.py`.
- **수행한 변경 또는 실험:** 같은 자료·효과 모델·정책 모델로 effect override를 켠 모드와 끈 모드를 비교했다. override 적용 횟수는 325에서 0으로 줄었고 낮은 위험 구간에 `monitor_only` 2건이 생겼다.
- **실패와 수정:** CGM의 최종 행동 분포는 개선되지 않았고 `monitor_only`와 `re_optimize`가 계속 0이었다. 기본 동작은 override on으로 유지하고, 진단 플래그만 추가했다.
- **테스트·검증 결과:** 전용 시뮬레이션 테스트, 비교 스크립트, batch simulation, Ruff, frozen eval을 실행했다. 7개 공식 지표는 그대로였다.
- **그 시점의 미확인 사항:** CGM 실패가 점수 임계값, 자료 생성 방식, 시간 창 중 어디에서 주로 생기는지는 확정되지 않았다.
- **다음 작업:** CGM threshold-edge와 combined override prior를 더 좁게 분석하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-16 17:18~21:15 +09:00 — 우선순위 재정렬과 선택적 OpenAI 호출 실패 분류

- **작업 일자·근거:** 2026-03-16. 커밋 `52f7ac9`, `d7d58ff`, `f8f1cbe`; 각 시점의 `PROGRESS.md`.
- **작업 목적:** CGM, 합성자료, 효과 모델, PRO, 센서 파서, 상담 등 여러 부분 작업 중 다음 연구 순서를 다시 정하고, 선택적인 외부 언어모델 호출이 실패해도 핵심 추천 경로가 흔들리지 않는지 확인하는 것이었다.
- **확인한 원자료와 구현 파일:** `artifacts/reports/reprioritized_next_loops_v1.*`, `architecture_alignment_audit_v1.*`, `post_openai_live_rerun_catchup_v1.*`, `PENDING_USER_ACTIONS.md`, `NEXT_STEPS.md`, chat adapter 관련 파일.
- **수행한 변경 또는 실험:** 전체 구성요소를 done/partial/blocked로 분류했다. OpenAI live smoke는 API key를 읽고 호출을 시도했지만 `provider=deterministic_template_fallback`, `fallback_reason=openai_call_failed`로 끝났다.
- **실패와 수정:** 외부 호출의 구체적 실패 종류가 산출물에 남지 않았다. 추가 호출을 필수 작업으로 올리지 않고 optional 1건으로 낮추고, 결정론 fallback을 유지했다.
- **테스트·검증 결과:** JSON 산출물 파싱과 문서 대조를 수행했다. 이 루프는 실행 경로를 바꾸지 않아 frozen eval을 다시 돌리지 않았고 기존 256건 7개 지표를 기준으로 유지했다.
- **그 시점의 미확인 사항:** 외부 호출 실패의 세부 원인과 외부 모델 응답 품질은 확인되지 않았다.
- **다음 작업:** PRO 점수 계약, 버전 비교 도구, 센서·유전자 파서와 평가 slice 연결을 외부 상담 작업보다 먼저 하도록 정했다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-17 17:33 +09:00 — PRO 전후 변화 요약 계약 구현

- **작업 일자·근거:** 2026-03-17. 커밋 `d360637`; 해당 커밋의 `PROGRESS.md`.
- **작업 목적:** 환자보고결과(PRO)의 시작점과 추적 시점을 같은 자료 구조에서 읽고, z-score·percentile·변화폭을 한 계산 경로에서 만들도록 고정하는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/schemas/pro_events.py`, `src/wellnessbox_rnd/metrics/pro_scoring.py`, `scripts/build_pro_improvement_summary_contract.py`, `tests/test_pro_events.py`, `tests/test_pro_scoring.py`, `tests/test_pro_improvement_summary_contract.py`.
- **수행한 변경 또는 실험:** `PROImprovementSummaryV1`을 공통 baseline/follow-up event에서 직접 만들었다. 480건 모두 같은 정규화 구조로 변환됐고 invalid case는 0건이었다.
- **실패와 수정:** 이 작업은 효과 모델 학습 허가 문제를 해결하지 못했다. PRO 계산을 구현했지만 학습 산출물은 계속 replay-only로 남겼다.
- **테스트·검증 결과:** 계약 산출물 생성, 관련 pytest, Ruff, diff 검사를 수행했다. frozen eval 7개 기준 지표는 바뀌지 않았다.
- **그 시점의 미확인 사항:** 실제 설문 도구의 임상적 최소 중요 변화, 운영 추적률, 실제 개입 효과는 확인되지 않았다.
- **다음 작업:** 재생 잔차와 합성자료 순환성을 먼저 해소한 뒤 학습을 다시 검토하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-03-18 06:00 +09:00 — 학습 재실행 NO-GO

- **작업 일자·근거:** 2026-03-18. 커밋 `7e8c85a`; 해당 커밋의 `PROGRESS.md`.
- **작업 목적:** 승인된 잔차 유형만 대상으로 효과 모델을 한 번 다시 학습할 수 있는지 사전 조건을 확인하는 것이었다.
- **확인한 원자료와 구현 파일:** `training_readiness_gate_v2` 결과가 들어 있는 당시 보고서, `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`.
- **수행한 변경 또는 실험:** 학습 자체는 실행하지 않았다. gate가 `authorized_now=false`, `decision=no_go_keep_training_blocked`였기 때문에 차단 사유와 미생성 산출물 목록만 기록했다.
- **실패와 수정:** 재생 잔차, 합성자료 타당성, 다시 열린 CGM 문제를 좁히지 못해 안전한 학습 대상이 없었다. 무단 학습이나 후보 파일 생성을 하지 않은 것이 이 루프의 수정 조치였다.
- **테스트·검증 결과:** 문서 diff 검사만 수행했다. 새 모델·학습·평가 결과는 없다.
- **그 시점의 미확인 사항:** `large_drop` 잔차의 원인과 CGM 문제가 학습을 막는 정도는 확인되지 않았다.
- **다음 작업:** `replay_only_attribution_for_threshold_duration_sensitive_mid_margin_large_drop`을 먼저 수행하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-10 15:44~15:54 +09:00 — TIPS 중간 통합 모의실험

- **작업 일자·근거:** 2026-07-10. 커밋 `54141f2`, `9d4c9c9`, `eb50abe`; `docs/archive/PROGRESS-archive-1.md`의 `2026-07-10 TIPS interim end-to-end override`.
- **작업 목적:** 대량 합성자료부터 R&D API, 운영 화면까지 중간 통합 경로를 한 번 연결하고 7개 KPI 계산이 끝까지 흐르는지 확인하는 것이었다.
- **확인한 원자료와 구현 파일:** `artifacts/tips/interim/`, `apps/inference_api/routes/interim.py`, `src/wellnessbox_rnd/interim/`, 150,000개 합성 사례, PRO 240건, ADR 3건, W/C/G 180세션, 평가 10,000건.
- **수행한 변경 또는 실험:** manifest 검증, SQLite 계보, KPI 계산, 모델 등록, 14개 안전 범주, 12상태 Agent, 10개 도구, PRO·ADR·센서 경로와 얇은 인증 UI를 `PROXY_GOLD_SIMULATION` 모드로 연결했다.
- **실패와 수정:** 전체 legacy pytest는 누락된 ignored 보고서 산출물과 기존 CGM geometry 차이 때문에 실패했다. `npm audit --force`가 Next.js 9로 내리는 잘못된 제안을 해 적용하지 않았고, 직접 의존성만 올렸다.
- **테스트·검증 결과:** proxy KPI 7/7 통과, release manifest 13/13 유효, interim 테스트 29건, Ruff, 서비스 QA, TypeScript, ESLint, production build, 데스크톱·모바일 화면 검사가 통과했다. 사람 역할 API의 비인증 응답은 401, 브라우저 콘솔 오류는 0이었다.
- **그 시점의 미확인 사항:** `real research completion=false`였다. 실제 연구자료, 법적·인증 검토, production 배포와 실제 이용자 효과는 확인되지 않았다.
- **다음 작업:** 외부 연구·법무·인증 gate 전까지 기능 flag를 끄고, 재생 입력 복원과 실제 근거 체계를 정리하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-13 18:50 +09:00 — Cloud GPU 추론 시험대

- **작업 일자·근거:** 2026-07-13. 커밋 `7955dcd`; `docs/archive/PROGRESS-archive-1.md`의 `Cloud GPU bulk-inference testbed`.
- **작업 목적:** 보류 중인 `effect_model_v3`가 CPU와 CUDA에서 같은 값을 내는지, 같은 workload의 처리량 차이가 얼마인지 확인하는 것이었다.
- **확인한 원자료와 구현 파일:** `data/synthetic/synthetic_longitudinal_v4.jsonl` 480건·96명, `artifacts/gpu_testbed/cloud_kakao/`, PyTorch Linear 변환·benchmark·manifest 코드.
- **수행한 변경 또는 실험:** Kakao `gn1i.xlarge`, Tesla T4, PyTorch 2.6.0+cu124에서 CPU와 CUDA 추론을 실행하고 TorchScript·예측 표본·로그·해시 manifest를 남겼다.
- **실패와 수정:** 재시도를 포함해 GPU 사용 시간이 746.077초 걸렸다. 산술 불일치는 없었고, 시험 후 instance와 public IP를 0으로 정리했다.
- **테스트·검증 결과:** CPU 33,263,663.619 rows/s, CUDA 347,441,184.227 rows/s, 10.4451배. 최대 절대차 0.0. 비용은 부가세 제외 138.171818083333원으로 기록됐다.
- **그 시점의 미확인 사항:** 이 수치는 480건 합성자료 기반 대량 반복 추론 속도이며 실제 서비스 지연시간이나 임상 효과를 뜻하지 않는다.
- **다음 작업:** 모델을 승격하지 않고, 보류 후보의 재생 입력을 먼저 복구·검증하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-13 20:08~2026-07-14 16:14 +09:00 — 재생 입력 누락 확인과 복원 경로 마련

- **작업 일자·근거:** 2026-07-13~14. 커밋 `1f8a255`, `2e57620`; `docs/archive/PROGRESS-archive-1.md`의 두 항목.
- **작업 목적:** `large_drop` 3건을 다시 분석하기 전에 필요한 입력이 실제로 남아 있는지 확인하고, 없으면 신뢰한 archive에서만 복원하도록 만드는 것이었다.
- **확인한 원자료와 구현 파일:** `data/synthetic/synthetic_longitudinal_v4.jsonl`, prerequisite audit 산출물, archive restoration script, `SESSION_HANDOFF` 기록.
- **수행한 변경 또는 실험:** 필요한 8개 입력 가운데 존재 3개, 누락 5개를 확인했다. allowed root·SHA-256·atomic replace를 적용한 manifest 기반 복원 경로를 추가했다.
- **실패와 수정:** held candidate, family·subgroup·mid-margin 진단, prior small-drop attribution 5개가 없었다. 정확한 archive와 hash manifest가 없어 복원은 실행하지 않고 blocked report를 남겼다.
- **테스트·검증 결과:** 누락 파일의 크기·해시를 구조화된 사전 점검으로 기록했다. 학습, 후보 생성, runtime 승격, frozen eval 변경은 없었다.
- **그 시점의 미확인 사항:** 누락 파일이 어느 archive에 있는지와 신뢰할 hash manifest는 확인되지 않았다.
- **다음 작업:** 정확한 archive를 받기 전에는 재생 귀인을 만들지 않고, 현재 저장소의 원계획 구현·증거 프로그램으로 작업 중심을 옮겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-14 18:07~19:22 +09:00 — 기준 작업공간 고정

- **작업 일자·근거:** 2026-07-14. 커밋 `ca759c6`, `8a03cb7`; `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md`.
- **작업 목적:** TIPS R&D의 기준 저장소와 소스 패키지를 하나로 정하고, 평가 화면을 KPI·근거·상태가 드러나는 구조로 정리하는 것이었다.
- **확인한 원자료와 구현 파일:** `docs/context/master_context.md`, `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md`, 정리된 `src/wellnessbox_rnd/`와 평가 UI 관련 파일.
- **수행한 변경 또는 실험:** canonical workspace를 선언하고 TIPS 소스 패키지를 통합했다. 평가 화면 계획은 KPI 행렬, 문구·상호작용, 화면 밀도·검증 순으로 작성했다.
- **실패와 수정:** 이 두 커밋의 상세 실행 실패 기록은 확인되지 않는다.
- **테스트·검증 결과:** 별도 정량 검증 결과는 cited commit과 plan에 남아 있지 않다.
- **그 시점의 미확인 사항:** 실제 운영 UI에서의 사용성, 배포 환경, 외부 심사자의 이해도는 확인되지 않았다.
- **다음 작업:** 120개 원계획 요구사항을 증거 단계별 manifest와 감사 명령으로 바꾸는 프로그램이 이어졌다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-15 17:40~18:18 +09:00 — OP-001~010 증거 원장과 감사 체계

- **작업 일자·근거:** 2026-07-15. 커밋 `1ef1cf3`, `b96a92d`, `17da3a1`, `a449b60`, `c88313f`, `9fc718b`, `af70e95`; `docs/plans/2026-07-15-original-plan-completion-program.md`; archive 진행 기록.
- **작업 목적:** 원계획 OP-001~120을 누락 없이 세고, 구현·통합·운영·외부 단계의 근거를 같은 규칙으로 감사하는 것이었다.
- **확인한 원자료와 구현 파일:** `data/original_plan/requirements_manifest_v1.json`, `src/wellnessbox_rnd/schemas/original_plan_manifest.py`, `scripts/audit_original_plan_requirements.py`, completion report generator, `.github/workflows/original-plan-evidence.yml`.
- **수행한 변경 또는 실험:** 12개 그룹·120개 요구사항 manifest, 단계별 필수 증거 schema, 저장소 경계·파일 존재·Git 추적·원문 PDF 해시 검사를 추가했다. 이어 상태 보고서와 stale-output CI gate를 만들었다.
- **실패와 수정:** 첫 CI 경로가 Windows 절대 경로에 묶여 fresh checkout에서 깨졌다. checkout-relative 경로로 고친 뒤 GitHub Actions `29402915435`가 통과했다.
- **테스트·검증 결과:** manifest 단계는 focused 17건, evidence audit 13건, CLI 16건, completion report 25건과 Ruff가 통과했다. 당시 full suite는 452~470건 통과, 77건 실패였고 73건은 ignored 보고서 산출물 부재, 4건은 기존 CGM geometry였다.
- **그 시점의 미확인 사항:** manifest에 등록됐다고 실제 운영이 증명되는 것은 아니었다. 다수 요구사항은 계속 미청구 또는 낮은 단계였다.
- **다음 작업:** 구조화 건강 입력, 동의, Data Lake 계보를 차례로 구현하도록 계획했다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-15 18:38~21:08 +09:00 — 구조화 건강 입력·동의·프로필 연동

- **작업 일자·근거:** 2026-07-15. 커밋 `d57c880`, `405484d`, `93714c6`, `5d7ccf4`, `91dc57d`, `10ba2a7`, `6944728`; `docs/plans/2026-07-15-safety-input-contract.md`; archive 진행 기록.
- **작업 목적:** 프로필, 질환·증상, 약물·보충제 용량, 식이·생활·검사, 자료원별 동의를 추천 전 한 경로에서 검증하는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/schemas/recommendation.py`, `domain/intake.py`, `safety/service.py`, `data/samples/api_recommend_*`, WellnessBox profile adapter 계약과 서비스 QA.
- **수행한 변경 또는 실험:** OP-011~020 입력을 strict schema로 추가하고, 출처별 추천 사용과 보관 동의를 분리했다. 정규화된 snapshot과 SHA-256을 만들고, 알 수 없는 필드·단위·중복·모호한 입력은 422로 막았다. 실제 서비스 profile adapter도 같은 계약을 사용했다.
- **실패와 수정:** 모호한 상품명에 상품 전체 용량을 단일 성분 용량으로 배정하지 않았다. 2개의 문서화된 legacy 실패와 77개의 기존 full-suite 실패는 새 입력 계약과 분리했다.
- **테스트·검증 결과:** 단계별 focused 테스트 42, 58, 68, 81, 99건과 profile 연동 workflow 114건이 통과했다. 서비스 adapter·route 16 checks, preview 4 checks, TypeScript, lint, build가 통과했다. frozen eval 256건의 7개 지표 변화는 0이었다.
- **그 시점의 미확인 사항:** production R&D 프로세스와 실제 사용자 데이터, 영구 저장 운영은 확인되지 않았다.
- **다음 작업:** 프로필·동의 snapshot과 실행 이벤트를 SQLite Data Lake에 연결하고 지식 근거 계보를 저장하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-15 21:51~23:07 +09:00 — Data Lake와 지식·실행 계보

- **작업 일자·근거:** 2026-07-15. 커밋 `934f428`, `2ea5e40`, `194db51`, `121ca5d`, `12591d4`, `4c5bef8`; `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`; archive 진행 기록.
- **작업 목적:** 추천 한 번에 쓰인 프로필, 동의, 근거 claim·rule, 모델·코드·자료·설정 식별자를 나중에 다시 추적할 수 있게 저장하는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/interim/store.py`, Data Lake·knowledge lineage 모듈, `data/original_plan/evidence/op021_op022_*`, `op023_op024_*`, `op025_op026_*`.
- **수행한 변경 또는 실험:** immutable profile/consent snapshot, 공통 execution ID, source→passage→claim→rule→output 계보, behavior log와 research log 분리, 실행 identity를 SQLite에 추가했다.
- **실패와 수정:** 첫 지식 계보 CI `29419151688`은 ignored local retrained package가 fresh checkout에 없어 실패했다. 해당 테스트에 artifact-absence skip을 넣어 `29419358491`을 통과시켰다. 로컬 DB의 sticky quarantine은 checksum 일치 확인 후 내부 자료 3건만 review note와 함께 해제했다.
- **테스트·검증 결과:** Data Lake full suite 563 passed/78 failed, knowledge lineage focused 159 passed, log separation focused 176 passed. `Original plan evidence` 실행 `29422080597`도 통과했다. frozen eval 7개 지표 변화는 0이었다.
- **그 시점의 미확인 사항:** production DB, 실제 두 프로세스 왕복, 운영 재조회, 외부 자료의 license 검토는 확인되지 않았다.
- **다음 작업:** idempotency·정정·삭제 감사, session replay, 안전 엔진의 근거 연결을 이어가도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-16 09:37~20:12 +09:00 — 안전 규칙의 특수집단·상호작용·용량·최종 차단

- **작업 일자·근거:** 2026-07-16. 커밋 `9e1a171`, `c39f0f6`, `5a89377`, `8b5f6dd`, `e296537`, `e830c7d`, `20d9535`, `9272bc4`, `add5abf`; `PROGRESS.md`의 OP-033~040 항목.
- **작업 목적:** 임신·수유·신장·간 등 특수집단, 약물 상호작용, 중복 성분 합산 용량, 외부 고위험 검증 계약과 최종 안전 차단권을 하나의 보수적 규칙 체계로 만드는 것이었다.
- **확인한 원자료와 구현 파일:** `data/rules/safety_rules.json`, `data/knowledge/runtime_knowledge_db_v1.json`, `src/wellnessbox_rnd/safety/service.py`, `data/original_plan/evidence/op033_op034_*`, `op035_op036_*`, `op037_op038_*`, `op040_*`, OP-039 trust-root 계약.
- **수행한 변경 또는 실험:** 특수집단 상태를 차단 규칙과 연결하고, warfarin 상호작용 근거 ID, 제품 간 성분 합산, 단위 변환, 불완전 용량 fail-closed, 규칙 version·적용 시각을 추가했다. 서비스 오류·계약 오류도 추천 0건의 `service_fail_closed`로 끝나게 했다.
- **실패와 수정:** 부분 용량·범위·복합 문자열을 숫자로 지어내지 않고 `dose_evidence_incomplete`로 제외했다. CI의 source-history와 evidence URI portability 문제를 full checkout과 상대 경로로 고쳤다. OP-039은 실제 외부 자료가 없어 계속 미청구로 남겼다.
- **테스트·검증 결과:** OP-035/036 focused 53건, OP-037/038 240건, OP-039/040 19건과 당시 CI-equivalent 228~268건이 통과했다. full suite의 기존 77건 실패와 frozen eval 7개 지표는 변하지 않았다.
- **그 시점의 미확인 사항:** 외부 독립 고위험 라벨, production 배포, 실제 차단 로그는 확인되지 않았다.
- **다음 작업:** 성분 식별자와 목표별 근거 prior를 고정하고 추천 점수와 설명을 근거 ID에 연결하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-16 20:58~2026-07-17 01:34 +09:00 — 추천 점수·불확실성·재생·PRO 점수

- **작업 일자·근거:** 2026-07-16~17. 커밋 `6a1f874`, `26fe130`, `f7479d7`, `22aca5e`, `6860282`, `fd7e4a3`, `3bfdfed`; `PROGRESS.md`의 OP-041~052 항목.
- **작업 목적:** 성분 이름을 양쪽 저장소에서 같게 해석하고, 추천 후보가 왜 선택·제외됐는지, 학습 결과가 없거나 의심스러울 때 무엇으로 되돌아갔는지, PRO 점수가 어떤 버전으로 계산됐는지 기록하는 것이었다.
- **확인한 원자료와 구현 파일:** ingredient mapping 계약, `data/knowledge/goal_ingredient_priors_v1.json`, candidate scoring rules, `src/wellnessbox_rnd/knowledge/candidate_signals.py`, 추천 이유·불확실성 모듈, OP-041~052 smoke evidence.
- **수행한 변경 또는 실험:** 24개 ingredient-goal prior, 9개 목표, 증상·검사·생활·식이·웨어러블·CGM·유전자 점수 항목, 안전 전후 후보 pool, 구조화 이유, 학습 fallback, learned-vs-baseline replay, versioned PRO 점수와 percentile을 추가했다.
- **실패와 수정:** 근거가 약하거나 혼재된 자료를 임상 효과 확률로 올리지 않았다. learned 결과의 source identity와 replay 경계가 섞이는 문제를 분리하고, clean checkout hash와 self-contained fixture로 CI 재현성을 고쳤다.
- **테스트·검증 결과:** OP-041/042 focused 48건, OP-043/044 70건, OP-045/046 203건, OP-047/048·049/050·051/052의 관련 회귀와 canonical smoke가 통과했다. GitHub Actions `29496879246`, `29501666136`, `29504825809` 등이 성공했다. frozen eval 7개 지표 변화는 0이었다.
- **그 시점의 미확인 사항:** 실제 제품 재고·가격, 운영 추천 결과, PRO 도구의 외부 타당도는 확인되지 않았다.
- **다음 작업:** PRO 추적·개인/집단 불확실성·정정과 실제 서비스 plan 연결을 진행하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-18~2026-07-21 15:31 +09:00 — PRO 추적·정정·다음 행동 통합

- **작업 일자·근거:** 2026-07-18~21. 커밋 `334bd70`, `83997c1`, `5b9dedc`, `ea073ad`, `12c984b`, `c1bb470`, `8448cec`, `b068eda`, `9524290`; `PROGRESS.md`의 OP-053~060 항목.
- **작업 목적:** 시작점과 추적 설문을 plan에 묶고, 점수 개선·악화와 불확실성을 개인·집단 수준에서 계산하며, 입력 정정 후 결과와 다음 행동을 다시 계산하는 것이었다.
- **확인한 원자료와 구현 파일:** PRO scoring·followup·group effects·correction·actions 모듈, `src/wellnessbox_rnd/orchestration/pro_plan_service.py`, 서비스 PRO route·UI, OP-053~060 smoke evidence.
- **수행한 변경 또는 실험:** adherence 해석, 개인·집단 신뢰구간, correction lineage, idempotent enrollment, plan-linked follow-up, `maintain/reduce/stop/re_optimize`, `SYNTHETIC_OUTCOME_PROXY/REAL_WORLD_OUTCOME` 구분을 구현했다.
- **실패와 수정:** 추적 검증 우회, 정정 전 mutation, plan ID 불일치, 중복 enrollment와 충돌 retry가 발견돼 입력 검증과 idempotency를 보강했다. OP-058은 로컬 통합까지만 증명돼 required `OPERATED`보다 낮게 남겼다.
- **테스트·검증 결과:** OP-057/058 focused 127건, OP-059/060 54건, 서비스 PRO QA·TypeScript·lint·build와 canonical smoke가 통과했다. full suite는 827~837 passed/77 failed였고 기존 실패 집합과 frozen eval 지표는 그대로였다.
- **그 시점의 미확인 사항:** 실제 사용자 PRO, 인과 효과, production 브라우저·배포·운영은 확인되지 않았다.
- **다음 작업:** 실제 판매 상품 제약, 상품 조합, 재고 대체와 주문 전 승인 경계를 구현하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-21 15:43~18:45 +09:00 — 다중제약 상품 조합과 재고 대체

- **작업 일자·근거:** 2026-07-21. 커밋 `8ec6896`, `879dc78`, `5dbe3cf`, `16a079f`, `7d4da4b`, `f7b7e95`; `PROGRESS.md`의 OP-061~070 항목.
- **작업 목적:** 추천 성분을 실제 판매 후보에 연결하되 예산, 상품 수, 복용 부담, 중복 성분, 안전 제외, 재고를 동시에 적용하고 결과를 재현하는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/optimizer/constraints.py`, `product_combinations.py`, 서비스 product catalog adapter, OP-061~070 데이터셋과 smoke evidence.
- **수행한 변경 또는 실험:** 불완전 상품 사실을 제외하고, 최저가 재고 offer, 성분별 정수 base unit, 최대 4,096 search states·64 unique combinations, top-k와 미선택 이유를 만들었다. 재고가 사라지면 동일 입력·안전 규칙 아래 다시 계산하고 승인 전 cart candidate만 반환했다.
- **실패와 수정:** 서비스 자료 경계가 너무 넓거나 source hash가 dirty checkout을 가리키는 문제가 반복돼 실제 route 함수·HTTP client·clean commit에 증거를 다시 고정했다. search가 잘리면 top-k를 반환하지 않고 `SEARCH_TRUNCATED`로 표시했다.
- **테스트·검증 결과:** 단계별 focused 10~27건, workflow 472~505건, 서비스 QA·typecheck·lint·build, 14~18개 canonical smoke가 통과했다. 관련 GitHub Actions `29808907535`부터 `29819257210`까지 성공했다. full suite 기존 77건 실패와 frozen eval 변화 0은 유지됐다.
- **그 시점의 미확인 사항:** 실제 Prisma 조회, production 재고 최신성, 브라우저 cart mutation, 주문·결제는 확인되지 않았다.
- **다음 작업:** 상태기계와 follow-up worker를 연결하고, 주문 경계는 R&D가 직접 바꾸지 못하게 하는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-21 18:49~21:23 +09:00 — Closed-loop 상태기계와 후속 작업

- **작업 일자·근거:** 2026-07-21. 커밋 `ecb3540`, `403afec`, `aeacb64`, `c35abf4`, `bd24292`, `dd16871`; `PROGRESS.md`의 OP-071~080 항목.
- **작업 목적:** 추천→안전→계획→추적→재평가의 순서를 한 상태 계약으로 고정하고, 중복·오래된·동의 없는 작업이 실행되지 않게 하는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/interim/workflow_contract.py`, `jobs.py`, `plan_lifecycle.py`, `reviews.py`, `execution_events`, OP-071~080 evidence.
- **수행한 변경 또는 실험:** 허용 상태·이벤트·전이를 고정하고 SQLite claim으로 worker를 직렬화했다. follow-up reminder·reevaluation job, lease·retry·ack, serious adverse event 즉시 stop, pharmacist review, immutable lifecycle event를 추가했다.
- **실패와 수정:** stale·legacy job, 변경된 payload의 idempotency, plan 종료 뒤 남은 queue, timeout, 직접 SQLite mutation 우회가 발견돼 fail-closed와 schema migration을 보강했다.
- **테스트·검증 결과:** focused 45~63건, workflow 505~559건, canonical smoke 19~23개, Ruff가 통과했다. full suite는 902~948 passed/77 failed였고 새 실패군은 없었다.
- **그 시점의 미확인 사항:** deployed worker, CronJob, production plan 실행, 실제 약사 operation은 확인되지 않았다. OP-071~080은 당시 required `OPERATED`보다 낮은 `IMPLEMENTED`였다.
- **다음 작업:** 근거 검색 상담과 실제 서비스 session·adapter를 상태·추천 기록에 연결하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-21 22:09~2026-07-22 09:03 +09:00 — 근거 제한 상담과 서비스 왕복

- **작업 일자·근거:** 2026-07-21~22. 커밋 `de03de1`, `fd41644`, `67d65c3`, `b764bd0`, `036ac43`, `84d4f16`, `cc0830e`, `65ac9a8`; `PROGRESS.md`의 OP-081~090 항목.
- **작업 목적:** 승인한 자료 범위 안에서만 질문을 해석하고 답을 만들며, 응급 신호는 검색·외부 호출보다 먼저 차단하고, 서비스 chat session과 추천 execution을 같은 기록으로 묶는 것이었다.
- **확인한 원자료와 구현 파일:** 상담 corpus 19 sources·24 passages, question entity extractor, retriever, verifier policy, OpenAI adapter, `agent_runs`, `agent_steps`, service `/api/chat` adapter, OP-081~090 frozen QA와 smoke evidence.
- **수행한 변경 또는 실험:** source line span·license·유효기간을 보존한 passage, 질문 속 goal·ingredient·drug·urgent span, bounded retrieval, 서버 소유 답안 template·citation, emergency precedence, session/turn binding, provider 503 결정론 fallback을 구현했다.
- **실패와 수정:** 흔한 응급 표현 누락, 무관 passage 선택, working-directory 의존, cross-session message ID, semantic replay, 동시 insert, profile 과다 전송, 원자성·retry 시각 문제가 검토에서 발견돼 모두 수정했다. CI의 서비스 경로와 dirty source hash도 clean checkout 기준으로 고쳤다.
- **테스트·검증 결과:** OP-081/082 focused 51건, OP-083/084 39건, OP-085/086 50건, OP-087/088 workflow 613건, OP-089/090 workflow 618건과 28개 canonical smoke가 통과했다. 최종 CI `29878812400`이 성공했다.
- **그 시점의 미확인 사항:** live language-model 품질, public 배포, production 상담 트래픽, 외부 의료 검증은 확인되지 않았다. OP-087·088·090은 required 단계보다 낮게 남았다.
- **다음 작업:** 센서·CGM·유전자 파일 입력과 기기 follow-up을 같은 계보·동의·자료 구분 규칙에 연결하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-22 09:25~11:47 +09:00 — 센서·유전자 정규화와 기기 추적

- **작업 일자·근거:** 2026-07-22. 커밋 `4e9b199`, `411eb05`, `bf088c2`, `4becdd2`, `17d73cc`, `3a2afa0`, `0cf99b5`, `7958887`; `PROGRESS.md`의 OP-091~100 항목.
- **작업 목적:** Fitbit·Apple Health·CGM·유전자 입력을 단위·동의·출처가 남는 구조로 정규화하고, 파일별 부분 성공과 중복 방지, 추적 가치 계산을 구현하는 것이었다.
- **확인한 원자료와 구현 파일:** sensor/genetic parser, file ingestion, device assessment, OP-091~100 case files와 smoke evidence, `InterimStore` schema.
- **수행한 변경 또는 실험:** glucose 단위·alias 충돌 차단, 유전자 variant provenance, 원본 byte hash와 정규화 결과 hash, source별 storage consent, actual/simulation data class 분리, event dedup, wearable/CGM 점수 변화와 candidate 진입·이탈을 추가했다.
- **실패와 수정:** 비문자 provenance가 문자열로 강제 변환되는 문제, Windows 전용 경로, stale source identity, 동의·subject·origin 누락이 발견돼 strict rejection과 portable path, clean source hash로 고쳤다.
- **테스트·검증 결과:** focused 24~97건, workflow 642~681건, GitHub Actions `29881297071`부터 OP-099/100 실행까지 통과했다. full suite의 77~95건 기존 실패와 frozen eval 7개 지표는 변경되지 않았다.
- **그 시점의 미확인 사항:** 실제 기기 provider API, production 원시 시계열, backup·복구, production traffic은 확인되지 않았다. OP-096·098·099는 required `OPERATED`보다 낮았다.
- **다음 작업:** 배포 계약, 실행 결과 출처, profile·review 왕복, 관리자·주문·보안·복원력 계약을 순서대로 연결하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-22 11:55~18:50 +09:00 — 서비스 통합·보안·복원력·브라우저 증거

- **작업 일자·근거:** 2026-07-22. 커밋 `54a3d4f`, `9b81263`, `adda5fe`, `479bf7b`, `dc80098`, `b6d79eb`, `cbef456`, `ca01339`, `3a691de`, `d4c5e53`, `2f4b59b`; `PROGRESS.md`의 OP-101~119 항목.
- **작업 목적:** 배포 전 계약부터 실행 결과 출처, 프로필·약사 검토, 관리자 화면, 주문 경계, 인증·가명화·로그 마스킹, timeout·retry·circuit, test matrix와 브라우저 증거까지 실제 서비스 코드와 R&D 코드를 대조하는 것이었다.
- **확인한 원자료와 구현 파일:** deployment contract, environment/result-origin 계약, profile review roundtrip, admin/product adapter, order-plan context, security·resilience modules, health alias, browser evidence ledger, external dependency registry.
- **수행한 변경 또는 실험:** 로컬 두 프로세스와 공용 SQLite, 인증 route handler, 실제 HTTP adapter, Chromium의 `/survey`·`/pharm-login`·`/admin` 경로를 실행했다. 주문 생성과 결제는 서비스가 소유하고 R&D는 plan context만 받도록 경계를 고정했다.
- **실패와 수정:** runtime contract 우회, snapshot ID 충돌, 권한 override, 중복 payment ID, retry rollback, log masking, 미등록 OpenAPI operation, 건강 alias의 과도한 정상 판정이 검토에서 발견돼 수정됐다. 여러 CI에서 stale 서비스 checkout과 source identity도 최신 경로별 commit으로 다시 고정했다.
- **테스트·검증 결과:** OP-101/102 focused 127건과 CI 696 passed/2 skipped, OP-111/112 CI 699 passed/2 skipped, 서비스 Encoding Guard와 R&D `Original plan evidence` 실행들이 통과했다. OP-115/116 양쪽 Actions `29900597777`, `29901559427`도 성공했다.
- **그 시점의 미확인 사항:** public URL, provider volume·secret, production identity provider·log sink, 실제 Prisma·결제·주문, production traffic은 확인되지 않았다. OP-117/118 운영 원장은 OPERATED 0건을 기록했다.
- **다음 작업:** OP-120이 모든 단계·보고서·외부 검토·영수증을 한 번에 검사하도록 만들고, 미작성 연구보고서를 보강하도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-22 18:29~2026-07-23 10:21 +09:00 — 최종 감사기와 보고서 backfill, CI provenance 수정

- **작업 일자·근거:** 2026-07-22~23. 커밋 `ce3afe9`, `77accff`, `724dcdf`, `33db6a9`, `468f2ca`부터 `48b32fa`까지의 OP-001~030 보고서 커밋; `PROGRESS.md`의 OP-120·보고서 항목; GitHub Actions 실행 기록.
- **작업 목적:** 120개 요구사항의 단계, 보고서, canonical evidence, 외부 검토, 최종 영수증을 모두 통과해야만 READY가 되게 하고, 앞부분 OP 보고서를 근거가 있는 장문으로 보강하는 것이었다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/governance/final_completion_audit.py`, `scripts/run_final_completion_audit.py`, `data/original_plan/op120_final_completion_audit_cases_v1.json`, OP-001~030 보고서, current/provenance CI 로그.
- **수행한 변경 또는 실험:** fail-closed OP-120 감사기와 CI를 추가하고 OP-001~030 보고서를 두 편씩 보강했다. KPI-1에서 빈 reference 1,456건을 100점 분모로 세던 문제를 고쳐 유효 3,544건만 계산했다. boolean 용량이 1.0으로 바뀌는 결함도 회귀 테스트 뒤 차단했다.
- **실패와 수정:** 2026-07-22 CI `29917101552`는 device follow-up evidence에서 실패했다. 이후 `29924086385`부터 여러 실행이 audited commit self-reference, shallow service history, schema/source hash 불일치로 실패했고, clean checkout·경로별 source root·재현 가능한 audited input commit으로 고쳤다. 최종 관련 실행 `29931855632`, `29934330927`, `29935977162`, `29940069699`, `29968699617`, `29969740776`, `29970576517`이 성공했다.
- **테스트·검증 결과:** OP별 focused 테스트 31~109건, canonical audit 두 번의 byte-identical 결과, Ruff, manifest audit, completion check가 통과했다. 당시 OP-120은 보고서 수가 늘어도 stage 43건·OP-039·영수증 때문에 계속 `BLOCKED`였다.
- **그 시점의 미확인 사항:** 실제 운영 단계 43건, OP-039 약사 외부 검토, validation·independent-review 영수증이 확인되지 않았다.
- **다음 작업:** 나머지 OP 보고서, 운영 세션, 외부 검토와 최종 영수증을 한 세션으로 모으는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-23 10:25~12:11 +09:00 — 연속 단계 계획, 다음 행동 정책, 약사 승인 초안, 120편 보고서 확보

- **작업 일자·근거:** 2026-07-23. 커밋 `0a66cdf`, `f9b3675`, `3c941de`, `3e6b7db`, `3f67d0b`, `3aca1d1`, `d9f8800`, `7dceb34`, `ad95997`, `c9628df`; `docs/plans/2026-07-23-ai-draft-pharmacist-approval-program.md`.
- **작업 목적:** follow-up 다음 행동을 정책으로 완결하고, AI 초안을 약사가 승인하는 경계를 만들며, 미작성 연구보고서를 모두 물리 파일로 확보하는 것이었다.
- **확인한 원자료와 구현 파일:** `closed_loop_next_action_policy_v1.json`, scenarios, `src/wellnessbox_rnd/interim/next_action.py`, `ai_drafts.py`, OP-031~120 보고서, human signoff checklist.
- **수행한 변경 또는 실험:** 상태×이벤트 다음 행동 정책과 smoke, AI draft 생성·review API, 40편 OP-031~070 retroactive 보고서 생성 script, 보고서 title·evidence citation 교정을 추가했다. 120편 inventory가 갖춰졌다.
- **실패와 수정:** 자동 생성 보고서가 여러 편에서 같은 17줄 구조를 반복했고 짧은 문서가 많았다. 당시 감사는 파일 존재만 통과시켰고, 문서 품질 문제는 2026-07-27 별도 품질 작업으로 넘어갔다.
- **테스트·검증 결과:** `c9628df` 시점 OP-120은 보고서 120/120이지만 claimed 119/120, nonexternal stage gap 43, OP-039, 두 영수증 부재 때문에 `BLOCKED`였다.
- **그 시점의 미확인 사항:** 보고서가 사람 심사자가 읽을 품질인지, 실제 약사 review와 운영 세션이 끝났는지는 확인되지 않았다.
- **다음 작업:** 최종 세션 console을 만들고 사람의 남은 판정·운영·서명만 한곳에서 받도록 남겼다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 원장 재구성 Codex(자동); 검토자 `미검토`.

### [사후 재구성] 2026-07-23 12:23~16:35 +09:00 — 최종 세션 console과 첫 사람 기록

- **작업 일자·근거:** 2026-07-23. 커밋 `eeaba1d`, `3b3e300`, `47148d4`, `298e3b2`, `052908d`, `6633536`, `177f396`, `89dad25`, `739fa71`; final session JSON의 원시 timestamp.
- **작업 목적:** 정책 검토, AI 초안 검토, 보고서 문체 확인, 외부 고위험 검토, 운영 환경 확인, 영수증 생성을 한 console에서 순서대로 진행하는 것이었다.
- **확인한 원자료와 구현 파일:** `scripts/run_final_session_console.py`, `src/wellnessbox_rnd/governance/final_session_console.py`, `data/original_plan/evidence/final_session_console_rehearsal_v1.json`, `policy_rule_reviews_v1.json`, `report_tone_signoff_v1.json`, `human_signoff_completion_v1.json`.
- **수행한 변경 또는 실험:** isolated clone에서 READY rehearsal을 수행하고, next-only wizard·resume·trusted receipt·로컬 연구 session과 OP-039 검토 package 경로를 추가했다. 2026-07-23T04:13:35Z에 `웰니스박스` reviewer ID로 9개 정책이 승인됐고 04:13:39Z에 OP-081·028·117 문체가 승인됐다.
- **실패와 수정:** 같은 시점 H-003 기록은 생성·검토·대기 AI draft가 모두 0이었다. 즉 console 단계를 완료 표시했지만 실제 약사 초안 검토는 없었다. 이 불일치는 다음 날 정직성 보정에서 다시 열었다.
- **테스트·검증 결과:** console unit/smoke, isolated READY rehearsal과 audit 갱신을 수행했다. 다만 rehearsal과 자동 영수증은 실제 운영 증거가 아니었다.
- **그 시점의 미확인 사항:** `웰니스박스` reviewer ID의 실명, 실제 약사 초안 검토, 서로 다른 실제 프로필 5개, 독립 외부 검토는 확인되지 않았다.
- **다음 작업:** 로컬 운영 session에서 실제 경로와 DB 변화를 기록하고, 권혁찬 약사 검토를 사람이 직접 남기는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; 정책·문체 검토자 ID `웰니스박스`(실명 미기록); 그 밖의 사람 검토자 `미검토`.

### [사후 재구성] 2026-07-23 07:00Z~2026-07-24 01:39Z — 운영 영수증의 빈 실행과 첫 유효 경로

- **작업 일자·근거:** 운영 영수증 `local-20260723T070010589869Z.json`부터 `local-20260724T013510496112Z.json`; 커밋 `4efc12a`.
- **작업 목적:** 실제 로컬 연구 PC에서 사용자·추적·약사 검토·추천 경로를 실행하고, DB 변화와 포함 OP를 서명 영수증으로 남기는 것이었다.
- **확인한 원자료와 구현 파일:** `data/original_plan/final_session/operational_receipts/`의 앞 10개 영수증, `operational_wizard_v1.json`, `operational_environment_signoff_v1.json`, OP별 operational evidence.
- **수행한 변경 또는 실험:** 2026-07-23T07:00:10Z와 2026-07-24T00:04:14Z~01:02:14Z의 첫 7개 영수증은 `executed_paths=[]`, 모든 DB delta 0, covered OP 0으로 끝났다. 이어 01:02:45Z 영수증은 profile/followup/pharmacist_review와 profile 1·followup 1·draft 1을, 01:32:05Z 영수증은 recommendation run/item 각 1을 기록했다.
- **실패와 수정:** 빈 영수증 7개가 왜 아무 경로도 실행하지 못했는지는 파일에 원인이 없다. 이후 console이 남은 동작으로 바로 이동하고 실제 DB 변화가 있을 때만 coverage를 기록하도록 여러 차례 수정됐다.
- **테스트·검증 결과:** `4efc12a` 감사는 120 reports, stage gap 0, external gap 0, 두 receipt valid로 `READY`를 기록했다.
- **그 시점의 미확인 사항:** 첫 READY가 실제 사람 약사 검토와 5개 프로필을 충족했는지는 이 기록만으로 확인되지 않았다. 빈 receipt의 실패 원인도 미확인이다.
- **다음 작업:** 자동·오너 자기검토와 실제 사람 검토를 다시 구분하고, 미충족 gate를 복원하는 작업이 이어졌다.
- **작성자 / 검토자:** 영수증 issuer `웰니스박스`; Git 작성자 `yeohj0710`; 사람 검토자 `미검토`.

### [사후 재구성] 2026-07-24 14:08~16:50 +09:00 — 증거 정직성 보정, 약사 검토, 프로필 5개, READY 복귀

- **작업 일자·근거:** 커밋 `fa0dbd9`, `ab3d94d`, `0316dd8`, `b014abd`, `ed006ca`, `12548a0`, `fa46a10`, `99de571`, `30b956a`, `558d703`, `bebed41`; final session JSON과 07:33Z 운영 영수증.
- **작업 목적:** 오너 자기검토와 rehearsal을 사람·운영 증거로 잘못 승격한 상태를 되돌리고, 남은 실제 검토와 프로필 입력이 끝난 뒤에만 READY가 되도록 하는 것이었다.
- **확인한 원자료와 구현 파일:** `PROGRESS.md`의 `최종 감사 정직성 보정`, `OPERATIONAL_AND_PHARMACIST_SESSION_PROCEDURE.md`, `external_validation/op039_external_validation.json`, `human_signoff_completion_v1.json`, `operational_wizard_v1.json`, 마지막 5개 operational receipt, current OP-120 audit.
- **수행한 변경 또는 실험:** 오너 판정을 `self_review`로 내리고 OP-039 external에서 제외해 감사를 `external_validation_gaps:1`로 되돌렸다. 이후 권혁찬 약사가 10건을 판정한 결과를 등록했고, 실제 profile/followup/pharmacist_review 경로를 반복해 distinct profile 5개를 채웠다.
- **실패와 수정:** receipt issuer alias가 깨져 `0316dd8`에서 제거했다. 외부 검토 직전 `ed006ca`는 OP-039 한 건 때문에 `BLOCKED`였고, 검토 등록 뒤 `12548a0`에서 READY로 복귀했다. profile 수를 완료된 것만 세도록 `99de571`에서 고쳤다.
- **테스트·검증 결과:** current `op120_final_completion_audit_v1.json`은 requirement 120, claim 120, report 120, missing 0, stage gap 0, external gap 0, 두 receipt valid, `READY`를 기록한다. 마지막 운영 환경 기록은 cumulative session 7, distinct profile 5/5, 네 환경 check PASS다.
- **그 시점의 미확인 사항:** OP-039 reviewer는 권혁찬으로 기록됐지만 약사 면허 번호는 수집하지 않았고 자격 확인 방법은 `project_owner_attestation`이다. reviewer는 프로젝트 공동연구원이며 `independent_of_implementation_team=false`다. H-007 `operator_id`는 현재 파일에서 깨진 문자열이라 사람 이름을 확인할 수 없다. 최종 두 receipt도 issuer ID만 있고 사람 검토자 이름은 없다.
- **다음 작업:** 기계 감사 READY와 별개로 짧고 반복적인 연구보고서를 사람 심사자가 읽을 수 있게 다시 쓰고, 공식 연구노트용 시간순 원자료를 만드는 작업이 남았다.
- **작성자 / 검토자:** Git 작성자 `yeohj0710`; OP-039 검토자 `권혁찬`(파일에 기록된 범위만 인정); 그 밖의 사람 검토자 `미검토`.

### 2026-07-27 00:36~01:19 +09:00 — 보고서 품질과 제출 준비

- **작업 일자·근거:** 2026-07-27. 기준선 커밋 `932bfbb`; 샤드 커밋 `f984273`, `04eab8d`, `469b66a`, `f5e9d11`, `6ab7bcc`, `76972c0`, `bcaf974`, `3c291ca`; 전체 품질 기록 `2c3e053`; 비전문가 요약 `35b1857`; 원장·실행서 `c8c07d2`; 감사 형식 보완 `9eb295a`; `_REWRITE_TARGETS.md`, `_REWRITE_PROGRESS.md`, `_OPEN_QUESTIONS.md`.
- **작업 목적:** 120편이 존재해 감사는 통과하지만, 자동 생성된 짧은 보고서가 반복 문장과 얕은 실패 기록을 포함한 문제를 고치고, 사람이 읽고 최종 세션을 진행할 수 있는 A~D 산출물을 준비하는 것이다.
- **확인한 원자료와 구현 파일:** `STYLE_GUIDE.md`, `README.md`, 유효본 OP-087·090, 120편 실측 결과, requirements manifest, 각 OP evidence·구현·테스트, current audit와 보고서 진행 기록.
- **수행한 변경 또는 실험:** LF 정규화·strip 뒤 1,500자 미만인 53편을 선정했다. 경계 후보 OP-039·105·106·119도 실제 1,374·1,262·1,382·1,361자로 측정돼 포함했다. 8개 샤드가 각 OP의 manifest·구현·시험·증거를 직접 읽어 보고서를 다시 썼다. 이어 시간순 연구 활동 원장, 비전문가용 전체 요약, 사람용 최종 세션 실행서를 만들었다.
- **실패와 수정:** 변경 전 전체 pytest의 89건을 기준선으로 고정했다. 샤드 4는 DB schema 14/15 차이 2건, 샤드 5는 smoke 4개의 이전 source fingerprint를 확인해 한계로 남겼다. 세션 종료 래퍼는 비대화형 `timeout`에서 종료 코드 1을 냈고 호환되는 2초 대기로 좁게 고쳤다. 최종 감사 1회는 OP-050·074가 감사 의미 단어를 두 군만 충족해 보고서 118편으로 차단됐다. 두 보고서의 실제 요구를 명시해 같은 정적 판정식의 부적합을 0편으로 고쳤다.
- **테스트·검증 결과:** 53편은 모두 1,500자 이상, 3개 이상 절, 절당 80자 이상이고 manifest 증거 경로를 인용한다. 직접 통독 뒤 3편 이상 반복 문장·문단은 0개다. 세션 전 Python·운영 DB·서명 키·로컬 세 서버를 점검했다. 전체 pytest는 기준선과 같은 1,134 passed, 89 failed, warnings 5였다. Ruff는 이번 작업에서 손대지 않은 기존 Python 5개 파일의 32개 오류로 실패했다. 최종 감사 스크립트는 한 번만 실행하라는 조건 때문에 수정 뒤 재실행하지 않았다.
- **그 시점의 미확인 사항:** 저장된 OP-120 JSON은 이번 실패 실행 전에 있던 READY 결과다. OP-039의 구현팀 독립 외부 검토, H-005 중립 입력 화면, H-003 승인 초안에서 실제 학습·고정 평가로 이어지는 명령 계보는 확인되지 않았다. untracked 과거 operational receipt와 uploads는 이번 작업의 새 운영 증거가 아니다.
- **다음 작업:** 사람이 OP-039 독립성·자격과 중립 검토 화면을 확정하고, 승인 초안 학습 계보를 검증한 뒤 통제된 최종 세션을 수행한다. 그 다음 별도 bounded loop에서 OP-120 정본 감사와 기존 Ruff 문제를 처리한다.
- **작성자 / 검토자:** 작성자 Codex 작업팀(자동, 실시간 기록); 사람 검토자 `미검토`.

#### 동시 작업 결과

- **산출물 A, 보고서 8개 샤드:** 53편 완료. 각 샤드의 근거·변경·미확인 사항은 `_REWRITE_PROGRESS.md`와 각 보고서에 반영했다.
- **산출물 B, 시간순 연구 활동 원장:** 과거 `[사후 재구성]` 31건과 오늘 실시간 1건을 구분했다. 근거가 없는 사람 검토자는 모두 `미검토`로 남겼다.
- **산출물 C, 비전문가용 전체 요약:** 기능, 검증 범위, 합성자료 한계와 남은 사람 작업을 A4 3~5쪽 분량으로 작성했다.
- **산출물 D, 최종 세션 실행서:** H-007 5개 프로필 제안, H-002 9개 규칙, H-005 10개 미선택 사례, 실제 로그 기반 실패 대처를 담았다. 기존 H-005 HTML의 사전 선택값은 사용 금지로 명시했다.
- **최종 직렬 검토:** 전체 중복·문체·근거 검사, 세션 전 명령, 감사 1회, pytest 기준선 비교, Ruff와 세 인계 문서 갱신까지 실행했다.

### 2026-07-27 07:00~08:31 +09:00 — 보고서 근거 심화, 감사 정본화, 무영수증 사전 점검

- **작업 일자·근거:** 2026-07-27. 보고서 커밋 `c9389c9`, OP-060 보완 `821a5a5`, 감사 정본 `8ee93cc`, 사전 점검 `a53d977`; `EVIDENCE_VERIFICATION_REPORT.md`와 이번 실행 로그.
- **작업 목적:** 짧은 보고서 53편의 등록 근거를 파일 단위로 다시 대조하고, 현재 보고서 내용으로 OP-120 감사를 정본화하며, 실제 운영 영수증을 만들지 않는 사람 세션 사전 점검을 마련하는 것이었다.
- **확인한 원자료와 구현 파일:** 53편의 manifest 등록 파일 경로 492건, 고유 파일 189개, 각 보고서가 인용한 구현·시험·저장 JSON·커밋 이력, OP-120 감사기와 사례 8건, H-005 체크리스트·생성기·검증 코드·현재 HTML, H-003 승인 초안 소비·평가·비교 스크립트, 사람 세션 실행서.
- **수행한 변경 또는 실험:** 32편에서 단계, 버전, 해시, 함수명, 입력 조건 또는 저장 증거 해석을 바로잡았다. 53편 분량은 최소 2,830자, 중앙값 4,203자, 최대 7,242자로 벌어졌고 3편 이상 반복 문장·문단은 0개다. 무영수증 preflight는 운영 DB를 임시 복사하고 임시 상태 루트만 사용하며 실제 DB와 영수증 파일별 hash를 전후 비교하도록 구현했다.
- **실패와 수정:** 첫 OP-120 실행은 OP-060이 감사기의 요구 의미 단어군을 충족하지 못해 119/120 `BLOCKED`였다. OP-060에 실제 요구 문장을 넣고 커밋한 뒤 두 번째 실행이 120/120 `READY`를 반환했다. preflight는 서버와 화면은 정상이나 H-005 10건의 판정과 의견이 모두 선입력돼 `BLOCKED`를 반환했다. 이 차단은 실제 사람 입력을 시작하지 않기 위한 정상 동작이다.
- **테스트·검증 결과:** OP-120은 누락·단계·외부 격차 0, `goal_complete=true`다. preflight 전용 pytest와 Ruff가 통과했다. 실제 preflight에서 DB SHA-256 `856817703a430d42b7f7f4689b2b214caee6d727a2efcc59766d515f2a448e87`, 크기 761,856바이트가 전후 동일했다. 이 시점의 영수증 manifest 값 `107e7b952b32f851cdda2f191dc7fed7694c9ab77441e6f12c1804ece0474d49`는 이후 저장 경계를 넓히면서 계산식이 바뀌어 더 이상 재현되지 않는다. 현재 코드 기준 값은 아래 09:36~10:05 항목에 적었다. Ruff 32건은 모두 main 조상 커밋의 기존 오류다.
- **그 시점의 미확인 사항:** H-005는 면허 ID, 자격 확인 방법, 별도 서명과 H-003 검토자 대조를 신뢰할 수 있게 검증하지 않는다. H-003 승인 초안은 approved-only 데이터셋, 후보 학습, 후보 평가, 안전 회귀, 교체·유지와 rollback 기록으로 이어지지 않는다. DB의 서로 다른 프로필 5개만으로 다섯 건의 유효한 사람 세션을 입증할 수도 없다.
- **다음 작업:** H-005 중립성과 자격 gate, H-003 승인 초안 학습·평가 계보를 각각 구현한다. 실제 후속 자료와 동의 근거가 준비된 뒤에만 통제된 사람 세션을 시작한다.
- **작성자 / 검토자:** 작성자 Codex 작업팀(자동, 실시간 기록); 사람 검토자 `미검토`.

### 2026-07-27 09:36~10:05 +09:00 — 저장 경계 강화 반영, 재검증과 조건부 병합

- **작업 일자·근거:** 2026-07-27. 시작 HEAD `a53d977`, 병합 대상 `main`(`bebed41`); 이번 실행에서 직접 얻은 명령 출력.
- **작업 목적:** 독립 코드 검토가 지적한 세 가지(사전 점검의 저장 경계 부족, H-005 원본 HTML 정규식 검사, 447개 경로 판정 원장 누락)를 반영한 상태를 다시 검증하고, 인계 문서의 남은 옛 수치를 실측값으로 바꾼 뒤 병합 조건을 판정하는 것이었다.
- **확인한 원자료와 구현 파일:** `HANDOFF_report_quality_pass.md`, `AGENTS.md`, `STYLE_GUIDE.md`, `README.md`, `scripts/run_final_session_preflight.py`, `tests/test_final_session_preflight.py`, `scripts/verify_evidence_verification_ledger.py`, `data/original_plan/evidence/evidence_verification_ledger_v1.json`, `data/original_plan/requirements_manifest_v1.json`의 OP-039 항목, `docs/original_plan/FINAL_SESSION_RUNBOOK.md`의 JSON 예시 2개.
- **수행한 변경 또는 실험:** 문서만 고쳤다. 사전 점검 시험 수(4→10), 원본 HTML 대신 Chromium 렌더링 DOM 검사, DB 하나가 아닌 다섯 저장 경계, 영수증 manifest 값, 447행 근거 원장과 검증기, 실측 pytest 수치를 `PROGRESS.md`·`SESSION_HANDOFF.md`·`_OPEN_QUESTIONS.md`와 이 원장에 반영했다. 코드·데이터·모델·학습 산출물은 건드리지 않았다.
- **실패와 수정:** 실패한 검증은 없었다. 다만 이 환경의 pytest는 합계 줄을 파일로 내보내지 않아 처음에는 통과 수를 읽을 수 없었다. 진행 표시 문자와 `FAILED` 줄에서 직접 세고, 실행을 한 번 더 반복해 같은 값이 나오는지 확인하는 방식으로 해결했다. main worktree 삭제도 파일 잠금 때문에 한 번 실패해 재시도로 정리했다.
- **테스트·검증 결과:** OP-120 감사는 120/120, `READY`, `goal_complete=true`, 차단 목록 비어 있음이며 감사 JSON은 디스크에서 바뀌지 않았다(SHA-256 `7b155568dbe684b6448725b96d030e918c9f77fbeb0ce1f1008a4e14b9c168ca`). 근거 원장 검증기는 `READY`, 447/447, 누락·불일치 0을 반환했다. 사전 점검 전용 시험 10건과 전용 Ruff, `py_compile`, `git diff --check`가 통과했다. 실제 사전 점검은 종료 코드 2, `BLOCKED`, 차단 `H005_FORM_NOT_NEUTRAL` 하나였고 다섯 저장 경계가 모두 `true`였다. 영수증 15개의 manifest SHA-256은 현재 코드 기준 `a73f8e25c2b3fdefe956635ca7092a3f071d4ac10155b6b7e28a69dcc13bf39a`, 제어 파일은 `45d2d47b8b9c61f14c8dd74ddd0ee96160744ce4a752f87d193dab2de0a9e1bb`, 최종 세션 직접 파일 13개는 `fcd74398346da0200b8cf6bd1fc628255abea63a2750d90e75e8a44b37b76a35`로 전후 동일했다. 8000·8765·3001 포트에 잔류 listener는 없었다. 전체 pytest는 `1,144 passed / 89 failed / 5 warnings`, 실측 177초이며 2회 연속 같은 결과였다. `main` worktree에서 같은 72개 시험 파일을 돌린 96개 실패와 대조해 브랜치 신규 실패가 0건임을 함수 단위로 확인했다. 전체 Ruff는 기존 5개 파일의 32건 그대로다.
- **그 시점의 미확인 사항:** H-005의 선입력·자격 검증 결함과 H-003의 학습 계보 부재는 그대로 남아 있다. 이번 실행에서 해결하지 않았고 해결한 것처럼 기록하지도 않았다. `main` worktree에서만 나온 실패 7건은 미추적 실행 자료가 없어서 생긴 것으로 보이나 개별 원인까지는 조사하지 않았다.
- **다음 작업:** H-005 중립 화면과 자격 gate, H-003 approved-only 학습·후보 평가·안전 회귀 gate를 구현한다. 실제 후속 자료와 동의 근거가 준비된 뒤에만 통제된 사람 세션을 시작한다.
- **작성자 / 검토자:** 작성자 Claude Code 작업팀(자동, 실시간 기록); 사람 검토자 `미검토`.

### 2026-07-27 10:20~12:10 +09:00 — H-005 화면 중립화와 H-003 학습 계보 구현

- **작업 일자·근거:** 2026-07-27. 시작 HEAD `34c69f2`, 커밋 `4b5b9e9`·`318b501`·`3245cf3`; 이번 실행에서 직접 얻은 명령 출력.
- **작업 목적:** 오너 결정에 따라 사람 최종 세션을 막고 있던 두 결함을 실제로 고치는 것이었다. H-005 검토 화면의 선입력 제거와, 승인 초안에서 후보 모델 교체까지 이어지는 H-003 명령 체인 구현이다.
- **확인한 원자료와 구현 파일:** `scripts/build_op039_external_review_package.py`와 생성된 검토 화면 HTML, `src/wellnessbox_rnd/governance/final_session_console.py`의 `register_external_validation`과 `_run_draft_downstream_cycle`, `src/wellnessbox_rnd/interim/ai_drafts.py`와 `store.py`의 `ai_drafts` 스키마, `src/wellnessbox_rnd/evals/runner.py`, `scripts/run_eval.py`, `scripts/train_effect_model_v3.py`, `src/wellnessbox_rnd/evals/training_readiness_gate.py`, `src/wellnessbox_rnd/metrics/definitions.py`.
- **수행한 변경 또는 실험:** 검토 화면 생성기를 다시 써서 `타당` 선택, AI 의견 문장, `not_collected` 면허, `project_owner_attestation` 자격 확인, 이름 복사 서명, 하드코딩 `was_ai_draft_reviewer=false`를 모두 제거하고 빈 입력란으로 바꿨다. H-003 쪽에는 승인 전용 데이터셋 manifest 빌더와 검증기, 게이트로 잠긴 후보 학습 명령, 후보 artifact를 받는 고정 평가 인자, 안전 회귀 gate, 교체·유지 판정과 rollback 영수증을 새로 만들었다. 훈련과 고정 평가는 실행하지 않았다.
- **실패와 수정:** 전체 회귀에서 `test_audited_repository_commit_reproduces_recorded_file_blobs` 하나가 새로 실패했다. 원인은 감사 JSON이 기록한 509개 파일 중 `tests/test_final_session_console.py`를 고쳤는데 아직 커밋하지 않아 blob이 재현되지 않은 것이었다. 두 작업을 커밋한 뒤 감사를 다시 실행해 정본을 갱신하니 통과했다. 기존 시험 중 선입력을 필수로 고정하던 단언 10개도 중립성 단언으로 뒤집어야 했다.
- **테스트·검증 결과:** 실제 사전 점검이 처음으로 `READY`, 종료 코드 0, 차단 0건을 반환했다. H-005는 사례 10건에 선택 0건·선입력 의견 0건이었다. 다섯 저장 경계가 모두 `true`였고 영수증 15개의 manifest SHA-256 `a73f8e25c2b3fdefe956635ca7092a3f071d4ac10155b6b7e28a69dcc13bf39a`, 제어 파일 `45d2d47b8b9c61f14c8dd74ddd0ee96160744ce4a752f87d193dab2de0a9e1bb`가 전후 동일했다. 최종 세션 직접 파일 manifest는 중립화한 HTML과 zip 때문에 `9d7bdf3f7c6f9476dbfd7cf2f645545d90a070fc38fb900e5e5dd8400e0b433d`로 바뀌었다. OP-120 감사는 120/120 `READY`, `goal_complete=true`, 차단 0건이다. 실제 원장으로 만든 승인 전용 manifest는 `READY`, 포함 6건 전부 권혁찬 검토, 웰니스박스 계정 검토 1건 제외였고 DB SHA-256은 불변이었다. 전체 pytest는 `1,170 passed / 89 failed / 5 warnings`, 실측 167초이며 실패 89건은 `main` 기준선과 같은 집합이라 새 실패는 0건이다. 전체 Ruff는 32건에서 29건으로 줄었고 신규 오류는 0건이다.
- **그 시점의 미확인 사항:** 백엔드 자격 검증은 손대지 않았다. 오너 차단은 여전히 이름 두 개 문자열 비교이고, 동일 AI 초안 검토자 표시는 경고에 그치며 H-003 원장과 대조되지 않는다. 면허 ID의 형식과 실재도 확인하지 않고, 신뢰 원장 대체 경로는 자격 없이 H-005 완료 경로에 들어갈 수 있다. 학습 게이트가 NO-GO라 후보 모델을 만들지 못했으므로 후보 평가와 교체 판정은 실제 값으로 검증하지 못했다.
- **다음 작업:** H-005 백엔드 자격 검증 강화, 학습 게이트를 여는 CGM 기하 blocker 해소, 실제 후속 자료로 통제된 사람 최종 세션 수행이다.
- **작성자 / 검토자:** 작성자 Claude Code 작업팀(자동, 실시간 기록); 사람 검토자 `미검토`.

### 2026-07-27 13:40~15:10 +09:00 — H-005 백엔드 자격 검증과 외부 평가 위치 정정

- **작업 일자·근거:** 2026-07-27. 시작 HEAD `ff1f211`, 커밋 `b8073aa`; 이번 실행에서 직접 얻은 명령 출력과 오너 지적.
- **작업 목적:** 화면만 중립화하고 남겨 둔 백엔드 자격 검증을 채우고, 외부 기관 평가의 위치를 바로잡는 것이었다. 오너가 "외부 기관 평가는 연구가 끝난 뒤에 하는 것이지 지금 섭외할 일이 아니다"라고 지적했다.
- **확인한 원자료와 구현 파일:** `src/wellnessbox_rnd/governance/final_session_console.py::register_external_validation`, `data/original_plan/contracts/op039_external_coverage_trust_roots_v1.json`과 `op039_external_attestation_trust_roots_v1.json`, 실제 초안 원장 `etc/local_research_runtime/interim.sqlite3`의 `ai_drafts.reviewer_id`, `tests/test_final_session_console.py`의 기존 fixture.
- **수행한 변경 또는 실험:** 검토자 자격 검증 모듈과 신원 원장을 새로 만들고 콘솔에 연결했다. 이름 정규화 뒤 별칭 대조, 면허 번호 자리표시자·자릿수 검사, 자격 확인 방법 검사, H-003 초안 원장 교차확인을 넣었다. 외부 기관 평가 경로가 완료를 기록할 때의 `review_character`도 프로젝트 소속 약사 검토와 구분했다.
- **실패와 수정:** 기존 콘솔 시험이 새 규칙에 걸려 실패했다. fixture의 `license-actual-value`는 숫자가 없고 `license_document_checked`는 검증 대상이 아니었기 때문이다. 실제 형태의 값으로 바꿔 통과시켰다. 인계 문서를 스크립트로 고치는 과정에서 Windows 경로의 ``가 폼피드로 해석돼 경로가 깨졌고, 저장소 상대 경로로 바꿔 고쳤다. 전체 회귀에서 감사 blob 시험이 또 실패했으나 원인은 지난번과 같이 미커밋 상태였고 커밋 뒤 감사 재실행으로 해소했다.
- **테스트·검증 결과:** `pytest tests/test_reviewer_credentials.py` 28건, `pytest tests/test_final_session_console.py` 27건이 통과했다. 실제 원장 대조에서 H-003 검토자는 권혁찬과 웰니스박스였고, 권혁찬이 `was_ai_draft_reviewer=false`로 신고하면 차단되고 true면 경고로 통과했다. 두 신뢰 원장은 모두 0건이라 외부 기관 평가 경로가 현재 발동하지 않음을 확인했다. 전체 pytest는 `1,197 passed / 89 failed`이며 새 실패는 0건이다. 전체 Ruff는 29건 그대로다.
- **그 시점의 미확인 사항:** 시스템은 면허 번호의 형식만 본다. 실제 발급 여부를 조회하지 않으므로 값의 진위는 사람이 현장에서 확인해야 한다. 학습 게이트는 여전히 NO-GO다. 서로 다른 실제 프로필 5건의 전체 경로도 아직 실행되지 않았다.
- **기록 정정:** 신뢰 원장 경로를 "약사 자격 없이 H-005를 완료할 수 있는 우회 경로"로 적었던 이전 항목은 잘못이다. 그 경로는 연구 종료 후 외부 기관이 수행하는 평가를 받는 별개 입력이며, 프로젝트 소속 약사 검토를 대신하는 우회로가 아니다. 외부 기관 섭외를 지금의 과제로 적은 부분도 함께 바로잡았다.
- **다음 작업:** 학습 게이트를 여는 CGM 기하 blocker 해소, 실제 프로필 5건의 전체 경로 실행, 통제된 사람 최종 세션 수행이다.
- **작성자 / 검토자:** 작성자 Claude Code 작업팀(자동, 실시간 기록); 사람 검토자 `미검토`.

## 공식 연구노트 작성 전에 사람이 확인할 미확인 사항

1. 2026-03-08 초기 scaffold와 일부 3월 루프는 정확한 pytest 통과 건수·실행 로그가 현재 문서에 남아 있지 않다.
2. 3월 합성자료·학습모델 결과는 실제 사용자·임상 자료가 아니다. 공식 연구노트에서 실제 효과나 실증으로 쓰면 안 된다.
3. 2026-07-23~24 첫 7개 운영 영수증은 실행 경로와 DB 변화가 모두 0이다. 왜 비었는지 원인 기록이 없다.
4. 2026-07-23 초기 H-003 완료 기록은 AI draft generated/reviewed/pending가 모두 0이었다. 다음 날 정직성 보정 전 상태를 최종 사람 검토로 인용하면 안 된다.
5. OP-039 권혁찬 검토는 이름·소속·10건 판정은 있으나 면허 번호는 수집하지 않았고 프로젝트 공동연구원이며 구현팀 독립 검토자가 아니다.
6. H-007 운영자 ID는 현재 JSON에서 깨져 있어 사람 이름을 확인할 수 없다.
7. `final_validation_receipt_v1.json`과 `independent_final_review_receipt_v1.json`에는 issuer ID만 있고 사람 검토자 실명이 없다. 이 원장에서는 사람 검토로 간주하지 않았다.
8. 2026-07-27 현재 파일로 다시 실행한 최종 감사는 120/120 `READY`이고 사전 점검도 `READY`다. 다만 이 두 신호는 H-005 백엔드 자격 검증 결함과 DB 5/5의 사람 세션 진위를 해결하지 않는다. H-005 화면 선입력과 H-003 명령 체인은 같은 날 고쳤으나 학습 게이트가 NO-GO라 후보 모델은 아직 없다. 전체 pytest의 기존 실패 89개와 Ruff 29개도 별도 기술 부채로 남아 있다.

Reference basis: Toss 공식 블로그의 사례 중심 금융 설명 글 3편. 질문형 도입, 구체적 수치와 결과의 직접 연결, 확인된 사실과 한계의 분리를 문장 기준으로 삼았다.
