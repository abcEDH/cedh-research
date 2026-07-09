-- Multi-game expansion (ADR 0015): composite index for game/format-scoped reads.
--
-- tournaments.game and tournaments.format exist since the initial schema with cEDH
-- defaults, so every pre-expansion row is already correctly labelled; no backfill is
-- needed. Ingestion now writes both columns explicitly, and multi-game read models
-- filter on (game, format) ordered by recency.

CREATE INDEX IF NOT EXISTS idx_tournaments_game_format_date
    ON tournaments(game, format, start_date DESC);
