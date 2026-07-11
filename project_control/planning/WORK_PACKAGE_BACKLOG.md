# Current Work-Package Backlog

Last updated: 2026-07-11.

This file owns detailed planned work. Exact status and gating are authoritative
in `WP_REGISTRY.md`.

## H01B-R02A3 — completed with warnings

- **Purpose:** consolidate codebase and service boundaries before UI work.
- **Dependencies:** R02A2D accepted; no remaining documentation gate.
- **Scope:** bounded package ownership, import/call boundary cleanup, behavior
  preservation, focused tests, package-level code-map refresh.
- **Explicit non-goals:** no service restart; no DB/schema/data change; no
  Product-domain, mission, provider, queue, or UI redesign.
- **Acceptance summary:** stable behavior and public imports, clearer service
  ownership, no new root-level service sprawl, full technical gate PASS.
- **Evidence/result:** `/opt/jc-coach-pm/reports/H01B-R02A3_codebase_service_boundary_consolidation_report.md`.

## H01B-R02A4 — current inserted acceptance gate

- **Purpose:** prove the post-refactor owner-scoped Steam-to-coach pipeline as
  one complete observable Product chain before UI implementation.
- **Dependencies:** accepted R02A3 architecture checkpoint.
- **Scope:** isolated clone, one genuine Steam acquisition, real parser and
  current metrics, real configured-model calls for both canonical domains,
  clone-only dual activation and subsequent-match evaluation, stable raw card
  payloads, structured stage trace, repeat/concurrency/failure evidence, and
  production no-mutation proof.
- **Explicit non-goals:** no permanent feature, UI, new domain or metric,
  provider architecture, queue, import-cap, schema, production activation, or
  30+10 replay change.
- **Acceptance summary:** every required vertical stage is real where mandated,
  owner-isolated, lineage-stable, observable, idempotent, and leaves production
  DB, artifacts, missions, and service untouched.
- **Evidence/result:** add the R02A4 report, JSON artifact, and JSONL stage trace.

## H01B-R03 — pending

- **Purpose:** deliver the minimal, complete two-mission functional MVP UI.
- **Dependencies:** accepted R02A4 inserted acceptance gate.
- **Scope:** two domain cards; analyzing/proposal/no-problem/insufficient/error
  states; pinning; explicit activation of one, both, or neither; per-domain
  mission lifecycle; baseline/current/target/confidence/caveats; per-match
  feedback and progress history; auth and owner isolation.
- **Explicit non-goals:** no automatic activation, third domain, broad visual
  redesign, public/multi-user readiness, or provider/queue hardening unless a
  blocking defect requires it.
- **Acceptance summary:** an owner with 30 eligible validated matches can review
  one proposal per supported domain and independently activate/use both mission
  flows with subsequent-match-only progress.
- **Evidence/result:** add the accepted R03 PM report when complete.

## H01B-R04 — pending

- **Purpose:** accept the complete two-domain Product loop through a 30+10 replay.
- **Dependencies:** accepted R03.
- **Scope:** immutable 30-match baseline; two proposals; explicit activation of
  both; 10 subsequent matches one by one; independent progress; insufficient
  data; idempotent reprocessing; DB/API/dashboard/match-page parity.
- **Explicit non-goals:** no visual polish, live Steam import, public rollout,
  or new domain/evidence expansion.
- **Acceptance summary:** replay is deterministic, owner-isolated, caveated,
  idempotent, and behaviorally consistent at every persistence and UI boundary.
- **Evidence/result:** add the accepted R04 PM report when complete.

## H01B-R05 — planned, not authorized

- **Purpose:** validate usefulness on real newly played personal matches.
- **Dependencies:** accepted R04 and separate live-action authorization.
- **Scope:** hypothesis usefulness, false positives/unsupported claims, latency,
  provider reliability, target quality, and a prioritized Product-change list.
- **Explicit non-goals:** no public beta, visual redesign, automatic activation,
  or broad operational platform build.
- **Acceptance summary:** evidence-backed personal-beta findings identify whether
  the Product loop and targets are useful enough to polish.
- **Evidence/result:** none until authorized and executed.

## H01B-R06 — planned, not authorized

- **Purpose:** bring accepted functionality to coherent presentation quality.
- **Dependencies:** accepted R04 and findings from R05.
- **Scope:** responsive layout, hierarchy, loading/empty/error presentation,
  mission history, readable evidence/caveats, accessibility, consistency.
- **Explicit non-goals:** no backend Product expansion, third domain, public
  deployment, or operational platform rewrite.
- **Acceptance summary:** the validated flow is clear, accessible, responsive,
  and visually consistent without changing accepted semantics.
- **Evidence/result:** none until authorized and executed.

## H01B-R07 — deferred/planned

- **Purpose:** harden provider, queue, observability, reliability, and cost after
  Product validation.
- **Dependencies:** R05 evidence, unless an earlier milestone proves a blocker.
- **Scope:** bounded operational hardening driven by measured failure/cost data.
- **Explicit non-goals:** not a default prerequisite for personal MVP; no public
  readiness claim or coach-domain expansion.
- **Acceptance summary:** explicit SLO, failure recovery, observability, and cost
  controls pass the task-specific gate.
- **Evidence/result:** none until authorized and executed.

## Historical/completed work

Foundation/readiness hardening, the owner import/parser loop, metric correctness,
Coach Metric Pack, two-domain backend, real LLM proposals, and R02A2–R02A2D
documentation consolidation are completed milestones. WP-018 and older
foundation queues are historical or superseded; they are not active next work.
Their detailed evidence remains in PM reports, Git history, and
`_legacy_archive/`.
