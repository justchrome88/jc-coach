# Current Status

Last updated: 2026-07-04.

Current Product Version: `v0.5`.

Current WP: `WP-014D2 Parent Checkpoints and Interruption Repair`.

Next Target Version: `v0.6`.

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
- Observe-only demo storage reporting and manifest generation.

## Partial Or Risky

- Parser-derived metric confidence is documented and partially hardened, but trade/KAST side/utility facts still need deeper validation before upgrading weak metrics.
- Steam import works as an alpha path with deterministic cursor semantics, repaired job truth/status taxonomy, repaired exact match-date truth, explicit retain-raw policy and WP-014D1 storage/batch guards. WP-014C live one-button acceptance still blocks promotion because parent job `#15` remains stale `running` with null `result_json`, parent progress is not checkpointed and graceful interruption handling is not repaired.
- Stage 2 ownership is single-owner mode, not full multi-user SaaS ownership across all core tables.
- Legacy `link_steam_account(..., user_id=None)` remains an internal Steam hardening risk, but it is not reachable from public OpenID callback without owner session.
- Stage 3 migration discipline is scaffold-level, not a full Alembic baseline or production migration ledger.
- Stage 4 split removes read side effects, but it is not a primary recommendation planner.
- Stage 5 is not parser hardening, diagnosis registry or recommendation planner.
- Stage 7 is not a production scheduler, durable Steam sync ledger, recommendation planner or UI redesign.
- Stage 8 is not provider-specific structured response mode, prompt versioning, recommendation planner, ProblemSnapshot or UI redesign.
- Stage 9 is UI presentation over existing persisted state/services, not recommendation planner, ProblemSnapshot or engine work.
- Next hardening stage is `WP-014D2 Parent Checkpoints and Interruption Repair` before a repeat `v0.6` live acceptance attempt.
- Recommendations are not yet consistently generated from the top verified problem snapshot.
- AI output validation exists, but prompt versioning and provider-specific structured response enforcement remain future work.
- Auth/security is still personal/VPS only; observability and public/friends release gates are not complete.

## Not Ready

- Secure friends alpha.
- Public beta.
- FACEIT import.
- Raw `.dem` deletion.
- One-button Steam import promotion to `v0.6` until incremental job progress and clean interruption handling are repaired and a repeat live acceptance is explicitly authorized.
- Payments, viewer, heatmaps, clips, practice servers or social features.
