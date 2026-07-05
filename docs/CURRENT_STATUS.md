# Current Status

Last updated: 2026-07-05.

Current Product Version: `v0.8`.

Current WP: `WP-017G Data Integrity Acceptance`.

Next Target Version: `v0.9`.

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
- WP-015A1 match date truth reconciliation repair completed with production DB backup/SHA evidence and no schema/file/live-job changes. At that point playable exact rows were `21-36, 70` (17 rows), playable approximate rows were `37-38` (2 rows), playable unknown rows were `0`, and 29 `steam_history` placeholders remained unknown for future explicit Steam metadata recovery.
- WP-015B metrics correctness diagnosis completed: then-current playable rows were structurally usable, parser artifacts existed for all 19 playable demo rows, DB reset was not needed, and the main risk was confidence/date-window gating rather than data cleanup.
- WP-015C metrics confidence/date-window gating repair completed without schema changes, production DB mutation, live import or parser jobs. Date-window dashboard/stats/coach/report/recommendation/AI paths now use exact-date playable rows for recent/trend/form windows, expose exact/approximate/excluded counts, and carry confidence metadata for weak/unavailable metrics.
- WP-015C1 metrics confidence performance repair completed: the raw JSON/date-window confidence path now uses request/helper-level metric context caching, removing the blocker-level repeated `json.loads` regression diagnosed by WP-015C-PERF.
- WP-015D runtime metrics acceptance completed / `PASS_WITH_WARNINGS`, promoting Metrics Correctness to `v0.7`: confidence/date-window gating is accepted for personal MVP runtime, unsupported metrics are suppressed/relabelled, approximate rows are excluded from exact windows, AI payload includes confidence metadata, service restart was clean, DB SHA stayed unchanged, and no production DB/files/schema/live jobs were touched.
- WP-016A recommendation loop diagnosis completed: production active recommendations are legacy; active recommendation `#1` used `steam_history` placeholder baseline rows, lacked confidence metadata, and existing evaluations lacked `metric_confidence`.
- WP-016B recommendation legacy refresh repair foundation completed without production DB mutation or schema change: legacy/incompatible recommendations are detected, read surfaces label them as `needs_refresh`, automatic evaluation skips legacy active recommendations, and the explicit category restart path creates confidence-aware active recommendations from playable exact-date baseline rows.
- WP-016C controlled recommendation refresh completed with production DB backup/SHA evidence: survival recommendation `#1` was archived and preserved, new active survival recommendation `#5` was created from playable exact-date demo baseline rows `23-36,70`, baseline confidence and metric confidence metadata are present, target metrics are real values, no evaluations/reports/import/parser jobs were created, and service restart/log safety passed.
- WP-016D runtime acceptance completed / `PASS_WITH_WARNINGS`: active survival recommendation `#5` is armed and accepted for hard progress, GET/read helpers are non-mutating, but no post-refresh exact playable match exists yet.
- WP-016E controlled next-match evaluation attempt failed safely before download/import/parser work: service-level shell invocation created `steam_import_all` job `#22`, but storage preflight resolved temp dir to `/tmp` instead of systemd `data/tmp` and failed with `storage_preflight_failed`. No match/evaluation/report/demo file was created.
- WP-016E2 controlled next-match evaluation retry completed as `BLOCKED_NO_NEW_MATCH`: the official guarded Steam import service path was run exactly once with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp`; parent job `#23` and child sync job `#24` succeeded with `overall_outcome=no_new`, no demo was downloaded, no parser/evaluation ran, recommendation `#5` still has zero evaluations, and v0.8 remains blocked until a real post-refresh playable exact-date match exists.
- WP-016E3 controlled next-match evaluation after a real Competitive match completed as `FAILED`: one guarded Steam import with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` created parent job `#25` and child sync job `#26`, imported/stored/parsed exactly one new Dust2 demo as playable exact-date match `#72`, but recommendation `#5` still received no evaluation and progress stayed at zero. The full loop is blocked at the post-import recommendation evaluation trigger.
- WP-016E4 post-import recommendation evaluation repair completed / `REPAIRED_AND_EVALUATED`: parser completion now targets the newly imported playable match for recommendation evaluation, tests cover target-specific evaluation/legacy skip/duplicate protection, and controlled production evaluation created evaluation `#76` for recommendation `#5` and Dust2 match `#72` with `metric_confidence`; progress now shows one completed match.
- WP-016F documentation/status promotion completed / `PROMOTED`, promoting Recommendation Loop Acceptance to `v0.8`: the controlled personal MVP runtime loop `recommendation #5 -> match #72 -> evaluation #76 with metric_confidence -> progress completed_matches=1` is accepted. This does not validate recommendation planner quality, refresh all categories, or make the product friends/public-ready.
- WP-017A real data onboarding diagnosis completed / `DIAGNOSED`: current state is 72 matches, 20 playable parsed demos, 18 exact playable dates, 52 steam_history placeholders, about 3.8G uploads, root free about 17.07 GiB, active accepted recommendation `#5` with one green evaluation, and match mode classification remains stored as unknown for all playable demos.
- WP-017B controlled bulk import plan completed / `PLANNED`: first v0.9 import batch runbook keeps `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`, allows at most three one-demo attempts, requires backup/SHA/storage/service/job/recommendation checks before and after every run, preserves explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` for shell fallback, and defers cap increases until WP-017D acceptance.
- WP-017C first controlled bulk import batch completed / `PASS_WITH_WARNINGS`: one authorized shell-fallback `steam_import_all` run with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` created parent job `#27` and child sync job `#28`, completed as `PASS_NO_NEW_MATCH`, downloaded no demo, ran no parser, created no new match/evaluation, kept uploads unchanged at 29 demo files, left `data/tmp` empty, and kept recommendation `#5` at one evaluation / one completed match. Report: `docs/audit/WP_017C_FIRST_CONTROLLED_BULK_IMPORT_BATCH_REPORT.md`.
- WP-017C2 controlled import after new match completed / `PASS_ONE_DEMO_IMPORTED_AND_EVALUATED`: one authorized shell-fallback attempt with explicit `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` created parent job `#29` and child sync job `#30`; Steam exposed two new share codes, the one-demo cap imported/retained/parsed exactly one Overpass demo as playable exact-date match `#75`, left one pending `steam_history` placeholder `#73`, and recommendation `#5` received evaluation `#77` with `metric_confidence`, moving progress to `2/10`. Parent job `#29` is persisted as `failed` because `overall_outcome=batch_cap_reached`; this is a batch-cap warning, not a parser or recommendation failure. Report: `docs/audit/WP_017C2_CONTROLLED_IMPORT_AFTER_NEW_MATCH_REPORT.md`.
- WP-017D post-batch diagnosis completed / `ACCEPT_WITH_REPAIR_REQUIRED`: WP-017C/C2 import/parser/storage evidence was accepted, but automatic post-import recommendation evaluation was not reliable in the Steam path because evaluation ran before exact Steam date truth was applied. Pending placeholder `#73` and cap raise were blocked until repair.
- WP-017E auto-evaluation trigger repair completed / `REPAIRED`: Steam downloader imports now defer parser-side evaluation, apply/commit/refresh authoritative Steam date truth, then run targeted recommendation evaluation with compact metadata in demo download results. Tests cover exact-date auto-evaluation, batch-cap metadata, duplicate protection, legacy skip and non-exact gating. Pending `#73` is still unprocessed and cap remains `1` until the repaired path is proven live.
- WP-017F controlled pending share code `#73` import completed / `PASS_PENDING_73_IMPORTED_AND_AUTO_EVALUATED`: one targeted pending-demo attempt processed `CSGO-owEoV-4o9Uj-kK5Fp-4zYKz-UqDZG`, downloaded/retained/parsed one Mirage demo as playable exact-date match `#76`, and automatic evaluation `#78` for recommendation `#5` was created with `metric_confidence`, moving progress to `3/10`. No manual evaluator ran, legacy `#3/#4` stayed unchanged, cap stayed `1`, schema stayed unchanged and `data/tmp` returned to `0` bytes. The narrow pending-demo path did not create a new parent `steam_import_all` job, so metadata is in the returned result and placeholder raw JSON rather than a new parent result JSON.
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
- `v0.8` accepts only the controlled primary survival recommendation loop. Legacy active `grenades` recommendation `#3` and `map` recommendation `#4` remain `needs_refresh` and are not accepted for hard progress.
- `v0.9` is still not promoted. WP-017F proved the repaired automatic evaluation path on one live pending demo, but WP-017G still needs to review data integrity/runtime evidence before any cap raise or promotion.
- Recommendation progress summary wording remains rough after one green evaluation: it may say the goal is failing because the 10-match target progress score is still low after `1/10` completed matches. This is a UX/calibration warning, not a loop blocker.
- Authenticated browser UI was not directly inspected by Codex for WP-016 because no authenticated session was available; unauthenticated smoke returned expected login redirects.
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
