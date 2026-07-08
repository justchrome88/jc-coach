# Execution Plan

Date: 2026-07-06.

Source audit: `docs/audits/2026-07-06-agentic-readiness-audit`.

## Phase A: Source Of Truth / Documentation Recovery

- Goal: pause normal roadmap, establish hardening lane and make current state
  unambiguous.
- Input docs: audit `00_EXECUTIVE_SUMMARY.md`, `03_DOCS_AND_CONTEXT.md`,
  `08_CRITICAL_GAPS.md`; `AGENTS.md`; `docs/CURRENT_STATUS.md`;
  `docs/project_management/WP_REGISTRY.md`.
- Tasks: add hardening pointers, risk register plan, docs checklist, roadmap
  pause/resume language.
- Dependencies: none.
- Allowed changes: docs only.
- Forbidden changes: production code, DB, imports, parser/evaluator, service,
  package installs.
- Expected output: current lane says restricted foundation hardening.
- Acceptance criteria: docs link to this folder; no stale roadmap claims major
  WP-018 is unrestricted.
- Checks to run: `git status --short`, `git diff --check`,
  `.venv/bin/python scripts/project_gate.py changed`.
- Stop and ask human when: canonical source-of-truth docs conflict or a prior
  untracked WP result must be accepted/reverted first.

## Phase B: Architecture Boundaries And Codebase Map

- Goal: make module, route, API and mutation boundaries clear enough for safe
  agent execution.
- Input docs: audit `04_ARCHITECTURE_CODEBASE.md`; audit matrix AR-017,
  AR-018, AR-021, AR-078, AR-080, AR-081; `docs/ARCHITECTURE.md`.
- Tasks: expand architecture map, API contract inventory, route/mutation
  matrix, DB import-order guard plan.
- Dependencies: Phase A.
- Allowed changes: docs and focused tests; no broad refactor.
- Forbidden changes: route restructuring, worker implementation, schema changes
  unless explicitly scoped.
- Expected output: clear read/write/mutation boundaries and first contract tests.
- Acceptance criteria: critical routes have contract expectations; mutation
  endpoints are identified; global DB risk is guarded or accepted.
- Checks to run: targeted contract/web tests if added, full pytest if code
  touched, Ruff, diff check.
- Stop and ask human when: implementation would require schema or broad module
  movement.

## Phase C: Data Contracts / Metrics Contracts / AI Coach Logic

- Goal: prevent unsupported or non-reproducible coaching claims.
- Input docs: audit `05_DATA_METRICS_AI_COACH.md`; audit matrix AR-033,
  AR-036, AR-038, AR-039, AR-055, AR-068, AR-069, AR-072, AR-076, AR-087,
  AR-088; `docs/METRICS.md`; `docs/RECOMMENDATIONS.md`; `docs/AI_COACH.md`.
- Tasks: source trust registry, sample-size policy, advice confidence contract,
  prompt/payload versioning, semantic eval fixtures, planner design.
- Dependencies: Phase A; migration baseline if implementation needs schema.
- Allowed changes: docs, tests, narrowly scoped AI/metrics metadata changes
  after migration safety is clear.
- Forbidden changes: unsupported CS2 hard claims, planner behavior changes
  without design approval, production report generation unless authorized.
- Expected output: contracts and tests for source trust, confidence,
  reproducibility and eval safety.
- Acceptance criteria: weak/unavailable metrics cannot drive hard
  recommendations; AI evals catch overclaims.
- Checks to run: metric truth tests, AI validator/eval tests, full pytest if
  code touched, Ruff, diff check.
- Stop and ask human when: prompt/payload versioning requires DB schema changes
  before migration baseline is accepted.

## Phase D: Tests / Evals / Quality Gates

- Goal: make readiness checks repeatable and hard to skip.
- Input docs: audit `06_TESTS_EVALS_QUALITY.md`; audit matrix AR-009, AR-016,
  AR-083 through AR-090; `docs/TESTING.md`; `scripts/project_gate.py`.
- Tasks: mandatory gate command, CI or local equivalent, semantic eval suite,
  golden metric fixtures, contract tests.
- Dependencies: Phase C for eval contracts.
- Allowed changes: scripts, CI config, tests, docs.
- Forbidden changes: test shortcuts that hit production DB; cache/artifact
  commits.
- Expected output: one standard quality gate for Executor reports.
- Acceptance criteria: gate runs pytest/Ruff/diff/project_gate and failures
  block PASS claims. Code, script or test changes require a passing
  `.venv/bin/python scripts/local_quality_gate.py` before Executor may claim
  `PASS`; docs-only governance/status/report tasks require docs-safe project
  gate commands, `git diff --check`, scope/allowed-file review and
  task-specific checks unless the Task Card or changed files require pytest,
  Ruff or the local quality gate.
- Checks to run: the new gate, full pytest, Ruff, diff check.
- Stop and ask human when: CI provider choice or repository policy is unclear.

## Phase E: Agent Workflow Enforcement

- Goal: enforce task lifecycle, permissions, reports and docs updates.
- Input docs: audit `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`; audit matrix AR-005,
  AR-007, AR-010, AR-014; `docs/project_management/AGENT_WORKFLOW.md`.
- Tasks: task close checklist, docs update checklist, DB/import/runtime safety
  declarations, handoff/report template updates.
- Dependencies: Phase D gate command.
- Allowed changes: governance docs and templates.
- Forbidden changes: weakening root `AGENTS.md` or protected docs outside scope.
- Expected output: every task has preflight, acceptance, checks and residual risk
  reporting.
- Acceptance criteria: Execution handoff can be used without extra decisions.
  `PASS`, `PASS_WITH_WARNINGS`, `FAIL` and `BLOCKED` are distinguished clearly:
  `PASS` requires all mandatory checks for the task/change class to pass,
  `PASS_WITH_WARNINGS` cannot stand in for a failed mandatory gate, `FAIL`
  covers completed work with failed required checks, and `BLOCKED` covers stop
  conditions or checks that cannot safely run. PM review may accept an
  Executor `BLOCKED` or `FAIL` cycle after PM-owned rerun evidence only under
  the workflow policy for same-diff, same-command-or-authorized-equivalent
  reruns with full owner/command/status/output evidence, original Executor
  verdict preserved and no better than `PASS_WITH_WARNINGS`.
- Checks to run: docs diff check, project gate changed.
- Stop and ask human when: workflow changes conflict with root `AGENTS.md`.

## Phase F: Security / Permissions / Operational Safety

- Goal: keep controlled personal scope safe and block premature exposure.
- Input docs: audit `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`; audit matrix AR-027,
  AR-095, AR-097, AR-098; `docs/SECURITY.md`; `docs/DEPLOYMENT.md`;
  `docs/BACKUP_RESTORE.md`.
- Tasks: public/friends gate, secret redaction policy, privacy/retention policy,
  incident/log taxonomy, deploy verification checklist.
- Dependencies: Phase A for roadmap pause.
- Allowed changes: docs/tests; no deploy/runtime changes.
- Forbidden changes: service restart, nginx/systemd edits, public exposure,
  secret printing.
- Expected output: explicit security/ops blockers and safe command policy.
- Acceptance criteria: public/friends readiness cannot be claimed before gate.
- Checks to run: docs diff check; security tests if code touched.
- Stop and ask human when: any live service/deploy change is needed.

## Phase G: Final Readiness Review

- Goal: decide PASS/FAIL against `04_READINESS_GATE.md`.
- Input docs: this folder, all hardening task reports, audit evidence, current
  project docs.
- Tasks: review P0/P1 closure, P2/P3 triage, checks, docs, residual risks and
  resume plan.
- Dependencies: Phases A-F accepted or explicitly risk-accepted.
- Allowed changes: final report and minimal current status/roadmap updates.
- Forbidden changes: feature implementation during review.
- Expected output: final readiness review report with PASS/FAIL.
- Acceptance criteria: binary gate result and clear return path to WP-018.
- Checks to run: final audit commands from `04_READINESS_GATE.md`.
- Stop and ask human when: any P0 remains unresolved without accepted blocker
  status or any P1 needs risk acceptance.
