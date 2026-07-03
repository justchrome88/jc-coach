# Steam Import

Last updated: 2026-07-03.

Canonical supporting docs:

- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/STEAM_MATCH_DATES_RU.md`

## Accepted Flow

1. User signs in with Steam OpenID.
2. User provides Game Authentication Code and latest `CSGO-...` share-code cursor from Steam Support.
3. Server operator configures `STEAM_WEB_API_KEY`.
4. Dedicated service bot resolves known share codes through the CS2 Game Coordinator.
5. App downloads `.dem.bz2`, decompresses to `.dem`, imports through parser and stores Steam GC `match_time` as authoritative `played_at`.

## Current Status

Steam import is an alpha path, not production-ready.

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
- Steam OpenID network verification can fail closed if Steam is unreachable.
- Low-level helper `link_steam_account(..., user_id=None)` still supports legacy Steam-only user creation for old service paths; public OpenID callback no longer uses this path without owner.

## Product Rule

Do not turn Steam import into manual share-code entry for every match. The target UX is one-time onboarding plus background sync with clear cursor freshness diagnostics.
