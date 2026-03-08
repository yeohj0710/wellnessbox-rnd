# 초기 저장소 구조

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 목적

독립 R&D 저장소 기준으로 최소 구조를 고정한다.

## 현재/권장 구조

```text
wellnessbox-rnd/
  apps/
    inference_api/
  src/
    wellnessbox_rnd/
      domain/
      schemas/
      safety/
      efficacy/
      optimizer/
      orchestration/
      metrics/
      evals/
  data/
    catalog/
    rules/
    frozen_eval/
  artifacts/
    reports/
  tests/
  docs/
    context/
    00_scope_reset/
    01_architecture/
    02_eval/
    03_integration/        # 현재 archive
    99_governance/
    legacy_from_wellnessbox/  # 현재 archive
    imported/                 # 현재 archive
  scripts/
```

## 구조 원칙

1. runtime code 는 `src/wellnessbox_rnd/`
2. API entry 는 `apps/inference_api/`
3. 평가 데이터는 `data/frozen_eval/`
4. generated report 는 `artifacts/reports/`
5. 과거 문서는 archive 와 active docs 를 구분한다

## archive 원칙

아래 경로는 현재 source of truth 가 아니다.

- `docs/03_integration/`
- `docs/legacy_from_wellnessbox/`
- `docs/imported/`

## 다음 확장 후보

- `data/knowledge/`
- `artifacts/runs/`
- `scripts/synthetic/`
