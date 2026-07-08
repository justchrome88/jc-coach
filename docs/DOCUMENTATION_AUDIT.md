# Documentation Inventory And Conflict Audit

Audit date: 2026-07-03.

Purpose: document the consolidation of README, docs, instructions, roadmap, audit files and agent rules under the canonical source of truth `docs/PROJECT_CONTROL.md`.

This file is the summary audit. Detailed audit artifacts now live in:

- `docs/audit/INSTRUCTIONS_AUDIT_REPORT.md`
- `docs/audit/INSTRUCTIONS_INVENTORY.md`
- `docs/audit/DOCUMENT_CONFLICTS.md`
- `docs/audit/DOCUMENT_DEPRECATION_PLAN.md`

## Source Of Truth Order

1. `docs/PROJECT_CONTROL.md` - canonical current product, architecture, constraints and priorities.
2. `README.md` - current operator/user entrypoint; should link to project control for canonical decisions.
3. `WORKLOG.md` - chronological implementation journal; factual history, not current-state contract.
4. Current supporting docs in `docs/` - architecture/spec/roadmap references under `PROJECT_CONTROL`.
5. `docs/audit/*` - point-in-time audits; useful evidence, not automatically current after later work.
6. `docs/archive/lean-docs-2026-07-09/from-root/instructions/*` - archived historical prompts/TZ/agent notes unless explicitly reactivated.

## Inventory

| File/group | Role after consolidation | Action |
|---|---|---|
| `docs/PROJECT_CONTROL.md` | Canonical source of truth | Created. |
| `README.md` | User/operator entrypoint | Keep current; add canonical-doc notice. |
| `WORKLOG.md` | Chronological work history | Keep as historical log. |
| `docs/FEATURES_RU.md` | Current feature list | Keep as supporting doc. |
| `docs/STEAM_IMPORT_ARCHITECTURE.md` | Steam architecture | Keep as supporting doc. |
| `docs/STEAM_MATCH_DATES_RU.md` | Steam date policy | Keep as supporting doc. |
| `docs/DEMO_DEEP_PARSER_TZ_RU.md` | Deep parser spec/log | Keep as supporting doc. |
| `docs/DEMO_STORAGE_TZ.md` | Raw demo lifecycle spec | Keep as supporting doc. |
| `docs/METRICS_ROADMAP_SCORING_RU.md` | Metrics priority matrix | Keep, but not a definitive formula spec. |
| `docs/FEATURE_ROADMAP_SCORING.md` | Feature scoring | Keep; percentages are advisory. |
| `docs/audit/CS2_AI_COACH_AUDIT_2026-07-02.md` | Point-in-time audit | Keep; link from control doc. |
| `docs/PRODUCT_EXECUTION_STRATEGY.md` | Strategy memo | Keep, mark subordinate to control doc. |
| `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` | Older implementation plan | Mark historical because several statuses are stale. |
| `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` | Older AI provider memo | Mark partially historical because persistence/local LLM scaffold has advanced. |
| `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` | Completed execution plan | Mark historical/completed. |
| `docs/COMPETITOR_FEATURE_MATRIX.md` | Competitor reference | Mark historical because implementation statuses are stale. |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | Prompt library | Mark historical; some instructions conflict with current no-code/no-jobs tasks. |
| `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md` | Deployment checklist | Keep as operational reference; security readiness still governed by control doc. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/00_PROJECT_BRIEF.md` | Original brief | Mark historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/01_OVERNIGHT_MVP_TASK.md` | Original MVP task | Mark historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/02_FULL_PERSONAL_PRODUCT_TZ.md` | Original full TZ | Mark historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/03_CODEX_AGENT_RULES.md` | Agent rules | Update to read `PROJECT_CONTROL` first and treat older instructions as historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/04_DATA_AND_METRICS_SPEC.md` | Original metric wish-list/spec | Mark historical until replaced by runtime metric spec. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/05_AI_COACH_PROMPT.md` | Prompt reference | Mark historical; runtime prompt lives in code. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/06_STEAM_AND_DEMO_IMPORT_NOTES.md` | Early Steam notes | Mark historical; superseded by Steam architecture docs. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/07_ROADMAP.md` | Early roadmap | Mark historical; superseded by control/backlog. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/08_TASKS_FOR_GPT55_AND_SPARK.md` | Agent division notes | Mark historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/09_READY_TO_PASTE_COMMANDS.md` | Old prompt commands | Mark historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/10_MINIMAL_SAMPLE_DATA.csv` | Sample data | Keep as archived historical evidence. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/11_REWRITTEN_USER_REQUEST_FOR_OTHER_CHAT.md` | Chat handoff prompt | Mark historical. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md` | Recommendation tracking TZ | Mark historical reference; runtime behavior is in current code/control doc. |
| `docs/archive/lean-docs-2026-07-09/from-root/instructions/1.txt` | Empty/placeholder-like artifact | Archived historical evidence. |

## Conflict Audit

| Conflict | Older source | Canonical resolution |
|---|---|---|
| Project called only `MVP v0.1` | README title, early instructions | Current status is `v0.7-prep: personal alpha with coach-loop foundation`, not public/friends ready. |
| Public/friends readiness implied by login/register | README deployment sections, worklog entries | App is personal/VPS only until API auth, user ownership, CSRF/rate limits and strong secrets are handled. |
| Steam/FACEIT login not started | `docs/COMPETITOR_FEATURE_MATRIX.md`, early roadmaps | Steam alpha path exists; FACEIT remains future. |
| Automatic match import not implemented | `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`, early instructions | Steam background import path exists but is not production-ready. |
| AI coach not started / OpenAI API path | early instructions and some plans | Current path is `codex_cli_handoff` plus `local_llm` scaffold; no OpenAI API dependency. |
| AI provider next step says persist results | `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` | AI result persistence already exists; next step is schema/validator/versioning. |
| Recommendation lifecycle not implemented | older prompt/roadmap docs | Lifecycle actions exist; planner/problem linkage is the remaining gap. |
| Aim stats very partial | older scoring/plan docs | Aim profile exists, but advanced aim metrics remain data gaps. |
| Raw demo deletion target may read as near-term | storage docs/plans | Delete policy is explicitly off until parsed payload verification is implemented. |
| Agent rules say inspect all root `.md` files only | `docs/archive/lean-docs-2026-07-09/from-root/instructions/03_CODEX_AGENT_RULES.md` | Agents must read `docs/PROJECT_CONTROL.md`, README, WORKLOG and relevant docs/instructions for the task. |
| Prompt libraries require commit/push/test/jobs | `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`, `docs/archive/lean-docs-2026-07-09/from-root/instructions/09_READY_TO_PASTE_COMMANDS.md` | Those are historical prompts. Current user instructions override them; do not run jobs or commit/push unless asked. |

## Deprecation Plan

No historical documents were deleted in this consolidation.

1. Add historical/deprecated notices to stale plans, original TZs and prompt libraries.
2. Keep all historical files for at least one review cycle while `PROJECT_CONTROL` proves sufficient.
3. Later docs-only cleanup moved stale instruction artifacts under `docs/archive/lean-docs-2026-07-09/from-root/` as archived historical evidence.
4. Before deleting any document, verify that unique current information has been migrated into `PROJECT_CONTROL` or a supporting doc.
5. Keep `WORKLOG.md` and dated audit files permanently unless the project adopts a formal changelog/archive policy.

## Gaps Left Intentionally

- A definitive `docs/METRICS.md` runtime formula/confidence spec still needs to be created.
- Roadmap Excel files were not edited in this pass.
- No code, DB, imports, parser jobs, Steam jobs or generated runtime data were touched.
