# POST-FOUNDATION-AUDIT-01 Full Foundation Defect / Warning Inventory Audit

Date: 2026-07-08

Task type: Audit / Review / Discovery

Mode: review-only, file-backed

## Executive summary

Executor verdict: `PASS_WITH_WARNINGS`

The audit completed a post-foundation defect/warning inventory for the
Foundation Hardening lane from `FH-000` through `FH-128`, including
`FH-124R-01`, `FH-124R-02`, `FH-124R-02A`, `FH-124R-02B`, `FH-124R-03`,
`FH-125A-01`, H1, H2, PM routing repairs, warning-ledger changes, gate stalls,
stale context/source-of-truth drift, model-routing defects, accepted risks and
process defects.

Current canonical product state is consistent across main-repo Hot/current docs:
foundation hardening is closed only as
`FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`; the required next
lane is `POST_FOUNDATION_AUDIT_AND_STABILIZATION`; `READY_FOR_MAJOR_CS2_FEATURE_WORK`
remains `NO`; unrestricted `WP-018`, major CS2 feature work, public/friends
access, system `v1.0` and system `v1.0` packaging remain blocked.

Main warnings still needing carry-forward are not product-code regressions from
this task. They are readiness/process boundaries: no migration engine or
production migration capability, public/friends hard block, local-only
CI-equivalent gate, accepted no-schema prompt/payload snapshot workaround,
practical API/route validation limits, TestClient/httpx deprecation warning,
historic gate-stall/recovery pattern, stale PM tracker "Current Next Task" text
after H2, warning-ledger drift risk, and model-routing/support-label defects
that were repaired but remain important process history.

No repairs were performed.

## Method and evidence sources inspected

Required source-of-truth docs inspected first:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/HANDOFF.md`
- `docs/DECISIONS.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`
- `/opt/jc-coach-pm/outbox/2026-07-08_POST-FOUNDATION-AUDIT-01_task-card.md`

PM-side current lane evidence inspected:

- `/opt/jc-coach-pm/PM_STATE.md`
- `/opt/jc-coach-pm/ACTIVE_PLAN.md`
- `/opt/jc-coach-pm/checklists/PM_CHECKLIST.md`
- `/opt/jc-coach-pm/TASK_LOG.md`
- `/opt/jc-coach-pm/memory/PROJECT_MEMORY_COMPACT.md`
- `/opt/jc-coach-pm/memory/FOUNDATION_HARDENING_MEMORY.md`
- `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/READINESS_TRACKER.md`
- `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/WARNING_LEDGER.md`
- `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/FH_050_128_MACRO_BATCH_PLAN.md`
- `/opt/jc-coach-pm/docs/pm_memory/MODEL_ROUTING_POLICY.md`
- `/opt/jc-coach-pm/sync/2026-07-08_pm_source_recovery_audit.md`
- `/opt/jc-coach-pm/reviews/2026-07-07_model_routing_dry_run_phase3_report.md`
- H1/H2/recovery PM reviews under `/opt/jc-coach-pm/reviews/2026-07-08_FH-*.md`
- Compact task summaries under `/opt/jc-coach-pm/summaries/tasks/`

Main-repo foundation evidence inspected:

- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md`
- H1/H2/recovery task reports:
  - `FH-120_124_final-readiness-verification-gates-batch_report.md`
  - `FH-120_124R-02_h1-final-readiness-rerun_report.md`
  - `FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md`
  - `FH-124R-02B_repair-testclient-anyio-portal-startup-hang_report.md`
  - `FH-124R-03_h1-final-readiness-rerun-after-testclient-repair_report.md`
  - `FH-125A-01_reconcile-p0-p1-risk-register_report.md`
  - `FH-125_128_final-foundation-closure-post-foundation-audit-handoff_report.md`
- Task report file list under
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/`

Raw run logs were not read. The task card instructed to prefer current
source-of-truth docs, summaries, reviews, warning-ledger entries and task
reports, and to avoid old `run.log` reads unless a specific defect could not be
understood otherwise. No defect required raw log archaeology.

## Completeness estimate and skipped old/cold sources

Completeness estimate: `High / about 90%`.

Coverage is high for current actionable post-foundation defects and warnings
because this audit used canonical Hot docs, the PM lane tracker, warning ledger,
macro-batch plan, compact task memory, summaries, risk register, H1/H2 reports
and targeted PM reviews.

Skipped cold sources with reason:

- Old raw run logs: skipped by task-card preference; current summaries, reviews
  and reports were enough to understand the defects.
- Historical full audit row files under old audit directories: skipped except
  where current risk/register docs cited their resulting risk. The task was a
  post-foundation defect/warning inventory, not a re-run of the original
  106-row readiness audit.
- Old task cards for completed FH tasks: skipped except current task card and
  macro-batch plan evidence. Accepted task reports/reviews were stronger
  evidence than old prompts.
- Old `/tmp` audit artifacts cited by PM warning ledger: not opened directly;
  ledger/reviews summarized their current accepted disposition.

Residual uncertainty:

- Some early `FH-000` through `FH-004` work is PM-side setup rather than
  main-repo Executor work; coverage comes from the PM tracker/checklist rather
  than main-repo task reports.
- Warning ledger currently says it tracks `FH-000` through `FH-047`, but it has
  been appended through H2. That labeling drift is a process defect listed
  below.

## FH coverage inventory

| FH scope | Coverage source | Current accepted state | Carry-forward note |
|---|---|---|---|
| `FH-000`-`FH-004` | PM tracker/checklist | PM control layer done/accepted | PM-side setup only; no main-repo product unlock. |
| `FH-010`-`FH-015` | task reports, PM reviews, risk register | accepted, with early warnings carried into ledger | Historical docs remain history; roadmap pause state active. |
| `FH-020`-`FH-026` | task reports, summaries, workflow docs | accepted | Local gate/report policies exist; hosted CI not claimed. |
| `FH-030`-`FH-037` | task reports, risk register, summaries | accepted with several warning recoveries | No Alembic, no migration engine, no production DB mutation. |
| `FH-038_039` | task report, PM review | accepted as `PASS_WITH_MINOR_WARNINGS` | No final readiness or major CS2 unlock. |
| `FH-040`-`FH-047` | task reports, PM reviews, warning ledger | accepted with warnings | API/test coverage and context-manifest warnings remain. |
| `FH-050`-`FH-056` | macro-batch A report/review/ledger | accepted with warnings | Docs/design only; no worker/retry implementation or cap raise. |
| `FH-060`-`FH-069` | macro-batch B report/review | accepted | CS2 limits documented; no runtime enforcement or feature unlock. |
| `FH-070`-`FH-074` | macro-batch C1 report/review | accepted | Source trust/aggregation governance accepted. |
| `FH-075`-`FH-079` | macro-batch C2 report/review | accepted with warnings | Tests/fixtures/policy only; no runtime enforcement. |
| `FH-080`-`FH-088` | macro-batch D report/review | accepted | AI coach contract docs only; no runtime enforcement. |
| `FH-090`-`FH-095` | macro-batch E1 report/review | accepted with warnings | Semantic eval suite accepted; gate stall recovered by PM. |
| `FH-096`-`FH-097` | macro-batch E2 report/review | accepted with warnings | Eval/golden fixtures in gate; no final readiness claim by itself. |
| `FH-100`-`FH-107` | macro-batch F report/review | accepted with warnings | Planner design only; planner implementation blocked. |
| `FH-110`-`FH-117` | macro-batch G report/review | accepted with warnings | Public/security/deploy docs only; public/friends still blocked. |
| `FH-120`-`FH-124` | H1 report/review | accepted as failed gate audit | H1 failed initially due full-suite stall and unreconciled risks. |
| `FH-124R-01` | recovery report, compact memory | accepted recovery evidence | Proved test path, did not retroactively pass H1. |
| `FH-125A-01` | report/review | accepted with warnings | Reconciled P0/P1 for rerun readiness; no final readiness/pass by itself. |
| `FH-120_124R-02` | rerun report/review | accepted failed rerun | Full-suite timeout under 420s. |
| `FH-124R-02A` | diagnostic report/review | accepted with warnings | Isolated recurring timeout to TestClient/AnyIO startup. |
| `FH-124R-02B` | repair report/review | accepted with warnings | Full suite/local gate restored; TestClient deprecation warning remains. |
| `FH-124R-03` | rerun report/review | accepted with warnings | H1 final-readiness rerun passed; H2 still required separate authorization. |
| `FH-125`-`FH-128` | H2 report/review | accepted with warnings | Closed hardening into post-foundation audit lane only. |

## Foundation defect/warning registry

| defect_id | category | severity: P0/P1/P2/P3 | source/evidence path | affected task(s) | status: open / fixed / accepted limitation / needs PM repair / needs Executor repair / needs user decision | recommended follow-up task | blocks product restart: yes/no | blocks system v1.0: yes/no |
|---|---|---|---|---|---|---|---|---|
| `PF-AUDIT-001` | readiness/source-of-truth | P1 | `docs/CURRENT_STATUS.md`; `docs/project_management/WP_REGISTRY.md`; `docs/project_management/VERSION_ROADMAP.md`; `docs/foundation_hardening/.../task_reports/FH-125_128_final-foundation-closure-post-foundation-audit-handoff_report.md` | H2, `FH-125`-`FH-128` | open | `POST-FOUNDATION-VERIFY-01` after repairs to verify current-source alignment and restart conditions | yes | yes |
| `PF-AUDIT-002` | PM tracker drift | P2 | `/opt/jc-coach-pm/docs/foundation_hardening/.../READINESS_TRACKER.md` | post-H2 lane | needs PM repair | PM-side tracker reconciliation task to update Current Next Task from pre-H2 authorization blocker to `POST-FOUNDATION-AUDIT-01`/post-foundation lane | no | yes |
| `PF-AUDIT-003` | warning-ledger drift | P2 | `/opt/jc-coach-pm/docs/foundation_hardening/.../WARNING_LEDGER.md` | `FH-000`-H2 | needs PM repair | Warning ledger normalization task: update stated scope/counts after H2 and reconcile open/accepted/deferred statuses | no | yes |
| `PF-AUDIT-004` | warning-ledger carry-forward | P1 | `/opt/jc-coach-pm/docs/foundation_hardening/.../WARNING_LEDGER.md`; H2 report | H2, `WL-FH-000-036` | open | Post-foundation repair planning should consume closed-narrowly `WL-FH-000-036` and list remaining restart blockers explicitly | yes | yes |
| `WL-FH-000-003` | readiness/P2-P3 triage | P2 | `/opt/jc-coach-pm/docs/foundation_hardening/.../WARNING_LEDGER.md`; H1 report | `FH-010`, `FH-123` | accepted limitation | Optional structured P2/P3 risk-register import task before readiness re-score | no | yes |
| `WL-FH-000-005` | docs hygiene | P3 | `/opt/jc-coach-pm/docs/foundation_hardening/.../WARNING_LEDGER.md` | `FH-014`, H2 | accepted limitation | Legacy docs hygiene task only if stale historical prose causes routing/source-of-truth confusion | no | no |
| `WL-FH-000-006` | tests/dependency warning | P3 | `/opt/jc-coach-pm/docs/foundation_hardening/.../WARNING_LEDGER.md`; `FH-124R-02B`/`FH-124R-03` reports | `FH-020`, `FH-124R-02B`, `FH-124R-03` | open | Test dependency maintenance task for Starlette/httpx TestClient deprecation without package install unless scoped | no | yes |
| `WL-FH-000-008` | CI/gate boundary | P1 | `/opt/jc-coach-pm/docs/foundation_hardening/.../WARNING_LEDGER.md`; `docs/project_management/AGENT_WORKFLOW.md` | `FH-023`-`FH-025`, H1/H2 | accepted limitation | Hosted CI decision/configuration task, or explicit re-acceptance of local-only gate for personal MVP | yes | yes |
| `WL-FH-000-009` | DB/schema/migration | P0 | `docs/foundation_hardening/.../RISK_REGISTER.md`; warning ledger | `FH-030`-`FH-037`, `FH-125A-01`, H1/H2 | accepted limitation | Future migration-engine/schema-capability decision task before schema-changing product work | yes | yes |
| `WL-FH-000-010` | startup schema behavior | P2 | warning ledger; `FH-033` report | `FH-030`-`FH-033` | accepted limitation | None before product restart unless startup schema behavior is changed; then schema-changing WP required | no | yes |
| `WL-FH-000-013` | token/process telemetry | P3 | warning ledger; PM reviews | `FH-032` and agent cycles | accepted limitation | No-run-log token accounting policy task only if exact cycle token metrics become required | no | no |
| `WL-FH-000-017` | readiness gate | P1 | warning ledger; `FH-038_039` review; H2 docs | `FH-038_039`, H1/H2 | fixed | No direct repair; verify through post-foundation readiness re-score before restart | yes | yes |
| `WL-FH-000-018` | stale context manifest | P2 | warning ledger; `FH-040_041` review | `FH-040_041` | accepted limitation | Add manifest freshness check to PM_CREATE/Executor cycle if stale task IDs recur | no | yes |
| `WL-FH-000-019` | API validation depth | P1 | warning ledger; `FH-045_046` report/review | `FH-045`-`FH-046` | open | Focused API/service validation matrix and route/auth edge tests task | yes | yes |
| `WL-FH-000-020` | stale context manifest | P2 | warning ledger; `FH-045_046` review | `FH-045_046` | accepted limitation | Same as `WL-FH-000-018`; consolidate in manifest freshness repair | no | yes |
| `WL-FH-000-023` | test coverage limitation | P1 | warning ledger; `FH-044_047` review/recovery | `FH-044`, `FH-047` | open | Safe live ASGI/TestClient or equivalent route-contract coverage task after TestClient repair evidence | yes | yes |
| `WL-FH-000-024` | historical failed cycle | P3 | warning ledger; recovery report | `FH-044_047` | accepted limitation | None; keep historical failure as evidence only | no | no |
| `WL-FH-000-027` | PM artifact prose drift | P3 | warning ledger; recovery artifacts | `FH-044_047` recovery | accepted limitation | PM artifact hygiene pass if historical pending markers confuse routing | no | no |
| `WL-FH-000-033` | semantic eval/gate boundary | P2 | warning ledger; E1/E2 reviews | `FH-090`-`FH-097` | fixed | Verify eval/golden fixtures in readiness re-score; no repair unless gate output regresses | no | yes |
| `WL-FH-000-034` | planner implementation boundary | P1 | warning ledger; `FH-100_107` review | `FH-100`-`FH-107` | accepted limitation | Planner implementation entry-criteria verification before any future planner code task | yes | yes |
| `WL-FH-000-035` | public/security/deploy boundary | P0 | warning ledger; `FH-110_117` review; `CURRENT_STATUS.md` | `FH-110`-`FH-117` | accepted limitation | Public/friends readiness task only after personal MVP gates; keep blocked now | yes | yes |
| `WL-FH-000-036` | final readiness handoff | P1 | warning ledger; `FH-124R-03` report/review; H2 report/review | H1, H2 | fixed | Post-foundation audit/stabilization tasks before any restart; no direct H2 rerun needed | yes | yes |
| `WL-FH-000-037` | model-routing unsupported model | P1 | warning ledger; `/opt/jc-coach-pm/config/model_policy.json`; `MODEL_ROUTING_POLICY.md` | pre-`FH-050` agent cycle | fixed | Keep supported-model allow-list/fallback tests and inspect future routing JSON | no | yes |
| `WL-FH-000-038` | local quality gate stall/recovery | P2 | warning ledger; `FH-050_056` review | `FH-050`-`FH-056` | fixed | No repair unless pattern recurs; keep gate heartbeat/timeout evidence | no | yes |
| `WL-FH-000-039` | local quality gate stall/recovery | P2 | warning ledger; `FH-075_079` review | `FH-075`-`FH-079` | fixed | No repair unless pattern recurs; include in gate-stall process history | no | yes |
| `WL-FH-000-040` | local quality gate observability | P2 | warning ledger; `scripts/local_quality_gate.py` history | `FH-090`-`FH-095` | fixed | Verify heartbeat/fail-closed timeout behavior during readiness re-score | no | yes |
| `WL-FH-000-041` | local quality gate stall/recovery | P2 | warning ledger; `FH-096_097` review | `FH-096`-`FH-097` | fixed | No repair unless pattern recurs; include in gate-stall process history | no | yes |
| `R-FH-P0-001` | DB/schema/migration | P0 | `docs/foundation_hardening/.../RISK_REGISTER.md`; `FH-125A-01` review | `FH-030`-`FH-037`, `FH-125A-01` | accepted limitation | Migration-engine/schema-capability decision task before schema-changing product work | yes | yes |
| `R-FH-P0-002` | public/friends access | P0 | `RISK_REGISTER.md`; `CURRENT_STATUS.md`; `FH-110_117` review | `FH-110`-`FH-117` | accepted limitation | Public-readiness gate task remains future; no friends/public work now | yes | yes |
| `R-FH-P0-003` | planner design/runtime gap | P1 | `RISK_REGISTER.md`; `FH-100_107` review | `FH-100`-`FH-107` | accepted limitation | Planner implementation task only after entry criteria and eval readiness | yes | yes |
| `R-FH-P1-003` | local-only CI | P1 | `RISK_REGISTER.md`; `FH-023`/`FH-024`; H1/H2 reports | `FH-023`, `FH-024`, `FH-096`, `FH-097`, H1 | accepted limitation | Hosted CI or explicit local-only acceptance decision before system v1.0 packaging | no | yes |
| `R-FH-P1-005` | API/route coverage | P1 | `RISK_REGISTER.md`; `FH-042_043`, `FH-044_047`, `FH-045_046` reviews | `FH-042`-`FH-047` | accepted limitation | Focused route/auth/service validation tests task | yes | yes |
| `R-FH-P1-006` | owner/auth edge state | P1 | `RISK_REGISTER.md`; `FH-110_117` review | `FH-110`-`FH-117` | accepted limitation | Security/runtime owner-edge tests before friends/public, optional before product restart | no | yes |
| `R-FH-P1-016` | prompt/payload runtime persistence | P1 | `RISK_REGISTER.md`; `FH-080_088` review; `FH-125A-01` review | `FH-085`, `FH-086` | accepted limitation | No-schema workaround verification; runtime persistence only under future schema scope | no | yes |
| `R-FH-P1-027` | metric/prompt snapshot persistence | P1 | `RISK_REGISTER.md`; `FH-080_088` review; `FH-125A-01` review | `FH-086` | accepted limitation | Same as `R-FH-P1-016` | no | yes |
| `R-FH-P1-029` | hosted CI absent | P1 | `RISK_REGISTER.md`; `AGENT_WORKFLOW.md`; H1/H2 reviews | `FH-023`, `FH-024`, `FH-096`, `FH-097`, H1 | accepted limitation | Hosted CI/provider decision before system v1.0 packaging or explicit accepted local-only rationale | no | yes |
| `PF-AUDIT-005` | model-routing classification | P2 | warning ledger `WL-FH-000-025`, `WL-FH-000-026`; `MODEL_ROUTING_POLICY.md` | `FH-040`-`FH-047`, pre-`FH-050` | fixed | Add a post-foundation model-routing verification check using current manifest and direct actual-model evidence | no | yes |
| `PF-AUDIT-006` | repeated wrong task selection | P1 | `/opt/jc-coach-pm/TASK_LOG.md`; PM checklist; compact memory | `FH-124R-02A`, `FH-124R-02B` | fixed | Add stale outbox/manifest conflict detection to PM_CREATE before starting next task | no | yes |
| `PF-AUDIT-007` | BLOCKED-but-accepted-after-rerun pattern | P2 | summaries for `FH-031`, `FH-034`, `FH-035`, `FH-036`, `FH-050_056`, `FH-075_079`, `FH-090_095`, `FH-096_097` | DB/schema, macro-batches A/C2/E1/E2 | accepted limitation | Gate-process review to decide when PM rerun can accept Executor `BLOCKED`/`FAIL` and how to record ownership | no | yes |
| `PF-AUDIT-008` | package/dependency maintenance | P2 | `FH-124R-02B` and `FH-124R-03` reports | `FH-124R-02B`, `FH-124R-03` | open | TestClient/httpx dependency maintenance task, with package install explicitly scoped or explicitly forbidden | no | yes |
| `PF-AUDIT-009` | system v1.0 packaging premature risk | P0 | `CURRENT_STATUS.md`; `WP_REGISTRY.md`; `VERSION_ROADMAP.md`; H2 review | H2, post-foundation lane | open | Do not create `SYSTEM-V1-PACKAGING-01` until audit, repairs, verify and readiness re-score pass and user authorizes | yes | yes |

## Carry-forward list for PASS_WITH_WARNINGS and PASS_WITH_MINOR_WARNINGS

| Source task/result | Carry-forward item | Status |
|---|---|---|
| `FH-010` `PASS_WITH_WARNINGS` | Dirty state after accepted output before commit; risk register not yet linked; P2/P3 not imported. | Dirty/link items fixed; P2/P3 structured import accepted/deferred. |
| `FH-021` `PASS_WITH_WARNINGS` | Full-suite stall risk surfaced by local gate wrapper. | Repaired later by `FH-124R-02B`; deprecation warning remains. |
| `FH-023` `PASS_WITH_WARNINGS` | Local CI-equivalent accepted; hosted CI not configured. | Accepted limitation. |
| `FH-025` `PASS_WITH_WARNINGS` | Gate-output evidence requirement added; hosted CI/full-suite stall not solved by this task. | Accepted limitation/fixed later for stall. |
| `FH-030` `PASS_WITH_WARNINGS` | Schema baseline/gate added; no Alembic, migration support or production mutation. | Accepted limitation. |
| `FH-031` `PASS_WITH_WARNINGS` | Original local gate stalled/BLOCKED; PM manual rerun passed. | Fixed as task result; process history remains. |
| `FH-032` `PASS_WITH_WARNINGS` | DB SHA policy added; no final readiness, hosted CI or migration support claimed. | Accepted limitation. |
| `FH-034` `PASS_WITH_WARNINGS` | Executor aggregate gate stalled; PM rerun passed; no production DB/startup behavior/migration claims. | Fixed as task result; process history remains. |
| `FH-035` `PASS_WITH_WARNINGS` | Gate stalled before PM rerun; test-only startup SQL guard; no runtime behavior change. | Fixed as task result; boundary remains. |
| `FH-036` `PASS_WITH_WARNINGS` | Executor reported `FAIL` from gate stall; PM rerun passed; temp DB-only guard. | Fixed as task result; process history remains. |
| `FH-038_039` `PASS_WITH_MINOR_WARNINGS` | Closure reconciliation did not run final readiness gate or claim 95% readiness. | Fixed by later H1/H2, but product restart still blocked. |
| `FH-040_041` `PASS_WITH_WARNINGS` | Stale manifest task id named `FH-037`. | Accepted process warning; manifest freshness follow-up recommended. |
| `FH-045_046` `PASS_WITH_WARNINGS` | `FH-046` validation inventory practical, not deep service-level matrix. | Open API/test follow-up. |
| `FH-044_047` `PASS_WITH_WARNINGS` | Original tests/gate timed out before recovery; critical endpoint tests avoid live ASGI/TestClient dispatch. | Gate fixed; route-test limitation open. |
| `FH-050_056` `PASS_WITH_WARNINGS` | Original local quality gate stalled/interrupted; PM rerun passed. | Fixed as task result; process history remains. |
| `FH-075_079` `PASS_WITH_WARNINGS` | Executor gate stalled/BLOCKED; PM rerun passed; accepted tests/fixtures/policy only. | Fixed as task result; runtime enforcement not claimed. |
| `FH-090_095` `PASS_WITH_WARNINGS` | Executor gate stalled/BLOCKED; PM rerun passed; E2 still needed for gate integration/readiness fixtures. | E2 accepted; process history remains. |
| `FH-096_097` `PASS_WITH_WARNINGS` | Executor gate stalled; PM rerun passed; no final readiness, runtime enforcement, planner implementation or feature unlock. | Fixed as task result; boundaries remain. |
| `FH-100_107` `PASS_WITH_WARNINGS` | Planner design accepted; planner implementation remains blocked. | Open future implementation boundary. |
| `FH-110_117` `PASS_WITH_WARNINGS` | Public/security/deploy docs accepted; public/friends readiness remains blocked. | Accepted limitation. |
| `FH-120_124` `FAIL` accepted with PM `PASS_WITH_WARNINGS` review | H1 failed: full-suite stall, unreconciled P0/P1, migration boundary. | Superseded by `FH-125A-01`, `FH-124R-02B`, `FH-124R-03`; process history remains. |
| `FH-125A-01` `PASS_WITH_WARNINGS` | P0/P1 reconciled for rerun; no final readiness, no migration engine, schema work blocked. | Accepted limitation. |
| `FH-120_124R-02` failed rerun accepted with warnings | Full-suite timed out under 420s. | Superseded by diagnostic/repair/rerun. |
| `FH-124R-02A` `PASS_WITH_WARNINGS` | Timeout diagnosis high for stuck area, medium for root cause; H1/H2/WP-018 blocked. | Superseded by repair; history retained. |
| `FH-124R-02B` `PASS_WITH_WARNINGS` | Repair passed full suite/local gate; TestClient deprecation warning remains; no H1 rerun by this task. | H1 rerun later passed; deprecation warning open. |
| `FH-124R-03` `PASS_WITH_WARNINGS` | H1 commands passed; H2/status/WP-018 unlock still separately blocked; deprecation warning remains. | H2 accepted; product restart still blocked. |
| `FH-125_128` `PASS_WITH_WARNINGS` | H2 closed hardening only to post-foundation audit; PM warning-ledger disposition PM-owned; H1 warning carried forward. | Current lane; audit/repair/verify/re-score required. |

## PM/process defects

- Stale context manifest task IDs appeared in multiple accepted tasks
  (`FH-040_041`, `FH-045_046`) and did not block because explicit task cards
  controlled scope. This should be repaired as a manifest freshness check if it
  recurs.
- Repeated `FH-124R-02A` routing occurred before `FH-124R-02B` because stale
  manifest/outbox state made selection ambiguous. PM repaired routing
  afterward; post-foundation process should add stale active-outbox conflict
  detection.
- PM tracker drift remains: `READINESS_TRACKER.md` still shows the pre-H2
  `USER_DECISION_H2_AUTHORIZATION` blocker in its Current Next Task section,
  while main Hot docs, PM checklist, compact memory and task card all route to
  `POST-FOUNDATION-AUDIT-01`.
- Warning ledger labeling/counts drifted: the title says it tracks
  `FH-000` through `FH-047`, but entries extend through H2. Counts also need
  PM-owned reconciliation after post-foundation audit.
- Several tasks were accepted after PM reran required gates that stalled or
  timed out during Executor. This is defensible when PM review records recovery
  evidence, but it should have a clearer ownership rule before system v1.0.
- PM-side superseded source-recovery audit retains old "safe to start" wording
  but has a supersession header. Do not use it as current routing truth.

## Test/gate defects

- Historic H1 full-suite pytest stall occurred in `FH-120_124` and recurred in
  `FH-120_124R-02`; later diagnosed as TestClient/AnyIO portal startup and
  repaired in `FH-124R-02B`.
- Current H1 rerun evidence from `FH-124R-03` passed: full-suite pytest
  `250 passed, 1 warning` and `LOCAL_QUALITY_GATE=PASS`.
- The remaining test warning is the upstream Starlette/httpx TestClient
  deprecation warning. It is accepted as non-blocking for H1/H2 but should be
  tracked before system v1.0 packaging.
- Hosted CI is not configured and is not claimed. The project uses the accepted
  local CI-equivalent gate for the restricted/personal lane.
- Route/API test coverage remains practical rather than exhaustive; deeper
  service-level validation and live ASGI/TestClient-style route coverage remain
  follow-up candidates.
- Gate-runner heartbeat/fail-closed timeout observability was added after the
  repeated stall pattern. Re-score should verify it still works.

## Model-routing defects

- Early model routing was dry-run only and did not pass a real `--model` flag.
- A later model-routing start selected unsupported `codex-spark` for current
  ChatGPT-account Codex CLI, causing a failed start before Batch A execution.
  The policy now says only `gpt-5.5` is supported for CLI use and unsupported
  labels must fail closed to `gpt-5.5`.
- Docs/design/governance tasks were previously over-classified as `db_schema`
  or `unknown`, routing them unnecessarily to strong models. A narrow balanced
  docs/design/governance path was added, but strong routing remains required for
  DB/schema, production DB, security, deploy/service, import/parser/evaluator,
  tests/fixtures/gates, final readiness, failed/stalled gate recovery and
  high-risk review.
- Future `model_routing_*.json` files must include direct actual model evidence
  such as `actual_model_label_passed`, switching mode and fallback reason.

## Follow-up repair recommendations grouped by risk and area

P0 / blocking:

- `POST-FOUNDATION-REPAIR-P0-DB-MIGRATION-BOUNDARY`: Decide whether no-engine
  migration remains accepted for product restart and system v1.0, or create a
  separately scoped migration-engine/schema-capability task. Scope: docs/schema
  planning; user decision likely required.
- `POST-FOUNDATION-REPAIR-P0-PUBLIC-ACCESS-BLOCK`: Verify public/friends access
  remains blocked across status/security/deploy docs and no task implies public
  readiness. Scope: docs/security review.
- `POST-FOUNDATION-REPAIR-P0-SYSTEM-V1-GATE`: Add an explicit system v1.0
  packaging precondition checklist so packaging cannot start before audit,
  repairs, verification, readiness re-score and user authorization.

P1 / product restart:

- `POST-FOUNDATION-REPAIR-P1-API-VALIDATION`: Build or scope deeper
  route/service/auth/owner validation coverage, including the practical limits
  from `WL-FH-000-019` and `WL-FH-000-023`.
- `POST-FOUNDATION-REPAIR-P1-PLANNER-ENTRY`: Verify planner implementation
  entry criteria, weak-metric exclusions and semantic eval readiness before any
  future planner implementation task.
- `POST-FOUNDATION-REPAIR-P1-CI-DECISION`: Decide whether local CI-equivalent
  remains sufficient through personal MVP, or scope hosted CI/provider work.
- `POST-FOUNDATION-REPAIR-P1-SNAPSHOT-WORKAROUND`: Verify no-schema prompt,
  payload and metric-registry snapshot workaround remains acceptable before
  restart.

P2 / process and gate:

- `POST-FOUNDATION-REPAIR-P2-PM-TRACKER-LEDGER`: PM-side repair for
  `READINESS_TRACKER.md` current-next drift and `WARNING_LEDGER.md` scope/count
  drift.
- `POST-FOUNDATION-REPAIR-P2-MANIFEST-ROUTING`: Add manifest/outbox/task-id
  freshness checks before PM_CREATE/Executor starts a cycle.
- `POST-FOUNDATION-REPAIR-P2-GATE-PROCESS`: Document when PM review reruns can
  accept an Executor `BLOCKED`/`FAIL` caused by a gate stall, and how that is
  reflected in task verdicts.
- `POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY`: Verify current routing JSON
  includes direct actual-model evidence and unsupported-model fallback metadata.

P3 / hygiene:

- `POST-FOUNDATION-REPAIR-P3-LEGACY-PROSE`: Clean or annotate historical prose
  only where it creates routing/source-of-truth confusion.
- `POST-FOUNDATION-REPAIR-P3-TOKEN-TELEMETRY`: Decide whether unknown token
  counts in no-run-log mode are acceptable, or add a compact token-evidence
  policy.

## Explicit block statements

- Product restart remains blocked: `YES`.
- `WP-018` remains blocked/paused: `YES`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK`: `NO`.
- Major CS2 feature work remains blocked: `YES`.
- Public/friends access remains blocked: `YES`.
- System `v1.0` remains unclaimed: `YES`.
- System `v1.0` packaging remains blocked: `YES`.
- A later `SYSTEM-V1-PACKAGING-01` task must not be prepared until
  post-foundation audit, repair sequence, verification, readiness re-score and
  separate user authorization all happen.

## Required checks and evidence

| Check | Result | Evidence |
|---|---|---|
| `git status --short` before work | `PASS` | No output; main repo clean before audit work. |
| `.venv/bin/python scripts/project_gate.py preflight` | `PASS` | Reported branch `agentdev`, clean `git status --short -uall`, required governance files present, production DB SHA observed read-only as `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `.venv/bin/python scripts/project_gate.py changed` before report | `PASS` | Output showed `## changed/untracked files` then `(none)`; activated guardian `PM_ORCHESTRATOR`. |
| `.venv/bin/python scripts/project_gate.py required-checks` | `PASS` | Required preflight, changed, required-checks, postflight, `git diff --check`, unauthorized git add/commit/push confirmation and final status evidence. |
| `.venv/bin/python scripts/project_gate.py postflight` | `PASS` | Reported only the expected untracked report file, activated `DOCUMENTATION_STEWARD` and `PM_ORCHESTRATOR`, no code/test/script change, governance files present, production DB SHA observed read-only as `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `git diff --check` | `PASS` | Exit `0`; no output. |

Checks intentionally not run:

- Full pytest, Ruff and `scripts/local_quality_gate.py`: not required for this
  review-only/docs report task. The task card required project-gate commands
  and `git diff --check`, not a code/test local quality gate.
- Live runtime/service smoke checks: forbidden/unneeded for audit-only scope.
- External docs lookup: not relevant; this task audited internal project
  source-of-truth and PM evidence, not dependency API behavior.

## Files changed

- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-AUDIT-01_full-foundation-defect-warning-inventory-audit_report.md`

No other file was intentionally changed.

## Safety declarations

- No repairs were performed.
- No source-of-truth docs were rewritten.
- No PM repo files were edited.
- No product/code/test/script/runtime/config/package files were changed.
- No DB/schema/data mutation occurred.
- No production DB copy occurred.
- No production DB mutation occurred.
- Production DB SHA was observed only through read-only project-gate evidence:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- No live Steam/Valve import ran.
- No demo download, decompression, parser job, evaluator job or manual
  evaluator job ran.
- No public/friends access work started.
- No service, nginx, systemd, deploy or live runtime configuration changed.
- No package installation occurred.
- No migration engine was implemented.
- No persistent app reports were generated.
- No secrets were printed.
- No `git add`, commit or push ran.

## Blockers

No blocker prevented completion of this audit report.

Product restart and system v1.0 remain blocked by the post-foundation lane:
audit review, repair sequence, verification and readiness re-score still need
to happen before any separate user-authorized restart/packaging decision.

## Next WP

Recommended next lane action after PM review of this audit:

```text
POST-FOUNDATION-REPAIR-SEQUENCE
```

Repair tasks should be separate and grouped by risk/area. Do not create one
broad fix-everything task.

## discovery_result

```yaml
discovery_result:
  completeness_estimate: "High / about 90%; current defects and warnings covered from Hot docs, PM tracker, warning ledger, compact memory, summaries, risk register, H1/H2 reports and targeted reviews; old raw logs intentionally skipped."
  missing_items_found: true
  followup_required: true
  followup_tasks_recommended:
    - proposed_id: "POST-FOUNDATION-REPAIR-P0-DB-MIGRATION-BOUNDARY"
      title: "Decide migration-engine boundary before restart"
      reason: "No Alembic/equivalent production migration engine or production migration capability is claimed; schema-changing product work remains blocked."
      risk: "P0"
      suggested_scope: "docs-only"
      needs_user_decision: true
    - proposed_id: "POST-FOUNDATION-REPAIR-P1-API-VALIDATION"
      title: "Deepen route and service validation coverage"
      reason: "Current API/route coverage is practical and accepted with limitations; deeper service-level validation and live route coverage remain open."
      risk: "P1"
      suggested_scope: "tests"
      needs_user_decision: false
    - proposed_id: "POST-FOUNDATION-REPAIR-P1-CI-DECISION"
      title: "Decide hosted CI versus local-only gate"
      reason: "Local CI-equivalent is accepted for the restricted lane, but hosted CI is not configured or claimed and may block system v1.0 packaging confidence."
      risk: "P1"
      suggested_scope: "config"
      needs_user_decision: true
    - proposed_id: "POST-FOUNDATION-REPAIR-P2-PM-TRACKER-LEDGER"
      title: "Reconcile PM tracker and warning ledger drift"
      reason: "READINESS_TRACKER Current Next Task still shows pre-H2 authorization blocker and WARNING_LEDGER scope/count metadata drifted after H2."
      risk: "P2"
      suggested_scope: "docs-only"
      needs_user_decision: false
    - proposed_id: "POST-FOUNDATION-REPAIR-P2-MANIFEST-ROUTING"
      title: "Add stale manifest and outbox conflict checks"
      reason: "Stale context manifest/task-id state and repeated FH-124R-02A routing created wrong-task risk."
      risk: "P2"
      suggested_scope: "config"
      needs_user_decision: false
    - proposed_id: "POST-FOUNDATION-VERIFY-01"
      title: "Verify repairs and source-of-truth consistency"
      reason: "After repairs, verify current status, registry, roadmap, PM tracker, warning ledger and model-routing evidence before readiness re-score."
      risk: "P1"
      suggested_scope: "docs-only"
      needs_user_decision: false
    - proposed_id: "POST-FOUNDATION-READINESS-SCORE-01"
      title: "Re-score foundation readiness"
      reason: "The original readiness score was about 66%; post-repair verification should rerun broad readiness scoring before any restart decision."
      risk: "P1"
      suggested_scope: "unknown"
      needs_user_decision: false
```
