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
- `regional_elo_leaderboard`: attendee Elo rating and displayed region.

The TopDeck API response does not explicitly identify league events. The page infers behavior from available data:

- `startDate` controls whether the tournament has started.
- Non-empty `rounds` controls whether actual result/decklist mode is available.
- Empty `rounds` after the start date keeps forecasted deck columns, but still shows standing and tournament record.

## Commander Forecast Algorithm

The deck-choice forecast is per player. It does not forecast the global metagame directly; field share is derived by combining each player's local commander probabilities.

For each attendee:

1. Use prior commander entries before the forecast reference date.
2. Use a primary 6-month lookback window.
3. If the player has fewer than 2 known commander entries in that primary window, fetch only that player's older 6-to-12-month history as fallback.
4. Group entries by normalized commander name.
5. Score each entry by recency only:

```text
score += 0.5 ** (ageDays / 15)
```

6. Sort commanders by:

```text
predictionScore desc
entries desc
latestDate desc
commander name asc
```

7. Display the highest-scoring commander as `Most Likely To Bring`.
8. Display the next two commanders as `Alternatives`.
9. Convert per-player scores into displayed confidence:

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
| Current chosen model: 6-month lookback, sparse 12-month fallback, 15-day half-life | 15,576 | 66.80% | 72.53% |
| Previous model: 6-month lookback, sparse 12-month fallback, 45-day half-life, 0.25 floor | 15,576 | 65.67% | 72.52% |
| Hard 3-month lookback, 15-day half-life | 14,073 | 68.35% | 73.05% |
| Last-played commander, 6-month lookback | 15,479 | 66.98% | n/a |
| Last-played commander, 12-month lookback | 15,576 | 66.79% | n/a |

The hard 3-month model had the best accuracy when a prediction existed, but it dropped coverage by about 1,500 entries compared to the 6-month plus sparse fallback model. The chosen model keeps broader coverage while nearly matching the last-played baseline.

Tournament-size and performance modifiers were tested and did not improve the result enough to justify the added complexity. The final model is intentionally close to "strongly prefer the most recently played commander," with enough frequency aggregation to handle players who repeat a deck several times.

## Region Display

The attendee table's region is not a true home-region field. It is selected from `regional_elo_leaderboard`:

1. Query rows for the attendee's `topdeck_id`.
2. Consider `state` and `global` leaderboard rows.
3. Prefer any `state` row over the global `ALL` row.
4. If multiple state rows exist, use the lowest rank.
5. If rank ties, use the row with more games played.
6. Fall back to `ALL` only when no state row exists.

This means the displayed value is better understood as the player's best state Elo region, not where the player lives.

## Performance Notes

The page uses `unstable_cache` with a 15-minute revalidation window:

```text
tournament-likelihood-analysis-v18
```

The version suffix is a manual cache-busting namespace. It is bumped when the returned analysis shape or forecast scoring changes, so old cached results do not mask algorithm updates.

The branch also reduced payload size by avoiding raw decklist text in the main tournament-prep data path. TopDeck standings are normalized to the actual commander name and TopDeck deck URL before being passed to the UI.
