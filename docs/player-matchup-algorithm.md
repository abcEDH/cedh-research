# Player Matchup Algorithm

This documents how the player profile page selects `Best Matchups` and `Worst Matchups` for opponents and commanders.

## Inputs

- Source data: per-game player logs already loaded for the profile page.
- Opponent matchups:
  - one record per opposing seat
  - uses the player's game result against that opposing player
  - if the same opponent has no TopDeck ID, the fallback key is `gameId + playerName + seat`
- Commander matchups:
  - one record per opposing commander per game
  - duplicate commander seats in the same game are deduped
  - empty commander names and `Unknown Commander` are normalized to `Unknown`

## Baseline Score

The player's baseline score is:

```text
(wins + 0.2 * draws) / total_games
```

This is the expected neutral reference point for all matchup comparisons.

## Matchup Score

For each opponent or commander matchup:

```text
raw_matchup_score = (wins + 0.2 * draws) / matchup_games
```

The UI does not rank on this raw value directly because small samples are noisy.

## Adjusted Score

Each matchup score is shrunk toward the player's baseline with a Bayesian-style prior:

```text
adjusted_score =
  (wins + 0.2 * draws + baseline_score * prior_games)
  / (matchup_games + prior_games)
```

Current constants:

- `opponent_prior_games = 60`
- `commander_prior_games = 100`

Interpretation:

- small samples stay close to the player's baseline
- larger samples move the adjusted score closer to the observed matchup result
- commander matchups use a stronger prior because commander labels are noisier and more sparse than opponent-player identities

## Matchup Delta

Each matchup is compared to baseline using:

```text
delta = adjusted_score - baseline_score
```

- positive delta: better-than-baseline matchup
- negative delta: worse-than-baseline matchup

## Selection Rules

- `Unknown` and `Unknown Player` records are not eligible to be selected as best or worst matchup cards.
- Unknown rows can still appear in the detailed matchup record tables.
- best matchup:
  - highest delta
  - tie-breaker: more games
- worst matchup:
  - lowest delta
  - tie-breaker: more games

If there are no matchup records at all, the profile shows no matchup insight.

There is currently no minimum-games requirement for a matchup to be selected.

## Practical Meaning

The displayed `adjusted score` is not raw win rate. It is the smoothed estimate of how favorable or unfavorable that matchup is after accounting for sample size.

## Prior Validation

The current priors were selected by walk-forward validation against the full Global Elo game-event log:

- validation rows: `992,250` participant result rows
- games: `246,256`
- scoring target:
  - win = `1`
  - draw = `0.2`
  - loss = `0`
- candidate priors tested:
  - `0`, `1`, `2`, `3`, `5`, `8`, `10`, `15`, `20`, `30`, `40`, `60`, `80`, `100`

For each game, only games earlier in time were used to build the player's baseline and matchup histories. The held-out game result was then compared to each prior's adjusted-score prediction. Histories were updated only after the held-out game was scored.

### Opponent Prior Results

Opponent matchups were evaluated over `1,072,034` held-out matchup predictions.

Best by mean squared error:

- `opponent_prior_games = 60`

Top tested priors:

| prior | MSE | RMSE | MAE |
|---:|---:|---:|---:|
| 60 | 0.155326 | 0.394114 | 0.304562 |
| 40 | 0.155330 | 0.394119 | 0.304388 |
| 80 | 0.155346 | 0.394139 | 0.304668 |
| 100 | 0.155366 | 0.394165 | 0.304738 |
| 30 | 0.155378 | 0.394180 | 0.304253 |
| 20 | 0.155570 | 0.394423 | 0.304068 |

### Commander Prior Results

Commander matchups were evaluated with `Unknown` commander labels excluded, because `Unknown` is missing metadata rather than a real commander matchup. This produced `621,073` held-out matchup predictions.

Best by mean squared error:

- `commander_prior_games = 100`

Top tested priors:

| prior | MSE | RMSE | MAE |
|---:|---:|---:|---:|
| 100 | 0.155061 | 0.393778 | 0.310586 |
| 80 | 0.155063 | 0.393780 | 0.310496 |
| 60 | 0.155076 | 0.393797 | 0.310364 |
| 40 | 0.155136 | 0.393873 | 0.310151 |
| 30 | 0.155229 | 0.393991 | 0.309992 |
| 20 | 0.155484 | 0.394315 | 0.309786 |

The tested range from `60` to `100` was close for commander matchups, but `100` had the lowest MSE and log loss.
