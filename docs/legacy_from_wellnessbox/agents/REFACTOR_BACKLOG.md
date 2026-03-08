# Refactor Backlog (Hotspot Driven)

Base input: `npm run audit:hotspots`

## Completed in this cycle

1. `app/api/chat/actions/route.ts`
   - Reduced to thin orchestration route.
   - Extracted action logic into `lib/chat/actions/{shared,fallback,model}.ts`.
2. `app/chat/hooks/useChat.ts`
   - Extracted browser helpers, suggestions, evaluation logic.
   - Added `useChat.api.ts` to centralize chat endpoint calls.
3. `components/chat/DesktopChatDock.tsx`
   - Split dock panel from trigger container.
   - Extracted launch lifecycle and route-nudge/global-event state into `useDesktopChatDockLauncher.ts`.
4. `components/chat/DesktopChatDockPanel.tsx`
   - Extracted session drawer layer into `DesktopChatDockSessionLayer.tsx`.
   - Extracted shell effects and session-layer handlers into `useDesktopChatDockPanelShell.ts`.
5. Agent maintenance tooling
   - Added `agent:skills-catalog` and `agent:refactor-report` scripts.
6. `app/api/health/nhis/fetch/route.ts`
   - Added DB cache replay protection + identity/request hashing.
   - Added cost guard caps (detail year scan / yearly detail call upper-bound).
   - Added low-cost client path and transparent cache metadata in response.
   - Extracted provider orchestration into `lib/server/hyphen/fetch-executor.ts`.
   - Added shared contracts in `lib/server/hyphen/fetch-contract.ts`.
   - Added force-refresh cooldown + in-flight dedupe guardrail.
   - Switched cooldown basis to latest fetch attempt (includes failed attempts) to block repeated paid retries.
   - Added server-side target policy block for high-cost NHIS targets by default.
7. `app/api/health/nhis/status/route.ts` + `/health-link`
   - Exposed cooldown/target policy state in status API.
   - Pre-disabled force-refresh UI actions while cooldown remains.
8. `app/(features)/health-link/HealthLinkClient.tsx`
   - Split shared presentational blocks into `components/HealthLinkCommon.tsx`.
   - Extracted status meta block into `components/HealthLinkStatusMeta.tsx`.
9. NHIS init/sign guard hardening
   - Added identity-aware `init` reuse path to avoid repeated paid init calls.
   - Added in-flight dedupe helper for `init/sign/fetch` concurrent duplicate requests.
   - Added `sign` short-circuit when already linked with same identity.
10. `app/(features)/health-link/useNhisHealthLink.ts`
   - Extracted fetch UI policy/constants into `fetchClientPolicy.ts`.
11. `app/api/health/nhis/fetch/route.ts` + `lib/server/hyphen/fetch-cache.ts`
   - Added identity-level cache fallback to absorb request-hash drift from date-window changes.
   - Added explicit cache source signaling (`db` vs `db-identity`) for observability.
   - Reset cache hit counters on fresh overwrite to keep cache telemetry accurate.
12. `app/api/health/nhis/fetch/route.ts`
   - Extracted cache replay + persistence helpers into `lib/server/hyphen/fetch-route-cache.ts`.
   - Reduced route responsibility to validation/auth/policy/orchestration.
13. `app/(features)/health-link/HealthLinkClient.tsx`
   - Extracted detail action toolbar to `components/HealthLinkFetchActions.tsx`.
   - Extracted raw JSON panel to `components/HealthLinkRawResponseSection.tsx`.
14. `app/(features)/health-link/HealthLinkClient.tsx`
   - Split header/auth/results presentation into:
     - `components/HealthLinkHeader.tsx`
     - `components/HealthLinkAuthSection.tsx`
     - `components/HealthLinkResultSection.tsx`
   - Kept page-level state/orchestration in client root and moved section markup out.
15. `app/api/health/nhis/fetch/route.ts`
   - Canonicalized `yearLimit` for summary-only targets to avoid cache key fragmentation.
   - Unified in-flight dedupe key across force/non-force fresh requests for lower duplicate call risk.
16. `app/(features)/health-link/*`
   - Added `copy.ts` + `view-model.ts` to separate copy/state derivation from rendering.
   - Reduced `HealthLinkClient.tsx` to orchestration-only composition.
17. `app/api/health/nhis/fetch/route.ts`
   - Removed dependency on pending easy-auth session in fetch path.
   - Fetch now uses persisted linked credentials only, reducing stale-session drift and paid-call risk.
18. NHIS paid-call budget guard (`fetch/status` + Prisma)
   - Added `HealthProviderFetchAttempt` model + migration for non-cached fetch-attempt logging.
   - Added rolling-window budget enforcement in `lib/server/hyphen/fetch-attempt.ts`.
   - `POST /api/health/nhis/fetch` now blocks over-limit fresh/force fetches with `429` + `Retry-After`.
   - `GET /api/health/nhis/status` now returns `fetchBudget` snapshot for UI transparency.
   - `/health-link` status meta now exposes fresh/force budget usage and remaining quota.
19. NHIS budget UX + maintenance hardening
   - Force-refresh buttons now pre-disable on both cooldown and budget-exhausted states.
   - Added budget-aware force-refresh hint text in `/health-link`.
   - Added maintenance script `maintenance:nhis-prune-attempts` to prune old fetch-attempt logs.
   - Documented retention env and prune runbook in NHIS API docs.
20. NHIS maintenance operations toolkit
   - Added `maintenance:nhis-prune-cache` for expired fetch-cache cleanup.
   - Added `maintenance:nhis-report-attempts` for recent window usage/success/force-rate reporting.
   - Added graceful migration-missing handling for maintenance scripts (`P2021` -> skip with guidance).
21. NHIS policy guard modularization + smoke check
   - Extracted fetch request policy helpers to `lib/server/hyphen/fetch-request-policy.ts`.
   - Added `maintenance:nhis-smoke-policy` to verify cooldown/target/year-limit invariants.
   - Optimized top-user attempt reporting query with DB-side aggregation (`$queryRaw`) for large datasets.
22. `app/chat/hooks/useChat.ts`
   - Extracted shared assistant stream orchestration into `useChat.assistant.ts`.
   - Extracted session-persist helpers into `useChat.persistence.ts`.
   - Reduced duplicate stream/sanitize/hydrate blocks and idempotent-save duplication.
23. NHIS force-refresh cost guard hardening
   - Added recent-cache replay guard for force-refresh requests (`db-force-guard` source).
   - Added env knob `HYPHEN_NHIS_FORCE_REFRESH_CACHE_GUARD_SECONDS` (default 1800s).
   - Exposed guarded-cache UX notice path through `/health-link` fetch notice policy.
24. NHIS cooldown accuracy hardening
   - Fixed latest-attempt resolver to read `HealthProviderFetchAttempt` (non-cached attempts) first.
   - Added fallback to cache timestamp when attempt table is unavailable (`P2021` compatibility path).
   - `GET /api/health/nhis/status` cooldown now aligns to latest attempt timestamp.
25. `app/chat/hooks` API wrapper consolidation
   - Added `requestSaveChatSession` and `requestDeleteChatSession` in `useChat.api.ts`.
   - Switched `useChat.persistence.ts` / `useChat.ts` delete flow to wrapper usage.
26. `/health-link` copy integrity cleanup
   - Replaced mojibake user-facing strings in `useNhisHealthLink.ts`, `constants.ts`, and `utils.ts`.
   - Centralized hook/workflow/status-meta/table copy into `copy.ts`.
   - Normalized status-details summary + fallback labels.
27. `app/chat/hooks/useChat.ts` state-update refactor
   - Added `useChat.sessionState.ts` for immutable session update helpers.
   - Replaced repeated inline `setSessions(...map...)` blocks with shared helpers.
28. `app/chat/hooks/useChat.ts` send-message preparation split
   - Added `useChat.sendMessage.ts` with `prepareOutgoingTurn`.
   - Reduced inline parsing/validation/message-construction logic in `sendMessage`.
29. `app/chat/hooks/useChat.ts` send-message branch resolver split
   - Added `useChat.sendMessageFlow.ts` to resolve assessment/offline/action/cart/stream branches.
   - Simplified `sendMessage` by removing duplicated branch-handling boilerplate.
30. `app/chat/hooks/useChat.ts` streamed-turn orchestration split
   - Added `useChat.streamTurn.ts` for shared stream/update/finalize lifecycle.
   - Unified chat/init streamed turn execution path to reduce duplication and drift risk.
31. `app/(components)/homeProductSection.tsx` presentational split + health-link duplicate-fetch guard
   - Extracted selected-pharmacy notice and load/empty status blocks into `homeProductSection.view.tsx`.
   - Added `useNhisHealthLink.ts` detail-fetch short-circuit when detailed rows are already loaded (no extra paid call).
   - Wired UI disabled/hint state for already-loaded detail path in health-link fetch actions.
32. `app/chat/hooks/useChat.ts` initial/bootstrap and session-action split
   - Added `useChat.initialAssistant.ts` to isolate empty-session bootstrap stream flow (guards/offline/error/stream lifecycle).
   - Added `useChat.sessionActions.ts` for session create/delete state transitions.
   - Reduced inline mutation logic in `useChat.ts` for startup/new/delete paths.
33. `app/chat/hooks/useChat.ts` finalize/assessment flow split
   - Added `useChat.finalizeFlow.ts` for title-generation + assistant turn finalize orchestration.
   - Added `useChat.assessmentFlow.ts` for in-chat assessment bootstrap/input flow.
   - Reduced inline assessment parser/evaluation branching and finalize post-processing in `useChat.ts`.
34. `app/chat/hooks/useChat.ts` follow-up fetch orchestration split
   - Added `useChat.followups.ts` to centralize suggestion/action follow-up fetch pipelines.
   - Moved fallback/history handling for suggestion generation out of `useChat.ts`.
   - Moved interactive action candidate resolution + fallback prioritization out of `useChat.ts`.
35. `lib/notification/core.ts` push fanout boundary split
   - Extracted push runtime/env policy helpers to `lib/notification/core.runtime.ts`.
   - Extracted push error classification + Prisma error guards to `lib/notification/core.error.ts`.
   - Extracted push delivery dedupe/finalize/dead-endpoint cleanup to `lib/notification/core.delivery-gate.ts`.
   - Added shared push types in `lib/notification/core.types.ts`.
   - Reduced `core.ts` to subscription/query + fanout orchestration flow.
36. `lib/server/result-normalizer.ts` snapshot normalization boundary split
   - Added `lib/server/result-normalizer.types.ts` for snapshot/result contracts + version constants.
   - Added `lib/server/result-normalizer.shared.ts` for parser/normalizer primitives.
   - Split assess-specific logic into `lib/server/result-normalizer.assess.ts`.
   - Split check-ai-specific logic into `lib/server/result-normalizer.check-ai.ts`.
   - Reduced `lib/server/result-normalizer.ts` to stable export surface + snapshot-version assertion.
37. `app/my-data/page.tsx` server-data orchestration split
   - Added `app/my-data/myDataPageData.ts` to isolate session/actor/appUser lookup and DB query orchestration.
   - Reduced page-level responsibilities to route guard + view composition.
   - Replaced inline profile-phone cast with typed helper (`readProfilePhone`).
38. `lib/product/product.ts` query duplication cleanup
   - Added shared in-stock where/select/order constants (`IN_STOCK_PRODUCT_WHERE`, `PRODUCT_CARD_SELECT`, `DEFAULT_PRODUCT_ORDER`).
   - Deduplicated `getProducts`/`getProductsByUpdatedAt` through `findProductsForCards`.
   - Replaced repeated relation id formatter (`any[]`) with typed helper `mapRelationIds`.
39. `app/(orders)/order-complete/page.tsx` payment/orchestration cleanup
   - Added `app/(orders)/order-complete/orderCompleteFlow.ts` for payment-context parsing, order-draft hydration, payment-outcome normalization, and checkout/payment storage cleanup helpers.
   - Replaced duplicated inicis/non-inicis order-create branches with one shared `createOrderFromPaymentOutcome` path.
   - Added lock release safety (`finally`) and non-OK payment-info response handling to prevent stale local storage loops.
   - Removed unused login-status fetch from order-complete page.
   - Added semantic/accessibility polish (`main` landmark, `aria-live` push status toast, focus-visible rings).
40. `app/chat/components/MessageBubble.tsx` markdown-rendering boundary split
   - Added `app/chat/components/messageBubble.markdown.tsx` for markdown plugin configuration and renderer component map.
   - Added `app/chat/components/messageBubble.format.ts` for shared message-text newline normalization.
   - Reduced in-component object churn by memoizing remark/rehype plugin lists and markdown component map.
   - Kept loading/copy/chat bubble orchestration in `MessageBubble.tsx` while moving render policy helpers out.
41. `app/api/get-payment-info/route.ts` payment verification safety hardening
   - Replaced ad-hoc body parsing with `zod` request validation (`paymentId`, `paymentMethod` required).
   - Added explicit env validation for PortOne v1/v2 credentials before remote calls.
   - Split PortOne v1/v2 token/payment lookup paths into dedicated helpers with shared error parsing.
   - Normalized API error responses (`400` invalid input, `500` provider/runtime failure) for predictable caller handling.
42. `app/(components)/homeProductSection.tsx` UI action boundary split
   - Added `app/(components)/useHomeProductActions.ts` for product-detail/cart open-close callbacks and scroll/return-path restore behavior.
   - Removed inline `restoreScroll`, `openProductDetail`, `closeProductDetail`, `openCart`, `closeCart` blocks from page component.
   - Kept page-level state/effect orchestration in `homeProductSection.tsx` and moved only imperative UI action handlers.
43. `app/assess/page.tsx` storage boundary split
   - Added `app/assess/lib/assessStorage.ts` for assess state load/save/clear helpers and C-section rollback helper.
   - Replaced direct inline `localStorage` snapshot/rollback mutations in page with storage helper calls.
   - Kept question flow/evaluation orchestration in page component while isolating persistence concerns.
44. `app/(components)/useHomeProductSectionEffects.ts` effect-module boundary split
   - Split monolithic effect module into dedicated files:
     - `useHomeProductSectionEffects.ui.ts`
     - `useHomeProductSectionEffects.query.ts`
     - `useHomeProductSectionEffects.lifecycle.ts`
     - `useHomeProductSectionEffects.computation.ts`
   - Added shared type aliases in `homeProductSectionEffects.types.ts`.
   - Converted `useHomeProductSectionEffects.ts` into a stable barrel export surface to keep call sites unchanged.
45. `lib/product/product.ts` product-module boundary split
   - Added `lib/product/product.shared.ts` for shared in-stock where/select/order constants and rating-default mapper.
   - Added `lib/product/product.catalog.ts` for card list, updated list, name list, and summary query paths.
   - Added `lib/product/product.admin.ts` for admin CRUD/query paths and typed relation-id mapping helper.
   - Kept `lib/product/product.ts` as the stable export surface and chat-catalog pricing-selection logic with async wrapper exports.
46. `lib/server/client-link.ts` client-resolution boundary split
   - Added `lib/server/client-link.session.ts` for session-context resolution and appUser client lookup helpers.
   - Added `lib/server/client-link.merge.ts` for client merge selection/merge execution/masked phone helpers.
   - Reduced `lib/server/client-link.ts` to attach/resolve orchestration with shared helper imports.
   - Preserved auth/ownership behavior while shrinking high-cyclomatic merge/session internals from the main entry module.
47. `lib/server/hyphen/client.ts` transport boundary split
   - Added `lib/server/hyphen/client.contracts.ts` for endpoint constants and Hyphen request/response contracts.
   - Added `lib/server/hyphen/client.runtime.ts` for auth-header/env timeout/common parsing helpers.
   - Added `lib/server/hyphen/client.request.ts` for `hyphenPost` transport and `HyphenApiError` classification.
   - Reduced `lib/server/hyphen/client.ts` to stable export surface + endpoint wrapper composition.
48. `lib/server/hyphen/fetch-executor.ts` helper-boundary split
   - Added `lib/server/hyphen/fetch-executor.helpers.ts` for date/year parsing, detail-key extraction, list merge, and medication probe-window helpers.
   - Reduced `lib/server/hyphen/fetch-executor.ts` to orchestration flow + failure policy handling.
   - Preserved endpoint call order and partial-failure semantics while lowering core executor size.
49. `lib/rnd/module07-biosensor-genetic-integration/mvp-engine.ts` runtime boundary split
   - Added `lib/rnd/module07-biosensor-genetic-integration/mvp-engine.shared.ts` for deterministic run-id/source-map/group/sort/source-summary helpers.
   - Added `lib/rnd/module07-biosensor-genetic-integration/mvp-engine.artifacts.ts` for session artifact payload/evidence/lineage construction.
   - Reduced `mvp-engine.ts` to input validation + wiring/orchestration loop while preserving deterministic output contracts.
50. Agent/audit script boundary split + encoding guard hardening
   - Added `scripts/lib/encoding-audit.cts` to centralize encoding/mojibake/BOM/line-ending checks used by `audit:encoding`.
   - Added `scripts/lib/route-method-export-audit.cts` so `audit:route-method-exports` and `audit:hotspots` share one method-export audit path.
   - Added `scripts/lib/route-guard-scan.cts` to share route-auth import and guard-token scan logic across `audit-hotspots` and `generate-api-guard-map`.
   - Added `scripts/lib/hotspot-paths.cts` to share hotspot file include/classification rules across hotspot reports.
   - Normalized BOM/CRLF remnants detected by the hardened encoding audit, so the repo returns to UTF-8 (no BOM) + LF baseline.
51. `lib/b2b/employee-sync-summary.ts` responsibility split
   - Moved NHIS summary patch fetch/cache/network orchestration into:
     - `lib/b2b/employee-sync-summary.fetch-patch.ts`
   - Moved medication/checkup normalized-data parser + patch-merge helpers into:
     - `lib/b2b/employee-sync-summary.normalizer.ts`
   - Kept `employee-sync-summary.ts` as public facade (`patchSummaryTargetsIfNeeded` + compatibility re-exports), preserving call sites while shrinking file size.
52. Agent report script write-flow normalization + hotspot audit flattening
   - Added `scripts/lib/write-if-changed.cts` to centralize idempotent UTF-8 report writes and stable relative-path logging.
   - Switched `generate-skill-catalog`, `generate-refactor-report`, `generate-function-hotspots`, and `generate-api-guard-map` to shared write helper.
   - Flattened `scripts/audit-hotspots.ts` by removing monolithic IIFE and reusing shared `hotspot-paths` + `route-guard-scan` + `route-method-export-audit` helpers.
   - Reduced script-level function hotspot pressure while preserving audit output and strict failure semantics.
53. Phone auth/link client API boundary consolidation
   - Added `lib/client/api-json.ts` for safe JSON response parsing (`ok/error` fallback) and HTTP result normalization.
   - Added `lib/client/phone-api.ts` for shared phone-domain client calls:
     - OTP send/verify (`/api/auth/phone/*`)
     - phone link (`/api/me/link-phone`)
     - phone status/unlink (`/api/me/phone-status`, `/api/me/unlink-phone`)
   - Replaced duplicated `fetch + text + JSON.parse + fallback` blocks in:
     - `components/order/hooks/usePhoneAndPassword.ts`
     - `app/me/phoneLinkSection.tsx`
     - `components/order/hooks/usePhoneStatus.ts`
     - `app/(orders)/my-orders/hooks/useLinkedPhoneStatus.ts`
     - `app/auth/phone/page.tsx`
   - Standardized response handling/error-shape assumptions for future session maintainability and safer endpoint change rollouts.
54. Phone profile surface deduplication + me client transport cleanup
   - Added shared phone display formatter `lib/client/phone-format.ts`.
   - Replaced duplicated phone display format implementations in:
     - `app/me/meClient.tsx`
     - `components/order/hooks/usePhoneStatus.ts`
     - `app/(orders)/my-orders/utils/formatPhoneDisplay.ts` (now re-exporting shared formatter)
   - Refactored `app/me/meClient.tsx` profile-save response handling to use `readApiHttpResult` instead of inline text/JSON parse branches.
   - Refactored `app/me/meClient.tsx` phone unlink flow to use shared `unlinkMyPhoneRequest` client API.
55. Role push subscription hook consolidation (`pharm` / `rider`)
   - Added `components/push/useRolePushSubscription.ts` as a shared hook for:
     - SW registration + VAPID mismatch handling
     - subscribe/status/unsubscribe orchestration
     - localStorage notify-off + `vapidKey` state sync
   - Replaced duplicated logic in:
     - `components/pharm/usePharmPushSubscription.ts`
     - `components/rider/useRiderPushSubscription.ts`
     with thin role-specific wrappers that inject endpoint/id-key config only.
   - Consolidated phone display formatting in `app/me/phoneLinkSection.tsx` to shared `lib/client/phone-format.ts` helper.
56. `app/me/meClient.tsx` profile mutation boundary split
   - Added `app/me/useMeProfileMutations.ts` to isolate:
     - profile image upload URL fetch + upload
     - profile save request/optimistic merge state
     - linked phone unlink request + loading/error state
   - Reduced `meClient.tsx` to page composition/state orchestration while preserving existing modal and section UI behavior.
   - Kept Korean-first user-facing error/loading messages in the extracted hook.
57. Hotspot report signal cleanup (`tmp/` exclusion)
   - Updated `scripts/lib/hotspot-paths.cts` to exclude `tmp/` from hotspot scans.
   - Prevented temporary/dev scratch files from polluting `FUNCTION_HOTSPOTS.md` and `audit:hotspots` ranking outputs.
58. `app/me/profileImageEditor.tsx` editor-core helper split
   - Added `app/me/profileImageEditor.helpers.ts` for reusable/pure editor internals:
     - zoom clamp + base-scale calculation
     - drag boundary clamp
     - editor/live preview style builders
     - image decode + canvas crop/render pipeline
   - Updated `profileImageEditor.tsx` to orchestrate UI/state only while delegating math/canvas logic to helpers.
   - Preserved existing crop behavior and modal UX while reducing single-component complexity for future sessions.
59. `components/push/useRolePushSubscription.ts` transport/check-flow split
   - Added `components/push/useRolePushSubscription.helpers.ts` and moved reusable blocks:
     - role payload + notify-off key/flag helpers
     - VAPID key read/store/mismatch logic
     - role subscribe/status/unsubscribe POST wrappers
     - permission gate helper + subscription status check runner
   - Reduced `useRolePushSubscription.ts` from monolithic transport+state flow to hook orchestration/state wiring.
   - Preserved existing route contracts and role ownership payload semantics (`pharm`/`rider`).
60. Push subscription runtime-safety + alert constant dedup
   - Added runtime capability guard (`isPushRuntimeAvailable`) in push helper flow to fail-safe when Notification/Push APIs are unavailable.
   - Applied runtime guard in subscribe/unsubscribe/check paths within `useRolePushSubscription`.
   - Moved duplicated Korean push alert messages to shared constant:
     - `DEFAULT_PUSH_ALERT_MESSAGES_KO` in `components/push/useRolePushSubscription.helpers.ts`
   - Updated role wrappers to reuse shared alerts:
     - `components/pharm/usePharmPushSubscription.ts`
     - `components/rider/useRiderPushSubscription.ts`
61. Hotspot script file-discovery dedup
   - Added `scripts/lib/hotspot-code-files.cts` to centralize hotspot 대상 코드 파일 수집/라인 집계 로직.
   - Updated `scripts/agent/generate-function-hotspots.cts` to reuse shared `listHotspotCodeFiles`.
   - Updated `scripts/agent/generate-refactor-report.cts` to reuse shared `buildHotspotCodeRows`.
   - Reduced duplicate scan/filter boilerplate so future report rule changes can be done in one module.
62. `lib/notification/subscriptions.ts` push subscription storage boundary split
   - Added `lib/notification/subscriptions.shared.ts` and moved shared DB/log orchestration:
     - role-scope where builders (`orderId` / `pharmacyId` / `riderId`)
     - scoped save/remove/status helpers
     - upsert/delete + status logging primitives
   - Reduced `subscriptions.ts` to role-specific public facade wrappers only (existing export API preserved).
   - Removed repeated role-specific Prisma where/upsert boilerplate, lowering future maintenance risk when push subscription schema/telemetry changes.
63. `scripts/audit-hotspots.ts` audit boundary split
   - Added `scripts/lib/hotspot-report.cts` for reusable hotspot section construction/printing.
   - Added `scripts/lib/hotspot-audit-checks.cts` for:
     - critical guard token checks
     - unexpected session-route checks
     - route-method export audit result rendering
   - Reduced `scripts/audit-hotspots.ts` to scanning + orchestration shell, preserving output format and fail-on-violation semantics.
64. `scripts/agent/generate-api-guard-map.cts` generation boundary split
   - Added `scripts/lib/guard-map.cts` for route entry scan/classification grouping and markdown section rendering.
   - Reduced `generate-api-guard-map.cts` to strict-mode policy + file write orchestration.
   - Preserved existing guard-map summary/section format and strict failure conditions while lowering entry-script complexity.
65. `scripts/agent/generate-skill-catalog.cts` generation boundary split
   - Added `scripts/lib/skill-catalog.cts` for recursive skill file scan, frontmatter parsing, and markdown row rendering.
   - Reduced `generate-skill-catalog.cts` to root validation + write orchestration only.
   - Preserved existing catalog format/output while lowering entry-script complexity for future maintenance.
66. `lib/b2b/report-payload.ts` medication history boundary split
   - Added `lib/b2b/report-payload-medication.ts` for:
     - raw-treatment to normalized medication row bridge
     - medication row quality/date ranking and visit dedupe
     - recent history backfill query orchestration (`b2bHealthDataSnapshot`)
   - Reduced `report-payload.ts` to source loading + payload assembly orchestration by delegating medication fallback logic.
   - Preserved payload contract while shrinking main report-payload runtime surface.
67. `lib/b2b/report-payload-health.ts` boundary split (facade + domain modules)
   - Added `lib/b2b/report-payload-health-metrics.ts` for metric/unit normalization and health metric extraction.
   - Added `lib/b2b/report-payload-health-medication.ts` for medication container parsing + visit-level consolidation.
   - Added `lib/b2b/report-payload-health-fetch.ts` for fetch partial/failed-target parsing.
   - Reduced `report-payload-health.ts` to stable re-export facade to preserve call sites while clarifying module responsibilities.
68. Push subscribe route boundary split (`lib/server/push-subscribe-route.ts`)
   - Added `lib/server/push-subscribe-parse.ts`:
     - role-specific request body schemas (`customer` / `pharm` / `rider`) with explicit `zod` validation
     - reusable parse helpers and payload types shared across subscribe/status/unsubscribe routes.
   - Added `lib/server/push-subscribe-auth.ts`:
     - shared auth wrappers for `requireCustomerOrderAccess` / `requirePharmSession` / `requireRiderSession`
     - generic parse+authorize+execute route runner (`runParsedRoute`) for consistent error flow.
   - Reduced `push-subscribe-route.ts` to route orchestration + role action handlers while preserving existing response contracts and guard usage.
69. Push detach role-scope safety hardening (`lib/server/push-detach-route.ts`)
   - Removed ambiguous branch where `pharm`/`rider` requests with `orderId` could enter order-scoped delete flow.
   - Enforced explicit role handling:
     - `customer`: `orderId` required + ownership guard + scoped remove
     - `pharm`/`rider`: role guard + endpoint+role scoped remove
     - empty role: endpoint all-role detach
   - Simplified nested condition tree into early-return role blocks to reduce future regression risk.
70. NHIS fetch-route helper boundary split (`lib/server/hyphen/fetch-route-helpers.ts`)
   - Added `lib/server/hyphen/fetch-route-constants.ts` for stable NHIS auth/session error-code constants.
   - Added `lib/server/hyphen/fetch-route-types.ts` for fetch-route orchestration/persist type contracts.
   - Added `lib/server/hyphen/fetch-route-persist.ts` for:
     - AI summary enrichment safe wrapper
     - fetch-attempt logging safe wrapper
     - failed-code normalization + failed-status derivation
     - execute+persist orchestration under fetch dedupe key
   - Reduced `fetch-route-helpers.ts` to request parsing/context preparation + failed-response shaping while preserving existing exports.
71. Module05 optimization contracts boundary split (`lib/rnd/module05-optimization/contracts.ts`)
   - Added `lib/rnd/module05-optimization/contracts.model.ts` for constants + all type contracts.
   - Added `lib/rnd/module05-optimization/contracts.guards.ts` for runtime validation/assert guards.
   - Reduced `contracts.ts` to stable re-export surface to preserve existing imports.
   - Preserved all public validator/type exports while isolating model vs guard responsibilities.
72. Module04 efficacy contracts boundary split (`lib/rnd/module04-efficacy-quantification/contracts.ts`)
   - Added `lib/rnd/module04-efficacy-quantification/contracts.model.ts` for constants + all type contracts.
   - Added `lib/rnd/module04-efficacy-quantification/contracts.guards.ts` for runtime validation/assert guards.
   - Reduced `contracts.ts` to stable re-export surface to preserve existing imports.
   - Preserved all public validator/type exports while isolating model vs guard responsibilities.
73. Module07 biosensor/genetic contracts boundary split (`lib/rnd/module07-biosensor-genetic-integration/contracts.ts`)
   - Added `lib/rnd/module07-biosensor-genetic-integration/contracts.model.ts` for constants + all type contracts.
   - Added `lib/rnd/module07-biosensor-genetic-integration/contracts.guards.ts` for runtime validation/assert guards.
   - Reduced `contracts.ts` to stable re-export surface to preserve existing imports.
   - Preserved all public validator/type exports while isolating model vs guard responsibilities.
74. Module03 personal-safety contracts boundary split (`lib/rnd/module03-personal-safety/contracts.ts`)
   - Added `lib/rnd/module03-personal-safety/contracts.model.ts` for constants + all type contracts.
   - Added `lib/rnd/module03-personal-safety/contracts.guards.ts` for runtime validation/assert guards.
   - Reduced `contracts.ts` to stable re-export surface to preserve existing imports.
   - Preserved all public validator/type exports while isolating model vs guard responsibilities.
75. Module02 data-lake contracts boundary split (`lib/rnd/module02-data-lake/contracts.ts`)
   - Added `lib/rnd/module02-data-lake/contracts.model.ts` for constants + type contracts + record-id builder utilities.
   - Added `lib/rnd/module02-data-lake/contracts.guards.ts` for runtime validation/assert guards.
   - Reduced `contracts.ts` to stable re-export surface to preserve existing imports.
   - Preserved all public validator/type exports while isolating model vs guard responsibilities.
76. Module06 closed-loop contracts validators boundary split (`lib/rnd/module06-closed-loop-ai/contracts-validators.ts`)
   - Added `lib/rnd/module06-closed-loop-ai/contracts-validators-loop-input.ts` for loop-input payload guards and assert helpers.
   - Added `lib/rnd/module06-closed-loop-ai/contracts-validators-loop-output.ts` for loop-output payload guards and assert helpers.
   - Reduced `contracts-validators.ts` to stable re-export surface while preserving public validator exports.
   - Kept primitive/enum validators in `contracts-validators-primitives.ts` and clarified validator module responsibilities for future sessions.
77. Module05 optimization scaffold boundary split (`lib/rnd/module05-optimization/scaffold.ts`)
   - Added `lib/rnd/module05-optimization/scaffold.fixture-data.ts` for deterministic scaffold fixture construction (input/output/trace logs).
   - Added `lib/rnd/module05-optimization/scaffold.assert.ts` for cross-payload integrity assertions and shared ISO datetime guard.
   - Added `lib/rnd/module05-optimization/scaffold.types.ts` for scaffold bundle contract type.
   - Reduced `scaffold.ts` to orchestration-only entry surface while preserving existing exports (`buildModule05ScaffoldBundle`, `assertModule05ScaffoldBundle`).
78. Wellness data-loader boundary split (`lib/wellness/data-loader.ts`)
   - Added `lib/wellness/data-loader-template.ts` for B2B survey template projection logic (common/section/question catalog mapping).
   - Added `lib/wellness/data-template-types.ts` for reusable survey template contracts.
   - Reduced `data-loader.ts` to JSON schema parse/cache orchestration + template loader entry while preserving public APIs.
   - Replaced broken mojibake placeholders/description copy in template assembly with Korean-first user-facing messages.
79. Wellness template mapper boundary split (`lib/wellness/data-loader-template.ts`)
   - Added `lib/wellness/data-loader-template.mappers.ts` for isolated common question/section/catalog mapping helpers.
   - Reduced `data-loader-template.ts` to template assembly orchestration (`C27` 정책값 + version/rules wiring) only.
   - Preserved `buildWellnessTemplateForB2b` public API and mapping behavior while making change impact points explicit.
80. Wellness template mapper submodule split (`lib/wellness/data-loader-template.mappers.ts`)
   - Added `lib/wellness/data-loader-template.common.ts` for common question option/field/placeholder/constraint mapping.
   - Added `lib/wellness/data-loader-template.sections.ts` for section question variant mapping and section catalog projection.
   - Added `lib/wellness/data-loader-template.version.ts` and `data-loader-template.shared.ts` for version policy + shared question type normalization.
   - Reduced `data-loader-template.mappers.ts` to barrel export surface so mapper composition changes can be localized.
81. Profile image editor UI block split (`app/me/profileImageEditor.tsx`)
   - Added `app/me/profileImageEditor.previewPane.tsx` for crop-preview and live-preview UI rendering.
   - Added `app/me/profileImageEditor.controls.tsx` for zoom/reset/cancel/apply control block rendering.
   - Reduced `profileImageEditor.tsx` to interaction/state orchestration while preserving drag/zoom/crop behavior.
   - Normalized user-facing editor copy in Korean for clearer interaction hints and loading/apply states.
82. Me profile section UI boundary split (`app/me/meClient.tsx`)
   - Added `app/me/meProfileSection.tsx` to isolate profile card rendering (image picker + nickname/email/phone rows).
   - Replaced direct DOM id click with local ref-driven image file input trigger for clearer component ownership.
   - Reduced `meClient.tsx` to page-level state/mutation/modal orchestration while preserving existing profile-edit flow.
   - Normalized top-level me-page/profile labels to Korean-first copy.
83. Profile image editor controller boundary split (`app/me/profileImageEditor.tsx`)
   - Added `app/me/useProfileImageEditorController.ts` for crop state, wheel/gesture zoom, drag movement, and apply pipeline orchestration.
   - Reduced `profileImageEditor.tsx` to modal shell + draggable container wiring + section composition.
   - Kept crop math and canvas output logic in `profileImageEditor.helpers.ts` and UI rendering in preview/controls components.
   - Preserved editor behavior while making state-transition and gesture logic easier to test/patch in isolation.
84. Assess C-section boundary split (`app/assess/components/CSection.tsx`)
   - Added `app/assess/components/cSection.helpers.ts` for:
     - C-section result payload normalization
     - question-type lookup + answer normalization by question type
     - option-grid column policy helper
   - Added `app/assess/components/CSectionOptionGrid.tsx` to isolate option button list rendering and selection UI states.
   - Reduced `CSection.tsx` to state/submission orchestration and replaced duplicated overlay markup with shared `LoadingOverlay`.
   - Normalized C-section loading/error/skip user-facing copy to Korean-first text for consistent UX.
85. Google translate gate script boundary split (`components/common/GoogleTranslateGate.tsx`)
   - Moved long inline translator orchestrator script into `public/scripts/google-translate-orchestrator.js`.
   - Reduced `GoogleTranslateGate.tsx` to route gate + script loader shell only.
   - Preserved disabled route policy (`/en/check-ai`) and existing runtime translation behavior.
   - Improved maintainability by isolating large imperative browser/runtime logic from React component render flow.
86. Test report page visual block split (`app/test/page.tsx`)
   - Added `app/test/reportBlocks.tsx` to isolate reusable report visual blocks:
     - `Gauge`, `BarRow`, `Donut`, `Legend`, `BigChip`, `PlanCard`, `MiniStat`
   - Reduced `app/test/page.tsx` to A4 report fixture/layout orchestration and section composition.
   - Removed unused in-file helpers (`Sparkline`, `Badge`) and icon imports to lower maintenance noise.
   - Normalized report fixture/user-facing copy to Korean-first text for clearer QA review context.
87. Chat profile modal form boundary split (`app/chat/components/ProfileModal.tsx`)
   - Added `app/chat/components/ProfileModalForm.tsx` to isolate profile field UI composition:
     - base fields (name/age/sex/height/weight)
     - boolean selects (임신/수유, 카페인 민감)
     - chip sections (복용 약/질환/알레르기/목표/식이 제한)
   - Reduced `ProfileModal.tsx` to modal shell + drag/reset/save orchestration and portal handling.
   - Kept state ownership in `useProfileModalState.ts` and passed typed `setField` callback to form section.
   - Normalized modal/reset/action labels to Korean-first copy.
88. Testimonials carousel boundary split (`app/(components)/testimonialsSection.tsx`)
   - Added `app/(components)/useTestimonialsCarousel.ts` for:
     - infinite-loop translate track state
     - resize/font/visibility sync and progress computation
     - pointer drag and wheel interaction orchestration
   - Added `app/(components)/testimonialsCarouselViewport.tsx` to isolate viewport/track/progress composition.
   - Added `app/(components)/testimonialCard.tsx`, `testimonialsProgressBar.tsx`, and `testimonials.types.ts` to separate card/progress/type concerns.
   - Reduced `testimonialsSection.tsx` to section shell + heading + hook wiring, lowering future UI/policy change impact radius.
89. Assess C-section controller split + Korean copy recovery (`app/assess/components/CSection.tsx`)
   - Added `app/assess/components/useCSectionController.ts` to isolate C-section state machine:
     - persisted state hydration/save/bookmark handling
     - progress emission + previous-step registration
     - transition/submit orchestration and loading notifier integration
   - Reduced `CSection.tsx` to UI shell + option grid composition only.
   - Verified Korean copy source consistency in `app/assess/data/c-options.ts` and `app/assess/data/c-bank.ts`, and centralized C-section loading/error/skip labels in the controller copy map.
   - Preserved existing result normalization and submit endpoint contract (`/api/c-section-score`).
90. Google translate orchestrator de-IIFE split (`public/scripts/google-translate-orchestrator.js`)
   - Replaced monolithic anonymous IIFE block with top-level named function boundaries.
   - Added idempotency guards for boot/history patch/observer registration (`__wbTranslateOrchestratorBooted`, `__wbTranslateHistoryPatched`, `__wbTranslateObserversStarted`).
   - Kept existing translate trigger flow, route mode sync, and observer-driven retranslate behavior.
   - Removed single 441-line anonymous runtime hotspot to improve future debugging and incremental edits.
91. Me account modal state boundary split + locale copy recovery (`app/me/*`)
   - Added `app/me/useEmailChangeModalState.ts`:
     - 이메일 OTP 발송/검증 요청 흐름
     - 쿨다운 타이머/입력 검증/ESC 닫기 제어
   - Added `app/me/useNicknameChangeModalState.ts`:
     - 닉네임 중복검사/저장 요청 흐름
     - 입력 유효성/저장 가능 상태/ESC 닫기 제어
   - Added `app/me/modalSpinner.tsx` and reused in `emailChangeModal.tsx`/`nicknameChangeModal.tsx` to remove duplicated spinner SVG blocks.
   - Added `app/me/usePhoneLinkSectionState.ts` and reduced `phoneLinkSection.tsx` to UI shell + field wiring only.
   - Updated `app/me/phoneLinkSection.tsx` to reuse `modalSpinner` and restore Korean OTP UX copy/messages.
   - Reduced `emailChangeModal.tsx` and `nicknameChangeModal.tsx` to modal shell + form composition while moving mutation state into hooks.
   - Restored Korean-first user-facing copy on me profile/account modal surfaces (`meClient.tsx`, `emailChangeModal.tsx`, `nicknameChangeModal.tsx`) for readability and locale consistency.
92. Assess flow hook boundary split (`app/assess/page.tsx`)
   - Added `app/assess/useAssessFlow.ts` and moved assess flow state machine:
     - section(A/B/C/DONE) transition and go-back/reset policy
     - answer progression + next-question selection + progress/loading copy
     - persisted snapshot hydrate/save + category fetch + C-section submit wiring
   - Reduced `app/assess/page.tsx` to route-level render composition (`IntroSection`, `QuestionSection`, `CSectionWrapper`, `DoneSection`, `ConfirmResetModal`).
   - Preserved existing C-section persistence key usage (`ASSESS_C_PERSIST_KEY`) and `/api/assess/save` payload contract.
   - Lowered future change impact by isolating flow control from presentation layout.
93. My-data page section composition split (`app/my-data/page.tsx`)
   - Added `app/my-data/myDataPageSections.tsx` and extracted major view blocks:
     - lock notice, header/status pills, metrics
     - account/session-profile/orders/assessment/check-ai/chat sections
   - Reduced `app/my-data/page.tsx` to route-level guard + data load + section composition only.
   - Preserved existing collection query path (`loadMyDataCollections`) and normalization usage (`normalizeAssessmentResult`, `normalizeCheckAiResult`) through section module wiring.
   - Improved follow-up change safety by separating data orchestration from large UI detail blocks.
94. Module02 KPI rollup runner orchestration split (`scripts/rnd/module02/evaluate-kpi-rollup.ts`)
   - Extracted path/output resolution and module execution flow into dedicated helpers:
     - `resolveRollupPaths`, `ensureOutputDirs`, `runAllModuleEvaluations`
   - Extracted evaluation artifact parsing and KPI derivation into:
     - `readModuleEvaluationOutputs`, `buildKpiBundle`
   - Reduced `main` from monolithic orchestration to high-level wiring (args -> paths -> module runs -> KPI bundle -> rollup emit).
   - Preserved output schema/command trace semantics while making KPI mapping updates easier to review in future sessions.
95. Module03 scheduler handoff validation orchestration split (`scripts/rnd/module03/run-scheduler-handoff-validation.ts`)
   - Added explicit helper boundaries:
     - `assertSchedulerRunnersAvailable`, `buildValidationPaths`, `resolveValidationInput`
     - `runDeploymentBundleGeneration`, `runInfraBindingGeneration`
     - `toRuntimeEnvOverrides`, `runDryRunValidation`, `buildValidationSummary`
   - Reduced `main` to high-level wiring (parse -> path/input resolve -> bundle/infra/dry-run -> summary emit).
   - Preserved strict-env behavior, required env binding flow, and summary JSON schema while making each execution phase independently reviewable.
   - Function hotspot impact: `main` dropped below script top hotspot threshold in `FUNCTION_HOTSPOTS.md`.
96. Module03 scheduler production gate orchestration split (`scripts/rnd/module03/run-scheduler-production-gate.ts`)
   - Added orchestration helper boundaries:
     - `assertProductionGateRunnersAvailable`, `buildProductionGatePaths`
     - `buildHandoffArgs`, `runHandoffValidation`
     - `buildReadinessArgs`, `runReadinessValidation`
     - `buildProductionGateArtifact`
   - Split argument parsing sub-helpers:
     - `parseInputPath`, `parseSchedulerName`, `parseEnvironmentArgs`
     - `parseOptionalSampleRowCount`, `parseValidatedKeyValuePairs`
   - Reduced `main` to high-level gate flow wiring and preserved existing fail/pass semantics and artifact schema.
   - Function hotspot impact: `main`/`parseArgs` dropped out of `FUNCTION_HOTSPOTS.md` Top script function list.
97. Module03 scheduler readiness check builder split (`scripts/rnd/module03/scheduler-readiness-checks.ts`)
   - Added explicit check-group helpers:
     - `addExecutionChecks`, `addInputAndEnvironmentChecks`
     - `addRequiredEnvCoverageChecks`, `addSecretRefChecks`
     - `addSchedulerTemplateCheck`
   - Introduced shared `ReadinessCheckContext` so precomputed sets/maps are reused across check groups.
   - Reduced `buildReadinessChecks` to orchestration-only composition while preserving readiness check IDs/detail text and pass/fail semantics.
   - Function hotspot impact: monolithic `buildReadinessChecks` replaced by smaller grouped functions in `FUNCTION_HOTSPOTS.md`.
98. Module03 infra-binding bundle parser split (`scripts/rnd/module03/generate-scheduler-infra-binding.ts`)
   - Split monolithic `parseSchedulerDeploymentBundle` into explicit helper boundaries:
     - identity/object guards (`assertBundleIdentity`, `requireBundleObject`)
     - array/template parsers (`parseStringArrayOrThrow`, `parseBindingsTemplateOrThrow`)
     - section parsers (`parseSchedulerSection`, `parseWarehouseSection`, `parseSecretsSection`, `parseArtifactsSection`, `parseVerificationSection`)
   - Reduced parse function responsibility to high-level bundle composition while preserving identity checks and existing error semantics.
   - Function hotspot impact: `parseSchedulerDeploymentBundle` dropped out of the script hotspot list in `FUNCTION_HOTSPOTS.md`.
99. Module03 dry-run infra parser + scheduler arg builder split (`scripts/rnd/module03/run-scheduler-dry-run-window.ts`)
   - Split monolithic infra-binding parser into explicit helpers:
     - identity/object guards (`assertInfraBindingIdentity`, `requireInfraSectionObject`)
     - section parsers (`parseInfraSchedulerSection`, `parseInfraSecretsSection`, `parseInfraWarehouseSection`, `parseInfraArtifactsSection`, `parseInfraVerificationSection`)
   - Split scheduler argument assembly into explicit helpers:
     - artifact path resolution (`resolveSchedulerArtifactPaths`)
     - base args + optional policy args (`buildBaseSchedulerArgs`, `applyRetentionMonthsArg`, `applyRequiredEnvArg`, `applyFailureWebhookArgs`)
   - Reduced `parseInfraBindingArtifact` and `buildSchedulerArgs` to orchestration-only composition while preserving strict-env, retention-months, and failure-webhook behavior.
   - Function hotspot impact: both functions dropped out of `FUNCTION_HOTSPOTS.md`; file now shows only smaller `main` function entry.
100. Module03 deployment bundle builder split (`scripts/rnd/module03/generate-scheduler-deployment-bundle.ts`)
   - Split monolithic `buildBundle` into explicit helper boundaries:
     - command derivation (`buildCommandTemplate`, `resolveDeploymentRequiredEnvKeys`)
     - section builders (`buildWarehouseSection`, `buildSecretsSection`, `buildArtifactsSection`, `buildVerificationSection`)
   - Reduced `buildBundle` to orchestration-only composition while preserving command template semantics and bundle output schema.
   - Function hotspot impact: `buildBundle` dropped out of `FUNCTION_HOTSPOTS.md`; script now retains only `parseArgs` as top function hotspot.
101. Module03 handoff validation parser/summary split (`scripts/rnd/module03/run-scheduler-handoff-validation.ts`)
   - Split parser responsibilities into explicit validation helpers:
     - bundle identity/sections (`assertDeploymentBundleIdentity`, `parseDeploymentBundleSecrets`, `parseDeploymentBundleVerification`)
     - dry-run identity/sections (`assertDryRunReportIdentity`, `parseDryRunExpectedOutputs`, `parseDryRunVerificationSection`, `parseDryRunSection`)
   - Split argument parsing and summary assembly boundaries:
     - arg helpers (`parseWindowEndArg`, `parseOutDirArg`, `parseInputPathArg`, `parseSampleRowCountArg`, `parseSchedulerNameArg`, `parseEnvironmentArg`)
     - summary section helpers (`buildSummaryInputSection`, `buildSummarySecretsSection`, `buildSummaryArtifactsSection`, `buildSummaryVerificationSection`)
   - Function hotspot impact: `parseArgs` and `buildValidationSummary` dropped out of `FUNCTION_HOTSPOTS.md`.
102. Module03 deployment bundle parseArgs split (`scripts/rnd/module03/generate-scheduler-deployment-bundle.ts`)
   - Split `parseArgs` into arg-specific helpers:
     - `parseGeneratedAtArg`, `parseCadenceCronArg`, `parseTimezoneArg`, `parseRetentionMonthsArg`
     - `parseSchemaMapPathArg`, `parseSqlTemplatePathArg`
     - `parseFailureWebhookEnvKeyArg`, `parseFailureWebhookTimeoutEnvKeyArg`
   - Preserved file-existence validation, default fallback behavior, and env-key validation semantics.
   - Function hotspot impact: `parseArgs` dropped out of `FUNCTION_HOTSPOTS.md`.
103. Module03 scheduler orchestration flow split (`scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly.ts`)
   - Split argument parsing into reusable validators:
     - `assertInputSourceProvided`, `parseOptionalExistingFileArg`, `parseRequiredExistingFileArg`
     - `parseFailureWebhookUrlArg`, `parseFailureWebhookTimeoutArg`
   - Split runtime orchestration boundaries:
     - execution helpers (`warnWhenInputTakesPrecedence`, `runArchiveAndReadResults`)
     - handoff builders (`buildHandoffArtifact`, `buildHandoffLatestPointer`, `buildHandoffOutputs`)
     - output helpers (`writeHandoffOutputs`, `printSchedulerSummary`)
   - Function hotspot impact: `parseArgs`, `runScheduler`, and `buildHandoffOutputs` dropped out of `FUNCTION_HOTSPOTS.md`.
104. Module03 dry-run runner execution error split (`scripts/rnd/module03/run-scheduler-dry-run-window.ts`)
   - Split `runSchedulerDryRun` internals into explicit execution/error helpers:
     - runner precheck (`assertSchedulerRunnerExists`)
     - process output normalization (`toProcessOutput`)
     - failure formatting (`buildDryRunExecutionError`)
   - Preserved dry-run command execution semantics and error detail payload (command, exitCode, stdout, stderr).
   - Function hotspot impact: `runSchedulerDryRun` dropped out of `FUNCTION_HOTSPOTS.md`; only small `main` remains for this script.
105. Module02 KPI rollup KPI/build orchestration split (`scripts/rnd/module02/evaluate-kpi-rollup.ts`)
   - Split monolithic KPI builder into explicit per-KPI helpers:
     - `buildKpi01`, `buildKpi02`, `buildKpi03`, `buildKpi04`, `buildKpi07`
     - `buildKpi05Breakdown`, `buildKpi05Measurement`, `buildKpi06`, `buildMeasuredKpis`
   - Split rollup assembly boundaries:
     - run timing (`resolveRunTimestamps`)
     - artifact sections (`buildEnvironmentSnapshot`, `buildModuleArtifactEntries`, `buildRollupSummary`, `buildRollupReport`)
   - Split module runner error formatting (`formatModuleRunError`) from execution flow.
   - Function hotspot impact: `buildKpiBundle`/`main`/`runModuleEvaluation` dropped out of `FUNCTION_HOTSPOTS.md` for this file.
106. Module03 monthly archive orchestration + retention split (`scripts/rnd/module03/archive-adverse-event-evaluation-monthly.ts`)
   - Split monolithic archive flow into explicit stages:
     - execution paths + entry/build/write/log (`buildArchiveExecutionPaths`, `buildArchiveEntry`, `buildNextManifest`, `writeArchiveOutputs`, `logArchiveResults`)
   - Split retention policy internals:
     - cutoff calculation + partition + prune + empty-dir cleanup (`cutoffMonthStartUtcMs`, `partitionEntriesByCutoffMonth`, `pruneArchivedReports`, `pruneEmptyMonthDirectories`)
   - Split ops output parsing and runner failure formatting:
     - identity/report parsing (`assertOpsOutputIdentity`, `parseOpsOutputReport`)
     - runner precheck/args/error (`assertOpsRunnerExists`, `buildOpsRunnerArgs`, `formatOpsEvaluationError`)
   - Function hotspot impact: `main`, `applyRetentionPolicy`, `readOpsOutput`, `parseArchiveEntry`, `runOpsEvaluation` dropped out of `FUNCTION_HOTSPOTS.md`.
107. Module03 handoff validation artifact module extraction (`scripts/rnd/module03/run-scheduler-handoff-validation.ts`)
   - Extracted deployment/dry-run artifact parsing and summary section builders into:
     - `scripts/rnd/module03/scheduler-handoff-validation-artifacts.ts`
   - Kept runner orchestration file focused on:
     - args/path/input resolution
     - deployment/infra/dry-run execution wiring
     - final summary assembly/write
   - Preserved output schema and parser validation semantics by passing expected identity (`moduleId`, `kpiId`) into extracted parsers.
   - Hotspot impact: script line size reduced from 769 to 492 (`audit:hotspots`), improving follow-up session navigation.
108. Module03 infra-binding artifact module extraction (`scripts/rnd/module03/generate-scheduler-infra-binding.ts`)
   - Extracted deployment-bundle parser, binding-source loaders/merge, and infra-artifact builders into:
     - `scripts/rnd/module03/scheduler-infra-binding-artifacts.ts`
   - Kept orchestration file focused on:
     - args parsing
     - bundle load + parser invocation
     - file/CLI binding merge wiring
     - artifact serialization/output routing
   - Preserved validation/error semantics for bundle identity, env-key hygiene, duplicate binding conflicts, and placeholder-secret policy.
   - Hotspot impact: `generate-scheduler-infra-binding.ts` dropped out of function hotspot list; file size reduced from 596 to 189 lines (`audit:hotspots`).
109. Module02 KPI rollup artifact module extraction (`scripts/rnd/module02/evaluate-kpi-rollup.ts`)
   - Extracted KPI contracts and KPI computation helpers into:
     - `scripts/rnd/module02/kpi-rollup-artifacts.ts`
   - Kept orchestration file focused on:
     - CLI parsing and output path resolution
     - module evaluation runner execution
     - rollup artifact assembly/write
   - Preserved KPI semantics by reusing existing builder logic and importing `buildKpiBundle` / `buildRollupSummary`.
   - Hotspot impact: `evaluate-kpi-rollup.ts` file size reduced from 714 to 352 lines (`audit:hotspots`).
110. Module03 production-readiness validator main split (`scripts/rnd/module03/validate-scheduler-production-readiness.ts`)
   - Split monolithic `main` into explicit stage helpers:
     - source load (`loadReadinessSource`)
     - check computation (`computeReadinessChecks`)
     - report assembly (`buildReadinessReport`)
     - output/exit policy (`handleReadinessExit`)
   - Preserved pass/fail semantics, report schema, and failing-check exit code behavior.
   - Function hotspot impact: `validate-scheduler-production-readiness.ts` `main` dropped out of `FUNCTION_HOTSPOTS.md`.
111. Module03 dry-run artifact helper extraction (`scripts/rnd/module03/run-scheduler-dry-run-window.ts`)
   - Extracted infra-binding parser, scheduler arg-composition, and output helper logic into:
     - `scripts/rnd/module03/scheduler-dry-run-artifacts.ts`
   - Kept dry-run runner file focused on:
     - scheduler process execution and error formatting
     - orchestration/report write flow
   - Preserved strict-env and required-env behavior, retention-months propagation, failure-webhook env handling, and dry-run report schema.
   - Hotspot impact: `run-scheduler-dry-run-window.ts` file size reduced and follow-up navigation now centers on one orchestration file + one artifact helper module.
112. Module03 infra-binding secret-binding module extraction (`scripts/rnd/module03/scheduler-infra-binding-artifacts.ts`)
   - Extracted secret-binding parse/merge/conflict logic into:
     - `scripts/rnd/module03/scheduler-secret-bindings.ts`
   - Kept infra-binding artifact file focused on:
     - deployment-bundle parsing
     - required-binding validation and infra artifact composition
   - Preserved secret-binding file schema support (object map or array), duplicate/conflict validation, CLI `KEY=secretRef` parsing, and merge precedence behavior.
   - Hotspot impact: `scheduler-infra-binding-artifacts.ts` line count reduced; binding workflow is now isolated for follow-up changes.
113. Module03 monthly archive artifact module extraction (`scripts/rnd/module03/archive-adverse-event-evaluation-monthly.ts`)
   - Extracted monthly archive parser/build/retention logic into:
     - `scripts/rnd/module03/monthly-archive-artifacts.ts`
   - Kept archive runner file focused on:
     - CLI argument parsing + ops runner execution
     - artifact orchestration + result logging
   - Preserved archive semantics for:
     - ops output identity/report parsing
     - entry upsert and retention pruning
     - manifest/latest artifact write schema
   - Hotspot impact: `archive-adverse-event-evaluation-monthly.ts` line count reduced, so follow-up edits can target orchestration vs artifact-policy modules independently.
114. Module03 monthly archive retention/type split (`scripts/rnd/module03/monthly-archive-artifacts.ts`)
   - Extracted retention policy and prune helpers into:
     - `scripts/rnd/module03/monthly-archive-retention.ts`
   - Extracted archive contract types/constants into:
     - `scripts/rnd/module03/monthly-archive-types.ts`
   - Kept artifact helper file focused on:
     - ops output + manifest parse
     - archive path/entry/next-manifest/latest write composition
   - Preserved retention behavior (cutoff month calculation, safe in-directory prune, empty month dir cleanup, entry upsert ordering) via dedicated retention module.
   - Hotspot impact: archive policy responsibilities are now split into parser/build (`monthly-archive-artifacts.ts`) and retention policy (`monthly-archive-retention.ts`) for faster follow-up navigation.
115. Module03 dry-run artifact module layered split (`scripts/rnd/module03/scheduler-dry-run-artifacts.ts`)
   - Extracted dry-run contract types/constants into:
     - `scripts/rnd/module03/scheduler-dry-run-types.ts`
   - Extracted CLI/infra parser helpers into:
     - `scripts/rnd/module03/scheduler-dry-run-infra.ts`
   - Extracted scheduler arg planning/output helpers into:
     - `scripts/rnd/module03/scheduler-dry-run-plan.ts`
   - Converted `scheduler-dry-run-artifacts.ts` into stable export surface so existing callers keep the same import path.
   - Preserved strict-env validation, retention-months propagation, failure-webhook env mapping, and expected-output verification behavior while improving follow-up session navigation.
116. Module03 handoff summary builder extraction (`scripts/rnd/module03/run-scheduler-handoff-validation.ts`)
   - Moved handoff summary assembly from runner file into:
     - `scripts/rnd/module03/scheduler-handoff-validation-artifacts.ts` (`buildValidationSummary`)
   - Kept runner file focused on:
     - args/path/input resolution
     - bundle/infra/dry-run execution orchestration
     - summary write/log
   - Preserved summary schema fields (`input`, `secrets`, `artifacts`, `verification`) and workspace-path normalization behavior while reducing orchestration-file complexity.
117. Module03 handoff artifact module layered split (`scripts/rnd/module03/scheduler-handoff-validation-artifacts.ts`)
   - Extracted handoff contract types into:
     - `scripts/rnd/module03/scheduler-handoff-validation-types.ts`
   - Extracted parser helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-parsers.ts`
   - Extracted summary composition helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-summary.ts`
   - Converted `scheduler-handoff-validation-artifacts.ts` into stable export surface to preserve existing caller imports.
   - Preserved deployment/dry-run identity checks and handoff summary output schema while making parser and summary changes independently maintainable.
118. Module03 handoff runner CLI/runtime split (`scripts/rnd/module03/run-scheduler-handoff-validation.ts`)
   - Extracted CLI parsing/default policy helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-cli.ts`
   - Extracted runtime flow helpers (runner availability, path/input resolution, deployment/infra/dry-run execution, env override shaping) into:
     - `scripts/rnd/module03/scheduler-handoff-validation-runtime.ts`
   - Reduced `run-scheduler-handoff-validation.ts` to high-level orchestration + summary write.
   - Preserved runtime behavior for strict-env propagation, secret-binding/env-value injection, and summary schema generation while improving follow-up navigation of execution stages.
119. Module03 production-gate layered split (`scripts/rnd/module03/run-scheduler-production-gate.ts`)
   - Extracted CLI parsing/default policy helpers into:
     - `scripts/rnd/module03/scheduler-production-gate-cli.ts`
   - Extracted runtime execution/path helpers into:
     - `scripts/rnd/module03/scheduler-production-gate-runtime.ts`
   - Extracted readiness parser + gate artifact builder into:
     - `scripts/rnd/module03/scheduler-production-gate-artifacts.ts`
   - Added shared production-gate contracts/constants in:
     - `scripts/rnd/module03/scheduler-production-gate-types.ts`
   - Reduced `run-scheduler-production-gate.ts` to orchestration-only flow while preserving handoff/readiness gate semantics and fail/pass artifact output behavior.
120. Module03 infra-binding artifact module layered split (`scripts/rnd/module03/scheduler-infra-binding-artifacts.ts`)
   - Extracted infra-binding contract types into:
     - `scripts/rnd/module03/scheduler-infra-binding-types.ts`
   - Extracted deployment-bundle parser helpers into:
     - `scripts/rnd/module03/scheduler-infra-binding-parsers.ts`
   - Extracted infra artifact builders into:
     - `scripts/rnd/module03/scheduler-infra-binding-builders.ts`
   - Kept `scheduler-infra-binding-artifacts.ts` as stable export surface and preserved existing caller import paths.
   - Preserved identity validation, secret binding requirement checks, placeholder-secret policy, and generated artifact schema while making parser vs builder modifications independently maintainable.
121. Module03 deployment-bundle layered split (`scripts/rnd/module03/generate-scheduler-deployment-bundle.ts`)
   - Extracted deployment-bundle contract types/constants into:
     - `scripts/rnd/module03/scheduler-deployment-bundle-types.ts`
   - Extracted CLI/default parser and validation helpers into:
     - `scripts/rnd/module03/scheduler-deployment-bundle-cli.ts`
   - Extracted command/section artifact builders into:
     - `scripts/rnd/module03/scheduler-deployment-bundle-artifacts.ts`
   - Reduced `generate-scheduler-deployment-bundle.ts` to orchestration-only flow (`parseArgs` -> `buildBundle` -> output write/stdout).
   - Preserved scheduler command-template composition, required env-key resolution, secret-binding template policy, and verification artifact schema while making CLI-policy and bundle-shape changes independently maintainable.
122. Module03 scheduler-orchestrator layered split (`scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly.ts`)
   - Extracted scheduler CLI/default parser and validation helpers into:
     - `scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-cli.ts`
   - Extracted handoff artifact/latest pointer builders and output helpers into:
     - `scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-artifacts.ts`
   - Extracted runtime orchestration helpers (input precedence warning, export/archive execution, env guard, output flow) into:
     - `scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-runtime.ts`
   - Extended shared scheduler types/constants in:
     - `scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-types.ts`
   - Reduced `orchestrate-adverse-event-evaluation-monthly.ts` to entry + failure-alert wrapping while preserving warehouse export resolution, archive evaluation invocation, handoff artifact schema, and failure alert behavior.
123. Module03 readiness-check layered split (`scripts/rnd/module03/scheduler-readiness-checks.ts`)
   - Extracted readiness contracts/options/context types into:
     - `scripts/rnd/module03/scheduler-readiness-checks.types.ts`
   - Extracted shared check helpers/context builder into:
     - `scripts/rnd/module03/scheduler-readiness-checks.shared.ts`
   - Extracted execution/input/environment check groups into:
     - `scripts/rnd/module03/scheduler-readiness-checks.execution.ts`
   - Extracted env coverage/secret hygiene/scheduler-template check groups into:
     - `scripts/rnd/module03/scheduler-readiness-checks.integrity.ts`
   - Reduced `scheduler-readiness-checks.ts` to orchestration entry + stable type export while preserving all readiness check IDs/messages and evaluation order.
124. Module03 export/archive reader layered split (`scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-export.ts`)
   - Extracted export runtime helpers into:
     - `scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-export-runtime.ts`
   - Extracted archive artifact reader/parser helpers into:
     - `scripts/rnd/module03/orchestrate-adverse-event-evaluation-monthly-archive-readers.ts`
   - Converted `orchestrate-adverse-event-evaluation-monthly-export.ts` into stable export surface to preserve existing caller imports.
   - Preserved export command template rendering, warehouse export command execution semantics, archive runner invocation/error formatting, and latest/manifest identity checks while making runtime vs parser changes independently maintainable.
125. Module03 monthly-archive artifact layered split (`scripts/rnd/module03/monthly-archive-artifacts.ts`)
   - Extracted ops output and archive manifest parser helpers into:
     - `scripts/rnd/module03/monthly-archive-parsers.ts`
   - Extracted archive path/entry/manifest/latest builder helpers into:
     - `scripts/rnd/module03/monthly-archive-builders.ts`
   - Converted `monthly-archive-artifacts.ts` into stable export surface to preserve existing caller imports.
   - Preserved ops output identity parsing, archive manifest validation, retention-policy integration, and latest/manifest write schema while making parser vs builder changes independently maintainable.
126. Module03 ops-source evaluator layered split (`scripts/rnd/module03/evaluate-adverse-event-count-from-source.ts`)
   - Extracted ops-schema/cli contracts/constants into:
     - `scripts/rnd/module03/evaluate-adverse-event-count-from-source-types.ts`
   - Extracted CLI/default parser and input/date validation into:
     - `scripts/rnd/module03/evaluate-adverse-event-count-from-source-cli.ts`
   - Extracted schema-map parser and row-to-sample mapper into:
     - `scripts/rnd/module03/evaluate-adverse-event-count-from-source-schema.ts`
   - Extracted output payload composition into:
     - `scripts/rnd/module03/evaluate-adverse-event-count-from-source-artifacts.ts`
   - Reduced `evaluate-adverse-event-count-from-source.ts` to orchestration-only flow while preserving schema identity checks, boolean-like mapping policy, sample-id generation, and output payload schema.
127. Module03 handoff runtime input/exec layered split (`scripts/rnd/module03/scheduler-handoff-validation-runtime.ts`)
   - Extracted handoff runtime constants/contracts into:
     - `scripts/rnd/module03/scheduler-handoff-validation-runtime-types.ts`
   - Extracted handoff input/path resolution helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-runtime-input.ts`
   - Extracted runner invocation/runtime env override helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-runtime-exec.ts`
   - Converted `scheduler-handoff-validation-runtime.ts` into stable export surface to preserve existing caller imports.
   - Preserved representative input generation, secret-binding/env-value precedence, deployment/infra/dry-run invocation semantics, and dry-run expected-output guard while isolating runtime stages for faster follow-up edits.
128. Module03 readiness-artifact parser/types layered split (`scripts/rnd/module03/scheduler-readiness-artifacts.ts`)
   - Extracted readiness artifact contracts/constants into:
     - `scripts/rnd/module03/scheduler-readiness-artifacts.types.ts`
   - Extracted handoff/infra parser and path resolver helpers into:
     - `scripts/rnd/module03/scheduler-readiness-artifacts.parsers.ts`
   - Converted `scheduler-readiness-artifacts.ts` into stable export surface to preserve existing caller imports.
   - Preserved handoff/infra identity validation, env-key/binding normalization rules, duplicate binding detection, and artifact path resolution policy while separating contracts from parser logic.
129. Module03 readiness-validator layered split (`scripts/rnd/module03/validate-scheduler-production-readiness.ts`)
   - Extracted validator contracts/constants into:
     - `scripts/rnd/module03/validate-scheduler-production-readiness-types.ts`
   - Extracted CLI/default parser and argument validation into:
     - `scripts/rnd/module03/validate-scheduler-production-readiness-cli.ts`
   - Extracted source loader and readiness-check computation into:
     - `scripts/rnd/module03/validate-scheduler-production-readiness-runtime.ts`
   - Extracted report builder and pass/fail exit policy into:
     - `scripts/rnd/module03/validate-scheduler-production-readiness-artifacts.ts`
   - Reduced `validate-scheduler-production-readiness.ts` to orchestration-only flow while preserving report schema, failing-check exit semantics, and output path policy.
130. Module03 archive-runner CLI/runtime layered split (`scripts/rnd/module03/archive-adverse-event-evaluation-monthly.ts`)
   - Extracted archive runner contracts/constants into:
     - `scripts/rnd/module03/archive-adverse-event-evaluation-monthly-types.ts`
   - Extracted CLI/default parser and argument/path validation into:
     - `scripts/rnd/module03/archive-adverse-event-evaluation-monthly-cli.ts`
   - Extracted ops runner invocation and archive result logging helpers into:
     - `scripts/rnd/module03/archive-adverse-event-evaluation-monthly-runtime.ts`
   - Reduced `archive-adverse-event-evaluation-monthly.ts` to orchestration-only flow while preserving runner command semantics, archive artifact schema, and retention log output behavior.
131. Module03 handoff-runtime exec env/runner layered split (`scripts/rnd/module03/scheduler-handoff-validation-runtime-exec.ts`)
   - Extracted handoff runtime env/secret-binding helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-runtime-exec-env.ts`
   - Extracted handoff deployment/infra/dry-run runner helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-runtime-exec-runners.ts`
   - Converted `scheduler-handoff-validation-runtime-exec.ts` into stable export surface to preserve existing caller imports.
   - Preserved default secret-ref mapping, explicit env/secret pair override precedence, runner invocation args, and dry-run expected-output guard while separating policy vs execution responsibilities.
132. Module03 dry-run infra CLI/parser layered split (`scripts/rnd/module03/scheduler-dry-run-infra.ts`)
   - Extracted dry-run CLI/default parser into:
     - `scripts/rnd/module03/scheduler-dry-run-infra-cli.ts`
   - Extracted infra-binding parser/path resolver helpers into:
     - `scripts/rnd/module03/scheduler-dry-run-infra-parser.ts`
   - Converted `scheduler-dry-run-infra.ts` into stable export surface to preserve existing caller imports.
   - Preserved infra artifact identity checks, env-key validation policy, CLI input/window validation, and relative artifact-path resolution behavior while separating parser vs CLI responsibilities.
133. Module03 handoff parser deployment/dry-run layered split (`scripts/rnd/module03/scheduler-handoff-validation-parsers.ts`)
   - Extracted deployment-bundle parser helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-parse-deployment.ts`
   - Extracted dry-run report parser helpers into:
     - `scripts/rnd/module03/scheduler-handoff-validation-parse-dry-run.ts`
   - Converted `scheduler-handoff-validation-parsers.ts` into stable export surface to preserve existing caller imports.
   - Preserved identity validation, env-key validation, verification output schema checks, and parser error semantics while separating deployment vs dry-run parser responsibilities.
134. Module03 dry-run plan args/output layered split (`scripts/rnd/module03/scheduler-dry-run-plan.ts`)
   - Extracted scheduler arg composition helpers into:
     - `scripts/rnd/module03/scheduler-dry-run-plan-args.ts`
   - Extracted expected output verification/default out-path helpers into:
     - `scripts/rnd/module03/scheduler-dry-run-plan-output.ts`
   - Converted `scheduler-dry-run-plan.ts` into stable export surface to preserve existing caller imports.
   - Preserved schema-map path existence checks, retention/strict-env/failure-webhook flag composition, expected-output existence verification, and default report path policy while separating arg vs output responsibilities.
135. Module03 readiness parser handoff/infra layered split (`scripts/rnd/module03/scheduler-readiness-artifacts.parsers.ts`)
   - Extracted shared readiness parser helpers into:
     - `scripts/rnd/module03/scheduler-readiness-parse-common.ts`
   - Extracted handoff summary parser helpers into:
     - `scripts/rnd/module03/scheduler-readiness-parse-handoff.ts`
   - Extracted infra-binding parser helpers into:
     - `scripts/rnd/module03/scheduler-readiness-parse-infra.ts`
   - Converted `scheduler-readiness-artifacts.parsers.ts` into stable export surface while keeping artifact-path resolver there.
   - Preserved readiness identity validation, env-key and secret-binding validation policy, and parser error semantics while separating handoff vs infra parser responsibilities.
136. Module03 deployment-bundle CLI defaults/fields layered split (`scripts/rnd/module03/scheduler-deployment-bundle-cli.ts`)
   - Extracted deployment-bundle CLI default constants into:
     - `scripts/rnd/module03/scheduler-deployment-bundle-cli-defaults.ts`
   - Extracted deployment-bundle CLI field parser/validation helpers into:
     - `scripts/rnd/module03/scheduler-deployment-bundle-cli-fields.ts`
   - Reduced `scheduler-deployment-bundle-cli.ts` to CLI arg wiring/orchestration (`field parser results -> CliArgs`).
   - Preserved cron/timezone/retention default policy, schema/sql file existence checks, required-env parsing, and failure-webhook env-key validation while separating defaults vs field parsing responsibilities.
137. B2B admin report toast effect extraction (`app/(admin)/admin/b2b-reports/B2bAdminReportClient.tsx`)
   - Extracted notice/error toast side-effects into:
     - `app/(admin)/admin/b2b-reports/_lib/use-b2b-admin-report-toast-effects.ts`
   - Reduced root client noise by removing inline toast `useEffect` blocks and delegating to shared hook.
   - Added QA guard:
     - `scripts/qa/check-b2b-admin-report-toast-effects-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/b2b-admin-report-toast-effects-extraction.md`
138. Employee report session effect extraction (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Extracted admin re-check/auth-sync subscription effects into:
     - `app/(features)/employee-report/_lib/use-employee-report-session-effects.ts`
   - Reduced client-root side-effect density by removing inline `subscribeAuthSyncEvent` effect.
   - Added QA guard:
     - `scripts/qa/check-employee-report-session-effects-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-session-effects-extraction.md`
139. Employee report session bootstrap extraction (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Extracted session restore + stored-identity auto-login bootstrap into:
     - `app/(features)/employee-report/_lib/use-employee-report-session-bootstrap.ts`
   - Replaced inline `checkSessionAndMaybeAutoLogin` implementation with hook-returned callback wiring.
   - Added QA guard:
     - `scripts/qa/check-employee-report-session-bootstrap-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-session-bootstrap-extraction.md`
140. Employee report existing-record actions extraction (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Extracted duplicated existing-report lookup/upsert handlers into:
     - `app/(features)/employee-report/_lib/use-employee-report-existing-record-actions.ts`
   - Removed inline `handleFindExisting` + `tryLoadExistingReport` implementations from client root.
   - Added QA guard:
     - `scripts/qa/check-employee-report-existing-record-actions-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-existing-record-actions-extraction.md`
141. Employee report report-actions extraction (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Extracted inline operational handlers into:
     - `app/(features)/employee-report/_lib/use-employee-report-report-actions.ts`
   - Removed inline `handleDownloadPdf`, `handleDownloadLegacyPdf`, `handleLogout`, and `handleChangePeriod` implementations from client root.
   - Added QA guard:
     - `scripts/qa/check-employee-report-report-actions-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-report-actions-extraction.md`
142. Employee report sync-actions extraction (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Extracted restart/sign sync orchestration handlers into:
     - `app/(features)/employee-report/_lib/use-employee-report-sync-actions.ts`
   - Removed inline `handleRestartAuth` and `handleSignAndSync` implementations from client root.
   - Added QA guard:
     - `scripts/qa/check-employee-report-sync-actions-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-sync-actions-extraction.md`
143. Employee report report-loading extraction (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Extracted inline report fetch/sync loaders into:
     - `app/(features)/employee-report/_lib/use-employee-report-report-loading.ts`
   - Removed inline `loadReport` and `syncEmployeeReport` implementations from client root.
   - Added QA guard:
     - `scripts/qa/check-employee-report-report-loading-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-report-loading-extraction.md`
144. Employee report sync-actions subhooks (`app/(features)/employee-report/_lib/use-employee-report-sync-actions.ts`)
   - Split sync-actions internals into dedicated subhooks:
     - `app/(features)/employee-report/_lib/use-employee-report-restart-auth-action.ts`
     - `app/(features)/employee-report/_lib/use-employee-report-sign-sync-action.ts`
   - Reduced `useEmployeeReportSyncActions` to shared preflight wiring + subhook composition.
   - Updated QA guard:
     - `scripts/qa/check-employee-report-sync-actions-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/employee-report-sync-actions-subhooks.md`
145. Survey auth-actions extraction (`app/survey/survey-page-client.tsx`)
   - Extracted inline Kakao auth action/sync handlers into:
     - `app/survey/_lib/use-survey-auth-actions.ts`
   - Removed inline `ensureEmployeeSessionFromIdentity`, `handleStartKakaoAuth`, and `handleConfirmKakaoAuth` from client root.
   - Added QA guard:
     - `scripts/qa/check-survey-auth-actions-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/survey-auth-actions-extraction.md`
146. Survey remote-sync extraction (`app/survey/survey-page-client.tsx`)
   - Extracted inline survey remote sync/save effects into:
     - `app/survey/_lib/use-survey-remote-sync.ts`
   - Removed inline `requestSurveyJson`, `persistSurveySnapshot`, and related remote bootstrap/autosave effects from client root.
   - Added QA guard:
     - `scripts/qa/check-survey-remote-sync-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/survey-remote-sync-extraction.md`
147. Survey lifecycle-actions extraction (`app/survey/survey-page-client.tsx`)
   - Extracted inline survey lifecycle handlers into:
     - `app/survey/_lib/use-survey-lifecycle-actions.ts`
   - Removed inline `requestReset`, `handleReset`, `handleStartSurvey`, `handleRenewalHoldStart`, and `handleRenewalHoldEnd` from client root.
   - Added QA guard:
     - `scripts/qa/check-survey-lifecycle-actions-extraction.cts`
   - Added maintenance note:
     - `docs/maintenance/survey-lifecycle-actions-extraction.md`
148. `app/(admin)/admin/b2b-reports/B2bAdminReportClient.tsx` detail-state boundary split
   - Added `app/(admin)/admin/b2b-reports/_lib/use-b2b-admin-report-detail-state.ts` to own employee-detail state, bundle hydration, preview state, and period-selection state.
   - Moved `fetchEmployeeDetailBundle` response normalization into the new hook so the page stays focused on list/search orchestration and action wiring.
   - Hardened employee switching by clearing survey/note/analysis/report detail state together, preventing stale detail content from leaking if the next employee load fails.
   - Centralized `B2bAdminReportPreviewTab` in `client-types.ts` to remove duplicated tab-union definitions across workspace/preview/lifecycle modules.
149. `app/my-data/myDataPageSections.tsx` copy/label boundary cleanup
   - Added `app/my-data/myDataPageLabels.ts` to centralize Korean-first badge, chat scope/status, and role labels.
   - Replaced raw English user-facing pills (`Kakao`, `Session`, `has data`, raw role/scope labels) in `myDataPageSections.tsx` with shared label helpers.
   - Added `scripts/qa/check-my-data-copy-localization.cts` and npm script `qa:my-data:copy-localization` to guard the surface against English-only copy regressions.
150. Employee report flow panel boundary split (`app/(features)/employee-report/EmployeeReportClient.tsx`)
   - Added `app/(features)/employee-report/_components/EmployeeReportInputFlowPanel.tsx`, `EmployeeReportReadyPanel.tsx`, and `EmployeeReportAdminOnlySection.tsx` so `EmployeeReportClient` can stay focused on state/hook orchestration.
   - Added `app/(features)/employee-report/_lib/employee-report-copy.ts` to centralize admin-only notice text, force-confirm wording, and summary CTA copy used across the employee report surface.
   - Updated static QA/doc maps so future sessions follow wrapper panels first, then leaf components and hooks.
151. Cart interaction-controller boundary split (`components/order/cart.tsx`)
   - Added `components/order/hooks/useCartInteractionController.ts` to own address save, product-detail scroll restore, phone modal callbacks, bulk option change, and checkout/pharmacy modal state.
   - Reused `updateCartAndPersist` from `components/order/cartItemsSection.actions.ts` so cart-level persistence follows the same notification path as row-level mutations.
   - Added `docs/cart_client_map.md`, `scripts/qa/check-cart-interaction-controller-extraction.cts`, and npm script `qa:cart:interaction-controller-extraction` to make cart follow-up sessions faster and safer.
152. Column editor controller boundary split (`app/(admin)/admin/column/editor/EditorAdminClient.tsx`)
   - Added `app/(admin)/admin/column/editor/_lib/use-column-editor-controller.ts` to own list/detail loading, query-param selection, form reset/edit state, mutation handlers, and markdown image-upload insertion flow.
   - Reduced `EditorAdminClient.tsx` to shell rendering plus `sidebarProps` / `workspaceProps` composition.
   - Parallelized multi-image upload with `Promise.all` while preserving insertion order.
   - Added `docs/maintenance/column-editor-controller-extraction.md`, `docs/column_editor_client_map.md` updates, and `scripts/qa/check-column-editor-controller-extraction.cts` for follow-up session clarity.
153. Column editor controller subhooks (`app/(admin)/admin/column/editor/_lib/use-column-editor-controller.ts`)
   - Added `use-column-editor-post-actions.ts` for save/publish/delete/dev-save mutation handlers and publish-block derivation.
   - Added `use-column-editor-markdown-media.ts` for textarea/file-input refs, paste/file upload flow, and markdown insertion.
   - Reduced `use-column-editor-controller.ts` to selection/form orchestration plus UI prop composition.
   - Added `docs/maintenance/column-editor-controller-subhooks.md` and `scripts/qa/check-column-editor-controller-subhooks.cts` to keep future follow-up edits on the right boundary.
154. Employee report client-utils module split (`app/(features)/employee-report/_lib/client-utils.ts`)
   - Split the monolithic client utility file into focused modules: `client-utils.identity.ts`, `client-utils.request.ts`, `client-utils.guidance.ts`, `client-utils.pdf.ts`, and `client-utils.format.ts`.
   - Kept `client-utils.ts` as a stable facade for legacy imports while moving feature code to direct focused-module imports.
   - Added `scripts/qa/check-employee-report-client-utils-modules.cts`, updated employee-report docs/precheck guidance, and documented the new boundary for follow-up sessions.
155. Column legacy editor redirect cleanup (`app/column/editor/page.tsx`)
   - Removed the unused `app/column/editor/EditorClient.tsx` legacy dev editor so follow-up sessions no longer mistake it for an active entry point.
   - Kept `/column/editor` redirect-only and documented the admin editor as the single maintained editor surface.
   - Added `scripts/qa/check-column-editor-legacy-redirect.cts` plus precheck/map updates to keep the dead client boundary from returning.
156. My-data section modules (`app/my-data/myDataPageSections.tsx`)
   - Split the monolithic my-data section file into focused modules: `myDataPageOverviewSections.tsx`, `myDataPageOrderSection.tsx`, `myDataPageResultSections.tsx`, and `myDataPageChatSection.tsx`.
   - Kept `myDataPageSections.tsx` as a stable export surface so `app/my-data/page.tsx` and future callers can keep a single import path.
   - Added `scripts/qa/check-my-data-section-modules.cts`, updated the localization QA, and documented the new map for follow-up sessions.
157. Desktop chat dock panel shell extraction (`components/chat/DesktopChatDockPanel.tsx`)
   - Moved dock prompt bootstrap, inert/focus cleanup, scroll-chain guard, and session-layer handlers into `components/chat/useDesktopChatDockPanelShell.ts`.
   - Kept `DesktopChatDockPanel.tsx` as the composition shell that wires `useChat`, layout state, and dock subcomponents.
   - Added `scripts/qa/check-desktop-chat-dock-panel-shell-extraction.cts` and documented the new boundary for follow-up sessions.
158. Desktop chat dock launcher extraction (`components/chat/DesktopChatDock.tsx`)
   - Moved lazy boot, pending-open, viewport/footer offset tracking, route-nudge visibility, and global dock open/close events into `components/chat/useDesktopChatDockLauncher.ts`.
   - Kept `DesktopChatDock.tsx` as the route-aware trigger shell that composes localized nudge UI and the dock panel.
   - Added `scripts/qa/check-desktop-chat-dock-launcher-extraction.cts` and documented the new launcher boundary for follow-up sessions.
159. Recommended product actions controller extraction (`app/chat/components/RecommendedProductActions.tsx`)
   - Moved recommendation resolve lifecycle, cart/address guard state, confirm dialog payloads, and address-save follow-up handling into `app/chat/components/useRecommendedProductActionsController.ts`.
   - Split preview/item-row rendering into `RecommendedProductActionList.tsx` and separated the draggable address guide / confirm dialogs into dedicated modal components.
   - Kept `RecommendedProductActions.tsx` as the chat CTA shell and added `scripts/qa/check-recommended-product-actions-controller-extraction.cts` plus follow-up docs.
160. Recommended product actions resolve modules (`app/chat/components/recommendedProductActions.resolve.ts`)
   - Moved product-name catalog fetch/cache normalization into `recommendedProductActions.resolve.catalog.ts`.
   - Moved name tokenization and candidate score/ranking into `recommendedProductActions.resolve.name.ts`.
   - Moved placeholder/category-like fallback predicates into `recommendedProductActions.resolve.category.ts`.
   - Kept `recommendedProductActions.resolve.ts` focused on category fallback policy, category scoring, and final recommendation assembly, and extended `scripts/qa/check-recommended-product-actions-resolve-modules.cts`.
161. Chat useChat command layer extraction (`app/chat/hooks/useChat.ts`)
   - Moved UI-facing handler assembly into `app/chat/hooks/useChat.commandLayer.ts`.
   - Kept `useChat.ts` focused on state, refs, bootstrap/scroll effects, derived context, and return wiring.
   - Added `scripts/qa/check-chat-command-layer-extraction.cts` plus follow-up maintenance docs.
162. Column summary query extraction (`app/column/_lib/columns.ts`)
   - Moved tag aggregation, tag archive filtering, related-column selection, and adjacent-column selection into `app/column/_lib/columns-summary-queries.ts`.
   - Kept `columns.ts` focused on file/DB loading, slug resolution, and async public wrappers.
   - Added `scripts/qa/check-column-summary-query-extraction.cts` plus follow-up maintenance docs.
163. Home product section data/content extraction (`app/(components)/homeProductSection.tsx`)
   - Moved home-data fetch/cache/recovery state into `app/(components)/useHomeProductSectionData.ts`.
   - Moved section composition plus product-detail/cart overlay rendering into `app/(components)/homeProductSection.content.tsx`.
   - Kept `homeProductSection.tsx` focused on state orchestration, effect wiring, and cart callbacks.
   - Added `scripts/qa/check-home-product-section-data-content-extraction.cts` plus follow-up maintenance docs.
164. Order-complete bootstrap/notification hook extraction (`app/(orders)/order-complete/page.tsx`)
   - Moved payment verification, duplicate-order lookup, order creation, and cart/checkout recovery routing into `app/(orders)/order-complete/useOrderCompleteBootstrap.ts`.
   - Moved push subscribe/send/unsubscribe handlers into `app/(orders)/order-complete/useOrderCompleteNotifications.ts`.
   - Added `orderComplete.client.ts`, `orderComplete.copy.ts`, and draft-validation helpers so future sessions can find order-complete boundaries faster.
   - Added `scripts/qa/check-order-complete-hooks-extraction.cts` plus follow-up maintenance docs.
165. Chat interactive action route modules (`app/chat/hooks/useChat.interactiveActions.ts`)
   - Moved route navigation, page-focus fallback, and support link config/helpers into `app/chat/hooks/useChat.interactiveActions.routes.ts`.
   - Moved shared interactive action contracts into `app/chat/hooks/useChat.interactiveActions.types.ts`.
   - Kept `useChat.interactiveActions.ts` focused on cart/profile/assessment orchestration plus route-helper wiring.
   - Added `scripts/qa/check-chat-interactive-actions-modules.cts` plus follow-up maintenance docs.
166. B2B integrated result preview modules (`app/(admin)/admin/b2b-reports/_components/B2bIntegratedResultPreview.tsx`)
   - Moved payload-to-preview normalization into `app/(admin)/admin/b2b-reports/_lib/b2b-integrated-result-preview-model.ts`.
   - Split the integrated preview card families into `B2bIntegratedHealthMetricsSection.tsx` and `B2bIntegratedMedicationReviewSection.tsx`.
   - Kept `B2bIntegratedResultPreview.tsx` focused on preview-model memoization plus section composition, and added `scripts/qa/check-b2b-integrated-result-preview-modules.cts`.
167. Assess flow modules (`app/assess/useAssessFlow.ts`)
   - Moved progress/current-question/recommendation derived state into `app/assess/useAssessFlow.derived.ts`.
   - Moved storage hydrate/persist, keyboard/focus/body-scroll effects, category fetch, and loading-timer cleanup into `app/assess/useAssessFlow.lifecycle.ts`.
   - Added `app/assess/useAssessFlow.types.ts` for the shared section union and `scripts/qa/check-assess-flow-modules.cts`.
168. Chat input controller extraction (`app/chat/components/ChatInput.tsx`)
   - Moved textarea sizing, coachmark persistence, quick-action tray state, and unified-action wiring into `app/chat/components/useChatInputController.ts`.
   - Split coachmark/hint/tray UI into `app/chat/components/ChatInputActionAssist.tsx` and shared the prop contract via `app/chat/components/chatInput.types.ts`.
   - Kept `ChatInput.tsx` focused on the shared input shell used by the chat page and desktop dock, and added `scripts/qa/check-chat-input-controller-extraction.cts`.
169. Desktop chat dock layout modules (`components/chat/DesktopChatDock.layout.ts`)
   - Moved clamp, scroll-chain, focus-blur, and resize-edge helpers into `components/chat/DesktopChatDock.layout.geometry.ts`.
   - Moved dock prompt queue, route-nudge persistence, footer offset parsing, and size/position storage helpers into `components/chat/DesktopChatDock.layout.storage.ts`.
   - Kept `DesktopChatDock.layout.ts` as the stable export surface for existing consumers and added `scripts/qa/check-desktop-chat-dock-layout-modules.cts`.
170. Chat recommendation modules (`app/chat/hooks/useChat.recommendation.ts`)
   - Moved home-data fetch/cache, best-option selection, and category bucket building into `app/chat/hooks/useChat.recommendation.catalog.ts`.
   - Kept `useChat.recommendation.ts` focused on recommendation section detection, resolved-price line replacement, and missing-price fallback hydration.
   - Added `scripts/qa/check-chat-recommendation-modules.cts` and documented the new hook boundary for follow-up sessions.

## Priority 1 (next)

1. `app/chat/components/ChatDrawer.tsx` (~350 lines)
   - Split session row rendering and modal-layer controls if the drawer surface expands again.
2. `components/pharm/orderAccordionItem.tsx` (~385 lines)
   - Split order summary, status, and action rows if the pharmacy order surface changes again.
3. `components/pharm/pharmOrderAccordionSections.tsx` (~349 lines)
   - Split status/action/helper blocks if the accordion section surface grows again.

## Priority 2

1. `lib/chat/context.ts` (~916 lines)
   - Move classification and scoring utilities into focused files.
2. `components/order/orderDetails.tsx` (~858 lines)
   - Split summary/payment/status detail blocks.
3. `app/api/health/nhis/fetch/route.ts`
   - Add unit tests for cooldown/policy/cache-serve branches around orchestration helpers.
4. `app/(features)/health-link/HealthLinkClient.tsx`
   - Optional: split section cards into dedicated feature components if UI scope expands.

## Guardrails

- Keep auth checks in `lib/server/route-auth.ts`.
- Keep Prisma singleton only in `lib/db.ts`.
- Keep order stock mutation inside `lib/order/mutations.ts:createOrder`.
- Run `npm run audit:encoding` before and after major edits.
- Final verification baseline: `npm run lint` and `npm run build`.
