# Audit Findings By Layer

Date: 2026-07-06.

Primary source: `docs/audits/2026-07-06-agentic-readiness-audit`.

## Agentic Development Core

- Readiness score: 4.0/5, 80%.
- Assessment: strong written governance, weak automated enforcement.
- Key findings: root `AGENTS.md`, Hot/Warm/Cold context, WP registry, role
  cards, invocation modes and control-plane protection exist; rules remain
  mostly manual.
- Evidence source: audit `00_EXECUTIVE_SUMMARY.md`, "Layer Scores" and "Top 10
  High-Risk Gaps"; audit `02_LAYER_READINESS.md`, "Layer 1"; audit matrix
  AR-001 through AR-016.
- Impact on CS2 development: safe for small scoped work, unsafe for long-running
  multi-agent expansion without enforceable gates.
- Risk level: HIGH for enforcement drift, MEDIUM otherwise.
- Must fix before major feature work: AR-009 project gate pre/postflight,
  AR-015 structured risk register, AR-016 CI/pre-commit or mandatory gate.

## Web Application Core

- Readiness score: 3.0/5, 60%.
- Assessment: usable controlled personal app; schema and job architecture are
  the main risks.
- Key findings: FastAPI/Jinja/SQLAlchemy/SQLite stack is working; startup still
  uses `Base.metadata.create_all()` plus legacy `_upgrade_sqlite_schema()`;
  BackgroundTasks are not durable enough for import-scale work.
- Evidence source: audit `02_LAYER_READINESS.md`, "Layer 2"; audit
  `04_ARCHITECTURE_CODEBASE.md`, "Findings" and "Risks"; audit matrix AR-017
  through AR-030.
- Impact on CS2 development: schema or import-scale features can damage
  production safety if started before migration/job hardening.
- Risk level: BLOCKER for schema work, HIGH for import cap raise.
- Must fix before major feature work: migration baseline/schema diff gate
  (AR-019, AR-026), API contract inventory (AR-018), durable worker/retry ledger
  design before cap raise (AR-029).

## AI Coach Product Archetype

- Readiness score: 3.1/5, 62%.
- Assessment: tracking and validation exist; planning and eval foundation is
  missing.
- Key findings: recommendation tracking, metric confidence and AI output
  validator are real; diagnosis registry, top verified problem selector,
  planner, prompt/payload versioning and semantic evals are missing.
- Evidence source: audit `02_LAYER_READINESS.md`, "Layer 3"; audit
  `05_DATA_METRICS_AI_COACH.md`, "Findings" and "Gaps"; audit matrix AR-031
  through AR-042.
- Impact on CS2 development: adding new coach intelligence before this layer is
  hardened risks schema-valid but semantically wrong advice.
- Risk level: BLOCKER for major recommendation intelligence.
- Must fix before major feature work: diagnosis registry/planner (AR-033),
  advice confidence/explainability contract (AR-036, AR-037),
  prompt/payload versioning (AR-038), semantic AI evals (AR-039).

## CS2 Domain Pack

- Readiness score: 2.9/5, 58%.
- Assessment: honest caveats exist; several CS2 concepts are absent or too weak
  for hard coaching claims.
- Key findings: match/round/parser models and Metric Truth suppression exist;
  economy, positioning, clutch definitions, canonical map registry, sample-size
  policy and glossary are missing or incomplete.
- Evidence source: audit `02_LAYER_READINESS.md`, "Layer 4"; audit
  `05_DATA_METRICS_AI_COACH.md`, "Gaps"; audit matrix AR-043 through AR-056.
- Impact on CS2 development: unsupported CS2 facts must not become hard
  recommendations, filters or claims.
- Risk level: HIGH for overclaiming, MEDIUM for docs gaps.
- Must fix before major feature work: sample-size thresholds (AR-055), source
  limits in UI/coach output (AR-054), CS2 domain pack/map/glossary/unavailable
  model doc (AR-043, AR-044, AR-049, AR-051, AR-052, AR-056).

## Project Instance

- Readiness score: 3.5/5, 70%.
- Assessment: current status and roadmap are strong; historical docs and runtime
  artifacts still add noise.
- Key findings: `CURRENT_STATUS`, `WP_REGISTRY` and roadmap docs are current;
  `PROJECT_INDEX.md` is absent but `DOCS_INDEX.md`/`DOCS_MAP.md` serve as the
  practical index; runtime DB/demos/backups/secrets-adjacent files exist locally
  and require discipline.
- Evidence source: audit `02_LAYER_READINESS.md`, "Layer 5"; audit
  `03_DOCS_AND_CONTEXT.md`, "Findings" and "Risks"; audit matrix AR-057 through
  AR-098; audit evidence `docs_inventory.txt` and `file_inventory.txt`.
- Impact on CS2 development: agents can proceed only if Hot/Warm/Cold source
  hierarchy is respected and runtime artifacts remain uncommitted.
- Risk level: MEDIUM overall, HIGH for source trust/global DB state.
- Must fix before major feature work: structured risk register (AR-015/AR-060),
  schema contract (AR-067), golden metric fixtures (AR-069, AR-087), source trust
  registry (AR-072), hidden global DB import-order guard (AR-081).

## Runtime / Tooling / CI / Ops

- Readiness score: Runtime Layer 4.1/5, 82%; tooling/CI gaps remain.
- Assessment: audit execution was disciplined; repeatable automated enforcement
  is incomplete.
- Key findings: audit ran safe tests and stored evidence; no CI workflow or
  pre-commit was discovered; `python scripts/project_gate.py changed` failed
  because `python` was not on PATH while `.venv/bin/python` passed.
- Evidence source: audit `02_LAYER_READINESS.md`, "Layer 6"; audit
  `06_TESTS_EVALS_QUALITY.md`, "Checks Run"; audit evidence
  `test_results.txt`; audit matrix AR-090, AR-099 through AR-106.
- Impact on CS2 development: quality gates can be skipped or run inconsistently
  unless wrapped in one mandatory command.
- Risk level: HIGH for long-running agentic development.
- Must fix before major feature work: CI or mandatory local gate (AR-016,
  AR-090), project_gate command standardization (AR-009).

## Documentation / Knowledge / State

- Readiness score: included in Agentic Development Core and Project Instance.
- Assessment: current source-of-truth docs are strong; old docs are classified
  but numerous.
- Key findings: Hot/Warm/Cold classification is strong; `KNOWN_LIMITATIONS` is
  useful but not a full risk register; old audit/task/instruction files remain
  evidence/history.
- Evidence source: audit `03_DOCS_AND_CONTEXT.md`; audit matrix AR-003, AR-013,
  AR-014, AR-015, AR-058, AR-065.
- Impact on CS2 development: wrong context loading can resurrect stale plans or
  unsupported features.
- Risk level: MEDIUM, HIGH if source hierarchy is ignored.
- Must fix before major feature work: risk register, docs update checklist,
  hardening plan pointers in canonical docs.

## Data / Metrics / AI Logic

- Readiness score: Data/AI concerns appear across AI Coach Archetype, CS2 Domain
  Pack and Project Instance.
- Assessment: Metric Truth is a real guardrail; reproducibility and policy
  contracts need hardening.
- Key findings: stable metric IDs/formulas/reliability exist; validator blocks
  unavailable/suppressed metrics; broader golden aggregate fixtures,
  source-trust registry, sample-size thresholds and prompt/payload versioning
  are incomplete.
- Evidence source: audit `05_DATA_METRICS_AI_COACH.md`; audit matrix AR-036,
  AR-038, AR-055, AR-068, AR-069, AR-072, AR-073, AR-076, AR-087, AR-088.
- Impact on CS2 development: coach outputs can become overconfident on weak,
  small or non-reproducible inputs.
- Risk level: HIGH.
- Must fix before major feature work: source trust/sample-size policy,
  reproducible payload/version snapshots, golden metric and semantic AI evals.

## Tests / Evals / Quality Gates

- Readiness score: no separate layer score; audit checks passed but missing
  eval/contract/CI depth.
- Assessment: current unit/integration test base is useful; semantic evals,
  contract tests and automated gate enforcement are insufficient.
- Key findings: `211 passed, 1 warning`; Ruff passed; `git diff --check`
  passed; no CI/pre-commit; E2E/browser tests and API contract tests are limited
  or absent.
- Evidence source: audit `06_TESTS_EVALS_QUALITY.md`; audit evidence
  `test_results.txt`; audit matrix AR-083 through AR-090.
- Impact on CS2 development: regressions and schema-valid hallucinations may
  slip through during major feature work.
- Risk level: HIGH for AI/metrics, MEDIUM for UI/API.
- Must fix before major feature work: semantic AI evals, golden metric fixtures,
  contract tests for critical endpoints, mandatory gate.

## Security / Permissions / Safety

- Readiness score: security baseline contributes to Web Application Core and
  Project Instance.
- Assessment: acceptable for controlled personal/VPS use only.
- Key findings: auth, owner boundary, CSRF, API auth, secret fail-fast and
  in-memory rate limiting exist; public/friends exposure remains blocked; data
  privacy/retention is not ready for sharing.
- Evidence source: audit `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`, "Security";
  audit matrix AR-027, AR-095, AR-097, AR-098.
- Impact on CS2 development: friends/public, sharing and remote access expansion
  remain forbidden until security/privacy/ops gates close.
- Risk level: HIGH for any access expansion.
- Must fix before major feature work: public-readiness stays explicitly blocked,
  secret redaction policy in gates, data privacy/retention policy before
  sharing.

