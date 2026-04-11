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

- `prior_games = 20`

Interpretation:

- small samples stay close to the player's baseline
- larger samples move the adjusted score closer to the observed matchup result

## Matchup Delta

Each matchup is compared to baseline using:

```text
delta = adjusted_score - baseline_score
```

- positive delta: better-than-baseline matchup
- negative delta: worse-than-baseline matchup

## Selection Rules

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
