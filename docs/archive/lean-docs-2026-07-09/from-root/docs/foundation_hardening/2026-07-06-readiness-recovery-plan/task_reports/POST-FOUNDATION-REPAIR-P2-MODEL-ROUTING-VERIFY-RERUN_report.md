# POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN Report

Date: 2026-07-08

## Result

`PASS_WITH_WARNINGS`

The PM-side model-routing selector rerun passed the task-card acceptance checks:

- Selector output for the active card reports
  `task_id="POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN"`.
- Selector output does not report stale `task_id="WP-018"`.
- Selector output reports `task_type="docs_design_governance_only"`, not
  `db_schema`, for this docs/config validation card.
- Selector output is live, actual switching is enabled, and it includes
  `actual_model_label_passed="gpt-5.5"`.
- Unsupported configured labels fail closed to
  `recommended_model_label="gpt-5.5"` with
  `fallback_reason="unsupported_model_label"`.
- `indexes/current_context_manifest.json`, `indexes/task_index.json`, the
  active outbox path and the primary `Task:` field agree on this rerun task id.

Warning: `/opt/jc-coach-pm` had a pre-existing modified
`indexes/current_context_manifest.json`. The active manifest content was the
object under validation and matched the task card/index. No PM files were edited
by this Executor run, and `/opt/jc-coach` was clean before report creation.

## Evidence

Initial safety state:

- `git status --short` in `/opt/jc-coach`: clean before work.
- `git -C /opt/jc-coach-pm status --short`: `M indexes/current_context_manifest.json`.
- Active non-dotfile outbox cards:
  `2026-07-08_POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN_task-card.md`
  only.

Selector command:

```bash
python3 /opt/jc-coach-pm/tools/select_codex_model.py \
  --phase EXECUTOR \
  --manifest /opt/jc-coach-pm/indexes/current_context_manifest.json \
  --task-card /opt/jc-coach-pm/outbox/2026-07-08_POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN_task-card.md \
  --pm-repo /opt/jc-coach-pm \
  --main-repo /opt/jc-coach \
  --output-json
```

Relevant selector JSON evidence:

```json
{
  "actual_model_changed": true,
  "actual_model_label_passed": "gpt-5.5",
  "actual_model_switching_enabled": true,
  "configured_model_label": "gpt-5.3",
  "docs_design_governance_only_eligible": true,
  "docs_design_governance_only_missing_conditions": [],
  "dry_run": false,
  "escalation_reasons": [],
  "fallback_model_label": "gpt-5.5",
  "fallback_reason": "unsupported_model_label",
  "model_label_fallback_applied": true,
  "model_routing_mode": "live",
  "recommended_model_label": "gpt-5.5",
  "recommended_model_tier": "balanced",
  "risk_level": "low",
  "supported_model_allowlist": ["gpt-5.5"],
  "task_id": "POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN",
  "task_type": "docs_design_governance_only"
}
```

Task identity evidence from selector JSON:

```json
{
  "active_outbox_path_task_id": "POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN",
  "manifest_task_id": "POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN",
  "mismatches": [],
  "primary_task_field_id": "POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN",
  "task_index_next_expected_task": "POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN"
}
```

Manifest/index/card agreement:

- Manifest phase: `EXECUTOR`.
- Manifest task id:
  `POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN`.
- Task index `next_expected_task`:
  `POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN`.
- Task index active outbox card:
  `outbox/2026-07-08_POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN_task-card.md`.
- Primary `Task:` field:
  `POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN`.

Unsupported-label checks using the selector's supported-label helper and the
current policy:

```json
{"configured_model_label": "gpt-5.3", "recommended_model_label": "gpt-5.5", "fallback_reason": "unsupported_model_label"}
{"configured_model_label": "codex-spark", "recommended_model_label": "gpt-5.5", "fallback_reason": "unsupported_model_label"}
{"configured_model_label": "unsupported-test-model", "recommended_model_label": "gpt-5.5", "fallback_reason": "unsupported_model_label"}
```

Policy evidence:

- `/opt/jc-coach-pm/config/model_policy.json` has
  `supported_model_allowlist: ["gpt-5.5"]`.
- `fallback_model_label` is `gpt-5.5`.
- `mode` is `live`.
- `actual_model_switching_enabled` is `true`.

## Files Changed

- Added this report:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-REPAIR-P2-MODEL-ROUTING-VERIFY-RERUN_report.md`.

No PM repo files were edited.

## Safety Declarations

- No code changes.
- No runtime behavior changes.
- No DB/schema changes.
- No production DB mutation.
- No deploy/service/nginx/systemd changes.
- No import/parser/evaluator jobs.
- No package installation.
- No `WP-018` resume.
- No Counter-Strike product/feature work.
- No public/friends access unlock.
- No system v1.0 claim or packaging.
- No `READY_FOR_MAJOR_CS2_FEATURE_WORK=YES` change.
- No migration engine or hosted CI work.
- No commit, push or `git add`.
- No production DB touch. Production DB SHA was not collected because this
  docs/config validation task had no DB/schema/import/parser/evaluator or
  production-data scope.

Forbidden actions detected: `false`.

## Context And Token Metrics

- Context manifest used: `true`.
- Broad reads avoided: main-repo forbidden-by-default groups listed in the
  manifest were not read (`docs/audit/**`, `docs/audits/**`, `docs/tasks/**`,
  `instructions/**`, `/var/tmp/**/run.log`). A PM-repo `rg` search was used to
  locate selector/config evidence.
- PM_CREATE tokens: `UNKNOWN`.
- EXECUTOR tokens: `UNKNOWN`.
- PM_REVIEW tokens: `UNKNOWN`.
- Total cycle tokens: `UNKNOWN`.
- Task verdict: `PASS_WITH_WARNINGS`.
- Quality verdict: `pending PM review`.

## Blockers

None.

## Discovery Result

```yaml
discovery_result:
  completeness_estimate: "complete for task-card acceptance checks"
  missing_items_found: false
  followup_required: false
  followup_tasks_recommended: []
```

## Next WP

PM review should decide whether to accept this rerun. If accepted, the canonical
sequence plan's next task is
`POST-FOUNDATION-REPAIR-P0-BOUNDARY-DECISIONS`; it was not started by this run.
