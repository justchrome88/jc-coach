# WP-018-02 AI Coach Prompt/Payload Version Snapshot Report

Task ID: `WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`

Date: 2026-07-09

## Result

`PASS_WITH_WARNINGS`

AI coach runtime payloads, handoff metadata and persisted report JSON now carry
a deterministic prompt/payload/metric-registry contract snapshot. The change
uses the existing flexible `coach_reports.report_json` metadata and
`payload_snapshot`; no DB schema, production data, parser/import, evaluator,
service/deploy or recommendation behavior was changed.

Warnings remain because this task intentionally does not fix the remaining
WP-018 domain-constraints or semantic-validator gaps.

## Branch / HEAD

- Branch: `cona`
- HEAD: `0db3b58a21cb96e9d9b5f932f1322b100bf5bade`
- Initial `git status --short`: clean, no output.

## Changed Files

- `app/services/ai_coach.py`
- `app/services/metric_truth.py`
- `tests/test_ai_coach.py`
- `tests/test_ai_validator.py`
- `docs/AI_COACH.md`
- `docs/audit/WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT_REPORT.md`

## Implementation Summary

- Added deterministic AI coach contract constants for prompt version, payload
  schema version, snapshot generator and snapshot contract version.
- Added `METRIC_REGISTRY_VERSION` to the Metric Truth runtime registry without
  changing metric definitions, formulas, reliability or usage decisions.
- Added a `contract_snapshot` object to AI coach runtime payloads.
- Copied the same contract fields into Codex handoff metadata.
- Copied the same contract fields into persisted AI report metadata in
  `coach_reports.report_json`, alongside the existing full `payload_snapshot`
  and payload hash.
- Preserved validator fallback behavior: invalid/free-form output is still
  replaced by safe fallback Markdown while carrying the snapshot metadata.

## Version/Snapshot Fields Added

- `ai_coach_prompt_version`
- `ai_coach_payload_schema_version`
- `metric_registry_version`
- `snapshot_generated_by`
- `snapshot_contract_version`

Current deterministic values:

- `ai_coach_prompt_version`: `ai-coach-prompt-v1`
- `ai_coach_payload_schema_version`: `ai-coach-payload-v1`
- `metric_registry_version`: `metric-truth-v1`
- `snapshot_generated_by`: `app.services.ai_coach`
- `snapshot_contract_version`: `ai-coach-snapshot-v1`

## Tests Added/Updated

- `tests/test_ai_coach.py`
  - payload includes deterministic `contract_snapshot`;
  - repeated payload builds for the same input produce the same snapshot;
  - prompt/handoff metadata carries snapshot fields;
  - persisted report metadata carries snapshot fields;
  - weak metric suppression and unavailable crosshair-placement caveats remain
    present;
  - snapshot metadata does not introduce exact playlist/mode labels.
- `tests/test_ai_validator.py`
  - invalid/free-form AI output still uses validator fallback and still stores
    version/snapshot metadata.

## Checks Run

Preflight:

- `git status --short`: pass, no output.
- `git branch --show-current`: pass, `cona`.
- `git rev-parse HEAD`: pass,
  `0db3b58a21cb96e9d9b5f932f1322b100bf5bade`.

Targeted checks:

- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_ai_coach.py tests/test_ai_validator.py -q -p no:cacheprovider`:
  pass, `18 passed, 1 warning`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests -k "coach or ai or recommendation or metric" -p no:cacheprovider`:
  pass, `116 passed, 139 deselected, 1 warning`.

Local quality gate:

- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/local_quality_gate.py`:
  first two runs failed on Ruff formatting only after tests passed; formatting
  was corrected.
- Final rerun:
  `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/local_quality_gate.py`:
  pass, `LOCAL_QUALITY_GATE=PASS`.
  - semantic AI eval fixtures: `7 passed, 1 warning`;
  - golden metric readiness fixtures: `8 passed, 1 warning`;
  - full safe pytest: `255 passed, 1 warning`;
  - Ruff: pass;
  - `git diff --check`: pass;
  - project gate postflight: pass.

Known warning:

- Existing Starlette/TestClient deprecation warning from
  `.venv/lib/python3.14/site-packages/fastapi/testclient.py`.

## Safety Notes

- No DB schema changes.
- No production DB or data mutation.
- No parser/import/evaluator/manual evaluator jobs.
- No live Steam/Valve import.
- No service restart, deploy command or package/dependency change.
- No recommendation selection logic change.
- No metric formula, reliability or usage-policy change.
- No broad prompt/domain-constraint remediation beyond version/snapshot
  metadata.
- No `git add`, commit or push.

## Remaining WP-018 Gaps

- P0: runtime AI coach payload still needs a complete explicit CS2
  domain-constraints block, including playlist/mode, economy, positioning,
  clutch, trade, side and map-boundary constraints.
- P1: runtime validator remains weaker than the semantic evaluation contract;
  semantic entailment checks are still fixture-level rather than enforced at
  report persistence time.
- Provider-specific structured response enforcement remains shallow.

## Recommended Next Task

`WP-018-03_AI_COACH_DOMAIN_CONSTRAINTS_IN_RUNTIME_PAYLOAD`

Purpose: add the missing explicit CS2 domain-constraint block to the runtime AI
coach payload/prompt without changing recommendation logic, metrics, DB schema,
parser/import behavior, services or deployment.
