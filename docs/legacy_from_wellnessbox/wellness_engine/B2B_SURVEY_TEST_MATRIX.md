# B2B 설문 테스트 매트릭스

이 문서는 B2B 설문/리포트 수정 후 어떤 테스트를 어떤 관점으로 확인해야 하는지 정의합니다.

## 1) 정적 정합성 테스트

대상:
- `survey.common.json`
- `survey.sections.json`
- `scoring.rules.json`
- `report.texts.json`

검증 포인트:
- 공통 문항 수/ID/순서 (`C01`~`C27`)
- 상세 섹션 수/ID/순서 (`S01`~`S24`)
- 섹션별 `questionCount` = 실제 문항 수
- 문항 ID 포맷 (`Sxx_Qyy`) 및 번호 연속성
- 점수 옵션 범위(`0~1`)
- `C27` 옵션값과 섹션 ID 1:1 매핑
- `report.texts.json` 키 범위(`S01~S24`) 완전성
- `scoring.rules.json` 참조 문항 ID 유효성

실행:
- `npm run qa:b2b:survey-readiness`

## 2) 계산 엔진 테스트

대상:
- `lib/wellness/scoring.ts`
- `lib/wellness/analysis.ts`
- `lib/wellness/reportGenerator.ts`
- `lib/b2b/report-score-engine.ts`

검증 포인트:
- 공통 점수 all-zero/all-one 극단값
- 섹션 평균(4개/5개 선택) 계산
- `C27` alias 기반 섹션 선택
- `maxSelections` 초과 입력 절단
- 섹션/생활습관 코멘트 생성 임계치 동작
- 건강점수 수식/클램프 동작
- 종합 점수 fallback(`estimated`/`missing`) 동작

실행:
- `npm run qa:b2b:survey-readiness`
- `npm run qa:b2b:wellness-scoring`
- `npm run qa:b2b:score-engine`

## 3) API/CRUD/리포트 흐름 테스트

대상 라우트:
- `/api/admin/b2b/employees/[employeeId]/survey` (GET/PUT)
- `/api/admin/b2b/reports/[reportId]/export/pdf`
- `/api/admin/b2b/reports/[reportId]/export/pptx`
- `/api/b2b/employee/report`
- `/api/b2b/employee/report/export/pdf`

검증 포인트:
- 설문 응답 저장/조회 정상 동작
- PDF/PPTX export 200 응답
- export validation 통과
- 텍스트 레이어/페이지 수/레이아웃 parity

실행:
- `npm run qa:b2b:export-smoke`
- `npm run qa:b2b:capture-pdf-visual`

## 4) 배포 전 최소 게이트

1. `npm run audit:encoding`
2. `npm run qa:b2b:survey-readiness`
3. `npm run qa:b2b:wellness-scoring`
4. `npm run qa:b2b:score-engine`
5. `npm run qa:b2b:export-smoke`
6. `npm run lint`
7. `npm run build`
