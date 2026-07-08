# Document Conflicts

Audit date: 2026-07-03.

## Conflict: Product Version

### Files involved

- `README.md`
- `instructions/01_OVERNIGHT_MVP_TASK.md`
- `instructions/07_ROADMAP.md`
- `docs/PROJECT_CONTROL.md`

### What conflicts

Older documents describe the project as `MVP v0.1` or early-week roadmap work. Current repository evidence includes CSV/JSON/DEM import, deep parser foundations, Steam alpha import, recommendation lifecycle and AI persistence.

### Current truth

The canonical version is `v0.7-prep: personal alpha with coach-loop foundation`.

### Decision

Keep `README.md` as a user/operator entrypoint but make `docs/PROJECT_CONTROL.md` the version source of truth.

### Required documentation update

Add canonical notice to README and mark older instructions historical.

## Conflict: Scope Expansion Versus Hardening

### Files involved

- `docs/COMPETITOR_FEATURE_MATRIX.md`
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`
- `instructions/07_ROADMAP.md`
- `docs/audit/CS2_AI_COACH_AUDIT_2026-07-02.md`
- `docs/CURRENT_MILESTONE.md`

### What conflicts

Some documents push FACEIT, viewer, heatmaps, friends beta or other expansion. The audit and current milestone require security, metric truth, parser confidence and recommendation planner hardening first.

### Current truth

Expansion features are frozen until the current milestone closes.

### Decision

Move expansion ideas into `LATER.md`/roadmap parking and keep current milestone focused on hardening.

### Required documentation update

Create `LATER.md`, `docs/CURRENT_MILESTONE.md` and deprecation notices for old prompt libraries.

## Conflict: Security Readiness

### Files involved

- `README.md`
- `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`
- `docs/audit/CS2_AI_COACH_AUDIT_2026-07-02.md`
- `docs/SECURITY.md`

### What conflicts

Login/register and deployment scaffolding can imply friends/public readiness, while audit findings identify API auth, user ownership, CSRF/rate limits, strong secrets and operational gaps.

### Current truth

The app is personal/VPS only until Security P0 blockers are closed.

### Decision

Security gates are canonical in `docs/SECURITY.md` and `docs/PROJECT_CONTROL.md`.

### Required documentation update

Keep deployment docs but subordinate them to the security gate.

## Conflict: Metrics Reliability

### Files involved

- `README.md`
- `docs/METRICS_ROADMAP_SCORING_RU.md`
- `instructions/04_DATA_AND_METRICS_SPEC.md`
- `docs/DEMO_DEEP_PARSER_TZ_RU.md`
- `docs/METRICS.md`

### What conflicts

Some docs list desired or displayed metrics as if complete. Audit and parser docs show several metrics are best-effort or missing confidence rules.

### Current truth

Metrics are mixed-confidence. Weak metrics must be labeled and suppressed from diagnosis when unreliable.

### Decision

`docs/METRICS.md` owns the runtime metric contract. Older metric scoring/wishlist docs are advisory/historical.

### Required documentation update

Create `docs/METRICS.md` and mark old metric wishlist historical.

## Conflict: Recommendation Model

### Files involved

- `instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md`
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md`
- `docs/RECOMMENDATIONS.md`
- `docs/PROJECT_CONTROL.md`

### What conflicts

Older documents focus on category goals and lifecycle. Current product direction requires one primary recommendation derived from the top verified problem.

### Current truth

Lifecycle exists; planner and evidence linkage remain the main gap.

### Decision

Preserve lifecycle behavior, but make verified problem -> primary recommendation the canonical product loop.

### Required documentation update

Create `docs/RECOMMENDATIONS.md` and mark old TZ/plan as historical.

## Conflict: Steam Import Requirements

### Files involved

- `instructions/06_STEAM_AND_DEMO_IMPORT_NOTES.md`
- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/STEAM_MATCH_DATES_RU.md`
- `docs/STEAM_IMPORT.md`

### What conflicts

Older Steam notes are exploratory. Current implementation requires Steam OpenID, Game Authentication Code, latest share-code cursor, operator Web API key and service bot GC resolver. Known-code freshness and replay URL expiry are still risks.

### Current truth

Steam import is alpha, not production-ready.

### Decision

Use `docs/STEAM_IMPORT.md` as the canonical Steam control doc and keep deeper architecture/date docs as supporting material.

### Required documentation update

Create `docs/STEAM_IMPORT.md` and mark early Steam notes historical.

## Conflict: AI Coach Maturity

### Files involved

- `instructions/05_AI_COACH_PROMPT.md`
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md`
- `README.md`
- `docs/AI_COACH.md`

### What conflicts

Older docs describe prompt ideas or next steps that are partly completed. Current AI can persist reports but still emits unvalidated free-form output.

### Current truth

AI handoff and persistence exist; structured schema, validator and prompt/version tracking are missing.

### Decision

AI is a controlled explanation layer over deterministic facts, not an autonomous parser or source of truth.

### Required documentation update

Create `docs/AI_COACH.md` and mark old AI provider memo/prompt as historical.

