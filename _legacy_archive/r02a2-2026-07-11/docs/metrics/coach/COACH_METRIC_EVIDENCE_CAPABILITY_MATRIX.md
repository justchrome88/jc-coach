# Coach Metric Evidence Capability Matrix

The retained demos and demoparser2 `0.41.3` expose round/warmup state,
`team_num`, spawn/connect/disconnect events, weapon fire, hurt, death, assist,
blind, grenade identity and ticks. H01A-M04 adds the compact
`coach-metric-events-v1` event set; it does not replace prior parser artifacts.

| Metrics | Raw evidence and relations | Pre-M04 state | H01A-M04 classification |
|---|---|---|---|
| rounds, participation, T/CT | round start/end, warmup, roster, spawn, connect/disconnect, team number | round boundaries available; quiet participation incomplete | retained-demo reparse required; available and validated |
| kills, deaths, assists, HS kills, opening, multi-kills | death tick, actor/victim/assister Steam IDs and teams, headshot | current artifact available | available; v3 relation validation required |
| effective damage, ADR | all hurt ticks, health after, actor/victim teams, per-round health reset | damage present but team/remaining-health proof absent | retained-demo reparse required; available and validated |
| KAST, trades | round participation plus ordered team death lineage | trade/quiet rounds incomplete | retained-demo reparse required; available and validated |
| utility damage | hurt weapon, owner/victim teams, remaining health | raw utility attribution present | retained-demo reparse required; available and validated |
| detonations, smokes | HE/smoke/flash/inferno entity and owner | current artifact available | available; entity-deduped v3 ledger |
| effective flashes | blind duration, owner/victim teams, round end | duration present; enemy relation incomplete | retained-demo reparse required; available and validated |
| shots, hits, hit HS%, accuracy | weapon fire plus enemy hurt and hitgroup | aggregate weapon stats only | retained-demo reparse required; available and validated |
| first bullet, engagement timing | shot/hurt/death ticks, weapon, round/team relation | shot timeline absent | retained-demo reparse required; available under local contract |
| map/side/weapon class | match map, round team, canonical weapon aliases | partial | derivable from v3 event set; query-time aggregation |
| view-angle/crosshair, spray trajectory | per-tick angles/trajectory | intentionally absent | not obtainable for this pack; no claim |
| HLTV/AIM/grenade universal scores | undocumented composite formulas | absent | excluded, not implemented |

Identity is always owner user, owner Steam ID, measured player Steam ID, match,
demo hash, original parser artifact, v3 event-set hash and semantic version.
Unclassified team or participation evidence blocks the affected match rather
than weakening a trusted calculation.
