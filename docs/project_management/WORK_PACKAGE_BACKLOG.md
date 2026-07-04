# Work Package Backlog

Last updated: 2026-07-04.

This backlog defines the planned WP sequence from `v0.4.2` to `v1.0`. It is a governance artifact, not implementation approval. Each WP still needs an explicit user prompt before changes begin.

## WP-012

| Field | Value |
|---|---|
| id | `WP-012` |
| title | DB Contamination Guardrails |
| target version | `v0.4.2` |
| status | completed / `PASS_WITH_WARNINGS` |
| objective | Prevent accidental production DB/runtime data contamination from tests, imports, parser/Steam jobs, migrations and smoke checks. |
| guardians | `DB_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN`, `RUNTIME_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/BACKUP_RESTORE.md`, `docs/TESTING.md`, `docs/MIGRATIONS.md`, `docs/PROJECT_GOVERNANCE.md`, `docs/HANDOFF.md` |
| forbidden actions | Production DB mutation, schema changes without explicit approval, live Steam/import/parser/AI jobs, service restart unless authorized, product features. |
| acceptance criteria | Production DB path is guarded from tests and unsafe jobs; smoke guidance separates read-only checks from login/write checks; DB SHA evidence is required before/after risky commands; manual backups are classified as runtime artifacts. |
| required evidence | `project_gate` preflight/changed/required-checks/postflight, DB SHA before/after, safe test evidence if code changes, no-live-jobs statement, audit report. |
| exit criteria | DB contamination paths are documented or guarded, required checks are green, production DB SHA impact is explained, next WP can run without ambiguity. |
| next WP | `WP-013 Personal MVP Runtime Acceptance` |

## WP-013

| Field | Value |
|---|---|
| id | `WP-013` |
| title | Personal MVP Runtime Acceptance |
| target version | `v0.5` |
| status | completed / `PASS_WITH_WARNINGS` |
| objective | Accept the controlled personal runtime across login/logout, dashboard, matches, `/coach`, reports and clean logs with no hidden live jobs. |
| guardians | `RUNTIME_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN`, `DB_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/TESTING.md`, `docs/audit/BUGFIX_001_COACH_RUNTIME_FAILURE_DIAGNOSIS.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | New features, broad UI redesign, live AI/Steam/import/parser jobs, production DB writes outside explicitly accepted runtime flows. |
| acceptance criteria | Auth flow works; dashboard, matches, `/coach`, reports load; service logs are clean; runtime freshness is verified after deploy/restart; page loads do not start hidden jobs. |
| required evidence | Service status, runtime smoke plan/results, log excerpts, DB SHA before/after smoke, safe tests for touched code, no-live-jobs statement. |
| exit criteria | Personal runtime can be used safely on VPS with known warnings and no unresolved P0 runtime blockers. Full owner manual browser checklist remains operator evidence to record after restart. |
| next WP | `WP-014 Import Acceptance` |

## WP-014

| Field | Value |
|---|---|
| id | `WP-014` |
| title | Import Acceptance |
| target version | `v0.6` |
| status | active; WP-014B1/B2/B3 repairs complete; WP-014C live acceptance failed; WP-014D1 storage guard/batch cap repair complete; WP-014D2 parent checkpoint/interruption repair complete; WP-014D3 stale job repair complete; repeat live acceptance required |
| objective | Accept the one-button Steam/Valve import as the primary workflow: connected Steam account, match/auth code, truthful import_job, duplicate/no-new/error states, exact match-date truth and raw demo cleanup after successful parse/persist. |
| guardians | `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `TEST_GUARDIAN`, `RUNTIME_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/STEAM_IMPORT.md`, `docs/DEMO_DEEP_PARSER_TZ_RU.md`, `docs/DEMO_STORAGE_TZ.md`, `docs/TESTING.md`, `docs/BACKUP_RESTORE.md` |
| forbidden actions | Live Steam calls, real demo downloads/parses or production import jobs unless the WP explicitly authorizes them with backup and DB evidence. |
| acceptance criteria | One-button import records clear success/no-new/need-code/Steam-not-connected/rate-limited/download-failed/parser-failed/partial-success/duplicate-skipped/interrupted outcomes; duplicate protection is verified; exact match date is stored from Steam GC metadata or explicitly unavailable; current raw demo policy is explicit retain-by-default with file/DB consistency metadata; future delete-after-success remains disabled until parser acceptance. Live acceptance additionally requires disk budget/batch caps, incremental parent job truth and clean interruption handling. WP-014B1 covers job truth/status taxonomy; WP-014B2 covers exact match-date truth; WP-014B3 covers retention policy/metadata; WP-014D1 covers storage budget/batch caps; WP-014D2 covers parent checkpoints and stale/interrupted handling; WP-014D3 repaired failed job `#15`. Repeat live acceptance is still required. |
| required evidence | WP-014A diagnosis, mocked tests by default, live-job authorization if any, DB SHA before/after, import job result examples, cursor mutation status, demo cleanup evidence, audit report. |
| exit criteria | The primary one-button Steam/Valve import is safe enough for controlled personal operation, including bounded disk usage and truthful interrupted-job handling, with manual demo upload documented as a secondary parser/debug path and remaining alpha limitations explicit. |
| next WP | `WP-015 Metrics Correctness` |

## WP-015

| Field | Value |
|---|---|
| id | `WP-015` |
| title | Metrics Correctness |
| target version | `v0.7` |
| status | planned |
| objective | Establish golden fixtures, trusted metrics and weak metric labeling. |
| guardians | `METRICS_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/METRICS.md`, `docs/audit/METRIC_TRUTH_INVENTORY.md`, `docs/audit/PARSER_FACTS_INVENTORY.md`, `docs/RECOMMENDATIONS.md`, `docs/AI_COACH.md` |
| forbidden actions | Upgrading weak metrics without fixture evidence, using unavailable metrics for hard claims, live AI/import/parser jobs without explicit authorization. |
| acceptance criteria | Golden fixtures exist for accepted metrics; trusted/medium/approximate/low/unavailable labels are enforced; weak metrics are visibly labeled or suppressed; AI/recommendation paths follow Metric Truth. |
| required evidence | Metric fixture results, Metric Truth tests, AI validator/recommendation evidence tests as applicable, no unsupported metric claims. |
| exit criteria | Accepted metrics are reliable enough to support serious recommendation evidence within documented limits. |
| next WP | `WP-016 Recommendation Loop Acceptance` |

## WP-016

| Field | Value |
|---|---|
| id | `WP-016` |
| title | Recommendation Loop Acceptance |
| target version | `v0.8` |
| status | planned |
| objective | Accept recommendation -> next match -> evaluation -> progress as a coherent loop. |
| guardians | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN`, `DB_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/RECOMMENDATIONS.md`, `docs/METRICS.md`, `docs/AI_COACH.md`, `docs/PROJECT_CONTROL.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | Planner claims without verified evidence, hidden writes on GET/read paths, AI overclaims, schema changes without explicit migration scope. |
| acceptance criteria | One primary recommendation is evidence-backed; next-match action is visible; evaluation updates progress through explicit write paths; weak metrics do not drive hard success/failure. |
| required evidence | Recommendation read/write tests, Metric Truth checks, UI evidence, DB SHA/mutation explanation, audit report. |
| exit criteria | The core coach loop is understandable, measurable and honest for personal use. |
| next WP | `WP-017 Personal Beta` |

## WP-017

| Field | Value |
|---|---|
| id | `WP-017` |
| title | Personal Beta |
| target version | `v0.9` |
| status | planned |
| objective | Stabilize personal usage across real sessions. |
| guardians | `PM_ORCHESTRATOR`, `RUNTIME_GUARDIAN`, `DB_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN`, `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN` |
| source docs | `docs/RELEASE_CHECKLIST.md`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | Friends/public claims, multi-user expansion, payments/social features, unsupported metric or AI claims. |
| acceptance criteria | Real-session personal workflows stay stable; known limitations are visible; backup/restore and runtime evidence exist; no P0 safety blockers remain for personal use. |
| required evidence | Acceptance matrix review, runtime logs, DB safety evidence, safe tests, limitation review, audit report. |
| exit criteria | Personal beta can be used repeatedly with documented risks and recovery procedure. |
| next WP | `WP-018 Trusted MVP` |

## WP-018

| Field | Value |
|---|---|
| id | `WP-018` |
| title | Trusted MVP |
| target version | `v1.0` |
| status | planned |
| objective | Make the core loop trusted enough for serious use/demo. |
| guardians | all guardians |
| source docs | `docs/PROJECT_CONTROL.md`, `docs/project_management/VERSION_ROADMAP.md`, `docs/project_management/ACCEPTANCE_MATRIX.md`, `docs/RELEASE_CHECKLIST.md`, all canonical domain docs |
| forbidden actions | Public/friends readiness claims unless release gates are met, hidden live jobs, unsupported data confidence, committing runtime secrets/data. |
| acceptance criteria | Auth/runtime/import/metrics/recommendations/AI/backup/deployment gates are accepted or explicitly deferred; core loop evidence is trusted and reproducible. |
| required evidence | Full acceptance matrix, audit report, release checklist, DB/runtime/test evidence, limitation review. |
| exit criteria | Trusted personal MVP is ready for serious personal use and controlled demo. |
| next WP | post-`v1.0` planning |
