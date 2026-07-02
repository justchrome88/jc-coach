# Document Deprecation Plan

Audit date: 2026-07-03.

No documents are deleted in this pass.

## Policy

1. Mark stale/conflicting documents with a historical/deprecated notice.
2. Keep them in place for at least one review cycle.
3. Migrate any unique current information into canonical docs.
4. Move to `docs/archive/` only after owner approval or a later explicit docs cleanup task.
5. Delete only after explicit owner approval.

## Marked Historical In This Pass

- `docs/PRODUCT_EXECUTION_STRATEGY.md`
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`
- `docs/AI_COACH_PROVIDER_ARCHITECTURE.md`
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md`
- `docs/COMPETITOR_FEATURE_MATRIX.md`
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`
- `instructions/00_PROJECT_BRIEF.md`
- `instructions/01_OVERNIGHT_MVP_TASK.md`
- `instructions/02_FULL_PERSONAL_PRODUCT_TZ.md`
- `instructions/03_CODEX_AGENT_RULES.md`
- `instructions/04_DATA_AND_METRICS_SPEC.md`
- `instructions/05_AI_COACH_PROMPT.md`
- `instructions/06_STEAM_AND_DEMO_IMPORT_NOTES.md`
- `instructions/07_ROADMAP.md`
- `instructions/08_TASKS_FOR_GPT55_AND_SPARK.md`
- `instructions/09_READY_TO_PASTE_COMMANDS.md`
- `instructions/11_REWRITTEN_USER_REQUEST_FOR_OTHER_CHAT.md`
- `instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md`

## Needs Owner Review

- `instructions/1.txt`
- Generated `data/reports/coach_report_*.md`
- Whether old historical docs should stay in place or be moved under `docs/archive/`

## Статус разобранных артефактов после validation fix pass

- `instructions/1.txt`: служебный/placeholder-артефакт со строкой `texst`. Не является инструкцией, roadmap, source of truth или планом реализации. Действие: `keep_as_history` до отдельного owner review; не удалять в рамках текущей консолидации.
- `data/reports/coach_report_*.md`: сгенерированные runtime-отчёты приложения. Не являются документацией проекта, инструкциями для Codex или source of truth. Действие: `keep_as_runtime_history`; не использовать как текущие инструкции и не удалять без отдельного решения по runtime data.
