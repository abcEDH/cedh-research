# ELO ranking tiers

Issue #288 defines three reusable datasets:

- `ranking`: at least 30 players, a dated completed event, and no league/casual markers.
- `local`: at least 10 players, a dated completed event, and no obvious casual markers; league games may qualify.
- `all`: every game with a date.

The migrations `20260726000000_elo_ranking_eligibility_tiers.sql` and
`20260727042641_ranking_game_level_eligibility.sql` append and refine
`ranking_eligible`, `local_eligible`, and `all_eligible` flags to
`global_elo_game_results` and exposes the `games_*_eligible` views for exports and
analysis. Ranking eligibility is game-level: every participant in an eligible game
is included, regardless of that entry's decklist presence.

To rebuild the persisted Elo tables for a tier, run a full rebuild with the service
environment loaded:

```bash
uv run python packages/backend/src/rebuild_global_elo_tables.py --tier ranking --apply
```

The rebuild defaults to `ranking`. `--tier local` and `--tier all` are available for
comparative snapshots. Tiered incremental rebuilds are intentionally rejected until
the pre-cutoff snapshot path is tier-aware.

There is no `league_games` table or explicit tournament-finalized column in the current
schema, so league detection is the documented conservative name/TID heuristic and
finalization is represented by completed game status plus a non-future tournament date.
