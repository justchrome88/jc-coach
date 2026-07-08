# Handoff

Last updated: 2026-07-09.

## Purpose

This file is the compact new-session bootstrap for JC Coach. It is not the full project history and must not duplicate `AGENTS.md`.

## Project Identity

- Project: JC Coach, a personal AI coach for CS2.
- Primary workspace convention: start future Codex sessions from
  `/opt/jc-coach`.
- JC Forge is not the active product and must not be built unless a future
  explicit task changes product scope.
- Current organizational mini-phase: `LEAN_DOCS_CLEANUP` /
  `CODEX_NATIVE_SIMPLIFICATION`, closed by `LEAN-DOCS-06`; return to scoped
  JC Coach product work.
- Current product version: `v0.9`.
- Current lane: scoped WP-018 restart preparation after
  `POST_FOUNDATION_AUDIT_AND_STABILIZATION` produced `PASS_WITH_WARNINGS`.
- Current active WP: none; latest completed product WP is `WP-017K Real Data Onboarding Promotion to v0.9`.
- Next product lane: `WP-018 Coach Quality Calibration` targeting `v0.10`,
  restart-authorized only for narrow AI coach quality, calibration and
  output-quality scope. This is not a broad product expansion.
- Runtime: FastAPI / Uvicorn service `jc-coach.service` on `127.0.0.1:8010`.
- Production DB: `data/cs2_coach.db`.

## Bootstrap For A New Codex Or ChatGPT Session

1. Read `AGENTS.md`.
2. Read `docs/CURRENT_STATUS.md`.
3. Read `docs/project_management/WP_REGISTRY.md`.
4. For a new long session or chat handoff, also read this file.
5. Use `/opt/jc-coach-pm` only as PM memory, archive or reference when the
   active task explicitly needs that context. It is not the primary Codex
   launch workspace.
6. Treat Codex PM, Executor, Reviewer and Documentation Steward as prompt
   roles, not mandatory separate Codex windows.
7. Read Warm docs only when the task requires them, and state which files are needed and why before reading them.
8. Treat old audit reports, prompts, stage reports and generated data reports as evidence/history only.
9. For governance, planning, task routing, prompt contract or WP role workflow scope, `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`, `docs/project_management/MASTER_WP_CHECKLIST.md`, `docs/project_management/AGENT_WORKFLOW.md` and invoked `docs/agents/roles/*` role cards are Warm references, not per-task Hot context.
10. For future ChatGPT-generated Codex prompts, use `docs/project_management/PROMPT_PLAYBOOK.md` as the prompt-template guide after Hot docs.
11. Prompt language policy: use `docs/project_management/PROMPT_PLAYBOOK.md`; Codex prompts/reports may be English, while direct ChatGPT user discussion remains Russian.

## Current State Summary

- `v0.8` Recommendation Loop Acceptance is promoted for controlled personal use.
- `v0.9` is promoted with warnings by WP-017K.
- WP-017G accepted data integrity with warnings.
- WP-017H accepted post-batch performance with warnings.
- WP-017I diagnosed exact playlist mode as unrecoverable from current persisted data.
- WP-017J accepted explicit deferral: `v0.9` must not claim exact Premier, Competitive, Wingman, Casual, Deathmatch, FACEIT or custom playlist labels.
- WP-017S repaired documentation/governance entrypoints and documented that `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is out-of-band evidence, not the planned WP-018 product block.
- WP-017T compacted the active current-state and handoff layer before WP-017K.
- WP-017U added the project operating protocol and master WP checklist before WP-017K.
- WP-017V added the repo-native agent workflow and Documentation Steward / Docs Currency Agent before WP-017K.
- WP-017W added task type profiles, role invocation shortcuts and the short Task Card prompt contract before WP-017K.
- WP-017X produced a legacy documentation currency snapshot and conservative cleanup plan without moving, deleting or archiving files.
- WP-017Y completed no-risk legacy pointer cleanup without moving, deleting or archiving files.
- WP-017Z added Warm workflow role cards and role handoff protocol without
  creating runtime agents or automation.
- WP-017K promoted Real Data Onboarding / Bulk Demo Usage to `v0.9` with
  warnings carried forward.
- WP-017Z1 added invocation modes and output modes so future prompts can stay
  short and long role outputs can be file-backed.
- WP-017Z2 added control-plane protection so ordinary product/code/DB/import/
  runtime/UI/recommendation tasks do not edit governance rules to make work
  easier.
- POST-FOUNDATION-01 completed the defect/warning audit and stabilization plan
  with `PASS_WITH_WARNINGS`.
- PF-STAB-01 closed the restart authorization/scope-lock gate for narrow
  WP-018 AI coach quality/calibration/output-quality work only.

## Data And Product Facts To Carry Forward

- Recommendation `#5` is the only accepted active recommendation for hard progress.
- Recommendation `#5` has three real evaluations with `metric_confidence`; progress is `3/10`.
- Legacy recommendations `#1`, `#3` and `#4` are not accepted for new hard evaluations unless a future WP explicitly refreshes them.
- Post-WP-017H evidence is about 76 total matches, 22 playable demo matches, 20 exact playable dates and 22 parser artifacts.
- Steam/import cap remains `1`.
- Shell service calls that touch Steam/import temp storage need `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` when explicitly authorized.
- Match mode labels accepted for `v0.9`: `mode_unknown`, `provenance_demo`, `provenance_valve_matchmaking`, `exact_date_source=steam_gc_match_time`.
- Playlist-specific labels and recommendations are not accepted for `v0.9`.

## Current Pause / Resume State

- Project status: `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK`: `NO`.
- Foundation hardening H2 closed the recovery lane as
  `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`.
- FH-124R-03 accepted H1 final-readiness rerun evidence: full-suite pytest and
  the local quality gate passed.
- Unrestricted major WP-018 / CS2 feature expansion remains paused.
- Narrow WP-018 AI coach quality, calibration, output-quality, evidence,
  caveat, docs or tests work may proceed only when explicitly scoped and when
  it improves readiness without adding unsupported claims.
- Docs-only roadmap edits, H1 PASS evidence and H2 closure do not change the
  readiness flag; `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`.

## Next Safe Step

Proceed to the first narrow WP-018 task:
`WP-018-01_AI_COACH_QUALITY_BASELINE_AND_GAP_MAP`.

That task should be an audit/design baseline for AI coach quality, accepted
caveats and output-quality gaps. It should not implement broad product
features, claim major CS2 readiness or change DB/import/parser/evaluator/
runtime/deploy/package behavior unless a later prompt explicitly scopes that
risk.

## Forbidden Without Explicit WP Authorization

- Do not mutate production DB or schema.
- Do not run live Steam/Valve import.
- Do not download demos.
- Do not run parser, evaluator or manual evaluator jobs.
- Do not delete, move or compress raw demo files.
- Do not raise `STEAM_IMPORT_MAX_DEMOS_PER_RUN`.
- Do not generate persistent app reports.
- Do not restart service, change systemd/nginx or deploy runtime config unless the active WP requires it.
- Do not make product logic changes during governance cleanup.
- Do not run `git add`, commit or push without explicit user approval.

## Reporting Back

- Write long WP reports to `docs/audit/WP_*.md`.
- Keep console output short: report path, changed files, checks, risks and whether git status is dirty.
- Update only relevant canonical docs. Do not create new docs if an existing canonical doc should be updated.
- Do not silently renumber WPs, close blockers or mark deferred/failed features as implemented.
