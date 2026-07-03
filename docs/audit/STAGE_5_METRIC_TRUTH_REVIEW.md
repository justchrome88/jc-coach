# Stage 5 Metric Truth Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 5 реализован в заявленном scope: появился runtime Metric Truth Layer без schema changes, без production DB mutation, без import/Steam/parser jobs и без перехода в parser hardening, AI validator, planner или UI redesign.

Статус не `PASS`, потому что Stage 5 сознательно не закрывает parser confidence, diagnosis registry и recommendation planner. Existing rule-based diagnosis still has hardcoded thresholds; это задокументированный later risk, не blocker для Stage 6.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | metric truth inventory exists and is accurate | PASS | `docs/audit/METRIC_TRUTH_INVENTORY.md` описывает DB model, analytics, aim profile, mistake detection, recommendations, AI payload and parser fact surfaces. |
| 2 | metric truth/registry module exists | PASS | `app/services/metric_truth.py` содержит `MetricDefinition`, `METRIC_REGISTRY`, alias lookup and policy helpers. |
| 3 | core metrics have source/formula/reliability/limitations | PASS | Registry entries define source, formula, reliability and limitations for required core metrics. `tests/test_metric_truth.py` asserts these fields exist. |
| 4 | fallback/weak metrics are not treated as fully trusted | PASS_WITH_WARNING | Registry marks `early_deaths` approximate, `trade_kills` low, `traded_deaths` unavailable, side split low. Recommendation hard-signal helpers reject non-`allowed` metrics. Existing rule-based diagnosis remains partial and documented as later work. |
| 5 | `early_deaths` limitations are explicit | PASS | Registry and `docs/METRICS.md` state historical fallback-to-`entry_deaths` risk; recommendation scoring no longer substitutes missing `early_deaths` with `entry_deaths`. |
| 6 | side split reliability limitations are explicit | PASS | `side_split_metrics` is `low`, display `warn`, diagnosis/recommendation `suppressed`; docs call side switching/team inference low confidence. |
| 7 | unknown metric behavior is safe | PASS | Unknown ids return `UNKNOWN_METRIC` with `unavailable` reliability and all usage suppressed; test covers this. |
| 8 | usage/suppression policy exists for display/diagnosis/recommendation/AI | PASS | `MetricUsage` includes all four usages; decisions are `allowed`, `warn`, `suppressed`; helpers expose allowed/hard-claim/suppressed behavior. |
| 9 | tests cover trusted/approximate/low/unavailable/unknown behavior | PASS | `tests/test_metric_truth.py` covers trusted K/D, approximate KAST and early deaths, low trade/side split, unavailable traded deaths and unknown metric behavior. |
| 10 | `docs/METRICS.md` no longer placeholder | PASS | File now contains current truth, reliability levels, usage decisions, core metric table, runtime policy, current integration and next work. |
| 11 | no DB schema changes | PASS | No changes to `app/db/models.py`, `app/db/session.py`, migrations, Alembic files, indexes or constraints. |
| 12 | production DB SHA unchanged | PASS | SHA remains `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`. |
| 13 | import/Steam/parser production jobs not run | PASS | Review ran only read commands, pytest with `APP_ENV=test`, ruff, `git diff --check`, and `sha256sum`. |
| 14 | full safe pytest passes | PASS | `APP_ENV=test .venv/bin/pytest tests -q`: `119 passed, 1 warning`. |
| 15 | ruff passes | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 16 | git diff --check passes | PASS | `git diff --check`: passed, no output. |
| 17 | no parser hardening | PASS | No parser modules changed; parser is referenced only as source/limitation metadata. |
| 18 | no Steam cursor work | PASS | No Steam import/cursor modules changed. |
| 19 | no AI validator/provider/schema-output refactor | PASS | `ai_coach.py` only adds metric truth metadata to payload and one prompt rule. Provider classes and output persistence/validation flow are unchanged. |
| 20 | no recommendation planner | PASS | Recommendation changes only add hard-claim gating/warnings; no primary problem snapshot or planner selection was added. |
| 21 | no UI redesign | PASS | No templates, CSS or frontend files changed. |

## Metric Truth Review

Trusted metrics:

- `result` / `winrate`
- `round_score`
- `kills`
- `deaths`
- `kd_ratio`

Medium metrics:

- `assists`
- `adr`
- `kills_per_round`
- `deaths_per_round`
- `headshot_rate`
- `entry_kills`
- `entry_deaths`
- `utility_damage`

Approximate metrics:

- `kast`
- `hltv_rating`
- `early_deaths`
- `flash_assists`
- `enemies_flashed`
- `swing_score`

Low/unavailable metrics:

- Low: `trade_kills`, `accuracy`, `side_split_metrics`
- Unavailable: `traded_deaths`, `grenade_rating`, `aim_rating`, `crosshair_placement`

Suppressed from hard diagnosis/recommendation:

- Diagnosis suppressed: `trade_kills`, `traded_deaths`, `grenade_rating`, `aim_rating`, `accuracy`, `side_split_metrics`, `crosshair_placement`
- Recommendation suppressed: same list.
- `early_deaths`, `kast`, `hltv_rating`, `flash_assists`, `enemies_flashed`, `swing_score` are warning metrics, not hard-claim metrics.

Metrics that can still look more precise than they are:

- Existing rule-based diagnosis and UI surfaces still display `KAST`, `entry_deaths`, `utility_damage`, `flash_assists`, `swing_score` and side stats in places that do not yet surface the full Metric Truth metadata.
- This is acceptable for Stage 5 as `PASS_WITH_WARNINGS`, because the registry and docs now define truth, recommendation hard signals are gated, and diagnosis registry/UI confidence display are later stages.

## AI Scope Review

Changed in `app/services/ai_coach.py`:

- imported `metric_truth_payload` and `suppressed_metrics_for_usage`;
- added `metric_truth` block to AI payload with selected definitions and suppressed lists;
- added one prompt rule: suppressed metrics must not become confident diagnosis/recommendations.

This is допустимое подключение metric truth metadata, not scope creep.

AI validator: no.

Provider refactor: no.

Schema-output refactor: no. AI output remains free-form Markdown; docs keep validator/schema as future work.

## Recommendation Scope Review

Changed in `app/services/recommendation_tracking.py`:

- imports Metric Truth helpers;
- survival target/rules mark `early_deaths` as warning-only;
- `_match_evidence()` no longer falls back missing `early_deaths` to `entry_deaths`;
- `_match_evidence()` includes metric truth warnings;
- compare helpers reject metrics that are not allowed for hard recommendation claim.

This is usage/suppression policy integration, not planner.

No implicit DB writes in read paths were reintroduced. The changed functions are in explicit recommendation creation/evaluation paths; Stage 4 read helpers remain query-only.

## Schema Change Review

No schema changes.

Confirmed:

- no DB model changes;
- no migration files;
- no Alembic changes;
- no startup `create_all()` / `_upgrade_sqlite_schema()` changes;
- no production DB mutation.

Stage 5 does not need an approved migration path because it is code/config/docs only.

## Scope Creep Review

- Parser hardening: no.
- Steam cursor work: no.
- AI validator: no.
- Recommendation planner: no.
- UI redesign: no.

## Changed Files Reviewed

Code reviewed:

- `app/services/metric_truth.py`
- `app/services/recommendation_tracking.py`
- `app/services/ai_coach.py`

Tests reviewed:

- `tests/test_metric_truth.py`

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
- `docs/audit/METRIC_TRUTH_INVENTORY.md`
- `docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md`
- `docs/tasks/STABILIZATION_STAGE_5_METRIC_TRUTH_TZ_CS2_AI_COACH.md`

## Test Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
```

Result: `8 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
```

Result: `13 passed, 1 warning`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `119 passed, 1 warning`.

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

No import, Steam or parser production jobs were run.

The full pytest suite ran with `APP_ENV=test` and Stage 0 test isolation. Existing tests may import modules with mocked/unit paths, but no production import/Steam/parser job was started.

## Remaining Risks

- Parser facts still need hardening for true early-death timing, traded/untraded deaths, KAST trade component, side switching and utility attribution.
- Diagnosis registry is not implemented; existing rule-based diagnosis remains threshold-based.
- Recommendation planner is not implemented; multi-category defaults remain.
- AI output is still free-form and unvalidated.
- Some UI/read surfaces can display metrics without surfacing full Metric Truth metadata.
- `docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md` contains a stale sentence saying final checks are recorded in the final assistant report, though the same section already records the checks. This is cosmetic and not a Stage 5 blocker.

## Must Fix Before Stage 6

No blocker found before Stage 6 if Stage 6 is parser confidence hardening and stays within the documented scope.

Recommended to carry forward:

- keep Metric Truth Layer as the consumer-facing confidence contract while parser facts are hardened;
- update registry reliability only when parser evidence actually improves;
- do not introduce schema changes without Stage 3 migration discipline.

## Can Proceed To Stage 6

yes
