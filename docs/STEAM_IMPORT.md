# Steam Import

Last updated: 2026-07-04.

Canonical supporting docs:

- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/STEAM_MATCH_DATES_RU.md`

## Accepted Flow

1. User signs in with Steam OpenID.
2. User provides Game Authentication Code and latest `CSGO-...` share-code cursor from Steam Support.
3. Server operator configures `STEAM_WEB_API_KEY`.
4. Dedicated service bot resolves known share codes through the CS2 Game Coordinator.
5. App downloads `.dem.bz2`, decompresses to `.dem`, imports through parser and stores Steam GC `match_time` as authoritative `played_at`.

## Primary v0.6 Target

The primary `v0.6` import is one-button Steam/Valve import from the logged-in owner's import/settings page. Manual demo upload is secondary and exists for parser fixtures/debugging.

Required primary behavior:

- the user opens `/settings/imports` and clicks "Обновить и скачать демки";
- the app validates a connected Steam account;
- the app validates the Game Authentication Code and latest share-code cursor;
- an `import_job` exists before any Steam, demo download or parser work begins;
- new share codes or match references are fetched from Valve/Steam;
- duplicates are skipped without creating duplicate match records;
- demos are downloaded only for new or missing matches;
- demos are parsed with current parser capabilities and weak/unavailable facts stay governed by Metric Truth;
- parsed data and match records are persisted before any future cleanup;
- current policy retains raw demo files for parser development by default;
- future delete-after-success mode may delete raw demos only after successful parse and DB persistence, but it is disabled now;
- failed demos are classified as failed/quarantine/cleanup-policy-needed;
- statuses distinguish success, no-new, need-code, Steam-not-connected, rate-limited, download-failed, parser-failed, partial-success, duplicate-skipped and exact match-date available/unavailable.

Exact match date means the actual match datetime from Valve/Steam/demo metadata. Job creation time, download time, parser time, DB creation time and file mtime must not be presented as match date.

## Current Status

Steam import is an alpha path, not production-ready.

WP-014A diagnosis found that the current one-button UI and backend path exist, but `v0.6` acceptance is blocked by incomplete status taxonomy, incomplete `import_job` coverage for exact share-code download/parser work, missing persisted raw-demo cleanup after successful parse/persist, weak failed-demo cleanup policy and inconsistent exact-date availability surfacing. See `docs/audit/WP_014A_STEAM_VALVE_IMPORT_DIAGNOSIS.md`.

WP-014B1 repaired import-job truth/status taxonomy without changing schema or demo cleanup lifecycle. The primary `steam_import_all` job now records `overall_outcome`, `statuses`, `clean_success`, `error_message` and the existing-status limitation in `result_json`. Exact share-code import is tracked by a `share_code_import` job before downloader/parser work, but remains a non-primary debug/manual path.

Standardized result statuses:

- `success`;
- `no_new`;
- `need_code`;
- `steam_not_connected`;
- `rate_limited`;
- `download_failed`;
- `parser_failed`;
- `partial_success`;
- `duplicate_skipped`;
- `exact_match_date_available`;
- `exact_match_date_unavailable`;
- `approximate_match_date`.

`ImportJob.status` still has only `queued`, `running`, `succeeded` and `failed`. Clean `success`, `no_new` and `duplicate_skipped` outcomes may use `succeeded`. Partial success is represented in `result_json.overall_outcome/statuses` and persisted as `failed` to avoid clean-success overclaim until a future schema/status migration is explicitly approved.

WP-014B2 repaired exact match-date truth without changing schema or demo cleanup lifecycle. For the primary Steam/Valve path, `Match.played_at` is exact only when Steam GC metadata provides valid `match_time` with source `steam_gc_match_time`. If Steam GC `match_time` is missing, primary Steam import records `exact_match_date_unavailable`, clears the imported match `played_at` instead of retaining parser/file-mtime fallback as a match date, and records date truth in `raw_json`/`result_json`. Steam freshness comparison now uses only exact imported Steam dates; manual/file-mtime fallback dates do not silently block new Steam imports.

WP-014B3 made demo retention explicit without enabling deletion. Current policy is `retain_raw_for_parser_development`; successful imports record `retained_for_parser_dev`, parser failures record `retained_after_failure` or `cleanup_needed`, and result/raw JSON include raw demo path/size when available. `delete_after_success` remains disabled by default and is future production mode after parser acceptance.

WP-014C live one-button acceptance failed. One authorized click on `/settings/imports` -> `POST /settings/imports/pull-all` created parent job `#15` and child `match_history_sync` job `#16`. The child sync succeeded, but the parent remained `running` with null `result_json` while multiple large raw demos were retained. `data/uploads` grew from `68K` to `3.1G`, root free space fell to `508M`, graceful service restart hung waiting for background tasks, and a force kill was required to protect the host. No production demo files were deleted and no schema changes were made. Do not repeat live one-button acceptance until disk budget/batch caps, incremental parent progress/result truth and clean interruption handling are repaired.

Stage 1 security hardening verifies Steam OpenID callback assertions through Steam `check_authentication` before linking an account. A callback that only provides a `claimed_id` is rejected.

Stage 2 ownership hardening requires current owner session for `/auth/steam/callback`. Без owner session callback не создаёт uncontrolled user, `steam_accounts` или `import_jobs`. При owner session Steam account линкуется только к owner user.

Stage 7 Steam cursor truth hardening documents and tests deterministic cursor transitions without live Steam calls, production jobs, production DB mutation or schema changes.

## Cursor Source Of Truth

- `steam_accounts.last_share_code` is the saved latest share-code cursor for the owner-linked Steam account.
- `import_jobs.requested_payload_json.known_share_code` may override the saved cursor for that one job only.
- `knowncode=0` is not a normal latest cursor. It is allowed only as `initial_sentinel_no_saved_cursor` when the account has no saved `last_share_code`.
- Steam GC `match_time`, not the share-code string itself, remains the authoritative match date once the service bot resolves metadata.
- Existing `matches(source="steam_history", external_match_id=<share_code>)` rows are the dedupe surface for collected share codes.

## Cursor Advance Rules

- On successful match-history sync with new collected share codes, the app stores/dedupes local `steam_history` rows first and then advances `steam_accounts.last_share_code` to the last collected code.
- On successful sync with no new share codes, the cursor is not changed and the outcome is `SUCCESS_NO_NEW_MATCHES`.
- On duplicate-only sync, no duplicate rows are created; the cursor may advance to the duplicate collected code to avoid reprocessing the same chain. The outcome is `DUPLICATE_ALREADY_IMPORTED`.
- On Steam/API failure or local persistence failure, the job fails and the cursor is not advanced.
- Manual exact share-code import still sets `last_share_code` to the submitted code because that action is an explicit operator mutation.

## Sync Outcome Semantics

`ImportJob.result_json` for match-history sync records:

- `sync_outcome`: `SUCCESS_NEW_MATCH_IMPORTED`, `SUCCESS_NO_NEW_MATCHES`, `DUPLICATE_ALREADY_IMPORTED` or `STEAM_TEMPORARY_ERROR`.
- `cursor_source`: `job_requested_payload`, `steam_account.last_share_code` or `initial_sentinel_no_saved_cursor`.
- `knowncode_zero_is_initial_sentinel`: `true` only for the initial no-cursor case.
- `cursor_advanced`: whether `steam_accounts.last_share_code` changed after successful local persistence.

These names describe Steam share-code collection state, not guaranteed demo parser/import completion. Demo download and parser import remain separate explicit steps.

## Retry / Backoff Policy

Stage 7 does not add a durable scheduler or retry ledger. Current retry policy is operator-driven:

- failed jobs keep `status=failed`, `error_message` and `result_json.sync_outcome`;
- queued jobs can be retried by owner/operator-protected routes;
- no automatic production Steam job was introduced;
- future scheduler work must keep no-new/duplicate/error outcomes distinct and must not advance the cursor after failed external or local writes.

## Known Risks

- Service bot cannot enumerate private user history by itself.
- `knowncode=0` is only an initial sentinel when no saved cursor exists; it is not a valid substitute for a latest cursor and can fail.
- Stale cursor can point behind already imported history.
- Valve replay URLs can expire or return transient 502/404/410.
- Durable retry/backoff, scheduler behavior and a sync ledger still need hardening.
- One-button live import currently lacks a safe disk budget/batch cap for retain-raw mode and can exhaust VPS disk headroom.
- Parent aggregate job progress/result truth is insufficient during long downloads; interruption can leave `steam_import_all` stuck as `running` with null `result_json`.
- Graceful shutdown does not currently cancel/fail active import work promptly enough for operator safety.
- Steam OpenID network verification can fail closed if Steam is unreachable.
- Low-level helper `link_steam_account(..., user_id=None)` still supports legacy Steam-only user creation for old service paths; public OpenID callback no longer uses this path without owner.

## Product Rule

Do not turn Steam import into manual share-code entry for every match. The target UX is one-time onboarding plus background sync with clear cursor freshness diagnostics.
