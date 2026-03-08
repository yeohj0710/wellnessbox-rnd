# 위험과 미확정 항목

작성 기준 시각: 2026-03-08

## 1. 기준 문서 충돌 가능성

위험

- `C:\dev\wellnessbox-rnd\docs\context\master_context.md`를 1차 기준으로 삼기로 했지만,
- `C:\dev\wellnessbox\docs\rnd\*` 역시 별도의 KPI/모듈 기준 체계를 이미 갖고 있다.

영향

- 다음 단계에서 같은 개념을 서로 다른 이름/구조로 중복 관리할 위험이 있다.

현재 상태

- 아직 어떤 문서를 “폐기”, “흡수”, “참고용 유지”로 확정하지 않았다.

## 2. R&D 구현이 이미 상당히 진행된 흔적

위험

- `C:\dev\wellnessbox\lib\rnd\*`, `C:\dev\wellnessbox\scripts\rnd\*`, `C:\dev\wellnessbox\docs\rnd\PROGRESS.md`를 보면,
- 기존 저장소 안의 R&D가 이미 모듈화·평가 자동화까지 진행된 상태다.

영향

- 다음 단계에서 단순 분류가 아니라 “기존 구현을 어떤 축으로 인정할지”를 판단해야 한다.
- 잘못하면 이미 있는 구현을 다시 만드는 중복 투자가 생긴다.

현재 상태

- 이번 단계에서는 현황만 수집했고, 채택/제외는 결정하지 않았다.

## 3. 사용자 진단/추천 흐름이 여러 갈래로 분산됨

관찰된 축

- `C:\dev\wellnessbox\app\check-ai`
- `C:\dev\wellnessbox\app\assess`
- `C:\dev\wellnessbox\app\survey`
- `C:\dev\wellnessbox\app\chat`
- `C:\dev\wellnessbox\lib\wellness`

위험

- “설문/진단/추천”이 한 체계가 아니라 여러 체계로 공존한다.

영향

- 다음 단계에서 R&D 후보를 분류할 때 이들을 하나의 계통도로 정리하지 않으면 혼선이 생긴다.

## 4. 운영 코드와 R&D 코드가 한 저장소 안에 섞여 있음

위험

- `wellnessbox` 안에는 운영 페이지, 어드민, NHIS 연동, 주문 시스템, R&D 코드가 한 저장소에 공존한다.

영향

- 다음 단계에서 이관/분류를 잘못하면 운영 코드와 실험 코드의 경계가 흐려질 수 있다.
- 특히 `app/(admin)`, `app/(features)`, `components/b2b`, `lib/wellness`, `lib/rnd`는 서로 연결돼 있다.

## 5. 일부 문서/문구의 인코딩 이상

관찰

- `C:\dev\wellnessbox\docs\rnd\RND_DOCS_INDEX.md`
- `C:\dev\wellnessbox\docs\rnd\00_readme_how_to_use.md`
- `C:\dev\wellnessbox\docs\my_data_client_map.md`
- `C:\dev\wellnessbox\docs\b2b_employee_report_spec.md`
- 일부 UI 문자열

문제

- CLI에서 읽을 때 한글이 깨져 보이는 파일이 섞여 있다.

영향

- 자동 분류/검색/문서 재사용 시 오판 가능성이 있다.

현재 상태

- 경로와 일부 구조는 식별했지만, 다음 단계에서 인코딩 정비 후보로 따로 분류할 필요가 있다.

## 6. 백업 데이터와 실제 기준 데이터의 구분 불명확

관찰된 경로

- 운영 기준 가능성이 큰 파일: `C:\dev\wellnessbox\data\b2b\survey.common.json`, `survey.sections.json`, `scoring.rules.json`, `report.texts.json`
- 백업 스냅샷: `C:\dev\wellnessbox\data\b2b\backups\*.json`

위험

- 백업 데이터를 기준 데이터처럼 읽으면 현재 운영 규칙과 어긋날 수 있다.

현재 상태

- 이번 단계에서는 `data/b2b/*.json`을 우선 신호로만 보고, `backups/*.json`은 참고용 후보로만 적었다.

## 7. NHIS 연동 범위와 TIPS 센서/유전자 범위의 차이

관찰

- 현재 운영 연동 신호는 주로 `C:\dev\wellnessbox\app\(features)\health-link`와 `app\api\health\nhis\*`에 있다.
- 반면 `master_context.md`는 웨어러블, 연속혈당, 유전자까지 포함한 통합 연동을 상정한다.

영향

- 기존 운영 구현을 그대로 R&D 모듈 07과 동일시하면 과대평가될 수 있다.

현재 상태

- 이번 단계에서는 “연동 관련 기존 자산 존재”까지만 확인했다.

## 8. `wellnessbox-rnd`는 아직 초기 저장소 상태

관찰

- 현재 `C:\dev\wellnessbox-rnd`의 가시 파일은 `docs/context`의 2개 파일이 전부였다.

영향

- 이후 분류 체계, 모듈별 후보 목록, 이관 기준을 새로 설계해야 한다.
- 즉, 현재는 기준 문서 저장소이지 실행 저장소가 아니다.

## 9. Git 작업 상태 주의점

관찰

- `C:\dev\wellnessbox-rnd` 워크트리에는 루트 Markdown 파일 삭제와 `docs/` 추가가 보인다.

영향

- 다음 단계에서 추가 정리 시 “이번 단계의 단순 재배치”와 “새 분류 작업”을 구분해서 커밋/이력 관리해야 한다.

## 10. 다음 단계에서 먼저 확정해야 할 질문

1. `C:\dev\wellnessbox\docs\rnd\*`를 `master_context.md`의 하위 참고 문서로 둘 것인가, 별도 레거시 축으로 둘 것인가.
2. `/check-ai`, `/assess`, `/survey + lib/wellness` 중 무엇을 R&D 핵심 후보로 볼 것인가.
3. `lib/wellness`와 `lib/rnd`의 경계를 어떻게 정의할 것인가.
4. `data/b2b/*.json`을 운영 데이터로만 볼 것인가, R&D 지식베이스 후보로도 볼 것인가.
5. `health-link/NHIS` 축을 모듈 07 후보에 어느 수준까지 포함할 것인가.
