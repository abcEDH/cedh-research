# Simulation Elo and seat adjustments

Swiss and top-cut winner probabilities use internal Elo model `2026-09-18-quarterly-v1`, published by PR #363. Displayed TopDeck Elo is separate from this calculation.

The simulation parameters live in `packages/backend/src/internal_elo.py`:

| Seat | Swiss Elo offset | Top-cut Elo offset |
|---|---:|---:|
| 1 | 0 | 0 |
| 2 | -48.820457256958306 | -117.5921368942531 |
| 3 | -97.04491395828074 | -172.63550764675733 |
| 4 | -144.80626927577129 | -227.7663864826161 |

For a decisive pod, each player's weight is `2 ** ((internal Elo + seat offset) / 200)`. Normalize weights across the pod. Explicit top-cut round labels or a round index beyond Swiss select top-cut offsets; the actual seat map selects the offset. Apply offsets only when a four-player pod has all four distinct seats, matching the published rating model. Three-player pods and incomplete seat maps use unadjusted internal Elo.

The same helper supplies single-pod and batch predictions, draw-model probability features, and exact top-cut propagation. Optional candidate-winner features use the corresponding stage offsets too. The default draw-model artifact remains unchanged; it now receives features derived from the current Swiss Elo adjustments.

Completed Swiss rounds replayed by the ongoing-tournament runner use the published learning rates: 64.20106085407248 for decisive games and 21.14298097296857 for draws. Its top-cut replay helper uses 39.67175522623664 for decisive games and retains the existing seat-one fallback for drawn top-cut pods. League replay applies the published league multiplier. Future simulated games retain the engine's existing fixed-rating behavior.

Prepared live-state cache keys include a fingerprint of the shared model version, base, divisor, both seat-offset maps, all replay learning rates, and the league multiplier. Changing any of these values automatically invalidates old cached states; a manual cache-version bump is not required. The web streaming route and CLI share this runner and the same stage-aware prediction functions.

This updates simulation inputs and replay calculations; publishing or rebuilding stored Elo tables is a separate maintenance operation.

## Updating model weights

Edit `internal_elo.py` only. The global rebuild, all-games recompute, simulator, and ongoing-event replay read its parameters. The shared `rating_equity` and `seat_offsets` helpers prevent inference and rating maintenance from keeping separate numeric copies. Compatibility aliases remain for older analysis callers, but active calculations use the shared module.

`test_internal_elo_shared.py` changes Swiss/top-cut offsets, learning rates, base, and divisor in memory and checks rating-event expectations, recomputed ratings, simulator predictions, replayed ratings, and cache invalidation. These tests run in the existing backend unit-test job.

Parameter changes take effect when the updated code runs. Publishing revised historical ratings still uses the normal manual maintenance process. A source-code change does not itself deploy the app or rewrite stored ratings.
