# PR 127 Summary

## Summary

This branch is now broader than the original commander-normalization patch. It currently includes:
- commander normalization and legal partner-pair canonicalization
- generated legality/review artifacts for partner ordering
- TopDeck Elo snapshot import plus Elo rebuild/maintenance updates
- tournament simulation and draw-model training infrastructure
- historical continuation backtests and live TopDeck outlook tooling
- player-profile and tournament-likelihood UI updates
- removal of commander Elo from the active simulation/rebuild pipeline

## Main Areas Changed

The diff against `main` is concentrated in these areas:
- `.github/workflows/ci-backend-maintenance.yml`
- `.github/workflows/topdeck-elo-import.yml`
- `apps/web/src/lib/meta-prep.ts`
- `apps/web/src/app/tournament-likelihood/tournament-analysis-tables.tsx`
- `apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx`
- `packages/backend/src/ingest.py`
- `packages/backend/src/backfill_moxfield_commanders.py`
- `packages/backend/src/generate_legal_commander_pairings.py`
- `packages/backend/src/generate_missing_partner_order_review.py`
- `packages/backend/src/rebuild_global_elo_tables.py`
- `packages/backend/src/recompute_global_elo_all_games.py`
- `packages/backend/src/rebuild_player_commander_profiles.py`
- `packages/backend/src/regional_elo.py`
- `packages/backend/src/train_draw_model.py`
- `packages/backend/src/train_draw_model_weight_experiments.py`
- `packages/backend/src/summarize_draw_backtest_slices.py`
- `packages/backend/src/sim_types.py`
- `packages/backend/src/sim_pairings.py`
- `packages/backend/src/sim_models.py`
- `packages/backend/src/sim_engine.py`
- `packages/backend/src/run_historical_tournament_sim.py`
- `packages/backend/src/run_historical_tournament_from_round_sim.py`
- `packages/backend/src/run_topdeck_ongoing_tournament_sim.py`
- `packages/backend/src/run_topdeck_player_outlook.py`
- `packages/backend/src/backtest_resume_tournament_sim.py`
- `packages/backend/src/fix_top_cut_labels.py`
- `packages/backend/data/legal_commander_pairings.json`
- `packages/backend/tests/test_ingest.py`
- `packages/backend/supabase/migrations/20260507170000_drop_global_commander_elo_tables.sql`
- `docs/partner-community-order-review.csv` (deleted)

## Commander Normalization And Legality

- Hardens `ingest.py` so commander payloads are normalized before write time:
  - strips escaped apostrophes
  - removes DFC back faces from commander names
  - rewrites Stranger Things Secret Lair names to in-universe equivalents
  - canonicalizes legal partner-pair ordering
  - maps illegal two-card pairings to `Unknown Commander`
- Applies the same normalization path to `backfill_moxfield_commanders.py` so repair/backfill jobs write the same canonical commander names as ingest.
- Adds `generate_legal_commander_pairings.py` to build `legal_commander_pairings.json` from Scryfall oracle data as the canonical legality/order reference.
- Replaces the checked-in archival review sheet by deleting `docs/partner-community-order-review.csv` and generating missing-order review artifacts from code instead.

## Partner Order Review Workflow

- Adds `generate_missing_partner_order_review.py` to emit a review queue for legal partner pairings not yet represented in stored commander rows.
- The generated review output includes direct search URLs for Reddit-focused search, X, and general web search so missing community ordering can be reviewed from discussion sources rather than inferred from TopDeck entry order.

## Commander Forecasting

- Updates commander-recommendation weighting in `apps/web/src/lib/meta-prep.ts`, `rebuild_player_commander_profiles.py`, and `regional_elo.py` to use a `24`-day recency half-life.
- This keeps the app-side forecast logic and the precomputed commander-profile rebuild aligned on the same weighting model.

## Elo Changes

- Updates `rebuild_global_elo_tables.py` and `recompute_global_elo_all_games.py` to use the currently tuned player-Elo settings:
  - `K_win = 64`
  - `K_draw = 26`
  - 4-seat offsets: `0 / -52 / -96 / -145`
  - draw-seat weighting enabled for valid 4-player draw pods
- Keeps TopDeck Elo enrichment support, including fallback handling for either `topdeck_id` or legacy `uid` in `topdeck_player_elos`.
- Keeps incremental rebuild support from `--since-start-date` so append-only Elo refreshes can replay only the affected suffix instead of replaying the full historical stream.
- Removes commander Elo from the active rebuild/recompute pipeline and adds a Supabase migration to drop the commander-Elo tables.

## Tournament Simulation

- Adds a resumable Monte Carlo tournament simulator:
  - `sim_types.py`
  - `sim_pairings.py`
  - `sim_models.py`
  - `sim_engine.py`
- Supports:
  - full-tournament simulation from pre-event state
  - resume-state simulation from a historical or live checkpoint
  - current-round pod locking for posted Swiss pairings
  - historical continuation backtests from completed-round checkpoints
  - TopDeck top-cut pod layouts for `Top 16`, `Top 10`, and the `Top 40 -> Top 16` play-in structure used by Quest-style events
- The current simulation stack now uses:
  - player Elo only
  - no commander Elo
  - no in-tournament Elo updates
  - lighter live-page summary outputs focused on advancement probabilities rather than expected-points / expected-finish bookkeeping

## Draw Modeling And Evaluation

- Adds draw-model training in `train_draw_model.py` for `P(draw)` with richer tournament-state features, including:
  - standings and cut-pressure features
  - OMW-aware bubble context
  - draw-safe / must-win incentive counts
  - rank/cut-band features
  - player-style and familiarity features
- Adds `train_draw_model_weight_experiments.py` to rerun the `v8` holdout protocol under alternative weighting schemes.
- Adds `summarize_draw_backtest_slices.py` to summarize draw-model backtests by:
  - rounds remaining
  - tournament size buckets
- Current branch finding: the tested weighting tweaks did not beat the existing `v8` all-games holdout baseline.

## Historical Backtesting And Live Outlook Tooling

- Adds `run_historical_tournament_sim.py` and `run_historical_tournament_from_round_sim.py` to simulate from full-tournament and post-round historical states.
- Adds `backtest_resume_tournament_sim.py` to score checkpointed tournament continuations on:
  - winner probability / log loss
  - top-cut Brier
  - top-cut overlap
  - remaining-round draw-rate MAE
- Adds `fix_top_cut_labels.py` to repair `made_top_cut` / `made_top_16` labels from `final_standing` and tournament cut structure.
- Adds `run_topdeck_ongoing_tournament_sim.py` and `run_topdeck_player_outlook.py` for live TopDeck event simulation and player-facing outlook generation.

## UI Updates

- `tournament-likelihood` attendee tables now display and sort by `TopDeck Elo` instead of the hidden internal Elo field.
- Regional player achievements now default to `best` ordering, with `recent` available by clicking the date header.

## Maintenance And Data Refresh

- Updates `ci-backend-maintenance.yml` so scheduled maintenance also rebuilds `player_commander_profiles`.
- Adds a weekly `topdeck-elo-import.yml` workflow to import TopDeck’s published EDH Elo snapshot into `topdeck_player_elos`.

## Tests And Validation

- Extends `packages/backend/tests/test_ingest.py` to cover:
  - apostrophe cleanup
  - DFC stripping
  - Stranger Things alias rewrites
  - canonical legal-pair ordering
  - illegal-pair fallback to `Unknown Commander`
- Local `py_compile` verification was run on the touched Python modules after the recent simulation / Elo cleanup.

## Notes

- This PR now bundles the original commander/elo work together with the simulation, backtest, draw-model, and live-outlook tooling.
- If review scope becomes unwieldy, the simulator / draw-model / live-outlook work is still the main candidate to split into a follow-up PR.
