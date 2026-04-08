# PR 48 Summary

## Summary

This PR shifts Global Elo from state-scoped ratings to a global all-games leaderboard, then layers precomputed assigned-state and country-filtered views on top of that global rating set. It also expands the player drilldown, updates Tournament Prep to use the same player-region and commander-forecasting logic, and moves expensive leaderboard derivation out of request-time rendering.

- Replaces state Elo computation with a global `ALL` Elo pipeline, including paged month-by-month reads, compatibility fallback to legacy source views, and a cleanup step before upserting `global_elo_ratings`.
- Adds backend computation for assigned-state activity and per-game Elo event rows, populating `global_elo_state_activity` and `global_elo_game_events` alongside global ratings.
- Adds backend computation for `global_elo_active_leaderboard` and `global_elo_player_profile_summaries` so active leaderboard ranks, home region, and state-assignment summaries can be read directly instead of recomputed during page renders.
- Adds weekly precomputation for compact per-player commander profiles in `player_commander_profiles`, with UI fallbacks for deployments where the migration has not been applied yet.
- Updates Global Elo UI to query precomputed `global_elo_regions` and `global_elo_leaderboard` rows instead of scanning all tournament entries and deriving state/region views during page render, with legacy `regional_elo_*` fallbacks until the new aliases are deployed.
- Updates Global Elo UI to prefer `global_elo_active_leaderboard` rows for six-month-active leaderboard views, with fallbacks to the existing leaderboard views until the new migration is deployed.
- Hides players who have not played a game in the last six months from leaderboard views and recalculates displayed ranks over only the visible active players.
- Uses global Elo for ranking and displayed leaderboard game counts while using assigned-state activity to determine each player's primary region and region-filtered leaderboard placement.
- Includes tournaments without state metadata in the global Elo source data and player profile totals, with those games grouped as `UNKNOWN` in state assignment.
- Adds country-level Global Elo rows and updates the filter flow so the View dropdown lists `GLOBAL` plus countries, then only shows states belonging to the selected country.
- Expands player drilldown pages with merged TopDeck rank/points, TopDeck profile record totals, global/state ranks, stored Elo, home region, active commander, played-commanders summary, state assignment, and paginated opponent records.
- Updates player drilldowns to show inactive global/state ranks as `--`, link active global rank to the global leaderboard, and link active home-region/state-rank cards to the matching state leaderboard.
- Updates player drilldowns to read precomputed active ranks, home region, and state-assignment summaries when available instead of loading/scanning leaderboard rows during page render.
- Updates player drilldowns so Played Commanders links known commander names to the latest decklist for that commander and links the Last Played tournament/date to the TopDeck tournament bracket, while leaving unknown commanders unlinked.
- Removes the player profile games table, renames `Counted Games` to `Games Played`, and simplifies unknown region labels to `UNKNOWN`.
- Revises Tournament Prep commander forecasting to use a 6-month primary window, sparse-history fallback to 12 months, last-known fallback when needed, and recency-only scoring with a 15-day half-life.
- Anchors Tournament Prep lookbacks to tournament start time for started events, excludes same-day/later history, and switches between forecasted decks and actual submitted decklists when TopDeck rounds/results are available.
- Combines Tournament Prep attendee data into a sortable/searchable table with global Elo, assigned region, most-likely deck, alternatives, records, and decklist links.
- Updates Tournament Prep to read player regions from precomputed Global Elo leaderboard rows instead of recomputing predicted regions from tournament history.
- Updates Tournament Prep to use precomputed commander profiles for not-yet-started events, falling back to raw commander history when profiles are unavailable.
- Updates Tournament Prep to use the latest stored player name consistently across profiles, leaderboards, and prep tables.
- Links the Tournament Prep snapshot tournament name to the corresponding TopDeck bracket and fixes raw-slug parsing for inputs like `cardart-weekly-44`.
- Removes the old Midseason Invitational page and related home/test navigation references, and stays compatible with `main`'s retired surface cleanup for cards, survival, and turn-order pages.
- Improves TopDeck tournament normalization by stripping raw decklist payloads from standings after extracting commander names and TopDeck deck URLs.
- Improves TopDeck draw normalization by recognizing `_DRAW_` winner IDs from older events.
- Adds backfill inputs/manifests for missing TopDeck historical tournament IDs and batches `--tids-file` ingestion requests with a configurable `--tids-batch-size`.
- Updates the weekly backend workflow so the scheduled recompute step explicitly covers global Elo, assigned-state activity, active leaderboard rows, player profile summaries, commander profiles, and per-game Elo event data.
- Adopts `main`'s split backend/frontend CI workflow structure and keeps the Global Elo backend smoke command (`regional_elo.py --smoke-days 30 --dry-run`) working for pull request checks.
- Removes the forced `--min-players 32` floor from the weekly `ingest.py --days 7` job.
- Updates CI/backend validation scripts to check the global `ALL` Elo aggregate instead of state rows and to validate the new Global Elo tables/views.
- Adds documentation for the Tournament Prep workflow, data sources, forecast algorithm, backtest rationale, and cache behavior.

## Testing / Validation

- Updated focused Global Elo player page test coverage for global leaderboard/assigned-state behavior, inactive-rank hiding, and unknown-region player profile handling.
- Updated E2E home-page expectations after removing the Midseason page link and after merging `main`'s retired-surface navigation changes.
- CI validation now samples global `ALL` Elo rows and compares them to canonical player stats.
- Backend workflow validation now checks `global_elo_regions`, `global_elo_game_event_log`, `global_elo_state_activity`, `global_elo_game_events`, `global_elo_active_leaderboard`, and `global_elo_player_profile_summaries`.
- Verified the performance/conflict-resolution changes with targeted eslint, focused Global Elo tests, production web build, Python compile for `regional_elo.py`, backend CLI smoke help, and `git diff --check`.
