# Stage 6 Parser Hardening Implementation Report

Дата: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 6 улучшил честность parser-derived facts без schema changes и без production parser/Steam/import jobs. Главная правка: parser больше не пишет `early_deaths = entry_deaths` silently. `early_deaths` заполняется только при наличии timing anchors; иначе остаётся `None` и warning/low confidence.

Статус не `PASS`, потому что trade graph, side split inference, KAST trade component, utility/flash attribution и AI/planner validation остаются later work.

## Parser Hardening Approach Chosen

Выбран conservative code/docs/tests approach:

- inventory текущих parser facts;
- minimal parser logic fix for `early_deaths`;
- clearer `metric_confidence` keys/warnings for weak parser facts;
- no DB schema changes;
- no production demo parsing;
- no reliability upgrades without evidence.

## Files Changed

- `app/services/demo_parser.py`
- `app/services/metric_truth.py`
- `tests/test_parser_facts_confidence.py`
- `docs/METRICS.md`
- `docs/RECOMMENDATIONS.md`
- `docs/AI_COACH.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_CONTROL.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`
- `docs/CHANGELOG.md`
- `docs/audit/PARSER_FACTS_INVENTORY.md`
- `docs/audit/STAGE_6_PARSER_HARDENING_IMPLEMENTATION_REPORT.md`

## Tests Added

`tests/test_parser_facts_confidence.py` covers:

- missing timing anchors do not produce fallback `early_deaths`;
- early death timing window counts only supported deaths;
- trade/traded death suppression;
- side split low-confidence policy;
- utility/flash/grenade reliability limits;
- parser confidence metadata for KAST trade component, traded deaths, side stats and flash.

## Safe Checks Results

Required Stage 6 checks passed:

```text
APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
6 passed

APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
14 passed

APP_ENV=test .venv/bin/pytest tests -q
125 passed, 1 warning

.venv/bin/ruff check .
All checks passed!

git diff --check
passed

sha256sum data/cs2_coach.db
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

## Production DB Touched

No.

## DB SHA Before/After

Before Stage 6:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

After Stage 6 checks:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

## Production Parser/Steam/Import Jobs Run

No.

## Schema Changes

No.

No models, migrations, indexes, constraints, Alembic files or startup schema helpers were changed.

## Remaining Risks

- `early_deaths` remains approximate because timing window and anchor availability need real-fixture validation before upgrade.
- `trade_kills` remains low confidence.
- `traded_deaths` / `untraded_deaths` remain unavailable.
- `side_split_metrics` remain low confidence.
- `flash_assists` / `enemies_flashed` remain approximate.
- Recommendation planner and AI validator are not implemented.

## Can Proceed To Stage 6 Review-Only

yes
