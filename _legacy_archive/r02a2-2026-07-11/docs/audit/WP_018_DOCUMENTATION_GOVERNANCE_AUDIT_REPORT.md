# WP-018 Documentation Governance Audit Report

Date: 2026-07-05.

Mode: documentation/governance audit with one permitted file creation.

Scope: read-only audit of project documentation and governance controls, with
this report saved as the only new file. No application code, runtime
configuration, business logic, DB/schema/data, imports, parser jobs, evaluator
jobs, systemd/nginx configuration, dependencies, existing documents, file moves,
git add, commit or push were performed.

Important naming note: this report uses the user-requested path
`docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md`. The current
`docs/project_management/WP_REGISTRY.md` already reserves `WP-018` for
`Coach Quality Calibration`. A future governance cleanup should decide whether
this audit is an out-of-band report, whether it gets a non-conflicting WP ID,
or whether the registry is explicitly updated. Do not silently reuse WP IDs.

## 1. Executive summary

What is good:

- The project already has a serious governance base: `AGENTS.md`,
  `docs/project_management/WP_REGISTRY.md`, `docs/CURRENT_STATUS.md`,
  `docs/HANDOFF.md`, `docs/PROJECT_CONTROL.md`, roadmap/backlog/acceptance
  docs, guardian docs, testing/deploy docs and extensive WP audit evidence.
- Runtime, DB, import/parser, recommendation and promotion safety rules are
  well documented in several places.
- `scripts/project_gate.py` is read-only and already checks for `AGENTS.md`,
  `WP_REGISTRY.md`, DB SHA and guardian-specific check hints.
- Current production DB SHA matches the handoff value:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.

What is risky:

- The control layer is too large and duplicated. Several files compete to be
  the new-session entrypoint.
- Some entrypoint/navigation docs are stale and point to old versions/WPs:
  `docs/PROJECT_OS.md`, `docs/README.md`,
  `docs/project_management/DOCS_INDEX.md`, `docs/PROJECT_GOVERNANCE.md`.
- `AGENT.md` and `AGENTS.md` coexist. `AGENT.md` still calls itself canonical
  and requires reading many files before any task, which conflicts with the
  intended small Hot context model.
- Current WP-017J worktree changes are uncommitted. The audit is being run on a
  dirty tree, and the new report is added on top of pre-existing uncommitted
  documentation changes.

Primary governance risk:

- A fresh Codex session can start from a stale entrypoint and believe the
  project is at `v0.5/WP-014` or `WP-012`, while the current control docs in
  the dirty worktree say product version `v0.8`, next WP `WP-017K`, and `v0.9`
  is still not promoted. This creates session drift, duplicate reading and
  possible unsafe WP sequencing.

Recommended next move:

- Run a dedicated documentation governance repair WP that does not touch product
  code. Its goal should be to make `AGENTS.md` the sole agent contract, mark or
  retire `AGENT.md`, repair stale entrypoints, define Hot/Warm/Cold context,
  and compress the always-read layer to 3-4 files. Do not move/delete archive
  evidence until the user approves the deprecation policy.

## 2. Read-only commands executed

Commands required by the audit prompt:

| Command | Summary |
|---|---|
| `pwd` | Confirmed project path: `/opt/jc-coach`. |
| `git status --short` | Dirty before this audit: modified `docs/CURRENT_STATUS.md`, `docs/HANDOFF.md`, `docs/PROJECT_CONTROL.md`, `docs/project_management/ACCEPTANCE_MATRIX.md`, `VERSION_ROADMAP.md`, `WORK_PACKAGE_BACKLOG.md`, `WP_REGISTRY.md`; untracked `docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md`. These changes existed before this report creation. |
| `git branch --show-current` | Confirmed branch: `main`. |
| `git log --oneline -12 --decorate` | Latest commit: `6514c80 (HEAD -> main) Diagnose match mode classification limits`; `origin/main` at `e17f070 Accept post-batch performance with warnings`; recent commits cover WP-017R/I0/I/H/G/F/E/D/C/C2. |
| `find . -maxdepth 4 -type f \( -name "*.md" -o -name "*.txt" \) \| sort` | Found root docs, `docs/`, `docs/project_management/`, `docs/agents/`, `docs/audit/`, `docs/tasks/`, legacy `instructions/`, generated data reports/handoffs and credential text artifacts. |
| `ls -la` | Confirmed repo root contains app, docs, data, deploy, scripts, tests, `AGENT.md`, `AGENTS.md`, `README.md`, `WORKLOG.md`, `.env`, `.venv`, etc. |
| `ls -la docs \|\| true` | Confirmed many top-level docs; large current files include `CURRENT_STATUS.md`, `HANDOFF.md`, `PROJECT_CONTROL.md`, `STEAM_IMPORT.md`, older strategy/scoring docs. |
| `ls -la docs/project_management \|\| true` | Confirmed `WP_REGISTRY.md`, `VERSION_ROADMAP.md`, `WORK_PACKAGE_BACKLOG.md`, `ACCEPTANCE_MATRIX.md`, `DOCS_INDEX.md`, `DOCS_MAP.md` and older curation docs. |
| `ls -la docs/audit \|\| true` | Confirmed extensive audit evidence through `WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md`. |
| `ls -la scripts \|\| true` | Confirmed `project_gate.py`, backup/restore, migration scripts and stale Steam import repair script. |
| `systemctl cat jc-coach 2>/dev/null \|\| true` | Confirmed unit uses `/opt/jc-coach`, uvicorn `app.main:app`, host `127.0.0.1`, port `8010`; drop-in sets `TMPDIR`, `TEMP`, `TMP` to `/opt/jc-coach/data/tmp`. |
| `systemctl status jc-coach --no-pager 2>/dev/null \|\| true` | Confirmed service active/running since 2026-07-04 22:18:58 MSK, PID `146750`, memory about `214.7M`, peak `241.4M`, recent logs include 200s and auth redirects. |

Additional safe read-only commands:

| Command | Summary |
|---|---|
| `find docs -path '*CODEX_WP_RUNBOOK.md' -o -path '*CHATGPT_BOOTSTRAP.md' -o -path '*/context/*' \| sort` | No `CODEX_WP_RUNBOOK.md`, `CHATGPT_BOOTSTRAP.md` or `docs/context/` found. |
| `wc -l ...` over docs/instructions | Markdown/txt corpus is about `33115` lines. Largest files include `CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` `1098` lines, task specs up to `937` lines, `WORKLOG.md` `633` lines, `WORK_PACKAGE_BACKLOG.md` `379` lines, `PROJECT_CONTROL.md` `332` lines. |
| `rg -n ...` for current WP/version/instruction drift | Found stale current-state claims in `PROJECT_OS.md`, `docs/README.md`, `DOCS_INDEX.md`, `PROJECT_GOVERNANCE.md`; found current `v0.8/WP-017K` in `CURRENT_STATUS.md`, `HANDOFF.md`, `PROJECT_CONTROL.md`, `WP_REGISTRY.md`. |
| `sed -n '1,240p' scripts/project_gate.py` | Confirmed read-only helper, guardian inference, DB SHA reporting and checks for `AGENTS.md`/`WP_REGISTRY.md`. |
| `sha256sum data/cs2_coach.db` | Confirmed SHA `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `sed -n '1,140p' pyproject.toml` | Confirmed Python/FastAPI/Uvicorn/SQLAlchemy/Jinja2/demoparser2 project dependencies. |
| `sed -n '1,120p' app/config.py` | Confirmed production DB default `data/cs2_coach.db`, upload/inbox/report/handoff dirs, Steam cap default `1`, test DB guard helpers. |
| `find app -maxdepth 2 -type d \| sort` | Confirmed app directories: `api`, `db`, `services`, `static`, `templates`, `web`. |

No service restart, live import, parser job, evaluator job, DB write, schema
change, dependency installation, git add, commit or push was performed.

## 3. Current project reality check

Git state:

- Branch: `main`.
- Latest commit: `6514c80 Diagnose match mode classification limits`.
- `origin/main` is behind current local HEAD by several commits.
- Worktree was already dirty before this audit because WP-017J documentation
  changes and its audit report are uncommitted.
- This audit adds one new untracked file:
  `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md`.

Service read-only status:

- `jc-coach.service` is active/running.
- Uvicorn command: `/opt/jc-coach/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010`.
- Systemd drop-in exists and sets:
  - `TMPDIR=/opt/jc-coach/data/tmp`
  - `TEMP=/opt/jc-coach/data/tmp`
  - `TMP=/opt/jc-coach/data/tmp`
- This confirms the known TMPDIR/storage issue has runtime-level mitigation in
  the currently installed service configuration.

Project path and structure:

- Root: `/opt/jc-coach`.
- Backend: Python/FastAPI/Uvicorn.
- Templates/static: `app/templates`, `app/static`.
- DB: SQLite via SQLAlchemy, default production DB path `data/cs2_coach.db`.
- Scripts: `scripts/project_gate.py`, backup/restore and migration helpers.
- Deploy references: `deploy/systemd/jc-coach.service`, `deploy/nginx/jcnodex.conf`.

Confirmed handoff assumptions:

- Current product docs in the dirty worktree say product version `v0.8`.
- Current docs say `v0.9` is not promoted.
- Current docs say next WP is `WP-017K Real Data Onboarding Promotion to v0.9`.
- Current docs say match playlist mode is unknown/provenance-only for `v0.9`.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` default remains `1` in `app/config.py`.
- Production DB SHA matches the provided handoff SHA.

Unconfirmed or not inspected:

- No live DB content queries were run.
- No tests were run.
- No external domain/network checks were run.
- Nginx live config under `/etc/nginx` was not read; only repo deploy config
  and systemd unit were inspected.
- No application routes were exercised.

## 4. Documentation inventory table

| file | role | active/historical status | problem | duplicate/overlap | recommended action | context level | read frequency |
|---|---|---|---|---|---|---|---|
| `AGENTS.md` | Root Codex operating contract | active | Missing explicit token-economy rules and no-git-add rule | overlaps `AGENT.md`, `PROJECT_CONTROL.md` safety rules | keep; later tighten | Hot | every task |
| `AGENT.md` | Older Codex agent rules | historical/stale | Claims canonical status; requires reading too many files | conflicts with `AGENTS.md` | mark superseded or replace with pointer | Cold | never except audit |
| `docs/CURRENT_STATUS.md` | Current product fact state | active | Too long for every task; accumulates history | overlaps `HANDOFF`, `PROJECT_CONTROL`, audit reports | keep; later shorten or split summary/history | Hot | every task until shorter replacement exists |
| `docs/HANDOFF.md` | Continuation state and next WP | active but too long | Very long; old history embedded | overlaps `CURRENT_STATUS`, audit reports | keep; compress later | Hot/Warm | every task for now; later per WP |
| `docs/PROJECT_CONTROL.md` | Broad source-of-truth/control doc | semi-active | Duplicates status, milestone, governance, roadmap | overlaps many docs | keep as control index; stop making always-read if Hot layer exists | Warm | per WP / process changes |
| `docs/project_management/WP_REGISTRY.md` | Canonical WP registry/status/dependencies | active | Good; but report path `WP_018...` may collide with planned WP-018 | overlaps backlog/roadmap | keep; make canonical for WP IDs | Hot | every task |
| `docs/project_management/WORK_PACKAGE_BACKLOG.md` | WP objectives, guardians, criteria | active | 379 lines; too big for every task | overlaps registry/roadmap/matrix | keep; topic/read when planning WP | Warm | per WP |
| `docs/project_management/ACCEPTANCE_MATRIX.md` | Feature acceptance and promotion criteria | active | Dense; should not be always-read | overlaps domain docs and backlog | keep | Warm | promotion/acceptance tasks |
| `docs/project_management/VERSION_ROADMAP.md` | Version-to-WP roadmap | active | Duplicates registry/backlog | overlaps ROADMAP/VERSION_MAP | keep as canonical roadmap | Warm | roadmap/promotion |
| `docs/project_management/DOCS_INDEX.md` | Human navigation index | stale | Says current WP is WP-012; points to `AGENT.md` | overlaps DOCS_MAP/README | update later | Warm | audit/navigation only |
| `docs/project_management/DOCS_MAP.md` | Docs ownership/freshness map | semi-active/stale | Points to `AGENT.md` as canonical; old WP ranges | overlaps DOCS_INDEX | update later | Warm | docs governance only |
| `docs/PROJECT_OS.md` | Short operating entrypoint | stale | Says `v0.5/WP-014`; mandates heavy reading | overlaps AGENT/PROJECT_CONTROL/HANDOFF | rewrite or replace; do not use until fixed | Cold | never until repaired |
| `docs/README.md` | Human docs entrypoint | stale | Says current WP is WP-012; points to `AGENT.md` | overlaps DOCS_INDEX | update later | Warm | human navigation only |
| `docs/PROJECT_GOVERNANCE.md` | WP/version/evidence policy | stale | Says current version `v0.4.1`, next `v0.4.2`, WP-012 | overlaps AGENTS/PROJECT_CONTROL | repair later | Warm | process changes |
| `README.md` | Repo/product overview and local run | semi-active | Long; product overview is useful but not current governance | overlaps docs README | keep as human overview | Warm | onboarding only |
| `WORKLOG.md` | Chronological engineering log | historical | Long; no longer current task log | overlaps changelog/audit | archive/evidence-only | Cold | audit only |
| `LATER.md` | Deferred ideas | semi-active | Small and useful, but not canonical roadmap | overlaps ROADMAP/PROJECT_CONTROL | keep | Warm | planning only |
| `docs/CHANGELOG.md` | Curated release notes | semi-active/stale | Does not include WP-014..WP-017 sequence | overlaps WORKLOG/audit | update per release or replace with task log summary | Warm | per release |
| `docs/DECISIONS.md` | Project decisions | semi-active/stale | Missing recent registry/mode/cap decisions | overlaps PROJECT_CONTROL | keep and update as ADR-lite | Warm | decision changes |
| `docs/ARCHITECTURE.md` | Architecture overview | active | Short; likely stale in places but useful | overlaps README | keep | Warm | architecture/code tasks |
| `docs/DEPLOYMENT.md` | Deployment/runtime policy | active | Good but high-level | overlaps deploy configs | keep | Warm | deploy/runtime tasks |
| `docs/TESTING.md` | Safe testing policy | active | Good; should be referenced by runbook | overlaps guardian rules | keep | Warm | test/code tasks |
| `docs/BACKUP_RESTORE.md` | Backup/restore policy | active | DB-task only | overlaps DB guardian | keep | Warm | DB/data tasks |
| `docs/MIGRATIONS.md` | Migration discipline | active | DB/schema-task only | overlaps DB guardian | keep | Warm | schema tasks |
| `docs/SECURITY.md` | Auth/security/public readiness | active | Security-task only | overlaps release checklist | keep | Warm | auth/security tasks |
| `docs/STEAM_IMPORT.md` | Steam import current truth | active | Long; import-task only | overlaps import audits | keep | Warm | import tasks |
| `docs/STEAM_IMPORT_ARCHITECTURE.md` | Deeper import architecture | semi-active | Supporting detail | overlaps STEAM_IMPORT | keep as reference | Warm | import design only |
| `docs/STEAM_MATCH_DATES_RU.md` | Steam date policy | semi-active | Supporting detail | overlaps import docs | keep as reference | Warm | date/import tasks |
| `docs/DEMO_DEEP_PARSER_TZ_RU.md` | Parser spec/context | semi-active | Long; partly historical | overlaps parser audits | keep as reference | Warm | parser tasks |
| `docs/DEMO_STORAGE_TZ.md` | Demo storage lifecycle | active/semi-active | Storage-task only | overlaps import/storage reports | keep | Warm | storage/import tasks |
| `docs/METRICS.md` | Metric truth contract | active | Domain-task only | overlaps metrics guardian | keep | Warm | metrics tasks |
| `docs/RECOMMENDATIONS.md` | Recommendation loop rules | active | Domain-task only | overlaps recommendation audits | keep | Warm | recommendation tasks |
| `docs/AI_COACH.md` | AI provider/output truth | active | Domain-task only | overlaps AI architecture memo | keep | Warm | AI tasks |
| `docs/KNOWN_LIMITATIONS.md` | Known limits | semi-active | Must be kept aligned with current status | overlaps CURRENT_STATUS | verify/update later | Warm | release/promotion |
| `docs/RELEASE_CHECKLIST.md` | Release gates | active/semi-active | Small; public/friends gates only | overlaps security/deploy | keep | Warm | release tasks |
| `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md` | Public deploy gate | semi-active | Future only | overlaps RELEASE_CHECKLIST/SECURITY | keep | Warm/Cold | public release only |
| `docs/ROADMAP.md` | Older roadmap | historical/stale | Known stale label risk | overlaps VERSION_ROADMAP | archive or rewrite as pointer | Cold | audit only |
| `docs/VERSION_MAP.md` | Older version map | historical/stale | Known stale labels | overlaps VERSION_ROADMAP | archive or rewrite as pointer | Cold | audit only |
| `docs/CURRENT_MILESTONE.md` | Old/historical milestone detail | semi-active/stale | Older stage context; not current WP truth | overlaps CURRENT_STATUS | keep as historical evidence | Cold/Warm | audit/stage review |
| `docs/agents/*.md` | Guardian-specific rules | active | Should not be always-read | overlaps project gate hints | keep; activate by task | Warm | by changed paths/task domain |
| `docs/audit/WP_*.md` | WP evidence reports | historical evidence | Numerous and large | overlaps summaries | keep immutable/evidence-only | Cold | latest relevant only |
| `docs/audit/STAGE_*.md` | Stage evidence | historical evidence | Large historical corpus | overlaps status docs | keep evidence-only | Cold | audit only |
| `docs/audit/*_INVENTORY.md` | Domain inventories | evidence/reference | Topic-specific only | overlaps domain docs | keep | Warm/Cold | domain audit only |
| `docs/audit/DOCUMENT_CONFLICTS.md` | Docs conflict inventory | semi-active | May be stale | overlaps this report | verify in docs cleanup | Warm | docs audit |
| `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` | Deprecation policy | active for docs cleanup | Needs to drive archive actions | overlaps docs map | keep | Warm | docs cleanup |
| `docs/tasks/*.md` | Historical task prompts/specs | historical | Very large; not active roadmap | overlaps audit reports | archive/evidence-only | Cold | audit only |
| `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` | Older curation playbook | historical | 1098 lines; too large | overlaps AGENTS/PROJECT_CONTROL | archive/evidence-only | Cold | audit only |
| `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` | Older handoff manual | historical | Large; predates current WP registry | overlaps HANDOFF | archive/evidence-only | Cold | audit only |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | Prompt library | historical | Prompt drift risk | overlaps task prompts | archive/evidence-only | Cold | audit only |
| `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` | Old plan | historical | Can mislead current roadmap | overlaps roadmap/backlog | archive/evidence-only | Cold | audit only |
| `docs/PRODUCT_EXECUTION_STRATEGY.md` | Old strategy | historical | Strategy drift | overlaps roadmap | archive/evidence-only | Cold | audit only |
| `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` | AI provider memo | semi-active/historical | Older design memo | overlaps AI_COACH.md | keep reference | Warm/Cold | AI architecture only |
| `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` | Old AI/recommendation plan | historical | Long and likely stale | overlaps recommendations/AI | archive/evidence-only | Cold | audit only |
| `docs/COMPETITOR_FEATURE_MATRIX.md` | Market comparison | historical/supporting | Not execution control | none critical | keep supporting | Cold | product planning only |
| `docs/FEATURE_ROADMAP_SCORING.md` | Feature scoring | historical/supporting | Not current roadmap | overlaps roadmap | archive/evidence-only | Cold | product planning only |
| `docs/METRICS_ROADMAP_SCORING_RU.md` | Metric wishlist/scoring | historical/supporting | Not metric truth | overlaps METRICS.md | archive/evidence-only | Cold | metrics planning only |
| `instructions/*` | Legacy prompts/specs | historical | Old external prompt set, high drift risk | overlaps AGENT/docs/tasks | archive/evidence-only | Cold | audit only |
| `data/reports/*.md` | Generated app reports | production/generated data | Should not be governance context | not docs control | do not use as project docs | Cold | never unless app-report audit |
| `data/ai_handoffs/*/codex_prompt.md` | Generated AI handoff prompts | production/generated data | Not governance docs | not source of truth | do not use for control | Cold | never unless AI handoff audit |
| `backups/*.manifest.txt` | Backup manifests | operational evidence | Not docs control | backup evidence only | keep outside startup context | Cold | backup audit only |
| `scripts/project_gate.py` | Read-only governance helper | active | Does not enforce Hot/Warm/Cold yet | overlaps runbook need | keep; later add doc freshness checks | Warm | every WP command, not reading as doc |
| `docs/project_management/CODEX_WP_RUNBOOK.md` | Expected runbook | missing | Not found | N/A | consider creating or using `AGENTS.md` + `project_gate.py` | N/A | N/A |
| `docs/context/CHATGPT_BOOTSTRAP.md` | Expected ChatGPT bootstrap | missing | Not found | N/A | consider only if user wants ChatGPT handoff doc | N/A | N/A |

## 5. Hot context recommendation

Target Hot context must be small: maximum 3-4 files.

Recommended Hot files now:

1. `AGENTS.md`
   - Owns Codex role, approval authority, hard safety rules, git rules, DB/import
     restrictions and source-of-truth order.
   - Must be the only agent contract. `AGENT.md` should be superseded later.

2. `docs/CURRENT_STATUS.md`
   - Owns current product version, active/next WP, current blockers and accepted
     limitations.
   - It is too long today, but it is the best current-state file until a
     shorter `CURRENT_STATE` layer exists.

3. `docs/project_management/WP_REGISTRY.md`
   - Owns WP IDs, status, dependencies, report paths and promotion
     prerequisites.
   - This is the main guard against silent WP reuse, skipped prerequisites and
     promotion drift.

4. `docs/HANDOFF.md`
   - Owns immediate continuation context and next WP instructions.
   - It should be compressed later, but it is currently important for new chat
     recovery.

Files explicitly excluded from Hot until repaired:

- `docs/PROJECT_OS.md`: stale current version/WP and heavy mandatory workflow.
- `docs/README.md`: stale current WP.
- `docs/project_management/DOCS_INDEX.md`: stale current WP and points to
  `AGENT.md`.
- `docs/PROJECT_GOVERNANCE.md`: stale current version/WP.

Alternative after cleanup:

- Replace `docs/CURRENT_STATUS.md` + `docs/HANDOFF.md` with a shorter
  `docs/CURRENT_STATE.md` and a compact `docs/NEXT_ACTIONS.md`, but do not add
  new docs unless the user approves.

## 6. Warm context recommendation

Governance:

- `docs/PROJECT_CONTROL.md`
- `docs/project_management/DOCS_MAP.md`
- `docs/project_management/DOCS_INDEX.md` after repair
- `docs/audit/DOCUMENT_CONFLICTS.md`
- `docs/audit/DOCUMENT_DEPRECATION_PLAN.md`
- `scripts/project_gate.py`

Roadmap/planning:

- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/WP_REGISTRY.md`
- `LATER.md`

Acceptance/promotion:

- `docs/project_management/ACCEPTANCE_MATRIX.md`
- latest relevant WP reports from `docs/audit/`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/RELEASE_CHECKLIST.md`

Deploy/service:

- `docs/DEPLOYMENT.md`
- `deploy/systemd/jc-coach.service`
- `deploy/nginx/jcnodex.conf`
- `docs/agents/RUNTIME_GUARDIAN.md`
- `docs/SECURITY.md` for public/friends readiness

Testing/gates:

- `docs/TESTING.md`
- `docs/agents/TEST_GUARDIAN.md`
- `scripts/project_gate.py`
- `tests/conftest.py` when investigating test isolation

DB/data integrity:

- `docs/BACKUP_RESTORE.md`
- `docs/MIGRATIONS.md`
- `docs/agents/DB_GUARDIAN.md`
- `docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md`
- `app/config.py`, `app/db/session.py`, `app/db/models.py` when code inspection
  is in scope

Import/parser/evaluator:

- `docs/STEAM_IMPORT.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/DEMO_DEEP_PARSER_TZ_RU.md`
- `docs/STEAM_MATCH_DATES_RU.md`
- `docs/agents/IMPORT_GUARDIAN.md`
- latest relevant `WP_014*`, `WP_017*` reports only

Recommendations:

- `docs/RECOMMENDATIONS.md`
- `docs/METRICS.md`
- `docs/agents/METRICS_GUARDIAN.md`
- latest relevant `WP_016*` and recommendation reports only

UI/web routes:

- `docs/agents/UI_COACH_GUARDIAN.md`
- `docs/ARCHITECTURE.md`
- relevant `app/web`, `app/templates`, `app/static` files
- `docs/TESTING.md` for safe UI tests

Historical WP review:

- `docs/audit/WP_*.md`, but only the WPs named by `WP_REGISTRY.md` or the
  active prompt.
- `docs/audit/STAGE_*.md` only for stage history or regression archaeology.

## 7. Cold archive recommendation

Evidence-only or archive candidates:

- `AGENT.md` after `AGENTS.md` is confirmed as sole root contract.
- `WORKLOG.md`.
- `docs/tasks/*`.
- `instructions/*`.
- `docs/audit/STAGE_*`.
- Older `docs/audit/WP_*` not directly relevant to the current WP.
- `docs/audit/FULL_PROJECT_AUDIT_*`.
- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`.
- `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`.
- `docs/ROADMAP.md` and `docs/VERSION_MAP.md` unless rewritten as short
  pointers to `VERSION_ROADMAP.md`.
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`.
- `docs/PRODUCT_EXECUTION_STRATEGY.md`.
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`.
- Historical scoring/wishlist docs:
  `FEATURE_ROADMAP_SCORING.md`, `METRICS_ROADMAP_SCORING_RU.md`,
  spreadsheets.
- Generated data markdown:
  `data/reports/*.md`, `data/ai_handoffs/*/codex_prompt.md`.

Recommendation:

- Do not physically move/delete these in the next cleanup unless the user
  explicitly approves. First mark active/semi-active/historical status and fix
  entrypoints so Codex does not read them by default.

## 8. Contradictions, drift, and duplicates

Found contradictions:

- `AGENT.md` says it is canonical and must be read before any task.
  `AGENTS.md` is the newer root contract and `WP_REGISTRY.md` requires it.
- `docs/project_management/DOCS_MAP.md` still lists `AGENT.md` as canonical
  agent rules.
- `docs/PROJECT_OS.md` says current product version `v0.5`, current WP
  `WP-014 Import Acceptance`.
- `docs/README.md` says current active target is `WP-012 DB Contamination
  Guardrails`.
- `docs/project_management/DOCS_INDEX.md` says current active WP is `WP-012`.
- `docs/PROJECT_GOVERNANCE.md` says current product version is `v0.4.1`, next
  target `v0.4.2`, next WP `WP-012`.
- Current control docs in the dirty worktree say `v0.8`, next WP `WP-017K`,
  `v0.9` not promoted.
- `WP_REGISTRY.md` already reserves `WP-018` for Coach Quality Calibration, but
  this user-requested report path uses `WP_018_DOCUMENTATION_GOVERNANCE...`.
  Future cleanup must resolve the naming/registry implication explicitly.

Duplicates and overlap:

- Current state appears in `CURRENT_STATUS.md`, `HANDOFF.md`,
  `PROJECT_CONTROL.md`, `PROJECT_OS.md`, `docs/README.md`, `DOCS_INDEX.md`.
- Roadmap appears in `WP_REGISTRY.md`, `VERSION_ROADMAP.md`,
  `WORK_PACKAGE_BACKLOG.md`, `ACCEPTANCE_MATRIX.md`, `ROADMAP.md`,
  `VERSION_MAP.md`.
- Task history appears in `WP_REGISTRY.md`, `HANDOFF.md`, `CURRENT_STATUS.md`,
  `WORKLOG.md`, `CHANGELOG.md` and all audit reports.
- Safety rules appear in `AGENTS.md`, `AGENT.md`, `PROJECT_CONTROL.md`,
  `PROJECT_GOVERNANCE.md`, guardian docs and WP prompts.
- Import/demo constraints appear in `STEAM_IMPORT.md`, `DEMO_STORAGE_TZ.md`,
  `AGENTS.md`, `PROJECT_CONTROL.md`, import audits and WP prompts.

Where Codex can get confused:

- Starting from `PROJECT_OS.md`, `docs/README.md`, `DOCS_INDEX.md` or
  `PROJECT_GOVERNANCE.md` gives stale WP/version.
- Reading `AGENT.md` first causes excessive mandatory reading and ignores
  `AGENTS.md` as the newer root contract.
- Reading `ROADMAP.md` or `VERSION_MAP.md` can override newer
  `VERSION_ROADMAP.md` if source order is not enforced.
- Reading old audit reports as current truth can resurrect fixed blockers.

## 9. Missing or weak control documents

Do not add many new docs automatically. Prefer repairing existing docs first.

Weak or missing controls:

- No compact Codex WP runbook exists. `CODEX_WP_RUNBOOK.md` was not found.
  This role may be added as a small file, or folded into `AGENTS.md` plus
  `scripts/project_gate.py`.
- No `CHATGPT_BOOTSTRAP.md` or `docs/context/` was found. If ChatGPT remains
  the PM prompt author, a short bootstrap file may reduce prompt size.
- No short `CURRENT_STATE.md` exists. `CURRENT_STATUS.md` is current but long.
- No concise `NEXT_ACTIONS.md` exists. Next actions live in `HANDOFF.md`,
  `WP_REGISTRY.md` and roadmap docs.
- No concise `TASK_LOG.md` exists. `WP_REGISTRY.md` can serve this role if
  expanded carefully, but do not duplicate it unless needed.
- `DECISIONS.md` exists but is stale and does not capture recent decisions:
  root `AGENTS.md`, WP registry governance, match mode deferral, cap remains
  `1`, no playlist-specific claims in `v0.9`.

Recommended bias:

- First repair existing stale docs and source order.
- Only create new docs if they replace long always-read documents.

## 10. Recommended target control layer

Minimal canonical structure:

1. `AGENTS.md`
   - Owns: Codex operating rules, safety, source order, Hot/Warm/Cold reading
     policy, no-git-add/no-commit rules, dangerous operation confirmation.
   - Must not contain: long WP history, domain implementation details, full
     roadmap.
   - Updated when: process/safety rules change.

2. `docs/CURRENT_STATUS.md` or future compact `docs/CURRENT_STATE.md`
   - Owns: current product version, current/next WP, current blockers, accepted
     limitations, latest DB SHA if relevant.
   - Must not contain: full historical WP narrative.
   - Updated when: every WP changes current state or next action.

3. `docs/project_management/WP_REGISTRY.md`
   - Owns: WP IDs, title, status, dependencies, report path, promotion
     prerequisites, no silent ID reuse.
   - Must not contain: long evidence payloads; link reports instead.
   - Updated when: every WP opens/closes/defers/supersedes.

4. `docs/HANDOFF.md`
   - Owns: immediate continuation context, next WP, do-not-do list, recent
     blockers only.
   - Must not contain: full history since WP-014.
   - Updated when: every WP closes or operational context changes.

Warm support:

- `VERSION_ROADMAP.md`: version roadmap only.
- `WORK_PACKAGE_BACKLOG.md`: planned WP definitions only.
- `ACCEPTANCE_MATRIX.md`: acceptance gates only.
- `PROJECT_CONTROL.md`: high-level control index and policy cross-reference,
  not a duplicate of all status/history.
- `DECISIONS.md`: concise ADR-like decisions.
- Domain docs: only by task.

Cold evidence:

- Audit reports remain immutable or append-only evidence.
- Historical task specs and old prompts are not active instructions.

## 11. Recommended Codex operating rules

Rules to add or verify later in `AGENTS.md` or a runbook:

- Do not read all documentation by default.
- Always read Hot context first, maximum 3-4 files.
- Read Warm docs only when the active task requires that domain.
- Before reading additional docs, state which files are needed and why.
- One WP/task at a time.
- Do not start a new feature inside governance cleanup.
- No commit without explicit user approval.
- No `git add` without explicit user approval, unless specifically requested.
- No DB mutation without explicit user approval, backup and SHA evidence.
- No live Steam/Valve import without explicit authorization.
- No parser jobs on production data without explicit authorization.
- No manual evaluator on production DB without explicit authorization.
- No product logic changes during documentation/governance cleanup.
- After each task, write an audit/report file when the WP asks for it; do not
  rely on console-only reports for long work.
- After each task, update only relevant docs.
- After each task, provide short console summary with report path, changed
  files, checks, risks, DB impact and commit status.
- Do not silently renumber WPs.
- Do not silently close blockers.
- Do not mark a deferred/failed feature as implemented.
- Do not create new docs if an existing canonical doc should be updated.
- Do not let old audit reports override current control docs.
- Treat generated data under `data/` as production artifacts, not project docs.

## 12. Recommended audit cadence

Per-task micro-check:

- Read Hot context.
- Run `git status --short`.
- Identify task domain and Warm docs.
- Run appropriate project gates when allowed.
- Confirm no forbidden live job/DB/schema/file operation is needed.

Per-WP review:

- Verify `WP_REGISTRY.md`, current status, handoff and audit report links.
- Confirm result, warnings, next WP and blockers.
- Confirm DB SHA impact and live job status.

After 3-5 tasks:

- Small governance revision: check Hot docs alignment, stale current WP/version
  references, registry/roadmap consistency.

After 10-15 commits:

- Medium documentation review: scan roadmap/backlog/matrix/domain docs for
  drift, compress repeated history, update decisions.

Before promotion:

- Promotion readiness audit: registry prerequisites, acceptance matrix, current
  warnings, DB/import/parser/recommendation evidence, limitations.

Before DB/deploy/import changes:

- Zonal audit using relevant guardian docs and latest related audit reports.
- Require explicit authorization and backup/SHA evidence where relevant.

When repeated bugs occur:

- Incident audit: isolate current truth, stale docs, runtime state, tests and
  prevention rules before repair.

Full audit:

- Major version boundary, after docs reorganization, after serious incident, or
  when Hot/Warm/Cold rules are suspected to be stale.

## 13. Proposed implementation plan for next WP

This is only a plan. Do not execute it in this audit.

Step 1: Repair source-of-truth entrypoints.

- Confirm `AGENTS.md` replaces `AGENT.md`.
- Update stale pointers in `DOCS_MAP.md`, `DOCS_INDEX.md`, `docs/README.md`,
  `PROJECT_OS.md`, `PROJECT_GOVERNANCE.md`.
- Add explicit Hot/Warm/Cold reading rule.
- Ensure no stale file says current WP is WP-012/WP-014/v0.4.1/v0.5.

Step 2: Compress current-state flow.

- Decide whether to keep `CURRENT_STATUS.md` as the current-state file or add a
  new compact `CURRENT_STATE.md`.
- Compress `HANDOFF.md` to recent context and next WP only.
- Keep historical details in audit reports and registry links.
- Update `DECISIONS.md` with recent decisions.

Step 3: Normalize task log and roadmap.

- Use `WP_REGISTRY.md` as canonical task registry.
- Keep `VERSION_ROADMAP.md` for version sequence.
- Keep `WORK_PACKAGE_BACKLOG.md` for planned WP definitions.
- Keep `ACCEPTANCE_MATRIX.md` for acceptance gates.
- Mark `ROADMAP.md`, `VERSION_MAP.md`, old curation docs, old prompts and task
  specs as historical or archive candidates.

Expected files to modify:

- `AGENTS.md`
- `AGENT.md`
- `docs/PROJECT_OS.md`
- `docs/README.md`
- `docs/project_management/DOCS_INDEX.md`
- `docs/project_management/DOCS_MAP.md`
- `docs/PROJECT_GOVERNANCE.md`
- `docs/CURRENT_STATUS.md` or a user-approved replacement
- `docs/HANDOFF.md`
- `docs/DECISIONS.md`
- `docs/project_management/WP_REGISTRY.md`
- possibly `scripts/project_gate.py`

Expected files to archive or mark historical:

- `AGENT.md` after replacement/pointer decision.
- `docs/ROADMAP.md`
- `docs/VERSION_MAP.md`
- `WORKLOG.md`
- `docs/tasks/*`
- `instructions/*`
- older curation/playbook docs
- old full-audit/task prompt docs

Risks:

- Moving files may break links in audit reports.
- Renaming/archiving may obscure historical evidence.
- Creating too many new docs may worsen duplication.
- Updating `WP_REGISTRY.md` for this audit may collide with planned `WP-018`
  Coach Quality Calibration unless the user explicitly decides the ID policy.

Stop points needing user approval:

- Whether `AGENT.md` is deleted, moved, or replaced by a pointer.
- Whether new compact files are created (`CURRENT_STATE.md`, `NEXT_ACTIONS.md`,
  `TASK_LOG.md`, `CODEX_WP_RUNBOOK.md`, `CHATGPT_BOOTSTRAP.md`).
- Whether physical archive moves are allowed or only in-place historical labels.
- Whether `WP-018` should remain Coach Quality Calibration or this audit should
  get a distinct registry ID.
- Whether `project_gate.py` should enforce Hot/Warm/Cold freshness checks.

## 14. Questions / user decisions needed

1. Should `AGENTS.md` become the only authoritative Codex instruction file,
   with `AGENT.md` converted to a pointer or archived?
2. Should the project add a compact `docs/CURRENT_STATE.md`, or should
   `docs/CURRENT_STATUS.md` be shortened in place?
3. Should there be a separate `docs/NEXT_ACTIONS.md`, or should next actions
   remain in `HANDOFF.md` and `WP_REGISTRY.md`?
4. Should `WP_REGISTRY.md` also become the task log, or should a separate
   `TASK_LOG.md` be created?
5. Should old docs be physically moved to `docs/archive/`, or only marked
   historical in place?
6. Should this audit be registered as a real WP despite `WP-018` already being
   planned for Coach Quality Calibration, or treated as an out-of-band audit?
7. Should ChatGPT get a short bootstrap file in the repo, or should bootstrap
   remain external/user-managed?
8. Should project gates warn/fail when stale entrypoint docs contain old
   current WP/version values?
9. Should future WP prompts omit repeated safety boilerplate and rely on
   `AGENTS.md` plus a short task-specific authorization block?

## 15. Final confirmation

No application code, DB data, service config, nginx config, or product logic was
changed. Only this audit report file was created.

