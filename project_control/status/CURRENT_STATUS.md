# Current Status

Last updated: 2026-07-11.

Original sources preserved at:

- `_legacy_archive/r02a2-2026-07-11/docs/CURRENT_STATUS.md`
- `_legacy_archive/r02a2-2026-07-11/docs/HANDOFF.md`
- `_legacy_archive/r02a2-2026-07-11/docs/project_management/WP_REGISTRY.md`

## Current route

- CURRENT_LANE: `H01B_DOCUMENTATION_AND_CODEBASE_CONSOLIDATION`
- CURRENT_TASK: `none`
- NEXT_TASK: `H01B-R03_TWO_MISSION_CARDS_ACTIVATION_AND_MATCH_FEEDBACK_UI`
- NEXT_TASK_GATED: `false`
- R02A3_MAY_START: `false`
- THEN: `H01B-R04_30_PLUS_10_PRODUCT_REPLAY`

## Accepted Product state

- PRODUCT_MATURITY: `v0.9`; PACKAGE_VERSION: `0.1.0` (intentional distinction).
- H01A_STATUS: `PASS_WITH_WARNINGS`.
- H01B_STATUS: `PASS_WITH_WARNINGS`.
- H01B_R01_STATUS: `PASS_WITH_WARNINGS`.
- H01B_R02_STATUS: `PASS_WITH_WARNINGS`.
- H01B_R02A2_STATUS: `PASS_WITH_WARNINGS`.
- H01B_R02A2C_STATUS: `PASS_WITH_WARNINGS`.
- H01B_R02A2D_STATUS: `PASS_WITH_WARNINGS`.
- H01B_R02A3_STATUS: `PASS_WITH_WARNINGS`.
- Canonical coach domains: `impact_leak`, `bad_fight_selection`.
- Performance, utility, and aim are metric groups, not coach domains.
- Domain slots per owner: `2`; cross-domain proposals are allowed.
- One active mission per domain is supported; no mission was auto-activated.
- Production baseline id `1`, accepted analyses `3` and `4`, proposal ids `1`
  and `2`, two `proposal_ready` slots, and zero active missions remain accepted.
- Recommendation `#5` is the current accepted hard recommendation. Legacy
  recommendations `#1`, `#3`, and `#4` require explicit refresh.
- Steam import cap remains `1`; exact playlist remains unknown/provenance-only.
- Weak metrics and metric-confidence limitations remain caveated.
- Public/friends readiness and `v1.0` claims remain blocked.
- The final `docs/` compatibility root contains only `README.md` and the
  fixed-path `metrics/AGENTS.md`; canonical Product and control truth lives
  outside `docs/`.

## Runtime and safety

- Runtime: FastAPI/Uvicorn, `jc-coach.service`, `127.0.0.1:8010`.
- Production DB: `data/cs2_coach.db`.
- No production mutation, model call, Steam action, parser/backfill/evaluator
  action, service restart, dependency change, or push is authorized by ordinary
  tasks without explicit scope.
