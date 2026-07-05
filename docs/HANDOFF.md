# Handoff

Last updated: 2026-07-05.

## Purpose

This file is the compact new-session bootstrap for JC Coach. It is not the full project history and must not duplicate `AGENTS.md`.

## Project Identity

- Project: JC Coach, a personal AI coach for CS2.
- Current product version: `v0.8`.
- Current lane: `WP-017` Real Data Onboarding / Bulk Demo Usage targeting `v0.9`.
- Current active WP: none; latest completed governance WP is `WP-017Y No-Risk Legacy Docs Pointer Cleanup`.
- Next product WP after WP-017Y: `WP-017K Real Data Onboarding Promotion to v0.9`.
- Runtime: FastAPI / Uvicorn service `jc-coach.service` on `127.0.0.1:8010`.
- Production DB: `data/cs2_coach.db`.

## Bootstrap For A New Codex Or ChatGPT Session

1. Read `AGENTS.md`.
2. Read `docs/CURRENT_STATUS.md`.
3. Read `docs/project_management/WP_REGISTRY.md`.
4. For a new long session or chat handoff, also read this file.
5. Read Warm docs only when the task requires them, and state which files are needed and why before reading them.
6. Treat old audit reports, prompts, stage reports and generated data reports as evidence/history only.
7. For governance, planning, task routing, prompt contract or WP role workflow scope, `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`, `docs/project_management/MASTER_WP_CHECKLIST.md` and `docs/project_management/AGENT_WORKFLOW.md` are Warm references, not per-task Hot context.

## Current State Summary

- `v0.8` Recommendation Loop Acceptance is promoted for controlled personal use.
- `v0.9` is not promoted yet.
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

## Data And Product Facts To Carry Forward

- Recommendation `#5` is the only accepted active recommendation for hard progress.
- Recommendation `#5` has three real evaluations with `metric_confidence`; progress is `3/10`.
- Legacy recommendations `#1`, `#3` and `#4` are not accepted for new hard evaluations unless a future WP explicitly refreshes them.
- Post-WP-017H evidence is about 76 total matches, 22 playable demo matches, 20 exact playable dates and 22 parser artifacts.
- Steam/import cap remains `1`.
- Shell service calls that touch Steam/import temp storage need `TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp` when explicitly authorized.
- Match mode labels accepted for `v0.9`: `mode_unknown`, `provenance_demo`, `provenance_valve_matchmaking`, `exact_date_source=steam_gc_match_time`.
- Playlist-specific labels and recommendations are not accepted for `v0.9`.

## Next Safe Step

After WP-017Y is reviewed and committed by the user if accepted, continue to `WP-017K Real Data Onboarding Promotion to v0.9` only with explicit user/ChatGPT approval. WP-017K must verify registry prerequisites, carry forward WP-017G/H warnings and WP-017J limitation text, and decide promote/block without raising cap or changing product logic.

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
