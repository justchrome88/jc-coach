> STATUS: SUPPORTING / BLOCKED PREFLIGHT / NOT SOURCE OF TRUTH
> Canonical sources: `docs/CURRENT_STATUS.md`, `docs/SECURITY.md` and
> `docs/DEPLOYMENT.md`.
> Do not use this file as an implementation plan or deploy runbook unless a
> future explicit public-readiness task card scopes it.

# Public Deployment Checklist

Last updated: 2026-07-08.

## Current Decision

Public/friends access remains blocked. This checklist records what a future
public-readiness task must verify; it does not authorize exposing the service,
opening ports, changing DNS, editing `.env`, issuing certificates, changing
nginx/systemd config, restarting services, creating users or running Steam,
import, parser, evaluator or AI jobs.

`READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO` until the final foundation
readiness gate passes.

## Required Gate Before Public/Friends Access

All items must be true before any public/friends access is claimed:

1. A future task card explicitly authorizes public-readiness verification.
2. `docs/SECURITY.md` public/friends readiness gate is satisfied.
3. `docs/DEPLOYMENT.md` deploy verification checklist passes.
4. Privacy/retention policy is accepted for any shared-user data.
5. Secret-redaction and safe environment-reference policy is followed: names
   and purpose only, no values.
6. Current in-memory rate limiting is replaced with public-grade protection or
   the limited exposure model is explicitly risk-accepted.
7. Incident/log taxonomy is accepted and logs are confirmed to avoid secrets.
8. Any production DB, schema, deploy, service or runtime mutation has explicit
   authorization and required evidence.

## Safe Environment Names

Public-readiness docs may refer to these names and their purpose only:

- `APP_ENV`: selects environment behavior.
- `PUBLIC_BASE_URL`: base URL for generated links and callbacks.
- `STEAM_REALM`: Steam OpenID realm/callback boundary.
- `AUTH_COOKIE_SECURE`: secure-cookie transport policy.
- `SESSION_SECRET_KEY`: session signing secret; never print the value.
- `API_TOKEN`: owner/operator bearer token; never print the value.
- `STEAM_WEB_API_KEY`: Steam API access when configured; never print the value.

Do not add values, masked values, lengths, checksums, prefixes or suffixes to
this file.

## Verification Shape For A Future Authorized Task

Read-only verification may check:

1. `GET /health`.
2. Anonymous `GET /`.
3. Anonymous protected-page redirects.
4. Non-health `/api/*` auth requirement.
5. Static asset availability.
6. Logs for absence of secret values.

Mutation verification may happen only when a future task explicitly authorizes
the exact deploy/service/config changes and required rollback evidence.

## Explicit Non-Authorization

This checklist does not authorize:

- Public router, firewall, DNS, HTTPS, nginx, systemd or service changes.
- `.env` edits or secret inspection.
- Registration/login smoke that mutates production DB state.
- Live Steam/Valve import.
- Parser, evaluator or manual evaluator jobs.
- Raw demo movement, deletion or compression.
- Final readiness, public/friends readiness, WP-018 restart or major CS2
  feature unlock claims.
