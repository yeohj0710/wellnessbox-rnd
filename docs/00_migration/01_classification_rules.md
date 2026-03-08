# 분류 규칙

기준 문서: `wellnessbox-rnd/docs/context/master_context.md`

이번 단계의 기준:
- `wellnessbox-rnd`가 최종 R&D source of truth가 되어야 한다.
- `wellnessbox`에는 웹서비스 운영에 필요한 화면, API, 저장, 인증, 주문, 관리자 기능만 남긴다.
- 실제 이동은 아직 하지 않고, 분류와 이주 순서만 결정한다.

## 1. 분류값 정의

| 분류값 | 의미 | 적용 기준 |
| --- | --- | --- |
| `KEEP_IN_WELLNESSBOX` | 서비스 repo에 남겨야 함 | 실제 서비스 화면, 인증/주문/회원/관리자 기능, 운영 API, 런타임 타입/유틸, 운영 문서 |
| `MOVE_TO_RND` | R&D repo로 원본을 옮겨야 함 | 연구개발 문서, agent/Codex 문서, 실험 코드, R&D 스크립트, prompt/평가/데이터셋/임시 handoff |
| `REPLACE_WITH_THIN_INTERFACE` | 본체는 R&D로 가고 wellnessbox에는 얇은 client/proxy/helper만 남겨야 함 | 현재 서비스가 직접 import 중인 AI 로직, 웰니스 계산 엔진, LLM 호출, RAG, AI 후처리 |
| `DELETE_AS_DUPLICATE` | canonical source를 하나로 남기고 중복본은 제거 대상 | 임시 handoff, 동일 트랙 중복 문서, generated duplicate |
| `NEEDS_REVIEW` | 현재 정보만으로 단정하면 위험함 | 런타임/문서/도구가 섞여 있거나, 데이터 민감도/의존성이 불명확한 경우 |

## 2. 빠른 판정 규칙

1. `app/`, `components/`, `lib/server/` 안이라도 실제 사용자 흐름을 바로 수행하면 우선 `KEEP_IN_WELLNESSBOX`를 검토한다.
2. `docs/rnd`, `docs/rnd_impl`, `lib/rnd`, `scripts/rnd`처럼 이름과 내용이 이미 R&D를 직접 가리키면 `MOVE_TO_RND`를 우선 적용한다.
3. OpenAI, LangChain, RAG, prompt, eval, AI summary, recommendation engine처럼 서비스가 직접 호출 중인 AI 본체는 `REPLACE_WITH_THIN_INTERFACE`를 우선 적용한다.
4. 루트의 agent/Codex 산출물, handoff, hotspot, guard-map, refactor backlog처럼 웹 런타임과 무관한 개발자 문서는 `MOVE_TO_RND`를 우선 적용한다.
5. 운영 매뉴얼, 클라이언트 맵, 관리자 화면 스펙, NHIS 연동 런북처럼 실제 서비스 유지보수에 직접 쓰이는 문서는 `KEEP_IN_WELLNESSBOX`를 우선 적용한다.
6. “임시”, “Temporary”, “Delete this file after …” 같은 문구가 있고 다른 canonical 문서가 존재하면 `DELETE_AS_DUPLICATE`를 검토한다.
7. 문서 묶음이나 도구 묶음이 service engineering과 agent tooling을 동시에 포함하면 `NEEDS_REVIEW`로 묶고 다음 단계에서 재분류한다.

## 3. 이번 작업에서 특히 강하게 적용한 세부 기준

### 3.1 `MOVE_TO_RND`

다음 성격이면 강하게 `MOVE_TO_RND`로 본다.

- TIPS, R&D, 연구개발, KPI, eval, dataset, prompt, closed-loop, module02~07
- agent/Codex 운영 문서
- 연구용 playground
- RAG ingest/debug/reindex 같은 실험/인덱싱 도구
- 서비스 화면과 무관한 스크립트형 실험 도구
- 지식 베이스 원문 문서

### 3.2 `REPLACE_WITH_THIN_INTERFACE`

다음 성격이면 강하게 `REPLACE_WITH_THIN_INTERFACE`로 본다.

- 서비스가 현재 직접 import하는 AI 호출 코드
- 서비스 안에 남아 있지만 미래에는 R&D API 또는 versioned package로 대체될 계산 엔진
- 정적 JSON/룰 파일이 서비스 렌더링과 계산에 동시에 쓰이는 경우
- NHIS, B2B report, chat 같은 운영 흐름 안에 박혀 있지만 실제로는 AI 후처리 계층인 경우

### 3.3 `KEEP_IN_WELLNESSBOX`

다음 성격이면 `KEEP_IN_WELLNESSBOX`로 본다.

- 실제 서비스 페이지
- 로그인, 주문, 결제, 내 데이터, 관리자 운영
- 현재 배포 중인 설문/진단 렌더링 화면
- 실제 운영용 export, sync, persistence, session, auth
- 운영 QA와 런북

### 3.4 `NEEDS_REVIEW`

다음 성격이면 `NEEDS_REVIEW`로 보류한다.

- 서비스 refactor 메모인데 agent 산출물이 섞인 문서 묶음
- shared utility라서 agent 스크립트와 build audit가 같이 물고 있는 경우
- 실제 운영 데이터 백업처럼 민감도와 필요성이 불명확한 경우
- 서비스 UI가 미래에 이동할 데이터 자산을 직접 import하는 경우

## 4. target destination path 제안 규칙

이번 manifest에서는 아래 규칙으로 대상 경로를 제안한다.

| 소스 성격 | 제안 target path 규칙 |
| --- | --- |
| R&D 문서 | `wellnessbox-rnd/docs/imported/wellnessbox/...` |
| Agent/Codex 문서 | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/...` |
| R&D 코드 | `wellnessbox-rnd/packages/...` |
| R&D / 실험 스크립트 | `wellnessbox-rnd/tools/...` |
| 지식 원문 데이터 | `wellnessbox-rnd/data/knowledge/...` |
| 웰니스/AI 엔진 | `wellnessbox-rnd/packages/wellness-engine/`, `packages/ai-runtime/`, `packages/b2b-ai/`, `packages/nhis-ai-summary/` |
| 서비스에서 얇게 남길 인터페이스 | 대상 경로는 R&D 본체 경로를 적고, `wellnessbox` 쪽 thin client는 후속 단계에서 별도 설계 |
| 검토 보류 자산 | `wellnessbox-rnd/docs/review/wellnessbox/...` 또는 `wellnessbox-rnd/quarantine/...` |

## 5. 실제 이동 순서 원칙

1. 먼저 `MOVE_TO_RND` 중 런타임 결합이 없는 문서/스크립트/코드를 옮긴다.
2. 다음으로 `REPLACE_WITH_THIN_INTERFACE` 항목에 대해 contract를 먼저 만든다.
3. 그 다음 `wellnessbox`에서 직접 import하는 경로를 thin client/proxy로 바꾼다.
4. 마지막에 `NEEDS_REVIEW`와 `DELETE_AS_DUPLICATE`를 정리한다.

## 6. 이번 분류에서 금지한 것

- `wellnessbox/` 안의 실제 파일 이동
- `wellnessbox/` 런타임 코드 수정
- `DELETE_AS_DUPLICATE` 남용
- “R&D 냄새가 난다”는 이유만으로 운영 API를 즉시 `MOVE_TO_RND`로 처리하는 것

## 7. 이번 문서의 해석 방법

1. manifest의 `classification`은 현재 시점의 1차 결정이다.
2. `move now or later`는 실제 물리 이동 우선순위를 뜻한다.
3. `target destination path`는 제안안이며, 다음 단계에서 폴더 구조를 확정하면서 조정될 수 있다.
