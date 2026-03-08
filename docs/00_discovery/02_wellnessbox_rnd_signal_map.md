# wellnessbox 내 R&D 신호 맵

작성 기준 시각: 2026-03-08  
분석 대상: `C:\dev\wellnessbox`

## 1. 총평

`C:\dev\wellnessbox` 안에는 이미 R&D 문서, 모듈 코드, 실행 스크립트, 평가 파이프라인, 도메인 데이터가 상당량 존재한다.  
즉, 이번 프로젝트는 “R&D를 처음 만드는 상태”가 아니라 “기존 서비스 저장소 안에 이미 진행 중인 R&D 축이 있다”는 전제에서 출발해야 한다.

다만 이번 단계에서는 어떤 것을 실제 이관 대상으로 확정하지 않고, 현황과 후보만 정리한다.

## 2. 가장 강한 R&D 신호

### 2-1. 공식 R&D 문서 계층

핵심 경로

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

관찰 포인트

- 문서 계층이 02~07 모듈 기준으로 이미 분리되어 있다.
- `RND_DOCS_INDEX.md`는 `docs/rnd`, `docs/rnd_impl`, `lib/rnd`, `scripts/rnd`, `tmp/rnd`를 하나의 체계로 묶는다.
- `PROGRESS.md`는 모듈별 scaffold/mvp/evaluation 및 `rnd:train:all` 진행 이력을 상세히 남기고 있다.

### 2-2. 구현 코드 계층

핵심 경로

- `C:\dev\wellnessbox\lib\rnd\ai-training`
- `C:\dev\wellnessbox\lib\rnd\module02-data-lake`
- `C:\dev\wellnessbox\lib\rnd\module03-personal-safety`
- `C:\dev\wellnessbox\lib\rnd\module04-efficacy-quantification`
- `C:\dev\wellnessbox\lib\rnd\module05-optimization`
- `C:\dev\wellnessbox\lib\rnd\module06-closed-loop-ai`
- `C:\dev\wellnessbox\lib\rnd\module07-biosensor-genetic-integration`

관찰 포인트

- 단순 stub가 아니라 `contracts`, `guards`, `scaffold`, `mvp-engine`, `evaluation` 구조가 실제 파일로 존재한다.
- 모듈 명칭이 `master_context.md`의 핵심 축과 상당 부분 대응한다.

### 2-3. 실행 스크립트 계층

핵심 경로

- `C:\dev\wellnessbox\scripts\rnd\train-all-ai.ts`
- `C:\dev\wellnessbox\scripts\rnd\train-all-ai.reporting.ts`
- `C:\dev\wellnessbox\scripts\rnd\module02`
- `C:\dev\wellnessbox\scripts\rnd\module03`
- `C:\dev\wellnessbox\scripts\rnd\module04`
- `C:\dev\wellnessbox\scripts\rnd\module05`
- `C:\dev\wellnessbox\scripts\rnd\module06`
- `C:\dev\wellnessbox\scripts\rnd\module07`

`C:\dev\wellnessbox\package.json`에 노출된 주요 스크립트

- `rnd:module02:scaffold`, `rnd:module02:mvp`, `rnd:module02:evaluation`
- `rnd:module03:scaffold`, `rnd:module03:mvp`, `rnd:module03:evaluation`
- `rnd:module03:evaluation:adverse:*` 계열
- `rnd:module04:scaffold`, `rnd:module04:mvp`, `rnd:module04:evaluation`
- `rnd:module05:scaffold`, `rnd:module05:mvp`, `rnd:module05:evaluation`
- `rnd:module06:scaffold`, `rnd:module06:mvp`, `rnd:module06:evaluation`
- `rnd:module07:scaffold`, `rnd:module07:mvp`, `rnd:module07:evaluation`
- `rnd:train:all`

관찰 포인트

- 서비스 저장소 안에 “모듈별 실행 가능 R&D 파이프라인”이 이미 심어져 있다.
- 특히 module03은 KPI #6, 소스 기반 adverse event 집계, scheduler gate까지 확장되어 있다.

## 3. 서비스 코드 안에 숨어 있는 R&D 관련 신호

### 3-1. B2B 설문 + 웰니스 계산 엔진

핵심 경로

- `C:\dev\wellnessbox\app\survey\survey-page-client.tsx`
- `C:\dev\wellnessbox\lib\b2b\public-survey.ts`
- `C:\dev\wellnessbox\lib\wellness\analysis.ts`
- `C:\dev\wellnessbox\lib\wellness\scoring.ts`
- `C:\dev\wellnessbox\lib\wellness\reportGenerator.ts`
- `C:\dev\wellnessbox\lib\wellness\data-loader.ts`

관찰 포인트

- `computeWellnessResult()`가 실제로 존재한다.
- 설문 템플릿과 계산 규칙이 JSON + TypeScript 조합으로 이미 운영 코드에 들어와 있다.
- 이는 R&D 문서와 별개로 이미 “서비스에 연결된 계산 엔진”이다.

### 3-2. B2B 도메인 데이터와 점수 규칙

핵심 경로

- `C:\dev\wellnessbox\data\b2b\survey.common.json`
- `C:\dev\wellnessbox\data\b2b\survey.sections.json`
- `C:\dev\wellnessbox\data\b2b\scoring.rules.json`
- `C:\dev\wellnessbox\data\b2b\report.texts.json`
- `C:\dev\wellnessbox\data\b2b\README.md`
- `C:\dev\wellnessbox\data\b2b\B2B_SURVEY_SYSTEM_GUIDE.md`
- `C:\dev\wellnessbox\data\b2b\B2B_SURVEY_TEST_MATRIX.md`

관찰 포인트

- 설문 구조, 섹션, 점수 규칙, 리포트 문구가 데이터 파일로 외부화되어 있다.
- `data/b2b/README.md`는 최신 설문 반영 이력, `C27` 섹션 선택 규칙, 검증 명령까지 적고 있다.
- 이 축은 “데이터 레이어 기반 R&D 후보”다.

### 3-3. 건강기능식품/안전성 지식 자산

핵심 경로

- `C:\dev\wellnessbox\data\mfds_supplement_functions.md`
- `C:\dev\wellnessbox\data\supplement_categories.md`
- `C:\dev\wellnessbox\data\supplement_overdose_and_drug_interactions_public.md`
- `C:\dev\wellnessbox\data\supplement_overdose_and_drug_interactions_expert.md`

관찰 포인트

- 규제/기능/카테고리/과다복용 상호작용 관련 지식이 별도 문서로 존재한다.
- `master_context.md`의 안전 검증 엔진, 후보 성분 생성기, 지식베이스 구축 전략과 연결 가능한 자산이다.

### 3-4. NHIS / 센서 연동 쪽 신호

핵심 경로

- `C:\dev\wellnessbox\app\(features)\health-link\README.md`
- `C:\dev\wellnessbox\docs\engineering\hyphen-nhis-integration.md`
- `C:\dev\wellnessbox\app\api\health\nhis\README.md`
- `C:\dev\wellnessbox\data\hyphen\nhis-mock.json`

관찰 포인트

- TIPS 원문에서 요구하는 “외부 건강 데이터 연동”과 직접적으로 닿는 기존 운영/개발 흔적이다.
- 현재 구현 범위는 NHIS 검진/복약 요약 중심이며, 웨어러블/CGM/유전자 전부가 있는 것은 아니다.

## 4. 결과물/백업/증빙 계층 신호

핵심 경로

- `C:\dev\wellnessbox\tmp\rnd\...` 계열 경로가 `docs/rnd/RND_DOCS_INDEX.md`에 명시되어 있음
- `C:\dev\wellnessbox\data\b2b\backups\*.json`
- `C:\dev\wellnessbox\components\b2b\ReportSummaryCards.tsx`
- `C:\dev\wellnessbox\components\b2b\ReportPdfPage.tsx`

관찰 포인트

- 서비스 산출물과 R&D 산출물이 완전히 분리돼 있지 않다.
- 일부는 실제 운영 리포트/백업이고, 일부는 TIPS KPI 증빙용 산출물 경로다.
- 다음 단계에서 “운영 산출물”과 “R&D 평가 산출물”을 반드시 구분해야 한다.

## 5. 후보 분류

### 5-1. 강한 재사용 후보

- `C:\dev\wellnessbox\docs\rnd\*`
- `C:\dev\wellnessbox\lib\rnd\*`
- `C:\dev\wellnessbox\scripts\rnd\*`
- `C:\dev\wellnessbox\lib\wellness\*`
- `C:\dev\wellnessbox\lib\b2b\public-survey.ts`
- `C:\dev\wellnessbox\data\b2b\*`
- `C:\dev\wellnessbox\data\mfds_supplement_functions.md`
- `C:\dev\wellnessbox\data\supplement_*`

### 5-2. 후보이지만 운영 코드와 섞여 있어 주의가 필요한 영역

- `C:\dev\wellnessbox\app\survey\*`
- `C:\dev\wellnessbox\app\(features)\employee-report\*`
- `C:\dev\wellnessbox\app\(features)\health-link\*`
- `C:\dev\wellnessbox\app\(admin)\admin\b2b-reports\*`
- `C:\dev\wellnessbox\app\(admin)\admin\b2b-employee-data\*`
- `C:\dev\wellnessbox\components\b2b\*`

### 5-3. 참고만 해야 하는 후보

- `C:\dev\wellnessbox\data\b2b\backups\*.json`
- `C:\dev\wellnessbox\.next\*`
- `C:\dev\wellnessbox\node_modules\*`

## 6. 이번 단계의 잠정 결론

- `wellnessbox`에는 이미 TIPS 대응을 염두에 둔 R&D 축이 상당 부분 구현되어 있다.
- 그러나 현재 1차 기준 문서는 이제부터 `C:\dev\wellnessbox-rnd\docs\context\master_context.md`로 통일해야 한다.
- 따라서 다음 단계의 핵심은 “기존 `wellnessbox` R&D 흔적을 어떤 축으로 분류할지”이지, “있는지 없는지”를 확인하는 것이 아니다.
