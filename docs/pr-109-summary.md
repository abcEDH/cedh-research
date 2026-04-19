# PR 109 Summary

## Summary

This PR switches the project Elo learning rate to `K=48`, refreshes the Supabase-derived Elo tables with that value, and changes user-facing Elo displays to use the published TopDeck Elo snapshot where available. The app-computed Elo remains available on player profiles as Hidden Elo.

Follow-up changes in this PR also make TopDeck Elo the sort source wherever the UI is sorting by Elo, and keep Tournament Prep Elo reads fresh instead of serving cached Elo rows.

Changed files in PR 109:

- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/methodology/elo/page.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/page.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx)
- [regional-leaderboard-table.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/regional-leaderboard-table.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/tournament-likelihood/page.tsx)
- [tournament-analysis-tables.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/tournament-likelihood/tournament-analysis-tables.tsx)
- [topdeck-elo.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck-elo.ts)
- [cedh-skill-rating.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/methodology/cedh-skill-rating.md)
- [rebuild_global_elo_tables.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_global_elo_tables.py)
- [recompute_global_elo_all_games.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/recompute_global_elo_all_games.py)
- [regional_elo.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/regional_elo.py)
- [pr-109-summary.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/pr-109-summary.md)

## K Factor Validation

- Tested broad Elo learning-rate candidates from `K=20` through `K=70` in steps of `5`.
- Broad sweep input:
  - `994,649` participant result rows
  - `257,063` grouped games
  - `255,813` valid games
  - `992,250` prediction observations
- Broad sweep best by mean squared error was `K=50`:
  - MSE: `0.141023046`
  - RMSE: `0.375530353`
  - MAE: `0.293288251`
  - log loss: `1.278595434`
- Existing `K=30` produced MSE `0.141298628`, which was `0.1954%` worse than `K=50`.
- Tight sweep around the broad winner selected `K=48` by lowest MSE:
  - `K=48`: MSE `0.141021630`, RMSE `0.375528468`, MAE `0.293291353`, log loss `1.278943173`
  - `K=49`: MSE `0.141021740`
  - `K=50`: MSE `0.141023046`
- `K=50` was only `0.0010%` worse than `K=48`, but `K=48` was the best measured candidate and is now the configured value.

## Calibration And Sanity Checks

Calibration for `K=48`:

- 0-10% bucket: average expected `8.37%`, actual `7.26%`
- 10-20% bucket: average expected `16.31%`, actual `14.69%`
- 20-30% bucket: average expected `24.66%`, actual `24.06%`
- 30-40% bucket: average expected `33.99%`, actual `36.46%`
- 40-50% bucket: average expected `44.13%`, actual `48.26%`
- 50%+ bucket: average expected `56.33%`, actual `59.48%`

Leaderboard sanity snapshot:

| K | Top 1 | Top 10 Min | Top 100 Min | SD | >=1900 | Event p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 45 | 2177.9 | 2025.9 | 1895.0 | 56.0 | 95 | 66.74 |
| 48 | 2190.3 | 2036.1 | 1903.4 | 58.3 | 106 | 71.16 |
| 50 | 2198.2 | 2044.4 | 1909.2 | 59.9 | 115 | 74.11 |
| 55 | 2216.4 | 2062.9 | 1919.1 | 63.7 | 135 | 81.43 |
| 58 | 2226.5 | 2072.8 | 1925.6 | 66.0 | 150 | 85.81 |

## Backend Elo

- Updates `K_FACTOR` from `30` to `48` in the backend Elo calculation scripts.
- Updates the Elo methodology page and methodology doc to document `K=48`.
- Keeps the historical PR 105 summary at its original `K=30` description, since that document describes the older PR state.

## Supabase Refresh

Rebuilt the derived Supabase Elo tables with:

```bash
python3 packages/backend/src/rebuild_global_elo_tables.py --apply
```

The rebuild processed:

- `994,649` participant result rows
- `84,149` ratings
- `52,029` state activity rows
- `992,250` game events
- `69,009` active leaderboard rows
- `84,149` player profile summaries

Updated tables:

- `global_elo_ratings`
- `global_elo_game_events`
- `global_elo_active_leaderboard`
- `global_elo_state_activity`
- `global_elo_player_profile_summaries`

Verified row counts after the rebuild:

- `global_elo_ratings`: `84,149`
- `global_elo_state_activity`: `52,029`
- `global_elo_game_events`: `992,250`
- `global_elo_active_leaderboard`: `69,009`
- global active leaderboard rows: `35,286`
- state/country leaderboard rows: `33,723`
- `global_elo_player_profile_summaries`: `84,149`

Top five app-computed ratings after the rebuild:

1. Alexander Bye: `2190.325`
2. Jase Sanders: `2110.168`
3. Tino "Strike It Rich" Kornitzsky // CriticalEDH: `2093.683`
4. Adam Drouillard: `2086.438`
5. [AP9] A!an: `2058.673`

## TopDeck Elo Source

- Adds [topdeck-elo.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck-elo.ts) to read published Elo values from the Supabase `topdeck_player_elos` table.
- Supports single-player and chunked multi-player lookups by TopDeck `uid`.
- Supports paged full-table reads for large leaderboard and rank sorts.
- Deduplicates requested IDs and chunks multi-player reads in batches of `250`.
- The table is expected to contain `name`, `profileImage`, `elo`, and `uid`.
- Confirmed the table is readable through the app's Supabase client with `9,704` available TopDeck Elo rows.

## Regional Leaderboard

- Renames visible leaderboard Elo copy from Global Elo to TopDeck Elo.
- Overlays each displayed leaderboard row with the matching TopDeck Elo value when available.
- Preserves the app-computed rating on the row as `hidden_rating`.
- Displays `-` for players without a published TopDeck Elo value.
- Sorts visible leaderboard pages by TopDeck Elo instead of the app-computed hidden Elo.
- Applies pagination after TopDeck Elo sorting so page order matches the displayed Elo values.
- Keeps country and state views tied to the local active player set while using TopDeck Elo as the displayed Elo number and sort key.
- Adds a faster TopDeck-sorted active leaderboard path for global and state views so normal leaderboard pages do not need to fully sort every active row in memory.

## Player Profiles

- Changes the main Elo stat card to TopDeck Elo.
- Adds a Hidden Elo stat card for the app-computed rating from the local Elo rebuild.
- Expands the profile stat grid to fit the additional Elo card.
- Shows `-` when no TopDeck Elo is available for the player.
- Recomputes displayed global, country, and state ranks from TopDeck Elo ordering instead of using the precomputed hidden-Elo rank.

## Tournament Prep

- Updates Tournament Prep Elo candidate rows to fetch TopDeck Elo values from Supabase.
- Stores the local app-computed rating as `hidden_rating`.
- Uses TopDeck Elo as the visible rating when available.
- Sorts available Elo rows by TopDeck Elo with missing TopDeck values last.
- Updates tournament analysis table labels and empty states from Global Elo or Best Elo to TopDeck Elo.
- Fetches Tournament Prep Elo rows outside the cached tournament analysis payload so updated `topdeck_player_elos` values are reflected on each request.
- Builds Tournament Prep Elo rows from every tournament attendee TopDeck ID, so players with a published TopDeck Elo can display even when they do not have a local hidden-Elo leaderboard row.
- Verified `the-quest-part-1` Tournament Prep page against Supabase `topdeck_player_elos` values:
  - Tino: displayed `2034`, Supabase `2033.6366158163835`
  - Evan Pierce: displayed `1954`, Supabase `1954.3983787363259`
  - Alex Lien: displayed `1899`, Supabase `1899.4242922873698`

## Validation

- Compared this document against the live GitHub diff for [PR 109](https://github.com/abcEDH/cedh-research/pull/109).
- Verified the web app with:

```bash
npm run lint --workspace apps/web
npm run build --workspace apps/web
```

- Lint passed with existing warnings only.
- Build passed.
- Local smoke checks:
  - `http://localhost:3000/regional-elo` returned `200` and displayed rows sorted by TopDeck Elo.
  - `http://localhost:3000/tournament-likelihood?tournament=https%3A%2F%2Ftopdeck.gg%2Fbracket%2Fthe-quest-part-1` returned `200` and displayed current TopDeck Elo values from Supabase.
- Verified backend syntax with:

```bash
python3 -m py_compile packages/backend/src/regional_elo.py packages/backend/src/rebuild_global_elo_tables.py packages/backend/src/recompute_global_elo_all_games.py
```
