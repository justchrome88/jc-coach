# Project Operating Protocol

Last updated: 2026-07-05.

## 1. Purpose

This document explains how JC Coach is managed so User, ChatGPT PM and Codex do
not lose context between sessions or work packages.

## 2. Roles

- User: approval authority, commit authority and product owner.
- ChatGPT PM chat: planning, review and decision-support layer.
- Codex CLI: executor, auditor and repository file updater.
- Repository docs: source of truth for accepted project state.
- Git: immutable technical history after user-approved commits.

`docs/project_management/AGENT_WORKFLOW.md` defines the repo-native role
workflow Codex uses inside WP-level work. These agents are process roles, not a
runtime agent platform.

## 3. Source Of Truth Hierarchy

1. `AGENTS.md` - Codex operating contract.
2. `docs/CURRENT_STATUS.md` - current product, runtime and blocker snapshot.
3. `docs/project_management/WP_REGISTRY.md` - WP IDs, statuses,
   dependencies and report paths.
4. `docs/HANDOFF.md` - new-session bootstrap.
5. `docs/DECISIONS.md` - durable decisions.
6. Domain docs, roadmap, backlog and acceptance matrix - Warm docs.
7. Audit reports, old prompts and old plans - evidence/history only.
8. Chat messages - not source of truth until written to repository docs.

## 4. Hot / Warm / Cold Rules

Per-task Hot context is only:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context additionally includes `docs/HANDOFF.md`.

Warm docs are read only when the task requires that domain. Before reading Warm
docs, Codex states which files are needed and why.

Cold context is old reports, prompts, stage docs, archived or generated
evidence. Cold context can support an investigation but must not override Hot
or Warm source-of-truth docs.

## 5. WP Lifecycle

- `planned`: approved for future work but not active.
- `active`: current approved work package being executed.
- `done`: completed with required report/evidence.
- `blocked`: cannot continue safely without a decision, external state or a
  diagnostic/repair WP.
- `deferred`: intentionally postponed without being accepted as complete.
- `failed`: attempted and did not meet acceptance criteria.
- `superseded`: replaced by another WP or decision.
- `out-of-band evidence`: evidence that supports governance or diagnosis but
  does not consume a planned WP ID.

The registry remains the canonical place for exact WP status wording. If an
older file uses `in_progress`, treat it as equivalent to `active` until that
file is reconciled.

## 6. When To Update Which Document

| Document | Update when |
|---|---|
| `docs/CURRENT_STATUS.md` | Current WP, blockers, promotion status, runtime assumptions or accepted limitations change. |
| `docs/project_management/WP_REGISTRY.md` | A WP is created, activated, completed, blocked, deferred or superseded, or dependency/report path changes. |
| `docs/HANDOFF.md` | At session handoff, after WP completion, before a long pause, or when the next safe step changes. |
| `docs/DECISIONS.md` | A durable process, product or architecture decision is made. |
| `docs/project_management/MASTER_WP_CHECKLIST.md` | The high-level campaign plan changes or a WP is added, renamed or reordered. |
| `docs/project_management/DOCS_INDEX.md` / `docs/project_management/DOCS_MAP.md` | Document roles or context levels change. |
| `docs/project_management/AGENT_WORKFLOW.md` | WP role workflow, Documentation Steward triggers or closure gate rules change. |
| `docs/audit/WP_*.md` | A WP-level task report is required. |
| Domain docs | The truth for that domain changes. |

## 7. How New WP Items Are Created

1. A new WP can be proposed by User, ChatGPT PM or Codex.
2. The proposal states why an existing WP or backlog item cannot cover it.
3. User approves before registry/checklist changes become official.
4. Add the item to `docs/project_management/WP_REGISTRY.md`.
5. Add or update `docs/project_management/MASTER_WP_CHECKLIST.md`.
6. Add or update roadmap/backlog only if product sequence changes.
7. Do not silently renumber existing WPs.
8. Do not consume reserved WP IDs.
9. Mark out-of-band audits as out-of-band evidence.

## 8. Blocker / Stuck Procedure

When blocked, stop work and do not invent product behavior. Record the blocker
in the WP report, update `CURRENT_STATUS.md` if the blocker affects current
state, update `WP_REGISTRY.md` if the WP becomes blocked/deferred, and update
`HANDOFF.md` if the next safe step changes. Ask User or ChatGPT PM for the
needed decision. If diagnosis is required, create a diagnostic WP instead of
folding unsafe work into the current WP.

## 9. Report Policy

Long reports must be saved under `docs/audit/`. Console output should stay
short. Every WP-level report must include changed files, checks, non-changes,
risks and the next step. Ordinary tiny tasks may use a short console summary
when no WP-level report is requested.

## 10. Commit Policy

Codex never commits unless explicitly instructed. User reviews the report and
diff. ChatGPT PM may review the report and recommend a commit. User performs
`git add`, commit and push.

## 11. Audit / Compaction Cadence

- Per task: read Hot context and show `git status --short`.
- Per WP: create a report and update registry/status/handoff as needed.
- Per WP: run the Documentation Steward check from
  `docs/project_management/AGENT_WORKFLOW.md` before closure. This owns docs
  currency checks and required doc updates, but does not require a full docs
  audit for every tiny task.
- Every 3-5 WPs, or when Hot docs grow too large: compact
  `CURRENT_STATUS.md` and `HANDOFF.md`.
- Before promotion: run promotion readiness audit.
- When repeated bugs or drift occur: run targeted audit.
- Full audit only at a major boundary or after serious drift.

## 12. Chat Policy

The master ChatGPT PM chat can be used for governance, review and prompt
creation. Side chats are allowed for brainstorming. Side-chat decisions are not
official until summarized into repository docs. This keeps project truth out of
chat history and inside versioned files.
