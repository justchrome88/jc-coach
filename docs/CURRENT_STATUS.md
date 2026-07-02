# Current Status

Last updated: 2026-07-03.

Фактический уровень продукта: `v0.4-alpha foundation`.

Текущий milestone разработки: `v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop`.

The project is past the original `v0.1` CSV MVP. It is usable as a personal FastAPI CS2 coach on a controlled VPS, but it is not a secure friends/public product and not a fully validated AI coach.

## Working

- FastAPI/Jinja UI with SQLite and SQLAlchemy.
- CSV/JSON import with incomplete-column tolerance and duplicate protection.
- Manual official `.dem` upload through `demoparser2`.
- Deep parser foundation with normalized parser tables, compact payload and `swing_score`.
- Dashboard, stats, match list/detail, reports and settings pages.
- Rule-based weakness detection and coach report generation.
- Recommendation tracking with active goals, lifecycle actions and match evaluation.
- AI coach handoff through `codex_cli_handoff`.
- AI report persistence with payload snapshot, provider metadata and payload hash.
- Steam OpenID onboarding, Game Authentication Code flow, share-code cursor and service bot demo URL resolver.
- Observe-only demo storage reporting and manifest generation.

## Partial Or Risky

- Parser-derived metrics still need explicit confidence and suppression rules.
- Steam import works as an alpha path, but needs durable scheduling, retries and cursor freshness diagnostics.
- Recommendations are not yet consistently generated from the top verified problem snapshot.
- AI output is still free-form and needs schema validation, prompt versioning and validator checks.
- Auth exists, but API auth, user ownership/single-user enforcement, CSRF/rate limits and strong secret enforcement are not complete.

## Not Ready

- Secure friends alpha.
- Public beta.
- FACEIT import.
- Raw `.dem` deletion.
- Payments, viewer, heatmaps, clips, practice servers or social features.
