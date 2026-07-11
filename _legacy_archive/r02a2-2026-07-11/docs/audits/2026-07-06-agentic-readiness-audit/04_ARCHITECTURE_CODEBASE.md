# Architecture And Codebase

## Findings

- Runtime stack: FastAPI, Jinja2, SQLAlchemy, SQLite, pytest and Ruff.
- `docs/ARCHITECTURE.md` states the intended boundaries, but is thin compared with the current app surface.
- Web/API routes orchestrate a large amount of behavior; services carry core logic, but route files are still large and include duplicated background-job helper code.
- Startup initializes DB via `Base.metadata.create_all()` plus legacy `_upgrade_sqlite_schema()`.
- Deployment references exist for systemd, nginx, Docker and compose, but current docs limit readiness to personal/VPS use.
- `.gitignore` protects DBs, backups, uploads, reports, handoffs, credentials and caches.

## Risks

- Migration discipline is the biggest architecture risk.
- API contracts are not separately versioned or tested as contracts.
- Import/background job architecture is not durable enough for larger cap/batch behavior.
- Global settings/engine import order remains a source of DB safety risk outside pytest discipline.

## Evidence

- `pyproject.toml`
- `app/main.py`
- `app/api/routes.py`
- `app/web/routes.py`
- `app/db/models.py`
- `app/db/session.py`
- `docs/ARCHITECTURE.md`
- `docs/MIGRATIONS.md`
- `docs/DEPLOYMENT.md`
- `evidence/architecture_inventory.txt`
