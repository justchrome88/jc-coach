# Agent Workflow

Last updated: 2026-07-06.

## 1. Purpose

This is the repo-native agent workflow v0.1 for JC Coach.

Agents here are not separate processes, daemons or services. They are roles and
working modes that Codex applies inside an approved WP lifecycle so scope,
verification and documentation currency stay explicit.

Canonical role cards live under `docs/agents/roles/`. This file remains the
workflow router; role cards define behavior for each invoked role.

## 2. Non-goals

- No autonomous daemon.
- No scheduler.
- No background monitoring.
- No automatic deletion or archiving.
- No separate runtime.
- No full-docs audit after every prompt.
- No expansion of per-task Hot context.

## 3. Roles

### PM / Orchestrator Agent

Role card: `docs/agents/roles/PM_ORCHESTRATOR.md`.

Responsibilities:

- Choose or propose the next WP.
- Check clean worktree before WP work starts.
- Define scope.
- Define affected zones.
- Decide which Warm docs are needed.
- Assign roles.
- Keep the task from becoming an unrelated refactor.
- Prepare close criteria.
- Do not close a WP without QA and Documentation Steward checks.

### Implementation Agent

Role card: `docs/agents/roles/IMPLEMENTATION_AGENT.md`.

Responsibilities:

- Make changes strictly inside scope.
- Do not change unrelated files.
- Do not change product logic outside the task.
- Do not change DB, import, parser or evaluator behavior without explicit
  authorization.
- Do not run `git add`, commit or push.
- Record changed files and checks.

### QA / Reviewer Agent

Role card: `docs/agents/roles/QA_REVIEWER.md`.

Responsibilities:

- Check the diff against scope.
- Check tests, checks and acceptance criteria.
- Identify regression risks.
- Check forbidden changes.
- Check that the report includes changed files, checks, risks and non-changes.
- Give `PASS`, `PASS_WITH_WARNINGS` or `FAIL`.

### Documentation Steward / Docs Currency Agent

Role card: `docs/agents/roles/DOCUMENTATION_STEWARD.md`.

Responsibilities:

- Check documentation currency.
- Decide which documents must be updated after a WP.
- Check whether required status documents were updated.
- Maintain a mental or documented map of project docs.
- Find duplicate instructions.
- Find stale entrypoints.
- Find documents that are not referenced anywhere.
- Classify documents as:
  - `CANONICAL`
  - `SUPPORTING`
  - `DRAFT`
  - `ARCHIVE_CANDIDATE`
  - `OBSOLETE`
- Propose merge, archive or deprecation actions, but do not delete
  automatically.
- Do not allow WP closure if required docs are not updated.

## 4. Optional Architect Role

Do not create a separate mandatory Architect Agent at this stage.

Architecture review is currently embedded in PM / Orchestrator and QA /
Reviewer. A separate Architect Agent can be added later if larger architecture
WPs need it.

## 5. Lifecycle

1. Feature, request or problem appears.
2. PM / Orchestrator checks if an existing WP covers it.
3. If a new WP is needed, User approval is required.
4. Worktree must be clean before WP starts.
5. PM defines scope, affected zones and needed Warm docs.
6. Implementation Agent executes.
7. QA / Reviewer checks diff, tests, acceptance and forbidden changes.
8. Documentation Steward checks required doc updates.
9. WP report is created.
10. ChatGPT PM / User review.
11. User commits and pushes.
12. WP can be closed only after required docs and report are in place.

## 6. Documentation Steward Triggers

Documentation Steward must run:

- After every WP-level task before closure.
- When a new document is created.
- When an existing canonical, Hot or Warm document is changed.
- Before promotion.
- When stale or conflicting instructions are detected.
- After 3-5 WPs as a small docs currency review.
- Before physical archiving or deprecation.
- When a new session starts from older docs and detects drift.

Documentation Steward should not run a full project docs audit after every tiny
task.

## 7. Role Handoff Protocol

Standard handoffs:

- PM / Orchestrator -> Implementation:
  scope, allowed files, forbidden zones, required checks and stop conditions.
- Implementation -> QA / Reviewer:
  changed files, summary, checks run, intentional non-changes and risks.
- QA / Reviewer -> Documentation Steward:
  whether docs/status/source-of-truth changed and required docs closure checks.
- Documentation Steward -> PM / Orchestrator / User:
  closure verdict, missing docs, stale docs and required user decisions.
- Any role -> User:
  blocker, approval request or unsafe action warning.

Rules:

- No role may run `git add`, commit or push.
- No role may expand scope without PM / Orchestrator and User approval.
- No role may use old prompts, audits or plans as current truth.
- Role cards are editable behavior contracts. Changes require explicit
  governance/documentation scope and docs navigation updates.
- New roles require explicit user approval and a role card.

## 8. Task Type Profiles

## 8. Invocation Modes

Invocation mode controls safety defaults. A prompt can make a mode stricter,
but cannot make it weaker than `AGENTS.md` or the active task type.

| Mode | Repo files edited | New report files | Code changes | DB/data read | DB/data mutate | Import/parser/evaluator jobs | Service/deploy config | Required output | Stop conditions |
|---|---|---|---|---|---|---|---|---|---|
| `planning-only` | no | only named file-backed report | no | no, unless explicitly read-only scoped | no | no | no | plan, scope, Warm docs, risks, next action | edit/mutation/job needed; output too long for console without file-backed mode |
| `review-only` | no | only named file-backed review report | no | read-only only if explicitly needed | no | no | no | findings, verdict, risks, missing checks | repair/edit needed; evidence insufficient |
| `diagnostic-only` | no, unless report allowed | only named diagnostic report | no repair edits | read-only only if scoped | no | no, unless explicitly diagnostic and safe | no | facts, hypotheses, blockers, next step | repair requested; mutation/live job needed; facts are ambiguous |
| `implementation` | yes, only allowed files | yes, if requested/WP-level | yes only if explicitly allowed | read-only if needed | only with explicit DB/data authorization | only with explicit authorization | only with explicit authorization | changed files, checks, non-changes, risks | scope expansion; forbidden zone touched; approval missing |
| `docs-currency` | docs only if allowed | yes, if requested/WP-level | no | no | no | no | no | classifications, stale/conflict findings, required updates | full audit needed but not requested; archive/delete/move needed |
| `WP-level` | as task allows | required WP report | only if task allows | read-only if needed | only with explicit authorization, backup and SHA | only with explicit authorization | only with explicit authorization | WP report, checks, status/docs updates, next WP | dirty worktree before start; required approval/evidence missing |
| `approval-required` | no until approved | planning/report only if allowed | no until approved | read-only only if safe and scoped | no until approved | no until approved | no until approved | approval request, risk, proposed command/change | user approval absent; risk cannot be bounded |

## 9. Output Modes

| Output mode | Use when | Behavior |
|---|---|---|
| `console-only` | Short answers that fit in one screen. | Do not create files. If output would be long, return a compact summary and recommend rerun with `file-backed` output. |
| `file-backed` | Output is important, long, reviewable or likely to exceed Codex CLI console limits. | Create exactly the requested report file. Console output includes only report path, verdict/result, short summary and `git status --short`. For `planning-only file-backed`, the only allowed file creation is the named report file. |
| `patch-producing` | Implementation or documentation edits are explicitly allowed. | Follow scoped edit discipline, role handoffs and standard WP report rules. |

Default: for any WP-level task, promotion task, architecture/PM planning task,
QA review, Documentation Steward audit or output expected to exceed about 80
lines, prefer `file-backed` output. Tiny tasks do not require output reports
unless explicitly requested.

## 10. Task Type Profiles

### Tiny Task

Example: typo, small docs wording or one-line config note.

- Required roles: Implementation only; QA light if needed.
- Documentation Steward: only if canonical docs, status docs or WP docs are
  affected.
- Report: no WP report unless requested.

### Scoped Implementation Task

- Required roles: PM / Orchestrator, Implementation, QA / Reviewer.
- Documentation Steward: only if docs, status or product behavior changed.
- Report: format depends on task size.

### WP-Level Implementation Task

- Required roles: PM / Orchestrator, Implementation, QA / Reviewer,
  Documentation Steward.
- Requires WP report.
- Requires registry, status and handoff checks.

### Promotion / Acceptance Task

- Required roles: PM / Orchestrator, QA / Reviewer, Documentation Steward.
- Implementation: only if documentation or status updates are required.
- Required Warm docs category: acceptance matrix, roadmap/version docs, current
  limitations and relevant recent reports.
- Must produce `PASS`, `PASS_WITH_WARNINGS`, `FAIL` or `DEFERRED`.

### Diagnostic / Investigation Task

- Required roles: PM / Orchestrator, QA / Reviewer.
- Implementation: only if repair is explicitly approved.
- Report must separate facts, hypotheses, blockers and recommended next step.

### Documentation / Governance Task

- Required roles: PM / Orchestrator, Documentation Steward, QA / Reviewer.
- Must not change product logic.
- Must avoid creating duplicate docs.

### Docs Currency Check

Primary role: Documentation Steward.

Modes:

- `targeted`
- `WP closure`
- `promotion readiness`
- `broad audit`

Classify docs only within the requested scope unless broad audit is explicitly
requested.

### DB / Data Task

- Requires explicit user approval before mutation.
- Requires backup/SHA policy.
- Requires DB/data guardian docs if relevant.
- No mutation by default.

### Import / Parser / Evaluator Task

- Requires explicit approval before live import, parser or evaluator jobs.
- Must respect Steam cap and current limitations.

### Deploy / Runtime Task

- Requires runtime/deploy Warm docs.
- Must distinguish repo config from live system config.
- No service/nginx changes without explicit authorization.

### UI / Web Task

- Requires relevant UI/web docs and route/template/static scope.
- QA must check user-facing regression risks.

### Recommendations / Coach Quality Task

- Requires recommendations, metrics and AI coach docs.
- Must distinguish evidence-backed claims from weak claims.

## 11. Role Invocation Shortcuts

| Phrase | Roles run | Expected output |
|---|---|---|
| `Use standard WP workflow.` | PM / Orchestrator, Implementation if changes are needed, QA / Reviewer, Documentation Steward | WP report, checks, changed files, required doc updates and next step. |
| `Task type: promotion / acceptance.` | PM / Orchestrator, QA / Reviewer, Documentation Steward; Implementation only for docs/status updates | `PASS`, `PASS_WITH_WARNINGS`, `FAIL` or `DEFERRED` with evidence and limitations. |
| `Task type: docs currency check.` | Documentation Steward, with PM / Orchestrator if scope must be clarified | Findings, classifications and minimal recommended actions inside scope. |
| `Invoke Documentation Steward.` | Documentation Steward | Scope checked, stale/conflicting docs, duplicate instructions, required updates and no automatic deletion. |
| `Run PM/Orchestrator planning only.` | PM / Orchestrator | Scope/options/risks/next-step proposal; no edits unless separately authorized. |
| `Run QA/Reviewer only.` | QA / Reviewer | Review findings, risks, missing checks and PASS/PASS_WITH_WARNINGS/FAIL if enough evidence exists. |
| `Tiny task, no full workflow unless needed.` | Implementation; QA light if needed; Documentation Steward only if canonical/status/WP docs are affected | Minimal change or answer, short summary, no WP report unless requested. |
| `Stop at diagnosis; do not repair.` | PM / Orchestrator, QA / Reviewer | Facts, hypotheses, blocker status and recommended next step; no repair edits. |

## 12. Standard Task Card Contract

Future prompts should use a short Task Card and rely on `AGENTS.md` plus this
workflow for generic rules. Generic restrictions should be inferred from mode,
task type and role cards instead of repeated in every prompt.

```text
Task:
Task type:
Mode:
Output mode:
Goal:
Scope, if needed:
Report path, if file-backed or WP-level:
Task-specific acceptance constraints, if needed:
Stop conditions, only if task-specific:
```

## 13. Standard WP Preflight

Run:

```bash
pwd
git status --short
git branch --show-current
git log --oneline -8 --decorate
```

If the worktree is dirty before a WP-level task, stop and report.

## 14. Standard Output Contract

For WP-level work, console output should include:

1. Report path.
2. Decision/result.
3. Changed files.
4. Short summary.
5. `git status --short`.
6. Confirmations:
   - no code changed, if docs-only;
   - no DB changed;
   - no imports/parser/evaluator ran;
   - no service/nginx changed;
   - no `git add`/commit/push.

The exact report path is task-specific and belongs in the Task Card.

## 15. Documentation Steward Standalone Mode

Example prompt:

```text
Invoke Documentation Steward.
Mode: targeted docs currency check.
Scope: governance docs.
Do not edit files.
Output: findings, classifications, recommended minimal actions.
```

Required output:

- Scope checked.
- Docs classified.
- Stale/conflicting docs.
- Duplicate instructions.
- Unreferenced docs if checked.
- Required updates.
- Recommended actions.
- Confirmation that no automatic deletion was performed.

## 16. Required Document Update Matrix

| Event | Required docs to check/update |
|---|---|
| New WP created | `WP_REGISTRY.md`, `MASTER_WP_CHECKLIST.md` if campaign plan changes, backlog/roadmap if product sequence changes |
| WP starts | `CURRENT_STATUS.md`, `WP_REGISTRY.md` |
| WP completes | `WP_REGISTRY.md`, `CURRENT_STATUS.md`, `HANDOFF.md`, WP report |
| Blocker found | `CURRENT_STATUS.md`, `WP_REGISTRY.md`, `HANDOFF.md` if next step changes, report |
| Durable decision made | `DECISIONS.md` |
| New canonical doc created | `DOCS_INDEX.md`, `DOCS_MAP.md`, maybe `PROJECT_OPERATING_PROTOCOL.md` |
| Hot context changed | `AGENTS.md` / `CURRENT_STATUS.md` / `WP_REGISTRY.md`, `DOCS_INDEX.md`, `HANDOFF.md` if bootstrap changes |
| Promotion attempted | `ACCEPTANCE_MATRIX.md`, `VERSION_ROADMAP.md`, `WP_REGISTRY.md`, `CURRENT_STATUS.md`, relevant reports |
| Document deprecated | `DOCS_INDEX.md`, `DOCS_MAP.md`, report, but no delete without approval |
| Side-chat decision accepted | `DECISIONS.md` or relevant canonical doc |

## 17. Docs Classification Model

- `CANONICAL` - source of truth for a specific area.
- `SUPPORTING` - useful reference but not source of truth.
- `DRAFT` - not authoritative yet.
- `ARCHIVE_CANDIDATE` - likely historical or stale, pending user decision.
- `OBSOLETE` - superseded and should not guide work.

Rules:

- `OBSOLETE` docs must not be used as current truth.
- `ARCHIVE_CANDIDATE` docs are not deleted automatically.
- Audit reports are evidence/history, not current truth.
- If docs conflict, the source-of-truth hierarchy in
  `PROJECT_OPERATING_PROTOCOL.md` wins.

## 18. WP Closure Checklist

A WP can close only if:

- Scope completed or explicitly deferred/failed.
- QA / Reviewer check completed.
- Documentation Steward check completed.
- Required docs updated.
- Report file created for WP-level work.
- Forbidden changes confirmed absent.
- Blockers/warnings recorded.
- Next step recorded.
- User/ChatGPT review completed before commit.

## 19. How To Use This Workflow In Prompts

### Normal WP Prompt

```text
Work according to AGENTS.md and AGENT_WORKFLOW.md.
Task: ...
Use Hot context. Read Warm docs only if needed.
Run PM/Implementation/QA/Docs Steward roles for this WP.
Do not git add/commit/push.
```

### Tiny Task Prompt

```text
Work according to AGENTS.md.
Task: ...
No full agent workflow required unless the task changes docs, WP status, DB,
deploy, or product behavior.
```
