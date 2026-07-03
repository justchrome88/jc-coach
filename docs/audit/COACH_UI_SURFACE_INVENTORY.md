# Coach UI Surface Inventory

Дата: 2026-07-03.

Stage: 9 — Coach-first UI.

## Verdict

Stage 9 можно выполнить без schema changes, migrations, live AI calls, live Steam/import/parser jobs, recommendation planner или ProblemSnapshot.

`/coach` уже был основной страницей для AI/recommendation/report surfaces, но порядок был stats/report-first. Stage 9 переводит верх страницы в action-first presentation поверх существующих persisted state/services.

## UI Surfaces

| Surface | File | Stage 9 status | Read/write behavior |
|---|---|---|---|
| `/coach` GET route | `app/web/routes.py::coach_page` | Updated with read-only `coach_ui` view model. | Reads matches, recommendation progress, evaluations, reports and parser overview. Does not call `ensure_default_*`, `evaluate_new_matches()` or jobs. |
| Coach template | `app/templates/coach.html` | Updated top hierarchy. | Renders current tracked recommendation, evidence/confidence, Metric Truth warnings, latest match and AI validation status. |
| Coach styling | `app/static/app.css` | Small scoped additions. | Presentation only. |
| AI handoff/generate/save buttons | `app/templates/coach.html`, `app/web/routes.py` POST routes | Kept explicit. | No AI action runs on page load. |
| Recommendation status/extend/restart buttons | `app/templates/coach.html`, POST routes | Kept explicit. | Existing command paths only. |
| Dashboard preview | `app/templates/dashboard.html` | Not changed in Stage 9. | Existing compact link remains. |

## Existing Read Inputs

- `playable_match_select()` for persisted matches.
- `get_active_recommendation_progress()`.
- `get_all_recommendation_progress()`.
- `get_evaluations_by_match_id()`.
- `latest_report()`.
- `latest_ai_handoff()`.
- `latest_ai_coach_report()`.
- `ai_provider_health()`.
- `get_aim_profile()`.
- `list_ai_coach_reports()`.
- `list_recommendation_history()`.
- `recommendation_category_summary()`.
- `_demo_parse_overview()`.

## Stage 9 View Model

New helper: `app/web/routes.py::_coach_first_view_model`.

It builds:

- current tracked recommendation card;
- next-match action;
- evidence rows with Metric Truth reliability and usage decision;
- last evaluation summary;
- latest match summary;
- AI validation/fallback status;
- weak metric notes for `early_deaths`, `trade_kills`, `side_split_metrics`, `traded_deaths`.

The helper does not receive a `Session` and does not write to DB.

## Explicit Non-Goals

- No recommendation planner.
- No ProblemSnapshot.
- No verified top problem claim.
- No new recommendation selection logic beyond existing active recommendation ordering.
- No schema changes or migrations.
- No live AI/Steam/import/parser jobs.
- No parser/Steam/AI engine work.
- No friends/public feature work.

## Safety Tests

Stage 9 adds `tests/test_coach_first_ui.py` covering:

- authenticated owner render;
- empty state;
- current tracked recommendation visibility;
- no verified-top-problem overclaim;
- Metric Truth weak metric warnings;
- AI validation/fallback status;
- GET `/coach` no-mutation row counts;
- no hidden live/external job calls from page render.
