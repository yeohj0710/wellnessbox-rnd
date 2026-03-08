# Agent Preflight Checklist

Purpose: speed up new coding sessions by checking structural risks first, before feature work.

## 1) Fast Baseline

Run these in order:

```bash
npm run agent:context-refresh
npm run audit:hotspots
npm run lint
npm run build
```

If `npm run build` fails at `prisma:generate` with Windows `EPERM rename` on
`node_modules/.prisma/client/query_engine-windows.dll.node`:

1. Close processes that may hold Prisma engine files (for example Prisma Studio or other Node dev servers).
2. Re-run `npm run build`.
3. For code-level regression verification while the lock persists, run:

```bash
npx next build
```

`audit:hotspots` gives:
- top long files by line count (refactor candidates)
- critical route guard checks for admin/rag/push endpoints

`agent:context-refresh` also refreshes:
- `REFACTOR_HOTSPOTS.md`
- `API_GUARD_MAP.md`
- `AGENT_SKILLS_CATALOG.md`

Guard policy strict check:

```bash
npm run agent:guard-check
```

This fails when a route uses session access (`getSession` / `route-auth` import) without matching guard policy notes.

## 2) Non-Negotiable Invariants

- Route auth/ownership must use `lib/server/route-auth.ts` guards.
- Order stock mutation must stay in `lib/order/mutations.ts:createOrder` transaction.
- Prisma client must stay singleton via `lib/db.ts`.
- Admin gate must stay aligned across:
  - `app/api/verify-password/route.ts`
  - `lib/admin-token.ts`
  - `middleware.ts`

## 3) High-Impact Hotspots

When touching these files, prefer block-level extraction over in-place growth:

- `app/chat/hooks/useChat.ts`
- `components/chat/DesktopChatDock.tsx`
- `app/api/chat/actions/route.ts`
- `lib/chat/context.ts`
- `components/order/orderDetails.tsx`

## 4) Refactor Rule of Thumb

- Split only when boundaries are clear (pure helper, UI fragment, parser/mapper).
- Keep behavior equivalent first; optimize behavior in a separate pass.
- For auth/order/push changes, do manual flow checks after build:
  - login
  - checkout complete
  - my-orders lookup
  - push subscribe/status

## 5) Quick Domain Maps

- Check AI maintenance map: `docs/engineering/check-ai-maintenance-map.md`
- Check API auth/guard coverage map: `API_GUARD_MAP.md`
