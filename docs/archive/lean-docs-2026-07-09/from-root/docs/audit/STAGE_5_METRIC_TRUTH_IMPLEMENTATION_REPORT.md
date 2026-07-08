# Stage 5 Metric Truth Implementation Report

Дата: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 5 реализован как code/config/docs layer без schema changes. Добавлен runtime registry метрик, reliability/usage policy, тесты и минимальная интеграция в recommendation/AI paths.

Статус не `PASS`, потому что это не parser hardening, не diagnosis registry и не recommendation planner. Часть метрик остаётся approximate/low/unavailable до следующих этапов.

## Metric Truth Approach Chosen

Выбран dataclass registry в `app/services/metric_truth.py`.

Причины:

- не требует DB schema changes;
- работает как deterministic source of truth для кода;
- unknown metric возвращает safe `unavailable`;
- policy можно тестировать без БД и runtime jobs;
- later parser hardening сможет обновлять reliability без миграций.

## Files Changed

- `app/services/metric_truth.py`
- `app/services/recommendation_tracking.py`
- `app/services/ai_coach.py`
- `tests/test_metric_truth.py`
- `docs/METRICS.md`
- `docs/RECOMMENDATIONS.md`
- `docs/AI_COACH.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_CONTROL.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`
- `docs/CHANGELOG.md`
- `docs/audit/METRIC_TRUTH_INVENTORY.md`
- `docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md`

## Tests Added

`tests/test_metric_truth.py` covers:

- required core registry entries;
- trusted metric hard-claim behavior;
- approximate metric warning behavior;
- low/unavailable suppression;
- `early_deaths` fallback risk;
- side split suppression;
- unknown metric safe behavior;
- serializable/deduplicated payload.

## Safe Checks Results

Required Stage 5 checks passed:

```text
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
8 passed

APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
13 passed, 1 warning

APP_ENV=test .venv/bin/pytest tests -q
119 passed, 1 warning

.venv/bin/ruff check .
All checks passed!

git diff --check
passed

sha256sum data/cs2_coach.db
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Final required checks are recorded in the final assistant report after execution.

## Production DB Touched

No.

## DB SHA Before/After

Before Stage 5:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

After Stage 5 checks:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

## Import/Steam/Parser Jobs Run

No.

## Schema Changes

No.

No models, migrations, indexes, constraints, Alembic files or startup schema helpers were changed.

## Remaining Risks

- Existing rule-based diagnosis still has hardcoded thresholds and is not a formal diagnosis registry.
- Recommendation planner still does not choose one primary recommendation from verified problem snapshot.
- Parser confidence still needs hardening for early deaths, KAST/trade, side splits and utility attribution.
- AI output remains free-form and unvalidated.

## Can Proceed To Stage 5 Review-Only

yes
