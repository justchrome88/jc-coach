# Handoff

Last updated: 2026-07-04.

## Current State

- Current Product Version: `v0.4.1`
- Current WP: `WP-012 DB Contamination Guardrails`
- Next Target Version: `v0.4.2`
- Mode after WP-011B: governance/tooling layer exists; product logic and DB were not intentionally changed.
- Runtime: `jc-coach.service` should be checked at pass start with `systemctl status jc-coach --no-pager`.
- Owner recovery state: production owner currently resolves to `justchrome88@yandex.ru` (`users.id=17`) after historical `test-*@example.test` and `smoke-*@example.test` users were manually deactivated and had password hashes cleared. Current reference DB SHA for WP-012 repair start: `50af6167e0c7b1db05088bef9649db8cf29a20442d6f382af2541271bd733030`.

## Last Incident Summary

`BUGFIX-001` diagnosed `/coach` runtime 500 as a stale uvicorn process after Stage 9 route/template changes. Current source was consistent; the running process had old route code while templates were updated on disk. Required operational lesson: after Python route/template deployment, restart the service and smoke the already-running runtime. Do not treat TestClient success alone as runtime freshness evidence.

## Current Blockers

- Production/friends readiness remains blocked by DB contamination guardrails, migration discipline hardening, operational visibility and release gates.
- Recommendation planner / verified top problem is not implemented.
- Parser, Steam, metrics and AI paths remain governed by confidence and no-live-job restrictions unless a WP explicitly authorizes them.

## Next WP

`WP-012 DB Contamination Guardrails` targeting `v0.4.2`.

The next active WP is still `WP-012 DB Contamination Guardrails`.

Expected focus: protect production DB/runtime data from accidental test, import, migration or job contamination. Do not implement schema changes or production mutations unless the WP explicitly authorizes them.

Roadmap and WP wiring:

- Human docs entrypoint: `docs/README.md`
- Human docs index: `docs/project_management/DOCS_INDEX.md`
- Version roadmap: `docs/project_management/VERSION_ROADMAP.md`
- Work package backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`

Next planned versions:

- `v0.4.2`: `WP-012 DB Contamination Guardrails`
- `v0.5`: `WP-013 Personal MVP Runtime Acceptance`
- `v0.6`: `WP-014 Import Acceptance`
- `v0.7`: `WP-015 Metrics Correctness`
- `v0.8`: `WP-016 Recommendation Loop Acceptance`
- `v0.9`: `WP-017 Personal Beta`
- `v1.0`: `WP-018 Trusted MVP`

## Commands To Run First

```bash
git status --short
git log --oneline -12
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python scripts/project_gate.py preflight
python scripts/project_gate.py changed
python scripts/project_gate.py required-checks
```

If `python` is unavailable on the host, use `python3` for `scripts/project_gate.py` and report the environment gap.

## Do Not Do

- Do not change product logic outside the active WP.
- Do not change DB schema/data without explicit authorization.
- Do not run live AI, Steam, import, parser or production jobs unless explicitly authorized.
- Do not restart `jc-coach.service` unless the task requires runtime deployment/smoke and the user allows it.
- Do not commit unless the user explicitly asks.
- Do not touch `/coach`, import, metrics or recommendation logic unless the active WP says so.
