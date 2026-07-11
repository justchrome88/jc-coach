# WP-018-04 AI Coach Semantic Validator Contract Report

Task ID: `WP-018-04_AI_COACH_SEMANTIC_VALIDATOR_CONTRACT`

Date: 2026-07-09

## Result

`PASS`

Runtime AI coach persistence now validates structured AI output against the
current semantic coach contract when a payload snapshot is available. Invalid
semantic output uses the existing safe fallback Markdown path and keeps
validator metadata in `coach_reports.report_json`.

No recommendation selection, metric formula, parser/import behavior, DB schema,
service/deploy config or package/dependency behavior was changed.

## Branch / HEAD

- Branch: `cona`
- HEAD: `5a9bcf01f5dba1def67eb0a026678dc8fcfcf1dd`
- Initial `git status --short`: clean, no output.

## Changed Files

- `app/services/ai_validator.py`
- `app/services/ai_coach.py`
- `tests/test_ai_validator.py`
- `tests/test_coach_first_ui.py`
- `docs/AI_COACH.md`
- `docs/audit/WP-018-04_AI_COACH_SEMANTIC_VALIDATOR_CONTRACT_REPORT.md`

## Implementation Summary

- Extended `validate_ai_coach_output()` to accept an optional runtime
  `payload_snapshot`.
- `save_ai_coach_result()` now builds or uses the payload snapshot before
  validation and passes it into the validator.
- The validator still performs the existing schema and Metric Truth checks.
- When runtime context is present, the validator also checks snapshot/domain
  metadata and conservative semantic claim boundaries.
- Valid structured output still renders and persists as before.
- Invalid semantic output falls back through the same safe fallback Markdown
  path used for malformed/free-form output.
- Updated the AI prompt and `docs/AI_COACH.md` so evidence items carry
  `metric_confidence` and optional evidence-chain fields when available.

## Semantic Validator Checks Added

- Required WP-018-02 metadata:
  `ai_coach_prompt_version`, `ai_coach_payload_schema_version`,
  `metric_registry_version`, `snapshot_generated_by` and
  `snapshot_contract_version`.
- Required WP-018-03 domain contract fields:
  `domain_contract_version`, `domain_constraints`, `claim_guardrails`,
  `metric_confidence_policy`, `playlist_mode_policy`,
  `recommendation_policy` and `public_readiness_policy`.
- Public/friends readiness and `v1.0` readiness claims are rejected.
- Exact playlist/mode claims such as Premier, Competitive, Wingman, Casual,
  Deathmatch, FACEIT or custom are rejected while mode remains
  unknown/provenance-only.
- Evidence for claimed metrics must include `metric_confidence` when runtime
  context is supplied.
- Weak/warn/low/unavailable metric hard advice without visible caveats is
  rejected.
- Legacy recommendations `#1`, `#3` and `#4` are rejected for new hard
  evaluations unless the output explicitly caveats refresh/audit context.
- Unsupported invented CS2 concepts are rejected from claim/action/rationale
  text when not phrased as unavailable/data-gap context, including economy,
  positioning, clutch, hard trade, parser-only facts and exact match-date
  claims.

## Tests Added/Updated

- `tests/test_ai_validator.py`
  - valid structured output with runtime semantic context passes;
  - public/friends and `v1.0` readiness claims fail;
  - unsupported exact playlist/mode claims fail;
  - weak metric hard advice without caveats fails;
  - legacy recommendation hard evaluation fails;
  - unsupported invented economy model claim fails;
  - missing version/snapshot/domain metadata fails;
  - semantic invalid JSON persists safe fallback and metadata;
  - valid persisted AI report keeps WP-018-02 and WP-018-03 metadata.
- `tests/test_coach_first_ui.py`
  - valid AI report fixture now includes `metric_confidence` so the `/coach`
    valid-validation state remains covered under the stricter runtime
    contract.

## Checks Run

Preflight:

- `git status --short`: pass, no output.
- `git branch --show-current`: pass, `cona`.
- `git rev-parse HEAD`: pass,
  `5a9bcf01f5dba1def67eb0a026678dc8fcfcf1dd`.

Targeted checks:

- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_ai_validator.py tests/test_ai_coach.py -p no:cacheprovider`:
  pass, `28 passed, 1 warning`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests -k "coach or ai or recommendation or metric" -p no:cacheprovider`:
  pass, `126 passed, 139 deselected, 1 warning`.

Local quality gate:

- First run failed on Ruff only:
  `E501 Line too long` in `app/services/ai_validator.py`; the line was
  wrapped.
- Final rerun:
  `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/local_quality_gate.py`:
  pass, `LOCAL_QUALITY_GATE=PASS`.
  - semantic AI eval fixtures: `7 passed, 1 warning`;
  - golden metric readiness fixtures: `8 passed, 1 warning`;
  - full safe pytest: `265 passed, 1 warning`;
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
- No public/friends readiness or `v1.0` claim.
- No playlist/mode caveat weakening.
- No Steam import cap change.
- No `git add`, commit or push.

## Remaining WP-018 Gaps

- Provider-specific structured response enforcement remains shallow; the app
  still asks for JSON and validates after generation/paste.
- Semantic checks are deterministic and conservative, not full natural-language
  entailment. They reject core known unsafe claim classes but do not prove every
  possible phrasing is semantically perfect.
- Output quality acceptance fixtures are still limited to the existing local
  semantic eval set plus targeted runtime validator tests.

## Recommended Next Task

`WP-018-05_AI_COACH_OUTPUT_QUALITY_ACCEPTANCE_FIXTURES`

Purpose: add richer accepted/rejected AI coach output fixtures and acceptance
coverage for wording quality, caveats, evidence-chain completeness and
semantic overclaiming without changing recommendation selection, metrics,
DB/schema, parser/import behavior, services or deployment.
