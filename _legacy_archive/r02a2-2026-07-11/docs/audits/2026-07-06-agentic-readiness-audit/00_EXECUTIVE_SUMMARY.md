# Executive Summary

Audit date: 2026-07-06. Scope: read-only agentic-readiness audit for JC Coach / CS2 AI Coach. Result: **YES, BUT - use a hybrid path: continue only small/scoped feature work while fixing foundation P0/P1 items before major coach/domain expansion.**

## Overall Readiness

- Overall readiness score: **66%** (3.30/5 across 106 audit rows).
- Tests run during audit: `211 passed, 1 warning`; Ruff passed; `git diff --check` passed.
- Production DB was not mutated; DB SHA observed: `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.

## Layer Scores

| Layer | Score | Percent | Verdict |
|---|---:|---:|---|
| Agentic Development Core | 4.0/5 | 80% | Strong governance, mostly manual enforcement. |
| Web Application Core | 3.0/5 | 60% | Usable personal app, migration/job architecture still risky. |
| AI Coach Archetype | 3.1/5 | 62% | Validator and tracking exist; planner/semantic evals missing. |
| CS2 Domain Pack | 2.9/5 | 58% | Good caveats; several domain models unavailable or weak. |
| Project Instance | 3.5/5 | 70% | Current status/roadmap strong; old docs/data artifacts still noisy. |
| Runtime Layer | 4.1/5 | 82% | Current audit execution is disciplined and reproducible. |

## Top 10 Blockers

1. No real migration baseline; `create_all()` plus legacy `_upgrade_sqlite_schema()` still protects old SQLite state but is unsafe for future schema work.
2. Recommendation planner/top verified problem selection is not implemented.
3. No semantic AI eval suite; schema validation alone cannot prove advice quality.
4. No CI/pre-commit enforcement for mandatory pytest/ruff/diff/gate checks.
5. Durable Steam/import worker and retry ledger are not in place; BackgroundTasks remain fragile.
6. No structured risk register with owner/status/target WP.
7. Prompt and payload versioning for AI coach is explicitly missing.
8. Source trust and sample-size policies are incomplete across metrics and domains.
9. CS2 economy/positioning/clutch models are absent or underdefined.
10. Friends/public readiness remains blocked by security, privacy, observability and operational gates.

## Top 10 High-Risk Gaps

1. Manual governance can be skipped despite good docs.
2. API contracts are not versioned or tested as contracts.
3. Single-owner policy is documented as fragile.
4. Global DB engine/settings import order can be dangerous outside pytest discipline.
5. Route/service boundaries are documented but not deeply mapped.
6. Metric formulas exist but broader golden aggregate fixtures are incomplete.
7. Runtime data, raw demos, backups and secret-adjacent files exist locally and require discipline.
8. Observability/runbook coverage is thin.
9. Data privacy and retention are not ready for sharing/friends use.
10. Old docs remain numerous; classification exists but physical cleanup/deprecation is incomplete.

## What Is Already Good

- Root `AGENTS.md`, Hot/Warm/Cold context, source-of-truth hierarchy and WP registry are strong.
- Current status, handoff, roadmap and acceptance matrix are current and linked.
- Metric Truth Layer and AI Output Validator create real guardrails against unsupported metric claims.
- Test isolation is strong: tests force `APP_ENV=test` and a temp DB, and the full suite passed.
- Security baseline for controlled personal/VPS use is materially better than an MVP default.
- Known limitations are honest and specific, including match mode, cap, weak metrics and public-readiness blockers.

## Do Not Touch Until Fixed Or Explicitly Scoped

- Do not add schema features before a migration baseline WP.
- Do not raise Steam import cap or run live import/parser/evaluator without explicit authorization.
- Do not make playlist-specific CS2 claims from current persisted mode data.
- Do not use economy/positioning/traded-death/crosshair-placement as hard coaching evidence.
- Do not expose to friends/public before security, privacy, observability and backup/storage gates close.

## Continue Feature Development?

**YES, BUT.** Continue narrow, evidence-backed work such as WP-018 coach quality calibration, wording/caveat improvements, docs/gate hardening and tests. Do not start major schema, import-scale, public-access, or new domain-intelligence features until foundation P0/P1 tasks are done.

## Shortest Safe Path

1. Add migration baseline/schema gate.
2. Add CI or mandatory local gate wrapper for pytest/ruff/diff/project_gate.
3. Define coach advice confidence + source trust + sample-size policy.
4. Implement diagnosis registry/top problem planner before new recommendation intelligence.
5. Add prompt/payload versioning and semantic AI evals.

## Fix In 1 Day

- Add canonical risk register or extend Known Limitations with owner/status/target WP.
- Add env reference without secret values.
- Add CI/gate checklist doc and make project_gate command standard in WP reports.
- Add AI prompt/payload version fields to docs/task acceptance if code changes are not yet scoped.

## Fix In 1 Week

- Create migration baseline and schema diff policy.
- Add golden metric fixtures for core accepted metrics.
- Add source trust/sample-size policy.
- Add first semantic AI eval fixtures.
- Refine coach progress wording and caveats for active recommendation #5.

## Defer

- Friends/public readiness.
- FACEIT integration.
- Economy/positioning/heatmaps/clips.
- Durable worker implementation beyond planning unless import cap raise is explicitly pursued.
