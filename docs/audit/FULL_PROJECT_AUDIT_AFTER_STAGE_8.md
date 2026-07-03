# Full Project Audit After Stage 8

Дата аудита: 2026-07-03.

Scope: read-only full project audit после Stage 0-8. Код, тесты, существующие документы, `.env` и production DB не изменялись. Создан только этот audit report.

## AUDIT_RESULT

PASS_WITH_WARNINGS

Проект прошёл безопасную проверку после Stage 0-8 и может переходить к Stage 9 Coach-first UI при жёстком ограничении scope: без schema changes, без Steam/parser/import jobs, без live AI calls, без recommendation planner и без переписывания UI шире существующего coach loop.

Статус не `PASS`, потому что остаются честно задокументированные ограничения: нет полноценного recommendation planner / ProblemSnapshot, parser facts всё ещё частично low/approximate, Steam import не имеет durable scheduler/ledger, миграции пока без Alembic baseline, а часть docs содержит устаревшие warnings.

## Executive Summary

Stage 0-8 создали рабочий safety/security/truth foundation:

- tests изолированы от production DB и проходят через `APP_ENV=test`;
- backup/restore и migration copy-check процесс описаны;
- non-health `/api/*` закрыты session auth или Bearer `API_TOKEN`;
- browser/API state changes защищены CSRF или token policy;
- single-owner boundary enforced;
- recommendation read/write split сохранён;
- Metric Truth Layer запрещает слабым метрикам становиться hard claims;
- parser facts стали честнее по `early_deaths`, trade/KAST, side split, utility/flash;
- Steam cursor source/advance/outcome semantics deterministic в mocked paths;
- AI Output Validator rejects unsupported structured claims and falls back safely.

Основная оставшаяся продуктовая дыра: система ещё не выбирает один verified primary problem и не строит из него planner-driven recommendation. Stage 9 должен делать не planner, а usable coach-first presentation поверх уже существующих данных: current recommendation, evidence, confidence, next-match tracking и Metric Truth warnings.

## Current Product Reality

What works:

- FastAPI/Jinja app, SQLite, dashboard, matches, stats, reports, upload pages.
- CSV/JSON import, manual `.dem` import, Steam alpha onboarding/sync paths.
- Rule-based report, recommendation lifecycle, evaluations and progress.
- AI handoff/local provider scaffold, report persistence and Stage 8 validation.
- Auth/session, CSRF, API token and single-owner controls for controlled personal/VPS use.
- Full safe test suite: `138 passed, 1 warning`.

What is partially reliable:

- Parser-derived metrics: `entry_deaths` medium, `early_deaths` approximate, side splits low, trade/KAST trade component limited.
- Recommendation tracking: lifecycle and evaluation work, but recommendations are category defaults, not chosen from verified problem snapshots.
- Steam import: cursor truth is deterministic, but production worker/retry/scheduler observability is not complete.
- AI coach: validator blocks unsupported metric claims, but natural-language semantic entailment, prompt versioning and provider structured mode are not complete.

What is still not trustworthy:

- `traded_deaths`, `untraded_deaths`, `aim_rating`, `grenade_rating`, `crosshair_placement` as coach facts.
- Side split diagnosis/recommendation claims.
- Claims based on old unvalidated AI reports already stored before Stage 8.
- Public/friends exposure without observability, release gate review and operational hardening.

What is only scaffolding:

- Migration discipline without Alembic baseline.
- Recommendation planner / ProblemSnapshot.
- Local LLM production workflow.
- Steam durable scheduler/retry ledger.
- Raw `.dem` verified-delete lifecycle.
- FACEIT, viewer, heatmaps, clips, payments and social/public features.

## Stage 0-8 Verification Matrix

| Stage | Claimed outcome | Evidence | Remaining risks | Blocker yes/no |
|---|---|---|---|---|
| Stage 0 Safety Foundation | Safe baseline, backup/restore, test isolation | `docs/TESTING.md`, `docs/BACKUP_RESTORE.md`, safe pytest passes, production DB SHA unchanged | Disaster recovery is minimal, not full production DR | no |
| Stage 1 Security P0 | API auth, CSRF, rate limits, strong secret fail-fast, Steam OpenID verification | `app/main.py`, `app/services/security.py`, `docs/audit/STAGE_1_SECURITY_P0_REVIEW.md`, security tests | In-memory rate limits, limited observability | no for Stage 9 |
| Stage 2 Ownership | Enforced single-owner mode | `app/services/auth.py`, owner tests, `docs/audit/STAGE_2_OWNERSHIP_REVIEW.md` | Not full multi-user; legacy `link_steam_account(..., user_id=None)` remains internal risk | no for Stage 9 |
| Stage 3 Migration Discipline | Copy-first migration policy and tooling | `docs/MIGRATIONS.md`, `scripts/migration_*`, migration tests, review report | No Alembic baseline; startup legacy `_upgrade_sqlite_schema()` remains | no if Stage 9 has no schema changes |
| Stage 4 Recommendation R/W Split | GET/read paths do not mutate recommendations/evaluations | `app/services/recommendation_tracking.py`, `tests/test_recommendation_read_write_split.py`, review report | Still no planner; defaults remain category-based | no |
| Stage 5 Metric Truth Layer | Runtime registry with reliability/usage policy | `app/services/metric_truth.py`, `tests/test_metric_truth.py`, `docs/METRICS.md` | Existing diagnosis remains threshold/rule-based, not registry-driven | no |
| Stage 6 Parser Facts Hardening | Parser confidence honesty without production parsing | `app/services/demo_parser.py` confidence metadata, parser tests, review report | Trade graph, side/team inference, utility/flash attribution still limited | no |
| Stage 7 Steam Cursor Truth | Deterministic cursor source/advance/outcome semantics | `app/services/steam_integration.py`, `tests/test_steam_cursor_truth.py`, review report | Early guard failures lack full `sync_outcome`; no durable scheduler/ledger | no |
| Stage 8 AI Validator | Structured AI output validator and safe fallback | `app/services/ai_validator.py`, `app/services/ai_coach.py`, AI validator tests, review report | No semantic entailment, prompt versioning or provider-specific structured mode | no |

## Architecture Scorecard

| Area | Score | Notes |
|---|---:|---|
| Safety / test isolation | 5 | Test DB and runtime dirs are isolated; production DB guard exists. |
| Security | 4 | Good personal/VPS hardening; observability and public-grade abuse controls remain. |
| Ownership | 4 | Single-owner boundary enforced; not full multi-user ownership. |
| Migrations | 3 | Policy and copy-check tooling exist; no Alembic baseline/ledger. |
| Import/data ingestion | 3 | CSV/JSON/DEM/Steam alpha work; Steam worker and replay failure handling need hardening. |
| Parser facts | 3 | Confidence metadata improved; several facts remain approximate/low/unavailable. |
| Metric Truth Layer | 4 | Runtime registry and suppression policy exist; diagnosis integration remains partial. |
| Diagnosis | 2 | Rule-based and threshold-based; no verified problem registry yet. |
| Recommendation lifecycle | 3 | Lifecycle/evaluation works; defaults are not planner-selected. |
| Recommendation planner | 1 | Explicitly future work. |
| AI coach | 3 | Handoff/persistence works; provider flow remains scaffold-level. |
| AI validator | 4 | Strong structural/Metric Truth checks; no deep semantic validator. |
| API | 4 | Protected and tested; mutation/read semantics improved. |
| UI | 3 | Usable pages exist; coach-first hierarchy is still pending. |
| Testing | 4 | Full suite passes and covers Stage 0-8 gates; some integration paths remain mocked. |
| Ops/deploy | 3 | Controlled VPS docs and systemd/nginx references exist; public ops gate incomplete. |
| Docs/process | 4 | Canonical docs mostly aligned; `docs/KNOWN_LIMITATIONS.md` has stale items. |

## P0 Blockers

No P0 blocker was found for starting Stage 9 Coach-first UI under the requested constraints.

No P0 blocker was found for safe controlled personal MVP use if the operator keeps auth enabled, uses strong secrets, keeps tests on `APP_ENV=test`, and does not expose the app as friends/public product.

P0 would appear if Stage 9 attempted any of these:

- schema changes without Stage 3 migration discipline and backup approval;
- live Steam/import/parser jobs;
- live AI provider changes;
- recommendation planner / ProblemSnapshot;
- friends/public launch.

## P1 Risks

- `docs/KNOWN_LIMITATIONS.md` is stale: it still says metrics are placeholder-level and AI output is not schema-validated. This can confuse future agents even though canonical docs are correct.
- Legacy `link_steam_account(..., user_id=None)` still exists as service-level path. It is not public-callback reachable after Stage 2, but remains a Steam hardening risk.
- Steam early guard failures in `sync_match_history_job()` still do not all write full deterministic `sync_outcome`.
- Steam import lacks durable scheduler/retry ledger and production observability.
- Migration discipline lacks Alembic baseline and migration ledger.
- Diagnosis is still rule/threshold-based and not a verified problem registry.
- Recommendation defaults exist, but no planner selects one primary recommendation from verified evidence.
- AI validator cannot prove natural-language semantic entailment and does not version prompt/payload schema.
- Old AI reports stored before Stage 8 are not backfilled/revalidated.
- Parser facts for trade, traded deaths, side split, utility/flash and crosshair/position remain limited.

## P2 Cleanup

- Update stale supporting docs after this audit, especially `docs/KNOWN_LIMITATIONS.md`.
- Remove or ignore committed `__pycache__` files in a separate cleanup if they are tracked unintentionally.
- Add concise UI copy that surfaces Metric Truth warnings without teaching implementation details.
- Expand release checklist with Stage 8 validator and Stage 9 UI readiness gates.
- Consider naming cleanup around Stage 7 outcomes: share-code collection success is not parser import success.

## Must Fix Before Stage 9

Required before Stage 9 start:

- Keep Stage 9 scope docs explicit: no schema changes, no Steam/parser/import jobs, no live AI calls, no recommendation planner.
- Record current production DB SHA before Stage 9 and verify unchanged after.
- Use only `APP_ENV=test .venv/bin/pytest tests -q`, ruff and diff checks unless the user explicitly permits runtime smoke checks.

Recommended tiny repair before or during Stage 9 planning:

- Update `docs/KNOWN_LIMITATIONS.md` so it no longer contradicts Stage 5 and Stage 8.

## Can Proceed To Stage 9

yes

Only under these start conditions:

- Stage 9 is Coach-first UI presentation over existing persisted state and services.
- Stage 9 does not add tables/columns/migrations.
- Stage 9 does not run live Steam/import/parser/AI jobs.
- Stage 9 does not implement recommendation planner, ProblemSnapshot, Metric Truth expansion, Steam cursor hardening or parser hardening.
- Stage 9 preserves GET/read no-mutation behavior.

## Recommended Stage 9 Scope

Stage 9 Coach-first UI should be deliberately narrow:

- no schema changes unless a separate migration task is approved;
- no Steam/parser/AI planner work;
- no live provider calls;
- focus on making the existing coach loop usable;
- show current primary/active recommendation from existing recommendation state;
- show evidence, baseline, target, confidence and next-match tracking;
- surface Metric Truth warnings for approximate/low/unavailable facts;
- show AI validator fallback/validation status where AI reports are displayed;
- keep manual UX safe: explicit buttons for handoff/generate/save, no hidden background jobs.

Do not use Stage 9 to invent the missing planner. If the UI needs a "primary" card, it should use existing active recommendation ordering and clearly label it as current tracked recommendation, not verified top problem.

## Suggested Repair Lane Before Stage 9

1. Tiny docs-only repair: refresh `docs/KNOWN_LIMITATIONS.md`.
2. Optional review-only check: confirm current templates do not imply unavailable metrics are reliable coach facts.
3. Optional Stage 9 preflight: inventory `/coach`, `/report`, dashboard and recommendation UI surfaces for read/mutation behavior.

## Test Results

Commands run during this audit:

```bash
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Results:

- `APP_ENV=test .venv/bin/pytest tests -q`: `138 passed, 1 warning`.
- `.venv/bin/ruff check .`: `All checks passed!`.
- `git diff --check`: passed, no output.
- Production DB SHA after safe checks: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`.

No live AI calls were made. No live Steam calls were made. No production import/parser jobs were run.

## Production DB Check

Production DB file checked:

```text
data/cs2_coach.db
```

Observed SHA:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

This matches the Stage 1-8 review baseline repeatedly recorded in prior audit reports. The audit created only this Markdown report and did not mutate production DB.

## Final Verdict

Проект готов начать Stage 9 Coach-first UI, если Stage 9 остаётся presentation/usability этапом поверх существующего safe foundation.

Самые безопасные условия старта:

- read current canonical docs before work;
- snapshot `git status --short` and production DB SHA;
- do not change schema;
- do not run live external jobs/providers;
- preserve recommendation read/write split;
- show Metric Truth and AI validation warnings visibly;
- keep all checks inside `APP_ENV=test`.

Если Stage 9 начнёт строить planner, менять schema, запускать Steam/parser/import/AI runtime или заявлять friends/public readiness, проект перестаёт быть готов к этому этапу без отдельного approved hardening task.
