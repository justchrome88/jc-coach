# Worklog

## MVP v0.1

- FastAPI app with SQLite/SQLAlchemy.
- CSV/JSON import with duplicate protection.
- Dashboard, matches table, analytics, period comparison, map stats.
- Rule-based coach report.
- Coach Recommendation Tracking for "Снизить первые смерти".
- Tests and linting are wired through `pytest` and `ruff`.

## Demo Import Iteration

Implemented direct upload of official CS2 `.dem` files.

### What Works

- UI upload accepts `.dem`.
- API endpoint `POST /api/import/demo` accepts multipart `.dem`.
- Optional `player_identifier` can be a player name or SteamID.
- If no player is provided, the importer picks the player with the most kill/damage activity.
- Uploaded demos are stored in `data/uploads/`.
- Parsing uses `demoparser2`.
- Imported demo creates a normal `matches` row with:
  - kills;
  - deaths;
  - assists;
  - K/D;
  - ADR;
  - KAST best-effort;
  - headshot percent;
  - entry kills/deaths;
  - early deaths fallback;
  - utility damage best-effort;
  - flash assists best-effort.
- Recommendation tracking evaluates imported demo matches the same way as CSV/JSON matches.

### Current Limits

- Match result and side score are not reliable yet from generic `.dem` parsing, so they are left empty.
- `early_deaths` currently falls back to entry deaths until real timing/round-phase logic is tuned on real demos.
- Utility and flash metrics are best-effort because event field names can vary by demo/parser version.
- Steam share links are not implemented yet. This iteration chooses direct `.dem` upload because it can be tested locally and does not require Steam auth/session handling.

### Verification

```bash
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Upload a demo:

```bash
curl -F "file=@/path/to/match.dem" \
  -F "player_identifier=your_nickname_or_steamid" \
  http://127.0.0.1:8000/api/import/demo
```

After the first real demo arrives, test the parser on that file and tune event field mappings if needed.

## Bitvise Demo Inbox

Configured server-side inbox for user `jc`:

```text
/home/jc/cs2-demos -> /opt/jc-coach/data/incoming_demos
```

The directory is owned by `jc:jc` and writable through SFTP/Bitvise. The app lists `.dem` files from this inbox on `/upload` and can import them without browser upload.

Verification performed:

- `jc` can create a file through `/home/jc/cs2-demos`.
- `GET /api/import/demo/inbox` lists the file.
- `/upload` displays the file.
- Invalid `.dem` returns controlled `422` instead of crashing the app.

## AI Coach Provider Direction

Decision: do not hardwire OpenAI API into the product. The current AI path uses `codex_cli_handoff` because the project owner wants to start with Codex CLI as the human-in-the-loop brain and later move toward a private/local LLM.

Implemented:

- `app/services/ai_coach.py` with provider abstraction.
- Current provider: `codex_cli_handoff`.
- Future provider placeholder: `local_llm`.
- `/coach` button to prepare AI handoff.
- API endpoints:
  - `GET /api/coach/ai/payload`;
  - `POST /api/coach/ai/handoff`;
  - `GET /api/coach/ai/handoff/latest`.
- Handoff files are written to `data/ai_handoffs/`:
  - `coach_payload.json`;
  - `codex_prompt.md`;
  - `metadata.json`.

Rationale:

- The app should keep deterministic CS2 facts separate from model reasoning.
- AI should explain structured evidence, not parse demos or invent stats.
- A provider boundary lets us later connect Ollama, LM Studio, or another OpenAI-compatible local server without changing dashboard/report/mistake logic.

## Structured Mistake Detection

Implemented deterministic mistake detection as the evidence layer for AI coach:

- Categories: aim, map, crosshair placement, grenades, entry duels, survival, utility, economy.
- Mistake object includes:
  - type;
  - category;
  - severity;
  - confidence;
  - match_id when available;
  - evidence;
  - recommendation.
- `/coach` now shows category scorecards and structured mistakes.
- Match detail now shows coach breakdown and per-match mistakes.
- AI coach payload now includes `structured_mistakes` and `coach_categories`.

Current limits:

- Crosshair placement is explicitly `no_data` until parser exposes reliable view/position timeline.
- Grenade analysis is still best-effort from current utility fields.
- Economy is planned, not evaluated yet.

## Steam Auth And Import Jobs Scaffold

FACEIT is intentionally skipped in implementation for now, but remains in roadmap as required future support.

Implemented Steam scaffold:

- `User`, `SteamAccount`, and `ImportJob` tables.
- Steam OpenID login URL generation.
- Steam callback scaffold that links SteamID.
- `/settings/imports` page for connected Steam accounts and import jobs.
- Share-code import job creation.
- API endpoints:
  - `GET /api/steam/login-url`;
  - `GET /api/steam/accounts`;
  - `POST /api/steam/import/share-code`;
  - `GET /api/import/jobs`.

Current limits:

- Steam OpenID callback verification is scaffold-level and needs hardening before public production.
- Share-code jobs are queued only; real demo download/sync worker is next.
- No Steam password is requested or stored.

## AI Coach Result Persistence

Implemented:

- `coach_reports.report_type` and `coach_reports.source_ref`.
- SQLite upgrade for existing DBs.
- AI coach result saving through:
  - `/coach` form;
  - `POST /api/coach/ai/result`.
- Latest AI coach result endpoint:
  - `GET /api/coach/ai/result/latest`.
- `/coach` displays the latest saved AI coach report.

Current flow:

1. Generate Codex CLI handoff.
2. Run/paste Codex result manually.
3. Save the AI report back into the product.

Next:

- Let a local LLM provider write into the same persistence path automatically.
- Add structured sections to AI result instead of plain markdown only.

## Multi-Category Recommendation Tracking

Implemented a broader recommendation tracker instead of a single survival-only goal.

Active system goals now include:

- `survival`: reduce first/early deaths while keeping KAST/ADR.
- `aim`: raise stable ADR without losing KAST.
- `grenades`: increase utility damage and flash assists.
- `map`: stabilize weak maps through better result/entry/ADR signals.

Compatibility:

- `get_active_recommendation_progress()` still returns the survival recommendation for old UI/API behavior.
- New `get_all_recommendation_progress()` returns all active category goals.
- `/coach` now shows multi-category progress cards.
- AI coach payload includes `all_recommendations`.
- API endpoint `GET /api/recommendations` returns all category progress items.

Current limits:

- Crosshair placement remains `no_data` until parser exposes reliable view/position data.
- Category lifecycle controls are not implemented yet; system-created goals are active.
- Per-category thresholds are intentionally simple and should be tuned with real demos.

## DEM Import Confidence And Evidence

Improved official `.dem` import visibility:

- Parser now stores `event_counts`.
- Parser now stores `metric_confidence`.
- Parser now stores `parser_confidence`.
- Parser warnings explain best-effort areas:
  - score/result;
  - early deaths timing;
  - T/CT side stats;
  - utility/flash fields.
- Upload page shows a DEM import result panel with:
  - selected player;
  - match/map/score/KD/ADR;
  - parser confidence;
  - event counts;
  - metric confidence;
  - warnings;
  - link to match detail.
- Match detail now shows parser evidence from `raw_json`.

Current limits:

- Existing old DEM rows may not have confidence metadata until reimported or reparsed.
- True early-death timing and side stats still need deeper event/tick parsing.

## Local LLM Provider Scaffold

Implemented local LLM execution path behind the same AI provider boundary:

- `AI_PROVIDER=local_llm`.
- `LOCAL_LLM_BASE_URL`.
- `LOCAL_LLM_MODEL`.
- `LOCAL_LLM_TIMEOUT_SECONDS`.
- Ollama-style request path:
  - `POST /api/generate`.
- OpenAI-compatible request path:
  - `POST /v1/chat/completions`.
- Provider health endpoint:
  - `GET /api/coach/ai/provider/health`.
- Direct generation endpoint:
  - `POST /api/coach/ai/generate`.
- `/coach` includes a direct provider generation button.

Current limits:

- No local model is installed/configured by default.
- Tests mock the HTTP provider; they do not require a real LLM.
- If `codex_cli_handoff` is active, direct generation returns a controlled error and the handoff flow remains the default.

## Recommendation Lifecycle Controls

Implemented basic lifecycle controls for category recommendations:

- API:
  - `POST /api/recommendations/{recommendation_id}/status`.
- UI controls on `/coach`:
  - pause;
  - complete;
  - archive.
- Supported statuses:
  - active;
  - paused;
  - completed;
  - failed;
  - archived.

Completed/failed/archived recommendations receive `ended_at`.

Important behavior:

- System-created category recommendations are not immediately recreated after being completed/archived.
- New recommendation creation rules should later become explicit user actions.

## Localized Stats And Steam Setup

Implemented:

- Curated locale service:
  - default locale `ru`;
  - supported locales `ru` and `en`;
  - cookie-based language switch through `/language/{locale}`;
  - translated navigation and new system labels without broad auto-translation.
- Dedicated `/stats` page:
  - last N matches;
  - date range;
  - all matches;
  - core metrics;
  - trend chart;
  - period comparison;
  - data quality;
  - ADR profile;
  - source breakdown;
  - map table;
  - recent match table.
- Steam import settings improvements:
  - Russian onboarding instructions;
  - links to Steam Support CS2 and Valve Match History docs;
  - per-account Game Authentication Code form;
  - match auth code persistence;
  - `match_history_sync` import job creation;
  - manual queue sync button.

Current limits:

- Steam jobs are queued but not yet processed by a real worker.
- Match history fetching and official demo download are the next implementation layer.
- EN translation currently covers navigation and new system surfaces only; full product copy must be translated section by section.

Verification:

- `ruff check .`
- `pytest` -> 46 passed, 1 Starlette/httpx deprecation warning.

## Steam Match History Worker And Data Reset

Implemented:

- `AppSetting` table for local product settings.
- Steam Web API key storage from `/settings/imports`.
- Steam match-history worker:
  - processes `match_history_sync` import jobs;
  - calls `ICSGOPlayers_730/GetNextMatchSharingCode`;
  - follows the returned share-code chain up to `STEAM_SYNC_MAX_CODES`;
  - stores collected codes as `source=steam_history` matches;
  - updates `SteamAccount.last_share_code` and `last_sync_at`;
  - writes clear failed-job diagnostics when `STEAM_WEB_API_KEY` is missing.
- Web/API run controls:
  - `POST /settings/imports/jobs/{job_id}/run`;
  - `POST /settings/imports/run-queued`;
  - `POST /api/steam/import/jobs/{job_id}/run`;
  - `POST /api/steam/import/jobs/run-queued`.

Operational action:

- Backed up the old SQLite DB before cleanup:
  - `data/cs2_coach.before-steam-sync.20260701140552.db`.
- Removed old test/manual match data from the active DB:
  - 34 matches;
  - 4 recommendation evaluations;
  - 4 recommendations;
  - 3 reports.
- Kept the linked Steam account and import jobs.
- Ran queued Steam sync once. It failed correctly because no Steam Web API key was present in `.env` or app settings.

Current limits:

- Steam share-code discovery now works once a valid Steam Web API key is saved.
- Demo download from share code is still the next layer; saved `steam_history` rows are real Steam match references, not parsed performance stats yet.

Verification:

- `ruff check .`
- `pytest` -> 49 passed, 1 Starlette/httpx deprecation warning.

## Public Landing, Auth, Nginx And Systemd

Implemented:

- Public landing page at `/`.
- Registration page at `/register`.
- Login page at `/login`.
- Logout action at `/logout`.
- Protected product dashboard at `/dashboard`.
- Session middleware with signed cookies.
- Password hashing with `pbkdf2_sha256`.
- User model fields:
  - `email`;
  - `password_hash`;
  - `is_active`;
  - `last_login_at`.
- SQLite schema upgrade for existing `users` table.
- Web auth middleware for protected UI pages.
- Steam OpenID linking now attaches to the current logged-in user when possible.
- Nginx reverse proxy installed/configured for `jcnodex.ru`.
- Systemd service installed/enabled:
  - `jc-coach.service`;
  - app listens on `127.0.0.1:8010`;
  - nginx serves public port `80`.
- Deployment config copies:
  - `deploy/nginx/jcnodex.conf`;
  - `deploy/systemd/jc-coach.service`.
- Public deployment checklist:
  - `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`.

Operational action:

- `.env` updated locally:
  - `PUBLIC_BASE_URL=http://jcnodex.ru`;
  - `STEAM_REALM=http://jcnodex.ru`;
  - `SESSION_SECRET_KEY` generated;
  - `AUTH_COOKIE_SECURE=false` until SSL is issued.
- Certbot and nginx plugin were already installed.
- Smoke-tested through nginx with `Host: jcnodex.ru`.
- Removed smoke `@example.test` users after live auth test.

Current limits:

- HTTPS is not issued yet because router port forwarding is not ready.
- After forwarding ports `80` and `443`, run `certbot --nginx -d jcnodex.ru`, then switch `.env` to `https://jcnodex.ru` and `AUTH_COOKIE_SECURE=true`.
- Registration is open for now; invite/approval flow should be added before a wider public launch.

Verification:

- `ruff check .`
- `pytest` -> 53 passed, 1 Starlette/httpx deprecation warning.
- `nginx -t`.
- `curl -H 'Host: jcnodex.ru' http://127.0.0.1/` -> landing 200.
- anonymous `/dashboard` -> 303 `/login`.
- live registration/login/logout smoke through nginx passed.

## LAN/Public Routing With Sing-box

Adjusted network preparation without breaking Codex outbound connectivity:

- Current LAN IP is `192.168.102.129`.
- Current VM outbound IP through sing-box remains `185.141.217.101`.
- Public router IP for the site is treated as `88.201.150.73`.
- Added local `/etc/hosts` mapping:
  - `192.168.102.129 jcnodex.ru jcnodex`.
- Updated nginx `server_name`:
  - `jcnodex.ru www.jcnodex.ru jcnodex 192.168.102.129 88.201.150.73`.
- Added sing-box direct route for:
  - `88.201.150.73/32`.
- Kept sing-box `final=proxy`, so normal external traffic still exits through the existing proxy.

Verification:

- `curl https://api.ipify.org` -> `185.141.217.101`.
- `curl http://jcnodex.ru/` -> `200`, remote `192.168.102.129`.
- `curl http://192.168.102.129/` -> `200`.
- `curl http://88.201.150.73/` from the VM currently returns connection refused through direct route; likely router hairpin/forwarding behavior, while local nginx is healthy.

## Steam Pull-All MVP

Implemented:

- Server-level Steam Web API key is configured in `.env`; users do not need to create their own API keys.
- `/settings/imports` was simplified:
  - removed visible Steam API key input;
  - removed manual Share-code job block;
  - keeps only Steam connect, latest match share code, authentication code, and a single "Подгрузить все" action.
- `POST /settings/imports/pull-all` and `POST /api/steam/import/all`.
- Pull-all flow:
  - syncs Steam match history for connected accounts;
  - stores new `steam_history` share-code matches;
  - decodes share codes into `matchid`, `outcomeid`, and `token`;
  - marks matches as `demo_download_pending` when no `.dem` file is attached;
  - applies a 5-minute cooldown before re-calling Steam history API to avoid `429 Too Many Requests`.
- Existing live account sync succeeded:
  - 20 Steam share codes collected;
  - 20 `steam_history` rows decoded;
  - 20 rows marked `demo_download_pending`.

Current Steam demo import direction:

- User-facing flow stays Steam OpenID + latest match share code + Game Authentication Code.
- User Steam password, QR login, Steam Guard approval, and local software are not part of the product flow.
- Demo URL resolution is implemented through a dedicated service Steam bot account, modeled after the public behavior of Scope/Leetify-like services and the `cs-demo-downloader` open-source architecture.
- The service bot asks the CS2 Game Coordinator for metadata by share code; `.dem.bz2` is then downloaded from Valve replay hosts and imported through the existing parser.
- Manual `.dem` upload remains as fallback.
- Added architecture note: `docs/STEAM_IMPORT_ARCHITECTURE.md`.

Verification:

- `ruff check .`
- `pytest tests/test_steam_integration.py tests/test_web_smoke.py` -> 23 passed, 1 Starlette/httpx deprecation warning.

## Steam Service Bot Demo Downloader

Implemented:

- Added `tools/steam-gc/fetch-demo-urls.js`:
  - logs in only a dedicated service Steam bot account;
  - launches CS2 app `730` in Steam client presence;
  - calls CS2 Game Coordinator by share code;
  - returns replay `.dem.bz2` URLs as JSON.
- Added `app/services/steam_demo_downloader.py`:
  - selects pending `steam_history` matches;
  - calls the Node helper in batch;
  - downloads `.dem.bz2`;
  - decompresses to `.dem`;
  - imports through the existing `demoparser2` pipeline;
  - marks source Steam rows as imported or failed.
- `POST /settings/imports/pull-all` now runs:
  - Steam Web API share-code sync;
  - pending demo status marking;
  - service-bot demo download when configured.
- `POST /settings/imports/pull-all` was moved to a background job flow:
  - the page queues/reuses one active `steam_import_all` job and redirects immediately;
  - a FastAPI background task runs sync/download/import with its own DB session;
  - the UI shows current job status and refreshes while the job is queued/running.
- `POST /api/steam/import/all` now queues the same background job.
- `GET /api/steam/import/overview` exposes import counters and current job status for polling.
- Added `GET /api/steam/demo-downloader/status`.
- Updated `/settings/imports` copy and CTA to “Обновить и скачать демки”.
- Added `docs/STEAM_IMPORT_ARCHITECTURE.md`.
- Updated `instructions/03_CODEX_AGENT_RULES.md`:
  - document significant changes regularly;
  - do not use user Steam login/QR/password for server-side demo import.

Current runtime state:

- Service bot is configured:
  - `/api/steam/demo-downloader/status` -> `{"configured": true}`.
- First bot login required an email Steam Guard code once; a refresh token was saved under `data/steam_bot_credentials/refresh-token`.
- `tools/steam-gc/fetch-demo-urls.js` now calls `requestFreeLicense([730])` before launching CS2 presence. This fixed a fresh-account issue where CS2 GC ignored `ClientHello`.
- Live GC test succeeded:
  - bot logged in;
  - CS2 app `730` launched;
  - GC `ClientWelcome` received;
  - `requestGame(shareCode)` returned a Valve replay URL.
- Live replay download for existing saved matches currently fails with Valve CDN `HTTP 502`.
  - The tested match was from May 29, 2026, and current date is July 1, 2026.
  - Treat this as likely expired/unavailable replay archive, not a GC/auth failure.
  - The next practical validation needs a fresh match/share code inside Valve's replay retention window.
- User-facing Steam password/QR flow remains absent.
- Basic Auth is active at nginx:
  - no auth -> `401`;
  - `jc` credentials -> `200`.

Next step:

- Play or provide a fresh CS2 competitive/Premier match share code, then run "Обновить и скачать демки" before Valve replay CDN expires the demo.
- Later harden the bot account with mobile Steam Guard/shared secret instead of relying on password + saved refresh token.

Verification:

- `cd tools/steam-gc && npm run check`.
- `ruff check .`.
- `pytest` -> 59 passed, 1 Starlette/httpx deprecation warning.
- Helper without bot credentials returns structured JSON error.
- Helper with bot credentials reaches CS2 GC and returns a replay URL.
- `systemctl restart jc-coach` -> active.
- `curl http://127.0.0.1:8010/api/steam/demo-downloader/status` -> configured true.

## Demo Storage Lifecycle

Specification:

- Added `docs/DEMO_STORAGE_TZ.md`.
- Target lifecycle is now explicit: `download -> parse -> verify parsed payload -> delete raw .dem`.
- Raw `.dem` files are not deleted yet because final metrics/raw slices are not approved.

Implemented:

- Added `app/services/demo_storage.py`.
- Added `/settings/storage` page.
- Added `GET /api/storage/demos`.
- Added `POST /api/storage/demos/manifest`.
- Added `docs/FEATURES_RU.md` as the Russian feature list.

Current behavior:

- The storage report is observe-only.
- It counts `data/uploads` size and files.
- It classifies demo files as referenced, missing, unreferenced, suspicious.
- It lists future deletion candidates only when a parsed payload exists and raw `.dem` still exists.
- Delete policy is hard-disabled in the report until the metric schema is approved.
- Manifest writes to `data/reports/demo_storage_manifest.json`; `data/` remains untracked.

Runtime note:

- Current server disk is tight: `/` is `ext4` and was observed at 96% usage.
- `data/uploads` had about 4.5 GB of demo files during implementation.
- No demo files were deleted or compressed.

## Documentation And Roadmap Inspection

Scope:

- Reviewed implemented Steam import, background job flow, service bot downloader, storage lifecycle, deployment protection, and docs.
- Found README and roadmap still partially described Steam import as scaffold.

Updated:

- `README.md` now documents actual Steam import/demo autoload behavior, background job flow, service bot env, storage lifecycle, and current API endpoints.
- `docs/FEATURES_RU.md` now includes current live storage state and next technical focus.
- `docs/FEATURE_ROADMAP_SCORING.md` now reflects current implementation percentages for Steam import, auto import, DEM import, AI handoff, and demo storage lifecycle.
- `docs/feature_roadmap_scoring_ru.xlsx` was updated:
  - Steam / FACEIT login -> 60%;
  - Automatic match import -> 75%;
  - added Demo storage lifecycle;
  - added Steam service bot demo downloader;
  - added ImportJob background worker flow;
  - added Nginx Basic Auth + robots.txt.

Control:

- No `.env`, tokens, refresh tokens, DB files, manifests, `node_modules`, or raw demos are tracked.
