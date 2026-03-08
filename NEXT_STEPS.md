# NEXT_STEPS

## 다음 세션에서 바로 할 일

### 1. `/survey` 실제 연동 시작

- 대상 파일:
  - `C:/dev/wellnessbox/app/survey/survey-page-client.tsx`
  - `C:/dev/wellnessbox/app/survey/_lib/survey-page-auto-compute.ts`
  - `C:/dev/wellnessbox/lib/b2b/public-survey.ts`
  - `C:/dev/wellnessbox/lib/wellness/analysis.ts`
- 목표:
  - 클라이언트 직접 계산을 바로 지우지 않고
  - `wellnessbox` 서버 route/server action 으로 recommend proxy 를 추가하고
  - flag 뒤에서 shadow call 또는 preview call 형태로 붙인다.

### 2. survey -> RND adapter 작성

- 기준 계약: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py`
- 참고 문서: `C:/dev/wellnessbox-rnd/docs/03_integration/02_request_response_contract.md`
- 해야 할 일:
  - goals enum 매핑표 작성
  - 질환/약물/증상/생활습관 답변 추출 규칙 작성
  - missing info 처리 기준 정의

### 3. shadow/fallback 로깅 추가

- 요구 필드:
  - `request_id`
  - `decision_id`
  - `latency_ms`
  - `fallback_used`
  - `fallback_reason`
  - `feature_flag_state`
- 참고 문서: `C:/dev/wellnessbox-rnd/docs/03_integration/03_error_timeout_fallback.md`

### 4. frozen eval 확대

- 파일:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/sample_cases.jsonl`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`
- 목표:
  - synthetic case 100건 이상
  - 정상 추천 / 차단 / 모호성 / 설명 품질 / edge case 균형 확보

### 5. safety/efficacy rule 강화

- 파일:
  - `C:/dev/wellnessbox-rnd/data/rules/safety_rules.json`
  - `C:/dev/wellnessbox-rnd/data/catalog/ingredients.json`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/service.py`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py`

## KPI 달성 관점의 다음 10개 작업

1. `/survey` 서버 프록시 route 추가
2. survey adapter 구현
3. legacy fallback 실제 연결
4. shadow mode 비교 로그 추가
5. frozen eval 100+ case 확대
6. safety interaction 규칙 확장
7. recommendation scoring 기준 고도화
8. explanation 품질 proxy 강화
9. NHIS summary enrichment API 설계 시작
10. rollout metric 과 feature flag 운영 계획을 `wellnessbox` env 에 반영

## 절대 먼저 하지 말 것

- chat 전면 교체
- NHIS fetch 본체 리팩토링
- DB/큐/학습 파이프라인 도입
- `wellnessbox` 기존 설문 JSON 구조 파괴
- 브라우저에서 `wellnessbox-rnd` 직접 호출

## 검증 순서

1. `C:/dev/wellnessbox-rnd` 에서 `python -m pytest`
2. `C:/dev/wellnessbox-rnd` 에서 `python scripts/run_eval.py`
3. `C:/dev/wellnessbox` 에서 `npm run qa:rnd:preview-route`
4. `wellnessbox-rnd` 서버 + `wellnessbox` dev 서버를 같이 띄워 preview 확인

## 주의점

- `wellnessbox` 에는 thin caller 만 추가해야 한다.
- 원본 규칙/평가/추천 로직은 `wellnessbox-rnd` 에서만 바꿔야 한다.
- 새로운 연구 문서는 `C:/dev/wellnessbox-rnd` 안에만 쓴다.
