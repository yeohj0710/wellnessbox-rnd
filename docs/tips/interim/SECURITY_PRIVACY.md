# 보안·개인정보

> 상태: `PROXY_GOLD_SIMULATION` · 생성 시각: 2026-07-10T06:53:49.153158+00:00

> 이 문서는 중간 시뮬레이션 근거다. 실제 약사 판정, 실제 임상 효과, 12개월 실제 운영, 생산 기기 연동, 외부 시험·인증 완료를 뜻하지 않는다.

## 적용한 경계

서비스는 raw 사용자 ID를 R&D에 보내지 않고 HMAC 기반 가명 ID만 전달한다. R&D API는 내부 token을 확인한다. 쓰기 tool은 scope별 동의를 확인하고, idempotency·hash audit·durable postcondition을 남긴다. 검색 근거 본문은 항상 `untrusted_content`로 취급해 명령으로 실행하지 않는다.

## 생산 전 의존성 gate

WellnessBox는 Next.js 15.5.20과 React 19.1.2로 올리고 회귀 검증했다. `npm audit --omit=dev`의 critical/high는 0건이며, Next.js 번들 PostCSS의 moderate 2건이 남았다. audit의 강제 수정은 Next.js 9 역다운그레이드를 제안해 적용하지 않았다. feature flag는 외부 연구·법무·인증 gate 전까지 꺼 둔다.
