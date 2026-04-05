-- Migration: Normalize top-cut and top-16 flags for small events (<=34 players)

UPDATE tournaments
SET top_cut = 4
WHERE player_count <= 34
  AND (top_cut IS NULL OR top_cut <> 4);

UPDATE tournament_entries te
SET made_top_cut = (te.final_standing <= 4),
    made_top_16 = (te.final_standing <= 4)
FROM tournaments t
WHERE te.tournament_id = t.id
  AND t.player_count <= 34;
