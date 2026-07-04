# Current Status

Last updated: 2026-07-04.

Current Product Version: `v0.7`.

Current WP: `WP-016 Recommendation Loop Acceptance` in progress after WP-016B repair foundation.

Next Target Version: `v0.8`.

The project is past the original `v0.1` CSV MVP. It is usable as a personal FastAPI CS2 coach on a controlled VPS, but it is not a secure friends/public product and not a fully validated AI coach.

## Working

- FastAPI/Jinja UI with SQLite and SQLAlchemy.
- CSV/JSON import with incomplete-column tolerance and duplicate protection.
- Manual official `.dem` upload through `demoparser2`.
- Deep parser foundation with normalized parser tables, compact payload and `swing_score`.
- Dashboard, stats, match list/detail, reports and settings pages.
- Rule-based weakness detection and coach report generation.
- Recommendation tracking with active goals, lifecycle actions and match evaluation.
- AI coach handoff through `codex_cli_handoff`.
- AI report persistence with payload snapshot, provider metadata and payload hash.
- Steam OpenID onboarding, Game Authentication Code flow, share-code cursor and service bot demo URL resolver.
- Stage 1 Security P0 hardening: API auth, CSRF/state-change checks, MVP rate limits, strong session secret fail-fast and Steam OpenID verification.
- Stage 2 Ownership hardening: enforced single-owner mode completed / `PASS_WITH_WARNINGS`.
- Stage 3 Migration discipline scaffold completed / `PASS_WITH_WARNINGS`: migration policy, schema inventory and safe copy-check tooling.
- Stage 4 Recommendation read/write split completed / `PASS_WITH_WARNINGS`: GET/read paths no longer create recommendations/evaluations.
- Stage 5 Metric Truth Layer completed / `PASS_WITH_WARNINGS`: metric registry, reliability/usage policy, tests and AI/recommendation metadata exist without schema changes.
- Stage 6 Parser facts & confidence hardening completed / `PASS_WITH_WARNINGS`: parser no longer silently maps `early_deaths` to `entry_deaths`, and parser confidence warnings are clearer.
- Stage 7 Steam cursor truth completed / `PASS_WITH_WARNINGS`: cursor source, `knowncode=0` initial sentinel, advance/no-advance rules and no-new/duplicate/error outcomes are explicit and covered by mocked tests.
- Stage 8 AI Output Validator completed / `PASS_WITH_WARNINGS`: structured AI output schema, Metric Truth validation, safe fallback and mocked tests exist without schema changes or live AI calls.
- Stage 9 Coach-first UI completed / `PASS_WITH_WARNINGS`: `/coach` now presents current tracked recommendation, next-match action, evidence/confidence, Metric Truth warnings, latest match summary and AI validation status without schema changes or live jobs.
- WP-011B Project OS completed: governance/tooling docs, guardian roles, handoff entrypoint and read-only `scripts/project_gate.py` exist.
- WP-012 DB Contamination Guardrails completed: test/smoke email registration guardrails, pytest DB isolation checks and runtime smoke runbook updates exist.
- WP-013 Personal MVP Runtime Smoke Gate completed / `PASS_WITH_WARNINGS`: service restart and read-only runtime smoke passed without 500s, unexpected DB mutation or hidden live jobs. Full owner browser checklist remains operator evidence to record after restart.
- WP-014B1 Steam import job truth/status taxonomy completed: `steam_import_all` now records standardized `result_json` outcomes/statuses, exact share-code import creates tracking jobs before downloader/parser work, and aggregate jobs no longer report clean success for missing-code/download/parser/partial cases.
- WP-014B2 Steam exact match-date truth completed: primary Steam import treats Steam GC `match_time` as exact, marks unavailable/approximate date states explicitly, clears `Match.played_at` for Steam imports without GC match time, and uses exact-only dates for Steam freshness.
- WP-014B3 demo retention policy completed: raw demos are retained by default under `retain_raw_for_parser_development`, retention metadata is recorded for successful/failed demo imports, and storage reporting includes read-only file/DB consistency classification.
- WP-014D1 Steam import storage guard/batch cap repair completed: one-button demo downloads now have configurable disk preflight, per-run demo cap, per-job byte budget, per-demo byte guard, preserve-free checks and streamed download byte counting.
- WP-014D2 Steam import parent checkpoint/interruption repair completed: parent `steam_import_all` jobs now persist bounded progress checkpoints, stale running parent jobs are marked failed/interrupted at queue time before a new parent is created, non-stale running jobs remain blocking, soft background interruption marking is best-effort, startup stale repair is opt-in, and explicit operator repair for production job `#15` is available through `scripts/repair_stale_steam_import_job.py`.
- WP-014D3 Steam import operator stale job repair completed: production `import_jobs.id=15` was backed up and marked `failed/interrupted`; only job `#15` changed logically, no live Steam/import/parser work ran, and `data/uploads` stayed unchanged.
- WP-014C3 repeat one-button live acceptance after TMPDIR fix verified the runtime storage guard path: service temp resolved to `data/tmp`, storage preflight passed, batch cap limited work to one demo, parent job reached a terminal failed result with checkpoints, and disk growth was bounded. The run exposed a parser/import model compatibility crash after raw demo retention: `played_at_source` was passed to `Match(...)`.
- WP-014E parser/import model compatibility repair completed without schema change: parser/Steam date-source metadata is preserved in `matches.raw_json` and result payloads, but non-column metadata such as `played_at_source` is filtered before `Match` ORM construction.
- WP-014C4 repeat one-button live acceptance completed / `PASS_WITH_WARNINGS`: one authorized click created parent job `#20`, storage/TMPDIR preflight passed, batch cap limited the run to one demo, parser/import succeeded, exact date truth was persisted from `steam_gc_match_time`, parent `result_json` was terminal/truthful, service stayed healthy and disk growth was bounded.
- WP-015A1 match date truth reconciliation repair completed with production DB backup/SHA evidence and no schema/file/live-job changes. Playable exact rows are now `21-36, 70` (17 rows), playable approximate rows are `37-38` (2 rows), playable unknown rows are `0`, and 29 `steam_history` placeholders remain unknown for future explicit Steam metadata recovery.
- WP-015B metrics correctness diagnosis completed: playable rows are structurally usable, parser artifacts exist for all 19 playable demo rows, DB reset is not needed, and the main risk is confidence/date-window gating rather than data cleanup.
- WP-015C metrics confidence/date-window gating repair completed without schema changes, production DB mutation, live import or parser jobs. Date-window dashboard/stats/coach/report/recommendation/AI paths now use exact-date playable rows for recent/trend/form windows, expose exact/approximate/excluded counts, and carry confidence metadata for weak/unavailable metrics.
- WP-015C1 metrics confidence performance repair completed: the raw JSON/date-window confidence path now uses request/helper-level metric context caching, removing the blocker-level repeated `json.loads` regression diagnosed by WP-015C-PERF.
- WP-015D runtime metrics acceptance completed / `PASS_WITH_WARNINGS`, promoting Metrics Correctness to `v0.7`: confidence/date-window gating is accepted for personal MVP runtime, unsupported metrics are suppressed/relabelled, approximate rows are excluded from exact windows, AI payload includes confidence metadata, service restart was clean, DB SHA stayed unchanged, and no production DB/files/schema/live jobs were touched.
- WP-016A recommendation loop diagnosis completed: production active recommendations are legacy; active recommendation `#1` used `steam_history` placeholder baseline rows, lacked confidence metadata, and existing evaluations lacked `metric_confidence`.
- WP-016B recommendation legacy refresh repair foundation completed without production DB mutation or schema change: legacy/incompatible recommendations are detected, read surfaces label them as `needs_refresh`, automatic evaluation skips legacy active recommendations, and the explicit category restart path creates confidence-aware active recommendations from playable exact-date baseline rows.
- Observe-only demo storage reporting and manifest generation.

## Partial Or Risky

- Parser-derived metric confidence is documented, date-window gating is accepted for `v0.7`, and WP-015C1 fixed the major runtime confidence-cache performance regression. Trade/KAST side/utility facts still need deeper fixture validation before upgrading weak metrics.
- Steam import is accepted for controlled personal `v0.6` with warnings. It has deterministic cursor semantics, repaired job truth/status taxonomy, exact match-date truth, explicit retain-raw policy, WP-014D1 storage/batch guards, WP-014D2 parent checkpoint/stale handling, WP-014D3 stale job repair, WP-014E parser/model compatibility repair and WP-014C4 live acceptance evidence.
- Match date truth is reconciled enough for accepted `v0.7` metric windows: metrics treat only exact playable rows as eligible for exact date windows, keep rows `37-38` approximate/excluded from exact windows, and exclude `source="steam_history"` placeholders from playable metrics.
- Stage 2 ownership is single-owner mode, not full multi-user SaaS ownership across all core tables.
- Legacy `link_steam_account(..., user_id=None)` remains an internal Steam hardening risk, but it is not reachable from public OpenID callback without owner session.
- Stage 3 migration discipline is scaffold-level, not a full Alembic baseline or production migration ledger.
- Stage 4 split removes read side effects, but it is not a primary recommendation planner.
- Stage 5 is not parser hardening, diagnosis registry or recommendation planner.
- Stage 7 is not a production scheduler, durable Steam sync ledger, recommendation planner or UI redesign.
- Stage 8 is not provider-specific structured response mode, prompt versioning, recommendation planner, ProblemSnapshot or UI redesign.
- Stage 9 is UI presentation over existing persisted state/services, not recommendation planner, ProblemSnapshot or engine work.
- WP-015D warnings carried forward: direct post-restart authenticated browser timings were not captured by Codex; persistent report generation acceptance is deferred because it mutates DB; `/coach` artifact overview still loads many artifact ORM rows; weak metrics remain weak; `ImportJob.status` remains coarse; uploads/tmp remain on root filesystem.
- WP-016B implemented the refresh/restart foundation, but production legacy recommendations have not yet been refreshed. WP-016C should run the controlled explicit refresh path with backup/SHA evidence.
- Recommendations are not yet consistently generated from the top verified problem snapshot.
- AI output validation exists, but prompt versioning and provider-specific structured response enforcement remain future work.
- Auth/security is still personal/VPS only; observability and public/friends release gates are not complete.

## Not Ready

- Secure friends alpha.
- Public beta.
- FACEIT import.
- Raw `.dem` deletion.
- Friends/public import readiness; `v0.6` is controlled personal acceptance only.
- Payments, viewer, heatmaps, clips, practice servers or social features.
