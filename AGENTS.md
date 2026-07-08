# AGENTS.md - JC Coach Root Contract

This file is the lean root operating contract for Codex work in this
repository. The current explicit user task controls the immediate scope and can
be stricter than this file. Do not broaden a task to make progress.

## 1. Project Identity

- JC Coach is the primary product: a controlled personal AI coach for CS2.
- This repository is the canonical product repository for JC Coach.
- JC Forge is not the active product unless a future explicit task says so.
- Codex may inspect, edit, verify and report only within the current task scope.
- Stop and report `BLOCKED` instead of improvising around missing authority,
  unsafe side effects or source-of-truth conflicts.

## 2. Source Of Truth And Context Policy

Use this source-of-truth order when sources conflict:

1. Current explicit user task, for scope and stricter constraints.
2. This root `AGENTS.md`.
3. `docs/CURRENT_STATUS.md`.
4. `docs/HANDOFF.md`.
5. `docs/project_management/WP_REGISTRY.md`.
6. Task-relevant Warm docs.
7. Code, tests and task-relevant historical evidence.

Do not read all docs by default.

Hot context for ordinary tasks: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
`docs/HANDOFF.md` and `docs/project_management/WP_REGISTRY.md`.

Read Warm docs only when task-relevant, such as roadmap, acceptance, workflow,
DB/data safety, import/parser/evaluator, recommendation, UI, service,
deployment, testing, security or historical WP review context. Old reports,
prompts, audits and generated app reports are evidence/history only; they must
not override this contract or Hot docs.

For external library, framework, API or tooling behavior, use Context7 MCP or
official current docs when the task depends on that behavior. External docs
never override project source-of-truth docs or the active task scope.

## 3. Universal Safety Rules

- Do not mutate DB, schema, data files, imports, parser/evaluator/manual
  evaluator jobs, services, deployment config, package/dependency config or raw
  demos unless the current task explicitly scopes that risk.
- Do not run live Steam/Valve import unless explicitly authorized.
- Do not run parser, evaluator or manual evaluator jobs unless explicitly
  authorized.
- Do not restart services or change systemd/nginx/deploy/runtime config unless
  explicitly authorized.
- Do not install packages or change package/dependency files unless explicitly
  authorized.
- Do not delete, move, compress or rewrite raw demos without explicit storage
  scope.
- Do not generate persistent app reports unless explicitly authorized.
- Do not print secret values.
- If risky work is authorized, keep it narrow and report the requested safety
  evidence.

## 4. Git Rules

- Show `git status --short` before work.
- Stop on unexplained dirty or untracked files.
- Do not run `git add` unless explicitly authorized.
- Do not commit unless explicitly authorized.
- Do not push unless explicitly authorized.
- Never commit DBs, backups, uploads, demos, `.dem`, `.dem.bz2` or
  `__pycache__`.
- Run `git diff --check` before final report when files changed.

## 5. Current Product Guardrails

- Product version is `v0.9` with accepted warnings unless Hot docs say a later
  accepted task changed it.
- Recommendation `#5` remains the current accepted active hard recommendation
  unless a future accepted task changes it.
- Legacy recommendations `#1`, `#3` and `#4` must not receive new hard
  evaluations unless explicitly refreshed.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` unless an explicit cap-change
  task changes it.
- Playlist/mode remains unknown or provenance-only unless reliable persisted
  metadata exists; do not claim exact playlist labels without accepted evidence.
- Weak metrics stay caveated, and recommendation evaluations must preserve
  metric-confidence limitations.
- WP-018 and major CS2 product work remain paused unless explicitly authorized
  by the current user task and Hot docs.
- Public/friends readiness remains blocked.

## 6. Task Execution Defaults

- Keep changes small, scoped and reversible.
- Prefer existing project patterns and canonical docs.
- Do not perform broad cleanup, archive, deletion, renumbering or roadmap
  rewriting unless explicitly scoped.
- Do not mark deferred, paused or failed work as implemented.
- Do not close blockers silently.
- Use task-relevant Warm docs for detailed workflow or safety mechanics instead
  of carrying old Foundation-era bureaucracy into every ordinary task.

## 7. Reporting Defaults

For small tasks, keep console output compact:

- Summary
- Changed files
- Checks
- Risks / blockers
- Next step

Use a long file-backed report only when requested, when a report path is
provided, or when risk/evidence volume genuinely requires it. Be honest with
`PASS`, `PASS_WITH_WARNINGS` or `BLOCKED`.

## 8. Stop Conditions

Stop and report `BLOCKED` when:

- Worktree is dirty or has unexplained untracked files before work.
- Required authorization is missing.
- Source-of-truth docs conflict in a way that affects the task outcome.
- The task would cause unsafe DB/schema/data/import/parser/evaluator/service/
  deploy/package/raw-demo side effects.
- Required evidence or checks cannot be produced.
- The requested change would broaden into unscoped cleanup or product work.

## 9. Reference Map

- Hot status: `docs/CURRENT_STATUS.md`; handoff: `docs/HANDOFF.md`; WP order
  and gates: `docs/project_management/WP_REGISTRY.md`.
- Warm governance/process references: `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`,
  `docs/project_management/AGENT_WORKFLOW.md`,
  `docs/project_management/MASTER_WP_CHECKLIST.md` and `docs/agents/roles/*`.
- Warm roadmap/planning references: `docs/project_management/VERSION_ROADMAP.md`,
  `docs/project_management/WORK_PACKAGE_BACKLOG.md` and
  `docs/project_management/ACCEPTANCE_MATRIX.md`.
- Historical reports and audits are task-relevant evidence only.
