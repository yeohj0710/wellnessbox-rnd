# scope reset 요약

## 핵심 선언

- 현재 목표는 `wellnessbox-rnd` 단독 연구개발이다.
- `wellnessbox` 연동은 현재 범위 밖(out of scope)이다.
- 현재 연구개발 기준 문서는 아래 두 개뿐이다.
  - `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
  - `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
- 이후 신규 문서와 코드는 이 기준만 따른다.

## 이번 정정의 의미

이전 작업 중 일부는 `wellnessbox` 연동, `/survey`, preview route, feature flag, NHIS, chat, file-by-file integration plan 쪽으로 scope drift 가 발생했다. 현재 세션에서는 그 전제를 실행 기준에서 제거하고, `wellnessbox-rnd` 를 독립 R&D 저장소로 다시 고정한다.

## 유지하는 것

- `C:/dev/wellnessbox-rnd/apps/inference_api/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/`
- `C:/dev/wellnessbox-rnd/data/catalog/`
- `C:/dev/wellnessbox-rnd/data/rules/`
- `C:/dev/wellnessbox-rnd/data/frozen_eval/`
- `C:/dev/wellnessbox-rnd/tests/`
- `C:/dev/wellnessbox-rnd/docs/02_eval/`

## 격리하는 것

- `C:/dev/wellnessbox-rnd/docs/03_integration/`
- `C:/dev/wellnessbox-rnd/docs/00_discovery/`
- `C:/dev/wellnessbox-rnd/docs/00_migration/`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/`
- `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/`

## wellnessbox 처리 원칙

- `wellnessbox` 는 이번 단계에서 실제로 되돌리지 않는다.
- 이번 작업 중 추가된 preview / proxy / helper / smoke script 는 out-of-scope 변경분으로 감사 문서에만 남긴다.
- 확실한 경우에만 `REVERT_CANDIDATE` 로 표시하고, 실제 revert 는 하지 않는다.

## 다음 작업 기준

- 1) KPI / 요구사항 재정리
- 2) R&D 데이터 계약 / 스키마 정교화
- 3) frozen eval 확대
- 4) deterministic baseline 고도화
- 5) safety / efficacy / ranking 강화
- 6) synthetic data generation pipeline
- 7) optional LLM / agent layer
