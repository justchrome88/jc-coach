# Stage 9 Coach-first UI Review

Дата review: 2026-07-03.

Scope: review-only проверка Stage 9. Код, тесты и существующие документы не изменялись. Создан только этот review report.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 9 проходит DoD: `/coach` стал coach-first страницей поверх существующего persisted state, без schema changes, без live AI/Steam/import/parser jobs, без planner/ProblemSnapshot и без скрытых write-side effects на GET.

Статус не `PASS`, потому что Stage 9 сознательно не закрывает recommendation planner: UI показывает current tracked recommendation из существующей active recommendation ordering/defaults, а не verified top problem.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---|---|---|---|
| 1 | `/coach` is coach-first, not stats-first | PASS | `app/templates/coach.html` теперь начинает страницу с `Current tracked recommendation`, next action, evidence/confidence, latest match и AI validation. Старые AI/report/stats блоки находятся ниже. |
| 2 | current tracked recommendation is visible | PASS | Template renders `Current tracked recommendation`, category, title, description, progress and counts from `coach_ui.current`. Test covers visible recommendation. |
| 3 | Honest label, not verified top problem | PASS | UI label is `Current tracked recommendation`; muted copy says `Это текущая отслеживаемая цель, не verified top problem.` |
| 4 | evidence/confidence/warnings visible | PASS | Evidence block renders metric name, id, reliability, usage decision, baseline/current/target and warning text. |
| 5 | Metric Truth approximate/low/unavailable warnings surfaced | PASS | `coach_ui.weak_metric_notes` includes `early_deaths`, `trade_kills`, `side_split_metrics`, `traded_deaths`; tests assert approximate/suppressed/unavailable labels. |
| 6 | next-match action visible | PASS | Template renders `Следующий матч` and `coach_ui.current.next_action`. Test covers marker. |
| 7 | progress/last evaluation visible if available | PASS | Hero renders completed/target, score, counts and `Last evaluation`; tests cover presence. |
| 8 | latest match coach summary visible if available | PASS | `coach_ui.latest_match` renders date/map/result/ADR/KAST/entry deaths and current goal evaluation state. Empty state is explicit. |
| 9 | AI validation/fallback status visible where relevant | PASS | `coach_ui.ai_validation` renders valid/fallback/unknown/no-report states. Tests cover valid and fallback reports. |
| 10 | empty states safe/honest | PASS | No recommendation shows `Нет отслеживаемой рекомендации`; no latest match says to import data; no AI report says no report and no page-render AI run. |
| 11 | GET `/coach` does not mutate recommendation/evaluation rows | PASS | `tests/test_coach_first_ui.py::test_get_coach_does_not_mutate_recommendation_or_evaluation_rows` passes; Stage 4 no-mutation tests still pass. |
| 12 | GET `/coach` does not call ensure/evaluate/import/AI/Steam/parser jobs | PASS | `coach_page` calls read helpers only. Test monkeypatches AI/Steam/parser job functions to fail if called and GET `/coach` passes. |
| 13 | no schema changes | PASS | No DB model/session/migration files changed; diff touches web route/template/CSS/docs/tests only. |
| 14 | no live AI/Steam/import/parser jobs | PASS | Review ran only requested pytest/ruff/diff/SHA checks. Tests use mocked/static paths. |
| 15 | no recommendation planner | PASS | No planner service/model added. UI explicitly says it is not verified top problem. |
| 16 | no ProblemSnapshot | PASS | No model/table/service/doc contract for `ProblemSnapshot` added. |
| 17 | no parser/Steam/AI engine scope creep | PASS | Parser/Steam/AI engine modules unchanged. Only AI validation metadata is read from existing report JSON. |
| 18 | no broad dashboard/UI redesign outside coach loop | PASS | Dashboard was not changed in Stage 9 diff. CSS additions are scoped to coach-first blocks. |
| 19 | tests pass | PASS | Targeted and full safe pytest passed. |
| 20 | ruff passes | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 21 | git diff --check passes | PASS | `git diff --check`: passed, no output. |
| 22 | production DB SHA unchanged | PASS | SHA after review checks: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`. |

## UI Truth Review

- Does UI overclaim: no. It does not claim a planner-selected primary problem.
- Does it call current tracked recommendation correctly: yes. The first card is labeled `Current tracked recommendation`.
- Are weak metrics labeled: yes. Evidence rows and Metric Truth warnings show reliability and usage decisions, including approximate/low/unavailable/suppressed.
- Does it avoid pretending planner/ProblemSnapshot exists: yes. The UI explicitly says this is not `verified top problem`, and no ProblemSnapshot/planner code exists.
- Are empty states honest: yes. No recommendation, no latest match and no AI report states are explicit and do not imply hidden work.

## Read/Write Safety Review

- Does GET `/coach` mutate DB: no evidence of mutation. New Stage 9 helper does not accept `Session`; tests verify recommendation/evaluation row counts unchanged.
- Does page render create recommendations/evaluations/reports: no. GET `/coach` does not call `ensure_default_recommendation(s)`, `evaluate_new_matches()`, `evaluate_match()` or `save_ai_coach_result()`.
- Does it call ensure/evaluate: no in GET path. Those calls appear only in tests setup and existing explicit write/import flows.
- Does it start AI/Steam/parser/import jobs: no. GET path reads `latest_ai_handoff`, `latest_ai_coach_report`, `ai_provider_health`, etc.; explicit POST buttons remain separate.
- Any hidden background side effects: no hidden background task added to GET `/coach`.

## app/web/routes.py Review

- What was added: `coach_ui` context and read-only helper functions: `_coach_first_view_model`, `_current_recommendation_card`, metric evidence formatting, latest match summary, AI validation status and weak metric notes.
- Is it read-only view-model code: yes. The new helper functions assemble dictionaries from already loaded matches/recommendation progress/evaluations/AI report metadata.
- Any route semantic changes: only GET `/coach` context/template presentation changed. Existing POST routes for AI and recommendation actions remain explicit.
- Any security/auth regression: no. Existing auth middleware and route protection are unchanged; `/coach` remains behind the existing web auth guard path.

## AI / Metric Truth UI Review

- AI validation/fallback status is surfaced through `coach_ui.ai_validation`, reading `coach_reports.report_json.ai_validation` when present.
- Valid structured reports show `Valid structured AI report`.
- Invalid/free-form reports show `Fallback AI report`.
- Old reports without validation metadata show `Validation status unknown`, which is honest.
- Metric Truth warnings are surfaced via `metric_definition`, `usage_decision` and `metric_warning`.
- Weak metrics are not presented as fully trusted; approximate/low/unavailable/suppressed states are visible.

## Scope Creep Review

- Schema changes: no.
- Planner: no.
- ProblemSnapshot: no.
- Parser hardening: no.
- Steam cursor/import work: no.
- Live AI/Steam/parser/import: no.
- UI redesign outside coach loop: no broad redesign. CSS additions are scoped to the new coach-first UI blocks.

## Changed Files Reviewed

Reviewed tracked diff:

- `app/web/routes.py`
- `app/templates/coach.html`
- `app/static/app.css`
- `docs/CHANGELOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/CURRENT_STATUS.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/PROJECT_CONTROL.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`

Reviewed untracked Stage 9 files:

- `tests/test_coach_first_ui.py`
- `docs/audit/COACH_UI_SURFACE_INVENTORY.md`
- `docs/audit/STAGE_9_COACH_FIRST_UI_IMPLEMENTATION_REPORT.md`
- `docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md`
- `docs/audit/FULL_PROJECT_AUDIT_AFTER_STAGE_8.md`

`docs/audit/FULL_PROJECT_AUDIT_AFTER_STAGE_8.md` is present and should be included in the Stage 9 commit: yes. Stage 9 implementation follows its restrictions: no schema changes, no live jobs/providers, no planner/ProblemSnapshot, no production DB mutation.

## Test Results

Commands run:

```bash
APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Results:

- `tests/test_coach_first_ui.py`: `7 passed, 1 warning`.
- Stage 4/8/9 subset: `20 passed, 1 warning`.
- Full safe pytest: `145 passed, 1 warning`.
- Ruff: `All checks passed!`.
- `git diff --check`: passed, no output.
- Production DB SHA: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`.

The warning is the existing `StarletteDeprecationWarning` from FastAPI/TestClient and is not Stage 9 behavior.

## Production DB Check

Production DB file:

```text
data/cs2_coach.db
```

SHA after review:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Production DB touched: no. No live AI calls, live Steam calls, production import jobs or production parser jobs were run.

## Remaining Risks

- Stage 9 is still not a recommendation planner.
- Current tracked recommendation can still be category/default-driven rather than selected from a verified top problem.
- AI validation status is shown, but old reports without Stage 8 metadata remain `Validation status unknown`.
- Metric Truth warnings are visible, but diagnosis registry/planner integration remains future work.
- Friends/public readiness remains blocked by broader ops/observability/release gates.

## Must Fix Before Stage 10

No Stage 9 blocker found.

Before Stage 10, define whether Stage 10 is recommendation planner / verified problem registry or another UI/process stage. If it touches planner, ProblemSnapshot or schema, require a separate migration/scope task first.

## Can Proceed To Stage 10

yes

Only if Stage 10 scope is explicit and does not silently combine planner, schema migration and UI work.
