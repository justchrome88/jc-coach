# FH-090_095 First Semantic AI Eval Suite Core Cases Batch Report

Date: 2026-07-08

Task: FH-090_095 Macro-batch E1 - first semantic AI eval suite and core cases

Executor verdict: BLOCKED

## Result

Implementation work for the first deterministic local semantic AI eval suite was completed, but batch acceptance is blocked because the required command
`.venv/bin/python scripts/local_quality_gate.py` stalled during the full safe pytest phase and was interrupted.

Per task-card rule, a stalled required check prevents a `PASS` claim.

## Per-FH Verdicts

| FH ID | Verdict | Evidence |
|---|---|---|
| FH-090 | BLOCKED | First semantic eval suite exists in `tests/semantic_ai_eval.py`, `tests/test_semantic_ai_eval.py` and `tests/fixtures/ai_semantic_eval/e1_cases.json`; focused suite passed. Required local quality gate stalled. |
| FH-091 | BLOCKED | Overclaim fixture `fh091_overclaim_unsupported_hard_claim` catches unsupported hard claims and overstated advice confidence. Required local quality gate stalled. |
| FH-092 | BLOCKED | Hallucinated metric fixture `fh092_hallucinated_metric_absent_from_payload` catches a registered metric absent from supplied evidence. Required local quality gate stalled. |
| FH-093 | BLOCKED | Weak-metric caveat fixture `fh093_weak_metric_missing_caveat` catches missing caveats for weak/warn evidence. Required local quality gate stalled. |
| FH-094 | BLOCKED | No-data fixture `fh094_no_data_fallback_blocks_hard_advice` catches unsafe no-data confidence, advice and missing data-gap warning. Required local quality gate stalled. |
| FH-095 | BLOCKED | Valid and negative advice-confidence fixtures verify metric confidence and problem -> metric -> match -> recommendation evidence-link expectations. Required local quality gate stalled. |

Batch verdict: BLOCKED. The batch verdict is no better than the weakest included FH verdict.

## Files Changed

- `tests/semantic_ai_eval.py`
- `tests/test_semantic_ai_eval.py`
- `tests/fixtures/ai_semantic_eval/e1_cases.json`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-090_095_first-semantic-ai-eval-suite-core-cases-batch_report.md`

## Implementation Summary

Added a test-side deterministic semantic evaluator for structured AI coach output. The evaluator is local-only and makes no AI/API/network calls.

The evaluator checks:

- schema validation issues from the existing AI validator;
- hard-claim wording against supplied evidence confidence;
- hallucinated metrics that are registered but absent from the supplied evidence payload;
- missing caveats for weak/warn/low-confidence metrics;
- no-data fallback behavior;
- advice confidence not exceeding metric confidence;
- metric confidence on evidence items;
- evidence-link presence for `problem -> metric -> match -> recommendation`.

Added E1 fixtures covering:

- a clean valid Batch D contract case;
- unsupported hard overclaim;
- hallucinated metric;
- weak metric with missing caveat;
- unsafe no-data fallback;
- missing metric confidence and evidence link.

## Checks

Command:

```bash
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_semantic_ai_eval.py -q -p no:cacheprovider
```

Output:

```text
.......                                                                  [100%]
7 passed in 0.10s
```

Command:

```bash
.venv/bin/ruff check . --no-cache
```

Output:

```text
All checks passed!
```

Command:

```bash
git diff --check
```

Output:

```text
PASS (no output)
```

Required command:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

Observed output before stall:

```text
LOCAL_QUALITY_GATE_ROOT=/opt/jc-coach

## project gate preflight
$ .venv/bin/python scripts/project_gate.py preflight
...
RESULT: PASS

## project gate changed
$ .venv/bin/python scripts/project_gate.py changed
...
RESULT: PASS

## project gate required checks
$ .venv/bin/python scripts/project_gate.py required-checks
...
RESULT: PASS

## full safe pytest
$ APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
.....................................
```

The command produced no further output across repeated waits after entering full safe pytest and was interrupted with Ctrl-C. Exit code: `130`.

## Warning-Ledger Handling

Carried warning: `WL-FH-000-033`.

Source warning summary: semantic AI eval suite and eval gate integration are not yet accepted; schema validation alone is not enough for advice quality.

Handling in this task:

- E1 semantic eval cases were added for the semantic-suite portion of `WL-FH-000-033`.
- The warning is not closed by this Executor report because the required local quality gate stalled.
- Eval-gate integration and readiness fixtures remain intentionally out of scope for this E1 task and belong to E2 (`FH-096`-`FH-097`).
- PM-side `WARNING_LEDGER.md` was not edited by this Executor task.

## Intentional Non-Changes

- Did not change runtime AI coach behavior.
- Did not integrate semantic evals into the local quality gate; E2 owns gate integration.
- Did not generate runtime prompt/payload snapshots.
- Did not implement planner behavior.
- Did not change schema, migrations, production DB, service/deploy config, import/parser/evaluator behavior or `STEAM_IMPORT_MAX_DEMOS_PER_RUN`.
- Did not set `READY_FOR_MAJOR_CS2_FEATURE_WORK=YES`.
- Did not read old task cards, old reviews or old run logs for implementation. A targeted `rg` lookup for `WL-FH-000-033` printed old-report path snippets while locating the warning ledger; no old report was used as source of truth.

## Safety Declarations

- Production DB mutation: none.
- Production DB SHA observed read-only by local quality gate preflight:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db`.
- DB/schema changes: none.
- Live Steam/Valve import: not run.
- Parser jobs on production data: not run.
- Manual evaluator on production DB: not run.
- External AI/API/network calls: not run.
- Package installation: not performed.
- `git add`, commit and push: not run.
- Forbidden actions detected: false.

## Residual Risks

- Acceptance remains blocked until the mandatory local quality gate completes successfully or PM/User explicitly directs a recovery path.
- The new semantic evaluator is test-side only; it does not enforce runtime acceptance of AI output.
- Negative semantic fixtures may trigger multiple related issue codes; tests assert the acceptance-relevant expected codes are present and require the valid case to have no issues.
- The context manifest read for this task still named the prior accepted Batch D task in its task metadata. The explicit task card and canonical macro-batch plan agreed on E1, so this was treated as stale context metadata and recorded here rather than used to broaden scope.

## Blockers

- Required local quality gate stalled during full safe pytest and was interrupted. This blocks a `PASS` or `PASS_WITH_WARNINGS` Executor verdict under the task-card acceptance rule.

## Next WP

Recommended next action: PM/User should decide whether to rerun or recover the required local quality gate for FH-090_095. Do not start E2 gate integration until E1 is accepted.
