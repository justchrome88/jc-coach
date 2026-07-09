# MVP-003 DB Schema Data Storage Mutation Plan

Date: 2026-07-09
Role: 02-Executor
Task: `MVP-003_DB_SCHEMA_DATA_STORAGE_MUTATION_PLAN`
Verdict: `PASS_WITH_WARNINGS`

## Summary

MVP-003 is complete as a report-only DB/schema/data-storage mutation plan. No
product code, SQLAlchemy models, migration scripts, schema artifacts, data
files, raw demos, imports, parser jobs, evaluator jobs, services, deploy config
or package files were changed.

Current persistence already covers owner users, linked Steam accounts, coarse
import jobs, matches, parsed demo artifacts/events, coach reports,
recommendations, recommendation evaluations and app settings. MVP gaps remain
around durable import units/attempts, demo-file lifecycle records, parser run
lineage, versioned derived context, metric definitions/snapshots, insight
cards, missions/checkpoints and structured coach messages.

Recommended next task:
`MVP-004_PARSER_CAPABILITY_AND_ARTIFACT_CONTRACT`.

## Source-Of-Truth And Scope

Read context was limited to the Task Card, context manifest, Hot docs,
storage/DB/migration/metrics/import docs, `app/db/models.py`, and
DB/storage-relevant tests.

Source-of-truth order used:

1. Current user task and Task Card.
2. `/opt/jc-coach/AGENTS.md`.
3. `docs/CURRENT_STATUS.md`.
4. `docs/HANDOFF.md`.
5. `docs/project_management/WP_REGISTRY.md`.
6. Task-relevant storage, DB, migration, import, metrics and testing docs.

The PM compact memory is stale relative to the main Hot docs and active MVP
Task Card. It labels itself non-canonical and was not used to override the
explicit `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` authorization recorded in Hot
docs and the Task Card.

## Read-Only DB Evidence

Production DB path inspected: `data/cs2_coach.db`.

Production DB SHA before and after read-only inspection:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Read-only inspection commands:

```bash
sha256sum data/cs2_coach.db
.venv/bin/python - <<'PY'
import sqlite3
conn = sqlite3.connect('file:data/cs2_coach.db?mode=ro', uri=True)
try:
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        print(name)
finally:
    conn.close()
PY
.venv/bin/python - <<'PY'
import sqlite3
conn = sqlite3.connect('file:data/cs2_coach.db?mode=ro', uri=True)
try:
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for table in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f'{table}|{count}')
finally:
    conn.close()
PY
.venv/bin/python - <<'PY'
import sqlite3
conn = sqlite3.connect('file:data/cs2_coach.db?mode=ro', uri=True)
try:
    print(conn.execute('PRAGMA integrity_check').fetchone()[0])
finally:
    conn.close()
PY
```

No-mutation confirmation:

- SQLite was opened with `mode=ro`.
- No SQL write statement, backup, copy, restore, vacuum, migration, parser,
  import or evaluator command was run.
- `PRAGMA integrity_check` returned `ok`.
- The observed DB SHA matches the Hot-doc latest known production DB SHA.
- `sqlite3` CLI is not installed on this host, so Python stdlib `sqlite3` was
  used for equivalent read-only inspection.

## Current DB / Storage Model Summary

Current SQLAlchemy models in `app/db/models.py`:

| Area | Existing models / tables | Current role |
|---|---|---|
| Owner/auth identity | `users` | Local user records with display name, email, password hash, active flag and login timestamps. |
| Steam identity | `steam_accounts` | Owner-linked Steam identity, persona/profile metadata, sync flag, auth code and latest share-code cursor. |
| Import orchestration | `import_jobs` | Coarse provider/job lifecycle plus JSON request/result/error payloads. |
| Match facts | `matches` | Match-level facts, source/external ID, demo path, date, map, mode/provenance, score, core stats and raw JSON. |
| Parser artifact | `demo_parse_artifacts` | One artifact per match with parser metadata, demo hash, event counts, confidence, gaps and compact payload JSON. |
| Normalized parser rows | `demo_rounds`, `demo_player_rounds`, `demo_weapon_stats`, `demo_damage_events`, `demo_duels`, `demo_grenade_events` | Parsed round/player/weapon/damage/duel/grenade data used by match detail, analytics, coach and recommendations. |
| Coach output | `coach_reports` | Persisted report markdown/JSON with report type and optional source reference. |
| Recommendations | `coach_recommendations`, `match_recommendation_evaluations` | Active/history recommendations and per-match evaluation evidence. |
| App config | `app_settings` | Key/value settings. Secret values must not be printed in reports. |

Production table row counts from read-only inspection:

| Table | Rows |
|---|---:|
| `app_settings` | 1 |
| `coach_recommendations` | 5 |
| `coach_reports` | 0 |
| `demo_damage_events` | 13522 |
| `demo_duels` | 3228 |
| `demo_grenade_events` | 4033 |
| `demo_parse_artifacts` | 22 |
| `demo_player_rounds` | 4624 |
| `demo_rounds` | 461 |
| `demo_weapon_stats` | 5487 |
| `import_jobs` | 28 |
| `match_recommendation_evaluations` | 78 |
| `matches` | 76 |
| `steam_accounts` | 1 |
| `users` | 254 |

Runtime storage snapshot:

| Path | Observed size/count |
|---|---:|
| `data/uploads` | 4.2G, 31 `.dem` files |
| `data/incoming_demos` | 275M, 1 `.dem` file |
| `data/reports` | 76K |

Current storage policy remains `retain_raw_for_parser_development`; raw demo
deletion/move/compression is not authorized by this task.

## MVP Storage Gap Table

| MVP area | Current support | Gap | Proposed future entities |
|---|---|---|---|
| Users / owner identity | `users`, `steam_accounts` exist. | No broader public/friends identity model should be inferred. Owner-only boundaries must stay explicit. | Keep current tables; add only narrow owner/profile fields when explicitly scoped. |
| Import jobs | `import_jobs` exists with coarse status and JSON payloads. | No durable import item/candidate table, attempt ledger, lease/heartbeat, idempotency key, per-phase safety evidence or retry state. | `import_job_items`, `import_attempts`, `import_job_events`, optional `import_idempotency_keys`. |
| Demo files | `matches.demo_file`, `demo_parse_artifacts.source_demo_file`, storage manifest/report logic. | No durable DB ledger for raw demo path, hash, size, retention status, quarantine state, source URL/share-code, parser readiness or deletion eligibility. | `demo_files` with path, sha1/sha256, size, source, status, retention_policy, parser_artifact_id, safety timestamps. |
| Parser artifacts | `demo_parse_artifacts` plus normalized parser tables. | Artifact lifecycle is match-unique and lacks explicit parser run lineage, invalidation/reparse state and schema-versioned artifact dependency graph. | `parser_runs`, `parser_artifacts`, `parser_artifact_entities`, `parser_reparse_queue`. |
| Normalized events | Typed demo tables cover rounds/player rounds/weapons/damage/duels/grenades. | No unified event identity/provenance layer; no full economy, positioning, tick/view-angle, clutch, side-confidence or trade-confidence model accepted for hard claims. | Keep typed tables; add future `normalized_events`, `normalized_event_players`, `event_confidence`, `event_source_links` only after parser contract. |
| Derived context | Some derived facts live in service code and JSON evidence. | No versioned persisted player-match, round-context, problem, source-coverage or evidence-link tables. | `derived_context_snapshots`, `derived_player_match_context`, `derived_round_context`, `evidence_links`, `source_coverage`. |
| Metric definitions | Docs/runtime `metric_truth.py`; no DB table. | Definitions are not persisted/versioned with snapshots; metric values and confidence are not captured as immutable per-window evidence. | `metric_definitions`, `metric_snapshots`, `metric_snapshot_values`, `metric_snapshot_sources`. |
| Metric snapshots | Recommendation baselines/evaluations contain JSON. | No general reusable snapshot table for dashboard, AI Scout, Evidence Validator, missions or insight cards. | `metric_snapshots` keyed by owner/window/source/version plus value rows and confidence metadata. |
| Insight cards | No dedicated model in current DB. | No durable insight lifecycle, evidence links, suppression reason, status or user feedback. | `insight_cards`, `insight_card_evidence`, `insight_card_actions`. |
| Missions | No dedicated model in current DB. | No mission definition, assignment, active target, progress, checkpoint or completion history. | `missions`, `mission_checkpoints`, `mission_progress_events`, `mission_evidence_links`. |
| Coach messages | `coach_reports` exists; AI handoffs are file artifacts. | No structured coach conversation/message/result table with prompt/version, source snapshot, validation state and evidence links. | `coach_threads`, `coach_messages`, `coach_message_evidence`, `ai_prompt_snapshots`, `ai_validation_results`. |
| Recommendations | Recommendation and evaluation tables exist. | Current recommendation evidence is JSON-heavy and category-specific; future mission/insight/AI integration needs shared evidence links and metric snapshot references. | Add snapshot/evidence foreign keys in future migration; do not retrofit without explicit schema task. |

## Future Mutation Evidence Contract

Future DB/schema/data mutation tasks must use profile `MVP_DB_SCHEMA_MUTATION`
or a stricter task-specific profile. This MVP-003 report does not authorize any
mutation.

Minimum future evidence contract:

1. Pre-work:
   - `git status --short` and `git branch --show-current`.
   - Confirm branch `cona`.
   - Confirm allowed files, schema scope and production DB mutation status.
   - `sha256sum data/cs2_coach.db`.
   - If mutation is authorized, run `scripts/backup_runtime.sh` and record the
     backup path.
   - Verify restore on a copy when production DB mutation or schema-risk work is
     authorized.
2. Copied-DB / fixture policy:
   - Use `APP_ENV=test` and temp/copy DB paths for tests.
   - Do not target `data/cs2_coach.db` for experiments.
   - Use `scripts/migration_check_on_copy.sh` for copy checks when scoped.
   - Do not refresh the schema baseline unless a schema artifact task explicitly
     authorizes it.
3. Change execution:
   - Record the exact SQL, script, app command or migration command before
     running it.
   - Apply only the authorized schema/data change.
   - Do not add startup helper schema behavior unless explicitly scoped.
   - Do not run live Steam import, parser, evaluator or manual evaluator jobs
     unless separately authorized.
4. Post-work:
   - `sha256sum data/cs2_coach.db` after mutation when production DB is touched.
   - Run integrity/schema verification required by the task.
   - Run task-specific tests with `APP_ENV=test`.
   - Run `git diff --check`.
   - Run `git status --short`.
5. Rollback notes:
   - Production rollback is production DB mutation and requires explicit
     operator/WP authorization.
   - Restore must use the recorded backup, must be verified on a copy first,
     and must record post-restore SHA evidence.
   - Raw demos remain out of scope unless a storage WP explicitly authorizes
     raw-demo lifecycle work.

## Recommended Next Task

`MVP-004_PARSER_CAPABILITY_AND_ARTIFACT_CONTRACT`

Recommended scope:

- Report-only parser capability and artifact contract.
- Inventory current parser outputs, artifact payload version, normalized parser
  tables and confidence/gap fields.
- Define what artifact evidence must exist before future metric snapshots,
  insight cards, missions and coach messages rely on parser-derived facts.
- Preserve current no-live-parser/no-production-mutation guardrails unless the
  next Task Card explicitly authorizes risky work.

## Changed Files

Changed file:

- `docs/audit/MVP_003_DB_SCHEMA_DATA_STORAGE_MUTATION_PLAN.md`

Docs Steward notes:

- Hot/current status docs were not updated because this task is report-only and
  does not change canonical product state.
- Navigation docs were not updated because the Task Card explicitly requested
  only the file-backed Executor report.
- The report does not weaken `AGENTS.md`, Hot docs or control-plane policy.

Final git status:

```text
?? docs/audit/MVP_003_DB_SCHEMA_DATA_STORAGE_MUTATION_PLAN.md
```

## Checks Run

Profile and docs-only checks:

```text
git status --short
git branch --show-current
.venv/bin/python scripts/project_gate.py preflight
.venv/bin/python scripts/project_gate.py changed
.venv/bin/python scripts/project_gate.py required-checks
.venv/bin/python scripts/project_gate.py postflight
sha256sum data/cs2_coach.db
.venv/bin/python read-only sqlite3 mode=ro table/schema/count inspection
.venv/bin/python read-only sqlite3 mode=ro PRAGMA integrity_check
du -sh data/uploads data/incoming_demos data/reports
find data/uploads -maxdepth 1 -type f -name '*.dem' | wc -l
find data/incoming_demos -maxdepth 1 -type f -name '*.dem' | wc -l
git diff --check
git diff --no-index --check /dev/null docs/audit/MVP_003_DB_SCHEMA_DATA_STORAGE_MUTATION_PLAN.md
git status --short
```

Checks intentionally not run:

- Full tests: forbidden by Task Card.
- Import/parser/evaluator/manual evaluator commands: forbidden by Task Card.
- Live Steam/Valve import: forbidden by Task Card.
- Backup/copy/restore/vacuum/migration: forbidden by Task Card for this
  report-only task.

## Safety Confirmations

- No production DB/schema/data mutation.
- No DB backup, copy, restore, vacuum or migration.
- No product code/model/migration/script changes.
- No data file or raw demo movement, deletion, compression or rewrite.
- No live Steam/Valve import.
- No parser, evaluator or manual evaluator jobs.
- No service/deploy/runtime/package/dependency changes.
- No public/friends readiness claims.
- No unsupported coach claims.
- No `git add`, commit or push.

## Risks / Warnings

- `PASS_WITH_WARNINGS` is used because PM compact memory is stale relative to
  the current Hot docs and Task Card. The stale memory is non-canonical and did
  not block this task, but it should be refreshed by PM tooling.
- `sqlite3` CLI is unavailable on this host. Python stdlib `sqlite3` read-only
  URI mode was used instead.
- Current storage remains large under root-backed `data/uploads`; this task did
  not authorize cleanup.
- Current DB has no adopted migration engine; future schema work must keep the
  backup/SHA/copy-check discipline from `docs/MIGRATIONS.md` and
  `docs/BACKUP_RESTORE.md`.
