> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/SECURITY.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Security

Last updated: 2026-07-08.

## Current Truth

The app is acceptable only for personal/VPS use under controlled access.

Stage 1 Security P0 added app-level protection for non-health `/api/*`, CSRF for browser POST routes, MVP in-memory rate limits, strong session secret fail-fast outside local/test and Steam OpenID assertion verification.

Stage 2 Ownership вводит enforced single-owner boundary: первый активный credentialed/register user считается owner инстанса, а дальнейшая self-registration по умолчанию закрыта.

The product is still not ready for friends/public exposure until migrations,
operational visibility, privacy/retention, rate-limit, deploy verification and
remaining release gates are closed.

## Public/Friends Readiness Gate

Current public/friends readiness: `BLOCKED`.

Public or friends access must not be exposed, advertised or treated as ready
until a future explicit public-readiness task verifies all of these conditions:

- Foundation readiness gate has passed; until then
  `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`.
- `project_docs/operations/DEPLOYMENT.md` deploy verification checklist passes without service,
  nginx, systemd or runtime configuration drift.
- Authentication, owner boundary, CSRF and API-token behavior are verified for
  the intended exposure model.
- Secret-redaction, safe environment-reference, privacy/retention,
  incident/log and public-grade rate-limit policies are implemented or
  explicitly accepted by the operator.
- Any production DB, schema, import/parser/evaluator, deploy or service action
  needed by the gate has explicit task authorization, backup/SHA evidence where
  required and a scoped report.

Docs-only edits cannot pass this gate and must not claim friends/public
readiness.

## Blockers For Friends/Public Use

- Non-health `/api/*` endpoints require authenticated session or optional Bearer `API_TOKEN`.
- State-changing browser routes require session CSRF.
- Session-authenticated API state changes require `X-CSRF-Token`; Bearer token API calls do not use browser CSRF.
- MVP rate limits cover login, upload/import, AI, Steam/import, reports, recommendations and storage mutation routes.
- Strong `SESSION_SECRET_KEY` is enforced outside local/test/dev.
- Steam OpenID callback verifies Steam `check_authentication`.
- Sensitive records still need user ownership or declared/enforced single-user mode.
- Migration discipline and operational visibility still need hardening.
- Privacy/retention boundaries and incident/log review are documented but not
  public-operations hardened.
- Current in-memory rate limiting is not public-grade.

## Stage 1 Notes

- Rate limiting is in-memory and single-process. It is suitable for personal/VPS hardening, not public-scale abuse protection.
- API auth is either browser session or configured `API_TOKEN`.
- Security event logging uses the app logger and records route/action/user context, not secrets.

## Secret Redaction Policy

Reports, docs, task outputs and diagnostic command output must not print,
infer, decode, copy or persist secret values.

Forbidden output includes values from `.env` files, service environment,
database URLs, `SESSION_SECRET_KEY`, `API_TOKEN`, Steam or provider API keys,
bot credentials, cookies, bearer tokens, CSRF tokens, passwords, refresh tokens
and raw authentication assertions.

Allowed output is limited to names, purpose and non-sensitive presence/status
labels, for example `SESSION_SECRET_KEY: present` or
`STEAM_WEB_API_KEY: missing`. Do not include prefixes, suffixes, checksums,
lengths or partially masked values for secrets.

Commands that display environment or secret-bearing files are forbidden in
reports unless a future task explicitly authorizes a redacted verifier that
prints names/status only. Avoid examples such as `cat .env`, `printenv`, `env`,
`set`, `systemctl show ... Environment`, unfiltered service dumps and log
queries that may include request headers or credential material.

## Safe Environment Reference

Environment references in project docs may list variable names and purpose
only. Values belong in operator-managed environment/config, not in git, docs,
reports or console output.

| Name | Purpose | Value policy |
|---|---|---|
| `APP_ENV` | Select local/test/dev/production behavior. | Name/purpose only. |
| `PUBLIC_BASE_URL` | Public base URL used by generated links and callbacks. | Name/purpose only. |
| `STEAM_REALM` | Steam OpenID realm/callback trust boundary. | Name/purpose only. |
| `AUTH_COOKIE_SECURE` | Whether auth cookies require HTTPS transport. | Name/purpose only. |
| `SESSION_SECRET_KEY` | Session signing secret. | Secret; never print. |
| `API_TOKEN` | Optional owner/operator bearer token. | Secret; never print. |
| `STEAM_WEB_API_KEY` | Steam Web API access when configured. | Secret; never print. |

Add new environment variables to this table only with names and purpose, never
with values.

## Privacy And Retention Before Sharing

Before any friends/public sharing, the operator must have an accepted
privacy/retention policy covering:

- Which personal match, Steam, upload, parser artifact, recommendation, report
  and log data is collected.
- Who can access owner data and whether any friend/public user can upload,
  view, link Steam or trigger imports.
- Retention periods for raw demos, uploads, parser artifacts, generated
  reports, import jobs, recommendation evaluations, auth/security logs and
  backups.
- Deletion/export process for shared-user data and how it avoids deleting raw
  demos or backups without an explicit storage WP.
- Whether third-party AI or Steam APIs receive personal data, and what data is
  sent.
- Backup/restore handling for shared-user data and incident response evidence.

Until that policy is accepted, JC Coach remains controlled personal-use only.

## Rate-Limit Public-Grade Boundary

Current rate limiting is in-memory, process-local and suitable only as an MVP
personal/VPS guardrail. It is not public-grade because it is not durable across
process restarts, not shared across replicas, not centrally observable and not
accepted as an abuse-control layer for unknown users.

Friends/public readiness requires a future task to either implement and verify
a public-grade limiter or explicitly risk-accept a narrower exposure model.

## Incident And Log Taxonomy

Incident/log records must use taxonomy labels and redact sensitive data. Logs
may include event type, timestamp, route/action, coarse actor class, internal
user/job IDs when needed, status, outcome and correlation IDs. Logs must not
include secret values, cookies, bearer tokens, CSRF tokens, passwords, Steam
assertions, raw request bodies, raw `.env` lines or uploaded demo contents.

| Category | Use for | Minimum response |
|---|---|---|
| `auth` | Login, logout, owner guard and registration boundary events. | Review owner boundary and session behavior. |
| `csrf` | Missing or invalid CSRF on session-authenticated state changes. | Confirm route protection and absence of token leakage. |
| `rate_limit` | Login, upload/import, AI, report, recommendation or storage throttle events. | Confirm request source and whether personal/VPS limit is sufficient. |
| `secret_handling` | Any suspected secret exposure in docs, logs, reports or console output. | Stop sharing output, rotate affected secret if exposure is confirmed and record a scoped incident report. |
| `privacy_data_access` | Access/export/delete concerns for uploads, demos, parser artifacts, recommendations, reports or backups. | Preserve evidence, avoid deletion without storage/DB authorization and define user-facing remediation. |
| `import_parser_evaluator` | Steam/import, parser, evaluator or manual evaluator safety events. | Do not rerun jobs without explicit WP authorization. |
| `deploy_runtime` | Health, nginx, systemd, service or public endpoint verification events. | Prefer read-only checks; avoid restart/reload/config mutation without authorization. |

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
