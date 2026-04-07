# PR 48 Summary

## Summary

This PR shifts Regional Elo from state-scoped ratings to a global all-games leaderboard, then layers profile-region views on top of that global rating set. It also expands the regional player drilldown and updates Tournament Prep to use the same player-region and commander-forecasting logic.

- Replaces state Elo computation with a global `ALL` Elo pipeline, including paged month-by-month reads and a cleanup step before upserting `regional_elo_ratings`.
- Updates Regional Elo UI to load the global leaderboard, derive state/region views from predicted player profile regions, and paginate the leaderboard client-side.
- Adds player profile-region prediction from tournament state/city history and uses it across Regional Elo, player drilldowns, and Tournament Prep attendee rows.
- Expands player drilldown pages with global Elo rank, profile-region rank, TopDeck rank, active commander, played-commanders summary, regional game summary, paginated opponent records, and paginated game logs.
- Revises Tournament Prep commander forecasting to use a 6-month primary window, sparse-history fallback to 12 months, last-known fallback when needed, and recency-only scoring with a 15-day half-life.
- Anchors Tournament Prep lookbacks to tournament start time for started events, excludes same-day/later history, and switches between forecasted decks and actual submitted decklists when TopDeck rounds/results are available.
- Combines Tournament Prep attendee data into a sortable/searchable table with global Elo, predicted region, most-likely deck, alternatives, records, and decklist links.
- Removes the old Midseason Invitational page and related home/test navigation references.
- Improves TopDeck tournament normalization by stripping raw decklist payloads from standings after extracting commander names and TopDeck deck URLs.
- Adds backfill inputs/manifests for missing TopDeck historical tournament IDs and batches `--tids-file` ingestion requests with a configurable `--tids-batch-size`.
- Updates CI/backend validation scripts to check the global `ALL` Elo aggregate instead of state rows.
- Adds documentation for the Tournament Prep workflow, data sources, forecast algorithm, backtest rationale, and cache behavior.

## Testing / Validation

- Updated focused Regional Elo player page test coverage for the global leaderboard/profile-region behavior.
- Updated E2E home-page expectations after removing the Midseason page link.
- CI validation now samples global `ALL` Elo rows and compares them to canonical player stats.
