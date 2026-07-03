# API Security Inventory

Дата: 2026-07-03.

Stage 1 Security P0 inventory. Это не feature roadmap; файл фиксирует текущую защиту routes после hardening.

## Policy

- Non-health `/api/*` requires authenticated browser session or configured Bearer `API_TOKEN`.
- Browser POST routes require session CSRF.
- Session-authenticated API state changes require `X-CSRF-Token`.
- Bearer token API calls are not browser-cookie based and do not require CSRF.
- Login/upload/import/AI/Steam/report/recommendation/storage mutation routes use MVP in-memory rate limits.
- Import, Steam, parser and AI jobs were not run during validation.

## Inventory

| Method | Path | Changes state? | Auth required? | CSRF/API token? | Rate limited? | Notes |
|---|---|---:|---:|---:|---:|---|
| GET | `/health` | no | no | no | no | Public health endpoint. |
| GET | `/api/matches` | no | yes | session or token | no | Protected API read. |
| GET | `/api/analytics/summary` | no | yes | session or token | no | Protected API read. |
| GET | `/api/analytics/aim` | no | yes | session or token | no | Protected API read. |
| GET | `/api/recommendations*` | can mutate indirectly | yes | session or token | no | Existing service read helpers can still evaluate/create records; planner/read-write split remains P1. |
| POST | `/api/import/csv` | yes | yes | CSRF for session or Bearer token | yes | Import endpoint; anonymous blocked. |
| POST | `/api/import/json` | yes | yes | CSRF for session or Bearer token | yes | Import endpoint; anonymous blocked. |
| POST | `/api/import/demo` | yes | yes | CSRF for session or Bearer token | yes | Parser endpoint; anonymous blocked. |
| POST | `/api/import/demo/inbox` | yes | yes | CSRF for session or Bearer token | yes | Parser endpoint; anonymous blocked. |
| POST | `/api/recommendations/{id}/status` | yes | yes | CSRF for session or Bearer token | yes | Recommendation action. |
| POST | `/api/recommendations/{id}/extend` | yes | yes | CSRF for session or Bearer token | yes | Recommendation action. |
| POST | `/api/recommendations/categories/{category}/restart` | yes | yes | CSRF for session or Bearer token | yes | Recommendation action. |
| POST | `/api/reports/generate` | yes | yes | CSRF for session or Bearer token | yes | Writes coach report. |
| GET | `/api/reports/latest` | no | yes | session or token | no | Protected API read. |
| GET | `/api/coach/ai/*` | no | yes | session or token | no | Protected AI read/health/handoff state. |
| POST | `/api/coach/ai/*` | yes | yes | CSRF for session or Bearer token | yes | AI handoff/generate/save; anonymous blocked. |
| GET | `/api/steam/*` | no | yes | session or token | no | Protected Steam status/read endpoints. |
| POST | `/api/steam/import/*` | yes | yes | CSRF for session or Bearer token | yes | Steam job endpoints; anonymous blocked. |
| GET | `/api/storage/demos` | no | yes | session or token | no | Protected storage read. |
| POST | `/api/storage/demos/manifest` | yes | yes | CSRF for session or Bearer token | yes | Writes manifest. |
| GET | `/api/import/jobs` | no | yes | session or token | no | Protected job status read. |
| POST | `/login` | yes | public route | CSRF | yes | Login attempts rate-limited. |
| POST | `/register` | yes | public route | CSRF | no | Registration creates local user. |
| POST | `/logout` | yes | yes | CSRF | no | Clears session. |
| POST | `/upload*` | yes | yes | CSRF | yes | Upload/import/parser web routes. |
| POST | `/settings/imports*` | yes | yes | CSRF | yes | Steam keys, sync and job actions. |
| POST | `/settings/storage/manifest` | yes | yes | CSRF | yes | Writes storage manifest. |
| POST | `/report/generate` | yes | yes | CSRF | yes | Writes report. |
| POST | `/coach/ai-*` | yes | yes | CSRF | yes | AI handoff/generate/save. |
| POST | `/coach/recommendations*` | yes | yes | CSRF | yes | Recommendation actions. |

## Remaining Security Gaps

- User ownership or enforced single-user mode is not implemented yet.
- MVP rate limiter is process-local and should be replaced before public exposure.
- Recommendation read endpoints can still have write side effects through existing services.
- Migration discipline and observability remain outside Stage 1.
