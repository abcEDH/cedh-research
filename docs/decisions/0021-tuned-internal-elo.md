# 0021 — Versioned internal Elo and atomic maintenance

## Status

Accepted — production rollout authorized September 18, 2026.

## Context

Internal Elo supports predictions; displayed ranking Elo continues to come from
TopDeck. Independent maintenance arithmetic could overwrite a validated replay.
Quarterly chronological validation supports separate Swiss and top-cut settings.

## Decision

`packages/backend/src/internal_elo.py` owns model `2026-09-18-quarterly-v1`, using
full-precision fitted constants. The divisor stays 200. Rounded reference values:

| Parameter | Value |
|---|---:|
| Swiss seats 1–4 | 0, -48.820457, -97.044914, -144.806269 |
| Top-cut seats 1–4 | 0, -117.592137, -172.635508, -227.766386 |
| Swiss decisive K | 64.201061 |
| Swiss draw K | 21.142981 |
| Top-cut K | 39.671755 |
| League multiplier | 0.579433 |

Seat adjustments require four distinct known seats in a four-player pod. The
persisted tournament league flag scales the applicable K. Numeric rounds are
Swiss; named `top N`/`final` stages use top-cut settings, matching the experiment.

A top-cut draw becomes a modeled win for the sole participant appearing in the
next smaller recorded stage, otherwise seat 1. Missing seat 1 or multiple possible
advancers fails closed for review. Raw source outcomes remain unchanged; Elo
events and W–L–D counts use the modeled outcomes. Remaining Swiss draws retain
their shared actual scores. Later stages resolve labels only, never features.
The research snapshot converted 567 draws: 565 seat-1 winners, two other winners;
554 seat-1 labels have no later-stage confirmation and are policy assumptions.

All completed eligible events, including leagues and small events, participate.
Future games and unresolved non-league player/round collisions remain excluded.
Previously live safety migrations are included in source control for fresh DBs.

Publishing entry points delegate to `internal_elo_maintenance`: full replay,
temporary staging, source fingerprint validation, compressed backups, and an
atomic replacement of five derived Elo tables plus a model-run record. Changed
source rows abort publication. Independent legacy/incremental arithmetic no
longer owns production ratings. Existing job lifecycle, dispatch ownership, and
downstream materialized-view refresh remain in the maintenance CLI.

## Validation and consequences

The fitting objective scores decisive games from 2024 onward; all earlier games
initialize Elo. Seven quarterly evaluations covered 198,970 decisive games from
2025 through September 14, 2026. The full-model procedure improved overall loss
in all seven quarters, by 0.0846% pooled (0.7228% for non-league top cut). Fitting
loss across all dates was 0.0090% worse in the pooled comparison. These are
retrospective comparisons. The final fit through September 14 needs confirmation
on future games. Tournament-start ordering lacks exact timestamps for overlapping
events and long leagues.

Reevaluate parameters quarterly; this is a research/release cadence, not an
automatic optimizer deployment. Full replays cost more but prevent mixed-model
rating histories and include backfills. Preserve rollback backups. Rollback must
restore all five tables together and redeploy matching prediction constants.
