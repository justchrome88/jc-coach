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
