# 0015 - Multi-Game Expansion on a Single Schema

## Status
Accepted

## Context
The project is expanding beyond cEDH into Riftbound, Gundam Card Game, and Yu-Gi-Oh retro
formats (Edison, Goat, …) — all served by the same TopDeck.gg v2 API and the same
structured `deckObj` decklist payload. The existing schema was implicitly single-tenant:
`tournaments.game`/`format` existed but were never written (all rows rode the
`'Magic: The Gathering'`/`'EDH'` column defaults), `commanders.name` was globally unique,
ingestion hardcoded the cEDH search payload, scoring (5/1/0), and the ≤34-player top-cut
heuristic, and every read model aggregated over all rows assuming they were cEDH.

## Decision

**One Supabase project, one schema, `(game, format)` discriminator columns — no parallel
per-game tables and no second database.**

1. **Ingestion writes `tournaments.game` and `tournaments.format` explicitly.** Configs
   with a pinned TopDeck format (cEDH → `EDH`) persist their canonical format; game-wide
   configs (`topdeck_format = None`) persist the tournament payload's own `format` string
   so real format names surface from the data itself (see Appendix).
2. **`commanders` becomes the game-scoped deck-identity table.** It keeps its physical
   name (renaming would ripple through every commander-centric view and the tedh.gg
   frontend) but gains `game` and `identity_kind`
   (`commander | legend | leader | archetype | unknown`), and `UNIQUE(name)` is replaced
   by `UNIQUE(game, name)`. MTG rows store the commander pair; Riftbound the Legend;
   Gundam the leader; Yu-Gi-Oh a derived archetype. All commander upserts use
   `on_conflict="game,name"` — the migration and code change land in the same commit.
3. **Legacy cEDH read models are pinned with explicit guards** (`WHERE t.game =
   'Magic: The Gathering' AND t.format = 'EDH'`), not protected by convention. The Elo
   pipeline reads through the single choke-point view `regional_elo_game_results`, so one
   guarded view protects all Elo surfaces. These guards must be applied before the first
   non-cEDH ingestion run.
4. **A Python game registry (`src/game_registry.py`) is the single source of per-game
   behavior**: TopDeck search strings, pod size, scoring, win/draw points, whether W/D may
   be derived from standings points (cEDH 5/1/0 only; losses are never derived — known
   issue #4), the small-event top-cut override, and the identity kind. The registry is
   pure data; identity-extraction behavior is dispatched by `GameConfig.key` from the
   deck-identity module so the registry never imports ingestion code.
5. **`tournament_entries.decklist_obj` (TopDeck `deckObj`) is persisted as the structured
   system of record** for decklists (extends ADR 0003/0005), enabling identity re-derivation
   and card-level analytics for non-MTG games without re-ingesting.
6. **Elo remains cEDH-only** (ADR 0008). Game-scoped Elo would require a `game` column on
   the Elo state tables and a parameterized `regional_elo_game_results`; recorded here as
   future work.

**Rejected alternatives**
- *Parallel tables per game* — duplicates the entire ingestion pipeline and forces either
  nullable FKs or fake identity rows (`tournament_entries.commander_id` is NOT NULL).
- *Separate Supabase projects per game* — splits the shared `players` graph (TopDeck IDs
  are cross-game), doubles ops cost, and buys no isolation the view guards don't.

## Consequences

**Easier**
- New games are a registry entry plus (if needed) an identity extractor — no schema work.
- The tedh.gg surface is provably isolated: its read models filter on game/format rather
  than assuming a single-tenant table.
- Cross-game player analytics stay possible (single `players` table keyed by TopDeck ID).

**Harder**
- Every future cEDH read model must remember the game/format guard (a migration-integrity
  test asserts the guards on the known views).
- `commanders` is now a slightly misleading physical name for non-MTG identities.

### Cross-Repo Impact
`cedh-research` only.

## Appendix: TopDeck game/format discovery

Live API probing was not possible from the implementation environment (egress to
topdeck.gg blocked), so:

- **Game strings** (verified against the documented `Game` enum in
  `packages/backend/openapi.yaml`, case-sensitive): `"Magic: The Gathering"`,
  `"Riftbound"`, `"Gundam TCG"`, `"Yu-Gi-Oh"`.
- **Format strings** for non-MTG games are not enumerated by the API docs and remain
  **unverified**. Riftbound and Gundam configs therefore search game-wide
  (`topdeck_format = None`, no client-side format filter) and persist each payload's own
  `format` string; Yu-Gi-Oh retro configs search game-wide and filter client-side via
  case-insensitive `format_aliases` (e.g. `("Edison", "Edison Format")`). After the first
  scheduled runs, `SELECT DISTINCT format FROM tournaments WHERE game = …` yields the
  exact strings; pin them in `game_registry.py` (and the frontend registry) then.
- **`deckObj` shape** (from `openapi.yaml`):
  `{Commanders|Mainboard|Sideboard: {<card name>: {id: <uuid>, count: <int>}}}` — present
  on `standings[]` and `tables[].players[]`; `id` is the game's card identifier (Scryfall
  ID for MTG).
- **`Table.table`** may be the string `"Byes"` instead of an integer — 1v1 Swiss makes
  this live; ingestion skips bye tables.

## Sources
- `docs/decisions/0003-supabase-as-system-of-record.md`
- `docs/decisions/0005-read-model-pattern.md`
- `docs/decisions/0008-manual-only-elo-maintenance.md`
- `packages/backend/openapi.yaml`
- `packages/backend/supabase/migrations/20260706000000_multigame_deck_identities.sql`
- `packages/backend/src/game_registry.py`
