# Security

Last updated: 2026-07-03.

## Current Truth

The app is acceptable only for personal/VPS use under controlled access.

Stage 1 Security P0 added app-level protection for non-health `/api/*`, CSRF for browser POST routes, MVP in-memory rate limits, strong session secret fail-fast outside local/test and Steam OpenID assertion verification.

The product is still not ready for friends/public exposure until ownership/single-user enforcement, migrations/operational visibility and remaining release gates are closed.

## Blockers For Friends/Public Use

- Non-health `/api/*` endpoints require authenticated session or optional Bearer `API_TOKEN`.
- State-changing browser routes require session CSRF.
- Session-authenticated API state changes require `X-CSRF-Token`; Bearer token API calls do not use browser CSRF.
- MVP rate limits cover login, upload/import, AI, Steam/import, reports, recommendations and storage mutation routes.
- Strong `SESSION_SECRET_KEY` is enforced outside local/test/dev.
- Steam OpenID callback verifies Steam `check_authentication`.
- Sensitive records still need user ownership or declared/enforced single-user mode.
- Migration discipline and operational visibility still need hardening.

## Stage 1 Notes

- Rate limiting is in-memory and single-process. It is suitable for personal/VPS hardening, not public-scale abuse protection.
- API auth is either browser session or configured `API_TOKEN`.
- Security event logging uses the app logger and records route/action/user context, not secrets.

## Steam Secret Rules

- Do not ask for or store a user's Steam password, Steam Guard approval, refresh token or personal credentials.
- Service bot credentials belong only to a dedicated bot account and must not be committed.
- `.env`, bot credentials and tokens stay out of git.
