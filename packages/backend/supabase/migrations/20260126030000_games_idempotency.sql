-- Migration: Make game ingestion idempotent via deterministic game_key

ALTER TABLE games
ADD COLUMN IF NOT EXISTS game_key TEXT;

UPDATE games
SET game_key = concat_ws(
    '|',
    tournament_id::text,
    COALESCE(round_number::text, 'RNULL'),
    COALESCE(round_name, 'RNNULL'),
    COALESCE(table_number::text, 'TNULL'),
    COALESCE(is_bracket::text, 'BNULL')
)
WHERE game_key IS NULL;

-- Enforce uniqueness for idempotent upserts
CREATE UNIQUE INDEX IF NOT EXISTS idx_games_game_key
ON games(game_key);
