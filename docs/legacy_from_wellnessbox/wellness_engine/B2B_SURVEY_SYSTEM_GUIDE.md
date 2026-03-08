# B2B 설문/리포트 시스템 가이드 (정밀)

이 문서는 `data/b2b/*` 설문 데이터와 B2B 리포트 계산 파이프라인을 새 세션에서도 바로 이해/수정할 수 있도록 정리한 운영 기준서입니다.

## 1) 소스 오브 트루스

- 설문 원천 데이터
  - `data/b2b/survey.common.json` (`C01`~`C27`)
  - `data/b2b/survey.sections.json` (`S01`~`S24`)
- 계산/결과 규칙
  - `data/b2b/scoring.rules.json`
  - `data/b2b/report.texts.json`
- 로더/스키마
  - `lib/wellness/data-loader.ts`
  - `lib/wellness/data-schemas.ts`

핵심 원칙:
- 문항/보기/순서/표기는 원본 설문(DOCX/PDF)과 동일해야 합니다.
- 계산 로직은 JSON 규칙(`scoring.rules.json`)과 코드(`lib/wellness/scoring.ts`, `lib/wellness/analysis.ts`)가 함께 소스 오브 트루스입니다.

## 2) 설문 구조

### 공통 설문 (`C01`~`C27`)

- `C01`~`C04`: 인적/기초 정보(성별, 나이, 키/몸무게, 여성 특이사항)
- `C05`~`C09`: 질환력/가족력/알러지/복용약/현재 관심 건강영역
- `C10`~`C26`: 생활습관 위험도 산출에 사용하는 핵심 점수 문항
- `C27`: 개선 희망 분야 선택(최대 5개)
  - 상세 섹션(`S01`~`S24`) 선택 트리거 문항
  - alias 매핑 포함(예: `호홉기`/`호흡기` -> `S24`)

### 상세 설문 (`S01`~`S24`)

- `S01`~`S24`는 `C27`에서 선택된 분야만 활성화합니다.
- 섹션별 문항 수는 `survey.sections.json`의 `questionCount`와 `questions.length`가 항상 일치해야 합니다.
- 각 문항 ID 규칙: `Sxx_Qyy` (예: `S21_Q03`)

## 3) 배점(스코어링) 방식

## 3-1) 공통 배점

구현 파일:
- `lib/wellness/scoring.ts`의 `scoreCommon`

규칙:
- 선택지 점수는 `0~1` 범위 (`score`)
- 문항별 점수 미응답은 `null`로 기록하지만 도메인 합산 시 `0`으로 처리
- 생활습관 도메인 점수 계산:
  - `normalized = (문항 점수 합) / divideBy`
  - `percent = normalized * 100`
- 전체 생활습관 위험도:
  - 4개 도메인(`diet`, `immuneManagement`, `sleep`, `activity`) 평균

## 3-2) 상세 섹션 배점

구현 파일:
- `lib/wellness/scoring.ts`의 `scoreSections`

규칙:
- 선택된 섹션별로 모든 문항 점수 평균
- 문항 미응답은 `0`으로 처리
- 섹션 점수:
  - `sectionNormalized = (섹션 문항 점수 합) / 섹션 문항 수`
  - `sectionPercent = sectionNormalized * 100`
- 건강관리 필요도 평균:
  - 선택 섹션 퍼센트 평균

## 3-3) 최종 건강점수

구현 파일:
- `lib/wellness/scoring.ts`의 `computeHealthScore`
- 실제 수식: `scoring.rules.json > overallHealthScore.calc.formula`

현재 수식:
- `healthScore = 100 - ((lifestyleRiskPercent + healthManagementNeedAveragePercent) / 2)`

보정:
- `clampToRange`로 `0~100` 제한
- 결과는 소수 둘째 자리 반올림

## 4) 검사결과(리포트) 도출 방식

구현 파일:
- `lib/wellness/analysis.ts`
- `lib/wellness/reportGenerator.ts`
- `lib/b2b/report-score-engine.ts`

### 4-1) wellness 결과 도출

- 입력:
  - `selectedSections`
  - `answersJson` / `answers`
- 섹션 선택 보정:
  - `C27` 응답값(라벨/값/alias)으로 선택 섹션 재유도
  - 최대 선택 수(`maxSelections`) 제한
- 산출:
  - 생활습관 위험도(도메인별/전체)
  - 섹션별 필요도 및 평균
  - 최종 건강점수
  - 문항별 점수 맵(`perQuestionScores`)

### 4-2) 문구 생성

- 섹션 분석 코멘트(`sectionAdvice`)
  - 기준: 문항 점수 `>= includeAdviceIfQuestionScoreGte`(기본 0.5)
  - 텍스트 소스: `report.texts.json > sectionAnalysisAdvice`
- 생활습관 실천 항목(`lifestyleRoutineAdvice`)
  - 범위: `C10~C26`
  - 우선: 점수 `== 1`
  - fallback: 점수 `>= 0.5`
  - 텍스트 소스: `lifestyleRoutineAdviceByCommonQuestionNumber`
- 맞춤 설계(`supplementDesign`)
  - 섹션 필요도 내림차순
  - 상위 `defaultTopN` 추출
  - 텍스트 소스: `supplementDesignTextBySectionId`

### 4-3) 하이라이트(고위험) 도출

- detailed/common 후보에서 우선 점수 `>=75`, 없으면 `>=50`
- 최대 5개 추출
- `domain`, `section` 카테고리 후보를 가능한 한 반드시 포함하도록 병합

### 4-4) 리포트 종합 점수 엔진

구현 파일:
- `lib/b2b/report-score-engine.ts`

역할:
- `survey`, `health`, `medication` 점수를 가중 결합하여 `overall` 산출
- 데이터 부족 시 `estimated`/`missing` 상태와 reason 제공
- 최종 risk level 계산

## 5) `/employee-report` 및 `/admin/b2b-reports` 연계 지점

### 설문 CRUD (관리자)

- GET: `app/api/admin/b2b/employees/[employeeId]/survey/route.ts`
  - `runAdminSurveyLookup` 호출
- PUT: 동일 route
  - `runAdminSurveyUpsert` 호출
  - `selectedSections`는 입력 + `C27` 파생값을 합쳐 정규화

핵심 서비스:
- `lib/b2b/survey-route-service.ts`
- `lib/b2b/survey-route-helpers.ts`
- `lib/b2b/survey-answer.ts`
- `lib/b2b/survey-template.ts`

### 임직원 리포트 조회/다운로드

- 조회 API: `app/api/b2b/employee/report/route.ts`
  - `requireB2bEmployeeToken` 인증
- 직원 PDF: `app/api/b2b/employee/report/export/pdf/route.ts`
- 관리자 PDF: `app/api/admin/b2b/reports/[reportId]/export/pdf/route.ts`

PDF 엔진:
- 기본 `web` 캡처(Playwright)
- 선택적으로 `legacy` 모드 허용(`B2B_ENABLE_LEGACY_PDF_EXPORT`)

## 6) 데이터 수정 시 반드시 지켜야 할 정합성

- `C27.options[].value`는 반드시 기존 섹션 ID(`S01~S24`)와 1:1 연결
- `sectionCatalog`(템플릿 변환 결과)는 `C27` 순서를 따라야 함
- `survey.sections.json`의 `questionCount`와 실제 문항 수 일치
- `report.texts.json`의 섹션 키는 `S01~S24` 전체 포함
- `scoring.rules.json`의 문항 참조 ID는 실제 문항 ID와 일치
- 모든 점수는 `0~1` 범위 유지

## 7) 변경 후 필수 검증 커맨드

1. `npm run audit:encoding`
2. `npm run qa:b2b:survey-readiness`
3. `npm run qa:b2b:score-engine`
4. `npm run qa:b2b:wellness-scoring`
5. `npm run qa:b2b:export-smoke`
6. `npm run lint`
7. `npm run build`
