# CS2 AI Coach — Master Curation Playbook / Full Stage Backup

> Status: Historical / archive candidate.
> This file is retained as project history/evidence.
> Do not use it as current workflow, roadmap, version truth or source of truth.
> Current workflow: `docs/project_management/AGENT_WORKFLOW.md`.
> Current WP truth: `docs/project_management/WP_REGISTRY.md`.
> Current Hot context: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md`.

Дата: 2026-07-03  
Назначение: полный резервный план управления проектом, чтобы продолжать разработку без текущего чата.  
Формат: stage-by-stage hardening pipeline, правила принятия решений, шаблоны prompt'ов, DoD для всех ключевых stages.

---

# 0. Главная правда проекта

Проект нельзя вести как “Codex, сделай всё”.  
Проект ведётся как управляемый pipeline:

```text
Stage TZ → Codex implementation → safe checks → review-only pass → repair if needed → commit → next stage
```

Любой stage считается незавершённым, пока нет:

```text
[ ] implementation report
[ ] review-only report
[ ] tests green
[ ] ruff green
[ ] git diff --check green
[ ] production DB SHA checked
[ ] no forbidden jobs
[ ] commit
[ ] clean git status
```

Если commit не сделан — stage не закрыт.

---

# 1. Текущий статус на момент создания playbook

Проект: CS2 AI Coach  
Путь: `/opt/jc-coach`

Уже закрыто:

```text
[✓] Stage 0: Safety Foundation
[✓] Stage 1: Security P0
[✓] Stage 2: Ownership / enforced single-owner boundaries
```

Текущий верхний commit после Stage 2:

```text
7420bce Add enforced single-owner boundaries
```

Следующий stage:

```text
[→] Stage 3: Migration discipline
```

Текущий известный production DB SHA:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

---

# 2. Source of truth

Перед любой работой читать:

```text
AGENT.md
docs/PROJECT_CONTROL.md
docs/CURRENT_STATUS.md
docs/CURRENT_MILESTONE.md
docs/VERSION_MAP.md
docs/ROADMAP.md
docs/SECURITY.md
docs/TESTING.md
docs/BACKUP_RESTORE.md
docs/RELEASE_CHECKLIST.md
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
docs/audit/API_SECURITY_INVENTORY.md
docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
docs/audit/STAGE_2_OWNERSHIP_REVIEW.md
```

После каждого нового stage добавляются:

```text
docs/audit/STAGE_N_*_IMPLEMENTATION_REPORT.md
docs/audit/STAGE_N_*_REVIEW.md
docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/STABILIZATION_STAGE_N_*_TZ_CS2_AI_COACH.md
```

---

# 3. Как понять, какой stage следующий

Выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -10
rg -n "Stage [0-9]|Current|Next|completed|PASS|BLOCKED" docs/PROJECT_CONTROL.md docs/CURRENT_STATUS.md docs/CURRENT_MILESTONE.md docs/ROADMAP.md docs/audit
```

Правило:

```text
Следующий stage = первый stage в roadmap, у которого нет:
1. implementation report;
2. review report PASS/PASS_WITH_WARNINGS без blockers;
3. commit после review.
```

Если docs говорят одно, а git history другое — верить git + audit reports, потом чинить docs.

---

# 4. Universal preflight before any stage

```bash
cd /opt/jc-coach

git status --short
git --no-pager diff --stat
git log --oneline -5
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой и эти изменения не являются текущим stage — STOP.

Запрещено начинать новый stage поверх незакоммиченного предыдущего.

---

# 5. Universal implementation prompt

```text
Начни Stage <N>: <NAME>.

Главный архивный исторический файл задания:
docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/STABILIZATION_STAGE_<N>_<NAME>_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/TESTING.md
- docs/BACKUP_RESTORE.md
- relevant previous stage review reports
- главный файл задания

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -5
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage <N>:
<one sentence objective>

Жёсткие ограничения:
- не переходить к следующему stage;
- не делать commit;
- не запускать import/Steam/parser production jobs;
- не менять production DB без explicit approval;
- не добавлять feature creep вне scope;
- если задача требует forbidden scope — остановиться и написать BLOCKED.

В конце:
- создать docs/audit/STAGE_<N>_<NAME>_IMPLEMENTATION_REPORT.md;
- запустить safe checks;
- показать STAGE_RESULT;
- production DB touched yes/no;
- import/Steam/parser jobs run yes/no;
- can proceed to review-only yes/no.
```

---

# 6. Universal review-only prompt

```text
Проведи review-only проверку Stage <N>: <NAME>.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_<N>_<NAME>_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к следующему stage.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- relevant docs
- implementation report
- текущий git diff, включая untracked files

Проверь Stage <N> DoD из task-файла.

Запусти safe checks:
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db
- stage-specific checks

Создай review report:

# Stage <N> <NAME> Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Next Stage

## Can Proceed To Next Stage
yes/no

Если stage не проходит — не исправляй, только напиши, что именно не проходит.
```

---

# 7. Universal repair-only prompt

```text
Исправь только FAIL/BLOCKED пункты из:
docs/audit/STAGE_<N>_<NAME>_REVIEW.md

Не переходи к следующему stage.
Не добавляй новые фичи.
Не трогай forbidden scope.
Не запускай import/Steam/parser production jobs.
Не делай commit.

После исправления:
- обнови implementation/review report addendum;
- запусти safe checks;
- покажи changed files;
- production DB touched yes/no;
- можно ли коммитить yes/no.
```

---

# 8. Universal commit procedure

```bash
git status --short
git --no-pager diff --stat
```

Проверить, что нет:

```text
.env
data/*.db
data/uploads/*
data/reports/*
data/incoming_demos/*
runtime artifacts
```

Потом:

```bash
git add app docs tests scripts alembic alembic.ini pyproject.toml requirements.txt .env.example
git commit -m "Add <stage result>"
git status --short
git log --oneline -5
```

Если какие-то пути отсутствуют — `git add` можно адаптировать.

---

# 9. Stage roadmap overview

```text
[✓] Stage 0: Safety Foundation
[✓] Stage 1: Security P0
[✓] Stage 2: Ownership / enforced single-owner boundaries
[→] Stage 3: Migration discipline
[ ] Stage 4: Recommendation read/write split
[ ] Stage 5: Metric Truth Layer
[ ] Stage 6: Parser hardening
[ ] Stage 7: Steam cursor truth
[ ] Stage 8: AI validator
[ ] Stage 9: Coach-first UI
[ ] Stage 10: Friends alpha gate
[ ] Stage 11+: SaaS / multi-user / billing / public launch
```

---

# 10. Completed stages summary

## Stage 0: Safety Foundation

Goal:

```text
backup/restore + test isolation
```

Closed when:

```text
[✓] backup script
[✓] restore verify
[✓] test isolation prevents production DB usage
[✓] safe pytest passed
[✓] ruff passed
[✓] DB SHA unchanged
[✓] commit: Add safety foundation with backup and isolated tests
```

## Stage 1: Security P0

Goal:

```text
close public API/security P0 holes
```

Closed when:

```text
[✓] non-health /api/* protected
[✓] CSRF
[✓] rate limits MVP
[✓] session secret fail-fast
[✓] Steam OpenID check_authentication
[✓] dangerous jobs protected
[✓] Bearer API_TOKEN tested
[✓] review PASS_WITH_WARNINGS
[✓] commit: Add Security P0 hardening
```

Known warnings:

```text
rate limiter process-local
recommendation reads can mutate
not full public-ready security
```

## Stage 2: Ownership / enforced single-owner boundaries

Goal:

```text
single-owner instance, not multi-user SaaS
```

Closed when:

```text
[✓] first user is owner
[✓] second self-registration blocked
[✓] legacy Steam-only user not owner
[✓] public Steam callback cannot create uncontrolled user
[✓] owner session links Steam only to owner
[✓] API token documented as owner/operator
[✓] review PASS_WITH_WARNINGS
[✓] commit: Add enforced single-owner boundaries
```

Known warnings:

```text
link_steam_account(..., user_id=None) remains internal legacy risk
not full multi-user ownership
```

---

# 11. Stage 3: Migration discipline

## Objective

Introduce safe schema-change discipline before any future DB-affecting stages.

## Why

Audit found:

```text
Base.metadata.create_all(bind=engine)
_upgrade_sqlite_schema()
manual SQLite ALTER
no Alembic / no migration ledger
```

Future stages will likely need DB changes. Without migration discipline, project risks silent production DB mutation.

## Scope

```text
[ ] audit current schema evolution
[ ] docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md
[ ] docs/MIGRATIONS.md
[ ] safe migration tooling, preferably Alembic baseline
[ ] scripts to check migration status / dry-run on copy
[ ] tests/test_migrations.py
[ ] production DB SHA unchanged
```

## Non-scope

```text
no Metric Truth Layer
no recommendation refactor
no parser changes
no Steam sync changes
no AI changes
no UI redesign
no destructive migration
no production DB mutation
```

## DoD

```text
[ ] schema evolution inventory exists
[ ] migration policy documented
[ ] future schema changes must be migration-first
[ ] startup schema mutations documented as legacy or constrained
[ ] backup-before-migration procedure documented
[ ] safe tooling exists or clear BLOCKED reason
[ ] tests pass
[ ] DB SHA unchanged
[ ] review report PASS/PASS_WITH_WARNINGS
[ ] commit: Add migration discipline
```

## Next stage trigger

Stage 4 starts only after Stage 3 review + commit.

---

# 12. Stage 4: Recommendation read/write split

## Objective

Stop read endpoints/helpers from mutating DB.

Current known issue:

```text
GET /api/recommendations* can mutate indirectly
recommendation service read helpers can evaluate/create records
```

This is architectural poison: reads must be reads, writes must be explicit.

## Scope

```text
[ ] inventory all recommendation read/write paths
[ ] split query/read service from mutation/evaluation service
[ ] no DB commit in read helpers
[ ] explicit commands for:
    - create recommendation
    - evaluate recommendation
    - extend/restart/status changes
[ ] route methods align with behavior
[ ] tests prove GET/read paths do not mutate DB
[ ] docs/audit/RECOMMENDATION_SIDE_EFFECT_INVENTORY.md
[ ] docs/audit/STAGE_4_RECOMMENDATION_RW_IMPLEMENTATION_REPORT.md
```

## Non-scope

```text
no new recommendation planner
no Metric Truth Layer
no AI output validator
no parser hardening
no UI redesign except minimal route/template fixes if required
```

## Suggested tests

```text
[ ] GET recommendations does not change row counts
[ ] GET recommendations does not create evaluations
[ ] POST status/extend/restart mutates intentionally
[ ] reports generation behavior remains explicit
[ ] existing coach page still works
```

## DoD

```text
[ ] read/write inventory created
[ ] read paths side-effect free
[ ] mutation paths explicit
[ ] tests prove no read mutation
[ ] docs updated
[ ] full pytest green
[ ] DB SHA unchanged unless explicitly allowed
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Split recommendation reads from writes
```

## Next stage trigger

Stage 5 Metric Truth Layer can start only after recommendation reads are side-effect free.

---

# 13. Stage 5: Metric Truth Layer

## Objective

Create a trustworthy metric registry/layer so coach recommendations know which metrics are reliable, approximate, missing, or suppressed.

Current known issues:

```text
early_deaths = entry_deaths fallback
side splits low confidence
trade_kill exists but no traded/untraded death
metrics exist without runtime source/formula/reliability
```

## Scope

```text
[ ] docs/audit/METRIC_TRUTH_INVENTORY.md
[ ] define MetricDefinition / registry
[ ] each metric has:
    - id
    - display name
    - source
    - formula
    - confidence/reliability
    - suppression rules
    - known limitations
[ ] expose reliability to diagnosis/recommendation layer
[ ] no false precision
[ ] tests for reliability/suppression
```

## Non-scope

```text
no parser deep refactor
no new AI coach schema
no UI redesign except minimal reliability labels
no new SaaS features
```

## DoD

```text
[ ] metric registry exists
[ ] unreliable metrics are labeled/suppressed
[ ] docs/METRICS.md no longer placeholder
[ ] diagnosis can consume reliability metadata
[ ] tests cover reliable/unreliable metrics
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Add metric truth layer
```

## Next stage trigger

Stage 6 Parser hardening starts after metrics have truth/reliability layer, so parser work targets known gaps instead of guessing.

---

# 14. Stage 6: Parser hardening

## Objective

Improve parser facts that feed metrics/recommendations, without lying about what is known.

Known gaps:

```text
early_deaths fallback
side_stats low confidence
no traded_death/untraded_death
limited movement/view-angle timeline
parser confidence not fully propagated
```

## Scope

```text
[ ] docs/audit/PARSER_FACTS_INVENTORY.md
[ ] improve early death calculation if safe
[ ] add traded/untraded death facts if available
[ ] propagate parser confidence to Metric Truth Layer
[ ] no recommendation logic changes except consuming confidence
[ ] tests with fixture/demo-derived data
```

## Non-scope

```text
no viewer/heatmaps/clips
no full demo analytics platform
no UI redesign
no AI validator
no Steam sync changes
```

## DoD

```text
[ ] parser fact inventory updated
[ ] new/updated facts tested
[ ] metric confidence reflects parser quality
[ ] no production parser jobs run
[ ] no raw demo destructive changes
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Harden parser facts
```

## Next stage trigger

Stage 7 Steam cursor truth starts after parser inputs/facts are more stable.

---

# 15. Stage 7: Steam cursor truth

## Objective

Make Steam import cursor/sync behavior reliable and non-destructive.

Known gaps:

```text
latest share code cursor partially implemented
residual knowncode=0
no durable scheduler/retry/backoff/rate limit
dangerous import jobs previously exposed
```

## Scope

```text
[ ] docs/audit/STEAM_CURSOR_INVENTORY.md
[ ] define source of truth for latest share code / cursor
[ ] remove ambiguous knowncode=0 behavior or document safely
[ ] implement durable sync state if safe
[ ] retry/backoff policy
[ ] no duplicate uncontrolled imports
[ ] tests with mocked Steam, no live Steam calls
```

## Non-scope

```text
no parser hardening
no AI validator
no UI redesign
no paid SaaS
no live Steam production sync during stage
```

## DoD

```text
[ ] cursor truth documented
[ ] sync state deterministic
[ ] mocked tests cover new/old/no match scenarios
[ ] no live Steam jobs run
[ ] DB changes only through migration discipline
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Add Steam cursor truth
```

## Next stage trigger

Stage 8 AI validator starts after data/import path is deterministic enough to feed AI.

---

# 16. Stage 8: AI validator

## Objective

Make AI coach output structured, validated, and safe to display/store.

Current known issue:

```text
AI provider/handoff/freeform exists
no output schema/validator
AI maturity: handoff/freeform_summary, not validated_coach
```

## How to know Stage 7 is finished before Stage 8

Stage 7 is finished only if:

```text
[ ] docs/audit/STAGE_7_STEAM_CURSOR_REVIEW.md exists
[ ] result PASS/PASS_WITH_WARNINGS without blockers
[ ] git commit exists after review
[ ] git status clean
[ ] docs/CURRENT_MILESTONE.md says next stage is Stage 8 AI validator
[ ] no uncommitted Steam/parser/import changes
```

If any item is missing, do not start Stage 8.

## Stage 8 scope

```text
[ ] define AI coach output schema
[ ] validate provider output before use
[ ] reject/repair invalid AI output
[ ] prevent unsupported claims
[ ] map AI output to:
    - diagnosis
    - recommendation
    - evidence
    - confidence
    - action
    - next-match verification criteria
[ ] tests for valid/invalid/malformed provider outputs
[ ] docs/AI_COACH.md updated
[ ] docs/audit/AI_OUTPUT_SCHEMA_INVENTORY.md
```

## Non-scope

```text
no new LLM provider unless absolutely required
no SaaS payment
no UI redesign beyond minimal display of validated output
no parser changes
no Steam sync changes
```

## Suggested AI output schema fields

```text
schema_version
summary
diagnoses[]
  - problem_id
  - label
  - evidence_metrics[]
  - confidence
  - limitations
recommendations[]
  - recommendation_id
  - action
  - reason
  - measurable_target
  - verification_window
  - suppress_if_metric_unreliable
next_match_focus[]
warnings[]
```

## DoD

```text
[ ] schema defined
[ ] validator implemented
[ ] invalid output rejected or safely downgraded
[ ] no hallucinated metrics accepted
[ ] AI output references Metric Truth Layer reliability
[ ] tests cover malformed/partial/valid outputs
[ ] docs updated
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Add AI coach output validator
```

## Next stage trigger

Stage 9 Coach-first UI starts after AI output is safe and structured.

---

# 17. Stage 9: Coach-first UI

## Objective

Make UI reflect the product idea:

```text
Match → facts → metrics → diagnosis → recommendation → next match verification → progress
```

Current issue:

```text
UI is partly stats/dashboard-first, not fully coach-first
```

## Scope

```text
[ ] inventory UI pages
[ ] coach page becomes primary
[ ] surface active recommendation
[ ] show whether previous recommendation was followed
[ ] show evidence and metric reliability
[ ] avoid noisy stats-first dashboard
[ ] no new backend architecture unless necessary
[ ] tests/smoke for pages
```

## Non-scope

```text
no viewer/heatmaps/clips
no public profiles
no payment
no friends/social expansion
```

## DoD

```text
[ ] coach-first flow visible
[ ] active recommendation prominent
[ ] progress/evaluation visible
[ ] limitations/reliability visible
[ ] existing auth/security boundaries preserved
[ ] smoke tests pass
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Add coach-first UI flow
```

## Next stage trigger

Stage 10 Friends alpha gate starts only after personal loop is usable.

---

# 18. Stage 10: Friends alpha gate

## Objective

Decide if project is safe/useful enough for a tiny controlled friends alpha.

## Scope

```text
[ ] security readiness checklist
[ ] backup/restore rehearsal
[ ] privacy/data boundaries
[ ] onboarding for 1-3 friends
[ ] manual account creation/invite policy
[ ] monitoring/logging minimum
[ ] known limitations page
[ ] rollback plan
```

## Non-scope

```text
no public SaaS launch
no paid subscriptions yet
no open registration
no marketing push
```

## DoD

```text
[ ] friends alpha checklist complete
[ ] owner/admin knows how to add/remove users
[ ] backup works
[ ] rollback works
[ ] known risks accepted
[ ] no public exposure without auth
[ ] review PASS/PASS_WITH_WARNINGS
[ ] commit: Prepare friends alpha gate
```

---

# 19. Stage 11+: SaaS path

Only after friends alpha shows value.

Future SaaS stages:

```text
[ ] true multi-user ownership
[ ] user_id in core tables through migrations
[ ] roles/admin
[ ] billing/subscriptions
[ ] quotas
[ ] background jobs per user
[ ] email/password reset
[ ] legal/privacy
[ ] public landing
[ ] monitoring/observability
[ ] horizontal scaling
```

Do not start SaaS work before:

```text
[✓] personal coach loop works
[✓] friends alpha feedback positive
[✓] core data model stable
[✓] migration discipline exists
```

---

# 20. How to generate a detailed TZ for any future stage

If no current ChatGPT curator exists, use this prompt in a new chat:

```text
Ты куратор проекта CS2 AI Coach. Мне нужно создать detailed TZ for Stage <N>: <NAME>.

Use this Master Curation Playbook as source of truth.

Current repo status:
<paste git log --oneline -10>
<paste git status --short>
<paste latest relevant stage review>

Historical archived stage task examples live under:
docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/STABILIZATION_STAGE_<N>_<NAME>_TZ_CS2_AI_COACH.md

It must include:
- status before stage
- objective
- non-goals
- scope
- acceptance criteria
- tests to add
- docs to update
- safe checks
- production DB safety rules
- implementation prompt
- review-only prompt
- commit instructions
- next stage trigger

Keep strict no feature creep.
```

---

# 21. If current chat dies

Open new chat and paste:

```text
Ты куратор проекта CS2 AI Coach. Отвечай строго по-русски.

Я продолжаю controlled hardening pipeline. Прочитай attached Master Curation Playbook.

Текущий known status:
[✓] Stage 0 Safety Foundation
[✓] Stage 1 Security P0
[✓] Stage 2 Ownership / enforced single-owner boundaries
[→] Stage 3 Migration discipline

Моя задача: продолжить с текущего stage, не потеряв process discipline.

Сначала попроси у меня:
- git status --short
- git log --oneline -10
- latest stage implementation/review report

Потом скажи:
- какой stage следующий;
- можно ли его начинать;
- какой prompt дать Codex;
- какие проверки нужны.
```

Attach these files:

```text
MASTER_CURATION_PLAYBOOK
docs/PROJECT_CONTROL.md
docs/CURRENT_STATUS.md
docs/CURRENT_MILESTONE.md
latest stage review reports
```

---

# 22. What to send curator after Codex finishes

Always send:

```bash
git status --short
git --no-pager diff --stat
sed -n '1,260p' docs/audit/STAGE_<N>_*_IMPLEMENTATION_REPORT.md
sed -n '1,280p' docs/audit/STAGE_<N>_*_REVIEW.md
```

And summary:

```text
pytest result
ruff result
git diff --check result
DB SHA
production jobs yes/no
commit yes/no
```

---

# 23. Decision table

## If implementation says PASS but no review

```text
Do not commit.
Run review-only pass.
```

## If review says PASS_WITH_WARNINGS

```text
Check Must Fix Before Next Stage.
If no blockers: commit.
If blockers: repair-only.
```

## If DB SHA changed unexpectedly

```text
STOP.
Do not commit.
Investigate.
Restore if needed.
```

## If Codex added out-of-scope feature

```text
STOP.
Revert or repair before commit.
```

## If git status is dirty before next stage

```text
Do not start next stage.
Commit/revert/current-stage repair first.
```

## If docs disagree with git

```text
Trust git + audit reports.
Repair docs before commit.
```

---

# 24. Brutal rule

The project does not need more “smart work”.  
It needs fewer uncontrolled changes.

Every stage must leave the repo in a better, smaller, more verifiable state.

If a change cannot be tested, reviewed, and committed separately, it does not belong in the current stage.
