# 0018 — All completed events contribute to internal Elo

## Status

Accepted

## Context

The canonical rebuild previously used the restricted `ranking` tier. This excluded small tournaments and leagues from prediction inputs even when their completed game results were available. Jae's history illustrated the gap: 161 games contributed to Elo while another 159 stored games from small events and leagues were excluded.

The user explicitly requested including all events for all players, so players and their opponents are rated against the same dataset.

## Decision

- Canonical internal Elo uses the `all` tier: every completed, scoreable game from a tournament that has already started, including small events and leagues.
- Preserve the current rating formula and chronological replay order. Apply the same inclusion rule to every player.
- Keep the future-date protections from ADR 0017. Pending or active games, byes, and incomplete pods without a scoreable result do not generate Elo changes.
- The canonical rebuild defaults to `--tier all`; `--apply` rejects restricted tiers. Ranking/local tiers remain available for offline comparisons.
- Rebuild existing history before publishing the new dataset. Check completeness by game and player IDs, not just dates.
- Displayed TopDeck Elo remains sourced from TopDeck. This decision changes internal model inputs, not imported TopDeck ratings.

## Consequences

Internal Elo uses more of the available evidence. Ratings can move substantially when previously excluded results and opponent histories are added. Restricting or weighting leagues differently would be a separate, evaluated model change.

### Cross-Repo Impact

`cedh-research` only: canonical rebuild defaults, Elo input views, maintenance queries, and methodology documentation.

## Sources

- User instruction on September 15, 2026: include all completed events for all players.
- [0017 — Exclude future games from Elo](0017-exclude-future-elo-games.md).
- Migration `20260915010000_all_completed_events_for_internal_elo.sql`.
