# Codex Execution Handoff

Date: 2026-07-06.

## Context

JC Coach / CS2 AI Coach completed a read-only agentic-readiness audit.

Audit folder:

```text
docs/audits/2026-07-06-agentic-readiness-audit
```

Foundation hardening plan folder:

```text
docs/foundation_hardening/2026-07-06-readiness-recovery-plan
```

Current status:

```text
CONTINUE WITH RESTRICTED SCOPE
READY_FOR_MAJOR_CS2_FEATURE_WORK: NO
```

Audit score: 66% / 3.30 of 5 across 106 audit rows. Evidence:
`00_EXECUTIVE_SUMMARY.md`.

## First Tasks In Order

1. Create or update canonical risk register / enriched known limitations.
2. Add mandatory local quality gate or CI-equivalent gate workflow.
3. Create migration baseline and schema gate.
4. Define source trust and sample-size policy.
5. Add prompt/payload versioning plan or implementation if schema-safe.
6. Build first semantic AI eval suite.
7. Design diagnosis registry and recommendation planner.
8. Expand architecture map and API contracts.
9. Add CS2 domain pack document.
10. Plan durable import worker and retry ledger.

This order follows audit `10_NEXT_10_TASKS.md`, with risk/gate work pulled
early so later execution has stronger controls.

## Strict Rules

- No unrelated changes.
- No production DB mutation.
- No live Steam/Valve import.
- No parser jobs on production data.
- No evaluator or manual evaluator on production DB.
- No major CS2 feature work.
- No broad refactor without explicit approval.
- No import cap raise.
- No service/nginx/systemd/deploy mutation.
- No package installation unless explicitly approved.
- No secret values in output.
- Every task must include diff summary.
- Every task must include tests/checks.
- Every task must include docs update summary.
- Every task must include residual risks.

## Definition Of Done For Each Hardening Task

A task is done only when:

- scope matches the Task Card;
- changed files are listed;
- no unrelated files are changed;
- required docs are updated or explicitly not needed;
- required tests/checks are run and reported;
- DB/import/runtime/service safety is declared;
- production DB SHA is reported for DB-impacting or DB-risk tasks;
- residual risks and follow-up tasks are listed;
- `git diff --check` passes.

## Standard Task Handoff Format

Use this report shape after each task:

```text
Result:
Verdict: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

Scope:

Files changed:

Diff summary:

Docs updated:

Tests/checks run:

DB/import/runtime/service safety:

Production DB SHA:

Residual risks:

Next recommended task:

Stop conditions encountered:
```

## Stop Conditions

Stop and report `BLOCKED` if:

- production DB mutation would be required without authorization;
- schema implementation is requested before migration baseline is accepted;
- public/friends access work appears in scope;
- task requires import/parser/evaluator/service/deploy action without explicit
  authorization;
- audit evidence conflicts with current Hot context;
- secret values appear in any output;
- main repo has unexplained unrelated changes before starting.

