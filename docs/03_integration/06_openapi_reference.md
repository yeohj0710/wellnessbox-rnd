# OpenAPI 참고

## 목적

`wellnessbox-rnd` inference API 의 현재 계약을 문서 외 산출물로도 고정하기 위해 OpenAPI JSON 을 함께 보관한다.

## 파일

- `docs/03_integration/openapi.inference_api.json`

## 생성 기준

- 소스 앱: `apps/inference_api/main.py`
- 생성 방식: FastAPI `app.openapi()` dump
- 포함 범위: `/health`, `/v1/recommend`

## 사용 방법

- `wellnessbox` 구현 시 TypeScript type 생성 또는 수동 adapter 검토 기준으로 사용
- breaking change 여부 검토 시 diff 기준으로 사용
- PR 리뷰에서 request/response 변경 추적에 사용

## 주의

- 이 파일은 계약 스냅샷이다.
- 최종 R&D 기준 문서는 여전히 `docs/context/master_context.md` 이다.
- 실제 런타임 변경이 있으면 OpenAPI 스냅샷도 함께 갱신한다.
