# Tournament Prep Update

Last reviewed: 2026-04-06

## Summary

This update changes the tournament prep page from separate Elo and commander-profile tables into one attendee-focused workflow. The page now accepts a TopDeck tournament link or slug, fetches event standings through the TopDeck API when `TOPDECK_API_KEY` is available, and combines that data with Supabase commander history and regional Elo.

Main user-facing changes:

- A single attendee table replaces the separate `Top Elo Attendees` and `Player Commander Profiles` tables.
- The table supports local search, client-side pagination, and sorting by visible columns.
- Before a tournament starts, the table forecasts deck choice with `Most Likely To Bring` and `Alternatives`.
- After a tournament starts, the table shows standing and tournament record.
- After a tournament starts and TopDeck returns non-empty `rounds`, the table switches from forecasted decks to actual submitted decklists.
- Field-share cards use expected player-weighted commander share before results, and actual submitted deck share once results are available.
- Player names link to the internal regional Elo profile.
- Commander/decklist links prefer TopDeck deck pages, using `https://topdeck.gg/deck/{tournament_slug}/{player_topdeck_id}`.
- Tournament analysis is cached with `unstable_cache` for 15 minutes to avoid redoing expensive TopDeck and Supabase work on every render.

The old Midseason page and its navigation links were removed as part of this branch.

## Data Sources

Tournament prep uses three main sources:

- TopDeck tournament API: event metadata, start time, standings, points, rounds, and submitted deck data when available.
- `tournament_entries`: historical player commander usage, tournament dates, and TopDeck tournament slugs for decklist links.
- `regional_elo_leaderboard`: attendee global Elo rating.

The TopDeck API response does not explicitly identify league events. The page infers behavior from available data:

- `startDate` controls whether the tournament has started.
- Non-empty `rounds` controls whether actual result/decklist mode is available.
- Empty `rounds` after the start date keeps forecasted deck columns, but still shows standing and tournament record.

## Commander Forecast Algorithm

The deck-choice forecast is per player. It does not forecast the global metagame directly; field share is derived by combining each player's local commander probabilities.

For each attendee:

1. Use prior commander entries before the forecast reference date.
2. Use a primary 6-month lookback window.
3. If the player has fewer than 2 known commander entries in that primary window, include that player's older 6-to-12-month history as fallback.
4. If the player has no known commander in the last 12 months, use only their last known commander before that window.
5. Group entries by normalized commander name.
6. Score each entry by recency only:

```text
score += 0.5 ** (ageDays / 15)
```

7. Sort commanders by:

```text
predictionScore desc
entries desc
latestDate desc
commander name asc
```

8. Display the highest-scoring commander as `Most Likely To Bring`.
9. Display the next two commanders as `Alternatives`. A player with only the last-known fallback has no alternatives.
10. Convert per-player scores into displayed confidence:

```text
predictionShare = commanderScore / sum(playerCommanderScores)
```

Important details:

- The model no longer uses tournament-size weighting.
- The model no longer uses performance weighting from wins, draws, or losses.
- For tournaments that have already started, the lookback window is anchored to the tournament start date and excludes entries from that date onward.
- For tournaments that have not started, the lookback window is anchored to the current date.

## Why This Algorithm Was Chosen

The branch tested multiple deck-choice predictors against historical `tournament_entries`. Each test treated a historical entry as the target event, predicted from that player's prior entries before the event, and compared the prediction to the commander actually chosen.

Key results from the backtest:

| Model | Predictable entries | Top-1 | Top-3 |
| --- | ---: | ---: | ---: |
| Last commander, 12-month or any prior fallback | 37,171 | 61.69% | n/a |
| 6-month lookback, sparse 12-month fallback, 7-day half-life | 37,171 | 61.60% | 68.82% |
| Current chosen model: 6-month lookback, sparse 12-month fallback, 15-day half-life | 37,171 | 61.08% | 68.86% |
| Last commander, 3-month lookback | 33,274 | 63.38% | n/a |
| Count-only 6-month lookback with sparse 12-month fallback | 37,171 | 56.78% | 68.37% |

The last-commander baseline had the best top-1 accuracy among full-coverage variants, but it cannot provide meaningful alternatives. The chosen model uses a 15-day half-life because it keeps stronger top-3 performance while preserving alternatives and confidence shares.

Tournament-size and performance modifiers were tested and did not improve the result enough to justify the added complexity. The final model is intentionally close to "strongly prefer the most recently played commander," with enough frequency aggregation to handle players who repeat a deck several times.

## Region Display

The attendee table's region is not a state-specific Elo field. It uses the same predicted profile region model as
the regional Elo player profile, while Elo values come from the global `ALL` leaderboard.

## Performance Notes

The page uses `unstable_cache` with a 15-minute revalidation window:

```text
tournament-likelihood-analysis-v21
```

The version suffix is a manual cache-busting namespace. It is bumped when the returned analysis shape or forecast scoring changes, so old cached results do not mask algorithm updates.

The branch also reduced payload size by avoiding raw decklist text in the main tournament-prep data path. TopDeck standings are normalized to the actual commander name and TopDeck deck URL before being passed to the UI.
