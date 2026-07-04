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
| status | completed / accepted with warnings |
| objective | Accept the one-button Steam/Valve import as the primary workflow: connected Steam account, match/auth code, truthful import_job, duplicate/no-new/error states, exact match-date truth and raw demo cleanup after successful parse/persist. |
| guardians | `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `TEST_GUARDIAN`, `RUNTIME_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/STEAM_IMPORT.md`, `docs/DEMO_DEEP_PARSER_TZ_RU.md`, `docs/DEMO_STORAGE_TZ.md`, `docs/TESTING.md`, `docs/BACKUP_RESTORE.md` |
| forbidden actions | Live Steam calls, real demo downloads/parses or production import jobs unless the WP explicitly authorizes them with backup and DB evidence. |
| acceptance criteria | One-button import records clear success/no-new/need-code/Steam-not-connected/rate-limited/download-failed/parser-failed/partial-success/duplicate-skipped/interrupted outcomes; duplicate protection is verified; exact match date is stored from Steam GC metadata or explicitly unavailable; current raw demo policy is explicit retain-by-default with file/DB consistency metadata; future delete-after-success remains disabled until parser acceptance. Live acceptance additionally requires disk budget/batch caps, incremental parent job truth and clean interruption handling. WP-014B1 covers job truth/status taxonomy; WP-014B2 covers exact match-date truth; WP-014B3 covers retention policy/metadata; WP-014D1 covers storage budget/batch caps; WP-014D2 covers parent checkpoints and stale/interrupted handling; WP-014D3 repaired failed job `#15`; WP-014E repaired parser/import `Match` model compatibility for date-source metadata; WP-014C4 passed repeat one-button live acceptance with warnings. |
| required evidence | WP-014A diagnosis, mocked tests by default, live-job authorization if any, DB SHA before/after, import job result examples, cursor mutation status, demo cleanup evidence, audit report. |
| exit criteria | The primary one-button Steam/Valve import is safe enough for controlled personal operation, including bounded disk usage and truthful interrupted-job handling, with manual demo upload documented as a secondary parser/debug path and remaining alpha limitations explicit. |
| next WP | `WP-015 Metrics Correctness` |

## WP-015

| Field | Value |
|---|---|
| id | `WP-015` |
| title | Metrics Correctness |
| target version | `v0.7` |
| status | completed / accepted with warnings |
| objective | Establish golden fixtures, trusted metrics and weak metric labeling. |
| guardians | `METRICS_GUARDIAN`, `TEST_GUARDIAN`, `IMPORT_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/METRICS.md`, `docs/audit/METRIC_TRUTH_INVENTORY.md`, `docs/audit/PARSER_FACTS_INVENTORY.md`, `docs/audit/WP_015A_MATCH_DATE_TRUTH_RECONCILIATION_DIAGNOSIS.md`, `docs/audit/WP_015A1_MATCH_DATE_TRUTH_RECONCILIATION_REPAIR_REPORT.md`, `docs/RECOMMENDATIONS.md`, `docs/AI_COACH.md` |
| forbidden actions | Upgrading weak metrics without fixture evidence, using unavailable metrics for hard claims, live AI/import/parser jobs without explicit authorization. |
| acceptance criteria | Golden fixtures exist for accepted metrics; trusted/medium/approximate/low/unavailable labels are enforced; weak metrics are visibly labeled or suppressed; date-window metrics treat only exact Steam GC dates as exact and label/exclude approximate dates; AI/recommendation paths follow Metric Truth. WP-015C implemented confidence/date-window guardrails, WP-015C1 repaired repeated raw JSON parsing performance regression, and WP-015D accepted runtime metric surfaces with warnings. |
| required evidence | Metric fixture results, Metric Truth tests, AI validator/recommendation evidence tests as applicable, no unsupported metric claims. |
| exit criteria | Accepted metrics are reliable enough to support serious recommendation evidence within documented limits. |
| next WP | `WP-016 Recommendation Loop Acceptance` |

## WP-016

| Field | Value |
|---|---|
| id | `WP-016` |
| title | Recommendation Loop Acceptance |
| target version | `v0.8` |
| status | completed / promoted |
| objective | Accept recommendation -> next match -> evaluation -> progress as a coherent loop. |
| guardians | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN`, `DB_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/RECOMMENDATIONS.md`, `docs/METRICS.md`, `docs/AI_COACH.md`, `docs/PROJECT_CONTROL.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | Planner claims without verified evidence, hidden writes on GET/read paths, AI overclaims, schema changes without explicit migration scope. |
| acceptance criteria | One primary recommendation is evidence-backed; legacy active recommendations are not accepted as hard progress; next-match action is visible; evaluation updates progress through explicit write paths; weak metrics do not drive hard success/failure; proven loop exists for `recommendation #5 -> match #72 -> evaluation #76 -> completed_matches=1`. |
| required evidence | WP-016A diagnosis, WP-016B legacy refresh repair tests, WP-016C controlled survival refresh evidence, WP-016D armed runtime acceptance, WP-016E/E2/E3 controlled attempts, WP-016E4 post-import evaluation repair/evidence, WP-016F promotion report, recommendation read/write tests, Metric Truth checks, DB SHA/mutation explanation. |
| exit criteria | The controlled personal core coach loop is understandable, measurable and honest within documented limits. |
| next WP | `WP-017A Roadmap v0.9-v1.0 Planning / Real Data Onboarding Diagnosis` |

## WP-017A

| Field | Value |
|---|---|
| id | `WP-017A` |
| title | Roadmap v0.9-v1.0 Planning / Real Data Onboarding Diagnosis |
| target version | `v0.9` |
| status | planned |
| objective | Plan the accepted `v0.9`-`v1.0` sequence and diagnose safe Real Data Onboarding / Bulk Demo Usage without running bulk jobs. |
| guardians | `PM_ORCHESTRATOR`, `IMPORT_GUARDIAN`, `DB_GUARDIAN`, `RUNTIME_GUARDIAN`, `TEST_GUARDIAN`, `METRICS_GUARDIAN` |
| source docs | `docs/STEAM_IMPORT.md`, `docs/DEMO_STORAGE_TZ.md`, `docs/BACKUP_RESTORE.md`, `docs/DEPLOYMENT.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/project_management/VERSION_ROADMAP.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | Live Steam/Valve import, demo downloads, parser jobs, production DB mutation, production demo file deletion/move, schema changes, DB reset/resync, friends/public claims. |
| acceptance criteria | The `v0.9`-`v1.0` roadmap is explicit; bulk/demo onboarding risks are diagnosed; storage/DB/import safeguards are identified; accepted and deferred evidence are separated; follow-up WPs do not claim recommendation planner quality without proof. |
| required evidence | Current DB SHA, read-only project gates, storage/import constraints review if needed, updated roadmap/backlog/matrix, audit report. |
| exit criteria | Real data onboarding and bulk demo usage have a safe next-step plan that can be executed by a future authorized WP. |
| next WP | `WP-018 Coach Quality Calibration` |

## WP-018

| Field | Value |
|---|---|
| id | `WP-018` |
| title | Coach Quality Calibration |
| target version | `v0.10` |
| status | planned |
| objective | Calibrate coach/recommendation quality, progress scoring and wording against accepted evidence. |
| guardians | `METRICS_GUARDIAN`, `UI_COACH_GUARDIAN`, `TEST_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/RECOMMENDATIONS.md`, `docs/METRICS.md`, `docs/AI_COACH.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | Unsupported metric upgrades, planner quality claims without evidence, live AI/import/parser jobs unless explicitly authorized. |
| acceptance criteria | Coach claims are calibrated to evidence confidence; rough one-match progress wording is repaired or explicitly bounded; planner and recommendation quality gaps are diagnosed; weak metrics remain caveated. |
| required evidence | Targeted tests if code changes, Metric Truth checks, UI/wording evidence, audit report. |
| exit criteria | Coach output is useful and honest enough for repeated personal use with known caveats. |
| next WP | `WP-019 Personal Daily Use UX` |

## WP-019

| Field | Value |
|---|---|
| id | `WP-019` |
| title | Personal Daily Use UX |
| target version | `v0.11` |
| status | planned |
| objective | Make the daily personal workflow clear, repeatable and low-friction. |
| guardians | `UI_COACH_GUARDIAN`, `RUNTIME_GUARDIAN`, `TEST_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/RECOMMENDATIONS.md`, `docs/DEPLOYMENT.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/project_management/ACCEPTANCE_MATRIX.md` |
| forbidden actions | Friends/public readiness claims, broad redesign detached from the coach loop, hidden live jobs. |
| acceptance criteria | Daily entrypoints show next action, latest match state, limitations and recovery hints clearly; read paths remain non-mutating; core pages are usable for repeated owner sessions. |
| required evidence | Runtime smoke, UI evidence, DB SHA impact explanation, targeted tests if code changes, audit report. |
| exit criteria | The owner can use the app day to day without relying on internal implementation knowledge. |
| next WP | `WP-020 Deployment / Backup / Storage Hardening` |

## WP-020

| Field | Value |
|---|---|
| id | `WP-020` |
| title | Deployment / Backup / Storage Hardening |
| target version | `v0.12` |
| status | planned |
| objective | Harden VPS operation, backup/restore, storage layout and recovery before the MVP lock. |
| guardians | `RUNTIME_GUARDIAN`, `DB_GUARDIAN`, `IMPORT_GUARDIAN`, `TEST_GUARDIAN`, `PM_ORCHESTRATOR` |
| source docs | `docs/DEPLOYMENT.md`, `docs/BACKUP_RESTORE.md`, `docs/DEMO_STORAGE_TZ.md`, `docs/SECURITY.md`, `docs/RELEASE_CHECKLIST.md` |
| forbidden actions | Unbounded import/parser jobs, production DB changes without backup/SHA evidence, demo deletion/move without explicit retention WP, schema changes without migration scope. |
| acceptance criteria | Backup/restore evidence is current; storage risk is bounded; service recovery is documented and tested; deployment gaps are named before `v1.0`. |
| required evidence | Backup/restore checks, service status/logs, storage evidence, safe tests if code changes, audit report. |
| exit criteria | Controlled personal deployment has enough recovery and storage discipline for MVP lock. |
| next WP | `WP-021 Personal MVP Lock` |

## WP-021

| Field | Value |
|---|---|
| id | `WP-021` |
| title | Personal MVP Lock |
| target version | `v1.0` |
| status | planned |
| objective | Lock the controlled personal MVP scope and acceptance evidence. |
| guardians | all guardians |
| source docs | `docs/PROJECT_CONTROL.md`, `docs/project_management/VERSION_ROADMAP.md`, `docs/project_management/ACCEPTANCE_MATRIX.md`, `docs/RELEASE_CHECKLIST.md`, all canonical domain docs |
| forbidden actions | Public/friends readiness claims unless release gates are met, hidden live jobs, unsupported data confidence, committing runtime secrets/data. |
| acceptance criteria | Auth/runtime/import/metrics/recommendations/AI/backup/deployment gates are accepted or explicitly deferred; core loop evidence is trusted and reproducible for personal use. |
| required evidence | Full acceptance matrix, audit report, release checklist, DB/runtime/test evidence, limitation review. |
| exit criteria | Personal MVP is locked for serious personal use within explicit non-public limits. |
| next WP | post-`v1.0` planning |
