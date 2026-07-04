# Project Control — CS2 AI Coach

Canonical project source of truth. Last updated: 2026-07-04.

This file overrides older README, roadmap, audit, prompt and `instructions/*` documents when they conflict. Historical files remain in the repository for context and should not be deleted until the deprecation plan in `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` is completed.

## 1. Project Goal

JC Coach is a personal CS2 coach, not a generic statistics clone. Statistics are an evidence layer for:

```text
Match -> Facts -> Metrics -> Diagnosis -> Primary Recommendation -> Evaluation -> Progress -> AI Explanation
```

The practical product question is:

1. What are my main recurring CS2 problems?
2. What evidence supports that diagnosis?
3. What should I train over the next matches/week?
4. Did my future matches improve against that recommendation?

## 2. Current Truth

Current Product Version: `v0.5`.

Current WP: `WP-014 Import Acceptance`.

Next Target Version: `v0.6`.

Current governance entrypoint: `docs/PROJECT_OS.md`.

Current handoff: `docs/HANDOFF.md`.

Governance contract: `docs/PROJECT_GOVERNANCE.md`.

The product is beyond the original `v0.1` CSV dashboard, but it is not a secure friends/public product and not a fully validated AI coach.

| Area | Canonical status | Notes |
|---|---|---|
| CSV/JSON import | Working MVP | Dedupe and missing-column tolerance exist. |
| Manual official `.dem` import | Working, partial confidence | `demoparser2` import works; parsed evidence exists; some metrics remain best-effort. |
| Deep DEM parser | Working foundation | Normalized parser tables and `swing_score` exist; raw `.dem` is still retained. |
| Steam import | Working alpha path, WP-014B1/B2 truth repaired | OpenID + Game Authentication Code + latest share-code cursor + service bot demo URL resolver. Cursor source/advance/outcome semantics are explicit and tested with mocked paths. `steam_import_all` records standardized `result_json` outcomes/statuses and avoids clean success for missing-code/download/parser/partial cases. Primary Steam match date is exact only from Steam GC `match_time`; unavailable GC dates are marked unknown instead of using file mtime as truth. Demo cleanup lifecycle and failed-demo quarantine policy still block `v0.6` acceptance. |
| FACEIT import | Future | Do not implement before Steam/security/parser hardening unless explicitly reprioritized. |
| Dashboard/matches/stats | Working personal MVP runtime; WP-013 `PASS_WITH_WARNINGS` | `/coach` now surfaces current tracked recommendation, next action, evidence/confidence, Metric Truth warnings, latest match summary and AI validation status. Runtime restart and read-only smoke passed; full owner manual checklist remains operator evidence to record. |
| Mistake detection | Partial | Rule-based, hardcoded thresholds, confidence not fully enforced. |
| Recommendations | Partial working loop, Stage 4 read/write split exists | Multi-category goals, lifecycle, evaluations and progress exist. GET/read paths no longer create recommendations/evaluations. Recommendations are not yet consistently generated from top verified problem snapshots. |
| Metrics | Metric Truth Layer exists, Stage 5 `PASS_WITH_WARNINGS`; parser confidence Stage 6 `PASS_WITH_WARNINGS` | Runtime registry defines source/formula/reliability/usage policy. Parser no longer silently maps early deaths to entry deaths; trade/side/utility facts still need deeper validation before weak metrics can be upgraded. |
| AI coach | Partial, Stage 8 `PASS_WITH_WARNINGS` | Codex handoff, local LLM scaffold, payload snapshots and saved AI reports exist. Structured AI output validator rejects unsupported metric claims and falls back safely; prompt versioning/provider structured mode remain future work. |
| Auth/security | Personal/VPS only, Stage 1 + Stage 2 app hardening exist | App-level API auth, CSRF, MVP rate limits, strong secret fail-fast, Steam OpenID verification and enforced single-owner mode exist. Stage 2 is `PASS_WITH_WARNINGS`: this is not full multi-user ownership, and legacy `link_steam_account(..., user_id=None)` remains a later Steam hardening risk. Observability remains a blocker for friends/public use. |
| DB/migrations | WP-012 guardrails completed; Stage 3 scaffold exists, not full Alembic | Production DB test/smoke contamination guardrails exist; migration policy, schema inventory and safe copy-check tooling exist. Alembic baseline and migration ledger are not implemented yet. |
| Demo storage lifecycle | Observe-only | Storage report and manifest exist. Raw `.dem` deletion is disabled until parsed payload verification is defined and implemented. |

## 3. Current Milestone

Current Product Version: `v0.5`.

Current WP: `WP-014 Import Acceptance`.

Next Target Version: `v0.6`.

Previous stabilization stages remain historical evidence for the product state. WP-012 DB Contamination Guardrails and WP-013 Personal MVP Runtime Smoke Gate are complete with warnings. The immediate next pass should accept import workflows without live-job ambiguity.

Canonical milestone doc: `docs/CURRENT_MILESTONE.md`.

Current focus:

1. Заморозить scope вокруг security, metric truth, parser verification и recommendation planner.
2. Подтвердить test isolation и backup/restore до рискованных проверок.
3. Закрыть Security P0 до friends/public use. Stage 1 covers API auth, CSRF, MVP rate limits, strong secrets and Steam OpenID verification.
4. Stage 2 Ownership / enforced single-owner boundaries: completed / `PASS_WITH_WARNINGS`.
5. Stage 3 Migration discipline: completed / `PASS_WITH_WARNINGS` scaffold.
6. Stage 4 Recommendation read/write split: completed / `PASS_WITH_WARNINGS`.
7. Stage 5 Metric Truth Layer: completed / `PASS_WITH_WARNINGS`.
8. Stage 6 Parser facts & confidence hardening: completed / `PASS_WITH_WARNINGS`.
9. Stage 7 Steam cursor truth: completed / `PASS_WITH_WARNINGS`.
10. Stage 8 AI Output Validator: completed / `PASS_WITH_WARNINGS`.
11. Stage 9 Coach-first UI: completed / `PASS_WITH_WARNINGS`.
12. Генерировать рекомендации из verified problem evidence.

## 4. Source-of-truth Documents

| Topic | Canonical document | Notes |
|---|---|---|
| Product status | `docs/CURRENT_STATUS.md` | Current fact state. |
| Project OS | `docs/PROJECT_OS.md` | Short entrypoint for new Codex passes. |
| Handoff | `docs/HANDOFF.md` | Current state and next-chat continuation context. |
| Governance | `docs/PROJECT_GOVERNANCE.md` | Versioning, WP gates, roles and safety policies. |
| Version roadmap | `docs/project_management/VERSION_ROADMAP.md` | Planned version-to-WP sequence from `v0.4.2` to `v1.0`. |
| Work package backlog | `docs/project_management/WORK_PACKAGE_BACKLOG.md` | WP objectives, guardians, acceptance and exit criteria. |
| Acceptance matrix | `docs/project_management/ACCEPTANCE_MATRIX.md` | Feature acceptance checks by version and guardian. |
| Docs map | `docs/project_management/DOCS_MAP.md` | Documentation ownership, source-of-truth and stale-risk map. |
| Version status | `docs/VERSION_MAP.md` | Version/milestone readiness map. |
| Current milestone | `docs/CURRENT_MILESTONE.md` | Active work and frozen scope. |
| Roadmap | `docs/ROADMAP.md` | Ordered development under this file. |
| Architecture | `docs/ARCHITECTURE.md` | System shape and boundaries. |
| Metrics | `docs/METRICS.md` | Runtime metric truth contract. |
| Recommendations | `docs/RECOMMENDATIONS.md` | Coach-loop and planner rules. |
| Security | `docs/SECURITY.md` | Friends/public gate. |
| Steam import | `docs/STEAM_IMPORT.md` | Steam import current truth. |
| AI coach | `docs/AI_COACH.md` | AI provider/output rules. |
| Testing | `docs/TESTING.md` | Safe verification commands. |
| Deployment | `docs/DEPLOYMENT.md` | Deployment status and gates. |
| Backup/restore | `docs/BACKUP_RESTORE.md` | Operational gap/runbook placeholder. |
| Migrations | `docs/MIGRATIONS.md` | Migration discipline and safe copy-check policy. |
| Decisions | `docs/DECISIONS.md` | Current decisions. |
| Changelog | `docs/CHANGELOG.md` | Curated documentation/product changes. |
| Limitations | `docs/KNOWN_LIMITATIONS.md` | Known non-readiness areas. |
| Release checklist | `docs/RELEASE_CHECKLIST.md` | Personal/friends/public gates. |
| Audit inventory | `docs/audit/INSTRUCTIONS_INVENTORY.md` | Document inventory. |
| Audit conflicts | `docs/audit/DOCUMENT_CONFLICTS.md` | Conflict map. |
| Deprecation plan | `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` | Historical-doc handling. |

## 5. Frozen Scope

Until the current milestone closes, do not prioritize:

- FACEIT sync.
- Viewer, heatmaps, clips or practice servers.
- Payments, social features or public share pages.
- Broad UI polish that does not support the coach loop.
- Raw `.dem` deletion.
- Fully automated production LLM flow before structured AI validation.

## 6. Codex Working Rules

Before task work, Codex must read:

1. `AGENT.md`
2. `docs/PROJECT_CONTROL.md`
3. `docs/PROJECT_OS.md`
4. `docs/HANDOFF.md`
5. `docs/CURRENT_MILESTONE.md`
6. `docs/project_management/WORK_PACKAGE_BACKLOG.md`
7. Relevant domain spec from the source-of-truth table

Codex should run `python scripts/project_gate.py preflight`, `changed`, `required-checks` and `postflight` around work packages when shell access is available. Activated guardian docs under `docs/agents/` must be read before touching their domains.

For future roadmap sequencing, use `docs/project_management/VERSION_ROADMAP.md` and `docs/project_management/WORK_PACKAGE_BACKLOG.md`. Older stage roadmaps remain historical evidence unless explicitly reactivated.

Older `instructions/*`, roadmap, prompt and audit files are historical/supporting unless explicitly reactivated here.

## 7. Definition Of Done

For product/code changes:

- The change follows current milestone scope.
- Tests or safe verification are run and reported.
- Metrics/AI/recommendation behavior does not claim more confidence than source data supports.
- Docs are updated when current truth, architecture, security posture or roadmap changes.
- No generated data, secrets, raw demos or credentials are committed.

For documentation changes:

- Inventory/conflict implications are considered first.
- Canonical docs are updated before marking old docs historical.
- Historical docs are not deleted without the deprecation plan.

## 8. How To Add New Work

1. Check whether the work fits `docs/CURRENT_MILESTONE.md`.
2. If it expands scope, add it to `LATER.md` or `docs/ROADMAP.md` unless the user explicitly reprioritizes.
3. Identify the canonical domain doc to update.
4. Add acceptance criteria and verification method.
5. Avoid implementing features that depend on unclosed security/metric/parser blockers.

## 9. How To Close A Milestone

1. Verify every done criterion in `docs/CURRENT_MILESTONE.md`.
2. Update `docs/CURRENT_STATUS.md`.
3. Update `docs/VERSION_MAP.md`.
4. Update `docs/ROADMAP.md`.
5. Add a `docs/CHANGELOG.md` entry.
6. Review deprecation/archive candidates if the milestone changed documentation truth.

## Non-Negotiable Constraints

- Do not ask for or store a user's Steam password, Steam Guard QR approval, Steam refresh token, or personal Steam credentials.
- Do not delete raw `.dem` files until `parsed_payload_verified` and retention policy are implemented.
- Do not commit `.env`, DB files, raw demos, generated reports, handoff files, bot credentials, refresh tokens, or `node_modules`.
- Do not claim friends/public readiness until API auth, user ownership, CSRF/rate limits, strong session secret enforcement, migrations, backup and observability are handled.
- Do not present best-effort metrics as reliable facts. Early deaths, side splits, KAST/trade logic, utility attribution, accuracy and crosshair/position metrics need explicit confidence/gap labels.
- Do not add viewer, clips, heatmaps, practice servers, payments, social features or broad UI polish before the hardening priorities below.

## Current Architecture Decisions

### AI Provider

Default provider is `codex_cli_handoff`: the app builds structured facts and prompt files for a human-in-the-loop Codex flow. `local_llm` exists as a scaffold for Ollama/LM Studio/OpenAI-compatible local servers.

AI must reason over deterministic payloads. It must not parse demos or invent missing stats. Next AI hardening is prompt/version tracking and provider-specific structured response enforcement.

Stage 8 AI validation policy:

- accepted structured output has `summary`, `diagnoses[]`, `recommendations[]`, `warnings[]`, `evidence[]`, `confidence`;
- unknown metric ids are rejected;
- suppressed/unavailable Metric Truth ids cannot support diagnosis/recommendation claims;
- approximate/warn metrics require caveats;
- invalid or free-form output is replaced by safe fallback Markdown before persistence/display.

### Steam Import

Accepted flow:

1. User signs in with Steam OpenID.
2. User saves Game Authentication Code and latest `CSGO-...` share-code cursor from Steam Support.
3. Server-side Steam Web API key is configured by the operator.
4. Dedicated service bot resolves known share codes through CS2 Game Coordinator.
5. The app downloads `.dem.bz2`, decompresses to `.dem`, imports through parser, and stores Steam GC `match_time` as authoritative `played_at`.

Service bot cannot enumerate private user history by itself. The app must diagnose stale cursors and must not convert the UX into manual share-code input for every match.

Stage 7 cursor truth policy:

- `SteamAccount.last_share_code` is the current saved cursor source of truth.
- A job payload `known_share_code` may override the saved cursor for that job only.
- `knowncode=0` is allowed only as an explicit initial sentinel when no saved cursor exists.
- A match-history sync advances `last_share_code` only after Steam collection and local share-code persistence complete successfully.
- Failed Steam/API/import persistence paths do not advance the cursor.
- No-new, duplicate, missing-code, disconnected-Steam, rate-limit, download-failed, parser-failed, partial-success, exact-date availability and approximate/unavailable match-date outcomes are represented in `ImportJob.result_json`.
- Primary Steam freshness checks use only exact imported Steam dates (`steam_gc_match_time`); parser/file-mtime fallback dates must not block new Steam imports.
- `ImportJob.status` still supports only `queued`, `running`, `succeeded` and `failed`; partial success is represented in `result_json` and persisted as `failed` until a schema/status migration is explicitly approved.

### Demo Storage

Target lifecycle:

```text
download -> parse -> verify parsed payload -> delete raw .dem
```

Current lifecycle is observe-only:

- raw demos stay in `data/uploads`;
- `/settings/storage` and `GET /api/storage/demos` report storage state;
- manifest can be written to `data/reports/demo_storage_manifest.json`;
- current explicit policy is `retain_raw_for_parser_development`;
- import metadata records retention status/path/size where available;
- no delete/compress/archive action is enabled by default.

## Supporting Runtime Documentation

Use these files as supporting docs under this control file:

| Topic | Supporting file |
|---|---|
| Latest user-facing setup/API overview | `README.md` |
| Engineering journal | `WORKLOG.md` |
| Implemented features | `docs/FEATURES_RU.md` |
| Steam architecture | `docs/STEAM_IMPORT_ARCHITECTURE.md` |
| Steam match date policy | `docs/STEAM_MATCH_DATES_RU.md` |
| DEM parser and raw-delete readiness | `docs/DEMO_DEEP_PARSER_TZ_RU.md`, `docs/DEMO_STORAGE_TZ.md` |
| Metrics roadmap | `docs/METRICS_ROADMAP_SCORING_RU.md` |
| Feature roadmap scoring | `docs/FEATURE_ROADMAP_SCORING.md` |
| Security/product audit | `docs/audit/CS2_AI_COACH_AUDIT_2026-07-02.md` |
| Documentation summary audit | `docs/DOCUMENTATION_AUDIT.md` |
| Documentation inventory/conflicts/deprecation | `docs/audit/INSTRUCTIONS_INVENTORY.md`, `docs/audit/DOCUMENT_CONFLICTS.md`, `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` |

## Priority Backlog

### P0: Secure Personal/Friends Alpha Prep

1. Изолировать тесты от production DB/settings.
2. Задокументировать и проверить backup/restore до рискованных проверок.
3. Закрыть non-health `/api/*` endpoints auth-ом или явной API token policy.
4. Добавить user ownership или объявленный/принудительный single-user mode для matches, recommendations, reports, Steam accounts и jobs. Stage 2 completed this as enforced single-owner mode / `PASS_WITH_WARNINGS`, not full multi-user ownership.
5. Добавить CSRF protection или эквивалентное same-site/state-change hardening.
6. Требовать strong `SESSION_SECRET_KEY` вне local development.

### P1: Metric Truth Layer

1. Create a definitive runtime metric spec with formula, source, confidence and suppression rule for every displayed/diagnostic metric.
2. Suppress weak metrics from diagnosis when sample size or parser confidence is insufficient.
3. Harden early-death timing, KAST/trade/traded-death logic, side switching and utility attribution.
4. Add `parsed_payload_verified` status before any raw demo retention policy.

### P1: Recommendation Planner

1. Produce top verified problems with evidence and confidence.
2. Create one primary active recommendation from the top problem snapshot.
3. Keep secondary category goals only when they do not dilute focus.
4. Separate read helpers from write/evaluation side effects.

### P1: Steam Worker Hardening

1. Add durable scheduler/retry/backoff model.
2. Expose cursor freshness diagnostics clearly in `/settings/imports`.
3. Skip or warn on old cursor history relative to latest imported match.
4. Keep Steam GC match time as authoritative for Steam imports.

### P2: Coach UX

1. Make next action and primary recommendation first-screen on dashboard/coach.
2. Show evidence links from recommendation to match/metric/problem.
3. Add latest-match coach summary after parser confidence improves.
4. Reduce metric overload with confidence-aware grouping.

## Documentation Rules

- Update this file when project status, architecture decisions, priority order, or hard constraints change.
- README should stay an operator/user entrypoint and link here for truth, not duplicate all strategy.
- `WORKLOG.md` records chronological engineering actions; it is not a current-state contract.
- `instructions/*` are historical prompt/TZ artifacts unless explicitly reactivated in this file.
- Roadmap/scoring docs can rank ideas, but their percentages are subordinate to this file and the latest audit.
- Any old document that contradicts this file should receive a historical/deprecated notice, not be deleted immediately.
