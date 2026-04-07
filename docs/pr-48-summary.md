# PR 48 Summary

## Summary

This PR shifts Global Elo from state-scoped ratings to a global all-games leaderboard, then layers precomputed assigned-state and country-filtered views on top of that global rating set. It also expands the player drilldown, updates Tournament Prep to use the same player-region and commander-forecasting logic, and moves expensive leaderboard derivation out of request-time rendering.

- Replaces state Elo computation with a global `ALL` Elo pipeline, including paged month-by-month reads and a cleanup step before upserting `regional_elo_ratings`.
- Adds backend computation for assigned-state activity and per-game Elo event rows, populating `regional_elo_state_activity` and `regional_elo_game_events` alongside global ratings.
- Adds weekly precomputation for compact per-player commander profiles in `player_commander_profiles`, with UI fallbacks for deployments where the migration has not been applied yet.
- Updates Global Elo UI to query precomputed `regional_elo_regions` and `regional_elo_leaderboard` rows instead of scanning all tournament entries and deriving state/region views during page render.
- Uses global Elo for ranking while using assigned-state activity to determine each player's primary region and region-filtered leaderboard placement.
- Adds country-level Global Elo rows and updates the filter flow to choose Global or Country, then only show states belonging to the selected country.
- Expands player drilldown pages with global Elo rank, assigned-state rank, TopDeck rank, active commander, played-commanders summary, region-filtered game summary, paginated opponent records, and paginated game logs.
- Updates player drilldowns to read precomputed primary-region and region-filtered rank data instead of loading the full global leaderboard to compute one player's state rank.
- Revises Tournament Prep commander forecasting to use a 6-month primary window, sparse-history fallback to 12 months, last-known fallback when needed, and recency-only scoring with a 15-day half-life.
- Anchors Tournament Prep lookbacks to tournament start time for started events, excludes same-day/later history, and switches between forecasted decks and actual submitted decklists when TopDeck rounds/results are available.
- Combines Tournament Prep attendee data into a sortable/searchable table with global Elo, assigned region, most-likely deck, alternatives, records, and decklist links.
- Updates Tournament Prep to read player regions from precomputed Global Elo leaderboard rows instead of recomputing predicted regions from tournament history.
- Updates Tournament Prep to use precomputed commander profiles for not-yet-started events, falling back to raw commander history when profiles are unavailable.
- Removes the old Midseason Invitational page and related home/test navigation references.
- Improves TopDeck tournament normalization by stripping raw decklist payloads from standings after extracting commander names and TopDeck deck URLs.
- Adds backfill inputs/manifests for missing TopDeck historical tournament IDs and batches `--tids-file` ingestion requests with a configurable `--tids-batch-size`.
- Updates the weekly backend workflow so the scheduled recompute step explicitly covers global Elo, assigned-state activity, and per-game Elo event data.
- Removes the forced `--min-players 32` floor from the weekly `ingest.py --days 7` job.
- Updates CI/backend validation scripts to check the global `ALL` Elo aggregate instead of state rows and to validate the new Global Elo tables/views.
- Adds documentation for the Tournament Prep workflow, data sources, forecast algorithm, backtest rationale, and cache behavior.

## Testing / Validation

- Updated focused Global Elo player page test coverage for the global leaderboard/assigned-state behavior.
- Updated E2E home-page expectations after removing the Midseason page link.
- CI validation now samples global `ALL` Elo rows and compares them to canonical player stats.
- Backend workflow validation now checks `regional_elo_regions`, `regional_elo_game_event_log`, `regional_elo_state_activity`, and `regional_elo_game_events`.
- Verified the performance changes with targeted eslint, focused Global Elo tests, Python compile for `regional_elo.py`, and `git diff --check`.
