# Steam Cursor Inventory

Дата: 2026-07-03.

Stage: 7 — Steam cursor truth.

## Verdict

Существующей схемы достаточно для Stage 7 code/docs/tests hardening без migrations:

- saved cursor: `steam_accounts.last_share_code`;
- one-job override: `import_jobs.requested_payload_json.known_share_code`;
- collected share-code dedupe: `matches(source="steam_history", external_match_id=<share_code>)`;
- job outcome/state: `import_jobs.status`, `error_message`, `result_json`.

Durable scheduler/retry ledger отдельной таблицей отсутствует. Это warning, не blocker для Stage 7, потому что Stage 7 не должен менять DB schema.

## Storage And State

| State | Location | Current use | Stage 7 truth |
|---|---|---|---|
| Steam account | `steam_accounts` | Owner-linked Steam identity and sync settings. | Single-owner account boundary already enforced by Stage 2. |
| Game Authentication Code | `steam_accounts.match_auth_code` | Used as `steamidkey` for `GetNextMatchSharingCode`. | Required before match-history sync. |
| Saved cursor | `steam_accounts.last_share_code` | Latest saved `CSGO-...` share-code cursor. | Primary source of truth for next Steam API `knowncode`. |
| Initial no-cursor sentinel | runtime value `knowncode=0` | Previously hidden fallback. | Explicit only as `initial_sentinel_no_saved_cursor`; not a normal latest cursor. |
| Job payload override | `import_jobs.requested_payload_json.known_share_code` | Optional known code for a job. | One-job override; does not replace saved cursor until successful sync advances it. |
| Share-code dedupe | `matches.source="steam_history"` + `external_match_id` | Placeholder rows before demo download/parser import. | Prevents duplicate collected share-code rows. |
| Job result | `import_jobs.result_json` | Stores sync/import summary. | Stores `sync_outcome`, `cursor_source`, sentinel flag and `cursor_advanced`. |

## Code Inventory

| File/function | Role | Stage 7 notes |
|---|---|---|
| `app/services/steam_integration.py::sync_match_history_job` | Processes one Steam match-history sync job. | Main cursor transition path. |
| `app/services/steam_integration.py::steam_cursor_source` | Selects known code. | New explicit source policy. |
| `app/services/steam_integration.py::advance_steam_cursor_after_success` | Advances cursor after successful local persistence. | New helper; does not advance on empty collection. |
| `app/services/steam_integration.py::classify_steam_sync_outcome` | Classifies no-new/duplicate/new outcomes. | New helper for `ImportJob.result_json`. |
| `app/services/steam_integration.py::_collect_match_share_codes` | Calls Steam Web API loop. | Not called live in Stage 7 tests; mocked in cursor tests. |
| `app/services/steam_integration.py::_get_next_match_sharing_code` | Low-level Steam Web API call. | Live network path remains runtime-only, not used in safe tests. |
| `app/services/steam_integration.py::_store_steam_share_code_match` | Inserts local `steam_history` placeholder row. | Existing dedupe via DB unique constraint. |
| `app/services/steam_integration.py::run_steam_import_all_job` | Runs sync + demo download pipeline. | Production job not run in Stage 7. |
| `app/services/steam_demo_downloader.py::download_pending_steam_demos` | Service bot demo URL/download/import path. | Not changed by Stage 7 and not run against production. |
| `app/api/routes.py` and `app/web/routes.py` | Owner/auth-protected Steam job endpoints. | Stage 1/2 protections remain; no route scope change. |

## Endpoint / Job Inventory

| Route/job | Behavior | Safety note |
|---|---|---|
| `POST /settings/imports/steam/{id}/auth-code` | Saves Game Authentication Code and latest share code, queues sync. | Browser POST protected by auth/CSRF. |
| `POST /settings/imports/steam/{id}/sync` | Queues `match_history_sync`. | Protected owner route. |
| `POST /settings/imports/jobs/{job_id}/run` | Runs one queued Steam sync job. | Protected owner route; not run in Stage 7 production. |
| `POST /settings/imports/pull-all` | Starts `steam_import_all` background path. | Protected owner route; not run in Stage 7 production. |
| `POST /api/steam/import/jobs/{job_id}/run` | API run job. | Protected by Stage 1 session/API token policy. |
| `POST /api/steam/import/all` | API pull all. | Protected by Stage 1 session/API token policy. |

## Cursor Policy

- Source of truth: `steam_accounts.last_share_code`.
- Override: `import_jobs.requested_payload_json.known_share_code` for one job only.
- Initial sentinel: `knowncode=0` only when there is no saved cursor or override.
- Advance: after Steam collection succeeds and local share-code persistence/dedupe has completed.
- No advance: no-new result, Steam/API exception, missing auth/API key, missing account, local failure before success commit.
- Duplicate: duplicate rows are not created; duplicate-only collection is recorded as `DUPLICATE_ALREADY_IMPORTED` and may advance cursor to avoid replaying the same chain.

## Outcome Semantics

| Outcome | Meaning |
|---|---|
| `SUCCESS_NEW_MATCH_IMPORTED` | New share-code rows were collected and at least one local placeholder row was inserted. |
| `SUCCESS_NO_NEW_MATCHES` | Steam returned no next share code; this is success, not failure. |
| `DUPLICATE_ALREADY_IMPORTED` | Collected share codes were already present locally; no duplicate rows created. |
| `STEAM_TEMPORARY_ERROR` | Steam/API/collection exception; job fails and cursor does not advance. |

Outcome names describe share-code collection, not guaranteed demo parser completion.

## Gaps

- No durable retry/backoff ledger.
- No production scheduler hardening.
- `link_steam_account(..., user_id=None)` remains a legacy internal Steam hardening risk from Stage 2.
- Service bot demo URL resolution/download/import remains a separate path.
- Freshness UX exists only at alpha level and can be improved after durable worker status exists.
