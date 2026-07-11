# WP-017X Legacy Documentation Currency Snapshot Report

## 1. Summary

WP-017X inspected the current documentation corpus and produced a conservative
Documentation Steward cleanup/deprecation snapshot. The inspection covered the
active Hot/Warm governance layer, root docs, `docs/*.md`, `docs/*.xlsx`,
`docs/agents/*`, `docs/project_management/*`, `docs/tasks/*`, `instructions/*`
and `docs/audit/*` as grouped evidence.

Overall verdict: `PASS_WITH_WARNINGS`. The active docs are controlled enough to
proceed to `WP-017K`, but several legacy documents still contain stale
source-of-truth claims or old workflow prompts. They are mostly bounded by the
current Hot context, `DOCS_INDEX.md`, `DOCS_MAP.md` and explicit superseded
pointers.

No physical cleanup, file moves, deletes or archive actions were performed.

## 2. Preflight

- `pwd`: `/opt/jc-coach`
- Branch: `main`
- Git status before: clean
- Latest commits:
  - `344739d (HEAD -> main) Add task type profiles and prompt contract`
  - `00726c4 (origin/main) Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`
  - `e96864c Repair WP registry governance`
  - `e6b5165 Add root Codex agent contract`

## 3. Inspection Method

Commands/approach used:

- `find` for root docs, `docs/*.md`, `docs/*.xlsx`, `docs/agents/*`,
  `docs/project_management/*`, `docs/tasks/*`, `instructions/*`, `docs/audit/*`
  and generated/runtime docs.
- `wc -l` for line-count and size risk scan.
- `rg` for `Status:`, `source of truth`, `Hot context`, `superseded`,
  `obsolete`, `archive`, `AGENT.md`, `AGENTS.md`, `PROJECT_OS`,
  `PROJECT_CONTROL`, `VERSION_MAP`, `ROADMAP`, `instructions/*` and
  `docs/tasks/*` references.
- Targeted heading/status checks on active governance docs and legacy
  entrypoints.
- Targeted samples from guardian docs, roadmap/control docs, old curation docs,
  task prompts and instruction files.
- Audit reports were grouped as evidence; every old report was not deeply read.

One malformed exploratory `wc` command attempted `/docs/...` absolute paths and
returned no file data. It had no side effects and was repeated correctly with
relative paths.

## 4. Directory-Level Classification

| Area | Role | Classification | Risk | Recommended action |
|---|---|---|---|---|
| root docs / repo root docs | Entrypoints and project-level user/operator context. | Mixed: `AGENTS.md` canonical, `AGENT.md` obsolete pointer, `README.md` supporting. | Root `README.md` still points to `PROJECT_CONTROL.md` as canonical, below newer Hot hierarchy. | Keep; later pointer cleanup can align root `README.md`. |
| `docs/` | Domain docs, current status, governance references, historical plans. | Mixed: current status/domain docs canonical or supporting; old roadmap/planning docs archive candidates. | Some old docs still claim `PROJECT_CONTROL.md` or old roadmap labels as current. | Keep; add pointer/status cleanup in a later no-risk WP. |
| `docs/agents/` | Domain guardian guardrails. | SUPPORTING. | Names overlap with new agent workflow roles, but content is domain-specific guardrails. | Keep; clarify later only if confusion recurs. |
| `docs/project_management/` | Current registry, workflow, roadmap and planning control. | Mixed: several canonical Warm/Hot-adjacent governance docs; old curation manuals archive candidates. | Old curation manuals are large and contain superseded process claims. | Keep canonical docs; mark old curation manuals as archive candidates in a later cleanup. |
| `docs/tasks/` | Historical task prompts/specs. | ARCHIVE_CANDIDATE as a group. | Large old task prompts contain old `AGENT.md`, `PROJECT_CONTROL.md`, `ROADMAP.md` assumptions. | Keep as evidence; do not read by default. |
| `instructions/` | Original briefs/prompts/specs and sample data. | ARCHIVE_CANDIDATE as a group, with `10_MINIMAL_SAMPLE_DATA.csv` supporting sample artifact. | Old prompts can conflict with current no-job/no-commit governance. | Keep as evidence; later status headers/archive optional. |
| `docs/audit/` | WP/stage/audit evidence history. | SUPPORTING evidence. | Old audits include stale findings and old source-of-truth assumptions. | Keep; read only when task-relevant. |
| generated docs/data docs | Runtime/generated handoffs, reports, sample data, credentials text, vendor docs. | Mixed runtime artifacts; not project docs source-of-truth. | Generated reports/handoffs and vendor `node_modules` docs can pollute broad searches; credential text files are sensitive runtime artifacts. | Do not read by default; exclude from docs-currency truth unless a specific task requires them. |

## 5. File/Group Classification Table

| Path or group | Classification | Reason | Current risk | Recommended action | Read by default |
|---|---|---|---|---|---|
| `AGENTS.md` | CANONICAL | Root Codex operating contract and Hot context definition. | Low. | keep | yes |
| `AGENT.md` | OBSOLETE | Explicit superseded pointer to `AGENTS.md`. | Low if treated as pointer only. | obsolete pointer | no |
| `docs/CURRENT_STATUS.md` | CANONICAL | Current product/runtime/blocker snapshot. | Low. | keep | yes |
| `docs/HANDOFF.md` | CANONICAL | New-session bootstrap and next safe step. | Low. | keep | yes for new sessions |
| `docs/DECISIONS.md` | CANONICAL | Durable decisions list. | Low. | keep | no |
| `docs/PROJECT_CONTROL.md` | SUPPORTING | Useful policy/product control history, but current hierarchy starts with Hot context. | Medium: top line still says canonical and lists `PROJECT_OS.md` as governance entrypoint. | update pointer | no |
| `docs/PROJECT_OS.md` | OBSOLETE | Explicit historical/superseded entrypoint pointing to Hot context. | Low. | obsolete pointer | no |
| `docs/PROJECT_GOVERNANCE.md` | SUPPORTING | Governance reference with current pointer to Hot context. | Low/medium if used as current state. | monitor | no |
| `docs/README.md` | SUPPORTING | Human documentation entrypoint with Hot context pointer. | Low. | keep | no |
| root `README.md` | SUPPORTING | Operator/user README. | Medium: still states `PROJECT_CONTROL.md` as canonical source. | update pointer | no |
| `docs/ROADMAP.md` | ARCHIVE_CANDIDATE | Older roadmap with stale `v0.7-prep` framing. | High if used for current sequence. | archive candidate | no |
| `docs/VERSION_MAP.md` | ARCHIVE_CANDIDATE | Older version table with stale labels. | High if used for current version truth. | archive candidate | no |
| `docs/project_management/WP_REGISTRY.md` | CANONICAL | WP IDs, order, status, dependencies and report paths. | Low. | keep | yes |
| `docs/project_management/AGENT_WORKFLOW.md` | CANONICAL | Repo-native task routing, roles, prompt/report contracts and Docs Steward model. | Low; ceremony creep if overused. | keep | no |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | CANONICAL | Source-of-truth hierarchy, WP lifecycle and operating policy. | Low. | keep | no |
| `docs/project_management/MASTER_WP_CHECKLIST.md` | SUPPORTING | Human campaign map; registry wins. | Medium if treated as status truth. | monitor | no |
| `docs/project_management/DOCS_INDEX.md` | SUPPORTING | Human navigation index. | Low. | keep | no |
| `docs/project_management/DOCS_MAP.md` | CANONICAL | Documentation ownership/context/stale-risk map. | Low. | keep | no |
| `docs/project_management/VERSION_ROADMAP.md` | CANONICAL | Version-to-WP roadmap table. | Medium: WP-017V/W governance additions not all reflected in prose, but registry wins. | monitor/update when promotion work touches roadmap | no |
| `docs/project_management/WORK_PACKAGE_BACKLOG.md` | SUPPORTING | Planned WP objectives and guards; explicit governance artifact. | Medium if used over registry for current status. | monitor | no |
| `docs/project_management/ACCEPTANCE_MATRIX.md` | CANONICAL | Acceptance status by feature/version. | Medium: update on promotion only. | keep/update during WP-017K | no |
| `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` | ARCHIVE_CANDIDATE | Large old operating playbook; claims itself as source of truth. | High if read as active workflow. | archive candidate / add pointer later | no |
| `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` | ARCHIVE_CANDIDATE | Large old handoff manual with old version/milestone framing. | High if read as active handoff. | archive candidate / add pointer later | no |
| `docs/agents/DB_GUARDIAN.md` | SUPPORTING | Domain guardrail for DB safety. | Low. | keep | no |
| `docs/agents/IMPORT_GUARDIAN.md` | SUPPORTING | Domain guardrail for Steam/import/parser boundaries. | Low. | keep | no |
| `docs/agents/METRICS_GUARDIAN.md` | SUPPORTING | Domain guardrail for metric/recommendation/AI truth. | Low. | keep | no |
| `docs/agents/PM_ORCHESTRATOR.md` | SUPPORTING | Domain guardian for PM scope/evidence. | Medium: activation paths still list `AGENT.md`. | update pointer later | no |
| `docs/agents/RUNTIME_GUARDIAN.md` | SUPPORTING | Domain guardrail for runtime/service safety. | Low. | keep | no |
| `docs/agents/TEST_GUARDIAN.md` | SUPPORTING | Domain guardrail for test isolation. | Low. | keep | no |
| `docs/agents/UI_COACH_GUARDIAN.md` | SUPPORTING | Domain guardrail for `/coach` UI honesty. | Low. | keep | no |
| `docs/tasks/*` | ARCHIVE_CANDIDATE | Historical stage/task prompts and old audit prompts. | High if used as current instructions. | archive candidate / status headers later | no |
| `instructions/*` | ARCHIVE_CANDIDATE | Original prompt/spec corpus; several files are old implementation instructions. | High if used as current instructions. | archive candidate / status headers later | no |
| `instructions/10_MINIMAL_SAMPLE_DATA.csv` | SUPPORTING | Small sample artifact, not instruction policy. | Low. | keep | no |
| `instructions/1.txt` | ARCHIVE_CANDIDATE | One-line placeholder-like artifact. | Low but unclear. | archive candidate after owner approval | no |
| `docs/audit/*` | SUPPORTING | Point-in-time evidence/history, grouped. | Medium if stale findings override current docs. | keep; read task-relevant reports only | no |
| `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` | SUPPORTING | Out-of-band governance audit evidence, not planned WP-018 product work. | Medium if ID is misread as product WP-018. | keep with registry note | no |
| Old scoring/spreadsheet docs | SUPPORTING | `FEATURE_ROADMAP_SCORING`, `METRICS_ROADMAP_SCORING_RU` and `.xlsx` files are planning/scoring evidence. | Medium if treated as roadmap/metric truth. | monitor / archive candidate later if stale | no |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | ARCHIVE_CANDIDATE | Old prompt pack for long autonomous sessions. | High if reused against current no-live/no-commit constraints. | archive candidate / pointer later | no |
| `docs/DOCUMENTATION_AUDIT.md` | SUPPORTING | Earlier consolidation audit. | Medium: old source-of-truth order names `PROJECT_CONTROL.md`. | keep as historical evidence | no |
| Generated `data/ai_handoffs/*/codex_prompt.md` | SUPPORTING | Generated runtime handoff prompts. | Medium if mistaken for current prompt contract. | do not read by default | no |
| Generated `data/reports/coach_report_*.md` | SUPPORTING | Generated app reports. | Medium; persistent reports must not be generated unless authorized. | do not read by default | no |
| `data/incoming_demos/README.txt` | SUPPORTING | Runtime storage note. | Low. | keep | no |
| `data/steam_bot_credentials/*.txt` | ARCHIVE_CANDIDATE | Runtime credential/token artifacts, not documentation truth. | High sensitivity; never commit. | keep out of docs workflow; do not read by default | no |
| Vendor `tools/steam-gc/node_modules/**` docs | SUPPORTING | Third-party package docs. | Search noise only. | exclude from docs-currency truth | no |

## 6. Duplicate Or Conflicting Instruction Risks

- `AGENT.md` vs `AGENTS.md`: resolved operationally. `AGENT.md` is now a
  superseded pointer; `AGENTS.md` is the root contract.
- Old prompt packs vs `AGENT_WORKFLOW.md`: `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`,
  `docs/tasks/*` and `instructions/*` include old task-running patterns and
  should not override Task Card routing.
- Old roadmap/version docs vs `WP_REGISTRY.md` / `VERSION_ROADMAP.md`:
  `docs/ROADMAP.md` and `docs/VERSION_MAP.md` still contain old `v0.7-prep`
  framing and should not drive current sequencing.
- Old project OS/governance docs vs `CURRENT_STATUS.md` /
  `PROJECT_OPERATING_PROTOCOL.md`: `PROJECT_OS.md` is now a safe obsolete
  pointer, but `PROJECT_CONTROL.md` still contains old canonical/entrypoint
  wording.
- Guardian docs vs `AGENT_WORKFLOW.md` roles: not a blocker. Guardian docs are
  domain guardrails; `AGENT_WORKFLOW.md` defines WP process roles. Naming can
  confuse future readers, but current docs distinguish them.
- Root `README.md` vs current Hot hierarchy: root README still says
  `PROJECT_CONTROL.md` is canonical. This is a pointer cleanup candidate, not
  a blocker because `AGENTS.md` and docs navigation supersede it for Codex.

## 7. Unreferenced / Low-Use Documents

No deletion was performed. Low-use or stale-risk candidates:

| Document/group | Type | Note |
|---|---|---|
| `instructions/1.txt` | archive candidate | Placeholder-like one-line artifact; owner decision needed before move/delete. |
| `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` | risky stale instruction | Large old playbook; useful history but should not be active workflow. |
| `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` | risky stale instruction | Old handoff manual; useful history but superseded by `HANDOFF.md`. |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | risky stale instruction | Old autonomous prompt pack; conflicts with current scoped WP controls. |
| `docs/ROADMAP.md` / `docs/VERSION_MAP.md` | risky stale instruction | Older roadmap/version labels. |
| `docs/tasks/*` | harmless history / possible useful reference | Historical task specs; useful to understand past WPs, not active roadmap. |
| `instructions/*` | possible useful reference / risky stale instruction | Original project briefs/specs and prompts; keep for history only. |
| Generated `data/ai_handoffs/*` and `data/reports/*` | generated runtime docs | Useful evidence only when explicitly requested. |
| Vendor `tools/steam-gc/node_modules/**` markdown | low-use search noise | Third-party docs, not project governance. |

## 8. Recommended Cleanup Plan

### Stage A — No-Risk Metadata/Pointer Cleanup

- Add or update status headers on `docs/PROJECT_CONTROL.md`, root `README.md`,
  `docs/ROADMAP.md`, `docs/VERSION_MAP.md`,
  `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`,
  `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`,
  `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`, `docs/tasks/*` and `instructions/*`.
- Update `PROJECT_CONTROL.md` wording so it no longer claims to be the top
  canonical source over `AGENTS.md` / `CURRENT_STATUS.md` / `WP_REGISTRY.md`.
- Update root `README.md` to point humans to Hot context and
  `docs/README.md`/`DOCS_INDEX.md` for navigation.
- Update `PM_ORCHESTRATOR.md` activation paths to prefer `AGENTS.md` over
  `AGENT.md`.
- Keep `DOCS_INDEX.md` and `DOCS_MAP.md` as the navigation/status location for
  all classifications.

### Stage B — Optional Physical Archive

Only if user approves:

- Move archive candidates to `docs/archive/` or a dated archive subfolder.
- Preserve a path mapping list so audit evidence remains traceable.
- Do not move WP reports that are referenced by the registry.
- Do not move files needed by current source-of-truth docs without updating
  references in the same WP.

### Stage C — Optional Automation Later

- Add a docs inventory script that excludes `.git`, `.venv`, `node_modules`,
  runtime credential paths and generated reports by default.
- Add stale docs checker for top-of-file status blocks.
- Add link/reference scanner for moved/archived docs.
- Add a low-cost report generator that only reads metadata/headings unless a
  broad audit is explicitly requested.

## 9. What Must Not Be Changed Automatically

- No deletion.
- No archive move.
- No rewrite of old history.
- No source-of-truth change without user approval.
- No treating old audit reports, prompts or plans as current truth.
- No automatic cleanup of generated data/report docs.

## 10. Documentation Steward Verdict

`PASS_WITH_WARNINGS` — proceed to WP-017K, but the cleanup plan exists.

Warnings:

- `PROJECT_CONTROL.md`, root `README.md`, `ROADMAP.md`, `VERSION_MAP.md`, old
  curation docs, old task prompts and `instructions/*` still carry stale or
  potentially confusing instructions.
- Current Hot context and docs navigation are strong enough to bound those
  risks for product development.
- Physical cleanup should be a separate explicit WP, not part of WP-017X.

## 11. Next Recommended Step

Proceed to WP-017K.

## 12. Checks

Final check results:

- `git diff --check`: PASS, no output.
- `git diff --stat`: PASS, tracked-doc diff shown:
  `docs/CURRENT_STATUS.md`, `docs/HANDOFF.md`,
  `docs/project_management/WP_REGISTRY.md`; 11 insertions, 5 deletions. New
  untracked WP report is visible in `git status --short`.
- `git status --short`: PASS, only WP-017X documentation changes are present.
- `python3 scripts/project_gate.py --help`: PASS, read-only help displayed
  available commands `preflight`, `changed`, `required-checks`, `postflight`.
