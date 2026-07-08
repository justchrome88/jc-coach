# Stage 8 AI Validator Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 8 выполнен в заявленном scope: добавлен AI Output Validator без schema changes, без live AI calls, без production DB mutation и без production Steam/import/parser jobs. Structured AI output валидируется перед сохранением/display, unsupported Metric Truth claims отклоняются, invalid/free-form output сохраняется только как safe fallback.

Статус не `PASS`, потому что validator проверяет структуру, metric ids, Metric Truth usage policy и caveats, но не доказывает семантическую истинность каждого natural-language claim. Provider-specific structured response mode и prompt/version tracking также остаются future work. Это не blocker для post-Stage-8 full audit или Stage 9, если Stage 9 не требует deep semantic validator.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | AI output validation inventory exists and is accurate | PASS | `docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md` covers payload, prompt, provider, save/display surfaces and remaining risks. |
| 2 | AI output schema/policy documented | PASS | `docs/AI_COACH.md`, `docs/PROJECT_CONTROL.md`, `docs/CURRENT_MILESTONE.md` document schema and Metric Truth policy. |
| 3 | validator exists | PASS | `app/services/ai_validator.py` exists and is imported by `app/services/ai_coach.py`. |
| 4 | validator checks Metric Truth usage policy | PASS | `_validate_metric_claims()` uses `metric_definition()` and `usage_decision()`. |
| 5 | suppressed/unavailable metrics cannot become hard diagnosis/recommendation | PASS | Suppressed or unavailable metrics create `suppressed_metric_claim` error; tests cover `trade_kills` and `aim_rating`. |
| 6 | approximate metrics require caveats/warnings | PASS | `warn` usage without caveat creates `metric_requires_caveat`; test covers `kast`. |
| 7 | unknown metric ids are safe | PASS | Unknown ids create `unknown_metric_id` and fallback; test covers `imaginary_metric`. |
| 8 | invalid AI output has safe fallback | PASS | Invalid/free-form output returns fallback Markdown and `ai_validation.valid=false`; test covers save path. |
| 9 | tests are mocked and do not perform live AI calls | PASS | `tests/test_ai_validator.py` uses static dict/JSON/free-form strings; no provider endpoint is called. |
| 10 | no production Steam/import/parser jobs run | PASS | Review ran only requested safe pytest, ruff, diff check and SHA commands. |
| 11 | no production DB mutation | PASS | Production DB SHA unchanged. |
| 12 | no schema changes | PASS | No DB model, migration, index, constraint or startup schema helper changes. |
| 13 | full safe pytest passes | PASS | `APP_ENV=test .venv/bin/pytest tests -q`: `138 passed, 1 warning`. |
| 14 | ruff passes | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 15 | git diff --check passes | PASS | `git diff --check`: passed, no output. |
| 16 | no parser hardening | PASS | No parser modules changed and no parser jobs run. |
| 17 | no Steam cursor work | PASS | No Steam modules/docs changed in Stage 8 diff. |
| 18 | no recommendation planner | PASS | No planner/problem-selection logic added. |
| 19 | no ProblemSnapshot | PASS | No `ProblemSnapshot` model/service/table/doc contract added. |
| 20 | no UI redesign | PASS | No templates/CSS/frontend changes. |

## AI Validator Review

- Enforced schema/policy: top-level `summary`, `diagnoses[]`, `recommendations[]`, `warnings[]`, `evidence[]`, `confidence`; diagnoses require category/claim/evidence metrics/confidence/caveats; recommendations require category/action/rationale/target metrics/confidence/caveats.
- Invalid outputs rejected/fallback: empty output, non-JSON/free-form Markdown, missing required sections, invalid confidence, unknown metric ids, suppressed/unavailable metric usage, warn metrics without caveats.
- Metric Truth policy enforcement: validator resolves ids through `metric_definition()` and applies `usage_decision()` for `diagnosis`, `recommendation` and `ai`.
- Unsupported confident claims can still pass only in a narrow semantic sense: if a claim uses allowed metric ids and passes caveat rules, validator does not perform deep natural-language entailment. It does block unsupported metric ids and forbidden Metric Truth usage.
- Suppressed/unavailable metrics cannot support hard diagnosis/recommendation: yes, they fail validation before persistence/display.
- Approximate metrics require caveats/warnings: yes, `warn` usage without caveat fails validation.

## Live AI / Job Safety Review

- Live AI calls made: no.
- Production Steam/import/parser jobs run: no.
- Tests use only mocked outputs/providers: yes. Stage 8 tests use static mocked outputs and do not call `LocalLLMProvider.generate()` or `_post_json()`.

## Integration Review

- Changed in `ai_coach`: `save_ai_coach_result()` now validates raw AI output, renders valid structured JSON to Markdown, or saves safe fallback Markdown for invalid/free-form output; validation metadata and structured output are stored in existing `report_json`. Prompt now asks for strict JSON and caveats.
- This is minimal validator integration, not provider rewrite. `AIProvider`, `CodexCliHandoffProvider`, `LocalLLMProvider`, `_call_ollama()`, `_call_openai_compatible()` and `_post_json()` behavior are not rewritten.
- Invalid output fails safe: yes. It does not crash save path and is not accepted as confident coach advice.
- Existing AI coach page/job degrades safely: yes. Generated or pasted invalid output is saved as a clear fallback report, so page serialization/rendering can continue through existing report flow.

## Schema Change Review

No schema changes.

Confirmed:

- no `app/db/models.py` change;
- no migration/Alembic files;
- no tables/columns/indexes/constraints added;
- no startup `create_all()` / `_upgrade_sqlite_schema()` changes;
- validation metadata uses existing `coach_reports.report_json`;
- production DB SHA unchanged.

## Scope Creep Review

- Parser hardening: no.
- Steam cursor work: no.
- Recommendation planner: no.
- ProblemSnapshot: no.
- UI redesign: no.

## Changed Files Reviewed

Tracked Stage 8 diff reviewed:

- `app/services/ai_coach.py`
- `docs/AI_COACH.md`
- `docs/CHANGELOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/CURRENT_STATUS.md`
- `docs/METRICS.md`
- `docs/PROJECT_CONTROL.md`
- `docs/RECOMMENDATIONS.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`

Untracked Stage 8 files reviewed:

- `app/services/ai_validator.py`
- `docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md`
- `docs/audit/STAGE_8_AI_VALIDATOR_IMPLEMENTATION_REPORT.md`
- `docs/tasks/STABILIZATION_STAGE_8_AI_VALIDATOR_TZ_CS2_AI_COACH.md`
- `tests/test_ai_validator.py`

Checked and unchanged for Stage 8:

- `app/services/metric_truth.py`

## Test Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q
```

Result: `8 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q
```

Result: `16 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `138 passed, 1 warning`.

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

Production DB SHA unchanged from Stage 8 preflight and implementation report.

## Import/Steam/Parser Jobs Check

No production import, Steam or parser jobs were run.

No live AI provider calls were run. Review used only safe pytest, ruff, `git diff --check` and SHA checks.

## Remaining Risks

- Validator does not perform deep semantic/natural-language entailment over every claim.
- Provider-specific structured response enforcement is not implemented; prompt asks for JSON and validator enforces after generation/paste.
- Prompt and payload version tracking remain future work.
- Recommendation planner and ProblemSnapshot remain future work.
- Historical AI reports already in DB are not backfilled/revalidated.

## Must Fix Before Stage 9

No blocker found before Stage 9 if Stage 9 does not require deep semantic AI validation, provider-specific structured response mode or schema changes.

Recommended follow-ups:

- Add prompt/payload version tracking.
- Add provider-specific structured response mode when provider integration is hardened.
- Keep recommendation planner and ProblemSnapshot as a separate explicit stage.

## Can Proceed To Post-Stage-8 Full Audit

yes

## Can Proceed To Stage 9

yes
