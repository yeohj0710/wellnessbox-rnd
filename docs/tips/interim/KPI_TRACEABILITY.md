# KPI 추적성

> 상태: `PROXY_GOLD_SIMULATION` · 생성 시각: 2026-07-10T06:53:49.153158+00:00

> 이 문서는 중간 시뮬레이션 근거다. 실제 약사 판정, 실제 임상 효과, 12개월 실제 운영, 생산 기기 연동, 외부 시험·인증 완료를 뜻하지 않는다.

## 지금 확인된 결과

| KPI | 프록시 결과 | 표본 | 95% CI | 프록시 판정 | 실제 연구 교체 상태 |
|---|---:|---:|---:|---|---|
| KPI-1 | 100.000000 | 5,000 | 100.0000–100.0000 | 통과 | PENDING_PHARMACIST_GOLD |
| KPI-2 | 6.045903 | 240 | 5.7740–6.3024 | 통과 | PENDING_REAL_WORLD_OUTCOME |
| KPI-3 | 99.933333 | 1,500 | 99.8000–100.0000 | 통과 | PENDING_EXTERNAL_TEST |
| KPI-4 | 98.533333 | 1,500 | 97.8667–99.1333 | 통과 | PENDING_EXTERNAL_TEST |
| KPI-5 | 99.900000 | 2,000 | 99.7500–100.0000 | 통과 | PENDING_PHARMACIST_GOLD |
| KPI-6 | 3.000000 | 1,200 | — | 통과 | PENDING_12_MONTH_REAL_OPERATION |
| KPI-7 | 97.777778 | 180 | — | 통과 | PENDING_PRODUCTION_DEVICE_SESSIONS |

프록시 KPI는 **7/7** 통과했다. 실제 연구 완료 여부는 `false`다.

## 계산 규칙

- KPI-1: `|reference ∩ predicted| / |reference|`의 케이스 평균.
- KPI-2: 240개 합성 PRO percentile-point 변화 평균과 bootstrap CI.
- KPI-3~5: 실행 postcondition·안전 hard failure를 포함한 exact 판정.
- KPI-6: 추천 관련 합성 ADR 건수.
- KPI-7: W/C/G별 성공률의 동일 가중 macro 평균.
