# wellnessbox 런타임 맵

작성 기준 시각: 2026-03-08  
분석 대상: `C:\dev\wellnessbox`

## 1. 앱 성격 요약

`C:\dev\wellnessbox`는 단일 Next.js 앱 안에 다음 축이 함께 들어 있다.

- 일반 사용자용 상품 탐색/주문
- 간이 진단과 상세 진단
- AI 채팅 추천
- 마이데이터 집계
- B2B 공개 설문
- 임직원 건강 리포트
- NHIS(하이픈) 연동
- 관리자용 B2B 운영 화면
- 별도 R&D 실험 코드와 학습 파이프라인

메인 메뉴 노출 경로는 `C:\dev\wellnessbox\components\common\menuLinks.desktop.tsx` 기준으로 다음 축이 확인된다.

- `/explore`
- `/my-orders`
- `/check-ai`
- `/assess`
- `/survey`
- `/chat`
- `/employee-report`

## 2. 핵심 사용자 흐름

### 2-1. 홈/상품/주문 흐름

주요 경로

- `/` -> `C:\dev\wellnessbox\app\page.tsx`
- 홈 CTA/섹션 -> `C:\dev\wellnessbox\app\(components)\homeLanding.client.tsx`
- 제품 여정 브리지 -> `C:\dev\wellnessbox\app\(components)\journeyCtaBridge.tsx`
- 증상 기반 진입 CTA -> `C:\dev\wellnessbox\app\(components)\symptomImprovement.tsx`
- 주문 조회 -> `C:\dev\wellnessbox\app\(orders)\my-orders\page.tsx`
- 주문 완료 -> `C:\dev\wellnessbox\app\(orders)\order-complete\page.tsx`

읽힌 흐름

1. 사용자는 홈(`/`)에서 상품 탐색, 랭킹, 홈 제품 섹션으로 진입한다.
2. 주문 완료 후 `/order-complete`에서 주문 요약을 보고 `/my-orders`로 이동한다.
3. 주문 이력은 이후 `/my-data`, `/chat` 컨텍스트에서도 다시 사용된다.

### 2-2. 빠른 진단 흐름

주요 경로

- 페이지: `C:\dev\wellnessbox\app\check-ai\page.tsx`
- 저장 헬퍼: `C:\dev\wellnessbox\lib\checkai-client.ts`
- 저장 API: `C:\dev\wellnessbox\app\api\check-ai\save\route.ts`
- 예측 API: `C:\dev\wellnessbox\app\api\predict\route.ts`
- 유지보수 문서: `C:\dev\wellnessbox\docs\engineering\check-ai-maintenance-map.md`

읽힌 흐름

1. 사용자가 설문형 질문에 응답한다.
2. 한국어 페이지는 `/api/predict`를 호출해 점수를 계산한다.
3. 결과는 모달에 표시된다.
4. `persistCheckAiResult`를 통해 `/api/check-ai/save`로 저장된다.
5. 저장된 결과는 `/chat`, `/my-data`에서 재참조된다.

### 2-3. 상세 진단 흐름

주요 경로

- 페이지: `C:\dev\wellnessbox\app\assess\page.tsx`
- 오케스트레이션: `C:\dev\wellnessbox\app\assess\useAssessFlow.ts`
- 질문/규칙/알고리즘:  
  - `C:\dev\wellnessbox\app\assess\data\questions.ts`  
  - `C:\dev\wellnessbox\app\assess\logic\algorithm.ts`  
  - `C:\dev\wellnessbox\app\assess\logic\rules.ts`
- 저장 API: `C:\dev\wellnessbox\app\api\assess\save\route.ts`
- 유지보수 문서: `C:\dev\wellnessbox\docs\maintenance\assess-flow-modules.md`

읽힌 흐름

1. `/assess`는 `INTRO -> 질문 흐름 -> C 섹션 -> DONE` 형태로 동작한다.
2. `useAssessFlow.ts`에서 `/api/assess/save` 호출이 확인된다.
3. 같은 저장 경로는 `C:\dev\wellnessbox\app\chat\hooks\useChat.evaluation.ts`에서도 재사용된다.
4. 즉, 상세 진단은 독립 페이지뿐 아니라 채팅 보조 흐름에도 연결되어 있다.

### 2-4. 채팅 추천/행동 유도 흐름

주요 경로

- 페이지: `C:\dev\wellnessbox\app\chat\page.tsx`
- 메인 상태기계: `C:\dev\wellnessbox\app\chat\hooks\useChat.ts`
- 훅 구조 설명: `C:\dev\wellnessbox\app\chat\hooks\README.md`
- 추천 액션 UI:  
  - `C:\dev\wellnessbox\app\chat\components\RecommendedProductActions.tsx`  
  - `C:\dev\wellnessbox\app\chat\components\ReferenceData.tsx`
- 인터랙션 라우팅: `C:\dev\wellnessbox\app\chat\hooks\useChat.interactiveActions.routes.ts`
- API:  
  - `C:\dev\wellnessbox\app\api\chat\route.ts`  
  - `C:\dev\wellnessbox\app\api\chat\actions\route.ts`  
  - `C:\dev\wellnessbox\app\api\chat\save\route.ts`

읽힌 흐름

1. 채팅은 세션, 프로필, 과거 결과를 불러온다.
2. 첫 메시지 시점에 주문, `assessResult`, `checkAiResult`를 `ReferenceData`로 보여준다.
3. 추천 액션은 `/my-orders`, `/my-data`, `/check-ai`, `/assess`, `/explore` 등으로 사용자를 보낸다.
4. 따라서 채팅은 독립 기능이 아니라 기존 결과/주문 데이터를 엮는 허브 역할이다.

### 2-5. 마이데이터 집계 흐름

주요 경로

- 페이지: `C:\dev\wellnessbox\app\my-data\page.tsx`
- 데이터 로더: `C:\dev\wellnessbox\app\my-data\myDataPageData.ts`
- 구조 문서: `C:\dev\wellnessbox\docs\my_data_client_map.md`

읽힌 흐름

1. 로그인/디바이스 컨텍스트를 읽는다.
2. `assessmentResult`, `checkAiResult`, `orders`, `chatSessions`를 한 번에 조회한다.
3. `/my-data`는 계정, 프로필, 주문, 진단 결과, 채팅 이력을 한 화면에서 요약한다.

즉, `/my-data`는 여러 사용자 흐름의 종착지이자 통합 조회 화면이다.

### 2-6. B2B 공개 설문 -> 계산 -> 결과 흐름

주요 경로

- 페이지 엔트리: `C:\dev\wellnessbox\app\survey\page.tsx`
- 메인 클라이언트: `C:\dev\wellnessbox\app\survey\survey-page-client.tsx`
- 설문 맵 문서: `C:\dev\wellnessbox\docs\survey_client_map.md`
- 설문 공용 로직: `C:\dev\wellnessbox\lib\b2b\public-survey.ts`
- 웰니스 계산 엔진: `C:\dev\wellnessbox\lib\wellness\analysis.ts`
- 템플릿 로더: `C:\dev\wellnessbox\lib\wellness\data-loader.ts`
- 원천 데이터:  
  - `C:\dev\wellnessbox\data\b2b\survey.common.json`  
  - `C:\dev\wellnessbox\data\b2b\survey.sections.json`  
  - `C:\dev\wellnessbox\data\b2b\scoring.rules.json`  
  - `C:\dev\wellnessbox\data\b2b\report.texts.json`
- 세션/설문 API:  
  - `C:\dev\wellnessbox\app\api\b2b\employee\session\route.ts`  
  - `C:\dev\wellnessbox\app\api\b2b\employee\survey\route.ts`

읽힌 흐름

1. 설문 단계는 `intro -> survey -> calculating -> result`다.
2. 로컬 저장 키는 `b2b-public-survey-state.v4`다.
3. 질문 리스트는 `lib/b2b/public-survey.ts`가 조립한다.
4. 계산은 `computeWellnessResult()`가 수행한다.
5. 결과가 생기면 관리자 로그인 상태에서는 `/employee-report`로 연결된다.

### 2-7. 임직원 리포트 / NHIS 연동 흐름

주요 경로

- 리포트 페이지: `C:\dev\wellnessbox\app\(features)\employee-report\page.tsx`
- 리포트 오케스트레이션: `C:\dev\wellnessbox\app\(features)\employee-report\EmployeeReportClient.tsx`
- 리포트 맵 문서: `C:\dev\wellnessbox\docs\employee_report_client_map.md`
- 스펙 문서: `C:\dev\wellnessbox\docs\b2b_employee_report_spec.md`
- NHIS 링크 페이지: `C:\dev\wellnessbox\app\(features)\health-link\page.tsx`
- NHIS 링크 문서: `C:\dev\wellnessbox\app\(features)\health-link\README.md`
- 관련 API:  
  - `C:\dev\wellnessbox\app\api\b2b\employee\report\route.ts`  
  - `C:\dev\wellnessbox\app\api\b2b\employee\report\export\pdf\route.ts`  
  - `C:\dev\wellnessbox\app\api\health\nhis\status\route.ts`  
  - `C:\dev\wellnessbox\app\api\health\nhis\init\route.ts`  
  - `C:\dev\wellnessbox\app\api\health\nhis\sign\route.ts`  
  - `C:\dev\wellnessbox\app\api\health\nhis\fetch\route.ts`  
  - `C:\dev\wellnessbox\app\api\health\nhis\unlink\route.ts`

읽힌 흐름

1. 임직원은 이름/생년월일/전화번호 기반으로 본인 확인을 수행한다.
2. 필요 시 `/health-link`에서 하이픈 NHIS 연동을 진행한다.
3. 최신 검진/복약 요약을 가져온 뒤 `/employee-report`에서 리포트를 본다.
4. PDF 다운로드 경로가 별도로 존재한다.

### 2-8. 관리자 운영 흐름

주요 경로

- 관리자 허브: `C:\dev\wellnessbox\app\(admin)\admin\page.tsx`
- 리포트 운영:  
  - 페이지: `C:\dev\wellnessbox\app\(admin)\admin\b2b-reports\page.tsx`  
  - 클라이언트: `C:\dev\wellnessbox\app\(admin)\admin\b2b-reports\B2bAdminReportClient.tsx`
- 직원 데이터 운영:  
  - 페이지: `C:\dev\wellnessbox\app\(admin)\admin\b2b-employee-data\page.tsx`  
  - 클라이언트: `C:\dev\wellnessbox\app\(admin)\admin\b2b-employee-data\B2bAdminEmployeeDataClient.tsx`
- 관련 문서:  
  - `C:\dev\wellnessbox\docs\b2b_admin_report_client_map.md`  
  - `C:\dev\wellnessbox\docs\b2b_admin_employee_data_client_map.md`
- 관련 API:  
  - `C:\dev\wellnessbox\app\api\admin\b2b\employees\route.ts`  
  - `C:\dev\wellnessbox\app\api\admin\b2b\employees\[employeeId]\survey\route.ts`  
  - `C:\dev\wellnessbox\app\api\admin\b2b\employees\[employeeId]\analysis\route.ts`  
  - `C:\dev\wellnessbox\app\api\admin\b2b\employees\[employeeId]\note\route.ts`  
  - `C:\dev\wellnessbox\app\api\admin\b2b\employees\[employeeId]\report\route.ts`

읽힌 흐름

1. `/admin`은 운영 허브다.
2. `/admin/b2b-reports`는 설문 편집, 분석, 노트, 보고서 생성, 검증, PDF/PPTX 내보내기를 담당한다.
3. `/admin/b2b-employee-data`는 직원 원천 데이터, 건강 링크 캐시, 리포트 상태, 로그, 전체 초기화까지 관리한다.

## 3. 설문/진단/추천/결과/어드민 관련 경로 정리

| 구분 | 사용자 경로 | 핵심 파일 | 관련 API |
| --- | --- | --- | --- |
| 빠른 진단 | `/check-ai` | `C:\dev\wellnessbox\app\check-ai\page.tsx` | `/api/predict`, `/api/check-ai/save` |
| 상세 진단 | `/assess` | `C:\dev\wellnessbox\app\assess\page.tsx` | `/api/assess/save` |
| 채팅 추천 | `/chat` | `C:\dev\wellnessbox\app\chat\page.tsx` | `/api/chat`, `/api/chat/actions`, `/api/chat/save` |
| B2B 설문 | `/survey` | `C:\dev\wellnessbox\app\survey\survey-page-client.tsx` | `/api/b2b/employee/session`, `/api/b2b/employee/survey` |
| 임직원 결과 | `/employee-report` | `C:\dev\wellnessbox\app\(features)\employee-report\EmployeeReportClient.tsx` | `/api/b2b/employee/report`, `/api/b2b/employee/report/export/pdf` |
| 건강 연동 | `/health-link` | `C:\dev\wellnessbox\app\(features)\health-link\HealthLinkClient.tsx` | `/api/health/nhis/*` |
| 관리자 리포트 | `/admin/b2b-reports` | `C:\dev\wellnessbox\app\(admin)\admin\b2b-reports\B2bAdminReportClient.tsx` | `/api/admin/b2b/employees/*`, `/api/admin/b2b/reports/*` |
| 관리자 데이터 운영 | `/admin/b2b-employee-data` | `C:\dev\wellnessbox\app\(admin)\admin\b2b-employee-data\B2bAdminEmployeeDataClient.tsx` | `/api/admin/b2b/employees/*` |

## 4. 현재 런타임 맵에서 보이는 중요한 사실

- `wellnessbox`에는 하나의 추천/설문 시스템만 있는 것이 아니다.
- `/check-ai`, `/assess`, `/survey + lib/wellness`, `/chat`가 각기 다른 입력/결과 체계를 갖고 공존한다.
- B2B 설문 계산 엔진은 이미 JSON 데이터 + TypeScript 로직으로 작동한다.
- 관리자 화면은 단순 조회가 아니라 설문/분석/리포트 생성/검증/내보내기까지 포함하는 운영 도구다.
- `my-data`와 `chat`는 주문/진단/채팅 기록을 엮는 통합 허브 역할을 한다.
