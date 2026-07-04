# Security

Last updated: 2026-07-04.

## Current Truth

The app is acceptable only for personal/VPS use under controlled access.

Stage 1 Security P0 added app-level protection for non-health `/api/*`, CSRF for browser POST routes, MVP in-memory rate limits, strong session secret fail-fast outside local/test and Steam OpenID assertion verification.

Stage 2 Ownership вводит enforced single-owner boundary: первый активный credentialed/register user считается owner инстанса, а дальнейшая self-registration по умолчанию закрыта.

The product is still not ready for friends/public exposure until migrations/operational visibility and remaining release gates are closed.

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

## Stage 2 Ownership Policy

- Owner policy: `first_active_credentialed_user_is_owner`.
- Первый активный пользователь с `email` и `password_hash`, созданный через register flow, является владельцем single-user инстанса.
- This policy is intentionally documented as fragile: owner resolution depends on mutable user state and insertion order until an explicit owner state exists. A lower-id active credentialed test/smoke user can become owner if guardrails fail.
- После появления owner новая публичная регистрация возвращает ошибку и не создаёт запись в `users`.
- `test-*@example.test` and `smoke-*@example.test` registrations are blocked outside `APP_ENV=test`.
- Session login и session guards принимают только owner. Legacy/non-owner записи не получают доступ к owner state через session.
- `API_TOKEN` трактуется как owner/operator token для автоматизации и не создаёт пользователей.
- Steam OpenID callback не создаёт и не линкует Steam account без текущей owner session.
- Owner session может линковать Steam account только к owner user; callback создаёт только queued metadata job, production Steam/import jobs этим не запускаются.

## Steam Secret Rules

- Do not ask for or store a user's Steam password, Steam Guard approval, refresh token or personal credentials.
- Service bot credentials belong only to a dedicated bot account and must not be committed.
- `.env`, bot credentials and tokens stay out of git.
