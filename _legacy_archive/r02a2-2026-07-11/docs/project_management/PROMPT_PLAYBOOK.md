# JC Coach Prompt Playbook

## 1. Purpose

This is a practical reference for ChatGPT to create clear, stable Codex task
prompts for JC Coach. It helps future prompts stay scoped, safety-aware and
consistent with the current project source of truth.

This file is not a new agent system, does not implement Codex Native and does
not introduce JC Forge.

## 2. Universal Prompt Rules

- Always start from `/opt/jc-coach`.
- Read Hot docs first: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
  `docs/HANDOFF.md` and `docs/project_management/WP_REGISTRY.md`.
- Do not read all docs by default.
- No JC Forge.
- No Codex Native implementation.
- PM, Executor, Reviewer and Documentation Steward are prompt roles only.
- No DB, schema, import, parser, evaluator, runtime, deploy or package changes
  unless explicitly scoped.
- Every prompt must include: Task ID, role, mode, goal, preflight, allowed
  files, forbidden files/actions, checks and console output.
- Every prompt should name task-relevant Warm docs only when they are required
  for the task type.
- Every prompt should say whether commits, pushes, live imports, parser jobs,
  evaluator jobs, service restarts and package installs are forbidden or
  explicitly authorized.

## Language Policy

- Direct ChatGPT-to-user explanations should stay Russian by default.
- Codex task prompts may be written in English.
- Codex console output and internal technical reports may be English.
- Short user-facing notes may be Russian when helpful.
- Human-facing product documentation should be Russian when it is meant for direct user reading.
- Long internal technical reports/docs may be English if that reduces token cost and keeps meaning clear.
- Language choice must not change scope, safety rules, source-of-truth order, or authorization requirements.

## 3. Task Type Router

| Task type | When to use | Required Warm docs | Required safety gates | Usual allowed files | Usual forbidden actions | Minimum checks |
|---|---|---|---|---|---|---|
| `POST_FOUNDATION_AUDIT` | Defect, warning and stabilization planning after foundation hardening closure. | Current Hot docs, current risk/closure summaries, and only task-relevant archived foundation evidence when needed. | Read-only unless a specific remediation is scoped; do not restart WP-018 or major CS2 work. | Audit/stabilization reports and explicitly scoped status docs. | Product feature work, DB/schema changes, imports, parser/evaluator jobs, runtime/deploy changes. | `git diff --check`, `git status --short`, evidence list of reviewed warnings. |
| `PARSER` | Demo parser, parser artifacts, import-to-parser handoff, parser reliability. | Parser/import docs, DB/data safety docs, relevant historical parser reports. | No production parser jobs unless explicitly authorized; use fixtures or copied DB only if scoped. | Parser code/tests/fixtures only when explicitly listed. | Live imports, production parser jobs, raw demo deletion/move/rewrite, DB mutation without scoped backup/SHA. | Targeted parser tests, fixture validation, `git diff --check`, `git status --short`. |
| `METRICS` | Metric truth, metric calculation, weak metric caveats, metric confidence. | Metrics/evaluation docs and relevant acceptance reports. | Preserve weak-metric caveats and metric confidence limitations. | Metric code/tests/docs explicitly listed. | Unsupported precision claims, hard-evaluating legacy recommendations without refresh. | Targeted metric tests, sample evidence, `git diff --check`, `git status --short`. |
| `RECOMMENDATION_ENGINE` | Recommendation loop, planner, evaluation routing or recommendation state. | Recommendation and evaluator docs, acceptance matrix, relevant WP reports. | Recommendation `#5` remains active hard recommendation unless explicitly changed. | Recommendation code/tests/docs explicitly listed. | New hard evaluations for legacy `#1`, `#3`, `#4`; evaluator jobs without authorization. | Targeted recommendation tests, state/evidence review, `git diff --check`, `git status --short`. |
| `AI_COACH_QUALITY` | WP-018-related coach quality, calibration, output caveats. | WP-018 context, coach quality docs, acceptance matrix. | Major WP-018 work remains paused until post-foundation audit/stabilization authorizes restart. | Narrow coach docs/tests/code only if explicitly scoped. | Unsupported CS2/domain claims, broad coach expansion, v1.0/public readiness claims. | Targeted tests or snapshot checks, caveat review, `git diff --check`, `git status --short`. |
| `UI_WEB` | Dashboard, settings, owner workflow and frontend views. | UI/workflow docs and relevant product acceptance docs. | Do not weaken playlist/mode caveats or public/friends blockers. | UI code/tests/docs explicitly listed. | Backend DB/schema/import/runtime changes unless separately scoped. | Targeted UI tests or screenshots when applicable, `git diff --check`, `git status --short`. |
| `STEAM_IMPORT` | Steam/Valve import planning, guarded live import, share-code processing. | Import runbooks, DB/data safety docs, latest status and relevant import reports. | Live Steam/Valve import requires explicit authorization; cap remains `1` unless explicitly changed. | Import docs/code/tests only when listed; live evidence report if authorized. | Unscoped live import, cap raise, unscoped demo download/storage mutation, parser/evaluator jobs, DB mutation without safety evidence. | Pre/post DB SHA if scoped, import logs/evidence if authorized, `git diff --check`, `git status --short`. |
| `DB_SCHEMA` | Database schema, migrations, data integrity and storage safety. | DB/data safety docs, migration docs, acceptance matrix. | Explicit backup/SHA and rollback scope required for any production DB/schema mutation. | Migration files/tests/docs only when listed. | Production DB mutation without explicit authorization, broad data rewrites, uploads/raw demo changes. | Migration tests, schema diff/evidence, backup/SHA evidence if authorized, `git diff --check`, `git status --short`. |
| `TESTING_QA` | Test stabilization, targeted QA, quality gates. | Testing docs, affected area docs, recent failure reports. | Do not broaden into feature work; avoid DB/import/parser/evaluator side effects unless scoped. | Tests and narrow code fixes explicitly listed. | Package installs, broad refactors, service restarts, production data mutation. | Relevant test command(s), `git diff --check`, `git status --short`. |
| `DOCS_ONLY` | Documentation cleanup, reports, handoff, governance clarification. | Only task-relevant Warm docs. | Do not change product behavior or source-of-truth state beyond scope. | Explicit docs/report paths. | Code/tests/scripts/tools/data/deploy/package/DB changes, broad archive/delete without scope. | `git diff --check`, `git status --short`, link/path sanity check when relevant. |
| `RELEASE_CLOSURE` | Promotion, closure, release readiness or final acceptance reports. | WP registry, roadmap, acceptance matrix, relevant completed reports. | Verify prerequisites; carry warnings forward; do not claim v1.0/public readiness unless accepted. | Release reports and explicitly scoped canonical docs. | Silent blocker closure, WP renumbering, unsupported promotion claims. | Prerequisite checklist, required tests/evidence, `git diff --check`, `git status --short`. |

## 4. Prompt Skeleton

Use this skeleton for future Codex task prompts:

````text
You are working in one Codex window from the product repo `/opt/jc-coach`.

Role: <PM / Executor / Reviewer / Documentation Steward>

Task ID: `<TASK_ID>`

Mode: `<task-type / risk-level / output-mode>`

Goal:
<One concise goal. State what success means.>

Do not:
- <Forbidden product or process expansions.>
- <Forbidden risky operations.>

Preflight:
```bash
cd /opt/jc-coach
git status --short
git branch --show-current
git rev-parse HEAD
```

If there are unexplained dirty or untracked files, STOP and report `BLOCKED`.

Read first:
```text
AGENTS.md
docs/CURRENT_STATUS.md
docs/HANDOFF.md
docs/project_management/WP_REGISTRY.md
<task-relevant Warm docs only>
```

Allowed changes:
```text
<Explicit file paths or globs>
```

Forbidden changes/actions:
```text
<Explicit files, folders and operations>
```

Required work:
- <Step 1>
- <Step 2>
- <Step 3>

Checks:
```bash
cd /opt/jc-coach
<targeted command if applicable>
git diff --check
git status --short
```

Do not commit.
Do not push.

Console output:
```text
Result:
Report path:
Changed files:
Checks:
git status --short:
Warnings / blockers:
Recommended next task:
```
````

## 5. Parser Task Template

Use this for parser, demo artifact and parser/import boundary tasks.

```text
Task type: PARSER

Read first:
- Hot docs.
- Task-relevant parser/import docs.
- DB/data safety docs if any DB, fixture, artifact or production data path is
  touched.
- Relevant parser/import historical report only when it is evidence for the
  current defect.

Safety:
- No production parser jobs unless explicitly authorized.
- No live Steam/Valve import unless explicitly authorized.
- No raw demo deletion, movement, compression or rewrite unless explicitly
  scoped.
- Use copied DBs, test fixtures or synthetic fixtures only when the prompt
  explicitly scopes them.
- If production DB read/write is authorized, require backup/SHA evidence and
  exact commands.

Allowed files:
- Name exact parser modules, parser tests, fixture files and report path.

Checks:
- Targeted parser/unit tests.
- Fixture or copied-DB validation evidence when scoped.
- `git diff --check`.
- `git status --short`.
```

## 6. Metrics Task Template

Use this for metric truth, metric calculation and metric caveat tasks.

```text
Task type: METRICS

Read first:
- Hot docs.
- Task-relevant metric/evaluation docs.
- Relevant acceptance reports for weak metrics and metric confidence.

Safety:
- Preserve weak-metric caveats.
- Do not convert low-confidence metrics into hard claims.
- Do not evaluate legacy recommendations `#1`, `#3` or `#4` unless explicitly
  refreshed.
- Do not run evaluator jobs unless explicitly authorized.

Allowed files:
- Name exact metric modules, tests and docs/report paths.

Checks:
- Targeted metric tests.
- Evidence sample or before/after calculation where useful.
- `git diff --check`.
- `git status --short`.
```

## 7. Recommendation Task Template

Use this for recommendation loop, planner, evaluation and recommendation state
tasks.

```text
Task type: RECOMMENDATION_ENGINE

Read first:
- Hot docs.
- Recommendation/evaluator docs relevant to the requested change.
- Acceptance matrix or relevant WP reports when recommendation status matters.

Safety:
- Recommendation `#5` remains the accepted active hard recommendation unless
  the task explicitly changes it.
- Do not hard-evaluate legacy recommendations `#1`, `#3` or `#4` unless a
  future accepted task refreshes them.
- Preserve `metric_confidence` in evaluations.
- Do not run evaluator/manual evaluator jobs unless explicitly authorized.

Allowed files:
- Name exact recommendation modules, tests and docs/report paths.

Checks:
- Targeted recommendation tests.
- State transition or report evidence if scoped.
- `git diff --check`.
- `git status --short`.
```

## 8. AI Coach Quality Task Template

Use this for WP-018, coach quality and output calibration tasks.

```text
Task type: AI_COACH_QUALITY

Read first:
- Hot docs.
- WP-018 context only when the task is explicitly WP-018-related.
- Coach quality, output calibration or acceptance docs relevant to the task.

Safety:
- Unrestricted WP-018 and major CS2 feature work remain paused until the
  post-foundation audit/stabilization lane authorizes restart.
- Do not add unsupported CS2/domain claims.
- Carry `v0.9` warnings forward.
- Do not claim public/friends readiness or `v1.0`.

Allowed files:
- Name exact coach modules, prompts, tests or docs/report paths.

Checks:
- Targeted coach quality tests or snapshot checks when applicable.
- Caveat/claim review.
- `git diff --check`.
- `git status --short`.
```

## 9. UI/Web Task Template

Use this for web, dashboard, settings and owner workflow tasks.

```text
Task type: UI_WEB

Read first:
- Hot docs.
- Task-relevant UI/workflow docs.
- Product acceptance docs if the UI displays recommendation, mode, playlist or
  readiness claims.

Safety:
- Preserve playlist/mode uncertainty unless reliable accepted metadata exists.
- Do not imply public/friends readiness.
- Do not change backend DB/schema/import/runtime/deploy behavior unless
  explicitly scoped.

Allowed files:
- Name exact UI modules, styles, tests and docs/report paths.

Checks:
- Targeted UI tests, lint or screenshot/manual verification as appropriate.
- `git diff --check`.
- `git status --short`.
```

## 10. Audit/Stabilization Task Template

Use this for post-foundation defect, warning and readiness stabilization tasks.

```text
Task type: POST_FOUNDATION_AUDIT

Read first:
- Hot docs.
- Current risk/closure summaries.
- Only task-relevant archived foundation evidence when needed.

Safety:
- Audit first; do not fix everything.
- Keep remediation scoped to explicitly listed files and risks.
- Do not restart WP-018 or major CS2 product work from audit evidence alone.
- Do not close blockers silently.

Allowed files:
- Audit report, stabilization plan and explicitly scoped status docs.

Checks:
- Evidence table or reviewed-warning list.
- `git diff --check`.
- `git status --short`.
```

## 11. Release/Closure Task Template

Use this for closure, release and promotion tasks.

```text
Task type: RELEASE_CLOSURE

Read first:
- Hot docs.
- WP registry.
- Roadmap, backlog and acceptance matrix when promotion or version state is in
  scope.
- Reports for all prerequisites named by the task.

Safety:
- Verify prerequisites before declaring closure or promotion.
- Carry warnings and accepted limitations forward.
- Do not claim `v1.0`, public/friends readiness, exact playlist mode or major
  CS2 readiness unless accepted evidence explicitly supports it.
- Do not renumber WPs or mark deferred/paused/failed work as implemented.

Allowed files:
- Closure report and explicitly scoped canonical docs.

Checks:
- Prerequisite checklist.
- Required test/evidence commands from the task.
- `git diff --check`.
- `git status --short`.
```

## 12. Anti-patterns

- Broad audit without scoped target.
- Read all docs.
- Fix everything.
- Archive, delete, move, renumber or rewrite without explicit scope.
- DB mutation by accident.
- Parser/import live jobs by accident.
- Evaluator/manual evaluator jobs by accident.
- Creating many task cards when one scoped task is enough.
- Building Forge.
- Inventing a Codex Native layer.
- Treating prompt roles as runtime agents or mandatory separate windows.
- Closing blockers silently.
- Claiming `v1.0`, public/friends readiness or exact playlist labels without
  accepted evidence.
