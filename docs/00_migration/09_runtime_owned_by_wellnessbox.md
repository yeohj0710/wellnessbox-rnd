# runtime owned by wellnessbox

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 원칙

- 아래 영역은 split 이후에도 `wellnessbox`가 계속 소유한다.
- 공통 원본은 두지 않는다.
- 서비스가 소비하는 R&D 결과가 필요하면 생성된 contract나 snapshot만 받는다.

## 서비스 런타임 소유 영역

### 사용자/운영 UI

- `C:/dev/wellnessbox/app/`
- `C:/dev/wellnessbox/components/`
- `C:/dev/wellnessbox/public/`
- `C:/dev/wellnessbox/src/`
- `C:/dev/wellnessbox/types/`

대표 경로:

- `C:/dev/wellnessbox/app/check-ai/`
- `C:/dev/wellnessbox/app/assess/`
- `C:/dev/wellnessbox/app/survey/`
- `C:/dev/wellnessbox/app/chat/`
- `C:/dev/wellnessbox/app/(features)/employee-report/`
- `C:/dev/wellnessbox/app/(features)/health-link/`
- `C:/dev/wellnessbox/app/(admin)/admin/b2b-reports/`
- `C:/dev/wellnessbox/app/(admin)/admin/b2b-employee-data/`

### 서비스 도메인 로직

- `C:/dev/wellnessbox/lib/order/`
- `C:/dev/wellnessbox/lib/server/route-auth.ts`
- `C:/dev/wellnessbox/lib/admin-token.ts`
- `C:/dev/wellnessbox/lib/db.ts`
- `C:/dev/wellnessbox/lib/product/`
- `C:/dev/wellnessbox/lib/notification/`
- `C:/dev/wellnessbox/lib/server/result-normalizer.ts`
- `C:/dev/wellnessbox/lib/b2b/analysis-service.ts`
- `C:/dev/wellnessbox/lib/b2b/report-payload.ts`

주의:

- `lib/ai`, `lib/wellness`, `lib/b2b/ai-evaluation`, `lib/server/hyphen/fetch-ai-summary*`는 현재 파일 위치는 `wellnessbox`에 있지만 장기적으로는 서비스 소유가 아니라 thin interface 후보다.

### 서비스용 데이터와 템플릿

- `C:/dev/wellnessbox/data/b2b/survey.common.json`
- `C:/dev/wellnessbox/data/b2b/survey.sections.json`
- `C:/dev/wellnessbox/data/b2b/scoring.rules.json`
- `C:/dev/wellnessbox/data/b2b/report.texts.json`
- `C:/dev/wellnessbox/data/b2b/backups/` (예외, 검토 필요)

### 서비스 API와 운영 기능

- `C:/dev/wellnessbox/app/api/health/nhis/`
- `C:/dev/wellnessbox/app/api/chat/`
- `C:/dev/wellnessbox/app/api/verify-password/route.ts`
- `C:/dev/wellnessbox/app/api/get-payment-info/route.ts`
- `C:/dev/wellnessbox/middleware.ts`

### 서비스 유지보수 문서와 검증 스크립트

- `C:/dev/wellnessbox/docs/README.md`
- `C:/dev/wellnessbox/docs/DOCS_CATALOG.md`
- `C:/dev/wellnessbox/docs/maintenance/` 중 서비스 유지보수 문서
- `C:/dev/wellnessbox/scripts/qa/`
- `C:/dev/wellnessbox/scripts/maintenance/`
- `C:/dev/wellnessbox/scripts/audit-encoding.ts`
- `C:/dev/wellnessbox/scripts/audit-hotspots.ts`
- `C:/dev/wellnessbox/scripts/audit-route-method-exports.ts`

## 서비스 저장소에 남아 있지만 장기적으로 경계 정리가 필요한 예외

- `C:/dev/wellnessbox/docs/rnd/`
- `C:/dev/wellnessbox/docs/rnd_impl/`
- `C:/dev/wellnessbox/lib/rnd/`
- `C:/dev/wellnessbox/scripts/rnd/`
- `C:/dev/wellnessbox/app/agent-playground/`
- `C:/dev/wellnessbox/app/api/rag/`
- `C:/dev/wellnessbox/lib/agent-playground/`
- `C:/dev/wellnessbox/lib/server/rag-debug-route.ts`
- `C:/dev/wellnessbox/lib/server/rag-ingest-route.ts`
- `C:/dev/wellnessbox/lib/server/rag-reindex-route.ts`

이 항목들은 현재 `wellnessbox`에 남아 있지만, ownership 기준으로는 서비스 영구 소유 영역으로 보지 않는다.
