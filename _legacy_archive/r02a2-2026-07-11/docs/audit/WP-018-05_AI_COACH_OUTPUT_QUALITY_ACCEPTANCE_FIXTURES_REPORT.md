# WP-018-05 AI Coach Output Quality Acceptance Fixtures Report

Task ID: `WP-018-05_AI_COACH_OUTPUT_QUALITY_ACCEPTANCE_FIXTURES`

Date: 2026-07-09

## Result

`PASS`

Added richer file-backed AI coach output-quality acceptance fixtures and tests
for accepted/rejected wording quality, caveats, evidence-chain completeness,
semantic overclaiming and safe fallback behavior.

No product logic, recommendation selection, metric formulas, DB/schema,
parser/import behavior, services, deployment config or package dependencies
were changed.

## Branch / HEAD

- Branch: `cona`
- HEAD: `d1d61d4e0a89b9caf8453503c91cb2dc5592df8b`
- Initial `git status --short`: clean, no output.

## Changed Files

- `tests/fixtures/ai_semantic_eval/output_quality_cases.json`
- `tests/test_ai_output_quality_fixtures.py`
- `docs/audit/WP-018-05_AI_COACH_OUTPUT_QUALITY_ACCEPTANCE_FIXTURES_REPORT.md`

## Fixture Coverage Added

Added explicit accepted fixture cases for:

- evidence-bound recommendation `#5` output with `metric_confidence`;
- complete `problem -> metric -> match -> recommendation` evidence chain;
- weak metric caveats for `early_deaths`, KAST and trade context;
- playlist/mode uncertainty without exact Premier/Competitive/Wingman claims;
- public/friends readiness blocked and `v0.9` not `v1.0`;
- unavailable economy, positioning, clutch, trade, parser-only match-date and
  crosshair-placement models stated as data gaps;
- fallback-safe no-data output that uses limitation/data-gap language and
  avoids hard advice.

Added explicit rejected fixture cases for:

- public/friends readiness and `v1.0` claims;
- exact Premier mode claim while playlist/mode is unknown/provenance-only;
- weak `early_deaths` hard advice without caveat;
- hard evaluation of legacy recommendation `#3` without refresh context;
- unsupported economy, positioning, clutch, trade, parser and exact match-date
  certainty;
- missing `metric_confidence` in claimed evidence;
- missing WP-018-02 version/snapshot metadata and WP-018-03 domain metadata in
  persisted/report context.

## Tests Added/Updated

Added `tests/test_ai_output_quality_fixtures.py`:

- parametrizes every output-quality fixture;
- asserts accepted fixtures pass runtime validation and deterministic semantic
  eval checks;
- asserts rejected fixtures expose expected issue codes;
- asserts validation issue messages and paths are diagnostic enough for
  debugging;
- asserts fixture coverage includes the required acceptance classes;
- verifies a missing-metadata rejected fixture persists through the existing
  safe fallback path with `ai_validation.valid=false`,
  `fallback_used=true` and no accepted `ai_structured_output`.

Existing UI valid/fallback states remain covered by `tests/test_coach_first_ui.py`.

## Checks Run

- `git status --short`: pass before work, no output.
- `git branch --show-current`: pass, `cona`.
- `git rev-parse HEAD`: pass,
  `d1d61d4e0a89b9caf8453503c91cb2dc5592df8b`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_ai_output_quality_fixtures.py -p no:cacheprovider`:
  pass, `11 passed, 1 warning`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_ai_validator.py tests/test_ai_coach.py tests/test_coach_first_ui.py -p no:cacheprovider`:
  pass, `36 passed, 1 warning`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests -k "coach or ai or recommendation or metric" -p no:cacheprovider`:
  pass, `137 passed, 139 deselected, 1 warning`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/local_quality_gate.py`:
  pass, `LOCAL_QUALITY_GATE=PASS`.
  - semantic AI eval fixtures: `7 passed, 1 warning`;
  - golden metric readiness fixtures: `8 passed, 1 warning`;
  - full safe pytest: `276 passed, 1 warning`;
  - Ruff: pass;
  - `git diff --check`: pass;
  - project gate preflight/changed/required-checks/postflight: pass.

Known warning:

- Existing Starlette/TestClient deprecation warning from
  `.venv/lib/python3.14/site-packages/fastapi/testclient.py`.

## Safety Notes

- No DB/schema/data file changes.
- No production DB mutation.
- No parser/import/evaluator/manual evaluator jobs.
- No live Steam/Valve import.
- No service restart, deploy command or package/dependency change.
- No recommendation selection logic change.
- No metric formula, reliability or usage-policy change.
- No public/friends readiness or `v1.0` claim.
- No playlist/mode caveat weakening.
- No Steam import cap change.
- No `git add`, commit or push.

## Remaining WP-018 Gaps

- Provider-specific structured response enforcement is still shallow; the app
  continues to validate after generation/paste rather than constraining every
  provider response mode upfront.
- Deterministic semantic fixtures now cover richer known unsafe classes, but
  they are still not a full natural-language entailment proof for every
  possible overclaiming phrasing.
- Wording calibration remains conservative and fixture-driven; accepted tone,
  phrasing and confidence wording can still be tightened in a dedicated
  calibration pass.

## Recommended Next Task

`WP-018-06_AI_COACH_OUTPUT_WORDING_CALIBRATION`

Reason: WP-018 now has version/snapshot metadata, domain constraints, runtime
semantic validator coverage and richer output-quality acceptance fixtures. The
next useful gap is calibrating accepted wording/tone and confidence phrasing
against these fixtures before considering provider-specific structured
response enforcement or closure review.
