# WP-016C Controlled Recommendation Refresh Report

Date: 2026-07-04

## RESULT: REFRESHED

WP-016C performed the controlled production recommendation refresh for category `survival`.

Exactly one official service-level write action was run:

```bash
.venv/bin/python - <<'PY'
from app.db.session import SessionLocal
from app.services.recommendation_tracking import restart_recommendation_category

with SessionLocal() as db:
    recommendation = restart_recommendation_category(db, "survival")
    print("REFRESHED", recommendation.id, recommendation.category, recommendation.status, recommendation.started_at, recommendation.start_after_match_id)
PY
```

Output:

```text
REFRESHED 5 survival active 2026-07-04 18:04:34.403854 70
```

No live Steam/Valve import, demo download, parser job, persistent report generation, schema change, DB reset/resync, demo cleanup, AI rewrite or recommendation planner rewrite was performed.

## Backup Path

```text
data/manual_backups/cs2_coach_before_wp016c_survival_refresh_20260704_210428.db
```

Backup SHA:

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/manual_backups/cs2_coach_before_wp016c_survival_refresh_20260704_210428.db
```

## DB SHA Before / After

Before:

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

After:

```text
45bd8b7b4a513cfa509ab40137abdc72b54820da2fe1244d44c42b495b4e374e  data/cs2_coach.db
```

The SHA changed because the authorized `survival` recommendation refresh mutated production `coach_recommendations`.

## Pre-Refresh Recommendation Inventory

Recommendation counts by status/category:

```text
('active', 'grenades', 1)
('active', 'map', 1)
('active', 'survival', 1)
('completed', 'aim', 1)
```

Evaluation counts:

```text
(1, 'gray', 19)
(2, 'gray', 18)
(3, 'gray', 19)
(4, 'gray', 19)
```

Selected active recommendation before refresh:

```text
id=1 category=survival status=active started_at=2026-07-01 19:22:57.307791 ended_at=None title=Снизить первые смерти
```

Active recommendations before refresh:

| id | category | status | baseline ids | confidence | health |
|---:|---|---|---|---|---|
| 1 | survival | active | `6-20` | no | `needs_refresh=true` |
| 3 | grenades | active | `6-20` | no | `needs_refresh=true` |
| 4 | map | active | `6-20` | no | `needs_refresh=true` |

Playable exact-date match IDs available before refresh:

```text
[21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 70]
```

Running import jobs before refresh:

```text
0
```

Storage before refresh:

```text
3.6G data/uploads
4.0K data/tmp
```

## Post-Refresh Recommendation Inventory

Recommendation counts by status/category:

```text
('active', 'grenades', 1)
('active', 'map', 1)
('active', 'survival', 1)
('archived', 'survival', 1)
('completed', 'aim', 1)
```

Evaluation counts remained unchanged:

```text
(1, 'gray', 19)
(2, 'gray', 18)
(3, 'gray', 19)
(4, 'gray', 19)
```

Total recommendation/evaluation/report counts after smoke:

```text
coach_recommendations 5
match_recommendation_evaluations 75
coach_reports 0
running_import_jobs 0
```

## Old Survival Recommendation Disposition

Old survival recommendation `#1`:

| Field | Value |
|---|---|
| id | `1` |
| category | `survival` |
| status | `archived` |
| created_by | `system` |
| started_at | `2026-07-01 19:22:57.307791` |
| ended_at | `2026-07-04 18:04:34.114661` |
| start_after_match_id | `20` |
| baseline ids | `6-20` |
| baseline source | `steam_history` placeholders |
| baseline confidence | missing |
| health | `needs_refresh=true` |

It is no longer active and remains preserved for audit/history. Its 19 legacy gray evaluations were not changed.

## New Active Survival Recommendation ID

```text
5
```

New active survival recommendation:

| Field | Value |
|---|---|
| id | `5` |
| category | `survival` |
| status | `active` |
| created_by | `system` |
| started_at | `2026-07-04 18:04:34.403854` |
| ended_at | `None` |
| start_after_match_id | `70` |

The app-selected active recommendation after refresh is `#5 survival active`.

## New Baseline IDs

```text
[23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 70]
```

## Baseline Source / Date Validation

All baseline rows are playable `source="demo"` rows. No `steam_history` baseline IDs are present.

Each baseline row has exact match date truth:

| Match id | Source | Exact date |
|---:|---|---|
| 23 | demo | yes |
| 24 | demo | yes |
| 25 | demo | yes |
| 26 | demo | yes |
| 27 | demo | yes |
| 28 | demo | yes |
| 29 | demo | yes |
| 30 | demo | yes |
| 31 | demo | yes |
| 32 | demo | yes |
| 33 | demo | yes |
| 34 | demo | yes |
| 35 | demo | yes |
| 36 | demo | yes |
| 70 | demo | yes |

## Baseline Confidence Validation

`baseline_metrics_json.confidence.date_window` is present:

```text
total_playable_matches=15
exact_date_matches=15
approximate_date_matches=0
unknown_date_matches=0
excluded_from_exact_windows=0
confidence=exact
insufficient_exact_sample=False
warnings=[]
```

`baseline_metrics_json.confidence.metrics` is present:

```text
kd_ratio=exact
entry_deaths=partial
early_deaths=low_confidence
kast=low_confidence
adr=partial
utility_damage=partial
flash_assists=low_confidence
result=exact
```

## Target Metrics Validation

New `target_metrics_json` is derived from real baseline values, not `need data` placeholders:

```text
{
  "kast": ">=63.54",
  "adr": ">=79.88",
  "entry_deaths_per_match": "<=1.3",
  "early_deaths_per_match": "warning: approximate metric, not used for hard scoring"
}
```

## Recommendation Health Validation

New active recommendation `#5`:

```text
needs_refresh=False
accepted_for_hard_progress=True
reasons=[]
baseline_non_playable_ids=[]
empty_required_metrics=[]
evaluations_checked=0
```

Active progress health after refresh:

```text
active_progress 5 survival False True 0
```

AI payload read path also sees active recommendation `#5` with `needs_refresh=false`.

## Evaluation Side Effects

No new evaluations were created by the refresh:

```text
match_recommendation_evaluations 75
new recommendation #5 evaluations count 0
```

No duplicate recommendation/match evaluations exist:

```text
[]
```

No evidence rows needed validation for new recommendation `#5` because no next-match evaluation exists yet. Existing legacy evaluations remain attached to archived/legacy recommendations.

## GET / Read Mutation Safety

Read helpers were exercised after refresh:

- `get_active_recommendation_progress(db)`;
- `get_all_recommendation_progress(db)`;
- `recommendation_category_summary(db)`;
- `build_ai_coach_payload(db)`.

Counts before/after read helpers stayed unchanged:

```text
(5, 75) -> (5, 75)
AI payload read safety: (5, 75, 0) -> (5, 75, 0)
```

Unauthenticated GET-only smoke was attempted after restart without forging auth:

```text
/coach 303
/dashboard 303
/stats 303
/matches 303
/settings/imports 303
```

The `303` redirects are expected without an authenticated session. Authenticated browser evidence is deferred to operator/runtime acceptance.

## Service / Log Safety

Service restart was performed and succeeded:

```text
systemctl restart jc-coach
systemctl status jc-coach --no-pager
Active: active (running)
Main PID: 141658 (uvicorn)
```

Journal after refresh/restart showed clean shutdown/startup and GET redirects. No traceback, HTTP 500, import POST, parser, Steam, download or report generation log lines were found in the checked window.

## File / Storage Safety

Storage after refresh:

```text
3.6G data/uploads
4.0K data/tmp
28 .dem files
```

No new files were found under `data/uploads` or `data/tmp` after the refresh start timestamp.

## Production Safety

- Production DB touched: yes, explicitly and with backup.
- Exact production DB write: one `restart_recommendation_category(db, "survival")`.
- Production demo/upload/temp files touched: no.
- Backup file created: yes, under `data/manual_backups/`.
- Docs/report files touched: yes.
- Live Steam/import/parser run: no.
- Persistent reports generated: no.
- Schema changed: no.
- DB reset/resync performed: no.
- Commit made: no.

## Whether WP-016D Recommendation Loop Runtime Acceptance Can Start

Yes.

WP-016D can start as runtime acceptance for:

- active survival recommendation `#5`;
- next-match action visibility;
- no hidden GET mutations;
- future next-match evaluation behavior;
- progress update after an explicitly authorized evaluation path.

## Remaining Risks

- Active `grenades` recommendation `#3` and active `map` recommendation `#4` remain legacy/`needs_refresh`; they are not accepted for hard progress.
- New survival recommendation `#5` has no post-refresh next-match evaluations yet, so the full recommendation -> next match -> evaluation -> progress loop still needs WP-016D runtime acceptance.
- Recommendation planner / verified top problem remains out of scope.
- Persistent report generation acceptance remains deferred because report generation mutates DB.
- Weak metrics remain weak and must remain caveated.
