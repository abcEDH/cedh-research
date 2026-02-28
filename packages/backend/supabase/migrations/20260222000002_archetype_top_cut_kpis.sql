-- Migration: Consolidated cEDH top-cut KPI view by archetype (Top 4/10/16)

DROP VIEW IF EXISTS archetype_top_cut_kpis;

CREATE OR REPLACE VIEW archetype_top_cut_kpis AS
WITH normalized_tournaments AS (
    SELECT
        t.id AS tournament_id,
        CASE
            WHEN t.player_count BETWEEN 17 AND 34 THEN 4
            WHEN t.player_count BETWEEN 35 AND 64 THEN 10
            WHEN t.player_count >= 65 THEN 16
            ELSE 0
        END AS normalized_top_cut
    FROM tournaments t
    WHERE t.format = 'EDH'
      AND t.player_count >= 17
),
eligible_entries AS (
    SELECT
        te.id AS entry_id,
        COALESCE(c.archetype, 'unassigned') AS archetype,
        te.final_standing,
        nt.normalized_top_cut
    FROM tournament_entries te
    JOIN normalized_tournaments nt ON nt.tournament_id = te.tournament_id
    JOIN commanders c ON c.id = te.commander_id
    WHERE nt.normalized_top_cut IN (4, 10, 16)
      AND te.final_standing IS NOT NULL
      AND c.name <> 'Unknown Commander'
),
global_top_cut_totals AS (
    SELECT
        COUNT(*) FILTER (WHERE normalized_top_cut = 4 AND final_standing <= 4) AS total_top4_entries,
        COUNT(*) FILTER (WHERE normalized_top_cut = 10 AND final_standing <= 10) AS total_top10_entries,
        COUNT(*) FILTER (WHERE normalized_top_cut = 16 AND final_standing <= 16) AS total_top16_entries
    FROM eligible_entries
),
per_archetype AS (
    SELECT
        e.archetype,
        COUNT(*) AS total_decks_analyzed,

        COUNT(*) FILTER (WHERE e.normalized_top_cut = 4) AS entries_in_top4_events,
        COUNT(*) FILTER (WHERE e.normalized_top_cut = 10) AS entries_in_top10_events,
        COUNT(*) FILTER (WHERE e.normalized_top_cut = 16) AS entries_in_top16_events,

        COUNT(*) FILTER (WHERE e.normalized_top_cut = 4 AND e.final_standing <= 4) AS top4_appearances,
        COUNT(*) FILTER (WHERE e.normalized_top_cut = 10 AND e.final_standing <= 10) AS top10_appearances,
        COUNT(*) FILTER (WHERE e.normalized_top_cut = 16 AND e.final_standing <= 16) AS top16_appearances,

        COUNT(*) FILTER (WHERE e.normalized_top_cut = 4 AND e.final_standing = 1) AS top4_event_wins,
        COUNT(*) FILTER (WHERE e.normalized_top_cut = 10 AND e.final_standing = 1) AS top10_event_wins,
        COUNT(*) FILTER (WHERE e.normalized_top_cut = 16 AND e.final_standing = 1) AS top16_event_wins
    FROM eligible_entries e
    GROUP BY e.archetype
)
SELECT
    p.archetype,
    p.total_decks_analyzed,

    p.top4_appearances,
    p.top10_appearances,
    p.top16_appearances,

    ROUND(p.top4_appearances::NUMERIC / NULLIF(g.total_top4_entries, 0), 4) AS top4_appearance_share,
    ROUND(p.top10_appearances::NUMERIC / NULLIF(g.total_top10_entries, 0), 4) AS top10_appearance_share,
    ROUND(p.top16_appearances::NUMERIC / NULLIF(g.total_top16_entries, 0), 4) AS top16_appearance_share,

    ROUND(p.top4_appearances::NUMERIC / NULLIF(p.entries_in_top4_events, 0), 4) AS top4_conversion_rate,
    ROUND(p.top10_appearances::NUMERIC / NULLIF(p.entries_in_top10_events, 0), 4) AS top10_conversion_rate,
    ROUND(p.top16_appearances::NUMERIC / NULLIF(p.entries_in_top16_events, 0), 4) AS top16_conversion_rate,

    ROUND(p.top4_event_wins::NUMERIC / NULLIF(p.top4_appearances, 0), 4) AS top4_win_rate,
    ROUND(p.top10_event_wins::NUMERIC / NULLIF(p.top10_appearances, 0), 4) AS top10_win_rate,
    ROUND(p.top16_event_wins::NUMERIC / NULLIF(p.top16_appearances, 0), 4) AS top16_win_rate
FROM per_archetype p
CROSS JOIN global_top_cut_totals g;

GRANT SELECT ON archetype_top_cut_kpis TO anon;
GRANT SELECT ON archetype_top_cut_kpis TO authenticated;
GRANT SELECT ON archetype_top_cut_kpis TO service_role;
