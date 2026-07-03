# Stage 7 Steam Cursor Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 7 выполняет основной scope: Steam cursor source/advance/no-advance semantics стали явными, `knowncode=0` больше не является скрытой магией, new/no-new/duplicate/Steam exception cases покрыты mock-only тестами, production DB не изменилась, live Steam/API calls и production Steam/import/parser jobs не запускались.

Статус не `PASS`, потому что `ImportJob.result_json.sync_outcome` детерминирован для Stage 7 cursor scenarios, но не для всех ранних failure paths в `sync_match_history_job()` (`missing account`, `missing Game Authentication Code`, `missing STEAM_WEB_API_KEY`). Эти пути всё ещё возвращают `error_message` через `_fail_job()` без `sync_outcome`. Это не ломает cursor safety и не является blocker before Stage 8, но должно быть учтено в later Steam worker/retry ledger hardening.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | Steam cursor inventory exists and is accurate | PASS | `docs/audit/STEAM_CURSOR_INVENTORY.md` фиксирует storage, code paths, endpoints/jobs, cursor policy, outcomes and gaps. |
| 2 | source of truth documented | PASS | `docs/STEAM_IMPORT.md` and `docs/PROJECT_CONTROL.md` document saved cursor, one-job override and sentinel policy. |
| 3 | `steam_accounts.last_share_code` действительно является saved cursor | PASS | `steam_cursor_source()` reads `account.last_share_code`; `advance_steam_cursor_after_success()` writes it after successful collection/persistence. |
| 4 | `import_jobs.requested_payload_json.known_share_code` является one-job override | PASS | `sync_match_history_job()` passes payload `known_share_code` into `steam_cursor_source()`. The payload value is used for that job's `known_code`; it is not directly persisted as `last_share_code`. |
| 5 | `knowncode=0` explicit and only initial sentinel | PASS | `steam_cursor_source()` returns `STEAM_INITIAL_CURSOR_SENTINEL` only when no payload override and no saved `last_share_code` exist. Test covers initial case. |
| 6 | cursor advances only after successful Steam collection and local persistence | PASS | Code calls `_collect_match_share_codes()`, then `_store_steam_share_code_match()` for collected codes, then `advance_steam_cursor_after_success()`. Tests cover successful advance. |
| 7 | failed Steam response does not advance cursor | PASS | `test_failed_steam_response_does_not_advance_cursor` raises from mocked collector and verifies saved cursor unchanged. |
| 8 | duplicate/no-new/error outcomes documented and tested | PASS | `docs/STEAM_IMPORT.md`, inventory and tests cover `SUCCESS_NO_NEW_MATCHES`, `DUPLICATE_ALREADY_IMPORTED`, `STEAM_TEMPORARY_ERROR`. |
| 9 | `ImportJob.result_json` semantics are deterministic | PASS_WITH_WARNING | Deterministic for Stage 7 cursor scenarios. Early guard failures still use `error_message` without `sync_outcome`. |
| 10 | tests are mocked and do not perform live Steam calls | PASS | `tests/test_steam_cursor_truth.py` monkeypatches `_collect_match_share_codes`; existing OpenID tests monkeypatch `urlopen`. |
| 11 | no production Steam/import/parser jobs run | PASS | Review ran only requested pytest/ruff/diff/SHA commands. |
| 12 | no production DB mutation | PASS | Production DB SHA remained unchanged. |
| 13 | no schema changes | PASS | No model/migration/schema helper changes in diff. |
| 14 | Stage 1 security behavior still passes | PASS | Security tests in requested bundle passed. |
| 15 | Stage 2 ownership behavior still passes | PASS | Ownership tests in requested bundle passed. |
| 16 | full safe pytest passes | PASS | `APP_ENV=test .venv/bin/pytest tests -q`: `130 passed, 1 warning`. |
| 17 | ruff passes | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 18 | git diff --check passes | PASS | `git diff --check`: passed, no output. |
| 19 | no parser hardening | PASS | No parser modules changed; no production parser jobs run. |
| 20 | no AI validator | PASS | No AI modules or validator/provider/schema-output changes. |
| 21 | no recommendation planner | PASS | No recommendation planner/problem snapshot work. |
| 22 | no UI redesign | PASS | No templates/CSS/frontend redesign changes. |

## Cursor Truth Review

- Source of truth: `steam_accounts.last_share_code` is the saved cursor; `import_jobs.requested_payload_json.known_share_code` is a per-job override; `matches(source="steam_history", external_match_id=<share_code>)` is the dedupe surface.
- Cursor advances after `_collect_match_share_codes()` returns collected codes and local `_store_steam_share_code_match()` has processed them; it is set to the last collected code.
- Cursor does not advance for no-new result, failed Steam collector response, missing account/auth/API key guard paths, or empty collection.
- Duplicate case: duplicate rows are not created; duplicate-only collection returns `DUPLICATE_ALREADY_IMPORTED` and may advance cursor to the duplicate collected code to avoid replaying that chain.
- No-new case: returns success with `SUCCESS_NO_NEW_MATCHES`, zero collected and `cursor_advanced=false`.
- Error case: mocked Steam/collection exception returns failed job with `STEAM_TEMPORARY_ERROR` and keeps cursor unchanged.
- `knowncode=0` no longer remains ambiguous in the Stage 7 path: it is named `initial_sentinel_no_saved_cursor` and appears only when no saved cursor/override exists.
- `ImportJob.result_json` outcome semantics are deterministic for Stage 7 cursor scenarios. Warning: early guard failures still rely on `error_message` without `sync_outcome`.

## Live Steam / Job Safety Review

- Live Steam calls made: no.
- Production Steam/import/parser jobs run: no.
- Tests use only mocked paths for Stage 7 cursor behavior: yes. `tests/test_steam_cursor_truth.py` monkeypatches `_collect_match_share_codes`; no test performs live `GetNextMatchSharingCode` calls.

## Legacy Steam Link Risk Review

- `link_steam_account(..., user_id=None)` status: still exists in `app/services/steam_integration.py` and can create a legacy Steam-only `User` if called directly without `user_id`.
- Public reachability: not reachable from public OpenID callback without owner session. `app/web/routes.py::steam_auth_callback` requires `current_user_from_session()` and calls `link_steam_account(..., user_id=owner.id)`.
- Owner-boundary impact: acceptable legacy internal risk for Stage 7. Stage 2 owner boundary remains intact for public callback and protected Steam job routes.
- Can it create uncontrolled user/account/job: yes if service code/tests directly call `link_steam_account()` without `user_id`; no unsafe public/authenticated Steam cursor route reviewed in Stage 7 does that.
- Blocker before Stage 8: no. It remains a later Steam hardening cleanup item, not a cursor truth blocker.

## Schema Change Review

No schema changes.

Confirmed:

- no `app/db/models.py` change;
- no migrations/Alembic files;
- no tables/columns/indexes/constraints added;
- no startup schema helper change;
- production DB SHA unchanged.

## Scope Creep Review

- Parser hardening: no.
- AI validator: no.
- Recommendation planner: no.
- UI redesign: no.

## Changed Files Reviewed

Tracked diff reviewed:

- `app/services/steam_integration.py`
- `docs/CHANGELOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_CONTROL.md`
- `docs/ROADMAP.md`
- `docs/STEAM_IMPORT.md`
- `docs/TESTING.md`
- `tests/test_steam_integration.py`

Untracked Stage 7 files reviewed:

- `docs/audit/STAGE_7_STEAM_CURSOR_IMPLEMENTATION_REPORT.md`
- `docs/audit/STEAM_CURSOR_INVENTORY.md`
- `docs/tasks/STABILIZATION_STAGE_7_STEAM_CURSOR_TZ_CS2_AI_COACH.md`
- `tests/test_steam_cursor_truth.py`

## Test Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_cursor_truth.py -q
```

Result: `5 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_security.py tests/test_ownership.py tests/test_steam_cursor_truth.py -q
```

Result: `45 passed, 1 warning`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `130 passed, 1 warning`.

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`.

```bash
git diff --check
```

Result: passed, no output.

## Production DB Check

```bash
sha256sum data/cs2_coach.db
```

Result:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

Production DB SHA unchanged from Stage 7 preflight and implementation report.

## Import/Steam/Parser Jobs Check

No production import, Steam or parser jobs were run.

The review ran only safe pytest, ruff, `git diff --check` and SHA checks. Stage 7 tests use mocked Steam collection paths and test DB isolation.

## Remaining Risks

- No durable Steam sync ledger or retry/backoff scheduler exists.
- Early guard failures in `sync_match_history_job()` do not yet write a structured `sync_outcome` into `ImportJob.result_json`.
- Outcome names describe share-code collection, not guaranteed demo download/parser completion.
- Service bot demo URL resolution/download/import remains a separate explicit path.
- `knowncode=0` can still fail against Steam in the initial no-cursor case; it is now explicit and documented.
- Legacy `link_steam_account(..., user_id=None)` remains an internal service-level risk.

## Must Fix Before Stage 8

No blocker found before Stage 8 if Stage 8 does not require durable Steam worker ledger/schema changes.

Recommended follow-ups:

- In later Steam worker/retry hardening, add structured outcomes for missing account/auth/API key and any parse/import-specific failure categories.
- Keep durable retry ledger/scheduler work separate unless Stage 8 explicitly authorizes schema changes.
- Remove or restrict production use of `link_steam_account(..., user_id=None)` in a later Steam hardening cleanup.

## Can Proceed To Stage 8

yes
