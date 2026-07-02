> СТАТУС: ВСПОМОГАТЕЛЬНЫЙ / ЧАСТИЧНО АКТУАЛЬНЫЙ / НЕ SOURCE OF TRUTH
> Канонический источник: `docs/PROJECT_CONTROL.md` и `docs/STEAM_IMPORT.md`.
> Не использовать этот файл как текущий план реализации, если `PROJECT_CONTROL` явно на него не ссылается.

# Steam Import Architecture

## Product Goal

The user flow should be close to Scope/Leetify:

1. User signs in with Steam OpenID.
2. User pastes the CS2 latest match share code and Game Authentication Code from Steam Support.
3. User clicks one update button.
4. The app syncs new share codes, downloads demos when possible, parses `.dem` files, and updates analytics.

Users must not provide Steam passwords, Steam Guard QR approvals, refresh tokens, or install local software.

Important constraint: the service bot cannot enumerate a user's private match history by itself. Valve's match-history
API still needs the user's SteamID, Game Authentication Code, and a valid `knowncode`/latest share-code cursor from
Steam Support. In live testing on 2026-07-02, calling `GetNextMatchSharingCode` with `knowncode=0` returned
`HTTP 412 Precondition Failed`, so the app must not assume OpenID + auth code is enough for first sync.

## Accepted Architecture

The app uses two separate Steam concepts:

- User authorization data:
  - SteamID from Steam OpenID.
  - Game Authentication Code from Steam Support.
  - Latest match share code.
  - Steam Web API key configured server-side.
- Service bot:
  - A dedicated Steam account controlled by the service.
  - Empty inventory and no personal use.
  - Used only to ask the CS2 Game Coordinator for demo metadata by share code.

The service bot is not the user's account. The user never sends Steam credentials to JC Coach.

## Data Flow

1. User supplies the latest share-code cursor shown by Steam Support. This is a one-time bootstrap value, not a
   per-match manual import step.
2. `ICSGOPlayers_730/GetNextMatchSharingCode` returns new share codes using:
   - service Steam Web API key;
   - user's SteamID;
   - user's Game Authentication Code;
   - previous known share code.
3. The app stores each share code as a `steam_history` match row.
4. `tools/steam-gc/fetch-demo-urls.js` logs the service bot into Steam client protocol.
5. The helper launches CS2 app ID `730` in Steam presence and calls `globaloffensive.requestGame(shareCode)`.
6. The CS2 Game Coordinator returns match metadata.
7. The app extracts `match_time` from Game Coordinator metadata and stores it as the authoritative match date.
8. The demo URL is read from the last `roundstatsall[].map` value.
9. The app downloads `.dem.bz2` from `replay*.valve.net`, decompresses it, and imports the `.dem` through `demoparser2`.

## Cursor Diagnostics

- Store and display the currently saved latest share-code cursor.
- Resolve the cursor through Steam GC when importing and persist `steam_metadata.played_at`.
- If the cursor's `match_time` is older than the latest imported match, surface a warning in `/settings/imports`.
- Do not silently download history behind an old cursor; skip candidates whose Steam GC `match_time` is not newer than
  the latest imported match.
- Do not ask users for a share code for every match. The intended model is one bootstrap cursor, then automatic sync.

## Match Date Policy

Steam-imported matches must use Steam metadata for calendar time:

1. Primary source: CS2 Game Coordinator `match_time` returned by `globaloffensive.requestGame(shareCode)`.
2. Stored value: `Match.played_at`, `raw_json.played_at`, and `raw_json.played_at_source = "steam_gc_match_time"`.
3. `.dem` parser fallback: allowed only when Steam metadata is unavailable; mark it as `file_modified_fallback`.
4. The fallback date is not a match date. It can be CDN file time, filesystem mtime, or import time.
5. Sorting and analytics should prefer `Match.played_at`, but UI/API must expose `played_at_source` so inaccurate dates are visible.

The `.dem` file is the source of gameplay statistics, not the source of truth for match time.

## Code Quality Rules

- Keep Steam date parsing isolated in `app/services/steam_match_metadata.py`.
- Keep `app/services/demo_parser.py` focused on parsing demo events/statistics.
- Pass Steam metadata into `import_demo_file(..., steam_metadata=...)`; do not infer Steam match dates from filenames or local upload time.
- Preserve raw Steam metadata in `steam_history.raw_json.steam_metadata` for debugging.
- Tests must cover timestamp normalization and the handoff from Steam downloader to demo import.

## Required Environment

Minimum:

- `STEAM_WEB_API_KEY`
- `STEAM_BOT_REFRESH_TOKEN`

Alternative bot login:

- `STEAM_BOT_USERNAME`
- `STEAM_BOT_PASSWORD`
- `STEAM_BOT_SHARED_SECRET`

`STEAM_BOT_TWO_FACTOR_CODE` exists only for short local tests and should not be used for production automation.

## Security Rules

- Never use a user's Steam password, QR login, or refresh token.
- Never commit `.env`, service bot credentials, refresh tokens, demos, or downloaded archives.
- Use a dedicated service bot account with no inventory and no personal value.
- Rate limit share-code and GC requests.
- Do not rely on manual `.dem` upload for Steam matchmaking/premier import. It is not the target product flow because it cannot reliably provide match dates by itself.

## Current Implementation Status

- Steam OpenID linking exists.
- Steam Web API share-code sync exists.
- Service bot helper exists under `tools/steam-gc`.
- Python orchestration exists in `app/services/steam_demo_downloader.py`.
- Steam GC match-time normalization exists in `app/services/steam_match_metadata.py`.
- `POST /settings/imports/pull-all` queues a `steam_import_all` job, returns the page immediately, and runs Steam sync/demo download in a background task.
- `GET /api/steam/import/overview` returns the current job and import counters for progress polling.
- `POST /api/steam/import/all` also queues the same background job instead of holding a long HTTP request.

Live demo download requires configuring a dedicated service bot account.
