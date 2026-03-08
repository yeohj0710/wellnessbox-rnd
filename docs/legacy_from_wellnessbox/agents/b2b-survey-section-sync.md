# B2B 설문 섹션 동기화 규칙 (C27)

이 문서는 `/survey` 와 `/admin/b2b-reports` 의 섹션 선택 동기화(C27) 관련 핵심 규칙을 정리합니다.

## 핵심 규칙

1. C27이 답변에 **명시적으로 존재**하면, 선택 섹션은 C27만을 기준으로 계산합니다.
2. C27이 없을 때만 `selectedSections` fallback 값을 사용합니다.
3. 선택 섹션에서 제외된 영역의 문항 답변은 즉시 제거(prune)해야 합니다.
4. 클라이언트뿐 아니라 서버 저장 시점에서도 동일한 prune를 강제해야 합니다.

## 소스 오브 트루스

- 공통 계산: `lib/b2b/public-survey.ts`
  - `resolveSelectedSectionsFromC27`
  - `pruneSurveyAnswersByVisibility`
  - `resolveSurveySelectionState`
- 서버 저장 방어: `lib/b2b/survey-route-helpers.ts`
  - `resolveSurveySelectedSections`
  - `pruneSurveyAnswersForSelectedSections`
- 업서트 경로: `lib/b2b/survey-route-service.ts`

## UI 반영 경로

- 사용자 설문: `app/survey/survey-page-client.tsx`
- 관리자 설문 편집: `app/(admin)/admin/b2b-reports/B2bAdminReportClient.tsx`

두 화면 모두 답변 변경/섹션 토글 시 `resolveSurveySelectionState`를 통해 같은 규칙을 사용해야 합니다.

## 회귀 방지 QA

- 단독 검증: `npm run qa:b2b:c27-deselection-sync`
- 전체 설문 스위트: `npm run qa:b2b:survey-full`

## 리팩토링 시 체크리스트

1. C27 해제 시 하위 섹션 문항이 즉시 화면에서 사라지는지
2. 하위 섹션 문항 답변이 메모리 상태/저장 데이터에서 제거되는지
3. `/survey`, `/admin/b2b-reports`, 레포트 미리보기에서 동일하게 반영되는지
