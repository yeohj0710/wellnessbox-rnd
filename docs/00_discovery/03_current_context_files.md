# 현재 컨텍스트 파일 정리

작성 기준 시각: 2026-03-08

## 1. 최우선 기준 문서

### 1-1. 단일 기준

- `C:\dev\wellnessbox-rnd\docs\context\master_context.md`

역할

- 앞으로 연구개발의 1차 기준 문서
- TIPS 원문 p.1~27 재구성 + 단일 창업자/단일 컴퓨터 조건의 재설계 기준
- 이후 분류/이관/개발 판단의 최우선 소스

### 1-2. 원문 참조

- `C:\dev\wellnessbox-rnd\docs\context\original_plan.pdf`

역할

- 원문 PDF 보관본
- 참조용 원문
- 이번 단계에서는 1차 기준 문서가 아님

## 2. `wellnessbox`에서 바로 읽어야 할 컨텍스트 파일

### 2-1. 저장소 운영 전반

- `C:\dev\wellnessbox\AGENTS.md`
- `C:\dev\wellnessbox\AGENT_SESSION_PRIMER.md`
- `C:\dev\wellnessbox\AGENT_SKILLS_CATALOG.md`
- `C:\dev\wellnessbox\API_GUARD_MAP.md`
- `C:\dev\wellnessbox\docs\README.md`
- `C:\dev\wellnessbox\docs\DOCS_CATALOG.md`

용도

- 저장소 공통 규칙
- 세션 시작 전 체크 포인트
- 문서 탐색 위치
- API 가드/권한 구조 확인

### 2-2. 현재 서비스 흐름 파악용

- `C:\dev\wellnessbox\docs\survey_client_map.md`
- `C:\dev\wellnessbox\docs\my_data_client_map.md`
- `C:\dev\wellnessbox\docs\employee_report_client_map.md`
- `C:\dev\wellnessbox\docs\b2b_admin_report_client_map.md`
- `C:\dev\wellnessbox\docs\b2b_admin_employee_data_client_map.md`
- `C:\dev\wellnessbox\app\(features)\health-link\README.md`
- `C:\dev\wellnessbox\app\chat\hooks\README.md`
- `C:\dev\wellnessbox\docs\engineering\check-ai-maintenance-map.md`

용도

- 설문/결과/마이데이터/어드민 흐름 맵
- 채팅 훅 구조
- NHIS 연동 구조
- 빠른 진단 유지보수 맵

## 3. `wellnessbox` 내부의 기존 R&D 컨텍스트 파일

### 3-1. 기존 R&D 문서 계층

- `C:\dev\wellnessbox\docs\rnd\00_readme_how_to_use.md`
- `C:\dev\wellnessbox\docs\rnd\01_kpi_and_evaluation.md`
- `C:\dev\wellnessbox\docs\rnd\02_data_lake.md`
- `C:\dev\wellnessbox\docs\rnd\03_personal_safety_validation_engine.md`
- `C:\dev\wellnessbox\docs\rnd\04_efficacy_quantification_model.md`
- `C:\dev\wellnessbox\docs\rnd\05_optimization_engine.md`
- `C:\dev\wellnessbox\docs\rnd\06_closed_loop_ai.md`
- `C:\dev\wellnessbox\docs\rnd\07_biosensor_and_genetic_data_integration.md`
- `C:\dev\wellnessbox\docs\rnd\ai_training_pipeline.md`
- `C:\dev\wellnessbox\docs\rnd\RND_DOCS_INDEX.md`
- `C:\dev\wellnessbox\docs\rnd\PROGRESS.md`
- `C:\dev\wellnessbox\docs\rnd\SESSION_HANDOFF.md`

### 3-2. 구현 참고 문서 계층

- `C:\dev\wellnessbox\docs\rnd_impl\02_data_lake_impl_notes.md`
- `C:\dev\wellnessbox\docs\rnd_impl\03_personal_safety_validation_engine_impl_notes.md`
- `C:\dev\wellnessbox\docs\rnd_impl\04_efficacy_quantification_model_impl_notes.md`
- `C:\dev\wellnessbox\docs\rnd_impl\05_optimization_engine_impl_notes.md`
- `C:\dev\wellnessbox\docs\rnd_impl\06_closed_loop_ai_impl_notes.md`
- `C:\dev\wellnessbox\docs\rnd_impl\07_biosensor_genetic_integration_impl_notes.md`

주의

- 이 문서들은 이미 존재하는 R&D 흔적이다.
- 그러나 앞으로의 1차 기준은 여전히 `C:\dev\wellnessbox-rnd\docs\context\master_context.md`다.
- 따라서 다음 단계에서는 “기존 `docs/rnd`를 그대로 기준으로 유지할지”, “`master_context.md` 기준으로 재정렬할지”를 분류해야 한다.

## 4. 데이터/지식베이스 성격의 컨텍스트 파일

- `C:\dev\wellnessbox\data\b2b\README.md`
- `C:\dev\wellnessbox\data\b2b\B2B_SURVEY_SYSTEM_GUIDE.md`
- `C:\dev\wellnessbox\data\b2b\B2B_SURVEY_TEST_MATRIX.md`
- `C:\dev\wellnessbox\data\b2b\survey.common.json`
- `C:\dev\wellnessbox\data\b2b\survey.sections.json`
- `C:\dev\wellnessbox\data\b2b\scoring.rules.json`
- `C:\dev\wellnessbox\data\b2b\report.texts.json`
- `C:\dev\wellnessbox\data\mfds_supplement_functions.md`
- `C:\dev\wellnessbox\data\supplement_categories.md`
- `C:\dev\wellnessbox\data\supplement_overdose_and_drug_interactions_public.md`
- `C:\dev\wellnessbox\data\supplement_overdose_and_drug_interactions_expert.md`
- `C:\dev\wellnessbox\data\hyphen\nhis-mock.json`

용도

- 설문 질문/섹션 구조
- 웰니스 점수 규칙
- 리포트 문구
- 건강기능식품 기능/카테고리/안전성 지식
- NHIS 연동 테스트 데이터

## 5. 다음 단계에서 우선 읽기 순서 제안

### 5-1. R&D 기준 정렬이 목적일 때

1. `C:\dev\wellnessbox-rnd\docs\context\master_context.md`
2. `C:\dev\wellnessbox\docs\rnd\01_kpi_and_evaluation.md`
3. `C:\dev\wellnessbox\docs\rnd\RND_DOCS_INDEX.md`
4. `C:\dev\wellnessbox\docs\rnd\PROGRESS.md`
5. `C:\dev\wellnessbox\lib\rnd\module02~07`, `scripts\rnd\module02~07`

### 5-2. 현재 서비스 흐름 정렬이 목적일 때

1. `C:\dev\wellnessbox\docs\survey_client_map.md`
2. `C:\dev\wellnessbox\docs\employee_report_client_map.md`
3. `C:\dev\wellnessbox\docs\b2b_admin_report_client_map.md`
4. `C:\dev\wellnessbox\docs\b2b_admin_employee_data_client_map.md`
5. `C:\dev\wellnessbox\app\(features)\health-link\README.md`

## 6. 이번 단계 결론

- 기준 문서의 중심은 이제 `wellnessbox-rnd/docs/context`로 옮겨졌다.
- 하지만 실질적인 운영/개발 맥락은 여전히 `wellnessbox` 안에 흩어져 있다.
- 따라서 다음 단계는 “새 기준 문서 체계”와 “기존 서비스/R&D 문서 체계”를 연결하는 분류 작업이 된다.
