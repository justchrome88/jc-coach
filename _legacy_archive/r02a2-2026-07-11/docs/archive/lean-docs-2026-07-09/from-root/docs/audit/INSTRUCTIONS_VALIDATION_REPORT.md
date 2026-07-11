# Instructions Validation Report

Audit date: 2026-07-03.

## 1. Verdict

PASS_WITH_WARNINGS

The documentation now has a real control structure with `docs/PROJECT_CONTROL.md` as the source of truth, explicit current docs, domain docs, audit inventory, conflict audit and deprecation plan.

Warnings remain because two validation requirements are not fully satisfied:

- `docs/PROJECT_CONTROL.md` and `docs/CURRENT_STATUS.md` say `v0.7-prep: personal alpha with coach-loop foundation`, while this validation request expects the project to be clearly stated as `v0.4-alpha foundation`.
- `AGENT.md` does not explicitly require `git status` before work and does not clearly require the post-work docs/tests/commit discipline requested in this validation pass.

## 2. Executive Summary

The consolidation did more than add files: it created a hierarchy:

1. `docs/PROJECT_CONTROL.md` overrides older docs.
2. `AGENT.md` gives agents a canonical read order.
3. `docs/CURRENT_STATUS.md`, `docs/CURRENT_MILESTONE.md`, `docs/VERSION_MAP.md`, `docs/ROADMAP.md` describe current state and direction.
4. Domain docs exist for architecture, metrics, recommendations, security, Steam, AI, testing, deployment, backup/restore, limitations and release gates.
5. Audit docs record inventory, conflicts and deprecation policy.

The system is usable for controlled next-stage planning, but hardening should not start until the version/milestone wording and agent workflow requirements are made unambiguous.

## 3. Required Files Check

| File | Exists | Status | Problem | Action |
|---|---:|---|---|---|
| `docs/PROJECT_CONTROL.md` | yes | warning | Uses `v0.7-prep`, not requested `v0.4-alpha foundation`. | Align version wording or explain why `v0.7-prep` supersedes `v0.4-alpha`. |
| `AGENT.md` | yes | warning | Missing explicit `git status` before work; missing explicit docs/tests/commit-after-work rule. | Update before hardening. |
| `docs/CURRENT_STATUS.md` | yes | warning | Uses `v0.7-prep`, not requested `v0.4-alpha foundation`. | Align with project control decision. |
| `docs/CURRENT_MILESTONE.md` | yes | pass | Current milestone and sub-phases are clear. | Keep. |
| `docs/VERSION_MAP.md` | yes | pass | Version table exists and marks secure friends alpha blocked. | Keep. |
| `docs/ROADMAP.md` | yes | pass | New roadmap is subordinate to project control. | Keep. |
| `LATER.md` | yes | pass | Deferred scope is separated. | Keep. |
| `docs/ARCHITECTURE.md` | yes | pass | Domain source of truth exists. | Keep. |
| `docs/METRICS.md` | yes | warning | Correctly marks itself as placeholder, not complete metric spec. | Expand before Metric Truth Layer work. |
| `docs/RECOMMENDATIONS.md` | yes | pass | Planner gap and primary recommendation loop are clear. | Keep. |
| `docs/SECURITY.md` | yes | pass | Friends/public blockers are explicit. | Keep. |
| `docs/STEAM_IMPORT.md` | yes | pass | Steam alpha status and risks are explicit. | Keep. |
| `docs/AI_COACH.md` | yes | pass | Validator/schema gap is explicit. | Keep. |
| `docs/TESTING.md` | yes | warning | Says `pytest` is safe, but also says tests must not use production DB/settings. | Verify test isolation before running tests. |
| `docs/DEPLOYMENT.md` | yes | pass | Controlled personal/VPS status is clear. | Keep. |
| `docs/BACKUP_RESTORE.md` | yes | warning | Correctly records backup/restore as incomplete. | Complete before friends/public use. |
| `docs/KNOWN_LIMITATIONS.md` | yes | pass | Key non-readiness areas are listed. | Keep. |
| `docs/RELEASE_CHECKLIST.md` | yes | pass | Personal/friends/public gates exist. | Keep. |
| `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` | yes | pass | Deprecation policy exists. | Keep. |
| `docs/audit/INSTRUCTIONS_INVENTORY.md` | yes | pass | Inventory exists with status/action columns. | Keep updated. |
| `docs/audit/DOCUMENT_CONFLICTS.md` | yes | pass | Main conflict classes are documented. | Keep updated. |

## 4. Source of Truth Check

`docs/PROJECT_CONTROL.md` passes these checks:

- It declares itself canonical and says it overrides older README, roadmap, audit, prompt and `instructions/*` documents.
- It points to current milestone.
- It lists source-of-truth documents by topic.
- It explains what Codex must read before work.
- It contains frozen scope.
- It blocks viewer, heatmaps, clips, payments, public share pages, raw `.dem` deletion and production LLM automation before hardening.
- It contains Definition of Done.

Open issue:

- The validation request asks for `v0.4-alpha foundation`, but project control currently says `v0.7-prep: personal alpha with coach-loop foundation`. This is the most important source-of-truth inconsistency to resolve before hardening.

## 5. Conflict Check

| Conflict area | Result | Notes |
|---|---|---|
| README vs CURRENT_STATUS | warning | README now links to project control, but still contains long operational sections that can imply more maturity than current status. |
| ROADMAP old vs ROADMAP new | pass_with_warning | `instructions/07_ROADMAP.md` is marked historical/deprecated; old roadmap still contains friends/viewer/FACEIT ideas and must not be used as current. |
| `instructions/*` vs PROJECT_CONTROL | pass_with_warning | Main instruction files are marked historical/deprecated, but they remain in place and contain old prompts, viewer/heatmap ideas and MVP v0.1 language. |
| Audit docs vs canonical docs | pass | Audit docs are clearly point-in-time/supporting and subordinate to project control. |
| STEAM_IMPORT vs old Steam instructions | pass | `docs/STEAM_IMPORT.md` states alpha/not production-ready; old Steam notes are marked deprecated. |
| METRICS.md vs old metric roadmap/scoring | warning | `docs/METRICS.md` is honest but incomplete; old scoring files are marked advisory in inventory, not deprecated headers. |

Old documents that can still mislead if read without the historical headers:

- `instructions/01_OVERNIGHT_MVP_TASK.md`: `MVP v0.1`, old scope, no Steam/public.
- `instructions/07_ROADMAP.md`: friends testing, Steam profile, FACEIT, viewer.
- `instructions/09_READY_TO_PASTE_COMMANDS.md`: old ready-to-paste implementation prompts.
- `instructions/02_FULL_PERSONAL_PRODUCT_TZ.md`: broad future product scope, heatmaps, viewer, friends/commercial future.
- `instructions/04_DATA_AND_METRICS_SPEC.md`: metric wishlist including heatmaps/viewer data.
- `instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md`: old recommendation TZ, useful historically but not current planner truth.
- `docs/COMPETITOR_FEATURE_MATRIX.md`: feature ideas and stale implementation statuses.
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`: old implementation plan.
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`: prompt library that can conflict with latest user constraints.
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md`: historical AI memo with stale next steps.

## 6. Deprecated Documents Check

`docs/audit/DOCUMENT_DEPRECATION_PLAN.md` exists and defines a non-destructive plan:

1. Mark stale/conflicting documents.
2. Keep them for review.
3. Migrate unique current information.
4. Move to `docs/archive/` only after approval.
5. Delete only after approval.

Most outdated instruction files have explicit historical/deprecated headers.

Remaining issues:

- `instructions/1.txt` remains `unknown/needs_review`.
- `docs/METRICS_ROADMAP_SCORING_RU.md`, `docs/FEATURE_ROADMAP_SCORING.md`, `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`, `docs/FEATURES_RU.md`, `docs/STEAM_IMPORT_ARCHITECTURE.md`, `docs/DEMO_DEEP_PARSER_TZ_RU.md` and `docs/DEMO_STORAGE_TZ.md` are handled in inventory but do not all have visible top-of-file status banners.
- Generated `data/reports/coach_report_*.md` are outside the canonical docs set but still appear in repository scans and need owner review.

## 7. Codex Readiness Check

Passes:

- `AGENT.md` requires reading `docs/PROJECT_CONTROL.md`.
- `AGENT.md` requires reading `docs/CURRENT_MILESTONE.md`.
- `AGENT.md` says older docs are subordinate to project control.
- `AGENT.md` blocks code, DB, jobs, commits, pushes and deploys unless explicitly requested.
- `AGENT.md` says new feature work must not bypass security, metric confidence, parser verification and recommendation planner hardening.

Warnings:

- `AGENT.md` does not explicitly require `git status --short` before work.
- `AGENT.md` does not explicitly require docs/tests/commit handling after work. It blocks commits unless requested, which is safe, but not the same as a complete post-work process.
- `AGENT.md` does not explicitly say "tasks outside current milestone are forbidden"; it says new feature work must not bypass hardening unless reprioritized. That is close but less strict than requested.

## 8. Remaining Risks

- Version naming is not settled: `v0.4-alpha foundation` vs `v0.7-prep`.
- `docs/METRICS.md` is a placeholder, so Metric Truth Layer work cannot rely on it yet.
- Test isolation is not proven; do not run tests until DB/settings isolation is verified.
- Backup/restore is acknowledged but not specified.
- Old docs remain searchable and can still influence an agent if it ignores headers.
- README remains long and operational; it links to canonical truth but still contains sections that could be overread as production readiness.

## 9. Must Fix Before Hardening

1. Resolve canonical version wording: decide whether current status is `v0.4-alpha foundation` or `v0.7-prep`, then update `docs/PROJECT_CONTROL.md`, `docs/CURRENT_STATUS.md`, `docs/VERSION_MAP.md` and audit notes consistently.
2. Update `AGENT.md` to require `git status --short` before work.
3. Update `AGENT.md` to define post-work expectations: docs updated, safe tests/checks reported, no commit unless explicitly requested.
4. Add a visible top-of-file status banner to partially-current supporting docs that can still mislead: roadmap scoring, metric scoring, public deployment checklist and feature list.
5. Decide how to handle `instructions/1.txt` and generated `data/reports/coach_report_*.md`.

## 10. Safe Next Prompt For Codex

```text
Perform a docs-only fix pass for the validation warnings in docs/audit/INSTRUCTIONS_VALIDATION_REPORT.md.

Do not change application code, database models, migrations, runtime data, imports, Steam jobs or parser jobs.
Do not run tests until test isolation is verified.

Tasks:
1. Resolve canonical version wording across PROJECT_CONTROL, CURRENT_STATUS and VERSION_MAP.
2. Update AGENT.md with required git status, current-milestone gate and post-work docs/tests/no-commit rules.
3. Add clear top-of-file status banners to partially-current supporting docs that can mislead future agents.
4. Leave old documents in place; do not archive or delete anything.
5. Show git diff --stat and a short report.
```

## Final Validation Notes

Can hardening start now: not yet. The documentation system is mostly ready, but the version mismatch and missing `AGENT.md` workflow requirements should be fixed first.

The next hardening stage should read these documents first:

1. `AGENT.md`
2. `docs/PROJECT_CONTROL.md`
3. `docs/CURRENT_MILESTONE.md`
4. `docs/SECURITY.md`
5. `docs/BACKUP_RESTORE.md`

Old documents that must not be used as current instructions:

- `instructions/01_OVERNIGHT_MVP_TASK.md`
- `instructions/02_FULL_PERSONAL_PRODUCT_TZ.md`
- `instructions/03_CODEX_AGENT_RULES.md`
- `instructions/07_ROADMAP.md`
- `instructions/09_READY_TO_PASTE_COMMANDS.md`
- `instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md`
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`
- `docs/COMPETITOR_FEATURE_MATRIX.md`
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md`

## Addendum: docs-only fix pass 2026-07-03

### Что исправлено

- Разведены две разные сущности:
  - фактический уровень продукта: `v0.4-alpha foundation`;
  - текущий milestone разработки: `v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop`.
- Обновлены `docs/PROJECT_CONTROL.md`, `docs/CURRENT_STATUS.md`, `docs/VERSION_MAP.md`, `docs/CURRENT_MILESTONE.md` и `docs/ROADMAP.md`.
- `AGENT.md` обновлён на русском языке и теперь явно требует:
  - читать `AGENT.md`, `docs/PROJECT_CONTROL.md` и `docs/CURRENT_MILESTONE.md` перед любой задачей;
  - выполнять `git status --short` перед любой задачей;
  - не делать задачи вне текущего milestone без явного разрешения пользователя;
  - не менять код, БД и jobs без прямого разрешения задачи;
  - после работы показывать изменённые файлы;
  - обновлять релевантные docs при изменении поведения или процесса;
  - запускать только безопасные проверки;
  - явно писать, если тесты пропущены из-за риска production DB/runtime data;
  - не делать commit без явной просьбы пользователя.
- Добавлены русскоязычные top-of-file status banners в partially-current supporting docs:
  - `docs/METRICS_ROADMAP_SCORING_RU.md`;
  - `docs/FEATURE_ROADMAP_SCORING.md`;
  - `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`;
  - `docs/FEATURES_RU.md`;
  - `docs/STEAM_IMPORT_ARCHITECTURE.md`;
  - `docs/DEMO_DEEP_PARSER_TZ_RU.md`;
  - `docs/DEMO_STORAGE_TZ.md`.
- В `docs/audit/DOCUMENT_DEPRECATION_PLAN.md` зафиксирован статус:
  - `instructions/1.txt` как `keep_as_history`;
  - `data/reports/coach_report_*.md` как `keep_as_runtime_history`.

### Что осталось

- `docs/METRICS.md` пока остаётся placeholder-спецификацией. Перед Metric Truth Layer нужно расширить его до полной таблицы формул, источников, confidence и suppression rules.
- `docs/BACKUP_RESTORE.md` фиксирует gap, но ещё не является полноценным runbook.
- Тесты не запускались, потому что test isolation всё ещё не подтверждён.
- Старые исторические документы остаются в репозитории и должны читаться только как контекст.

### Можно ли начинать hardening

Можно начинать следующий docs/engineering этап hardening только с безопасного первого шага: подтвердить test isolation и backup/restore-процесс. До этого не запускать тесты, которые могут тронуть production DB, и не запускать imports, Steam jobs или parser jobs.
