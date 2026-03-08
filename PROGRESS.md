# PROGRESS

## 현재 상태

`wellnessbox-rnd` 는 독립 R&D 저장소로 재고정되었고, 현재 실행 기준은 `master_context.md` 와 `original_plan.pdf` 두 문서다.

## source of truth

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

보조 기준:

- `C:/dev/wellnessbox-rnd/docs/01_architecture/`
- `C:/dev/wellnessbox-rnd/docs/02_eval/`
- `C:/dev/wellnessbox-rnd/docs/99_governance/`

archive:

- `C:/dev/wellnessbox-rnd/docs/03_integration/`
- `C:/dev/wellnessbox-rnd/docs/00_discovery/`
- `C:/dev/wellnessbox-rnd/docs/00_migration/`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/`
- `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/`

## 지금까지 구현된 것

- Python 프로젝트 scaffold
- FastAPI inference API
- `/health`
- `/v1/recommend`
- deterministic baseline:
  - intake normalization
  - safety validation
  - candidate filtering
  - goal / efficacy scoring
  - ranking
  - templated explanation
- frozen eval runner
- metric definitions / calculators
- demo catalog / safety rules
- scope reset 감사 문서와 governance 문서

## 아직 미구현인 것

- 대규모 frozen eval
- deterministic baseline 고도화
- richer safety citation structure
- synthetic data generation pipeline
- optional LLM/agent layer
- production-scale artifact/version management

## KPI 달성 관점에서 가장 중요한 다음 10개 작업

1. `master_context.md` 기준 KPI/요구사항 재정리
2. recommend request/response 계약 정교화
3. frozen eval case 100+ 확장
4. deterministic baseline ranking 개선
5. safety rule set 확장
6. efficacy scoring 강화
7. missing info / follow-up 질문 정교화
8. synthetic data generation 설계
9. evidence / citation 구조화
10. optional LLM layer 평가 기준만 선행 정의

## 깨질 수 있는 부분 / 주의점

- 현재 catalog 는 demo 데이터라 실제 제품 적합성을 보장하지 않는다.
- eval dataset 이 작아 KPI gate 로 쓰기엔 아직 부족하다.
- `sensor_genetic_integration_rate_pct` 는 목표치 미달 상태다.
- 과거 `wellnessbox` 연동 문서를 실행 입력으로 다시 사용하면 scope drift 가 재발한다.

## 범위 밖(out of scope)

- `wellnessbox` 특정 페이지/route/설문/NHIS/chat 흐름
- preview route / feature flag / rollout 계획
- 제품 repo 기준 adapter 설계

## 다음 세션 첫 작업

- `master_context.md` 와 `original_plan.pdf` 기준으로 KPI / 요구사항을 다시 쪼개고, 그 결과를 runtime schema 와 frozen eval 확장 항목으로 연결한다.
