# 보안·개인정보

> 상태: `PROXY_GOLD_SIMULATION` · 생성 시각: 2026-07-10T06:43:58.432475+00:00

> 이 문서는 중간 시뮬레이션 근거다. 실제 약사 판정, 실제 임상 효과, 12개월 실제 운영, 생산 기기 연동, 외부 시험·인증 완료를 뜻하지 않는다.

## 적용한 경계

서비스는 raw 사용자 ID를 R&D에 보내지 않고 HMAC 기반 가명 ID만 전달한다. R&D API는 내부 token을 확인한다. 쓰기 tool은 scope별 동의를 확인하고, idempotency·hash audit·durable postcondition을 남긴다. 검색 근거 본문은 항상 `untrusted_content`로 취급해 명령으로 실행하지 않는다.

## 생산 전 의존성 gate

현재 WellnessBox의 React는 `19.0.0-rc` 계열이다. 보안 지원 버전으로 업그레이드하고 전체 회귀 검증하기 전에는 이 기능을 production에 켜지 않는다. `npm audit --omit=dev`는 기존 production tree에서 37건(critical 3, high 11, moderate 23)을 보고했다. 이 저장소 변경은 기존 서비스 의존성을 임의로 올리지 않았다. feature flag는 remediation 전까지 꺼 둔다.
