-- Multi-game expansion (ADR 0015): generalize commanders into game-scoped deck identities.
--
-- The commanders table keeps its physical name (renaming would ripple through every
-- commander-centric view and the tedh.gg frontend) but now stores one deck identity per
-- (game, name): the commander pair for MTG, the Legend for Riftbound, the leader for
-- Gundam, and a derived archetype for Yu-Gi-Oh retro formats.
--
-- Existing rows are all cEDH and keep working via the column defaults. The old global
-- UNIQUE(name) is replaced by UNIQUE(game, name) so identically named identities in
-- different games cannot collide. Code that upserts commanders switches to
-- on_conflict="game,name" in the same commit as this migration.

ALTER TABLE commanders
    ADD COLUMN IF NOT EXISTS game TEXT NOT NULL DEFAULT 'Magic: The Gathering',
    ADD COLUMN IF NOT EXISTS identity_kind TEXT NOT NULL DEFAULT 'commander';

ALTER TABLE commanders
    ADD CONSTRAINT commanders_identity_kind_check
    CHECK (identity_kind IN ('commander', 'legend', 'leader', 'archetype', 'unknown'));

ALTER TABLE commanders DROP CONSTRAINT IF EXISTS commanders_name_key;
ALTER TABLE commanders ADD CONSTRAINT commanders_game_name_key UNIQUE (game, name);

CREATE INDEX IF NOT EXISTS idx_commanders_game ON commanders(game);

COMMENT ON TABLE commanders IS
    'Per-game deck identities. MTG: the commander pair; Riftbound: the Legend; Gundam: the leader; Yu-Gi-Oh: a derived archetype.';
COMMENT ON COLUMN commanders.game IS
    'TopDeck game string this identity belongs to (matches tournaments.game).';
COMMENT ON COLUMN commanders.identity_kind IS
    'What kind of deck identity this row represents: commander | legend | leader | archetype | unknown.';
