# Handoff

Last updated: 2026-07-10.

## Purpose

This file is the compact new-session bootstrap for JC Coach. It is not the full project history and must not duplicate `AGENTS.md`.

## Current F10 Handoff

- Current lane: F10_MISSION_BACKEND_REPAIR_SEQUENCE.
- F09 completed with warnings; the preserved JSON operation evidence identifies
  parser artifact 90.
- F10A and F10B are accepted repairs.
- F10C completed documentation and PM routing synchronization.
- Next task: F10D_FINAL_REAL_MISSION_BACKEND_ACCEPTANCE_RERUN.
- MISSION_BACKEND_ACCEPTED_FOR_UI_API: false. UI/API presentation remains
  blocked until F10D accepts the final real rerun.
- Owner-only personal scope, fail-closed weak evidence, no public/friends
  readiness, and no v1.0 claim remain mandatory.

## Historical Pre-F10 Handoff

- Project: JC Coach, a personal AI coach for CS2.
- Primary workspace convention: start future Codex sessions from
  `/opt/jc-coach`.
- JC Forge is not the active product and must not be built unless a future
  explicit task changes product scope.
- Current organizational mini-phase: `LEAN_DOCS_CLEANUP` /
  `CODEX_NATIVE_SIMPLIFICATION`, closed by `LEAN-DOCS-06`; do not return to
  docs cleanup unless explicitly scoped.
- Current product version: `v0.9`.
- Current lane:
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE`, authorized by user decision after
  GATE-001.
- The scoped WP-018 coach quality/calibration/output-quality lane remains
  available, but it is no longer the only authorized post-foundation product
  lane.
- Current active WP: `WP-018 Coach Quality Calibration` remains open and is
  not complete; the preparation/prelude layer is closed.
- Next scoped task:
  `MVP-001_AUTH_STEAM_IDENTITY_FOUNDATION_AND_GUARDRAILS`.
- WP-018 targets `v0.10`, but `v0.10` is not promoted. Work remains authorized
  only for narrow AI coach quality, calibration and output-quality scope. This
  is not a broad product expansion.
- Runtime: FastAPI / Uvicorn service `jc-coach.service` on `127.0.0.1:8010`.
- Production DB: `data/cs2_coach.db`.

## Bootstrap For A New Codex Or ChatGPT Session

1. Read `AGENTS.md`.
2. Read `docs/CURRENT_STATUS.md`.
3. Read `docs/project_management/WP_REGISTRY.md`.
4. For a new long session or chat handoff, also read this file.
5. Use `/opt/jc-coach-pm` only as legacy archive/reference when the active
   task explicitly needs that context. It is not the primary Codex launch
   workspace.
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
- WP-018-01 through WP-018-05 plus
  `WP-018-PRELUDE-CLOSE_QUALITY_INFRASTRUCTURE_READY` closed the WP-018
  preparation/prelude layer.
- Runtime AI coach quality infrastructure now available: version/snapshot
  metadata, runtime CS2 domain constraints, semantic validator checks, safe
  fallback behavior and accepted/rejected output-quality fixtures.
- GATE-002 records the user decision to authorize
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` for controlled implementation WPs
  across auth / Steam identity, import, demo storage, parser, normalized
  events, derived context, metric snapshots, AI Scout, Evidence Validator,
  missions and coach UI.

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
- The old broad pause language no longer blocks scoped work inside
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` when the future WP explicitly defines
  scope, allowed files, mutation/job authorization and evidence requirements.
- Narrow WP-018 AI coach quality, calibration, output-quality, evidence,
  caveat, docs or tests work may proceed only when explicitly scoped and when
  it improves readiness without adding unsupported claims.
- Can-carry warnings: Starlette/TestClient deprecation warning remains known;
  provider-specific structured response enforcement remains shallow;
  deterministic semantic checks are not a full entailment proof; wording
  calibration remains future WP-018 work.
- Docs-only roadmap edits, H1 PASS evidence and H2 closure do not change the
  readiness flag; `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`.

## Current Next Safe Step

Run F10D_FINAL_REAL_MISSION_BACKEND_ACCEPTANCE_RERUN manually against the
accepted repaired semantics. Do not authorize mission UI/API work before it
accepts.

## Historical Pre-F10 Next Safe Step

Proceed to the first MVP lane WP:
`MVP-001_AUTH_STEAM_IDENTITY_FOUNDATION_AND_GUARDRAILS`.

That task should define and implement only the first scoped auth / Steam
identity foundation slice named by its Task Card. It must preserve owner-only
identity boundaries, avoid public/friends readiness claims, and must not run
live Steam/Valve import, parser, evaluator, manual evaluator, service/deploy
changes or production DB/schema/data mutation unless the Task Card explicitly
authorizes that risk and includes the required evidence contract.

`WP-018A_COACH_OUTPUT_QUALITY_DIAGNOSIS` remains a valid scoped WP-018 next
task if the user chooses the coach-quality lane instead of the MVP auth/import
lane.

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
