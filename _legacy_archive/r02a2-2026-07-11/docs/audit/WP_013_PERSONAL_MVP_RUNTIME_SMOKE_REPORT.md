# WP-013 Personal MVP Runtime Smoke Gate

## RESULT

PASS_WITH_WARNINGS

No P0 runtime blocker was found during service restart and read-only runtime smoke. The warning is that Codex did not execute the owner-authenticated manual browser checklist because owner credentials must not be handled in this pass. Pre-prompt logs showed a successful owner login followed by `/dashboard`, `/matches` and `/coach`, but the full checklist below still needs operator confirmation after this restart.

## Product Version Before

v0.4.2

## Product Version After Candidate

v0.5

## Runtime Checks

- Service: `jc-coach.service`
- Runtime status before restart: active/running.
- Initial uvicorn PID before restart: `107111`.
- Uvicorn PID after restart: `107945`.
- Process cwd: `/opt/jc-coach`.
- Process command: `/opt/jc-coach/.venv/bin/python /opt/jc-coach/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010`.
- App bind: `127.0.0.1:8010`.
- Worktree at baseline: clean.
- Latest commit at baseline: `948fa5f Add DB contamination guardrails`.

## Service Restart Result

- Restart command run: `systemctl restart jc-coach`.
- Restart time: `2026-07-04 16:15:45 MSK`.
- Result: service stopped cleanly, started cleanly and reached `Application startup complete`.
- Post-restart status: active/running.
- Restart journal window contained no traceback, `500`, `ERROR` or exception.

## Route Smoke Matrix

| route | auth state | expected result | actual result | pass/fail |
|---|---|---|---|---|
| `/` | anonymous | `200` | `200` | pass |
| `/login` | anonymous | `200` | `200` | pass |
| `/coach` | anonymous | redirect/login, not `500` | `303 /login` | pass |
| `/matches` | anonymous | redirect/login, not `500` | `303 /login` | pass |
| `/dashboard` | anonymous | redirect/login, not `500` | `303 /login` | pass |
| `/report` | anonymous | redirect/login, not `500` | `303 /login` | pass |
| `/upload` | anonymous | redirect/login, not `500` | `303 /login` | pass |
| `/settings/imports` | anonymous | redirect/login, not `500` | `303 /login` | pass |
| `/settings/storage` | anonymous | redirect/login, not `500` | `303 /login` | pass |

## Manual Browser Checklist

Operator checklist for owner-authenticated acceptance:

- [ ] Open `/login`.
- [ ] Login as owner.
- [ ] Open `/dashboard`.
- [ ] Open `/matches`.
- [ ] Open `/coach`.
- [ ] Open `/report`.
- [ ] Open `/upload`.
- [ ] Open `/settings/imports`.
- [ ] Open `/settings/storage`.
- [ ] Logout.
- [ ] Login again.
- [ ] After the checklist, run `journalctl -u jc-coach --since "<manual smoke start>" --no-pager` and confirm no `500`, traceback or unexpected job POSTs.

Pre-prompt runtime logs showed one failed login attempt (`400`) followed by successful login (`303`) and successful `/dashboard`, `/matches`, `/coach` page loads. That evidence is useful but incomplete because it did not cover the full checklist after the controlled restart.

## Logs Summary

Restart and read-only smoke journal window:

- clean shutdown of PID `107111`;
- clean startup of PID `107945`;
- `Application startup complete`;
- read-only `GET` requests returned `200` or `303`;
- no `500`;
- no traceback;
- no `ERROR`;
- no live job POSTs.

The log grep matched `/settings/imports` because it contains the word `import`, but those entries were anonymous `GET` redirects to `/login`, not import job execution.

## DB Mutation Summary

- SHA before restart/smoke: `0850e6a28b08e4150cff43e10fbd39f38bef3e3ca3e494ab5a534c22738a230d`.
- SHA after unauthenticated smoke: `0850e6a28b08e4150cff43e10fbd39f38bef3e3ca3e494ab5a534c22738a230d`.
- SHA after authenticated smoke if performed: not performed by Codex.
- Expected mutations: owner `POST /login` may update `users.last_login_at`.
- Unexpected mutations during Codex smoke: none detected by DB SHA.
- DB row count checks stayed stable during read-only smoke:
  - `users_total=254`
  - `import_jobs_total=12`
  - `queued_running_import_jobs=2`
  - `recommendations_total=4`
  - `reports_total=0`

## Test/Smoke User Contamination Check

- Active credentialed `test-*@example.test` users: `0`.
- Active credentialed `smoke-*@example.test` users: `0`.
- Historical inactive/non-credentialed test/smoke rows remain present by design from WP-012 and were not cleaned up in this pass.

## Hidden Live Jobs Check

- No live AI, Steam, import or parser jobs were started by Codex.
- Runtime journal since restart showed no job-triggering POSTs.
- DB counts for import jobs, recommendations and reports did not change during read-only smoke.
- Existing `queued_running_import_jobs=2` is pre-existing state, not created by this smoke.

## P0 Blockers

None found in restart/read-only smoke.

## P1 Risks

- Full owner-authenticated manual browser checklist was not executed by Codex after restart.
- Existing `queued_running_import_jobs=2` should be reviewed in WP-014/import acceptance to distinguish queued backlog from active runtime work.
- Owner policy remains single-owner/insertion-order based until explicit owner state is implemented in a later WP.
- Friends/public readiness remains blocked by security/observability/release gates.

## Can Promote To v0.5

yes, as `PASS_WITH_WARNINGS` for controlled personal/VPS use.

The bounded warning is that the operator should complete and record the full manual owner browser checklist after this restart before treating v0.5 as fully exercised by hand.

## Next Recommended WP

`WP-014 Import Acceptance`, with an initial check of the existing queued/running import job state before any live import/parser/Steam work is authorized.
