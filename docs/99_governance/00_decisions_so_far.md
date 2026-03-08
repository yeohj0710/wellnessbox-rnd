# 지금까지의 결정

## 최상위 결정

1. 연구개발 기준 문서는 `C:/dev/wellnessbox-rnd/docs/context/master_context.md` 하나로 통일한다.
2. `wellnessbox` 는 웹서비스/UI 레이어다.
3. `wellnessbox-rnd` 는 연구개발/API/평가/규칙 원본 repo 다.
4. 무거운 학습 코드, 데이터 생성 파이프라인, 평가 하네스, 추론 본체는 `wellnessbox-rnd` 에 둔다.
5. 웹은 최종적으로 `wellnessbox-rnd` API 를 호출하는 얇은 caller 가 된다.

## 아키텍처 결정

- deterministic baseline first
- eval first
- LLM is optional layer
- no training inside Next.js
- hard split web vs rnd

ADR 문서:

- `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-001-hard-split-web-vs-rnd.md`
- `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-002-eval-first.md`
- `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-003-deterministic-baseline-first.md`
- `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-004-llm-is-optional-layer.md`
- `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-005-no-training-inside-nextjs.md`

## 구현 결정

- Python stack: FastAPI + Pydantic + pytest + ruff
- 현재 추천 API: `/health`, `/v1/recommend`
- recommend 응답은 structured JSON 만 사용
- demo catalog 와 rules 로 baseline 을 시작하고 점진 고도화한다
- frozen eval 을 먼저 고정하고 구현은 그 뒤에 바꾼다

## 연동 결정

- 브라우저는 `wellnessbox-rnd` 를 직접 호출하지 않는다
- `wellnessbox` 서버가 proxy/adapter 역할을 한다
- 1차 실제 대상은 `/survey`
- 이번까지 실제 구현된 것은 dev-only preview route/page
- 실패 시 fallback 우선

## 레거시 문서 처리 결정

- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/` 는 참고 자료다
- 새 설계/결정/운영 문서는 모두 `wellnessbox-rnd` 쪽 새 문서에만 쓴다
- `wellnessbox` 안에 R&D 원본을 다시 만들지 않는다

## KPI 관점 우선순위 결정

1. safety
2. recommendation quality
3. next action/policy
4. measurable eval
5. rollout-safe integration

## 지금까지 구현된 것

- baseline recommend engine
- eval runner
- OpenAPI snapshot
- `wellnessbox` dev preview integration

## 아직 미구현인 것

- survey live integration
- NHIS summary integration
- chat thin interface
- product SSOT
- large eval dataset

## 주의점

- 이 repo 안의 새 결정이 legacy 문서를 덮어쓴다
- source of truth 는 한 군데만 유지한다
- 추후 계약 변경 시 OpenAPI 와 integration 문서를 같이 갱신한다
