-- Expose decklist URLs for tournament prep commander forecasts.

CREATE OR REPLACE VIEW player_commander_entries AS
SELECT
  te.player_id,
  p.topdeck_id,
  p.name AS player_name,
  te.commander_id,
  c.name AS commander_name,
  t.start_date,
  t.state,
  t.country,
  te.wins,
  te.losses,
  te.draws,
  te.decklist_url
FROM tournament_entries te
JOIN players p ON te.player_id = p.id
LEFT JOIN commanders c ON te.commander_id = c.id
JOIN tournaments t ON te.tournament_id = t.id;

GRANT SELECT ON player_commander_entries TO anon, authenticated;
