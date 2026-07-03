# Stage 6 Parser Hardening Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 6 выполнен в заявленном scope: parser facts стали честнее, `early_deaths` больше не является silent fallback из `entry_deaths`, parser confidence warnings расширены, production DB не изменялась, production parser/Steam/import jobs не запускались.

Статус не `PASS`, потому что это не full parser rewrite: trade graph, KAST trade component, side split inference, traded/untraded deaths и utility/flash attribution остаются limited и требуют later hardening.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | parser facts inventory exists and is accurate | PASS | `docs/audit/PARSER_FACTS_INVENTORY.md` covers Match summary, parser metadata, deep rounds, player rounds, duels, damage, grenades, AI payload and recommendations. |
| 2 | parser confidence limitations documented | PASS | Inventory and `docs/METRICS.md` document early-death timing anchors, KAST trade gap, trade/traded death, side split and utility/flash limitations. |
| 3 | `early_deaths` behavior is honest and not falsely trusted | PASS | `app/services/demo_parser.py` computes `early_deaths` only from timing anchors and keeps Metric Truth reliability `approximate`. |
| 4 | no silent `early_deaths=entry_deaths` hard claim | PASS | Previous assignment was removed; missing timing anchors now produce `None`, not `entry_deaths`. Tests cover this. |
| 5 | side split limitations remain honest | PASS | `side_stats` confidence remains `low`; `side_split_metrics` remains `low` and suppressed from diagnosis/recommendation. |
| 6 | `traded_deaths`/`untraded_deaths` not falsely treated as available | PASS | Parser confidence marks `traded_deaths` as `unavailable`; Metric Truth keeps `traded_deaths` unavailable and suppressed. |
| 7 | utility/flash facts reliability documented | PASS | `utility_damage` remains `medium`; flash facts remain `approximate`; parser confidence separates `utility` and `flash`. |
| 8 | Metric Truth Layer updated only where evidence supports it | PASS | No reliability was upgraded. Only `early_deaths` formula/limitation text was corrected to match parser behavior. |
| 9 | tests cover parser fact confidence behavior | PASS | `tests/test_parser_facts_confidence.py` covers early death anchors/fallback, trade/traded death suppression, side split policy, utility/flash limits and parser confidence warnings. |
| 10 | no DB schema changes | PASS | No model, migration, Alembic, index, constraint or startup schema helper changed. |
| 11 | production DB SHA unchanged | PASS | SHA remains `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`. |
| 12 | no production parser/Steam/import jobs run | PASS | Review ran only read commands, safe pytest, ruff, `git diff --check`, and SHA check. |
| 13 | full safe pytest passes | PASS | `APP_ENV=test .venv/bin/pytest tests -q`: `125 passed, 1 warning`. |
| 14 | ruff passes | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 15 | git diff --check passes | PASS | `git diff --check`: passed, no output. |
| 16 | no viewer/heatmaps/clips | PASS | No UI/media/viewer modules changed. |
| 17 | no Steam cursor work | PASS | No Steam import/cursor modules changed. |
| 18 | no AI validator | PASS | AI docs mention future validator only; no AI validator/provider/schema refactor was added. |
| 19 | no recommendation planner | PASS | No planner/problem snapshot logic added. |
| 20 | no UI redesign | PASS | No templates, CSS or frontend files changed. |

## Parser Facts Review

Improved parser facts:

- `early_deaths`: no longer equals `entry_deaths` by default. It is computed only when `round_freeze_end` or `round_start` timing anchors exist and the player's death tick is inside the early-round timing window.
- Parser confidence metadata: added/clarified `kast_trade_component`, `trade_kills`, `traded_deaths`, `flash`, and more explicit warnings.

Still approximate/low/unavailable:

- Approximate: `early_deaths`, `KAST`, `flash_assists`, `enemies_flashed`, `swing_score`.
- Low: `trade_kills`, `side_split_metrics`, `accuracy`.
- Unavailable: `traded_deaths`, `untraded_deaths`, `grenade_rating`, `aim_rating`, `crosshair_placement`.

Suppressed from hard diagnosis/recommendation:

- `trade_kills`
- `traded_deaths` / `untraded_deaths`
- `side_split_metrics`
- `accuracy`
- `grenade_rating`
- `aim_rating`
- `crosshair_placement`

No claims stronger than evidence were introduced. `early_deaths` confidence can become `medium` in parser metadata only when timing anchors produce a value, while Metric Truth remains conservative as `approximate`.

## Demo Parser Change Review

Changed in `app/services/demo_parser.py`:

- added `EARLY_DEATH_WINDOW_TICKS`;
- added `_early_deaths_from_timing()` and `_round_anchor_ticks()`;
- `parse_demo()` now sets `match["early_deaths"]` from timing-derived value or `None`;
- `_metric_confidence()` now accepts `early_deaths` and emits explicit weak-fact keys;
- `_parser_warnings()` now explains early-death anchor gaps, KAST trade component, traded deaths, side stats and utility/flash limitations.

This is допустимый Stage 6 scope: focused confidence/facts hardening, not a parser rewrite.

Production parsing risk: no new automatic production parsing path was added. Existing `parse_demo()` behavior changes only when a parser/import path is explicitly invoked; review did not run production parser jobs or reparse production demos.

Schema/contract changes: no DB schema changes. Runtime JSON payload has additional confidence keys/warnings and `early_deaths` may now be `None` instead of copied from `entry_deaths` when timing anchors are missing. That is an honesty correction within existing nullable fields/contracts.

Claims stronger than evidence: no. Reliability was not upgraded; weak facts remain warning/suppressed.

## Metric Truth Integration Review

Metric reliability changed:

- None.

Why evidence is sufficient:

- Evidence is sufficient only to correct `early_deaths` definition/limitations, because code now derives it from existing timing anchors when available and leaves it missing otherwise.

Reliability intentionally not raised:

- `early_deaths` remains `approximate` until timing window/tickrate behavior is validated against real fixture corpus.
- `trade_kills` remains `low`.
- `traded_deaths` / `untraded_deaths` remain `unavailable`.
- `side_split_metrics` remain `low`.
- `flash_assists` / `enemies_flashed` remain `approximate`.
- `grenade_rating` and `aim_rating` remain `unavailable`.

## Schema Change Review

No schema changes.

Confirmed:

- no changes to `app/db/models.py`;
- no migrations or Alembic changes;
- no indexes/constraints/tables/columns added;
- no startup `create_all()` / `_upgrade_sqlite_schema()` changes;
- production DB SHA unchanged.

Stage 6 does not need an approved migration path because there were no schema changes.

## Scope Creep Review

- Viewer/heatmap/clip work: no.
- Steam cursor work: no.
- AI validator: no.
- Recommendation planner: no.
- UI redesign: no.

## Changed Files Reviewed

Code reviewed:

- `app/services/demo_parser.py`
- `app/services/metric_truth.py`

Tests reviewed:

- `tests/test_parser_facts_confidence.py`

Docs reviewed:

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
- `docs/tasks/STABILIZATION_STAGE_6_PARSER_HARDENING_TZ_CS2_AI_COACH.md`

## Test Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
```

Result: `6 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
```

Result: `14 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `125 passed, 1 warning`.

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`.

```bash
git diff --check
```

Result: passed, no output.

## Production DB Check

```bash
sha256sum data/cs2_coach.db
```

Result:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

Production DB SHA unchanged.

## Import/Steam/Parser Jobs Check

No production import, Steam or parser jobs were run.

The full pytest suite ran with `APP_ENV=test` and Stage 0 test isolation. Parser-related tests use mocked/unit paths and do not parse production demo files.

## Remaining Risks

- `early_deaths` needs validation against real fixture corpus before any reliability upgrade.
- Trade graph is not implemented; `trade_kills` remains low confidence.
- `traded_deaths` / `untraded_deaths` remain unavailable.
- Side split/team inference remains low confidence.
- Utility/flash attribution remains best-effort.
- Diagnosis registry, recommendation planner and AI validator remain future work.

## Must Fix Before Stage 7

No blocker found before Stage 7 if Stage 7 is Steam cursor truth and does not depend on parser reliability upgrades.

Carry forward:

- do not upgrade parser-derived metric reliability without evidence;
- do not add schema changes without Stage 3 migration discipline;
- keep production parser jobs disabled during review/validation tasks.

## Can Proceed To Stage 7

yes
