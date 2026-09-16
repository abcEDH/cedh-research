# 0019 — Preserve verified game identity corrections

## Status

Accepted

## Context

TopDeck internal pod indexes and displayed table numbers can identify the same
game differently. A game key containing the table number accepts both as distinct
rows. Removing a copy alone allows a later import to recreate it. A global unique
constraint on participant sets would incorrectly collapse legitimate league
rematches.

## Decision

Store administrator-verified obsolete keys in `superseded_game_keys`, with a
reference to the retained canonical game and a reason. Restrict registry access
to the service role. After canonical key construction, a database trigger skips
inserts and updates targeting these obsolete identities, including upserts.

Populate this registry only from a source-reviewed correction manifest. Back up
removed data and rebuild internal Elo chronologically with the corrected input.
Treat conflicting outcomes and overlapping separate event IDs as separate review
cases; neither participant overlap nor repeated league pairings proves duplication.

## Consequences

Verified removed copies cannot reappear through another ingestion client.
Canonical games and legitimate rematches remain available. Importers must accept
an empty result for a suppressed write, as the current ingestion paths already do.
An authoritative later correction that reuses a retired identity requires an
administrator to review and amend its registry entry. This registry guards known
corrections; it does not discover every possible duplicate.

### Cross-Repo Impact

`cedh-research` only; the database trigger applies to all ingestion clients.

## Sources

- [PR #354](https://github.com/abcEDH/cedh-research/pull/354)
- [Data model](../methodology/data-model.md)
- Migration `20260915020000_block_superseded_game_reimports.sql`
