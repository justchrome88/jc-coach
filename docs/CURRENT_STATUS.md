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
- Stage 1 Security P0 hardening: API auth, CSRF/state-change checks, MVP rate limits, strong session secret fail-fast and Steam OpenID verification.
- Stage 2 Ownership hardening: enforced single-owner mode completed / `PASS_WITH_WARNINGS`.
- Stage 3 Migration discipline scaffold completed / `PASS_WITH_WARNINGS`: migration policy, schema inventory and safe copy-check tooling.
- Observe-only demo storage reporting and manifest generation.

## Partial Or Risky

- Parser-derived metrics still need explicit confidence and suppression rules.
- Steam import works as an alpha path, but needs durable scheduling, retries and cursor freshness diagnostics.
- Stage 2 ownership is single-owner mode, not full multi-user SaaS ownership across all core tables.
- Legacy `link_steam_account(..., user_id=None)` remains an internal Steam hardening risk, but it is not reachable from public OpenID callback without owner session.
- Stage 3 migration discipline is scaffold-level, not a full Alembic baseline or production migration ledger.
- Next hardening stage after Stage 3 review should stay within the ordered milestone scope.
- Recommendations are not yet consistently generated from the top verified problem snapshot.
- AI output is still free-form and needs schema validation, prompt versioning and validator checks.
- Auth/security is still personal/VPS only; observability and public/friends release gates are not complete.

## Not Ready

- Secure friends alpha.
- Public beta.
- FACEIT import.
- Raw `.dem` deletion.
- Payments, viewer, heatmaps, clips, practice servers or social features.
