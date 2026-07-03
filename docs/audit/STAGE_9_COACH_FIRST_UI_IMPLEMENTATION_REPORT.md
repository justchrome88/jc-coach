# Stage 9 Coach-first UI Implementation Report

Дата: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 9 выполнен как presentation/usability layer поверх существующих persisted state/services. `/coach` стал action-first страницей: current tracked recommendation, next-match action, evidence/confidence, Metric Truth warnings, progress/last evaluation, latest match summary and AI validation status are visible.

Статус не `PASS`, потому что это не recommendation planner и не ProblemSnapshot. Current recommendation всё ещё берётся из существующего active recommendation ordering/defaults.

## UI Approach Chosen

- Создан read-only view model helper `app/web/routes.py::_coach_first_view_model`.
- Верх `/coach` перестроен вокруг `Current tracked recommendation`.
- UI явно говорит: это текущая отслеживаемая цель, не `verified top problem`.
- Evidence/confidence берётся из Metric Truth Layer через runtime registry.
- Weak facts показываются как warning/suppressed/unavailable, а не hard claims.
- AI validation status читается из существующего `coach_reports.report_json`.
- AI/Steam/import/parser actions не запускаются на page render; POST actions остались явными.

## Files Changed

- `app/web/routes.py`
- `app/templates/coach.html`
- `app/static/app.css`
- `tests/test_coach_first_ui.py`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/CHANGELOG.md`
- `docs/audit/COACH_UI_SURFACE_INVENTORY.md`
- `docs/audit/STAGE_9_COACH_FIRST_UI_IMPLEMENTATION_REPORT.md`

Note: pre-existing untracked files before Stage 9 were `docs/audit/FULL_PROJECT_AUDIT_AFTER_STAGE_8.md` and `docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md`.

## Tests Added

Added `tests/test_coach_first_ui.py`.

Coverage:

- `/coach` renders for authenticated owner.
- Safe empty state when no recommendation/matches exist.
- Current tracked recommendation is visible.
- UI does not claim `verified top problem`.
- Next-match action and last evaluation are visible.
- Metric Truth warnings for approximate/low/unavailable metrics are surfaced.
- AI validation/fallback status is visible.
- GET `/coach` does not mutate recommendation/evaluation rows.
- Page render does not call live AI/Steam/parser/import job functions.

## Safe Checks Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
```

Result: `7 passed, 1 warning`.

```bash
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
```

Result: `20 passed, 1 warning`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `145 passed, 1 warning`.

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`.

```bash
git diff --check
```

Result: passed, no output.

```bash
sha256sum data/cs2_coach.db
```

Result:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

## Production DB Touched

No.

Production DB SHA before Stage 9:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Production DB SHA after safe checks:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

## Live AI/Steam/Parser/Import Jobs Run

No.

- No live AI provider calls.
- No live Steam calls.
- No production import jobs.
- No production parser jobs.
- No hidden background jobs from GET `/coach`.

## Schema Changes

No.

- No DB models changed.
- No migrations added.
- No tables/columns/indexes/constraints added.
- No startup schema helper changes.

## Remaining Risks

- Stage 9 is not recommendation planner.
- Stage 9 does not create ProblemSnapshot or verified top problem.
- Current recommendation ordering/defaults remain from existing recommendation tracking.
- Metric Truth warnings are visible, but diagnosis registry and planner integration remain future work.
- AI validation status covers saved reports with Stage 8 metadata; old reports can still show unknown validation status.
- Friends/public readiness remains blocked by broader ops/observability/release gates.

## Can Proceed To Stage 9 Review-only

yes
