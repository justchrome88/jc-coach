# AGENTS.md - JC Coach Project Contract

This repository is the controlled personal CS2 coach project `JC Coach`.
Codex must treat this file as the only root operating contract for every work
package unless the current explicit user WP prompt is stricter. The older
`AGENT.md` file is superseded and must not be used as the active contract.

## 1. Roles

- Codex is the executor/engineer: inspect, edit, verify and report within scope.
- The human/user is the operator and approval authority.
- ChatGPT/PM prompts and project docs define the active WP scope.
- Do not broaden a WP. Stop and report `BLOCKED` instead of improvising unsafe
  work.

## 2. Source Of Truth Order

When sources conflict, use this order:

1. Explicit current user WP prompt.
2. This root `AGENTS.md`.
3. `docs/CURRENT_STATUS.md`.
4. `docs/HANDOFF.md`.
5. `docs/PROJECT_CONTROL.md`.
6. `docs/project_management/*`.
7. Relevant `docs/audit/*` reports.
8. Code and tests.

Old audit reports, stage reports, task prompts and generated app reports are
evidence/history. They must not override the current control docs above.

## 2.1 Context Reading Policy

Do not read all documentation by default.

Per-task Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context additionally includes:

4. `docs/HANDOFF.md`

Read Warm context only when the task requires that domain, such as roadmap,
acceptance, deploy/service, testing, DB/data integrity, import/parser/evaluator,
recommendations, UI/web routes, security or historical WP review. Before
reading Warm docs, state which files are needed and why.

Cold context includes old audit reports, stage reports, old prompts,
`docs/tasks/*`, `instructions/*`, old roadmap/version docs and generated data
reports. Use Cold context only as evidence during investigation or audit.

For task routing, task type profiles and standard prompt/report contracts, use
`docs/project_management/AGENT_WORKFLOW.md` when the task calls for governance
workflow context. This does not expand per-task Hot context.

## 2.2 External Documentation Policy

For tasks involving external libraries, frameworks, APIs or tooling behavior,
use Context7 MCP when available before changing code, config or docs that
depend on those APIs. This includes FastAPI, SQLAlchemy, Alembic, pytest,
Playwright, frontend libraries, Codex/MCP config and other
dependency-specific behavior.

If Context7 MCP is unavailable, state that MCP docs lookup was unavailable, use
another current official source if available, and avoid confident
version-specific API claims without evidence.

This is not required for docs-only PM/process tasks that only modify internal
project state. External docs never override this file, project source-of-truth
docs or the active Task Card scope/allowed files. Executor reports should
mention external documentation lookup only when it was relevant.

## 3. Hard Safety Rules

- Never commit `data/cs2_coach.db`.
- Never commit `data/manual_backups`.
- Never commit `data/uploads`.
- Never commit `.dem` or `.dem.bz2` files.
- Never commit `__pycache__`.
- Do not mutate the production DB without explicit WP authorization, backup,
  SHA evidence and report.
- Do not run live Steam/Valve import without explicit WP authorization.
- Do not run parser jobs on production data without explicit WP authorization.
- Do not run the manual evaluator on the production DB without explicit WP
  authorization.
- Do not delete, move or compress raw demos without explicit storage WP
  authorization.
- Do not raise `STEAM_IMPORT_MAX_DEMOS_PER_RUN` without an explicit cap-change
  WP.
- Do not generate persistent app reports unless explicitly authorized.

## 4. Git Rules

- Show `git status --short` before work.
- Do not run `git add` unless explicitly asked.
- Executor Codex must not commit unless explicitly asked or a Task Card
  explicitly authorizes it.
- PM_ORCHESTRATOR may create local commits after an accepted PM review verifies
  scope, acceptance, forbidden-action safety, required checks and that no user
  decision is needed.
- Do not push unless explicitly asked.
- Commits, when authorized, must exclude DBs, backups, uploads and demos.
- Commit only scoped reports, docs, code or tests.
- Run `git diff --check` before report/commit.

## 5. Production DB Rules

- `data/cs2_coach.db` is the production DB.
- For any authorized production DB mutation, record `sha256sum
  data/cs2_coach.db` before and after.
- Back up the production DB before any authorized production mutation.
- Do not change schema unless schema work is explicitly scoped.

## 6. Steam And Import Rules

- For shell service calls, set `TMPDIR`, `TEMP` and `TMP` to
  `/opt/jc-coach/data/tmp`.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` unless changed by explicit WP.
- `ImportJob.status` is coarse; `result_json` is canonical for detailed import
  outcomes.
- Match mode is unknown for Premier/Competitive/Wingman unless reliable
  persisted metadata proves the mode.

## 7. Recommendation Rules

- Recommendation `#5` survival is the current accepted active recommendation.
- Legacy recommendations `#1`, `#3` and `#4` must not receive new hard
  evaluations unless explicitly refreshed.
- Recommendation evaluations must include `metric_confidence`.
- Weak metrics must remain caveated.
- Do not use manual evaluation as a substitute for a broken automatic loop
  unless explicitly authorized.

## 8. Reporting Rules

- Each WP must create a `docs/audit/WP_*` report.
- The report must include result, evidence, files changed, safety declarations,
  DB SHA, blockers and next WP.
- Long reports must be written to a file; console output should stay short and
  include the report path.
- Be honest: use `PASS_WITH_WARNINGS` when warnings exist.

## 9. Current Roadmap

- `v0.8` accepted: recommendation loop.
- `v0.9` target: real data onboarding.
- Next after `v0.9`: `v0.10` coach quality calibration.
- Then `v0.11` daily UX, `v0.12` hardening and `v1.0` personal MVP.

## 10. Style

- Keep changes small and scoped.
- Prefer existing project patterns and docs.
- Do not change product logic during governance cleanup.
- Do not perform hidden runtime, DB, import, parser, evaluator or report-writing
  side effects.
- Do not silently renumber WPs.
- Do not silently close blockers.
- Do not mark deferred or failed features as implemented.
- Do not create new docs when an existing canonical doc should be updated.
- If safe completion is not possible inside the WP, stop and report `BLOCKED`.
