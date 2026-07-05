# Agent Workflow

Last updated: 2026-07-05.

## 1. Purpose

This is the repo-native agent workflow v0.1 for JC Coach.

Agents here are not separate processes, daemons or services. They are roles and
working modes that Codex applies inside an approved WP lifecycle so scope,
verification and documentation currency stay explicit.

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

Responsibilities:

- Make changes strictly inside scope.
- Do not change unrelated files.
- Do not change product logic outside the task.
- Do not change DB, import, parser or evaluator behavior without explicit
  authorization.
- Do not run `git add`, commit or push.
- Record changed files and checks.

### QA / Reviewer Agent

Responsibilities:

- Check the diff against scope.
- Check tests, checks and acceptance criteria.
- Identify regression risks.
- Check forbidden changes.
- Check that the report includes changed files, checks, risks and non-changes.
- Give `PASS`, `PASS_WITH_WARNINGS` or `FAIL`.

### Documentation Steward / Docs Currency Agent

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

## 7. Required Document Update Matrix

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

## 8. Docs Classification Model

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

## 9. WP Closure Checklist

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

## 10. How To Use This Workflow In Prompts

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
