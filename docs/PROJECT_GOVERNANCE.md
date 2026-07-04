# Project Governance

## Product Versioning

Version map:

| Version | Meaning |
|---|---|
| `v0.1` | Skeleton |
| `v0.2` | Safety + Security + Ownership |
| `v0.3` | Data/Metric/AI foundation |
| `v0.4` | Coach-first UI |
| `v0.4.1` | Runtime/Auth emergency repair |
| `v0.4.2` | DB Contamination Guardrails |
| `v0.5` | Personal MVP Acceptance |
| `v0.6` | Import Acceptance |
| `v0.7` | Metrics Correctness |
| `v0.8` | Recommendation Loop Acceptance |
| `v0.9` | Personal Beta |
| `v1.0` | Trusted MVP |

The current product version is `v0.4.1`. The next target version is `v0.4.2`.

## WP Numbering

Work packages are numbered as `WP-###` and may have sub-parts such as `WP-011B`. A WP must define scope, forbidden actions, expected evidence and closeout checks before product changes begin.

Current WP for the next implementation pass: `WP-012 DB Contamination Guardrails`.

Roadmap control files:

- `docs/project_management/VERSION_ROADMAP.md`: version-to-WP sequence.
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`: WP objectives, guardians, acceptance and exit criteria.
- `docs/project_management/ACCEPTANCE_MATRIX.md`: feature acceptance by version.
- `docs/project_management/DOCS_MAP.md`: documentation ownership and stale-risk map.

## Evidence Gates

Every WP must report:

- `git status --short` baseline.
- Latest commits.
- Production DB SHA before/after when `data/cs2_coach.db` exists.
- Activated guardians and required checks.
- Tests/static checks/smoke checks run.
- Whether production DB was touched.
- Whether live jobs were run.
- Whether service was restarted.
- Files created/updated.

Use `scripts/project_gate.py` for preflight, changed-path guardian inference, required-check hints and postflight.

Acceptance checks should be cross-referenced with `docs/project_management/ACCEPTANCE_MATRIX.md` before a WP is closed.

## Bugfix Lane

Bugfixes use a separate lane when runtime is broken or user-facing behavior is failing. Diagnosis-only passes may inspect logs and status but must not mutate DB/runtime state unless the repair step is explicitly approved. Runtime incidents should create or update an audit report under `docs/audit/`.

## Codex And User Roles

- User sets WP, scope and permission boundaries.
- Codex reads control docs, infers guardians, executes only authorized work and reports evidence.
- Codex may challenge unsafe scope when DB/runtime/live-job risk is present.
- Codex must not silently expand a governance/tooling pass into product features.

## Commit Policy

- No commit unless the user explicitly asks.
- Never commit `.env`, DB files, raw demos, generated reports, handoff runtime artifacts, bot credentials, refresh tokens or `node_modules`.
- Dirty worktree entries not created by the active pass must be preserved and called out.

## DB Safety Policy

- `data/cs2_coach.db` is production runtime data unless a WP states otherwise.
- Do not run migrations, parser jobs, import jobs, Steam jobs or tests against production DB.
- Safe tests must run with `APP_ENV=test`.
- Before any future schema work, follow `docs/BACKUP_RESTORE.md` and `docs/MIGRATIONS.md`.

## Runtime Safety Policy

- Do not restart production service unless the task requires it and the user allows it.
- After route/template/runtime deployment, restart and smoke the running service before claiming runtime repair.
- TestClient evidence is source-level evidence, not proof that the already-running service is fresh.

## Test Safety Policy

- Preferred full command: `APP_ENV=test .venv/bin/pytest tests -q`.
- Static check: `.venv/bin/ruff check .`.
- Whitespace check: `git diff --check`.
- Tests must not use production DB/settings.
