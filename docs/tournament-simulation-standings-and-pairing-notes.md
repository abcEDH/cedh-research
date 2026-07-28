# Tournament Simulation Standings And Pairing Notes

Date: 2026-05-26

## Local Worktree Snapshot

This note summarizes the current uncommitted worktree, not only the latest standings fix. The tracked diff currently spans 29 files with roughly 2,197 insertions and 425 deletions, plus untracked source files, tests, docs, local caches, and generated model artifacts.

High-level areas changed:

- Regional Elo pages now separate displayed TopDeck Elo from internal prediction data more clearly, fetch latest played tournament metadata from event logs, adjust player profile commander prediction fields, and update related frontend tests.
- Tournament likelihood now has TopDeck tournament structure inference, precomputed profile extraction, a new simulator route, a streaming simulation runner, an SSE API route, and tests for structure/profile behavior.
- Backend ingestion defaults and workflow scheduling changed to a 45-day window, with league ingestion enabled by default, exclusive end-date handling, and TID manifest helpers plus tests.
- Player commander profiling now blends recent commander evidence into active commander predictions, and new offline backtest/training scripts evaluate active commander prediction baselines and ML challengers.
- Tournament simulation now carries richer player features, including TopDeck Elo and commander colors, supports richer draw/pod-outcome model artifacts, streams ongoing tournament simulations, handles exact top-cut probability propagation for supported cut sizes, and uses the updated standings tiebreaker order.
- Pairing research tooling was added to audit TopDeck pairings, evaluate candidate pairing algorithms against posted pairings, summarize evaluation results, and test the evaluator.
- Local generated artifacts include prepared tournament simulation caches and a rich draw-model cache. These are working artifacts, not source-code changes.

## Local Change Inventory

Tracked modified files:

```text
.github/workflows/ci-backend-ingestion.yml
apps/web/src/app/regional-elo/page.tsx
apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx
apps/web/src/app/regional-elo/player/[topdeckId]/player-profile-components.tsx
apps/web/src/app/regional-elo/regional-leaderboard-table.tsx
apps/web/src/app/tournament-likelihood/page.tsx
apps/web/src/lib/topdeck.ts
apps/web/tests/regional-elo/player-page-reads.test.ts
apps/web/tests/regional-elo/player-page.test.ts
apps/web/tests/regional-elo/regional-elo-cache.test.ts
apps/web/tests/regional-elo/regional-elo-page.test.ts
apps/web/tests/topdeck/topdeck.test.ts
packages/backend/src/backtest_tournament_sim_models.py
packages/backend/src/ingest.py
packages/backend/src/rebuild_global_elo_tables.py
packages/backend/src/rebuild_player_commander_profiles.py
packages/backend/src/run_historical_tournament_sim.py
packages/backend/src/run_topdeck_ongoing_tournament_sim.py
packages/backend/src/run_topdeck_player_outlook.py
packages/backend/src/sim_engine.py
packages/backend/src/sim_models.py
packages/backend/src/sim_pairings.py
packages/backend/src/sim_types.py
packages/backend/src/tournament_sim_runner.py
packages/backend/src/train_draw_model.py
packages/backend/tests/test_ci_backend_ingestion_workflow.py
packages/backend/tests/test_ingest.py
packages/backend/tests/test_sim_engine_exact_top_cut.py
packages/backend/tests/test_sim_pairings.py
```

Untracked files and directories:

```text
.cache/
AGENTS.md
apps/web/src/app/tournament-likelihood/precomputed-profiles.ts
apps/web/src/app/tournament-likelihood/simulate/
apps/web/tests/tournament-likelihood/
docs/tournament-simulation-standings-and-pairing-notes.md
packages/backend/data/draw_model_rich_cache.pkl
packages/backend/src/audit_topdeck_pairings.py
packages/backend/src/backtest_active_commander_model.py
packages/backend/src/evaluate_pairing_hybrid_policy.py
packages/backend/src/evaluate_topdeck_pairings.py
packages/backend/src/summarize_pairing_evaluation.py
packages/backend/src/train_active_commander_ml.py
packages/backend/src/train_pod_outcome_model.py
packages/backend/tests/test_active_commander_backtest.py
packages/backend/tests/test_active_commander_ml.py
packages/backend/tests/test_evaluate_topdeck_pairings.py
packages/backend/tests/test_historical_tournament_sim.py
packages/backend/tests/test_ongoing_tournament_sim_parity.py
packages/backend/tests/test_pod_outcome_model.py
packages/backend/tests/tournament_sim_model_validation.md
```

## Frontend Changes

### Regional Elo

- `apps/web/src/app/regional-elo/page.tsx`
  - Adds `fetchLatestPlayedTournaments(playerIds)`, using `global_elo_game_event_log` and `tournaments` to derive the latest event a player actually played.
  - Avoids using future signup data as "latest tournament" metadata.
  - Bumps regional Elo cache keys.

- `apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx`
  - Updates player commander profile handling to use `active_commander_prediction_score`, `latest_commander`, `latest_commander_date`, and `commander_predictions`.
  - Adds UI for predicted active commander, latest commander, and top predictions.
  - Changes home region priority to prefer `globalEloRank.primary_region_key`.

- `apps/web/src/app/regional-elo/player/[topdeckId]/player-profile-components.tsx`
  - Reads the new commander profile fields.
  - Adjusts cache keys and home region/country fallback behavior.

- `apps/web/src/app/regional-elo/regional-leaderboard-table.tsx`
  - Renames the displayed Elo label to `TopDeck Elo`.
  - Generalizes empty-state copy.

- Regional Elo tests were updated under `apps/web/tests/regional-elo/` for the changed cache keys, profile fields, and page behavior.

### Tournament Likelihood

- `apps/web/src/lib/topdeck.ts`
  - Adds tournament structure inference from TopDeck event text.
  - Adds fallback Swiss round/top cut defaults by player count, following the TopDeck Commander addendum behavior.
  - Adds `fetchTournamentStructureDefaults`.

- `apps/web/src/app/tournament-likelihood/page.tsx`
  - Uses the new structure defaults.
  - Adds `swissRounds` and `topCut` URL handling.
  - Adds a simulator entry point from tournament likelihood pages.
  - Moves precomputed profile transformation into a helper module.

- `apps/web/src/app/tournament-likelihood/precomputed-profiles.ts`
  - New helper for building profile rows and metagame shares from precomputed records.
  - Uses `model_share` when available.

- `apps/web/src/app/tournament-likelihood/simulate/`
  - Adds a simulator page that reads tournament id, Swiss rounds, top cut, and run-time parameters.
  - Adds a client-side streaming runner for snapshots, probability tables, active/completed pods, point lines, and run controls.
  - Adds an SSE route that spawns `run_topdeck_ongoing_tournament_sim.py` and streams simulation output.

- Tests were added or updated under `apps/web/tests/topdeck/` and `apps/web/tests/tournament-likelihood/`.

## Backend Changes

### Ingestion

- `.github/workflows/ci-backend-ingestion.yml`
  - Scheduled backend ingestion now uses `--days 45`.
  - Removes the previous `--min-players 32` filter.

- `packages/backend/src/ingest.py`
  - Defaults the ingestion window to 45 days.
  - Enables league ingestion by default while preserving an explicit opt-out.
  - Treats the end date as an exclusive next-day boundary.
  - Adds TID manifest load/write/chunk helpers and a default backfill run key.

- Tests in `packages/backend/tests/test_ci_backend_ingestion_workflow.py` and `packages/backend/tests/test_ingest.py` cover those ingestion changes.

### Player Commander Profiles

- `packages/backend/src/rebuild_player_commander_profiles.py`
  - Blends model commander share with latest commander evidence.
  - Normalizes date values before comparison.
  - Sorts predictions by model share and stores active commander scores from that share.

- `packages/backend/src/rebuild_global_elo_tables.py`
  - Adds timezone-aware datetime parsing for event start comparisons.

- `packages/backend/src/backtest_active_commander_model.py`
  - New offline backtest for next active commander prediction using production/current/last-played/most-played/hybrid distributions and latest-weight sweeps.

- `packages/backend/src/train_active_commander_ml.py`
  - New offline challenger training script with usage, history, decklist, and hidden Elo features.

- Tests were added in `packages/backend/tests/test_active_commander_backtest.py` and `packages/backend/tests/test_active_commander_ml.py`.

### Tournament Simulation And Modeling

- `packages/backend/src/run_historical_tournament_sim.py`
  - Defaults to the v4 hybrid draw model path.
  - Fetches TopDeck Elo by TopDeck id.
  - Adds commander colors and TopDeck Elo to `SimPlayer`.
  - Handles TopDeck datetime values with short fractional seconds.

- `packages/backend/src/sim_types.py`
  - Adds `topdeck_elo` and `commander_colors` to simulated player data.
  - Adds `standings_random_tiebreakers` to tournament state.

- `packages/backend/src/sim_models.py`
  - Extends loaded draw model metadata with target/classes.
  - Adds TopDeck Elo and commander color features.
  - Adds pod-outcome probability support for multiclass artifacts.
  - Keeps top-cut draw probability forced to zero.

- `packages/backend/src/train_draw_model.py`
  - Adds winner index, TopDeck Elo, commander colors, bracket rows, and top-cut rows to draw model training/cache rows.
  - Preserves compatibility with cached rows that do not yet have the new fields.

- `packages/backend/src/train_pod_outcome_model.py`
  - New multiclass pod outcome model trainer, including top-cut rows.

- `packages/backend/src/sim_engine.py`
  - Uses combined pod outcome probabilities.
  - Allows exact top-cut propagation to start from later rounds.
  - Reduces or samples larger cuts until exact supported cut sizes are reached.
  - Uses seeded random fallback for exact standings ties after points, OMW, and tiebreak seed.

- `packages/backend/src/tournament_sim_runner.py`
  - Emits only advancement sizes present in the summary.

- `packages/backend/src/run_topdeck_ongoing_tournament_sim.py`
  - Adds prepared-state caching under `.cache/tournament-sim`.
  - Adds streaming/batched simulation output with worker and time-budget controls.
  - Adds fast live mode and active/completed pod metadata.
  - Uses requested advancement sizes based on actual top cut.
  - Uses richer pod outcome probabilities and seeded random fallback for top-cut ties.

- `packages/backend/src/run_topdeck_player_outlook.py`
  - Uses pod outcome probabilities.
  - Supports current-state top-cut probability even without an active pod.
  - Emits conditional win/loss/draw top-cut outlooks for the target active pod.
  - Uses seeded random fallback in top-cut checks.

- `packages/backend/src/backtest_tournament_sim_models.py`
  - Adds prepared tournament reuse, checkpoint/resume/retry behavior, atomic output, progress logging, error tracking, model load timing, and stdout filtering.

- Tests were added or updated in:

```text
packages/backend/tests/test_historical_tournament_sim.py
packages/backend/tests/test_ongoing_tournament_sim_parity.py
packages/backend/tests/test_pod_outcome_model.py
packages/backend/tests/test_sim_engine_exact_top_cut.py
packages/backend/tests/test_sim_pairings.py
```

### Pairing Evaluation Tools

- `packages/backend/src/audit_topdeck_pairings.py`
  - New audit tool for comparing TopDeck posted pairings with stored games and identifying duplicate delete candidates.

- `packages/backend/src/evaluate_topdeck_pairings.py`
  - New evaluator for candidate pairing algorithms against historical TopDeck pairings.
  - Reports pair recall, precision, exact pod recall, and table exact recall.

- `packages/backend/src/summarize_pairing_evaluation.py`
  - New summarizer for pairing evaluation JSON outputs.

- `packages/backend/src/evaluate_pairing_hybrid_policy.py`
  - New helper for learning/evaluating a hybrid pairing policy from evaluation output.

- `packages/backend/tests/test_evaluate_topdeck_pairings.py`
  - Tests the pairing evaluator behavior.

## Generated And Local-Only Artifacts

- `.cache/`
  - Contains prepared tournament simulation caches, including cache entries from tournament simulation work.

- `packages/backend/data/draw_model_rich_cache.pkl`
  - Generated rich draw-model cache artifact.

- `AGENTS.md`
  - Untracked repo-root agent instruction file, matching the project guidance used for this work.

- `packages/backend/tests/tournament_sim_model_validation.md`
  - Untracked validation note for tournament simulation modeling work.

## Context

While simulating `the-side-quest-redemption-event&swissRounds=5&topCut=16`, Jack Selvig was shown as having a 0% chance to make Top 16 after round 5 results were entered. Jack later appeared in Top 4, which exposed a standings/tiebreaker mismatch in the simulator.

## TopDeck OMW Finding

TopDeck's current tournament payload exposes final/current `winRate` and `opponentWinRate`, but not per-round standings snapshots. Replaying the posted Swiss round tables for Side Quest and recomputing final standings showed that TopDeck's `opponentWinRate` is matched exactly by:

```text
player match-point rate = max(points / (5 * matches), 0.20)
opponentWinRate = average(match-point rate of unique opponents)
```

Byes continue to be represented as three synthetic opponents at `0.20`, matching the Commander MTRA addendum language already captured in `docs/tournament-rules/topdeck-commander-mtra-addendum-v2.2-2024-05-13.md`.

The previous simulator formula used:

```text
max(wins / matches, 0.20)
```

That incorrectly treated draws as 0 for opponent tiebreak purposes. TopDeck's formula gives a draw 1 match point, which contributes `1 / 5 = 0.20` of a match win.

For Jack Selvig in Side Quest:

```text
R1: points=1,  W-D-L=0-1-0, proposed OMW=0.200000, old OMW=0.200000
R2: points=6,  W-D-L=1-1-0, proposed OMW=0.200000, old OMW=0.200000
R3: points=6,  W-D-L=1-1-1, proposed OMW=0.370370, old OMW=0.325926
R4: points=11, W-D-L=2-1-1, proposed OMW=0.358333, old OMW=0.300000
R5: points=11, W-D-L=2-1-2, proposed OMW=0.355333, old OMW=0.300000
```

After round 5, the replayed formula matched TopDeck for all 133 players:

```text
points max error: 0
winRate max abs error: 0
opponentWinRate max abs error: 0
```

The resulting Swiss Top 16 seed order also matched TopDeck's posted Top 16 bracket exactly. Jack was Swiss seed 15.

## Code Changes Made

- `packages/backend/src/sim_pairings.py`
  - Added `match_point_percentage`.
  - Updated `opponent_match_win_percentage` to average opponent match-point percentage instead of raw opponent win rate.
  - Kept `match_win_percentage` as a compatibility alias to the corrected match-point percentage behavior.
  - Standings sort now uses:

```text
points -> TopDeck-style OMW -> tiebreak_seed -> seeded random fallback -> player_id safety fallback
```

- `packages/backend/src/sim_types.py`
  - Added `standings_random_tiebreakers` to `TournamentState` so each simulated state can keep a consistent random fallback ordering.

- `packages/backend/src/sim_engine.py`
  - Clones `standings_random_tiebreakers`.
  - Passes the simulation RNG into `select_top_cut` so exact ties after `tiebreak_seed` are randomized reproducibly.

- `packages/backend/src/run_topdeck_ongoing_tournament_sim.py`
  - Passes the simulation RNG into live Top Cut selection.

- `packages/backend/src/run_topdeck_player_outlook.py`
  - Passes the simulation RNG into player-outlook Top Cut checks.

- `packages/backend/tests/test_sim_pairings.py`
  - Added coverage that OMW uses match points, so an opponent with `1 win, 1 draw, 1 loss` contributes `6 / 15 = 0.40`.
  - Added coverage that exact ties after `tiebreak_seed` use the seeded random fallback.

## Verification Run

Targeted checks passed:

```bash
PYTHONPATH=packages/backend/src python3 -m unittest packages/backend/tests/test_sim_pairings.py
PYTHONPATH=packages/backend/src python3 -m unittest packages/backend/tests/test_ongoing_tournament_sim_parity.py
PYTHONPATH=packages/backend/src python3 -m unittest packages/backend/tests/test_sim_engine_exact_top_cut.py
PYTHONPATH=packages/backend/src python3 -m py_compile \
  packages/backend/src/sim_pairings.py \
  packages/backend/src/sim_engine.py \
  packages/backend/src/sim_types.py \
  packages/backend/src/run_topdeck_ongoing_tournament_sim.py \
  packages/backend/src/run_topdeck_player_outlook.py
```

An event-specific smoke replay of Side Quest with the patched code produced:

```text
Jack rank: 15
Jack OMW: 0.355333333333
Jack in Top 16: true
```

## Current Swiss Pairing Algorithm

The future-round Swiss pairing code currently lives in `packages/backend/src/sim_pairings.py`.

Current behavior:

1. Filter to `eligible_player_ids` when present.
2. Group players by exact record tuple:

```text
(points, wins, draws, -losses)
```

3. Sort those record groups descending.
4. Shuffle players within each exact record group using the simulation RNG.
5. Flatten groups into one ordered player list.
6. Chunk adjacent players into pods using `_topdeck_pod_sizes`.
7. For 4-player events, pod sizes are:

```text
4n     -> all 4-player pods
4n + 1 -> tail becomes three 3-player pods when possible
4n + 2 -> tail becomes two 3-player pods when possible
4n + 3 -> one 3-player pod
```

8. If repeat-opponent avoidance is enabled and the generated pod count is at or below `repeat_avoidance_max_pods`, greedily swap players between pods to reduce repeated pairings.
9. Shuffle seats independently.

If TopDeck has already posted the current active round, `simulate_swiss` locks those posted pods for that round instead of generating pairings.

## Open Pairing Questions

The current pairing algorithm is not yet confirmed as TopDeck-faithful. The main questions are:

- TopDeck may pair by points only, while current code groups by `(points, wins, draws, losses)`.
- Repeat-avoidance swaps can move players across record groups. That may violate strict points-bracket pairing.
- Need to compare simulated pairings against posted TopDeck pairings round by round across multiple completed events.
- Need to decide how to handle exact pairing ambiguity when many TopDeck-valid pairings are possible.
