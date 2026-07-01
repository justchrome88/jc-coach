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
