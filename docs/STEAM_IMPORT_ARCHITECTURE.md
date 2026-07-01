# Steam Import Architecture

## Product Goal

The user flow should be close to Scope/Leetify:

1. User signs in with Steam OpenID.
2. User pastes the CS2 latest match share code and Game Authentication Code from Steam Support.
3. User clicks one update button.
4. The app syncs new share codes, downloads demos when possible, parses `.dem` files, and updates analytics.

Users must not provide Steam passwords, Steam Guard QR approvals, refresh tokens, or install local software.

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

1. `ICSGOPlayers_730/GetNextMatchSharingCode` returns new share codes using:
   - service Steam Web API key;
   - user's SteamID;
   - user's Game Authentication Code;
   - previous known share code.
2. The app stores each share code as a `steam_history` match row.
3. `tools/steam-gc/fetch-demo-urls.js` logs the service bot into Steam client protocol.
4. The helper launches CS2 app ID `730` in Steam presence and calls `globaloffensive.requestGame(shareCode)`.
5. The CS2 Game Coordinator returns match metadata.
6. The demo URL is read from the last `roundstatsall[].map` value.
7. The app downloads `.dem.bz2` from `replay*.valve.net`, decompresses it, and imports the `.dem` through `demoparser2`.

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
- Keep the manual `.dem` upload path as fallback.

## Current Implementation Status

- Steam OpenID linking exists.
- Steam Web API share-code sync exists.
- Service bot helper exists under `tools/steam-gc`.
- Python orchestration exists in `app/services/steam_demo_downloader.py`.
- `POST /settings/imports/pull-all` queues a `steam_import_all` job, returns the page immediately, and runs Steam sync/demo download in a background task.
- `GET /api/steam/import/overview` returns the current job and import counters for progress polling.
- `POST /api/steam/import/all` also queues the same background job instead of holding a long HTTP request.

Live demo download requires configuring a dedicated service bot account.
