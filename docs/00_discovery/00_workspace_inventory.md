# 워크스페이스 인벤토리

작성 기준 시각: 2026-03-08  
작업 루트: `C:\dev`

## 1. 이번 단계에서 확인한 최상위 폴더

`C:\dev` 아래에서 확인된 주요 폴더는 다음과 같다.

- `C:\dev\wellnessbox`
- `C:\dev\wellnessbox-rnd`
- `C:\dev\codingterrace`
- `C:\dev\doc-factory`
- `C:\dev\flyer-web`
- `C:\dev\kakaotalk-chat-web`
- `C:\dev\kakaotalk-trained-ai-chatbot`
- `C:\dev\kakaotalk_chatbot_pruned_20260228_185504`
- `C:\dev\NASDAQ-leverage-backtesting-since-1971`
- `C:\dev\test`
- `C:\dev\yeohj0710`

이번 단계의 실제 분석 대상은 `C:\dev\wellnessbox`, `C:\dev\wellnessbox-rnd` 두 폴더다.

## 2. 저장소별 현재 상태 요약

| 대상 | 경로 | 현재 성격 | 관찰된 상태 |
| --- | --- | --- | --- |
| 운영 서비스 저장소 | `C:\dev\wellnessbox` | 실제 앱/어드민/B2B/R&D 코드가 함께 있는 메인 저장소 | `main` 브랜치, `git status --short` 기준 변경 없음 |
| R&D 컨텍스트 저장소 | `C:\dev\wellnessbox-rnd` | 이번 단계에서는 기준 문서와 discovery 문서를 쌓는 별도 저장소 | `main` 브랜치, 기존 루트 문서를 `docs/context`로 옮긴 작업 흔적 존재 |

## 3. `wellnessbox` 구조 스냅샷

`C:\dev\wellnessbox`는 Next.js 15 기반 단일 앱으로 보이며, 최상위에 다음 축이 같이 존재한다.

- 앱 라우트: `C:\dev\wellnessbox\app`
- 공용 컴포넌트: `C:\dev\wellnessbox\components`
- 도메인 데이터: `C:\dev\wellnessbox\data`
- 문서: `C:\dev\wellnessbox\docs`
- 핵심 로직: `C:\dev\wellnessbox\lib`
- 실행 스크립트: `C:\dev\wellnessbox\scripts`
- DB 스키마: `C:\dev\wellnessbox\prisma`
- 모바일 빌드 자산: `C:\dev\wellnessbox\android`, `C:\dev\wellnessbox\ios`

추가 관찰:

- 가시 파일 수는 약 `90,700`개였다.
- 이 수치는 `node_modules`, `.next`가 포함된 전체 스캔 결과이므로, 소스 분석 시에는 주로 `app`, `components`, `data`, `docs`, `lib`, `scripts`, `prisma`를 중심으로 읽었다.

## 4. `wellnessbox-rnd` 구조 스냅샷

이번 단계 시작 시 루트에 있던 파일:

- `C:\dev\wellnessbox-rnd\TIPS 연구개발계획서 Markdown 정리본.md`
- `C:\dev\wellnessbox-rnd\TIPS 연구개발계획서 전체본.pdf`

이번 단계 종료 시 표준화된 위치:

- `C:\dev\wellnessbox-rnd\docs\context\master_context.md`
- `C:\dev\wellnessbox-rnd\docs\context\original_plan.pdf`

현재 관찰되는 구조:

- `C:\dev\wellnessbox-rnd\docs\context`
- `C:\dev\wellnessbox-rnd\docs\00_discovery`

추가 관찰:

- 가시 파일 수는 `2`개였다.
- 즉, 이번 시점의 `wellnessbox-rnd`는 코드 저장소라기보다 “R&D 기준 문서와 discovery 산출물을 쌓는 초기 저장소”에 가깝다.
- `txt` 계열 파일은 발견되지 않았다.

## 5. 표준 컨텍스트 파일 정리 결과

이번 단계에서 기준 문서 체계는 아래처럼 통일했다.

- 1차 기준 문서: `C:\dev\wellnessbox-rnd\docs\context\master_context.md`
- 원문 참조 PDF: `C:\dev\wellnessbox-rnd\docs\context\original_plan.pdf`

운영 원칙:

- 이후 R&D의 1차 기준은 `master_context.md`다.
- `original_plan.pdf`는 원문 참조용으로만 취급한다.
- `wellnessbox` 내부 기존 문서/코드의 삭제/이동은 이번 단계에서 수행하지 않았다.

## 6. Git 상태 메모

`C:\dev\wellnessbox`

- 브랜치: `main`
- 워크트리: 깨끗함

`C:\dev\wellnessbox-rnd`

- 브랜치: `main`
- 워크트리에서 보이는 변경:
  - 루트의 기존 Markdown 파일 삭제 표시
  - `docs/` 신규 추가 표시
- 이는 이번 단계에서 수행한 “루트 문서를 표준 위치로 재배치”한 결과다.

## 7. 이번 단계에서 아직 하지 않은 일

- `C:\dev\wellnessbox` 내부 파일 이동/삭제
- `wellnessbox-rnd` 안의 연구개발 코드 생성
- `wellnessbox` 내부 R&D 후보의 확정 이관
- `original_plan.pdf`의 심층 파싱/재구성
