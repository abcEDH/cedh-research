# PR 48 Summary

## Summary

This PR shifts Regional Elo from state-scoped ratings to a global all-games leaderboard, then layers precomputed assigned-state views on top of that global rating set. It also expands the regional player drilldown, updates Tournament Prep to use the same player-region and commander-forecasting logic, and moves expensive leaderboard derivation out of request-time rendering.

- Replaces state Elo computation with a global `ALL` Elo pipeline, including paged month-by-month reads and a cleanup step before upserting `regional_elo_ratings`.
- Adds backend computation for assigned-state activity and per-game Elo event rows, populating `regional_elo_state_activity` and `regional_elo_game_events` alongside global ratings.
- Updates Regional Elo UI to query precomputed `regional_elo_regions` and `regional_elo_leaderboard` rows instead of scanning all tournament entries and deriving state/region views during page render.
- Uses global Elo for ranking while using assigned-state activity to determine each player's primary region and regional leaderboard placement.
- Expands player drilldown pages with global Elo rank, assigned-state rank, TopDeck rank, active commander, played-commanders summary, regional game summary, paginated opponent records, and paginated game logs.
- Updates player drilldowns to read precomputed primary-region and regional-rank data instead of loading the full global leaderboard to compute one player's state rank.
- Revises Tournament Prep commander forecasting to use a 6-month primary window, sparse-history fallback to 12 months, last-known fallback when needed, and recency-only scoring with a 15-day half-life.
- Anchors Tournament Prep lookbacks to tournament start time for started events, excludes same-day/later history, and switches between forecasted decks and actual submitted decklists when TopDeck rounds/results are available.
- Combines Tournament Prep attendee data into a sortable/searchable table with global Elo, assigned region, most-likely deck, alternatives, records, and decklist links.
- Updates Tournament Prep to read player regions from precomputed Regional Elo leaderboard rows instead of recomputing predicted regions from tournament history.
- Removes the old Midseason Invitational page and related home/test navigation references.
- Improves TopDeck tournament normalization by stripping raw decklist payloads from standings after extracting commander names and TopDeck deck URLs.
- Adds backfill inputs/manifests for missing TopDeck historical tournament IDs and batches `--tids-file` ingestion requests with a configurable `--tids-batch-size`.
- Updates the weekly backend workflow so the scheduled recompute step explicitly covers global Elo, assigned-state activity, and per-game Elo event data.
- Removes the forced `--min-players 32` floor from the weekly `ingest.py --days 7` job.
- Updates CI/backend validation scripts to check the global `ALL` Elo aggregate instead of state rows and to validate the new Regional Elo tables/views.
- Adds documentation for the Tournament Prep workflow, data sources, forecast algorithm, backtest rationale, and cache behavior.

## Testing / Validation

- Updated focused Regional Elo player page test coverage for the global leaderboard/assigned-state behavior.
- Updated E2E home-page expectations after removing the Midseason page link.
- CI validation now samples global `ALL` Elo rows and compares them to canonical player stats.
- Backend workflow validation now checks `regional_elo_regions`, `regional_elo_game_event_log`, `regional_elo_state_activity`, and `regional_elo_game_events`.
- Verified the performance changes with targeted eslint, focused Regional Elo tests, Python compile for `regional_elo.py`, and `git diff --check`.
