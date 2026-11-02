# Tournament Simulation Model Validation

Use this checklist before treating a new tournament simulation or draw-model artifact as production-ready.

## Required Invariants

- Live/page simulations and script simulations must use the same modeling inputs and rules. Streaming is only an output mode.
- Swiss pairings use TopDeck Swiss Pods approximation: order adjacent players by W/D/L record, randomize exact-record ties, then apply repeat-avoidance swaps when enabled.
- Pairing formation must not use OMW, Elo, tiebreak seed, standings rank, or player id.
- Swiss seating is randomized per simulation unless TopDeck has already posted the table.
- Repeat-opponent avoidance runs only when the generated Swiss round has 32 or fewer tables/pods.
- Standings and top cut qualification may use points, OMW, tiebreak seed, and deterministic fallback ordering.
- Top cut brackets are seeded.
- Top 16, Top 10, and Top 4 must use exact probability propagation.
- Displayed leaderboards use TopDeck Elo; prediction and simulation calculations use hidden/internal Elo.

## Baseline Comparison

Compare every candidate model against the current production/reference model on the same tournament set, seed policy, simulation count, workers, and repeat-avoidance threshold.

Example:

```bash
PYTHONPATH=packages/backend/src python3 packages/backend/src/backtest_tournament_sim_models.py \
  --model v4-hybrid=packages/backend/models/pod-outcome/v4/pod_outcome_model_artifact_v4_draw_elo_hybrid.pkl \
  --model candidate=packages/backend/reports/draw-model/<candidate>/cedh_draw_model_artifact_<candidate>.pkl \
  --simulations 500 \
  --workers 4 \
  --limit 20 \
  --candidate-scan-limit 100 \
  --min-active-player-count 100 \
  --repeat-avoidance-max-pods 32 \
  --output packages/backend/reports/tournament-sim-backtests/v4_hybrid_vs_candidate.json \
  > packages/backend/reports/tournament-sim-backtests/v4_hybrid_vs_candidate.summary.json
```

If the run is interrupted, resume it with the same arguments plus `--resume`.

## Metrics To Review

- Brier score for top cut, Top 16, Top 4, and winner probabilities.
- Log loss for pod winner probabilities where actual pod results are known.
- Calibration curves: predictions near 10%, 25%, 50%, 75%, and 90% should occur at roughly those rates.
- Favorite bias: high hidden-Elo players should not systematically overperform or underperform predicted top cut and win rates.
- Seat calibration: seat-adjusted decisive win probabilities should match actual outcomes by seat and Elo bucket.
- Draw calibration: predicted draw buckets should match actual draw frequency.
- Point-line calibration: simulated top cut and bye point lines should match actual lines across completed events.

## Sensitivity Checks

Run targeted sweeps before trusting a surprising player-level result:

- Reference model vs candidate model.
- 10k vs 100k simulations for the same event.
- Multiple random seeds.
- Repeat avoidance enabled at 32 vs disabled.
- Seat adjustment enabled vs seat-averaged diagnostic mode, when available.
- Live stream output vs non-stream script output with cache disabled.

For a single high-impact player estimate, such as a projected 18-20% tournament win rate, the estimate is only credible if it remains stable across these checks or if the movement is explainable by a known modeling change.

## Acceptance Bar

A candidate model should not replace the reference model unless it improves or matches the reference on aggregate calibration and does not introduce a clear regression in:

- top cut calibration,
- winner calibration,
- favorite bias,
- point-line calibration,
- live/script parity,
- tournament simulation invariants.

If aggregate metrics improve but one of these areas regresses, document the tradeoff in the backtest report before using the model on the live page.
