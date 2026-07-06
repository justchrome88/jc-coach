# P2/P3 Triage

Date: 2026-07-06.

Source: audit `01_AUDIT_MATRIX.csv` and `01_AUDIT_MATRIX.md`.

## A. Fix During Foundation-Hardening

| Audit ID | Source audit file | Finding | Decision | Rationale | Impact | Revisit condition |
|---|---|---|---|---|---|---|
| AR-005 | `01_AUDIT_MATRIX.csv` | Task lifecycle documented but manual. | Fix during hardening. | Supports gate enforcement. | Reduces skipped closure steps. | Revisit after report template/gate update. |
| AR-007 | `01_AUDIT_MATRIX.csv` | Permission matrix not tool-enforced. | Fix during hardening. | Prevents unsafe DB/import/runtime tasks. | Better execution safety. | Revisit after prompt lint/checklist exists. |
| AR-010 | `01_AUDIT_MATRIX.csv` | DoD strong but manual. | Fix during hardening. | Needed for binary readiness gate. | More reliable PASS/FAIL. | Revisit after report checklist template. |
| AR-014 | `01_AUDIT_MATRIX.csv` | Docs update policy can drift. | Fix during hardening. | Foundation docs must remain source of truth. | Reduces stale docs. | Revisit after docs checklist in reports. |
| AR-021 | `01_AUDIT_MATRIX.csv` | Route-level validation inventory missing. | Fix during hardening if touching API contracts. | Complements AR-018. | Safer mutation endpoints. | Revisit during API contract task. |
| AR-023 | `01_AUDIT_MATRIX.csv` | Logging policy thin. | Fix during hardening. | Supports ops/security gate. | Better incident diagnosis. | Revisit after observability runbook. |
| AR-024 | `01_AUDIT_MATRIX.csv` | Deploy verification checklist missing. | Fix during hardening as docs-only. | Needed before later VPS hardening. | Safer deploy comparisons. | Revisit in WP-020. |
| AR-040 | `01_AUDIT_MATRIX.csv` | Provider structured-response enforcement missing. | Fix during hardening if AI version/eval code is touched. | Strengthens AI output safety. | Less hallucination risk. | Revisit after semantic evals. |
| AR-042 | `01_AUDIT_MATRIX.csv` | Coach archetype vs CS2 domain separation unclear. | Fix during hardening. | Needed to avoid domain overreach. | Cleaner planner design. | Revisit after AI coach archetype/domain pack docs. |
| AR-049 | `01_AUDIT_MATRIX.csv` | Economy model absent. | Fix during hardening as explicit unavailable status. | Blocks unsupported economy advice. | Reduces overclaims. | Revisit when parser supports economy. |
| AR-051 | `01_AUDIT_MATRIX.csv` | Positioning model absent. | Fix during hardening as explicit unavailable status. | Blocks unsupported positioning advice. | Reduces overclaims. | Revisit when parser payload supports positions. |
| AR-052 | `01_AUDIT_MATRIX.csv` | Clutch semantics incomplete. | Fix during hardening as definition or unavailable status. | Blocks ambiguous clutch claims. | Safer coach wording. | Revisit when metric definition accepted. |
| AR-053 | `01_AUDIT_MATRIX.csv` | Entry sample-size thresholds missing. | Fix during hardening with sample policy. | Same policy as AR-055. | Safer entry conclusions. | Revisit after sample-size policy. |
| AR-060 | `01_AUDIT_MATRIX.csv` | Known limitations lack owner/target WP fields. | Fix during hardening via risk register. | Duplicate of P1 risk-register need. | Better risk ownership. | Revisit after risk register. |
| AR-070 | `01_AUDIT_MATRIX.csv` | New metric null/empty tests needed. | Fix during hardening policy. | Prevents future metric regressions. | Safer metric expansion. | Revisit for each metric WP. |
| AR-071 | `01_AUDIT_MATRIX.csv` | Source trust per importer not documented. | Fix during hardening. | Supports AR-072. | Safer data provenance. | Revisit after source trust registry. |
| AR-074 | `01_AUDIT_MATRIX.csv` | Period comparison semantics undocumented. | Fix during hardening if touching analytics docs. | Supports confidence interpretation. | Clearer progress comparisons. | Revisit during metrics contract task. |
| AR-075 | `01_AUDIT_MATRIX.csv` | Filter confidence labels/tests missing. | Fix during hardening if touching UI filters. | Prevents playlist/side overclaims. | Safer UI. | Revisit after source/sample policy. |
| AR-086 | `01_AUDIT_MATRIX.csv` | Contract tests absent. | Fix during hardening with AR-018. | Core gate item. | Reduces API drift. | Revisit after contract tests. |
| AR-089 | `01_AUDIT_MATRIX.csv` | Sanitized parser payload fixtures needed. | Fix during hardening if parser/metric fixtures are added. | Avoids raw demo dependency. | Safer tests. | Revisit during golden fixture task. |
| AR-091 | `01_AUDIT_MATRIX.csv` | Logs/errors/debug traces thin. | Fix during hardening. | Supports incident runbook. | Better ops readiness. | Revisit after observability doc. |
| AR-094 | `01_AUDIT_MATRIX.csv` | Incident process thin. | Fix during hardening as runbook. | Needed before public/runtime expansion. | Faster recovery. | Revisit after incident runbook. |
| AR-099 | `01_AUDIT_MATRIX.csv` | Follow-up task registration needs approval. | Fix during hardening by registering this plan. | Current plan changes active lane. | Better PM continuity. | Revisit after canonical docs updated. |
| AR-104 | `01_AUDIT_MATRIX.csv` | Audit comments need PM review before implementing. | Fix during hardening. | This plan is that review. | Converts audit into execution plan. | Revisit after first Executor task. |
| AR-105 | `01_AUDIT_MATRIX.csv` | User/PM must decide follow-up WPs. | Fix during hardening. | Decision captured in this package. | Reduces roadmap ambiguity. | Revisit after user accepts hardening lane. |

## B. Backlog After Readiness

| Audit ID | Source audit file | Finding | Decision | Rationale | Impact | Revisit condition |
|---|---|---|---|---|---|---|
| AR-004 | `01_AUDIT_MATRIX.csv` | Role handoff examples could improve. | Backlog. | Helpful but not gate-critical. | Better examples later. | Revisit after 2-3 hardening tasks. |
| AR-011 | `01_AUDIT_MATRIX.csv` | Review protocol should stay findings-first. | Backlog/maintain. | Existing state is good. | Low risk. | Revisit if review quality drops. |
| AR-028 | `01_AUDIT_MATRIX.csv` | Performance budget/benchmark needed. | Backlog after readiness unless `/coach` volume grows. | Not blocking docs/AI foundation. | Future runtime safety. | Revisit before larger demo volume. |
| AR-030 | `01_AUDIT_MATRIX.csv` | Frontend inventory/UI tests needed. | Backlog after core contracts. | Useful but not first gate item. | Better UI stability. | Revisit during WP-019. |
| AR-044 | `01_AUDIT_MATRIX.csv` | CS2 map registry/normalizer missing. | Backlog after domain pack documents unavailable/weak states. | Domain expansion item. | Better map features later. | Revisit before map-specific advice. |
| AR-048 | `01_AUDIT_MATRIX.csv` | Utility event fixture/confidence thresholds missing. | Backlog unless utility advice is touched. | Domain-specific. | Safer utility claims later. | Revisit before utility hard recommendations. |
| AR-056 | `01_AUDIT_MATRIX.csv` | CS2 glossary missing. | Backlog or bundle with domain pack. | Low risk. | Better shared terms. | Revisit during domain pack doc. |
| AR-077 | `01_AUDIT_MATRIX.csv` | mypy/pyright gradual adoption. | Backlog. | Good engineering, not immediate readiness blocker. | Better static safety. | Revisit after P0/P1 closed. |
| AR-079 | `01_AUDIT_MATRIX.csv` | Dead-code audit missing. | Backlog. | Cleanup after foundation. | Smaller codebase later. | Revisit after hardening gate. |
| AR-080 | `01_AUDIT_MATRIX.csv` | Duplicate background job helper logic. | Backlog; fix only when Steam routes are touched. | Avoid broad refactor now. | Cleaner import code later. | Revisit during worker implementation. |
| AR-082 | `01_AUDIT_MATRIX.csv` | Dependency direction/templates context. | Backlog. | Broad module movement not needed now. | Cleaner architecture later. | Revisit after architecture map. |
| AR-084 | `01_AUDIT_MATRIX.csv` | More integration/browser tests. | Backlog unless UI changes. | Core eval/contract gaps are higher priority. | Better UI confidence. | Revisit for WP-019. |
| AR-085 | `01_AUDIT_MATRIX.csv` | E2E tests absent. | Backlog. | Not required for practical 95 if scoped gates pass. | Better browser safety later. | Revisit before daily UX/public work. |
| AR-092 | `01_AUDIT_MATRIX.csv` | Restore verification should be regular. | Backlog to WP-020 unless DB task needs it. | Ops hardening later. | Better disaster recovery. | Revisit in deployment/storage hardening. |

## C. Accepted Risk

| Audit ID | Source audit file | Finding | Decision | Rationale | Impact | Revisit condition |
|---|---|---|---|---|---|---|
| AR-001 | `01_AUDIT_MATRIX.csv` | Root contract exists. | Accepted risk / maintain. | Strong current state. | Low risk. | Revisit if root contract changes. |
| AR-002 | `01_AUDIT_MATRIX.csv` | Source-of-truth hierarchy exists. | Accepted risk / maintain. | Strong current state. | Low risk. | Revisit if docs conflict. |
| AR-003 | `01_AUDIT_MATRIX.csv` | Context loading protocol exists. | Accepted risk / maintain. | Strong current state. | Low risk. | Revisit if stale docs pollute tasks. |
| AR-006 | `01_AUDIT_MATRIX.csv` | Task card contract exists. | Accepted risk / enforce usage. | Already usable. | Low risk. | Revisit if Executor reports omit fields. |
| AR-008 | `01_AUDIT_MATRIX.csv` | Safe modes exist. | Accepted risk / enforce usage. | Already documented. | Low risk. | Revisit if tasks omit mode. |
| AR-012 | `01_AUDIT_MATRIX.csv` | Git/diff rules exist; worktree can be dirty. | Accepted with explicit preflight. | Current audit files are intentionally untracked. | Medium if ignored. | Revisit before each task. |
| AR-013 | `01_AUDIT_MATRIX.csv` | Current status/handoff strong. | Accepted risk / maintain. | Strong current state. | Low risk. | Revisit every 3-5 WPs. |
| AR-041 | `01_AUDIT_MATRIX.csv` | Fallback behavior visible. | Accepted risk / maintain. | Existing validator/fallback is good. | Low risk. | Revisit with AI UI history changes. |
| AR-046 | `01_AUDIT_MATRIX.csv` | early_deaths warning-only. | Accepted risk. | Current warning-only status is safe. | Low risk if maintained. | Revisit before hard early-death advice. |
| AR-050 | `01_AUDIT_MATRIX.csv` | Aim metrics good; crosshair/spray unavailable. | Accepted risk. | Current limitation is honest. | Low risk if maintained. | Revisit when data exists. |
| AR-057 | `01_AUDIT_MATRIX.csv` | Stack documented. | Accepted risk. | Good enough. | Low risk. | Revisit if port/runtime changes. |
| AR-059 | `01_AUDIT_MATRIX.csv` | Feature status mostly clear. | Accepted risk. | Acceptance matrix is canonical. | Low risk. | Revisit during roadmap updates. |
| AR-061 | `01_AUDIT_MATRIX.csv` | Roadmap strong. | Accepted risk with pause overlay. | Registry/version roadmap are usable. | Low risk after pause doc. | Revisit after gate PASS. |
| AR-063 | `01_AUDIT_MATRIX.csv` | Decisions doc exists. | Accepted risk. | Low risk. | Low risk. | Revisit for durable product decisions. |
| AR-064 | `01_AUDIT_MATRIX.csv` | Current state strong. | Accepted risk / maintain DB SHA checks. | Good current state. | Low risk. | Revisit before DB-dependent WP. |
| AR-083 | `01_AUDIT_MATRIX.csv` | Unit tests good. | Accepted risk / maintain. | Full suite passed. | Low risk. | Revisit if test count drops. |
| AR-096 | `01_AUDIT_MATRIX.csv` | No secrets in git baseline. | Accepted risk / maintain. | Status checks exist. | Low risk. | Revisit before commits. |
| AR-100 | `01_AUDIT_MATRIX.csv` | Evidence file-backed. | Accepted risk. | Strong audit evidence. | Low risk. | Revisit next audit. |
| AR-102 | `01_AUDIT_MATRIX.csv` | Diff discipline good. | Accepted risk. | Rules exist. | Low risk. | Revisit every task. |
| AR-103 | `01_AUDIT_MATRIX.csv` | Test results stored. | Accepted risk. | Strong evidence. | Low risk. | Revisit next audit. |
| AR-106 | `01_AUDIT_MATRIX.csv` | Audit rollback point is delete audit folder if rejected. | Accepted risk. | No production mutation. | Low risk. | Revisit only if audit rejected. |

## D. Duplicate / Not Needed

| Audit ID | Source audit file | Finding | Decision | Rationale | Impact | Revisit condition |
|---|---|---|---|---|---|---|
| AR-058 | `01_AUDIT_MATRIX.csv` | `PROJECT_INDEX` missing; `DOCS_INDEX` exists. | Duplicate/not needed now. | Current navigation uses `docs/project_management/DOCS_INDEX.md` and `DOCS_MAP.md`. | Low. | Revisit only if user wants root `PROJECT_INDEX.md`. |
| AR-062 | `01_AUDIT_MATRIX.csv` | Current deploy verification. | Duplicate with deploy/ops hardening. | Covered later by AR-024/WP-020. | Low now. | Revisit in deployment hardening. |
| AR-065 | `01_AUDIT_MATRIX.csv` | Historical docs numerous. | Duplicate with docs context policy. | Already classified; no deletion now. | Medium if ignored. | Revisit in conservative docs cleanup. |
| AR-066 | `01_AUDIT_MATRIX.csv` | Runtime artifacts in repo tree. | Duplicate with storage/ops hardening. | Root rules and `.gitignore` already block commits. | Medium. | Revisit in storage hardening. |
| AR-101 | `01_AUDIT_MATRIX.csv` | Use report next steps for durable state. | Duplicate with this hardening package. | Plan provides durable state. | Low. | Revisit after first task report. |

## E. Needs Clarification

| Audit ID | Source audit file | Finding | Decision | Rationale | Impact | Revisit condition |
|---|---|---|---|---|---|---|
| None | audit matrix | No P2/P3 item needs immediate human clarification. | No clarification needed. | The audit gives enough evidence for triage. | None. | Reopen if user wants root `PROJECT_INDEX.md` or public/friends roadmap. |

