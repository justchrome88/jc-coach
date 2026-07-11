# FH-070-FH-074 Metrics Source Trust Policy Batch Report

Date: 2026-07-08

Task: Macro-batch C1: FH-070-FH-074 metrics/source trust policy

## Result

Batch verdict: `PASS`

Per-FH verdicts:

| FH ID | Verdict | Evidence |
|---|---|---|
| `FH-070` | `PASS` | `docs/METRICS.md` now defines the source trust registry requirements for current and future metric sources. |
| `FH-071` | `PASS` | `docs/METRICS.md` defines current trust levels for CSV, JSON, demo parser, Steam / Valve share-code import and FACEIT. FACEIT is explicitly `unavailable_source`. |
| `FH-072` | `PASS` | `docs/METRICS.md` defines sample-size thresholds per metric category and behavior for insufficient samples. |
| `FH-073` | `PASS` | `docs/METRICS.md` documents aggregation rules for counts, rates, ratios, mixed sources, missing values, low-confidence values and suppressed metrics. |
| `FH-074` | `PASS` | `docs/METRICS.md` documents period comparison semantics, comparison windows, freshness/date-source caveats and suppression/caveat conditions. |

The batch verdict is no better than the weakest included FH verdict.

## Summary

Implemented the accepted docs/design/governance policy for mixed metric sources
without code, tests, runtime behavior, DB/schema changes, import/parser/evaluator
jobs, service/deploy changes, package installation, git staging, commit or push.

The policy lives primarily in `docs/METRICS.md` and is cross-referenced from
`docs/CS2_DOMAIN_CONTRACT.md`, `docs/AI_COACH.md`, `docs/API_CONTRACTS.md` and
`docs/ARCHITECTURE.md` so coach, API and architecture surfaces inherit the same
source-trust and aggregation boundaries.

## Scope And Acceptance Evidence

- Carried in `WL-FH-000-030`: source trust and aggregation semantics were
  incomplete before this batch and are now addressed at docs/design level.
- Preserved `WL-FH-000-031` for C2: confidence labels, fixtures and regression
  policy remain future scope and were referenced only as dependencies.
- Preserved Macro-batch B boundaries: no exact playlist/mode, reliable economy,
  positioning, clutch, map, side or hard trade semantics were claimed.
- Kept weak or source-limited metrics caveated and blocked unsupported hard
  advice from mixed, weak, unavailable or low-sample sources.
- Did not claim final readiness, unrestricted CS2 feature work, WP-018 restart,
  runtime enforcement, parser hardening, AI eval completion, planner work,
  public/friends readiness or deploy/security readiness.

## Files Changed

- `docs/METRICS.md`
- `docs/CS2_DOMAIN_CONTRACT.md`
- `docs/AI_COACH.md`
- `docs/API_CONTRACTS.md`
- `docs/ARCHITECTURE.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-070_074_metrics-source-trust-policy-batch_report.md`

## Checks Evidence

Required by Task Card and workflow:

| Check | Result | Evidence excerpt |
|---|---|---|
| `git status --short` before work | `PASS` | Initial command returned no output; worktree was clean before edits. |
| `.venv/bin/python scripts/project_gate.py preflight` | `PASS` | Reported branch `agentdev`; governance files present; scoped changed files after edits: `docs/AI_COACH.md`, `docs/API_CONTRACTS.md`, `docs/ARCHITECTURE.md`, `docs/CS2_DOMAIN_CONTRACT.md`, `docs/METRICS.md`. |
| `.venv/bin/python scripts/project_gate.py changed` | `PASS` | Reported changed docs and activated `DOCUMENTATION_STEWARD`, `METRICS_GUARDIAN`, `PM_ORCHESTRATOR`, `UI_COACH_GUARDIAN`. |
| `.venv/bin/python scripts/project_gate.py required-checks` | `PASS` | Required project gate commands, docs checklist, source/claim review and no unauthorized git actions; recommended tests were listed only where applicable. |
| `git diff --check` | `PASS` | No output. |
| `.venv/bin/python scripts/project_gate.py postflight` | `PASS` | Reported `code/test/script change: no`; activated guardians unchanged; governance files present; changed docs plus untracked report path listed; production DB SHA unchanged from preflight. |
| Scope review against allowed files and forbidden actions | `PASS` | All changed files are in the Task Card allowed product-repo edit candidates. No forbidden commands/actions were performed. |

Checks not run:

- `scripts/local_quality_gate.py`: not required because this was docs-only and
  no code, scripts or tests changed.
- `pytest` / Ruff: not required by the Task Card for docs-only work and not
  applicable without code, script or test changes.
- Recommended metric/AI/coach pytest commands from `required-checks`: not run
  because no runtime code, metric registry code, AI validator code,
  recommendation code, routes, templates or tests changed.
- Runtime smoke / live service checks: not authorized or required for this
  docs/design/governance-only task.

## Safety Declarations

- Production DB: no mutation. `project_gate.py preflight` performed a read-only
  SHA evidence check and reported
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db`.
- Schema/migration/startup schema behavior: not touched.
- Live Steam/Valve calls: none.
- Demo download/decompression/parser jobs: none.
- Evaluator/manual evaluator jobs: none.
- Worker, queue runner, retry path or stale-job repair: none.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN`: unchanged.
- Production import data, Steam cursors, raw demos, backups and uploads: not
  touched.
- Persistent app report generation: none. This file is the authorized Executor
  task report, not an app-generated report.
- Service/nginx/systemd/deploy config: not touched.
- Package installation: none.
- `git add`, commit and push: not run.

## Standard Report Docs Update Checklist

| Item | Status | Reason |
|---|---|---|
| Hot/current status docs | `checked; no update required` | Task allowed canonical metrics/domain/API/architecture docs and report only; no current project status changed. |
| WP registry/status/handoff docs | `checked; no update required` | No WP registry, handoff or active status state changed; control-plane docs were not in allowed edit candidates. |
| Navigation docs | `checked; no update required` | No new canonical/navigation-relevant doc was created; existing docs held the policy cleanly. |
| Task-relevant domain docs | `checked and updated` | Updated metrics source trust policy and cross-referenced it from domain, AI coach, API contracts and architecture docs. |
| Documentation Steward | `checked and updated` | Documentation Steward was required by workflow/guardian activation; scoped closure checklist completed here. |
| Deferred docs follow-up | `checked; no update required` | No new follow-up created by this task. C2 confidence labels, fixtures and regression policy remain the existing next macro-batch scope. |

## Blockers

None.

## Next WP

Proceed to Macro-batch C2 (`FH-075`-`FH-079`) for confidence labels, formula /
reliability sync, golden aggregate fixtures and sanitized parser payload
fixtures. Do not treat this C1 docs/design policy as runtime enforcement until a
future scoped implementation/test task accepts that work.
