# Audit Matrix

Total rows: 106. Full canonical machine-readable matrix is `01_AUDIT_MATRIX.csv`.

| ID | Layer | Category | Audit Item | Score | Criticality | Evidence | Recommended Action |
|---|---|---|---|---:|---|---|---|
| AR-001 | Layer 1 Agentic Development Core | Source of truth | Root agent contract | 5/5 | LOW | AGENTS.md; AGENT.md; docs/CURRENT_STATUS.md | Keep AGENTS.md protected and compact. |
| AR-002 | Layer 1 Agentic Development Core | Source of truth | Source-of-truth hierarchy | 5/5 | LOW | AGENTS.md; docs/project_management/PROJECT_OPERATING_PROTOCOL.md | Maintain hierarchy in docs updates. |
| AR-003 | Layer 1 Agentic Development Core | Context | Context loading protocol | 5/5 | LOW | AGENTS.md; docs/HANDOFF.md; docs/project_management/DOCS_INDEX.md; docs/project_management/DOCS_MAP.md | Keep old docs classified. |
| AR-004 | Layer 1 Agentic Development Core | Roles | PM/Execution/Reviewer/QA roles | 4/5 | LOW | docs/project_management/AGENT_WORKFLOW.md; docs/agents/roles/* | Add examples of role handoff artifacts in future WPs. |
| AR-005 | Layer 1 Agentic Development Core | Lifecycle | Task lifecycle | 4/5 | MEDIUM | docs/project_management/AGENT_WORKFLOW.md; docs/project_management/PROJECT_OPERATING_PROTOCOL.md | Add a scripted WP close checklist. |
| AR-006 | Layer 1 Agentic Development Core | Task templates | Task card contract | 4/5 | LOW | docs/project_management/AGENT_WORKFLOW.md | Use in every future WP prompt. |
| AR-007 | Layer 1 Agentic Development Core | Permissions | Permission matrix | 4/5 | MEDIUM | docs/project_management/AGENT_WORKFLOW.md; AGENTS.md | Add preflight prompt lint/checklist. |
| AR-008 | Layer 1 Agentic Development Core | Safe modes | Safe modes | 4/5 | LOW | docs/project_management/AGENT_WORKFLOW.md | Keep mode in every WP task card. |
| AR-009 | Layer 1 Agentic Development Core | Tool registry | Tool registry / command gates | 3/5 | MEDIUM | scripts/project_gate.py; docs/TESTING.md | Expand project_gate into explicit task preflight/postflight command. |
| AR-010 | Layer 1 Agentic Development Core | Definition of Done | Definition of Done | 4/5 | MEDIUM | docs/project_management/AGENT_WORKFLOW.md; AGENTS.md | Create checklist template in reports. |
| AR-011 | Layer 1 Agentic Development Core | Review protocol | Review protocol | 4/5 | LOW | docs/agents/roles/QA_REVIEWER.md | Keep findings-first reviews. |
| AR-012 | Layer 1 Agentic Development Core | Git discipline | Git/diff control | 4/5 | LOW | AGENTS.md; evidence/git_status.txt; evidence/test_results.txt | Make dirty-worktree handling explicit in audit/report tasks. |
| AR-013 | Layer 1 Agentic Development Core | Memory/state | State/current status | 5/5 | LOW | docs/CURRENT_STATUS.md; docs/HANDOFF.md; docs/project_management/WP_REGISTRY.md | Keep compacting every 3-5 WPs. |
| AR-014 | Layer 1 Agentic Development Core | Docs policy | Documentation update policy | 4/5 | MEDIUM | docs/project_management/PROJECT_OPERATING_PROTOCOL.md; docs/project_management/AGENT_WORKFLOW.md | Add docs update checklist to WP report template. |
| AR-015 | Layer 1 Agentic Development Core | Risk management | Risk register | 3/5 | HIGH | docs/KNOWN_LIMITATIONS.md; docs/CURRENT_STATUS.md | Create canonical risk register or extend Known Limitations with owner/status/target WP. |
| AR-016 | Layer 1 Agentic Development Core | Automation | Automated enforcement of agent rules | 2/5 | HIGH | scripts/project_gate.py; NOT_FOUND:.github; NOT_FOUND:.pre-commit-config.yaml | Add CI/pre-commit or mandatory gate script workflow. |
| AR-017 | Layer 2 Web Application Core | Architecture | Frontend/backend/API boundaries | 3/5 | MEDIUM | docs/ARCHITECTURE.md; app/main.py; app/api/routes.py; app/web/routes.py | Expand architecture map with modules, data flow and mutation boundaries. |
| AR-018 | Layer 2 Web Application Core | API contracts | API contract documentation | 2/5 | MEDIUM | README.md; app/api/routes.py; NOT_FOUND:api_contracts | Add API contract inventory and smoke/contract tests for core endpoints. |
| AR-019 | Layer 2 Web Application Core | Database | Database boundaries | 3/5 | HIGH | app/db/models.py; app/db/session.py; AGENTS.md; docs/MIGRATIONS.md | Replace legacy schema upgrade path with migration baseline. |
| AR-020 | Layer 2 Web Application Core | Auth/session | Auth/session model | 4/5 | MEDIUM | app/main.py; app/services/auth.py; docs/SECURITY.md; tests/test_auth.py; tests/test_security.py | Add explicit owner state/config and harden multi-record edge cases. |
| AR-021 | Layer 2 Web Application Core | Validation | Input validation | 3/5 | MEDIUM | app/api/routes.py; app/web/routes.py; app/services/importer.py; tests/test_importer.py | Add route-level validation inventory for mutating endpoints. |
| AR-022 | Layer 2 Web Application Core | Errors | Error handling | 3/5 | MEDIUM | app/api/routes.py; docs/STEAM_IMPORT.md; docs/CURRENT_STATUS.md | Create job error taxonomy and result_json schema doc. |
| AR-023 | Layer 2 Web Application Core | Logging | Logging policy | 3/5 | MEDIUM | docs/SECURITY.md; app/services/security.py | Add logging/observability runbook and event inventory. |
| AR-024 | Layer 2 Web Application Core | Deployment | Deployment docs/config | 3/5 | MEDIUM | docs/DEPLOYMENT.md; deploy/systemd/jc-coach.service; deploy/nginx/jcnodex.conf; Dockerfile; docker-compose.yml | Add deploy verification checklist with live-vs-repo config comparison. |
| AR-025 | Layer 2 Web Application Core | Environments | Environment docs | 3/5 | MEDIUM | .env.example; .gitignore; README.md; evidence/commands_run.txt | Create safe env reference with required/optional vars and no values. |
| AR-026 | Layer 2 Web Application Core | Migrations | Migration system | 2/5 | BLOCKER | docs/MIGRATIONS.md; app/db/session.py; pyproject.toml | Adopt Alembic or equivalent baseline before schema features. |
| AR-027 | Layer 2 Web Application Core | Security | Security baseline | 4/5 | HIGH | docs/SECURITY.md; app/main.py; tests/test_security.py; tests/test_ownership.py | Do not expand access until release security gates pass. |
| AR-028 | Layer 2 Web Application Core | Performance | Performance readiness | 3/5 | MEDIUM | docs/CURRENT_STATUS.md; docs/KNOWN_LIMITATIONS.md; docs/audit/WP_017H_POST_BATCH_PERFORMANCE_ACCEPTANCE_REPORT.md | Add performance budget and benchmark command for /coach and stats. |
| AR-029 | Layer 2 Web Application Core | Background jobs | Worker/job architecture | 2/5 | HIGH | app/api/routes.py; app/web/routes.py; app/db/models.py; docs/KNOWN_LIMITATIONS.md | Design durable worker/retry ledger before cap raise. |
| AR-030 | Layer 2 Web Application Core | Static/frontend | Frontend architecture | 3/5 | MEDIUM | app/templates; app/static/app.css; tests/test_web_smoke.py; tests/test_coach_first_ui.py | Add route/template inventory and targeted UI acceptance tests. |
| AR-031 | Layer 3 AI Coach Product Archetype | Model | Generic coach model | 3/5 | HIGH | docs/RECOMMENDATIONS.md; app/db/models.py | Create AI Coach archetype model doc separate from CS2 domain pack. |
| AR-032 | Layer 3 AI Coach Product Archetype | User goals | User goals | 4/5 | MEDIUM | app/db/models.py; app/services/recommendation_tracking.py; docs/RECOMMENDATIONS.md | Keep only one primary accepted focus until planner exists. |
| AR-033 | Layer 3 AI Coach Product Archetype | Recommendations | Recommendation generation | 2/5 | BLOCKER | docs/RECOMMENDATIONS.md; docs/KNOWN_LIMITATIONS.md; app/services/recommendation_tracking.py | Build diagnosis registry and planner in WP-018/next. |
| AR-034 | Layer 3 AI Coach Product Archetype | Progress | Progress tracking | 4/5 | MEDIUM | app/db/models.py; app/services/recommendation_tracking.py; docs/CURRENT_STATUS.md | Calibrate progress wording and sample confidence. |
| AR-035 | Layer 3 AI Coach Product Archetype | Execution check | Checking recommendation execution | 4/5 | MEDIUM | tests/test_recommendation_tracking.py; tests/test_recommendation_read_write_split.py; app/services/recommendation_tracking.py | Keep metric_confidence mandatory in evaluations. |
| AR-036 | Layer 3 AI Coach Product Archetype | Confidence | Confidence model | 4/5 | MEDIUM | docs/METRICS.md; app/services/metric_truth.py; app/services/metric_confidence.py; docs/AI_COACH.md | Create coach advice confidence contract. |
| AR-037 | Layer 3 AI Coach Product Archetype | Explainability | Explainability | 3/5 | HIGH | docs/AI_COACH.md; app/db/models.py; docs/RECOMMENDATIONS.md | Add evidence link model from problem -> metric -> match -> recommendation. |
| AR-038 | Layer 3 AI Coach Product Archetype | Prompts | AI prompt/payload versioning | 2/5 | HIGH | docs/AI_COACH.md; app/services/ai_coach.py | Add prompt_version and payload_version to handoff/result metadata. |
| AR-039 | Layer 3 AI Coach Product Archetype | AI evals | AI evals | 2/5 | HIGH | tests/test_ai_validator.py; docs/AI_COACH.md; NOT_FOUND:evals | Add small golden AI-output eval suite. |
| AR-040 | Layer 3 AI Coach Product Archetype | Hallucination prevention | Hallucination prevention | 4/5 | MEDIUM | app/services/ai_validator.py; tests/test_ai_validator.py; docs/AI_COACH.md | Add provider structured-response enforcement. |
| AR-041 | Layer 3 AI Coach Product Archetype | Fallback | Fallback behavior | 4/5 | LOW | app/services/ai_validator.py; docs/AI_COACH.md; tests/test_ai_validator.py | Keep fallback visible in UI history. |
| AR-042 | Layer 3 AI Coach Product Archetype | Separation | Coach archetype vs CS2 domain | 2/5 | MEDIUM | app/services/recommendation_tracking.py; app/services/coach_rules.py; docs/METRICS.md | Define package boundaries for coach_core vs cs2_domain. |
| AR-043 | Layer 4 CS2 Domain Pack | Match model | Match/round model | 4/5 | MEDIUM | app/db/models.py; app/services/demo_parser.py | Add CS2 domain model map. |
| AR-044 | Layer 4 CS2 Domain Pack | Maps | Maps | 2/5 | MEDIUM | app/db/models.py; app/services/analytics.py; NOT_FOUND:cs2_map_registry | Add CS2 map registry/normalizer and tests. |
| AR-045 | Layer 4 CS2 Domain Pack | Sides | CT/T sides | 3/5 | HIGH | app/db/models.py; docs/METRICS.md; app/services/metric_truth.py | Keep side metrics display-only until parser confidence improves. |
| AR-046 | Layer 4 CS2 Domain Pack | First death | First death / early death logic | 4/5 | MEDIUM | docs/METRICS.md; app/services/metric_truth.py; tests/test_parser_facts_confidence.py | Keep early_deaths warning-only. |
| AR-047 | Layer 4 CS2 Domain Pack | Trades | Trade logic | 3/5 | HIGH | docs/METRICS.md; app/services/metric_truth.py; app/db/models.py | Do not build hard trade recommendations before parser hardening. |
| AR-048 | Layer 4 CS2 Domain Pack | Utility | Utility logic | 3/5 | MEDIUM | app/db/models.py; docs/METRICS.md; app/services/metric_truth.py | Add utility event fixture and confidence thresholds. |
| AR-049 | Layer 4 CS2 Domain Pack | Economy | Economy model | 0/5 | MEDIUM | NOT_FOUND:economy model; app/db/models.py; docs/METRICS.md | Mark economy explicitly unavailable in domain pack. |
| AR-050 | Layer 4 CS2 Domain Pack | Aim | Aim metrics | 4/5 | MEDIUM | app/services/aim_stats.py; docs/METRICS.md; app/services/metric_truth.py; README.md | Keep crosshair/spray unavailable until data exists. |
| AR-051 | Layer 4 CS2 Domain Pack | Positioning | Positioning model | 1/5 | MEDIUM | docs/METRICS.md; NOT_FOUND:position model | Document positioning as unavailable until parser payload supports it. |
| AR-052 | Layer 4 CS2 Domain Pack | Clutch | Clutch model | 2/5 | MEDIUM | app/db/models.py; docs/METRICS.md | Add clutch metric definition or mark unavailable. |
| AR-053 | Layer 4 CS2 Domain Pack | Entry | Entry model | 4/5 | LOW | docs/METRICS.md; app/services/metric_truth.py | Add sample-size thresholds for entry conclusions. |
| AR-054 | Layer 4 CS2 Domain Pack | Data sources | Demos/FACEIT/Steam | 4/5 | MEDIUM | docs/STEAM_IMPORT.md; docs/CURRENT_STATUS.md; docs/KNOWN_LIMITATIONS.md | Keep source limitations visible in UI/coach output. |
| AR-055 | Layer 4 CS2 Domain Pack | Sample size | Sample size rules | 3/5 | HIGH | app/services/metric_confidence.py; docs/METRICS.md | Define sample-size thresholds per metric/category. |
| AR-056 | Layer 4 CS2 Domain Pack | Glossary | Domain glossary | 2/5 | LOW | docs/METRICS.md; docs/STEAM_IMPORT.md; NOT_FOUND:CS2 glossary | Add concise CS2 domain glossary. |
| AR-057 | Layer 5 Project Instance | Stack | Current stack | 5/5 | LOW | pyproject.toml; README.md; docs/CURRENT_STATUS.md | Keep README current with port 8010 vs local 8000 distinction. |
| AR-058 | Layer 5 Project Instance | Repo structure | Repo map | 4/5 | LOW | docs/project_management/DOCS_INDEX.md; NOT_FOUND:PROJECT_INDEX; evidence/file_inventory.txt | Optionally add PROJECT_INDEX pointer or document DOCS_INDEX as equivalent. |
| AR-059 | Layer 5 Project Instance | Features | Current features | 4/5 | LOW | README.md; docs/project_management/ACCEPTANCE_MATRIX.md | Keep acceptance matrix as canonical feature status. |
| AR-060 | Layer 5 Project Instance | Limitations | Known limitations | 5/5 | LOW | docs/KNOWN_LIMITATIONS.md; docs/CURRENT_STATUS.md | Add owner/target WP fields for risk tracking. |
| AR-061 | Layer 5 Project Instance | Roadmap | Roadmap | 5/5 | LOW | docs/project_management/VERSION_ROADMAP.md; docs/project_management/WP_REGISTRY.md | Maintain registry-first status. |
| AR-062 | Layer 5 Project Instance | Deployment | Current deployment | 4/5 | MEDIUM | docs/CURRENT_STATUS.md; deploy/systemd/jc-coach.service; docs/DEPLOYMENT.md | Add authorized runtime config verification in deploy WP. |
| AR-063 | Layer 5 Project Instance | Product decisions | Product decisions | 4/5 | LOW | docs/DECISIONS.md | Keep decision entries brief and dated. |
| AR-064 | Layer 5 Project Instance | Current status | Current state | 5/5 | LOW | docs/CURRENT_STATUS.md | Re-check SHA before any DB-dependent WP. |
| AR-065 | Layer 5 Project Instance | Old docs | Historical docs | 4/5 | MEDIUM | docs/project_management/DOCS_INDEX.md; docs/project_management/DOCS_MAP.md | Continue conservative pointer cleanup; no deletion without approval. |
| AR-066 | Layer 5 Project Instance | Data artifacts | Runtime artifacts in repo | 3/5 | MEDIUM | .gitignore; evidence/file_inventory.txt; AGENTS.md | Add audit command filters and storage hardening WP. |
| AR-067 | Layer 5 Project Instance | Data schema | Database schema contract | 2/5 | BLOCKER | app/db/models.py; docs/MIGRATIONS.md; app/db/session.py | Create migration baseline and schema diff gate. |
| AR-068 | Layer 5 Project Instance | Metric formulas | Metric formulas | 4/5 | MEDIUM | docs/METRICS.md; app/services/metric_truth.py; tests/test_metric_truth.py | Keep formula/reliability sync tests. |
| AR-069 | Layer 5 Project Instance | Invariants | Metric invariants | 3/5 | HIGH | tests/test_metric_truth.py; tests/test_analytics.py; tests/test_parser_facts_confidence.py | Add golden aggregate fixture suite. |
| AR-070 | Layer 5 Project Instance | Null handling | Null/empty data | 4/5 | MEDIUM | tests/test_importer.py; app/services/metric_confidence.py; docs/METRICS.md | Add null/empty tests for each new metric. |
| AR-071 | Layer 5 Project Instance | Deduplication | Deduplication | 4/5 | LOW | app/db/models.py; tests/test_importer.py | Document source trust per importer. |
| AR-072 | Layer 5 Project Instance | Source trust | Source trust levels | 3/5 | HIGH | docs/METRICS.md; docs/STEAM_MATCH_DATES_RU.md; docs/CURRENT_STATUS.md | Create source trust registry for CSV/JSON/demo/Steam/FACEIT. |
| AR-073 | Layer 5 Project Instance | Aggregation | Aggregation rules | 3/5 | MEDIUM | app/services/analytics.py; app/services/metric_confidence.py; tests/test_analytics.py | Document aggregation rules and add golden fixtures. |
| AR-074 | Layer 5 Project Instance | Period comparison | Period comparison | 3/5 | MEDIUM | app/services/analytics.py; tests/test_analytics.py | Document period comparison semantics. |
| AR-075 | Layer 5 Project Instance | Filters | Map/side/player filters | 3/5 | MEDIUM | app/web/routes.py; app/templates/stats.html; docs/METRICS.md | Add filter confidence labels and tests. |
| AR-076 | Layer 5 Project Instance | Reproducibility | Calculation reproducibility | 3/5 | HIGH | evidence/test_results.txt; docs/AI_COACH.md; app/services/metric_truth.py | Version metric registry/prompt payload snapshots. |
| AR-077 | Layer 5 Project Instance | Code quality | Coding standards | 3/5 | MEDIUM | pyproject.toml; evidence/test_results.txt; NOT_FOUND:mypy/pyright | Add mypy/pyright gradually for services. |
| AR-078 | Layer 5 Project Instance | Code quality | Module boundaries | 3/5 | MEDIUM | docs/ARCHITECTURE.md; app/api/routes.py; app/web/routes.py | Refactor only as scoped feature work; add route/service map. |
| AR-079 | Layer 5 Project Instance | Code quality | Dead code/stale code | 2/5 | LOW | evidence/file_inventory.txt; NOT_FOUND:dead_code_report | Run targeted dead-code audit after foundation tasks. |
| AR-080 | Layer 5 Project Instance | Code quality | Duplicate logic | 2/5 | MEDIUM | app/api/routes.py; app/web/routes.py | Extract shared background job helper when touching Steam routes. |
| AR-081 | Layer 5 Project Instance | Code quality | Hidden global state | 3/5 | HIGH | app/db/session.py; app/config.py; tests/conftest.py; docs/TESTING.md | Reduce global engine binding or add import-order smoke guard. |
| AR-082 | Layer 5 Project Instance | Code quality | Dependency direction | 2/5 | MEDIUM | app/web/routes.py; app/main.py | Move templates/context into a web module. |
| AR-083 | Layer 5 Project Instance | Tests | Unit tests | 4/5 | LOW | tests/*; evidence/test_results.txt | Keep targeted tests with each WP. |
| AR-084 | Layer 5 Project Instance | Tests | Integration tests | 3/5 | MEDIUM | tests/test_web_smoke.py; tests/test_security.py; tests/test_coach_first_ui.py | Add lightweight Playwright/browser tests only when needed. |
| AR-085 | Layer 5 Project Instance | Tests | E2E tests | 1/5 | MEDIUM | NOT_FOUND:e2e; tests_inventory.txt | Add minimal authenticated read-only e2e smoke later. |
| AR-086 | Layer 5 Project Instance | Tests | Contract tests | 2/5 | MEDIUM | app/api/routes.py; NOT_FOUND:contract tests | Add contract tests for core GET and mutation payloads. |
| AR-087 | Layer 5 Project Instance | Tests | Metric tests | 3/5 | HIGH | tests/test_metric_truth.py; tests/test_analytics.py; docs/project_management/ACCEPTANCE_MATRIX.md | Build golden metric fixture suite for accepted metrics. |
| AR-088 | Layer 5 Project Instance | Tests | AI eval tests | 2/5 | HIGH | tests/test_ai_validator.py; NOT_FOUND:evals | Add golden AI semantic evals. |
| AR-089 | Layer 5 Project Instance | Tests | Test data fixtures | 3/5 | MEDIUM | tests/conftest.py; data/sample_matches.csv; tests/test_demo_parser.py | Add small sanitized parser payload fixtures instead of raw demos. |
| AR-090 | Layer 5 Project Instance | Tests | CI quality gates | 2/5 | HIGH | evidence/test_results.txt; NOT_FOUND:.github/workflows | Add CI for pytest, ruff, diff/check scripts. |
| AR-091 | Layer 5 Project Instance | Observability | Logs/errors/debug traces | 2/5 | MEDIUM | docs/SECURITY.md; docs/DEPLOYMENT.md; app/services/security.py | Add observability runbook and log taxonomy. |
| AR-092 | Layer 5 Project Instance | Ops | Rollback | 4/5 | MEDIUM | docs/BACKUP_RESTORE.md; scripts/backup_runtime.sh; scripts/restore_runtime.sh | Verify restore regularly and document raw demo policy. |
| AR-093 | Layer 5 Project Instance | Ops | Backups/snapshots | 4/5 | MEDIUM | AGENTS.md; docs/BACKUP_RESTORE.md; evidence/commands_run.txt | Keep SHA in every DB-impacting WP. |
| AR-094 | Layer 5 Project Instance | Ops | Incident process | 2/5 | MEDIUM | docs/audit/BUGFIX_001_COACH_RUNTIME_FAILURE_DIAGNOSIS.md; docs/DEPLOYMENT.md | Add short incident runbook. |
| AR-095 | Layer 5 Project Instance | Security | Secret storage | 4/5 | HIGH | .gitignore; evidence/commands_run.txt; docs/SECURITY.md | Add secret redaction command policy to docs/gate. |
| AR-096 | Layer 5 Project Instance | Security | No secrets in git | 4/5 | LOW | .gitignore; evidence/git_status.txt | Keep status checks before commits. |
| AR-097 | Layer 5 Project Instance | Security | Rate limiting | 3/5 | HIGH | docs/SECURITY.md; app/main.py; app/services/security.py; tests/test_security.py | Do not claim public readiness; add reverse proxy/Redis limiter later. |
| AR-098 | Layer 5 Project Instance | Security | Data privacy | 2/5 | HIGH | docs/SECURITY.md; docs/DEMO_STORAGE_TZ.md; docs/KNOWN_LIMITATIONS.md | Add data privacy/retention policy before sharing/friends use. |
| AR-099 | Layer 6 Runtime Layer | Active task | Active task tracking | 4/5 | LOW | docs/CURRENT_STATUS.md; user prompt | If accepted, register follow-up tasks only with user approval. |
| AR-100 | Layer 6 Runtime Layer | Loaded context | Loaded context record | 4/5 | LOW | evidence/* | Keep evidence file-backed for long audits. |
| AR-101 | Layer 6 Runtime Layer | Plans | Plan discipline | 3/5 | LOW | conversation plan; evidence/commands_run.txt | Use report next-steps for durable state. |
| AR-102 | Layer 6 Runtime Layer | Diffs | Diff discipline | 4/5 | LOW | git status; evidence/git_status.txt | Do not git add/commit without approval. |
| AR-103 | Layer 6 Runtime Layer | Tests | Test results stored | 5/5 | LOW | evidence/test_results.txt | Retain with audit. |
| AR-104 | Layer 6 Runtime Layer | Review comments | Review comments | 4/5 | LOW | 08_CRITICAL_GAPS.md; 09_RECOMMENDED_TASKS.md; 10_NEXT_10_TASKS.md | Review with PM before implementing. |
| AR-105 | Layer 6 Runtime Layer | Decisions | Decision capture | 4/5 | LOW | AGENTS.md; this audit folder | User/PM decides which tasks become WPs. |
| AR-106 | Layer 6 Runtime Layer | Rollback points | Rollback points | 5/5 | LOW | evidence/commands_run.txt; sha256sum output | No rollback needed for source except deleting audit folder if rejected. |
