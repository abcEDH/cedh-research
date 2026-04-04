-- Canonicalize game_key values and remove duplicated logical games.

CREATE OR REPLACE FUNCTION compute_game_key(
  p_tournament_id uuid,
  p_round_number integer,
  p_round_name text,
  p_table_number integer,
  p_is_bracket boolean
) RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT concat_ws(
    '|',
    p_tournament_id::text,
    COALESCE(p_round_number::text, 'RNULL'),
    COALESCE(p_round_name, 'RNNULL'),
    COALESCE(p_table_number::text, 'TNULL'),
    lower(COALESCE(p_is_bracket::text, 'false'))
  );
$$;

CREATE OR REPLACE FUNCTION set_canonical_game_key()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.game_key := compute_game_key(
    NEW.tournament_id,
    NEW.round_number,
    NEW.round_name,
    NEW.table_number,
    NEW.is_bracket
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_canonical_game_key ON games;

CREATE TRIGGER trg_set_canonical_game_key
BEFORE INSERT OR UPDATE ON games
FOR EACH ROW
EXECUTE FUNCTION set_canonical_game_key();

WITH ranked_games AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY
        tournament_id,
        round_number,
        COALESCE(round_name, 'RNNULL'),
        table_number,
        COALESCE(is_bracket, false)
      ORDER BY created_at ASC, id ASC
    ) AS row_num
  FROM games
),
duplicate_games AS (
  SELECT id
  FROM ranked_games
  WHERE row_num > 1
)
DELETE FROM games g
USING duplicate_games d
WHERE g.id = d.id;

UPDATE games
SET game_key = compute_game_key(
  tournament_id,
  round_number,
  round_name,
  table_number,
  is_bracket
);

ALTER TABLE games
ALTER COLUMN game_key SET NOT NULL;

DROP INDEX IF EXISTS idx_games_game_key;

CREATE UNIQUE INDEX idx_games_game_key
ON games(game_key);
