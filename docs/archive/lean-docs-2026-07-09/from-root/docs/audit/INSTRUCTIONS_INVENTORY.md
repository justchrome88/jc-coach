# Instructions Inventory

Audit date: 2026-07-03.

| File | Type | Current/Historical/Unknown | Main topic | Still relevant? | Conflicts? | Action |
|---|---|---|---|---|---|---|
| `README.md` | deployment_doc | partially_current | User/operator entrypoint | Yes | Version title understates current state | keep |
| `AGENT.md` | codex_instruction | current | Agent rules | Yes | No | keep |
| `LATER.md` | roadmap | current | Deferred scope | Yes | No | keep |
| `WORKLOG.md` | historical_worklog | partially_current | Engineering chronology | Yes as history | Can look current despite chronology | keep |
| `INSTRUCTIONS_CONSOLIDATION_TASK.md` | task_plan | current | This consolidation task | Yes for this pass | No | keep |
| `data/incoming_demos/README.txt` | deployment_doc | current | Demo inbox note | Yes | No | keep |
| `data/reports/coach_report_*.md` | unknown | historical | Generated reports | No for docs control | Runtime generated output | needs_review |
| `docs/PROJECT_CONTROL.md` | project_brief | current | Canonical source of truth | Yes | No | keep |
| `docs/CURRENT_STATUS.md` | project_brief | current | Fact state | Yes | No | keep |
| `docs/VERSION_MAP.md` | roadmap | current | Version status | Yes | No | keep |
| `docs/CURRENT_MILESTONE.md` | roadmap | current | Active milestone | Yes | No | keep |
| `docs/ROADMAP.md` | roadmap | current | Ordered development | Yes | No | keep |
| `docs/ARCHITECTURE.md` | feature_spec | current | Architecture | Yes | No | keep |
| `docs/METRICS.md` | metric_spec | current | Metric contract placeholder | Yes | No | keep |
| `docs/RECOMMENDATIONS.md` | feature_spec | current | Recommendation loop | Yes | No | keep |
| `docs/SECURITY.md` | security_spec | current | Security gates | Yes | No | keep |
| `docs/STEAM_IMPORT.md` | steam_doc | current | Steam import control doc | Yes | No | keep |
| `docs/AI_COACH.md` | ai_doc | current | AI coach control doc | Yes | No | keep |
| `docs/TESTING.md` | testing_doc | current | Safe verification | Yes | No | keep |
| `docs/DEPLOYMENT.md` | deployment_doc | current | Deployment status | Yes | No | keep |
| `docs/BACKUP_RESTORE.md` | deployment_doc | current | Backup gap | Yes | No | keep |
| `docs/DECISIONS.md` | project_brief | current | Project decisions | Yes | No | keep |
| `docs/CHANGELOG.md` | historical_worklog | current | Curated changes | Yes | No | keep |
| `docs/KNOWN_LIMITATIONS.md` | audit_report | current | Limitations | Yes | No | keep |
| `docs/RELEASE_CHECKLIST.md` | deployment_doc | current | Release gates | Yes | No | keep |
| `docs/FEATURES_RU.md` | feature_spec | partially_current | Implemented feature list | Yes | May lag code | keep |
| `docs/STEAM_IMPORT_ARCHITECTURE.md` | steam_doc | partially_current | Steam design | Yes | Subordinate to `STEAM_IMPORT.md` | keep |
| `docs/STEAM_MATCH_DATES_RU.md` | steam_doc | current | Steam match date policy | Yes | No | keep |
| `docs/DEMO_DEEP_PARSER_TZ_RU.md` | feature_spec | partially_current | Deep parser design/history | Yes | Raw-delete target must stay gated | keep |
| `docs/DEMO_STORAGE_TZ.md` | feature_spec | partially_current | Demo storage lifecycle | Yes | Raw-delete target can be misread | keep |
| `docs/METRICS_ROADMAP_SCORING_RU.md` | metric_spec | partially_current | Metric priority scoring | Yes as roadmap | Not a runtime metric truth spec | keep |
| `docs/FEATURE_ROADMAP_SCORING.md` | roadmap | partially_current | Feature scoring | Yes as advisory | Percentages may lag current truth | keep |
| `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md` | deployment_doc | partially_current | Public deploy checklist | Yes | Must not imply public readiness | keep |
| `docs/audit/CS2_AI_COACH_AUDIT_2026-07-02.md` | audit_report | current | Security/product audit | Yes | Point-in-time only | keep |
| `docs/DOCUMENTATION_AUDIT.md` | audit_report | current | Summary audit | Yes | Duplicates split audit files | keep |
| `docs/PRODUCT_EXECUTION_STRATEGY.md` | roadmap | historical | Product strategy memo | Some | Subordinate to control doc | mark_deprecated |
| `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` | task_plan | historical | Old implementation plan | Some | Several statuses stale | mark_deprecated |
| `docs/AI_COACH_PROVIDER_ARCHITECTURE.md` | ai_doc | historical | AI provider memo | Some | Next steps stale | mark_deprecated |
| `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` | task_plan | historical | Completed AI/recommendation/aim plan | Some | Implementation has advanced | mark_deprecated |
| `docs/COMPETITOR_FEATURE_MATRIX.md` | roadmap | historical | Competitor feature matrix | Some | Statuses stale | mark_deprecated |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | codex_instruction | historical | Prompt library | Some | Can conflict with current user constraints | mark_deprecated |
| `instructions/00_PROJECT_BRIEF.md` | project_brief | historical | Original project brief | Historical only | Outdated scope/version | mark_deprecated |
| `instructions/01_OVERNIGHT_MVP_TASK.md` | task_plan | historical | Original overnight MVP | Historical only | Completed/outdated | mark_deprecated |
| `instructions/02_FULL_PERSONAL_PRODUCT_TZ.md` | feature_spec | historical | Original full TZ | Historical only | Overbroad vs current milestone | mark_deprecated |
| `instructions/03_CODEX_AGENT_RULES.md` | codex_instruction | superseded | Old agent rules | Historical only | Superseded by `AGENT.md` | mark_deprecated |
| `instructions/04_DATA_AND_METRICS_SPEC.md` | metric_spec | historical | Original metric wishlist | Some | Reliability not current | mark_deprecated |
| `instructions/05_AI_COACH_PROMPT.md` | ai_doc | historical | Old AI prompt | Some | Runtime prompt/payload differs | mark_deprecated |
| `instructions/06_STEAM_AND_DEMO_IMPORT_NOTES.md` | steam_doc | historical | Early Steam/demo notes | Some | Superseded by current Steam docs | mark_deprecated |
| `instructions/07_ROADMAP.md` | roadmap | historical | Early roadmap | Historical only | Superseded by current roadmap | mark_deprecated |
| `instructions/08_TASKS_FOR_GPT55_AND_SPARK.md` | codex_instruction | historical | Agent split notes | Historical only | Not current process | mark_deprecated |
| `instructions/09_READY_TO_PASTE_COMMANDS.md` | codex_instruction | historical | Old prompt commands | Historical only | Can ask for outdated work/jobs | mark_deprecated |
| `instructions/10_MINIMAL_SAMPLE_DATA.csv` | unknown | current | Sample data | Yes | No | keep |
| `instructions/11_REWRITTEN_USER_REQUEST_FOR_OTHER_CHAT.md` | task_plan | historical | Handoff prompt | Historical only | Outdated | mark_deprecated |
| `instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md` | feature_spec | historical | Recommendation tracking TZ | Some | Implementation has advanced | mark_deprecated |
| `instructions/1.txt` | unknown | unknown | Placeholder artifact | No clear value | Unknown | needs_review |

