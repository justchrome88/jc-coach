# Metrics

Last updated: 2026-07-03.

This is the canonical placeholder for the runtime metric spec. Until every metric has a formula, source, confidence and suppression rule, metric output must be treated as mixed-confidence.

## Required Metric Contract

Each metric used in UI, diagnosis, recommendations or AI payload must define:

- Name.
- Formula.
- Source fields/events.
- Parser/import source support.
- Minimum sample size.
- Confidence level.
- Suppression rule.
- Known gaps.

## Current Truth

- K/D, kills, deaths and damage are generally reliable when source data provides death/damage events.
- ADR is reliable when damage and round counts are available.
- Accuracy is estimated from available `hits / weapon_fire`, not bullet-level truth.
- KAST, trades, traded deaths, early deaths, utility attribution, flash value and side splits need confidence labels and suppression.
- Crosshair placement, first bullet accuracy, spray control, positioning and heatmaps are not reliable current metrics.

## Next Work

Replace this placeholder with a full metric table before using weak metrics to drive primary diagnosis.

