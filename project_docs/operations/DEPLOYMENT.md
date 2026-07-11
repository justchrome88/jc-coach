> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/DEPLOYMENT.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Deployment

Last updated: 2026-07-08.

## Current Shape

The repository includes deployment references:

- `deploy/systemd/jc-coach.service`
- `deploy/nginx/jcnodex.conf`
- `project_control/checklists/PUBLIC_DEPLOYMENT_CHECKLIST.md`

The current deployment is suitable for controlled personal/VPS use only.

## Public/Friends Gate

Current public/friends readiness: `BLOCKED`.

Do not claim friends/public readiness until `project_docs/operations/SECURITY.md` blockers are
closed and a future explicit public-readiness gate verifies the intended
exposure model. Docs-only edits, roadmap edits and checklist updates do not
make the service public-ready and do not change
`READY_FOR_MAJOR_CS2_FEATURE_WORK: NO`.

`project_control/checklists/PUBLIC_DEPLOYMENT_CHECKLIST.md` is a blocked preflight checklist, not an
authorization to expose ports, edit `.env`, reload nginx, restart services or
run live import/parser/evaluator jobs.

## Operational Notes

- Keep secrets in environment/config, not git.
- Keep generated data under `data/` out of git.
- Verify health, auth flow and core pages after deployment changes.
- Use safe environment references by name/purpose only. Do not print values in
  docs, reports or command output.

## Deploy Verification Checklist

This checklist is documentation for a future authorized deploy-verification
task. It must not be executed as an implicit deploy, service, nginx, systemd or
runtime mutation.

Preflight:

1. Confirm the task explicitly authorizes the deploy/runtime scope.
2. Confirm the worktree status and allowed files before changes.
3. Confirm whether the task is read-only or permits service/nginx/systemd
   mutation.
4. Confirm no `.env` values, tokens, cookies or service environment values will
   be printed.
5. Confirm production DB mutation is not part of the check; if it is, stop
   unless the task includes backup and SHA authorization.

Read-only verification:

1. Verify service health with `GET /health`.
2. Verify anonymous `GET /` returns the expected public landing response for
   the current exposure model.
3. Verify protected pages redirect anonymous users to login.
4. Verify non-health `/api/*` routes require session auth or the configured
   owner/operator bearer token.
5. Verify static assets load for the active frontend pages.
6. Verify logs show no secret values, request credentials or raw uploads.

Authorized mutation verification, only when explicitly scoped:

1. Run config syntax checks before applying deploy config changes.
2. Apply only the named deploy/runtime changes.
3. Restart or reload only the named service when explicitly authorized.
4. Repeat read-only verification after the change.
5. Record changed files, commands, health evidence, forbidden actions avoided
   and rollback notes in the task report.

Public/friends gate additions:

1. Confirm HTTPS/cookie policy, public base URL and Steam realm are configured
   without printing values.
2. Confirm registration/owner policy matches the intended exposure model.
3. Confirm privacy/retention policy and incident/log taxonomy are accepted.
4. Confirm rate limiting is public-grade or the exposure model is explicitly
   risk-accepted.
5. Confirm final readiness gate status before claiming public/friends access.

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
