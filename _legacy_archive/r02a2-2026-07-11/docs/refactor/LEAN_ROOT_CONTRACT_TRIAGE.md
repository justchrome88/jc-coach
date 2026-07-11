# LEAN-DOCS-00 Root Contract Triage

Task ID: `LEAN-DOCS-00_ROOT_CONTRACT_TRIAGE`
Date: 2026-07-08
Mode: `planning-only / root-contract-triage / file-backed`

## 1. Branch And HEAD

Product repo `/opt/jc-coach`:

- Branch: `cona`
- HEAD: `9f4e39258f638ddb65f5f2210f20d51c4dc844e1`
- Preflight `git status --short`: clean

PM repo `/opt/jc-coach-pm`:

- Branch: `cona`
- HEAD: `036bdd2de1ac1adc963ebd34a4ec5b636847e26b`
- Preflight `git status --short`: clean

## 2. Current `AGENTS.md` Assessment

Useful:

- It establishes the root operating contract and source-of-truth precedence.
- It keeps strong safety boundaries for DB, raw demos, imports, parser,
  evaluator, service/deploy, commits and pushes.
- It prevents old audit reports and generated reports from overriding current
  Hot docs.
- It has a useful context-reading policy: do not read all documentation by
  default.
- It preserves core product constraints: `v0.9`, recommendation `#5`,
  weak-metric caveats, playlist-mode limitations and Steam import cap `1`.

Stale or overweight:

- It still carries too much Foundation Hardening and WP-report machinery inside
  the root contract.
- Sections on schema-changing policy, DB SHA evidence, discovery reporting,
  report templates, task classes and local quality gates are too detailed for a
  root file that every future Codex task must load.
- The current roadmap section is too broad for a lean root contract and should
  be reduced to a pointer plus current product guardrails.
- It preserves process history as operating rules, which increases active
  context and makes ordinary product tasks inherit Foundation-era bureaucracy.

Creates bureaucracy:

- Mandatory WP report rules for every WP, discovery-result YAML, large report
  evidence requirements and decomposition policy are better as workflow
  references, not root-contract text.
- Detailed DB/schema/import/reporting policies belong in stable Foundation
  contracts that are read only when the task touches those domains.
- The root contract currently mixes universal safety rules with implementation
  workflow, PM decomposition, report templates and historical recovery notes.

## 3. Conflicts And Drift Found

Product Hot docs vs PM Hot docs:

- `CURRENT_STATUS.md`, `HANDOFF.md` and `WP_REGISTRY.md` say the current lane
  is `POST_FOUNDATION_AUDIT_AND_STABILIZATION` and that Foundation Hardening is
  closed pending post-foundation audit/stabilization.
- `PM_STATE.md` and `ACTIVE_PLAN.md` say the Foundation plus post-foundation
  repair sequence is already closed as
  `POST_FOUNDATION_REPAIR_SEQUENCE_CLOSED_ACCEPTED_WITH_WARNINGS`, readiness is
  `82% / 4.10 of 5`, and the next lane is
  `CODEX_NATIVE_SIMPLIFICATION_AND_SYSTEM_REFACTOR`.
- Product Hot docs still carry the older readiness state around `66% / 3.30 of
  5`; PM docs carry the later `82% / 4.10 of 5` score.

Main repo HEAD vs PM memory:

- This triage preflight saw product HEAD
  `9f4e39258f638ddb65f5f2210f20d51c4dc844e1`.
- `PM_STATE.md` records several later or different main commits, including
  `364000110da1b36998c0303bbed69f4e3b866d01`,
  `db08a0f12273ecb207968f399511cd04ed1b49af` and individual post-foundation
  task commits.
- This is a source-of-truth drift risk. Before applying root-contract cleanup,
  Task 1 should explicitly reconcile whether `/opt/jc-coach` at this HEAD is
  expected to contain the PM-recorded post-foundation closure state.

Product workflow vs current user direction:

- `AGENTS.md`, `AGENT_WORKFLOW.md`, `CURRENT_STATUS.md`, `HANDOFF.md` and
  `WP_REGISTRY.md` still preserve a Foundation/WP-heavy operating model.
- The current user direction is to keep JC Coach as the product, not build JC
  Forge now, and reduce active context quickly so future Codex tasks can return
  to product work.

`AGENT_WORKFLOW.md` internal drift:

- It states the known full-suite pytest stall remains open, while later PM
  memory says TestClient/AnyIO repair and H1 rerun passed with warnings.
- This may be stale workflow text or a branch/HEAD mismatch; do not rewrite it
  blindly in Task 1 without confirming the accepted product-repo state.

PM-side plan drift:

- `PM_STATE.md` and `ACTIVE_PLAN.md` both contain long historical hardening
  sequences. They agree on the newer PM lane, but both are too large for Hot PM
  context and repeat many task-level details.
- PM-side cleanup is outside Task 1 unless explicitly included later.

## 4. What Should Stay In Lean `AGENTS.md`

Keep only universal root rules that every task needs:

- Project identity: JC Coach, controlled personal CS2 coach product.
- Source-of-truth order:
  1. explicit current user task;
  2. root `AGENTS.md`;
  3. `docs/CURRENT_STATUS.md`;
  4. `docs/HANDOFF.md`;
  5. `docs/project_management/WP_REGISTRY.md`;
  6. task-relevant Foundation/core/adapters docs.
- Minimal context policy: read Hot docs only; read domain docs only when needed.
- Absolute prohibitions: no DB/schema/data/import/parser/evaluator/service/
  deploy/package/raw-demo mutation unless explicitly scoped.
- Git policy: show status, no `git add`, no commit or push unless explicitly
  authorized; never commit DB/backups/uploads/demos.
- Product guardrails: `v0.9` with warnings, WP-018 paused unless separately
  authorized, playlist mode not exact, weak metrics caveated, import cap `1`,
  recommendation `#5` is the current accepted active hard recommendation.
- Report/output principle: keep console short; write long outputs to the
  named report path when requested.
- Stop rule: stop as `BLOCKED` on unexplained dirty worktree, missing
  authorization, source-of-truth conflict or unsafe side effect.

## 5. What Should Be Removed Or Moved From `AGENTS.md`

Remove from root and move to focused references:

- Detailed task-class and discovery-result YAML contract.
- PM decomposition and follow-up task ownership rules.
- Detailed DB SHA evidence matrix.
- Detailed schema-changing WP policy.
- Startup schema compatibility history for FH-030/FH-031/FH-032.
- Import safety declaration template details.
- Full WP report template details and required evidence sections.
- Mandatory local quality gate narrative and known historical pytest-stall
  details.
- Detailed roadmap list beyond current product status and next blocked lane.
- Foundation recovery history embedded as operating policy.

Do not delete this material in Task 1 unless the task explicitly scopes the
destination files and acceptance checks.

## 6. Move To `foundation/core/*`

Proposed destination for product-agnostic safety and contract rules:

- `foundation/core/context_policy.md`: Hot/Warm/Cold reading rules and
  source-of-truth precedence details.
- `foundation/core/git_policy.md`: status, commit, push and forbidden artifact
  rules.
- `foundation/core/data_safety.md`: DB/data/raw-demo/import/parser/evaluator
  safety boundaries.
- `foundation/core/reporting_contract.md`: file-backed output, report evidence
  expectations and PASS/PASS_WITH_WARNINGS/BLOCKED semantics.
- `foundation/core/task_lifecycle.md`: task classes, discovery reporting and
  decomposition rules.
- `foundation/core/product_guardrails.md`: current JC Coach limitations that
  are not implementation code: playlist unknown, weak metrics, import cap,
  public/friends blocked, WP-018 paused.

These files should be loaded only when relevant, not as mandatory Hot context
for every task.

## 7. Move To `foundation/adapters/codex/*`

Proposed destination for Codex-specific workflow mechanics:

- `foundation/adapters/codex/root_runtime.md`: how Codex interprets root
  contract rules.
- `foundation/adapters/codex/task_cards.md`: Task Card fields, output modes
  and report-path conventions.
- `foundation/adapters/codex/role_workflow.md`: PM/Executor/QA/Docs Steward
  role routing, if still needed.
- `foundation/adapters/codex/checks.md`: project gate/local quality gate usage,
  evidence capture and skip reporting.
- `foundation/adapters/codex/control_plane_protection.md`: control-plane
  protection rules and governance-doc edit boundaries.

These are adapter docs because they describe Codex operating behavior, not
the JC Coach product itself.

## 8. Move To Archive / History

Archive or mark historical after a separate explicit cleanup task:

- Foundation recovery sequence narrative once its final accepted state is
  reflected in `CURRENT_STATUS.md`, `HANDOFF.md` and `WP_REGISTRY.md`.
- Old WP-017 governance buildup details that no longer guide active product
  work.
- Historical report-template evolution and old gate-stall notes once the
  current check contract is preserved in Foundation/core or Codex adapter docs.
- Superseded references to the unresolved full-suite stall if the accepted
  product repo state confirms it was repaired and rerun.
- Any JC Forge planning or runner-system packaging material that is not needed
  for JC Coach product tasks now.

No archive, delete or move should happen in this triage task.

## 9. Proposed Lean `AGENTS.md` Outline

```text
# AGENTS.md - JC Coach Root Contract

## 1. Project Identity
- JC Coach is the primary product.
- This repo is the canonical product repo.
- Current task prompt can be stricter than this file.

## 2. Source Of Truth And Context
- Source-of-truth order.
- Hot docs to read.
- Read domain docs only when relevant.
- Old reports are evidence/history only.

## 3. Universal Safety Rules
- DB/data/raw demos/import/parser/evaluator/service/deploy/package prohibitions.
- Explicit authorization requirements.

## 4. Git Rules
- Status before work.
- No add/commit/push unless authorized.
- Never commit protected artifacts.

## 5. Current Product Guardrails
- v0.9 with warnings.
- WP-018 paused unless separately authorized.
- Recommendation #5 active.
- Playlist mode unknown/provenance-only.
- Weak metrics caveated.
- Import cap 1.
- Public/friends access blocked.

## 6. Task Execution Defaults
- Keep scope small.
- Do not broaden task.
- Use file-backed reports when requested.
- Stop as BLOCKED on dirty worktree, conflict or missing authorization.

## 7. Reference Map
- foundation/core/* for safety, reporting, lifecycle and product guardrails.
- foundation/adapters/codex/* for Codex-specific workflow.
- docs/CURRENT_STATUS.md, docs/HANDOFF.md and WP_REGISTRY remain Hot status.
```

Target size: roughly 120-180 lines, not a full workflow manual.

## 10. Proposed Next Task

Task ID: `LEAN-DOCS-01_APPLY_LEAN_ROOT_CONTRACT`

Task type: docs/governance implementation

Mode: `planning-approved / docs-only / root-contract-apply`

Output mode: `file-backed`

Goal:

- Replace the current root `AGENTS.md` with a lean root contract.
- Preserve all safety-critical rules by moving detailed mechanics into
  focused Foundation/core or Codex-adapter docs, or by leaving clear pointers
  to existing canonical docs.
- Do not perform broad cleanup, archiving or deletion.

Allowed files should be narrow:

- `/opt/jc-coach/AGENTS.md`
- the minimum explicitly named `docs/foundation/core/*` files needed
- the minimum explicitly named `docs/foundation/adapters/codex/*` files needed
- report path for Task 1

Required preflight:

- Re-run branch, HEAD and `git status --short` in both repos.
- Stop if product HEAD/state does not match the intended source-of-truth state
  for applying lean docs.

Acceptance constraints:

- No runtime code, tests, DB/schema/data, import/parser/evaluator, service or
  deploy changes.
- Root `AGENTS.md` remains sufficient for ordinary product tasks without
  forcing Foundation-history into active context.
- No safety rule is weakened.
- Product status drift between product Hot docs and PM Hot docs is either
  resolved by explicit allowed-file updates or reported as a blocker.

Recommended report path:

```text
/opt/jc-coach/docs/refactor/LEAN-DOCS-01_APPLY_LEAN_ROOT_CONTRACT_REPORT.md
```

## 11. Risks

- Safety regression: over-compressing root rules could accidentally weaken DB,
  import, raw-demo, service/deploy or git protections.
- Source-of-truth drift: PM state appears newer than product Hot docs and the
  current product HEAD. Applying lean docs before reconciling state could encode
  the wrong lane.
- Context fragmentation: moving rules into too many files could recreate the
  same bureaucracy under new paths.
- Hidden dependency risk: future Executor prompts may rely on current
  `AGENTS.md` details; Task 1 should preserve pointers for moved details.
- Product delay risk: over-scoping cleanup into archive/history would delay the
  intended return to JC Coach product work.

## 12. Stop Conditions

Task 1 should stop before edits if:

- `/opt/jc-coach` or `/opt/jc-coach-pm` has unexplained dirty or untracked
  files.
- The user has not decided whether PM's newer post-foundation state should be
  reflected in product Hot docs before root-contract rewrite.
- Applying the lean contract would require broad archive/delete/move cleanup.
- Any proposed change touches runtime code, tests, DB/schema/data, raw demos,
  imports, parser/evaluator, service/deploy, package config or generated app
  reports.
- Any safety rule cannot be preserved in root or an explicitly named
  Foundation/core or Codex-adapter destination.
- The task starts turning into a broad documentation audit instead of a minimal
  root-contract compression.

