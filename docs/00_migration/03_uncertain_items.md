# uncertain items

기준 문서: `wellnessbox-rnd/docs/context/master_context.md`

이번 단계에서 `즉시 이동 결정`을 하지 않고 보류한 항목들이다.

## 1. `wellnessbox/docs/maintenance/`

- 이유:
  서비스 refactor 메모, extraction 노트, hotspot 로드맵이 섞여 있다.
- 불확실성:
  R&D 문서라기보다 service engineering 문서 성격이 더 강하다.
- 이동 전 확인:
  1. 실제로 누가 참조하는 문서인지
  2. CI/운영 런북으로 쓰는 문서가 있는지
  3. agent generated artifact와 human-maintained note를 분리할 수 있는지

## 2. `wellnessbox/scripts/lib/`

- 이유:
  `scripts/agent/*`와 `scripts/audit-hotspots.ts`, `scripts/audit-route-method-exports.ts` 같은 build/prebuild 계열이 공용으로 물고 있다.
- 불확실성:
  일부 helper만 분리 가능한지, 아니면 구조 전체를 재배치해야 하는지 아직 불명확하다.
- 이동 전 확인:
  1. `predev`, `prebuild`, `prelint` 경로에 걸린 helper 목록
  2. agent tooling 전용 helper와 build audit 전용 helper 분리 가능성

## 3. `wellnessbox/data/b2b/backups/`

- 이유:
  파일명이 실제 스냅샷처럼 보인다.
- 불확실성:
  샘플인지, 운영 데이터 백업인지, 민감정보가 포함됐는지 아직 확인하지 않았다.
- 이동 전 확인:
  1. PII 포함 여부
  2. 운영/감사 목적 보관 의무 존재 여부
  3. 실제 복구에 쓰이는 백업인지

## 4. `wellnessbox/lib/b2b/survey-template.ts`

- 이유:
  DB bootstrap과 `lib/wellness/data-loader` 기반 file template SSOT를 동시에 다룬다.
- 불확실성:
  R&D 엔진을 빼도 서비스 쪽에서 DB template 활성화 로직이 계속 필요한지 아직 단정하기 어렵다.
- 이동 전 확인:
  1. template version activation을 서비스가 계속 가져야 하는지
  2. R&D 쪽이 schema version만 공급하고 서비스는 DB projection만 유지할 수 있는지

## 5. `wellnessbox/components/b2b/report-summary/card-insights.ts`

- 이유:
  UI 코드가 `@/data/b2b/survey.common.json`, `@/data/b2b/survey.sections.json`을 직접 import한다.
- 불확실성:
  데이터 이주 시 UI가 어떤 최소 metadata만 필요로 하는지 정리되지 않았다.
- 이동 전 확인:
  1. 실제로 필요한 필드 최소셋
  2. R&D API 응답으로 대체할지, 서비스 쪽에 별도 snapshot을 둘지

## 6. `wellnessbox/docs/scenarios/chat-client-scenarios.md`

- 이유:
  채팅 세션 분리/재현 시나리오 문서다.
- 불확실성:
  R&D 문서라기보다 서비스 QA 문서 성격이 크다.
- 이동 전 확인:
  1. 서비스 QA 문서로 계속 둘지
  2. agent/chat 실험 시나리오로 묶을지

## 7. `wellnessbox/docs/scenarios/client-appuser-linking.md`

- 이유:
  clientId와 appUser linking 정책 문서다.
- 불확실성:
  인증/세션 설계 문서라서 R&D repo로 보내면 경계가 흐려질 수 있다.
- 이동 전 확인:
  1. 서비스 auth 문서 카테고리로 유지할지
  2. 별도 engineering docs로 분리할지

## 8. `wellnessbox/PORTING_EDITOR_IMAGE_UPLOAD.md`

- 이유:
  제목만 보면 admin/editor 포팅 메모다.
- 불확실성:
  ongoing 운영 문서인지, 과거 일회성 메모인지 불분명하다.
- 이동 전 확인:
  1. 현재 작업자가 참조 중인지
  2. 완료된 포팅 이력 보관만 필요한지

## 9. `wellnessbox/lib/b2b/analysis-service.ts`

- 이유:
  서비스 DB orchestration과 AI evaluation 호출, wellness compute가 한 파일 안에 함께 있다.
- 불확실성:
  파일 전체를 keep해야 하는지, 내부 일부만 thin interface로 바꿀지 추가 설계가 필요하다.
- 이동 전 확인:
  1. AI evaluation 호출부와 wellness compute 호출부의 분리 지점
  2. DB transaction 경계를 서비스에 남길 범위

## 10. `wellnessbox/scripts/b2b/regenerate-reports-with-wellness.*`

- 이유:
  운영 배치처럼 보이지만 엔진 내부 구현에 강하게 결합돼 있다.
- 불확실성:
  최종적으로 서비스 repo에 thin runner를 둘지, R&D repo에서 전체 배치를 돌릴지 미정이다.
- 이동 전 확인:
  1. 운영자가 이 배치를 어디서 실행해야 하는지
  2. 배치 입력/출력 contract를 서비스와 R&D 중 어디에 둘지

## 11. confirmed duplicate 1건

- 중복 후보:
  `wellnessbox/CHAT_AGENT_HANDOFF.md`
- canonical 후보:
  `wellnessbox/docs/scenarios/ai-chat-agent-handoff.md`
- 판단 근거:
  제목, 트랙, 완료 작업, 다음 세션 checklist가 같은 축이며 루트 파일에는 임시 삭제 안내가 명시돼 있다.
- 실제 삭제 전 확인:
  1. 두 문서의 차이를 병합했는지
  2. canonical 경로를 어디로 둘지 확정했는지

## 12. 보류 항목을 다음 단계에서 판단하는 순서

1. `scripts/lib/`와 `docs/maintenance/`를 먼저 service engineering vs agent tooling으로 분리한다.
2. `data/b2b/backups/`는 민감정보와 운영 필요성을 먼저 판정한다.
3. `survey-template.ts`, `card-insights.ts`, `analysis-service.ts`, `regenerate-reports-with-wellness.*`는 웰니스 엔진 thin interface 설계가 나온 뒤 최종 분류한다.
