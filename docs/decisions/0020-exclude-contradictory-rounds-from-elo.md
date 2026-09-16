# 0020 — Exclude contradictory non-league rounds from Elo

## Status

Accepted

## Context

TopDeck can contain repeated bracket pods and contradictory pairings. Stored
records can also associate same-name players with the wrong TopDeck identity.
Matching the source does not prove a game is logically valid: outside leagues,
one player cannot play at two tables in the same round.

## Decision

Derive `elo_conflicted_games` from completed, non-future raw games and exclude
all participants of both conflicting pods from regional/global Elo input views.
Use the tournament's explicit league classification to exempt league rematches.
Preserve unresolved raw evidence instead of selecting an arbitrary winner or
removing only the repeated player's result. Repair source-verifiable identities,
rosters, and table numbers; retire only obsolete keys that are not reused by a
valid game. Back up corrections and replay Elo chronologically.

## Consequences

New contradictions are excluded immediately from model inputs. Previously
published ratings still require manual maintenance to reflect any source change,
consistent with ADRs 0007 and 0008. The dynamic guard adds a database aggregation
to Elo source reads (about five seconds for the current full dataset). Public
rating pages continue to read persisted rating tables. League classification must
be accurate; a false non-league flag can suppress valid league games.

### Cross-Repo Impact

`cedh-research` only; no frontend contract changes.

## Sources

- [Verified game identity corrections](0019-superseded-game-identities.md)
- [Data model](../methodology/data-model.md)
- Migration `20260915030000_exclude_nonleague_round_conflicts.sql`
