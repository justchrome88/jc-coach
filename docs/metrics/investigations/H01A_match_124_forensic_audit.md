# H01A Match 124 Forensic Metric Audit

Result: `PASS_WITH_WARNINGS` for audit completeness; metric correctness is not accepted. DB inspection was read-only. Retained demo SHA-1 matches artifact 91. No parser rerun, recomputation persistence, snapshot rewrite, or coach mutation occurred.

## Identity and evidence

- owner: user `17`, Steam account `1`, Steam ID `76561198056634139` (`JC`);
- source match `123`, demo match `124`, import job `101`;
- retained demo SHA-1 `fc3aac7a6176d1ec7b827762803fb4d333ecc6aa`;
- artifact `91`, demoparser2 `0.41.3`, payload `2026-07-02.1`;
- event set `parser-artifact:91:events:8285d8fafd78be0f`;
- snapshots `1138` core and `1149` utility; analysis `59`; hypotheses `110/111`; mission `3`; progress `9`.

The duel graph independently resolves a bipartite 5v5 roster around the owner Steam ID. No alias, side-switch roster change, disconnect, or reconnect event is persisted in the artifact. Lack of activity in rounds 1, 5, and 19 therefore cannot prove absence.

## Deterministic ledger

Command: `.venv/bin/python scripts/audit_match_metrics.py --expect-sha256 7613ce49785f4e9a28e759117da96fc0249e1e95db3d236797127b7457384fe3`.

`Dmg` is raw owner damage split enemy/team; `U` is raw utility damage. KAST is only K/A/survive, because trade is unavailable. Source IDs are deterministic `deep` array indexes; the command emits every ID.

| R | Class | Participation | K | D | A | FA | HSK | Dmg E/T | U | Survived | KAS | First | Source count |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|
| 0 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 0/0 | 0 | no | no | none | 1 |
| 1 | regulation | not proven | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | unknown | unknown | none | 0 |
| 2 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 52/0 | 52 | no | no | none | 2 |
| 3 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 0/0 | 0 | no | no | none | 1 |
| 4 | regulation | observed | 1 | 0 | 1 | 0 | 1 | 161/0 | 0 | yes | yes | none | 5 |
| 5 | regulation | not proven | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | unknown | unknown | none | 0 |
| 6 | regulation | observed | 3 | 0 | 0 | 0 | 3 | 396/0 | 0 | yes | yes | none | 11 |
| 7 | regulation | observed | 1 | 0 | 0 | 0 | 0 | 118/0 | 0 | yes | yes | none | 5 |
| 8 | regulation | observed | 2 | 0 | 0 | 0 | 2 | 304/0 | 0 | yes | yes | none | 8 |
| 9 | regulation | observed | 0 | 1 | 2 | 0 | 0 | 160/5 | 94 | no | yes | first death | 11 |
| 10 | regulation | observed | 0 | 1 | 1 | 1 | 0 | 52/0 | 0 | no | yes | none | 4 |
| 11 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 25/0 | 3 | no | no | none | 4 |
| 12 | regulation | observed | 1 | 1 | 0 | 0 | 0 | 107/0 | 0 | no | yes | first kill | 10 |
| 13 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 0/0 | 0 | no | no | none | 1 |
| 14 | regulation | observed | 2 | 0 | 0 | 0 | 1 | 170/0 | 0 | yes | yes | none | 5 |
| 15 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 0/0 | 0 | no | no | none | 1 |
| 16 | regulation | observed | 4 | 0 | 0 | 0 | 1 | 374/0 | 0 | yes | yes | none | 23 |
| 17 | regulation | observed | 0 | 1 | 0 | 0 | 0 | 0/0 | 0 | no | no | none | 1 |
| 18 | regulation | observed | 2 | 0 | 0 | 0 | 2 | 246/0 | 0 | yes | yes | none | 4 |
| 19 | regulation | not proven | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | unknown | unknown | none | 0 |
| 20 | post-match | observed artifact row | 0 | 1 | 0 | 0 | 0 | 0/0 | 0 | no | no | none | 1 |

Regulation totals: 16 kills, 10 deaths, 4 assists (3 ordinary + 1 flash), 10 headshot kills, 2165 raw enemy damage, 5 raw team damage, 149 raw HE damage, 20 completed rounds, and only 17 activity-derived participation rows. The post-match event at tick `115232`, after final round end tick `114168`, is a `world` self-death; normalized core code counts it as both a kill and death, while legacy match code excludes it from kills but includes it in deaths.

The ledger's 1643 enemy effective-damage reconstruction uses all persisted hurt rows to cap owner attribution at prior observed victim health. It is deterministic but not accepted ground truth: round-boundary/health reset semantics and the comparator's 1664 are not fully reconciled.

## Per-metric discrepancy matrix

| Metric | Raw ledger | Normalized tables/snapshot | Match/UI | Comparator | Verdict | Localized layer |
|---|---:|---:|---:|---:|---|---|
| kills | 16 regulation enemy kills | snapshot 1138: 17 | match/UI: 16 | 16 | `MISMATCH` snapshot; UI `MATCH` | event filtering/aggregation: self post-match kill |
| deaths | 10 regulation deaths | snapshot: 11 | match/UI: 11 | 10 | `MISMATCH` | round participation/event filtering: post-match world death |
| K/D | 16/10 = 1.60 | no stored ratio; inputs 17/11 | 1.45 = 16/11 | 1.60 | `MISMATCH` | contaminated death and divergent kill paths |
| assists | 4 = 3 ordinary + 1 flash | 4 | match reportedly/UI data 4 | 3 | `SEMANTIC_DIFFERENCE` | comparator appears ordinary-only; external definition not supplied |
| flash assists | 1 | utility snapshot omits; player round/match 1 | API match 1 | not supplied | `MATCH` internally / comparator `INSUFFICIENT_EVIDENCE` | source contract differs by snapshot family |
| damage | 2165 enemy raw + 5 team; effective reconstruction 1643 | snapshot 2170 | not directly shown | 1664 | `MISMATCH` plus `INSUFFICIENT_EVIDENCE` for accepted effective formula | aggregation formula/event filtering; external semantic gap remains |
| ADR | disputed numerator / 20 completed rounds | 2170/18 = 120.556 | 2170/21 = 103.33 | 83 (1664/20≈83.2) | `MISMATCH` | raw damage, round count, participation, persistence/UI source divergence |
| KAST | K/A/S known; trade unknown; 3 quiet rounds unresolved | no core KAST; player rows conflict | 55.56% | 69% | `INSUFFICIENT_EVIDENCE` and semantic difference | participation and unavailable trade component |
| headshot kills | 10/16 accepted kills | deep rows 10; snapshot omits | HS%=62.5 | differing value not supplied | internal `MATCH`; comparator `INSUFFICIENT_EVIDENCE` | external semantics unknown |
| HS% | headshot kills / kills = 62.5% | weapon aliases have per-weapon rates | 62.5% | not supplied | `INSUFFICIENT_EVIDENCE` externally | must not compare to head hits/hits or weapon accuracy |
| utility damage | raw HE 149, including team 5 | snapshot 1149: 149 | match/API 149 | reportedly correct | `MATCH` for current raw semantics | enemy-only meaning remains unresolved |
| enemies flashed | team relation not enforced | snapshot 19 | match row 0 | not supplied | `MISMATCH` internal semantics | parser/normalization and persistence paths |
| weapon accuracy | alias split | zero/none across paired aliases | weapon UI inherits split | not supplied | `MISMATCH` | normalization: `ak47` vs `weapon_ak47` |
| traded deaths | no accepted events | unavailable | not shown | not supplied | `NOT_IMPLEMENTED` | parser/derivation evidence absent |

## Root causes

Confirmed: post-match self/world death not filtered; activity-based round participation; raw attempted damage summed without victim relation/effective cap; team damage included; legacy match and snapshot formulas diverge; weapon aliases are not normalized; semantic version is metadata only and snapshot upsert overwrites under `(match, player, source)`.

Not confirmed and therefore excluded from formula repair: the exact 1664 external damage contract, exact 69% KAST contract/trade state, and external HS% semantics.

## Documentation authority audit

| Path | Claimed / actual authority | Match/conflicts | Classification and disposition |
|---|---|---|---|
| `docs/metrics/*` | canonical registry/contracts | reflects audited implementation and disputes | canonical; maintain together |
| `docs/METRICS.md` | former canonical; runtime policy mirror | overstates ADR 100% readiness and kills/deaths trust for match 124 | contradictory/supporting; point to new canonical, reconcile in M02 |
| `app/services/metric_truth.py` | executable usage policy | lacks snapshot metrics and carries now-disputed trust labels | supporting runtime policy; version/reconcile in M02 |
| `docs/agents/METRICS_GUARDIAN.md` | role guardrail | consistent but not formula authority | supporting; reference new agent contract |
| `docs/audit/METRIC_TRUTH_INVENTORY.md` | Stage 5 inventory | useful surface map; predates snapshot/mission pipeline | historical/supporting; retain |
| `docs/audit/WP_015B_METRICS_CORRECTNESS_DIAGNOSIS.md` | v0.7 diagnosis | accurately records older risks; no H01A real-match proof | historical/supporting; retain |
| `docs/audit/WP_015C_METRICS_CONFIDENCE_DATE_GATING_REPAIR_REPORT.md` | repair evidence | date/confidence only, not formula validation | historical; retain |
| `docs/audit/WP_015C1_METRICS_PERFORMANCE_REPAIR_REPORT.md` | performance repair | no formula authority | historical; retain |
| `docs/audit/WP_015D_RUNTIME_METRICS_ACCEPTANCE_REPORT.md` | runtime acceptance | service/UI acceptance did not independently validate formulas | historical; do not cite as metric verification |
| `docs/audit/WP_015E_PROMOTE_METRICS_CORRECTNESS_TO_V0_7_REPORT.md` | old promotion | explicitly says formulas not all externally validated | historical; retain warning |
| `docs/METRICS_ROADMAP_SCORING_RU.md` and `.xlsx` | scoring roadmap | ADR “100%” and HS “ready” conflict with audit | contradictory historical; retain, never use as truth |
| archived Stage 5 reports/tasks and old instruction `04_DATA_AND_METRICS_SPEC.md` | historical implementation intent | superseded by current code/contracts | deprecated historical; retain, no deletion |
| readiness audit `05_DATA_METRICS_AI_COACH.md` | audit finding | correctly identifies registry strength but predates H01A discrepancy | historical/supporting |

## Test and fixture audit

- formula unit: `test_core_combat_metrics.py`, `test_utility_metrics.py`, `test_metric_truth.py`;
- synthetic event fixture: core/utility/event dictionary/combat derivation tests;
- parser fixture: `test_parser_artifact_reader.py`, `test_demo_parser.py`;
- semantic/golden: `test_metrics_c2_fixtures.py` and `fixtures/metrics/golden_aggregate_c2.json`;
- UI mapping: `test_coach_first_ui.py` and web/template tests;
- owner scope: `test_metric_snapshots.py`, ownership/owner-sync tests;
- coach consumption: `test_coach_insights.py`, `test_mission_domain.py`, `test_ai_coach.py`;
- real-demo golden: newly added read-only `test_metric_forensic_audit.py` uses retained artifact 91; no parser rerun;
- external comparator: this investigation only; not automated ground truth.

Most formula tests are synthetic and valid as regression tests but circular for ground-truth assurance when their expected values restate current formulas. Existing golden C2 is synthetic, not independent real-demo truth.

## Downstream impact and quarantine

- snapshots 1138/1149: retain historical evidence; 1138 is stale/disputed and must be superseded/recomputed after versioned repair; 1149 is partially verified but its team-damage semantics must be versioned;
- analysis run 59: retain; mark stale/superseded later because it selected 1138/1149 under unversioned semantics;
- hypothesis 110: quarantine from user-facing claims and recompute; it relies on disputed 18-round survival;
- hypothesis 111: retain as caveated historical evidence; recompute after utility contract decision;
- mission 3: its pre-H01A rolling evidence may also share current unversioned utility semantics; retain active record but block hard user-facing assurance until M02 validates the historical sample;
- progress evaluation 9: retain, mark stale/superseded and recompute after M02; it consumes snapshot 1149 and includes disputed snapshot 1138 as context, although final status is honestly `insufficient_data`.

## M02 repair specification

Must fix before H01B: versioned snapshot provenance/selection; quarantine disputed metrics; post-match/warmup/incomplete filtering; explicit player participation; enemy/team/self/world damage classes; accepted damage/ADR fixture; K/D independent counts; KAST per-round K/A/S/T fixture; assist/flash-assist separation; owner/match/player/version selection tests; stale/superseded handling for listed downstream objects. M02 must stop rather than choose 1664, 69%, or external HS semantics without independent evidence.

Should fix before public UI: make UI and coach select one canonical versioned source; show semantic/version/confidence; normalize weapon aliases; distinguish raw and effective damage; prohibit generic unowned latest-snapshot helpers; provide user-visible stale/quarantine state.

Later improvements: reliable connect/reconnect and side timeline, trade validation, enemy-only flash value, bullet/weapon correlation, crosshair/TTK/spray evidence, calibrated swing/composite ratings.

Schema/provenance decision: add first-class semantic version to snapshot identity (prefer append-only uniqueness including version), retain old rows, select an allowlisted version, and never in-place overwrite changed semantics. Backfill scope is all snapshots produced by affected core/utility versions only after source artifacts pass validation. Rollback switches consumers to quarantine/previous allowlist; it does not rewrite history. Acceptance fixtures include artifact 91 ledger plus synthetic warmup, post-round, self/world/team damage, quiet round, disconnect/reconnect, overtime, incomplete round, assist/flash, KAST trade, and weapon-alias cases.
