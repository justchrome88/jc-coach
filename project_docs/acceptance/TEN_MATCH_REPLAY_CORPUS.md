> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/metrics/coach/TEN_MATCH_REPLAY_CORPUS.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Ten-Match Canonical Replay Corpus

The H01B-R01 corpus contains exactly ten retained owner matches ordered by
actual `played_at`. All have retained demos, accepted parser artifacts, and
validated Coach Metric Pack v1 sources.

| Seq | Match | Time | Result | Score | ADR | KAST | Deaths / opening / untraded | Multi-kill rounds | Utility damage | Shot accuracy | Edge coverage |
|---:|---:|---|---|---|---:|---:|---|---:|---:|---:|---|
| 1 | 29 | 2026-06-06 19:56 | loss | 5:13 | 32.444 | 38.889 | 14 / 3 / 13 | 1 | 0 | 24.286 | severe impact/death leak; low utility |
| 2 | 30 | 2026-06-11 18:32 | win | 13:11 | 97.417 | 87.500 | 17 / 0 / 13 | 4 | 14 | 27.660 | high impact, strong participation |
| 3 | 35 | 2026-06-12 20:09 | draw | 15:15 | 78.367 | 73.333 | 23 / 2 / 20 | 7 | 0 | 21.505 | overtime, multi-kills, zero utility |
| 4 | 120 | 2026-06-13 16:20 | draw | 15:15 | 66.900 | 63.333 | 25 / 2 / 21 | 4 | 73 | 22.253 | required id; overtime; repeated deaths |
| 5 | 117 | 2026-06-13 20:18 | win | 13:5 | 89.500 | 72.222 | 10 / 1 / 8 | 5 | 137 | 21.963 | required id; high utility context |
| 6 | 109 | 2026-06-26 19:56 | loss | 2:13 | 29.200 | 40.000 | 14 / 1 / 13 | 1 | 0 | 10.769 | low-impact/quiet negative context |
| 7 | 79 | 2026-07-03 18:55 | loss | 9:13 | 101.409 | 72.727 | 15 / 1 / 14 | 7 | 32 | 22.222 | clear outcome-vs-impact mismatch |
| 8 | 92 | 2026-07-07 22:51 | draw | 2:2 | 69.750 | 100.000 | 3 / 0 / 3 | 0 | 0 | 25.000 | four-round incomplete/quiet edge |
| 9 | 122 | 2026-07-10 00:40 | win | 8:5 | 114.615 | 84.615 | 7 / 1 / 6 | 4 | 61 | 23.333 | required id; incomplete side-switch edge |
| 10 | 124 | 2026-07-10 19:01 | win | 13:7 | 82.150 | 70.000 | 10 / 1 / 9 | 5 | 144 | 24.051 | required golden fixture; high utility/aim context |

The corpus covers useful/useless death patterns, outcome/impact mismatch,
opening duels, bounded trade context, high/low utility, multi-kills, aim,
overtime, and incomplete/quiet edges. Playlist remains provenance-only.
