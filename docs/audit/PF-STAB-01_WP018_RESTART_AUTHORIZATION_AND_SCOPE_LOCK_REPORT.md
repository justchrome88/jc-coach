# PF-STAB-01 WP-018 Restart Authorization And Scope Lock Report

Task ID: `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK`

Date: 2026-07-09

## Result

`PASS_WITH_WARNINGS`

The post-foundation stabilization gate is formally closed for the narrow
purpose of restarting `WP-018 Coach Quality Calibration` in an AI coach
quality, calibration and output-quality scope only.

This report does not implement WP-018, change product code, mutate data, run
imports/parser/evaluator jobs, restart services, change dependencies, claim
`v1.0`, unlock public/friends readiness or authorize broad CS2 product
expansion.

## Branch / HEAD

- Branch: `cona`
- HEAD: `2aa583054aa2a0cbf4154d2ebe848d7c3a97d9b0`
- Initial `git status --short`: clean, no output.

## Changed Files

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/audit/PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK_REPORT.md`

## Authorization Recorded

- `POST-FOUNDATION-01_DEFECT_WARNING_AUDIT_AND_STABILIZATION_PLAN` produced
  `PASS_WITH_WARNINGS`.
- Hot docs now record that WP-018 may restart only in a narrow AI coach
  quality/calibration/output-quality scope.
- Hot docs continue to block unrestricted WP-018 expansion and major CS2
  feature work.

## Scope Allowed For WP-018

Allowed only when explicitly scoped by a future WP-018 task:

- AI coach quality baseline and gap mapping.
- Coach output calibration.
- Caveat, claim and weak-metric review.
- Documentation or tests that improve coach output quality and preserve
  accepted warnings.
- No-schema/no-runtime-risk design or audit work for prompt/payload quality,
  versioning or snapshots.

## Still-Forbidden Work

- Implementing WP-018 in this task.
- Broad CS2 feature expansion or unrestricted WP-018 work.
- AI coach code changes, runtime prompt changes, recommendation logic changes
  or metric logic changes unless a later task explicitly scopes them.
- Production DB, schema, data, upload, raw demo, backup, parser/import,
  evaluator/manual evaluator, service, deploy/runtime or package/dependency
  changes.
- Live Steam/Valve import, parser jobs, evaluator jobs, manual evaluator jobs,
  service restarts, deploy commands or package installs.
- `v1.0` claims, public/friends readiness claims, Steam import cap raise,
  removal of playlist/mode caveats or removal of weak-metric caveats.
- New hard evaluations for legacy recommendations `#1`, `#3` or `#4` unless a
  future accepted task refreshes them.

## Can-Carry Warnings

- Upstream `TestClient` deprecation warning remains non-blocking.
- Hosted CI/branch protection is not configured; local gate remains the current
  accepted discipline.
- No schema/migration engine; schema-changing work remains blocked unless a
  separate authorized DB/migration task scopes it.
- Prompt/payload snapshots and runtime metric-registry snapshots are not
  implemented.
- Provider-specific structured response enforcement and semantic entailment
  checks remain future hardening.
- Playlist/mode remains unknown or provenance-only unless reliable persisted
  metadata exists.
- Weak metrics remain caveated and recommendation evaluations must preserve
  `metric_confidence`.
- Steam import cap remains `1`; durable worker/retry/cap raise work stays
  outside WP-018.
- Public/friends readiness remains blocked.
- `v0.9` remains promoted with warnings; `v1.0` is not claimed.

## Checks

Preflight:

- `git status --short`: exit `0`, no output.
- `git branch --show-current`: exit `0`, `cona`.
- `git rev-parse HEAD`: exit `0`,
  `2aa583054aa2a0cbf4154d2ebe848d7c3a97d9b0`.

Final:

- `git diff --check`: pass, no output.
- `git status --short`: docs-only changes listed.

## Recommended Next Task

`WP-018-01_AI_COACH_QUALITY_BASELINE_AND_GAP_MAP`

Purpose: perform the first real WP-018 audit/design task by establishing the AI
coach quality baseline, known output-quality gaps, accepted caveats and a
narrow follow-on calibration plan. It should not implement broad product
features or change DB/import/parser/evaluator/runtime/deploy/package behavior.
