# Architecture

Last updated: 2026-07-03.

## Shape

- FastAPI application.
- Jinja2 server-rendered UI.
- SQLite through SQLAlchemy.
- Service modules for imports, analytics, recommendations, reports, AI coach, Steam and parser work.
- Local filesystem under `data/` for samples, uploads, reports, handoffs and generated runtime artifacts.

## Current Flow

```text
CSV/JSON/DEM/Steam -> importer/parser -> database facts -> analytics -> diagnosis -> recommendations -> reports/AI handoff
```

AI and recommendations must consume deterministic facts. They must not invent parser data or silently treat low-confidence metrics as reliable.

## Boundaries

- Web routes should orchestrate request/response concerns.
- Services should hold business logic.
- Database models define persistence, not product policy.
- AI provider boundary must keep payload construction separate from generation.
- Steam service bot is infrastructure, not a user's Steam account.

## Supporting Docs

- Steam: `docs/STEAM_IMPORT.md`
- AI: `docs/AI_COACH.md`
- Metrics: `docs/METRICS.md`
- Recommendations: `docs/RECOMMENDATIONS.md`
- Security: `docs/SECURITY.md`

