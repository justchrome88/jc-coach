# AGENTS.md - JC Coach Project Contract

This repository is the controlled personal CS2 coach project `JC Coach`.
Codex must treat this file as the root operating contract for every work
package unless the current explicit user WP prompt is stricter.

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
- Do not commit unless explicitly asked.
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
- Be honest: use `PASS_WITH_WARNINGS` when warnings exist.

## 9. Current Roadmap

- `v0.8` accepted: recommendation loop.
- `v0.9` target: real data onboarding.
- Next after `v0.9`: `v0.10` coach quality calibration.
- Then `v0.11` daily UX, `v0.12` hardening and `v1.0` personal MVP.

## 10. Style

- Keep changes small and scoped.
- Prefer existing project patterns and docs.
- Do not perform hidden runtime, DB, import, parser, evaluator or report-writing
  side effects.
- If safe completion is not possible inside the WP, stop and report `BLOCKED`.
