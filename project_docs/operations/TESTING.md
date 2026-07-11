> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/TESTING.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Testing

Last updated: 2026-07-07.

## Current Truth

Test isolation is now a Stage 0 safety requirement. Tests must run with `APP_ENV=test` and a non-production SQLite database.

`tests/conftest.py` forces `APP_ENV=test` and defaults `DATABASE_URL` to a temp DB under `/tmp`. If a caller explicitly sets `DATABASE_URL` to the production path `data/cs2_coach.db`, app settings fail fast.

Standalone `TestClient` snippets are forbidden unless `APP_ENV=test`, `DATABASE_URL` and runtime artifact directories are configured to temp paths before importing `app.main` or `app.db.session`. Importing the app first can bind the global SQLAlchemy engine to the default runtime DB.

## Safe Commands

Recommended full safe test command:

```bash
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
```

Targeted safe command while working on test isolation:

```bash
APP_ENV=test .venv/bin/pytest tests/test_config.py tests/test_web_smoke.py -q
```

Static check:

```bash
.venv/bin/ruff check . --no-cache
```

Accepted local CI-equivalent gate command:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

`scripts/local_quality_gate.py` is the accepted local CI-equivalent gate for JC
Coach during the restricted foundation-hardening lane. It is the standard local
command to run before an Executor claims PASS on code, script or test changes,
subject to stricter Task Card requirements. It runs project gate preflight,
changed and required-checks evidence; deterministic semantic AI eval fixtures;
golden metric readiness fixtures; the full safe pytest command with
`APP_ENV=test` and `PYTHONDONTWRITEBYTECODE=1`; Ruff; `git diff --check`; and
project gate postflight. The command returns non-zero if any required
subcommand fails. The focused fixture checks are intentionally named in the gate
output so AI/recommendation/final-readiness review cannot miss them by relying
only on inferred full-suite coverage.

Each local gate subcommand logs a timestamped start and end marker, emits a
heartbeat for long-running steps, and has a per-step timeout. A timed-out
subcommand fails the gate; timeout handling is diagnostic only and does not skip
or weaken semantic eval fixtures, golden metric fixtures, full safe pytest,
Ruff, `git diff --check` or project-gate checks.

This local CI-equivalent gate is not hosted CI. It does not add provider
configuration, `.github` workflow files, secrets, external accounts, package
installation or branch protection. Hosted CI remains a separate future policy
and configuration decision if the user explicitly approves it. The local gate
also does not by itself prove the final readiness gate.

Known residual quality-gate risk: H1 final readiness evidence recorded a
full-suite pytest stall during
`APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`.
FH-124R-01 bounded recovery diagnostics did not reproduce the stall: verbose
full-suite pytest, the original H1 full-suite command and
`scripts/local_quality_gate.py` passed. This recovery evidence does not by
itself make H1 a readiness PASS; reports must keep the H1 failed-gate history
visible until H1 is rerun and accepted.

Project gate preflight/postflight commands:

```bash
.venv/bin/python scripts/project_gate.py preflight
.venv/bin/python scripts/project_gate.py changed
.venv/bin/python scripts/project_gate.py required-checks
.venv/bin/python scripts/project_gate.py postflight
```

`project_gate.py` is a read-only report helper. It records task-start and
task-close evidence such as working directory, branch, recent commits,
`git status --short -uall`, changed/untracked files, inferred guardians,
required/recommended checks, governance file presence, diff stat and the
production DB SHA. It does not run services, imports, parser jobs, evaluator
jobs, package installs or DB mutations.

PASS verdict policy:

- Code, script or test changes require a passing `.venv/bin/python
  scripts/local_quality_gate.py` before Executor may claim `PASS`, unless a
  stricter Task Card requires additional checks.
- Docs-only governance/status/report tasks are not required to run pytest, Ruff
  or the local quality gate unless the Task Card or changed files require them.
  Their PASS requirements remain the docs-safe project gate commands,
  `git diff --check`, scope/allowed-file review and any stricter Task Card
  checks.
- `PASS` is forbidden when a required check is missing, failed, stalled, timed
  out or skipped without explicit task authorization.
- `PASS_WITH_WARNINGS` must not be used to imply that a mandatory gate passed
  when it did not. Use `FAIL` when required acceptance checks fail after work
  completes, and `BLOCKED` when a stop condition or missing authorization
  prevents safe completion.

For code, test or script changes, task reports should include the project gate
commands, the focused relevant tests, the full safe test suite, Ruff and
`git diff --check` unless the task card gives stricter instructions.

## Required Checks By Task Class

Task Cards can add stricter checks. Reports must list required checks, checks
actually run, checks not run with exact reasons, failed or stalled checks and
any residual risk/owner/target follow-up.

Minimum check expectations:

| Task/change class | Minimum checks |
|---|---|
| Docs-only governance/status/report tasks | `git status --short` before edits, project gate `preflight`, project gate `changed`, project gate `required-checks`, project gate `postflight`, `git diff --check` and scope/allowed-file review. Do not run live app, service, import, parser, evaluator or manual evaluator commands unless explicitly authorized. Do not run pytest, Ruff or the local quality gate unless the Task Card or changed files require them. |
| Code, script or test changes | `.venv/bin/python scripts/local_quality_gate.py` plus any focused tests required by the Task Card. This is the accepted local CI-equivalent PASS gate for this class and covers project gate preflight/changed/required-checks/postflight evidence, full safe pytest, Ruff and `git diff --check`. |
| DB/schema-risk tasks | Explicit DB/schema authorization first; DB backup/SHA evidence when mutation is authorized; migration/schema checks and DB tests named by the Task Card; project gate evidence; `git diff --check`. |
| Import/parser/evaluator-risk tasks | Explicit authorization before live import, parser, evaluator or manual evaluator commands; cap/temp-dir/safety evidence when relevant; targeted safe checks or dry-run/read-only diagnostics; project gate evidence; `git diff --check`. |
| Runtime/deploy/service-risk tasks | Explicit authorization before service/deploy changes; targeted runtime checks or smoke checks named by the Task Card; project gate evidence; `git diff --check`. |
| UI/web route/template/static tasks | Relevant route/template/static tests; safe smoke or screenshot checks when scoped; local quality gate if code/tests changed; project gate evidence; `git diff --check`. |
| Recommendation/coach/metrics/AI tasks | Relevant recommendation, metric truth, confidence, AI validator or semantic eval checks; local quality gate if code/tests changed; project gate evidence; `git diff --check`; no unsupported hard claims. |
| Audit/review/discovery tasks | Read-only evidence commands named by the Task Card, `git status --short`, project gate evidence when requested and a report with findings, completeness and follow-up recommendations when gaps are found. |

Skipped or failed checks are not accepted silently. If a required check cannot
run or does not pass, the report must state the command, exact reason, residual
risk and whether the task is `BLOCKED` or `FAIL`. A task-authorized skipped
check can still be reported as not run, but it is not a missing mandatory check.
`PASS_WITH_WARNINGS` is reserved for passed required checks with non-blocking
warnings or residual risks.

Migration discipline checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_migrations.py -q
bash -n scripts/migration_status.sh
bash -n scripts/migration_check_on_copy.sh
```

Metric Truth Layer targeted checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
```

Parser facts confidence checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
```

C2 metric fixture and null/empty regression checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_metrics_c2_fixtures.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py tests/test_metrics_c2_fixtures.py -q
```

Null/empty metric regression policy:

- Empty match windows must produce `unavailable` confidence, not `exact`,
  `partial` or hard advice evidence.
- A metric with only `null`/missing values must keep `present_count=0`,
  `coverage=0.0` and a visible no-populated-values reason.
- Missing metric values must not be imputed from adjacent stats, parser payload
  warnings, map/source filters or aggregate math.
- Static regression fixtures must be synthetic or sanitized and must not include
  raw demos, uploads, production DB rows, secrets, tokens, real Steam IDs or
  personally sensitive values.

Steam cursor truth checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_cursor_truth.py -q
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_security.py tests/test_ownership.py tests/test_steam_cursor_truth.py -q
```

AI Output Validator checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q
```

Semantic AI eval gate checks:

```bash
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_semantic_ai_eval.py -q -p no:cacheprovider
```

Golden metric readiness fixture checks:

```bash
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_metrics_c2_fixtures.py -q -p no:cacheprovider
```

Coach-first UI checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
```

Do not run tests by invoking the app against the default runtime `.env` or `data/cs2_coach.db`.

## Rules

- Do not run parser jobs, Steam jobs or import jobs during documentation-only tasks.
- Tests must not use production DB/settings.
- `APP_ENV=test` with production `DATABASE_URL` must fail.
- Test/smoke registration emails (`test-*@example.test`, `smoke-*@example.test`) are allowed only in `APP_ENV=test` with a non-production DB.
- `TestClient(app)` must use the temp test DB created by pytest configuration, not `data/cs2_coach.db`.
- For Python route/template changes, perform live smoke checks only when the task explicitly involves runtime behavior and it is safe to start/restart the app.

## Endpoint Contract Test Rules

Endpoint contract tests should stay small and critical-path focused. Prefer
stable contracts: status/auth behavior, redirect targets, API-token versus
browser CSRF behavior, and representative response/input fields.

Required when endpoint behavior changes:

- path, method, auth/owner boundary, CSRF/API-token behavior, status code,
  redirect target, request input or response field semantics changed;
- mutation route behavior changed, including DB writes, artifact writes,
  recommendation updates, AI result/report persistence or settings writes;
- import/parser/Steam/evaluator routes changed, with explicit task
  authorization and isolated mocks/fixtures only.

Not enough by itself:

- broad UI smoke coverage without the changed contract assertion;
- service tests that do not verify route translation for an HTTP contract
  change;
- tests pointed at `data/cs2_coach.db`, live Steam/Valve imports, parser jobs,
  evaluator/manual-evaluator jobs or service/deploy state.

## Isolation Guarantees

- Test runtime DB: `/tmp/jc-coach-pytest-<pid>/cs2_coach_test.db` by default.
- Test upload/inbox/reports/AI handoff dirs: `/tmp/jc-coach-pytest-<pid>/...`.
- Production DB path guard: `app.config._assert_safe_test_settings`.
- Pytest DB path guard: `tests/conftest.py` calls `app.config.assert_test_database_not_production()` before importing app DB/session modules.
- Web smoke tests may import `app.main`, but startup `init_db()` must target the temp test DB.

## Coverage Priorities

- API auth, CSRF, rate limits and strong secret fail-fast.
- Import tolerance and dedupe.
- Analytics and metric confidence.
- Metric Truth Layer reliability/suppression policy.
- Parser-derived fact confidence and weak-fact suppression.
- Recommendation lifecycle and evaluation.
- AI payload/result persistence.
- AI output validation with mocked provider/output only.
- Coach-first UI rendering and GET/read no-mutation behavior.
- Steam cursor handling and job status without real external jobs.
- Steam OpenID verification with mocked Steam responses only.
- Migration status/copy tooling against temp DB or copied DB only.

## Forbidden During Stage 0

- Import jobs.
- Steam jobs.
- Parser jobs against real demos.
- Tests or smoke checks that touch `data/cs2_coach.db`.
