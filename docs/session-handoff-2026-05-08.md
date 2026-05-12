# Session Handoff - 2026-05-08

## Current State

This repo has been updated substantially in four main areas:
- player Elo tuning and rebuild logic
- tournament simulation / Monte Carlo tooling
- draw-model training and evaluation

This file is meant to let a new session recover the important context quickly.

## Final Player Elo Settings

The current tuned player-Elo settings are:
- decisive `K = 64`
- draw `K = 26`
- 4-seat offsets:
  - seat 1: `0`
  - seat 2: `-52`
  - seat 3: `-96`
  - seat 4: `-145`
- draw-seat weighting is enabled for valid 4-player draw pods

These settings are reflected in:
- `packages/backend/src/rebuild_global_elo_tables.py`
- `packages/backend/src/recompute_global_elo_all_games.py`

Touched files include:
- `packages/backend/src/sim_types.py`
- `packages/backend/src/sim_models.py`
- `packages/backend/src/sim_engine.py`
- `packages/backend/src/run_topdeck_ongoing_tournament_sim.py`
- `packages/backend/src/run_topdeck_player_outlook.py`
- `packages/backend/src/run_historical_tournament_sim.py`
- `packages/backend/src/run_historical_tournament_from_round_sim.py`
- `packages/backend/src/backtest_resume_tournament_sim.py`
- `packages/backend/src/rebuild_global_elo_tables.py`
- `packages/backend/src/recompute_global_elo_all_games.py`


## Simulation Architecture

The current simulation stack now uses:
- player Elo only
- no in-tournament Elo updates
- lighter live-page summary outputs

Live summary outputs now focus on advancement probabilities rather than expected points / expected finish:
- `Top 40`
- `Top 16`
- `Top 4`
- `Win`

Files:
- `packages/backend/src/sim_types.py`
- `packages/backend/src/sim_models.py`
- `packages/backend/src/sim_engine.py`
- `packages/backend/src/sim_pairings.py`

## Top 40 Play-In Format

Quest-style `Top 40` was clarified and implemented as:
- after Swiss, seeds `1-8` get byes
- seeds `9-40` play in `8` snake-seeded pods
- `8` winners join seeds `1-8`
- then `Top 16` is reseeded by original Swiss seed and paired as snake pods

Implementation is in:
- `packages/backend/src/sim_pairings.py`

Current `Top 16` snake pattern:
- pod 1: `1, 8, 9, 16`
- pod 2: `2, 7, 10, 15`
- pod 3: `3, 6, 11, 14`
- pod 4: `4, 5, 12, 13`

## Seat Bonus In Simulation

Seat bonus is still used in simulation to determine decisive pod winner probabilities.

It is applied through:
- `effective_player_rating(...)`
- `predict_decisive_win_probabilities(...)`

in:
- `packages/backend/src/sim_models.py`

There was a review comment claiming seat bonus was not being used. That was not a functional bug. The issue was only an unused import of `SEAT_ELO_BONUS` in `sim_engine.py`, which was removed.

## Runtime Optimization Work Done

Several runtime optimizations were attempted:
- precompute locked current-round probabilities once
- lighter live-page summary mode
- disable round draw-rate bookkeeping in live mode
- fast live mode to avoid unnecessary mutation of some historical context
- remove in-tournament Elo updates

Conclusion:
- these helped somewhat
- but not enough to make `1000`-sim live runs truly fast
- the remaining bottleneck is still the object-heavy Python simulation architecture

Likely next big optimization options:
- reduce live-page sims substantially
- cache results by tournament snapshot
- redesign the simulator around lighter state representation / arrays

## Quest Simulation Status

Multiple Quest runs were started historically, but most did not finish and left empty files in `/tmp`.

Only one Quest run produced a completed JSON artifact:
- `/tmp/the_quest_part_1_1000sims_benchmark_fastpath_v3.json`

That run used:
- `1000` sims
- `6` Swiss rounds
- simpler `Top 40` interpretation from before the full `Top 40 -> Top 16` play-in patch

So those results are useful as a prior, but not the final correct Quest format.

Top win probabilities from that completed run:
- Jason Doan // CriticalEDH: `8.4%`
- Atlas Kulish: `6.0%`
- Evan Pierce: `5.3%`
- Alex Lien: `5.0%`
- Sam Black: `4.7%`

Top `Top 40` probabilities:
- Jason Doan // CriticalEDH: `63.9%`
- Isaiah wright: `59.7%`
- Atlas Kulish: `59.7%`
- Evan Pierce: `57.0%`
- Sam Black: `56.9%`

Top `Top 16` probabilities:
- Jason Doan // CriticalEDH: `48.4%`
- Isaiah wright: `43.3%`
- Atlas Kulish: `43.1%`
- Evan Pierce: `40.1%`
- Sam Black: `38.6%`

Top `Top 4` probabilities:
- Jason Doan // CriticalEDH: `22.7%`
- Atlas Kulish: `17.2%`
- Evan Pierce: `17.1%`
- Isaiah wright: `16.1%`
- Sam Black: `15.8%`

No completed Quest artifact yet exists for the corrected `Top 40 play-in -> Top 16` format.

## Steel City Benchmark

A run was started to benchmark:
- last Swiss round + top cut only
- `1000` sims
- Steel City Spectacular

Purpose:
- estimate how much faster “resume from late event state” is versus simulating the full tournament

If the machine is restarted, assume that timing/result may be lost unless the output file was completed before restart.

## Draw Model

The current reference draw model is `v8`.

Key facts:
- exact artifact existed in `/tmp`
- it has been copied into a durable repo-local location
- the tested weighting experiments did not beat the current `v8` all-games holdout baseline

Saved artifact directory:
- `packages/backend/reports/draw-model/v8`

Saved files:
- `packages/backend/reports/draw-model/v8/cedh_draw_model_artifact_v8.pkl`
- `packages/backend/reports/draw-model/v8/cedh_draw_model_report_v8.json`
- `packages/backend/reports/draw-model/v8/cedh_draw_model_rich_cache_v8.pkl`
- `packages/backend/reports/draw-model/v8/cedh_draw_model_weight_experiments_v9_candidate.json`

Important:
- this is safe from `/tmp` cleanup
- but it is only repo-local, not necessarily committed

## Draw Model Results

The v8 weighting experiments showed:
- no tested weighting variant beat the existing `v8` baseline on the all-games holdout objective

Baseline holdout result:
- log loss `0.4597696739146026`
- Brier `0.1489796429158125`

Next likely path for improving `P(draw)`:
- feature changes, not just sample weighting

## Draw Backtest Slice Report

A slice report was built to analyze draw-model performance by:
- `rounds_remaining`
- tournament size buckets

Important takeaway:
- worst draw-rate fit was not necessarily at `1` round remaining
- smaller large-event buckets and some `2 rounds remaining` slices were worse than pure last-round slices

Relevant helper:
- `packages/backend/src/summarize_draw_backtest_slices.py`

## Recommended Next Steps

If starting a fresh session, the highest-value next actions are:

1. Decide whether to keep live sims at low counts
- likely `100-250` for interactive pages
- unless simulator architecture is redesigned

2. If needed, rerun Quest under the corrected `Top 40 -> Top 16` structure
- because no completed artifact exists yet for that exact format

3. If needed, benchmark late-event simulation speed
- Steel City from after round `7` is a good measuring case

