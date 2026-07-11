# WP-018-03 AI Coach Domain Constraints In Runtime Payload Report

Task ID: `WP-018-03_AI_COACH_DOMAIN_CONSTRAINTS_IN_RUNTIME_PAYLOAD`

Date: 2026-07-09

## Result

`PASS_WITH_WARNINGS`

Runtime AI coach payloads, Codex handoff metadata and persisted AI coach report
metadata now carry an explicit deterministic CS2 domain constraints contract.
The prompt also points the AI at the runtime contract and states the main
unsupported-claim boundaries.

Warnings remain because this task intentionally does not close the remaining
WP-018 semantic-validator gap. Runtime validation is still schema/Metric Truth
focused and weaker than the semantic eval contract.

## Branch / HEAD

- Branch: `cona`
- HEAD: `cbc4515e6f01897d690ca3a0fb7f4266ba96fc9a`
- Initial `git status --short`: clean, no output.

## Changed Files

- `app/services/ai_coach.py`
- `tests/test_ai_coach.py`
- `tests/test_ai_validator.py`
- `docs/AI_COACH.md`
- `docs/audit/WP-018-03_AI_COACH_DOMAIN_CONSTRAINTS_IN_RUNTIME_PAYLOAD_REPORT.md`

## Implementation Summary

- Added `AI_COACH_DOMAIN_CONTRACT_VERSION`.
- Added deterministic `_ai_coach_domain_contract()` metadata with the required
  runtime keys:
  - `domain_contract_version`
  - `domain_constraints`
  - `claim_guardrails`
  - `metric_confidence_policy`
  - `playlist_mode_policy`
  - `recommendation_policy`
  - `public_readiness_policy`
- Included the domain contract in `build_ai_coach_payload()`.
- Copied the same domain contract into Codex handoff metadata.
- Copied the same domain contract into persisted `coach_reports.report_json`
  metadata and kept the full `payload_snapshot`.
- Updated prompt instructions to obey the runtime domain policies and treat
  unsupported CS2 concepts as data gaps unless accepted payload evidence exists.
- Preserved the WP-018-02 version/snapshot fields:
  `ai_coach_prompt_version`, `ai_coach_payload_schema_version`,
  `metric_registry_version`, `snapshot_generated_by` and
  `snapshot_contract_version`.

## Domain Constraints Added

The runtime contract now explicitly carries:

- product status: `v0.9`, `v1.0` not claimed;
- recommendation status: recommendation `#5` is the current accepted active
  hard recommendation;
- legacy recommendation status: `#1`, `#3` and `#4` are blocked from new hard
  evaluations unless refreshed;
- Steam import cap: `1`;
- weak-metric policy: weak metrics and missing `metric_confidence` cannot
  support hard advice and must remain caveated;
- playlist/mode policy: mode remains unknown or provenance-only, with only
  `mode_unknown`, `provenance_demo` and `provenance_valve_matchmaking` accepted
  as current labels;
- unsupported-claim boundaries: no invented parser data, exact playlist labels,
  match dates, confidence, economy model, positioning model, clutch model,
  trade model, crosshair-placement diagnosis or map-specific certainty;
- public/friends status: blocked, with no public/friends readiness claim.

## Tests Added/Updated

- `tests/test_ai_coach.py`
  - verifies payload domain constraints are present;
  - verifies the domain constraints are deterministic across repeated payload
    builds for the same input;
  - verifies WP-018-02 version/snapshot fields remain present;
  - verifies prompt/handoff metadata carries the domain contract;
  - verifies weak-metric caveats and suppressed/unavailable metric boundaries
    remain visible;
  - verifies playlist/mode uncertainty remains explicit;
  - verifies public/friends and `v1.0` readiness claims remain false/blocked;
  - verifies persisted report metadata carries the same domain contract as the
    payload snapshot.
- `tests/test_ai_validator.py`
  - verifies validator fallback still persists safe fallback output and now
    also stores the domain contract metadata.

## Checks Run

Preflight:

- `git status --short`: pass, no output.
- `git branch --show-current`: pass, `cona`.
- `git rev-parse HEAD`: pass,
  `cbc4515e6f01897d690ca3a0fb7f4266ba96fc9a`.

Targeted checks:

- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_ai_coach.py tests/test_ai_validator.py -q -p no:cacheprovider`:
  pass, `19 passed, 1 warning`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests -k "coach or ai or recommendation or metric" -p no:cacheprovider`:
  pass, `117 passed, 139 deselected, 1 warning`.

Local quality gate:

- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/local_quality_gate.py`:
  pass, `LOCAL_QUALITY_GATE=PASS`.
  - semantic AI eval fixtures: `7 passed, 1 warning`;
  - golden metric readiness fixtures: `8 passed, 1 warning`;
  - full safe pytest: `256 passed, 1 warning`;
  - Ruff: pass;
  - `git diff --check`: pass;
  - project gate preflight/changed/required-checks/postflight: pass.

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
- No semantic-validator broadening beyond fallback metadata assertions.
- No public/friends readiness or `v1.0` claim.
- No Steam import cap change.
- No `git add`, commit or push.

## Remaining WP-018 Gaps

- P1: runtime validator remains weaker than the semantic evaluation contract;
  semantic entailment checks are still fixture-level rather than enforced at
  report persistence time.
- Provider-specific structured response enforcement remains shallow.

## Recommended Next Task

`WP-018-04_AI_COACH_SEMANTIC_VALIDATOR_CONTRACT`

Purpose: align the runtime AI output validator contract with the existing
semantic AI eval expectations without changing recommendation selection,
metric formulas, DB schema, parser/import behavior, services or deployment.
