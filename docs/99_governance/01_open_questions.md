# 열린 질문

## 현재 가장 중요한 미결정 질문

1. `/survey` 실연동을 route 로 할지 server action 으로 할지
2. survey goals 를 `RecommendationGoal` enum 으로 어떻게 매핑할지
3. 기존 `analysis.ts` 결과와 RND 결과를 어떤 view model 로 비교할지
4. 실제 제품 SSOT 를 `wellnessbox-rnd` 로 옮길지, 별도 계약 레이어로 둘지
5. safety citation 근거를 어떤 포맷으로 저장할지
6. NHIS summary API 를 recommend API 와 분리할지, 공용 context API 를 둘지
7. `wellnessbox` shadow mode 비교 결과를 어디에 기록할지
8. rollout 대상 사용자 샘플링 키를 무엇으로 할지
9. sensor/genetic KPI 를 어떤 synthetic + 실제 로그 조합으로 측정할지
10. chat optional layer 를 언제 붙일지

## 즉시 답이 필요한 질문

### survey adapter

- `public-survey.ts` 의 어떤 함수가 adapter 재사용에 적합한가
- 응답 누락과 모호성을 `missing_information` 으로 어떻게 승격할 것인가

### fallback 전략

- `/survey` 1차 rollout 에서 사용자에게 legacy 결과만 보여줄지
- 일부 내부 세션에서만 RND 결과 preview 를 보여줄지

### 데이터 자산

- demo catalog 를 언제 실제 catalog 로 바꿀지
- legacy supplement markdown 을 어떻게 structured knowledge 로 바꿀지

## KPI 달성 관점 다음 10개 작업

1. survey adapter 결정
2. `/survey` shadow route 구현
3. fallback logging format 고정
4. safety rules 확장
5. eval set 확대
6. ranking 개선
7. explanation proxy 재정의
8. NHIS summary contract 설계
9. product/catalog ownership 결정
10. rollout bucket 설계

## 깨질 수 있는 부분

- survey mapping 을 성급히 하면 현재 결과 UX 와 크게 어긋날 수 있다
- contract 를 자주 바꾸면 `wellnessbox` 쪽 연동 비용이 커진다
- 실제 product SSOT 없이 recommendation 정확도 논의가 공회전할 수 있다

## 다음 세션 첫 질문

- `/survey` 서버 프록시를 어디에 둘지부터 고정한다.
