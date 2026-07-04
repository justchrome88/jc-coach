# Deployment

Last updated: 2026-07-04.

## Current Shape

The repository includes deployment references:

- `deploy/systemd/jc-coach.service`
- `deploy/nginx/jcnodex.conf`
- `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`

The current deployment is suitable for controlled personal/VPS use only.

## Public/Friends Gate

Do not claim friends/public readiness until `docs/SECURITY.md` blockers are closed and verified.

## Operational Notes

- Keep secrets in environment/config, not git.
- Keep generated data under `data/` out of git.
- Verify health, auth flow and core pages after deployment changes.

## Runtime Smoke Policy

Read-only smoke is the default after deployment/runtime checks:

- `GET /health`
- anonymous `GET /`
- anonymous protected-page redirect checks such as `GET /dashboard` expecting `/login`
- static asset availability when relevant

Read-only smoke must not post to `/register`, `/login`, import, parser, Steam or AI routes.

Mutating or authenticated smoke is a separate operation and needs explicit authorization. Before any mutating/authenticated runtime smoke:

1. Record `sha256sum data/cs2_coach.db`.
2. Confirm whether login will update `last_login_at` or any other persisted state.
3. Use the real owner account only; never create `test-*@example.test` or `smoke-*@example.test` users in production.
4. Record `sha256sum data/cs2_coach.db` after the check and explain any expected change.
