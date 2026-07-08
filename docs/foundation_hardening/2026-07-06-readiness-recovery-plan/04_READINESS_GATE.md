# Readiness Gate

Date: 2026-07-06.

Gate result is binary:

```text
PASS / FAIL
```

Until this gate is PASS:

```text
READY_FOR_MAJOR_CS2_FEATURE_WORK: NO
```

## Hard Blockers

Gate FAIL if any item is true:

- Any P0 from `02_P0_P1_HARDENING_BACKLOG.md` is open without explicit hard
  blocker status and owner.
- Any P1 is open without approved workaround and risk acceptance.
- Main repo worktree contains unexplained unrelated changes before a hardening
  task starts.
- Production DB was mutated without explicit WP authorization, backup and
  before/after SHA.
- Live Steam/import/parser/evaluator/manual evaluator ran without explicit
  authorization.
- Public/friends access work started.
- Major schema, import-scale, planner implementation or CS2 domain expansion
  started before the relevant foundation task passed.

Evidence basis: audit `00_EXECUTIVE_SUMMARY.md`, "Do Not Touch Until Fixed Or
Explicitly Scoped"; audit `08_CRITICAL_GAPS.md`; root `AGENTS.md`.

## Required Docs

Gate PASS requires all:

- `docs/CURRENT_STATUS.md` points to this foundation-hardening lane and states
  restricted scope.
- `docs/project_management/WP_REGISTRY.md` records that normal WP-018 major work
  is paused or restricted pending this gate.
- `docs/project_management/VERSION_ROADMAP.md` carries the pause/resume state.
- A structured risk register exists or `docs/KNOWN_LIMITATIONS.md` has
  owner/status/target WP/evidence fields for foundation risks.
- Source trust/sample-size policy is documented.
- AI coach prompt/payload versioning contract is documented.
- CS2 domain unavailable/weak/hard-evidence boundaries are documented.

## Required Code/Architecture Conditions

Gate PASS requires all:

- Migration baseline and schema diff gate are accepted.
- Startup schema compatibility helper receives no new schema behavior.
- Architecture map documents modules, data flow and mutation boundaries.
- API contract inventory exists for critical read and mutation endpoints.
- Global DB engine/settings import-order hazard is guarded by tests or accepted
  with documented workaround.

## Required Data/Metrics Conditions

Gate PASS requires all:

- Source trust registry covers CSV, JSON, demo, Steam/Valve and FACEIT states.
- Sample-size thresholds exist for accepted metric categories.
- Metric formulas/reliability docs stay synchronized with tests.
- Golden aggregate fixtures cover the accepted core metrics.
- Weak/unavailable metrics cannot drive hard recommendations.
- Playlist-specific claims remain forbidden unless reliable metadata exists.

## Required AI Coach Conditions

Gate PASS requires all:

- Prompt and payload versions are present in AI handoff/result metadata or an
  accepted no-schema workaround is documented.
- Semantic AI eval baseline exists and covers overclaim, hallucinated metric,
  weak-metric caveat and fallback cases.
- Coach advice confidence contract exists.
- Evidence link model exists from problem to metric to match to recommendation.
- Diagnosis registry/recommendation planner design is accepted before any major
  planner implementation.

## Required Tests/Evals/Quality Gates

Gate PASS requires all:

- Mandatory local gate or CI runs pytest, Ruff, `git diff --check` and project
  gate.
- For code, script or test changes, the accepted local CI-equivalent PASS gate
  is `.venv/bin/python scripts/local_quality_gate.py`, which covers project
  gate preflight, changed, required-checks and postflight evidence; focused
  deterministic semantic AI eval fixtures; focused golden metric readiness
  fixtures; full safe pytest; Ruff; and `git diff --check`.
- Docs-only governance/status/report tasks are not required to run pytest, Ruff
  or the local quality gate unless the Task Card or changed files require them.
  Their PASS requirements are the docs-safe project gate commands,
  `git diff --check`, scope/allowed-file review and any stricter Task Card
  checks.
- No task may claim `PASS` when a required check for its task/change class is
  missing, failed, stalled, timed out or skipped without explicit task
  authorization. `PASS_WITH_WARNINGS` must not be used to imply that a
  mandatory gate passed when it did not.
- Latest required command outputs are in the final hardening report.
- Full test suite passes or failures are explicitly accepted as unrelated with
  owner and target WP.
- Ruff passes.
- `git diff --check` passes.
- Contract/eval/golden metric tests added during hardening pass.
- The known full-suite pytest stall remains visible as an unresolved residual
  quality-gate risk until fixed or explicitly accepted for the final readiness
  gate.

## Required Agent Workflow Conditions

Gate PASS requires all:

- Every hardening task used a task card or equivalent prompt with Task, Task
  type, Mode, Output mode, Goal, Scope, Report path, acceptance constraints and
  stop conditions.
- Every task report includes changed files, diff summary, checks, docs update
  summary, DB/import/runtime safety declaration and residual risks.
- PM/Execution roles remain separate unless the user explicitly merges them for
  a task.
- Protected control-plane docs are changed only by explicitly scoped
  governance/control-plane tasks.

## Required PM/Execution Handoff Conditions

Gate PASS requires all:

- `07_CODEX_EXECUTION_HANDOFF.md` is current.
- All accepted hardening task reports are linked from current state or registry.
- Open residual risks are either accepted or placed in post-readiness backlog.
- The user has a clear resume plan for WP-018 and later WPs.

## Required Final Audit Commands/Checks

Run before declaring PASS:

```bash
git status --short
.venv/bin/python scripts/project_gate.py changed
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_semantic_ai_eval.py -q -p no:cacheprovider
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_metrics_c2_fixtures.py -q -p no:cacheprovider
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
.venv/bin/ruff check . --no-cache
git diff --check
```

If a docs-only final audit chooses not to run the full suite, the gate is FAIL
unless the user explicitly accepts the reduced check set.

## Exit Criteria

Gate PASS only when:

- P0 status: closed or explicit hard blocker.
- P1 status: closed or accepted workaround/risk.
- P2/P3 status: triaged.
- Major CS2 work remains frozen until PASS.
- Hardening report proves checks, docs, safety and residual risks.
- Project status can change from `CONTINUE WITH RESTRICTED SCOPE` to
  `READY_FOR_MAJOR_CS2_FEATURE_WORK`.
