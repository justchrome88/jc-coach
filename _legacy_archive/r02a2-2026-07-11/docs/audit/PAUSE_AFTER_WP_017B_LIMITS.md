# Pause After WP-017B Due To Limits

Date: 2026-07-04

Current product version: v0.8.

Last completed WP:
- WP-017B Controlled Bulk Import Plan / Settings.

Last commit before pause:
- d4f7e80 Plan controlled bulk import batch.

Current DB SHA:
- 36ccd84dc5c695af1c75a74f8d1059ade68a2a0355bb43aca1a7b473dd68f320

Current safe state:
- git status clean;
- jc-coach.service active/running;
- data/uploads about 3.8G;
- data/tmp empty/trivial;
- data/manual_backups about 1.2G;
- root has about 18G available;
- 29 demo files;
- no queued/running steam_import_all jobs.

Next WP:
- WP-017C First Controlled Bulk Import Batch.

Do not start WP-017C without explicit live-run authorization.
WP-017C may mutate production DB, download demos, run parser and create recommendation evaluations.

Rules for resume:
- keep STEAM_IMPORT_MAX_DEMOS_PER_RUN=1;
- backup DB before first live run;
- max 3 one-demo attempts;
- stop after every terminal attempt;
- do not raise cap;
- do not delete/move/compress raw demos;
- do not generate persistent reports;
- do not run full resync;
- shell fallback must use TMPDIR/TEMP/TMP=/opt/jc-coach/data/tmp.
