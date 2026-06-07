# Pi-PM Frontend

React Native + React Native Web monorepo for the Pi-PM portfolio console.

**Architecture:** [ADR-026](../docs/architecture/ADR-026-Frontend-Architecture.md)  
**Report:** [ARCHITECTURE_REPORT.md](./docs/ARCHITECTURE_REPORT.md)

## Prerequisites

- Node.js ≥ 20
- pnpm 9 (`corepack enable`)

## Quick start

```bash
cd frontend
pnpm install
pnpm dev:web      # http://localhost:8081 — responsive web
pnpm dev:mobile   # Expo native dev client
```

## Commands

| Command | Description |
|---------|-------------|
| `pnpm dev:web` | Start Expo web dev server |
| `pnpm dev:mobile` | Start Expo native dev server |
| `pnpm preview:web` | Build static web bundle + serve on http://localhost:3000 |
| `pnpm preview:web:serve` | Serve existing `apps/web/dist` (after build) |
| `pnpm typecheck` | TypeScript check all packages |
| `pnpm test` | Unit tests (api, navigation, ui) |
| `pnpm build` | Export web + mobile bundles |

## Structure

```
apps/web      — Primary web target (Expo Web)
apps/mobile   — Native shell (iOS/Android)
packages/ui   — Shared components + screen shells
packages/api  — Typed HTTP clients
packages/hooks — Zustand + TanStack Query
packages/theme — Bloomberg Terminal Lite dark theme
packages/navigation — Sidebar / TabBar / AppShell
packages/types — Shared TypeScript contracts
```

## Environment

Copy `apps/web/.env.example` to `apps/web/.env` (or export vars before `build` / `preview:web`).

```bash
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
EXPO_PUBLIC_DEFAULT_STRATEGY=momentum_sqe
EXPO_PUBLIC_AUTH_BYPASS=true
```

## Static preview (production-like)

Requires the API at `http://localhost:8000` (Docker or `uvicorn`). For auth bypass, set `AUTH_ENABLED=false` in the repo root `.env`.

```bash
cd frontend
cp apps/web/.env.example apps/web/.env   # optional; vars are baked in at build time
pnpm preview:web                         # http://localhost:3000
```
