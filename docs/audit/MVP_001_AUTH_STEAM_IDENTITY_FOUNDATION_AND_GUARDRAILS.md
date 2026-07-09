# MVP-001 Auth / Steam Identity Foundation and Guardrails

Date: 2026-07-09
Executor: 02-Executor
Task: `MVP-001_AUTH_STEAM_IDENTITY_FOUNDATION_AND_GUARDRAILS`
Verdict: `PASS_WITH_WARNINGS`

## Summary

MVP-001 completed the scoped auth / Steam identity audit and applied one narrow
owner-only guardrail fix in allowed files. No DB/schema/data files, package
files, runtime/deploy config, raw demos, live Steam import, parser jobs,
evaluator jobs or manual evaluator jobs were touched.

The implemented fix adds explicit owner-session redirects to the browser Steam
connect/import settings routes before they list Steam state, save Steam
configuration, queue Steam jobs or start the one-button import path.

## Changed Files

- `app/web/routes.py`
- `tests/test_ownership.py`
- `docs/audit/MVP_001_AUTH_STEAM_IDENTITY_FOUNDATION_AND_GUARDRAILS.md`

## Auth / Session / Owner Posture Findings

- Current owner policy is `first_active_credentialed_user_is_owner` in
  `app/services/auth.py`.
- Owner resolution is the first active user with both `email` and
  `password_hash`, ordered by `users.id`.
- `register_user()` blocks second registration once an owner exists.
- `authenticate_user()` and `current_user_from_session()` reject active
  credentialed non-owner users.
- Test/smoke registration emails are blocked outside `APP_ENV=test`.
- `API_TOKEN` remains an owner/operator automation credential and does not
  create users.
- Residual warning: owner state is implicit and fragile because it depends on
  mutable user rows and insertion order; there is no explicit owner table,
  owner flag or accepted multi-user model.

## Steam Identity Link-State Findings

- `SteamAccount.user_id` exists but is nullable, and `steam_id` is unique.
- `/auth/steam/callback` already required a current owner session before
  linking and passes `user_id=owner.id` to `link_steam_account()`.
- The callback creates a `steam_openid_linked` metadata job only after owner
  session validation and successful OpenID assertion verification.
- `validate_openid_callback()` verifies Steam OpenID with
  `check_authentication`; claimed-id-only callbacks are rejected.
- `link_steam_account()` can still create a legacy Steam-only user if called
  without `user_id`. Current production browser callback avoids that path, but
  future cleanup should tighten the service-level helper contract before any
  broader identity model.

## Implemented Guardrail

The browser routes below now call `_require_user_redirect()` before showing or
mutating Steam import state:

- `GET /settings/imports`
- `GET /auth/steam`
- `POST /settings/imports/steam-web-api-key`
- `POST /settings/imports/steam/{steam_account_id}/auth-code`
- `POST /settings/imports/steam/{steam_account_id}/share-code`
- `POST /settings/imports/steam/{steam_account_id}/sync`
- `POST /settings/imports/jobs/{job_id}/run`
- `POST /settings/imports/run-queued`
- `POST /settings/imports/pull-all`
- `POST /settings/imports/clear-demo-errors`

Focused tests now verify unauthenticated browser access redirects to `/login`
and that `POST /settings/imports/pull-all` with a valid session CSRF token but
without an owner session does not create an `ImportJob`.

## `user_id -> steam_id_64` Ownership Contract Findings

- Implemented contract today: owner session links Steam OpenID identity to
  `steam_accounts.user_id`, with the Steam identifier stored in
  `steam_accounts.steam_id`.
- The contract is route-enforced, not fully model-enforced:
  `steam_accounts.user_id` is nullable and there is no schema-level
  single-owner constraint.
- Import jobs reference `steam_account_id`; they do not carry `user_id`.
- Matches, demo parse artifacts, demo event rows, coach reports,
  recommendations and recommendation evaluations do not carry `user_id`.
- Current data ownership is therefore single-instance/single-owner by
  operational posture, not row-level multi-tenant isolation.

## Match / Demo / Recommendation Ownership Assumptions

- `matches`, demo artifact/event tables, coach reports, recommendations and
  recommendation evaluations are global personal-instance data.
- Steam history placeholder rows use `Match.source == "steam_history"` and
  external share codes for dedupe; playable imported demo matches are not
  user-scoped at the row level.
- Recommendation tracking assumes one owner dataset. Legacy recommendation
  guardrails still apply: accepted hard progress remains recommendation `#5`,
  and legacy `#1`, `#3` and `#4` must not receive new hard evaluations unless
  explicitly refreshed.
- Future import/demo/parser work must preserve the single-owner assumption or
  explicitly introduce row-level ownership through a separate DB/schema task
  with backup/SHA evidence.

## UI / API Steam Connection Status Findings

- Browser Steam import UI now requires owner session before exposing connected
  Steam accounts, cursor status, import jobs, import overview or action forms.
- The template does not claim public/friends readiness and continues to frame
  Steam connection as the personal owner workflow.
- API routes remain protected by the app-level API/session posture documented
  in `docs/SECURITY.md`: non-health `/api/*` requires session or owner/operator
  Bearer `API_TOKEN`, with CSRF for session-authenticated state changes.
- API Steam status endpoints still expose instance-wide Steam/import state to
  an authorized owner/operator; they are not user-scoped APIs.

## Gaps Before Import / Demo / Parser Pipeline Work

- Explicit owner state does not exist; owner resolution remains insertion-order
  based.
- `SteamAccount.user_id` is nullable and helper-level linking can create
  legacy Steam-only users if called outside the guarded route.
- Import jobs are linked to `steam_account_id`, not directly to `user_id`.
- Match/demo/recommendation rows are not row-level owned.
- Import/demo/parser pipeline work must not assume friends/public readiness,
  multi-user isolation or playlist certainty.
- Live import, parser jobs, evaluator jobs, production DB/schema/data mutation
  and raw-demo lifecycle changes remain blocked until a future task explicitly
  authorizes them.

## MVP-002 Recommendation

MVP-002 should stay diagnostic/report-first by default. It may authorize narrow
non-DB safety-contract implementation only if the task card names exact allowed
files and avoids live import, parser jobs, raw-demo movement/deletion,
production DB/schema/data mutation, package changes and runtime/deploy changes.

Any row-level ownership, non-null ownership constraints, import-job `user_id`
backfill, or match/demo/recommendation ownership persistence belongs in a later
explicit DB/schema/data task with backup and pre/post SHA evidence.

## Checks Run

- `git status --short` before work: clean.
- `git branch --show-current`: `cona`.
- `APP_ENV=test .venv/bin/pytest tests/test_auth.py tests/test_ownership.py tests/test_security.py -q`: `27 passed, 1 warning`.
- `APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py -q`: `53 passed, 1 warning`.
- `git diff --check`: passed.

Notes:

- An initial attempt ran two pytest commands in parallel and failed due shared
  test database fixture interference (`table already exists` / `no such table`)
  between concurrent processes. The same checks were rerun sequentially and
  passed.
- The warning is the known Starlette/TestClient deprecation warning.
- Full tests/local quality gate were not run because the task card explicitly
  said not to run full tests and named focused checks for implementation.

## Safety Confirmations

- Live Steam/Valve import: not run.
- Parser jobs: not run.
- Evaluator/manual evaluator jobs: not run.
- Production DB/schema/data mutation: not performed.
- Raw demo delete/move/compress/rewrite: not performed.
- Service/deploy/runtime changes or restarts: not performed.
- Package/dependency changes: not performed.
- Public/friends readiness: not claimed.
- Secrets printed: no.
- `git add`, commit, push: not run.

## Final Status

`PASS_WITH_WARNINGS`: the scoped owner-only browser guardrail was implemented
and focused checks passed. Remaining warnings are architectural ownership
limitations that require future explicitly scoped tasks.
