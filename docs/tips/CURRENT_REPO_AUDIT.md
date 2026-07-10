# 현재 저장소 감사

> 상태: `PROXY_GOLD_SIMULATION` · 생성 시각: 2026-07-10T06:52:11.930327+00:00

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

## 직접 검증한 근거

- 원본 패키지: `C:\dev\wellnessbox_tips_interim_simulation_package`
- 원본 manifest SHA-256: `2a430ac5899544885d4be923213b50d526ffd0df016b2b34bf57a077d4c650a4`
- 원본 manifest 항목: 19
- 재학습 manifest SHA-256: `ec1a038a5ac372beed3b8254311c9c4a271e6aad970515397bd1d7028afcb934`
- 등록 모델: `proxy-recommendation-f6b053ee0eb39d16` / `f6b053ee0eb39d16e12e102723f9435a03e71068b70502f6ca702c80e82a7612`
- 원 개발계획 PDF 25–26쪽 수식 대조: 추천 분모는 기준 집합 `|R_i|`; W/C/G는 세 출처 동일 가중 macro 평균.

## 구현 판정

| 영역 | 상태 | 직접 근거 |
|---|---|---|
| 패키지 무결성·15만 건 import | IMPLEMENTED_AND_VERIFIED | manifest·DB count |
| 7개 KPI 계산 | IMPLEMENTED_AND_VERIFIED | 독립 수식·CI·DB 결과 |
| 근거·안전·Agent·API | IMPLEMENTED_AND_VERIFIED | 자동 테스트 |
| 실제 약사 라벨 | BLOCKED_EXTERNAL | 계약·라벨링 미실시 |
| 실제 효과·12개월 ADR | BLOCKED_EXTERNAL | 실제 관찰 미실시 |
| 생산 기기·외부 시험·인증 | BLOCKED_EXTERNAL | 외부 환경 미제공 |
