-- Scope legacy cEDH read models to Magic: The Gathering / EDH (ADR 0015).
--
-- Non-cEDH tournaments (Riftbound, Gundam TCG, Yu-Gi-Oh) will soon share the
-- tournaments / tournament_entries / games / commanders tables. Every legacy
-- read model below predates tournaments.game/format scoping and would silently
-- mix games; each gains an explicit cEDH guard while preserving its exact
-- column order (CREATE OR REPLACE VIEW is append-only).
--
-- Guard styles used:
--   * `t.game = 'Magic: The Gathering' AND t.format = 'EDH'` where a
--     tournaments join exists or is cheap to add;
--   * `c.game = 'Magic: The Gathering'` where the view is anchored on the
--     (now game-scoped) commanders table and adding a tournaments join would
--     change LEFT JOIN semantics.
--
-- Surfaces intentionally NOT touched here:
--   * Dropped by 20260407000001_retire_unused_surfaces.sql (do not recreate):
--     commander_seat_stats (matview), survival_summary, player_survival_stats,
--     commander_tournament_depth, commander_survival_curve,
--     seat_survival_by_round, seat_survival_by_commander, round_win_rates,
--     seat_position_stats, get_commanders_for_card(TEXT).
--   * latest_analysis (20260111110000): reads analysis_snapshots only; no
--     tournament/game aggregation, nothing to guard.
--   * regional_elo_game_results / global_elo_game_results: guarded in
--     20260706000002_scope_cedh_elo_views.sql.
--   * regional_elo_data_validity / global_elo_data_validity (20260617053055):
--     Elo diagnostics matview that scans raw games/tournaments; downstream Elo
--     state is already scoped via regional_elo_game_results. Left unguarded
--     for now — flagged as a follow-up if raw-vs-included ratios matter after
--     multi-game ingestion begins.
--   * commander_wow_mom, commander_card_report, trap_cards_report,
--     spice_cards_report: read only from the guarded materialized views below,
--     so they inherit the cEDH scope; they are recreated verbatim here purely
--     because dropping their source matviews requires it.
--
-- The *_remote_placeholder.sql migrations are empty alignment stubs (no view
-- definitions live only remotely), and archive/remote-history-conflicts/ is
-- not applied; both were checked and ignored.

-- ============================================================================
-- SECTION 1: Plain views over base tables
-- ============================================================================

-- commander_stats (latest definition: 20260110000001_initial_schema.sql).
-- Guard: c.game — the view is anchored on commanders via LEFT JOINs, so a
-- commanders-side filter keeps zero-entry MTG commanders visible while
-- excluding other games' identities (entries can only join same-game
-- identities, so this also scopes the entry aggregates).
CREATE OR REPLACE VIEW commander_stats AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    c.archetype,
    c.color_identity,
    COUNT(DISTINCT te.id) AS total_entries,
    COUNT(DISTINCT t.id) AS tournaments_played,
    SUM(te.wins) AS total_wins,
    SUM(te.losses) AS total_losses,
    SUM(te.draws) AS total_draws,
    ROUND(AVG(te.win_rate), 4) AS avg_win_rate,
    COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_16) AS top_16_count,
    ROUND(
        COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_16)::NUMERIC /
        NULLIF(COUNT(DISTINCT te.id), 0),
        4
    ) AS conversion_rate_top_16,
    COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_cut) AS top_cut_count,
    ROUND(
        COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_cut)::NUMERIC /
        NULLIF(COUNT(DISTINCT te.id), 0),
        4
    ) AS conversion_rate_top_cut
FROM commanders c
LEFT JOIN tournament_entries te ON c.id = te.commander_id
LEFT JOIN tournaments t ON te.tournament_id = t.id AND t.player_count >= 32
WHERE c.game = 'Magic: The Gathering'
GROUP BY c.id, c.name, c.archetype, c.color_identity;

-- commander_head_to_head (latest definition: 20260110000001_initial_schema.sql).
-- commander_matchups carries a denormalized tournament_id, so the canonical
-- tournaments guard is cheap here.
CREATE OR REPLACE VIEW commander_head_to_head AS
SELECT
    c1.name AS commander,
    c2.name AS opponent,
    COUNT(*) AS games_together,
    COUNT(*) FILTER (WHERE cm.won_against = TRUE) AS wins_against,
    COUNT(*) FILTER (WHERE cm.won_against = FALSE) AS losses_against,
    ROUND(
        COUNT(*) FILTER (WHERE cm.won_against = TRUE)::NUMERIC /
        NULLIF(COUNT(*), 0),
        4
    ) AS win_rate_against
FROM commander_matchups cm
JOIN commanders c1 ON cm.commander_id = c1.id
JOIN commanders c2 ON cm.opponent_commander_id = c2.id
JOIN tournaments t ON cm.tournament_id = t.id
WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
GROUP BY c1.name, c2.name
HAVING COUNT(*) >= 5  -- Minimum sample size
ORDER BY games_together DESC;

-- player_tournament_journey (latest definition: 20260110190000).
CREATE OR REPLACE VIEW player_tournament_journey AS
SELECT
  t.name as tournament,
  t.start_date,
  p.name as player,
  c.name as commander,
  g.round_number,
  g.round_name,
  g.table_number,
  gp.seat_position + 1 as seat,
  gp.result,
  g.is_draw
FROM games g
JOIN game_participants gp ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
LEFT JOIN commanders c ON te.commander_id = c.id
JOIN tournaments t ON g.tournament_id = t.id
WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH';

-- pod_composition (latest definition: 20260110190000).
CREATE OR REPLACE VIEW pod_composition AS
SELECT
  t.name as tournament,
  t.start_date,
  g.round_number,
  g.round_name,
  g.table_number,
  g.is_draw,
  gp.seat_position + 1 as seat,
  p.name as player,
  c.name as commander,
  gp.result,
  CASE WHEN gp.result = 'win' THEN true ELSE false END as won
FROM games g
JOIN game_participants gp ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
LEFT JOIN commanders c ON te.commander_id = c.id
JOIN tournaments t ON g.tournament_id = t.id
WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH';

-- player_seat_distribution (latest definition: 20260110190000).
-- Had no tournaments join; added via te.tournament_id for the guard.
CREATE OR REPLACE VIEW player_seat_distribution AS
SELECT
  p.name as player,
  COUNT(*) as total_games,
  SUM(CASE WHEN gp.seat_position = 0 THEN 1 ELSE 0 END) as seat_1_count,
  SUM(CASE WHEN gp.seat_position = 1 THEN 1 ELSE 0 END) as seat_2_count,
  SUM(CASE WHEN gp.seat_position = 2 THEN 1 ELSE 0 END) as seat_3_count,
  SUM(CASE WHEN gp.seat_position = 3 THEN 1 ELSE 0 END) as seat_4_count,
  ROUND(SUM(CASE WHEN gp.result = 'win' THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as win_rate
FROM game_participants gp
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
GROUP BY p.name
HAVING COUNT(*) >= 3;

-- commander_meta_monthly (latest definition: 20260111100000).
CREATE OR REPLACE VIEW commander_meta_monthly AS
SELECT
    DATE_TRUNC('month', t.start_date) AS month,
    c.name AS commander_name,
    COUNT(DISTINCT te.id) AS entries,
    -- Meta share for this month
    ROUND(
        COUNT(DISTINCT te.id)::NUMERIC /
        SUM(COUNT(DISTINCT te.id)) OVER (PARTITION BY DATE_TRUNC('month', t.start_date)),
        4
    ) AS meta_share,
    -- Performance metrics
    ROUND(AVG(te.win_rate), 4) AS avg_win_rate,
    COUNT(*) FILTER (WHERE te.made_top_16) AS top_16_count,
    ROUND(
        COUNT(*) FILTER (WHERE te.made_top_16)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS top_16_rate
FROM commanders c
JOIN tournament_entries te ON c.id = te.commander_id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.player_count >= 32
  AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
GROUP BY DATE_TRUNC('month', t.start_date), c.name
HAVING COUNT(DISTINCT te.id) >= 3
ORDER BY month DESC, entries DESC;

-- commander_momentum (latest definition: 20260111100000).
CREATE OR REPLACE VIEW commander_momentum AS
WITH monthly_stats AS (
    SELECT
        DATE_TRUNC('month', t.start_date) AS month,
        c.name AS commander_name,
        COUNT(DISTINCT te.id) AS entries,
        ROUND(
            COUNT(DISTINCT te.id)::NUMERIC /
            SUM(COUNT(DISTINCT te.id)) OVER (PARTITION BY DATE_TRUNC('month', t.start_date)),
            4
        ) AS meta_share,
        ROUND(AVG(te.win_rate), 4) AS avg_win_rate
    FROM commanders c
    JOIN tournament_entries te ON c.id = te.commander_id
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.player_count >= 32
      AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
    GROUP BY DATE_TRUNC('month', t.start_date), c.name
    HAVING COUNT(DISTINCT te.id) >= 2
),
with_lag AS (
    SELECT
        *,
        LAG(meta_share) OVER (PARTITION BY commander_name ORDER BY month) AS prev_meta_share,
        LAG(avg_win_rate) OVER (PARTITION BY commander_name ORDER BY month) AS prev_win_rate
    FROM monthly_stats
)
SELECT
    month,
    commander_name,
    entries,
    meta_share,
    prev_meta_share,
    ROUND(meta_share - COALESCE(prev_meta_share, 0), 4) AS meta_share_delta,
    avg_win_rate,
    prev_win_rate,
    ROUND(avg_win_rate - COALESCE(prev_win_rate, 0), 4) AS win_rate_delta,
    -- Momentum score: combination of meta share growth and win rate growth
    ROUND(
        (COALESCE(meta_share - prev_meta_share, 0) * 100) +
        (COALESCE(avg_win_rate - prev_win_rate, 0) * 100),
        2
    ) AS momentum_score
FROM with_lag
WHERE month = (SELECT MAX(month) FROM with_lag)  -- Latest month only
ORDER BY momentum_score DESC;

-- commander_first_appearances (latest definition: 20260111100000).
CREATE OR REPLACE VIEW commander_first_appearances AS
SELECT
    c.name AS commander_name,
    MIN(t.start_date) AS first_seen,
    COUNT(DISTINCT te.id) AS total_entries,
    COUNT(DISTINCT t.id) AS tournaments,
    ROUND(AVG(te.win_rate), 4) AS avg_win_rate,
    COUNT(*) FILTER (WHERE te.made_top_16) AS top_16s
FROM commanders c
JOIN tournament_entries te ON c.id = te.commander_id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.player_count >= 32
  AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
GROUP BY c.name
ORDER BY first_seen DESC;

-- player_commander_entries (latest definition: 20260406000001).
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
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH';

-- ============================================================================
-- SECTION 2: Commander trend materialized views (+ dependent commander_wow_mom)
-- ============================================================================

-- Matviews cannot be CREATE OR REPLACE'd: drop the dependent view first, then
-- the matviews, then rebuild everything (definitions from 20260126010000,
-- commander_wow_mom from 20260126020000).
DROP VIEW IF EXISTS commander_wow_mom;
DROP MATERIALIZED VIEW IF EXISTS commander_weekly_trends;
DROP MATERIALIZED VIEW IF EXISTS commander_monthly_trends;

CREATE MATERIALIZED VIEW commander_weekly_trends AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    date_trunc('week', t.start_date)::date AS week_start_date,
    to_char(date_trunc('week', t.start_date), 'IYYY-"W"IW') AS week_key,
    COUNT(*) AS entries,
    SUM(te.wins) AS wins,
    SUM(te.losses) AS losses,
    SUM(te.draws) AS draws,
    ROUND(
        SUM(te.wins)::numeric / NULLIF(SUM(te.wins + te.losses + te.draws), 0),
        4
    ) AS win_rate
FROM tournament_entries te
JOIN tournaments t ON te.tournament_id = t.id
JOIN commanders c ON te.commander_id = c.id
WHERE t.player_count >= 32
  AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
  AND c.name <> 'Unknown Commander'
GROUP BY c.id, c.name, date_trunc('week', t.start_date);

-- Recreate the indexes from 20260126010000.
CREATE UNIQUE INDEX idx_commander_weekly_trends_pk
ON commander_weekly_trends(commander_id, week_start_date);

CREATE INDEX idx_commander_weekly_trends_commander
ON commander_weekly_trends(commander_id);

CREATE INDEX idx_commander_weekly_trends_week_start
ON commander_weekly_trends(week_start_date);

CREATE MATERIALIZED VIEW commander_monthly_trends AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    date_trunc('month', t.start_date)::date AS month_start_date,
    to_char(date_trunc('month', t.start_date), 'YYYY-MM') AS month_key,
    COUNT(*) AS entries,
    SUM(te.wins) AS wins,
    SUM(te.losses) AS losses,
    SUM(te.draws) AS draws,
    ROUND(
        SUM(te.wins)::numeric / NULLIF(SUM(te.wins + te.losses + te.draws), 0),
        4
    ) AS win_rate
FROM tournament_entries te
JOIN tournaments t ON te.tournament_id = t.id
JOIN commanders c ON te.commander_id = c.id
WHERE t.player_count >= 32
  AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
  AND c.name <> 'Unknown Commander'
GROUP BY c.id, c.name, date_trunc('month', t.start_date);

CREATE UNIQUE INDEX idx_commander_monthly_trends_pk
ON commander_monthly_trends(commander_id, month_start_date);

CREATE INDEX idx_commander_monthly_trends_commander
ON commander_monthly_trends(commander_id);

CREATE INDEX idx_commander_monthly_trends_month_start
ON commander_monthly_trends(month_start_date);

-- commander_wow_mom: recreated verbatim from 20260126020000. It reads only the
-- two matviews above, so it inherits the cEDH guard; no filter of its own.
CREATE OR REPLACE VIEW commander_wow_mom AS
WITH weekly AS (
    SELECT
        commander_id,
        commander_name,
        week_start_date,
        week_key,
        entries,
        win_rate,
        LAG(entries) OVER (
            PARTITION BY commander_id
            ORDER BY week_start_date
        ) AS prev_entries,
        LAG(win_rate) OVER (
            PARTITION BY commander_id
            ORDER BY week_start_date
        ) AS prev_win_rate,
        ROW_NUMBER() OVER (
            PARTITION BY commander_id
            ORDER BY week_start_date DESC
        ) AS rn
    FROM commander_weekly_trends
),
monthly AS (
    SELECT
        commander_id,
        commander_name,
        month_start_date,
        month_key,
        entries,
        win_rate,
        LAG(entries) OVER (
            PARTITION BY commander_id
            ORDER BY month_start_date
        ) AS prev_entries,
        LAG(win_rate) OVER (
            PARTITION BY commander_id
            ORDER BY month_start_date
        ) AS prev_win_rate,
        ROW_NUMBER() OVER (
            PARTITION BY commander_id
            ORDER BY month_start_date DESC
        ) AS rn
    FROM commander_monthly_trends
)
SELECT
    w.commander_id,
    w.commander_name,
    w.week_start_date AS latest_week_start_date,
    w.week_key AS latest_week_key,
    w.entries AS week_entries,
    w.win_rate AS week_win_rate,
    ROUND(
        (w.entries - w.prev_entries)::numeric / NULLIF(w.prev_entries, 0) * 100,
        2
    ) AS week_entries_change_pct,
    ROUND(
        (w.win_rate - w.prev_win_rate) * 100,
        2
    ) AS week_win_rate_change_pp,
    m.month_start_date AS latest_month_start_date,
    m.month_key AS latest_month_key,
    m.entries AS month_entries,
    m.win_rate AS month_win_rate,
    ROUND(
        (m.entries - m.prev_entries)::numeric / NULLIF(m.prev_entries, 0) * 100,
        2
    ) AS month_entries_change_pct,
    ROUND(
        (m.win_rate - m.prev_win_rate) * 100,
        2
    ) AS month_win_rate_change_pp
FROM weekly w
LEFT JOIN monthly m
    ON m.commander_id = w.commander_id
   AND m.rn = 1
WHERE w.rn = 1;

GRANT SELECT ON commander_weekly_trends TO anon, authenticated, service_role;
GRANT SELECT ON commander_monthly_trends TO anon, authenticated, service_role;
GRANT SELECT ON commander_wow_mom TO anon, authenticated, service_role;

-- ============================================================================
-- SECTION 3: Card frequency materialized views (+ dependent commander_card_report)
-- ============================================================================

DROP VIEW IF EXISTS commander_card_report;
DROP MATERIALIZED VIEW IF EXISTS card_frequencies_by_commander;
DROP MATERIALIZED VIEW IF EXISTS card_frequencies_global;

-- Definition from 20260121000000 with a tournaments guard added to both CTEs
-- (parse_decklist is MTG-specific, so both the numerator and the per-commander
-- deck totals must be cEDH-only).
CREATE MATERIALIZED VIEW card_frequencies_by_commander AS
WITH deck_cards AS (
    -- Extract cards from each deck
    SELECT
        te.id AS entry_id,
        te.tournament_id,
        te.commander_id,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
),
commander_totals AS (
    -- Count total decks per commander (only those with parsed decklists)
    SELECT
        te.commander_id,
        COUNT(DISTINCT te.id) AS total_decks
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
    GROUP BY te.commander_id
)
SELECT
    c.id AS commander_id,
    c.name AS commander,
    dc.card_name,
    COUNT(DISTINCT dc.entry_id) AS deck_count,
    ct.total_decks,
    ROUND(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF(ct.total_decks, 0),
        4
    ) AS inclusion_rate,
    classify_card_tier(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF(ct.total_decks, 0)
    ) AS tier
FROM deck_cards dc
JOIN commanders c ON dc.commander_id = c.id
JOIN commander_totals ct ON dc.commander_id = ct.commander_id
GROUP BY c.id, c.name, dc.card_name, ct.total_decks
HAVING COUNT(DISTINCT dc.entry_id) >= 2  -- Minimum 2 appearances
ORDER BY c.name, COUNT(DISTINCT dc.entry_id) DESC;

-- Recreate the indexes from 20260121000000 and 20260121100003.
CREATE UNIQUE INDEX idx_card_freq_pk ON card_frequencies_by_commander(commander_id, card_name);
CREATE INDEX idx_card_freq_commander ON card_frequencies_by_commander(commander_id);
CREATE INDEX idx_card_freq_commander_name ON card_frequencies_by_commander(commander);
CREATE INDEX idx_card_freq_card ON card_frequencies_by_commander(card_name);
CREATE INDEX idx_card_freq_tier ON card_frequencies_by_commander(tier);
CREATE INDEX idx_card_freq_rate ON card_frequencies_by_commander(inclusion_rate DESC);
CREATE INDEX IF NOT EXISTS idx_card_freq_by_commander_cardname
ON card_frequencies_by_commander(card_name);

COMMENT ON MATERIALIZED VIEW card_frequencies_by_commander IS 'Card inclusion frequencies per commander (cEDH only), refreshed manually';

CREATE MATERIALIZED VIEW card_frequencies_global AS
WITH deck_cards AS (
    SELECT
        te.id AS entry_id,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
),
total_decks AS (
    SELECT COUNT(DISTINCT te.id) AS total
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
)
SELECT
    dc.card_name,
    COUNT(DISTINCT dc.entry_id) AS deck_count,
    (SELECT total FROM total_decks) AS total_decks,
    ROUND(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF((SELECT total FROM total_decks), 0),
        4
    ) AS inclusion_rate,
    COUNT(DISTINCT te.commander_id) AS commander_count,
    classify_card_tier(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF((SELECT total FROM total_decks), 0)
    ) AS tier
FROM deck_cards dc
JOIN tournament_entries te ON dc.entry_id = te.id
GROUP BY dc.card_name
HAVING COUNT(DISTINCT dc.entry_id) >= 3  -- Minimum 3 appearances globally
ORDER BY COUNT(DISTINCT dc.entry_id) DESC;

CREATE UNIQUE INDEX idx_card_freq_global_pk ON card_frequencies_global(card_name);
CREATE INDEX idx_card_freq_global_tier ON card_frequencies_global(tier);
CREATE INDEX idx_card_freq_global_rate ON card_frequencies_global(inclusion_rate DESC);
CREATE INDEX idx_card_freq_global_cmd_count ON card_frequencies_global(commander_count DESC);

COMMENT ON MATERIALIZED VIEW card_frequencies_global IS 'Global card inclusion frequencies across all cEDH commanders';

-- commander_card_report: recreated verbatim from 20260121000000; reads only
-- the guarded matviews above, so no filter of its own.
CREATE OR REPLACE VIEW commander_card_report AS
SELECT
    cf.commander,
    cf.commander_id,
    cf.card_name,
    cf.deck_count,
    cf.total_decks,
    cf.inclusion_rate,
    cf.tier,
    gf.inclusion_rate AS global_rate,
    ROUND(cf.inclusion_rate - COALESCE(gf.inclusion_rate, 0), 4) AS synergy_score
FROM card_frequencies_by_commander cf
LEFT JOIN card_frequencies_global gf ON cf.card_name = gf.card_name
ORDER BY cf.commander, cf.inclusion_rate DESC;

COMMENT ON VIEW commander_card_report IS 'Card frequencies with synergy scores (commander rate - global rate)';

GRANT SELECT ON card_frequencies_by_commander TO anon, authenticated, service_role;
GRANT SELECT ON card_frequencies_global TO anon, authenticated, service_role;
GRANT SELECT ON commander_card_report TO anon, authenticated, service_role;

-- ============================================================================
-- SECTION 4: Card performance materialized views (+ trap/spice reports)
-- ============================================================================

DROP VIEW IF EXISTS trap_cards_report;
DROP VIEW IF EXISTS spice_cards_report;
DROP MATERIALIZED VIEW IF EXISTS card_performance_by_commander;
DROP MATERIALIZED VIEW IF EXISTS card_performance_global;

-- Definition from 20260121000001 with the tournaments guard added to the
-- deck_cards and commander_baseline CTEs.
CREATE MATERIALIZED VIEW card_performance_by_commander AS
WITH deck_cards AS (
    -- Extract cards from each deck with performance data
    SELECT
        te.id AS entry_id,
        te.commander_id,
        te.win_rate,
        te.made_top_16,
        te.made_top_cut,
        te.final_standing,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
      AND te.win_rate IS NOT NULL
),
card_stats AS (
    SELECT
        dc.commander_id,
        dc.card_name,
        COUNT(DISTINCT dc.entry_id) AS deck_count,
        AVG(dc.win_rate) AS avg_win_rate,
        STDDEV(dc.win_rate) AS std_win_rate,
        COUNT(*) FILTER (WHERE dc.made_top_16) AS top_16_count,
        COUNT(*) FILTER (WHERE dc.made_top_cut) AS top_cut_count,
        AVG(dc.final_standing) AS avg_standing
    FROM deck_cards dc
    GROUP BY dc.commander_id, dc.card_name
    HAVING COUNT(DISTINCT dc.entry_id) >= 5  -- Minimum sample size
),
commander_baseline AS (
    -- Get baseline win rate per commander (all decks)
    SELECT
        te.commander_id,
        AVG(te.win_rate) AS baseline_win_rate,
        COUNT(*) AS total_decks,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY te.win_rate) AS median_win_rate
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.win_rate IS NOT NULL
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
    GROUP BY te.commander_id
)
SELECT
    c.id AS commander_id,
    c.name AS commander,
    cs.card_name,
    cs.deck_count,
    cb.total_decks,
    ROUND(cs.deck_count::NUMERIC / cb.total_decks, 4) AS inclusion_rate,
    ROUND(cs.avg_win_rate::NUMERIC, 4) AS avg_win_rate,
    ROUND(cb.baseline_win_rate::NUMERIC, 4) AS baseline_win_rate,
    ROUND((cs.avg_win_rate - cb.baseline_win_rate)::NUMERIC, 4) AS win_rate_delta,
    ROUND(cs.std_win_rate::NUMERIC, 4) AS std_win_rate,
    cs.top_16_count,
    cs.top_cut_count,
    ROUND(cs.top_16_count::NUMERIC / cs.deck_count, 4) AS top_16_rate,
    ROUND(cs.avg_standing::NUMERIC, 1) AS avg_standing,
    -- Performance tier based on delta from baseline
    CASE
        WHEN cs.avg_win_rate - cb.baseline_win_rate >= 0.05 THEN 'overperformer'
        WHEN cs.avg_win_rate - cb.baseline_win_rate <= -0.05 THEN 'underperformer'
        ELSE 'neutral'
    END AS performance_tier
FROM card_stats cs
JOIN commanders c ON cs.commander_id = c.id
JOIN commander_baseline cb ON cs.commander_id = cb.commander_id
ORDER BY c.name, cs.deck_count DESC;

CREATE UNIQUE INDEX idx_card_perf_pk ON card_performance_by_commander(commander_id, card_name);
CREATE INDEX idx_card_perf_commander ON card_performance_by_commander(commander_id);
CREATE INDEX idx_card_perf_card ON card_performance_by_commander(card_name);
CREATE INDEX idx_card_perf_delta ON card_performance_by_commander(win_rate_delta DESC);
CREATE INDEX idx_card_perf_tier ON card_performance_by_commander(performance_tier);

COMMENT ON MATERIALIZED VIEW card_performance_by_commander IS 'Card win rate correlation per commander with performance tiers (cEDH only)';

CREATE MATERIALIZED VIEW card_performance_global AS
WITH deck_cards AS (
    SELECT
        te.id AS entry_id,
        te.commander_id,
        te.win_rate,
        te.made_top_16,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
      AND te.win_rate IS NOT NULL
),
global_baseline AS (
    SELECT
        AVG(te.win_rate) AS baseline_win_rate,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY te.win_rate) AS median_win_rate,
        COUNT(*) AS total_decks
    FROM tournament_entries te
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND te.win_rate IS NOT NULL
      AND te.decklist_text IS NOT NULL
),
card_stats AS (
    SELECT
        dc.card_name,
        COUNT(DISTINCT dc.entry_id) AS deck_count,
        COUNT(DISTINCT dc.commander_id) AS commander_count,
        AVG(dc.win_rate) AS avg_win_rate,
        STDDEV(dc.win_rate) AS std_win_rate,
        COUNT(*) FILTER (WHERE dc.made_top_16) AS top_16_count,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dc.win_rate) AS median_win_rate
    FROM deck_cards dc
    GROUP BY dc.card_name
    HAVING COUNT(DISTINCT dc.entry_id) >= 10  -- Higher threshold for global
)
SELECT
    cs.card_name,
    cs.deck_count,
    (SELECT total_decks FROM global_baseline) AS total_decks,
    ROUND(cs.deck_count::NUMERIC / (SELECT total_decks FROM global_baseline), 4) AS inclusion_rate,
    cs.commander_count,
    ROUND(cs.avg_win_rate::NUMERIC, 4) AS avg_win_rate,
    ROUND((SELECT baseline_win_rate FROM global_baseline)::NUMERIC, 4) AS baseline_win_rate,
    ROUND((cs.avg_win_rate - (SELECT baseline_win_rate FROM global_baseline))::NUMERIC, 4) AS win_rate_delta,
    ROUND(cs.std_win_rate::NUMERIC, 4) AS std_win_rate,
    ROUND(cs.median_win_rate::NUMERIC, 4) AS median_win_rate,
    cs.top_16_count,
    ROUND(cs.top_16_count::NUMERIC / cs.deck_count, 4) AS top_16_rate,
    -- Trap card identification: high popularity + below median performance
    CASE
        WHEN cs.deck_count::NUMERIC / (SELECT total_decks FROM global_baseline) >= 0.20
             AND cs.avg_win_rate < (SELECT median_win_rate FROM global_baseline)
        THEN TRUE
        ELSE FALSE
    END AS is_potential_trap,
    -- Spice card identification: low popularity + above median performance
    CASE
        WHEN cs.deck_count::NUMERIC / (SELECT total_decks FROM global_baseline) < 0.10
             AND cs.avg_win_rate > (SELECT baseline_win_rate FROM global_baseline) + 0.03
        THEN TRUE
        ELSE FALSE
    END AS is_spice
FROM card_stats cs
ORDER BY cs.deck_count DESC;

CREATE UNIQUE INDEX idx_card_perf_global_pk ON card_performance_global(card_name);
CREATE INDEX idx_card_perf_global_delta ON card_performance_global(win_rate_delta DESC);
CREATE INDEX idx_card_perf_global_trap ON card_performance_global(is_potential_trap) WHERE is_potential_trap = TRUE;
CREATE INDEX idx_card_perf_global_spice ON card_performance_global(is_spice) WHERE is_spice = TRUE;

COMMENT ON MATERIALIZED VIEW card_performance_global IS 'Global cEDH card performance with trap and spice identification';

-- trap/spice reports: recreated verbatim from 20260121000001; they read only
-- the guarded card_performance_global matview.
CREATE OR REPLACE VIEW trap_cards_report AS
SELECT
    card_name,
    deck_count,
    inclusion_rate,
    avg_win_rate,
    baseline_win_rate,
    win_rate_delta,
    top_16_rate,
    commander_count,
    ROUND(inclusion_rate * ABS(win_rate_delta), 4) AS trap_score
FROM card_performance_global
WHERE is_potential_trap = TRUE
ORDER BY inclusion_rate * ABS(win_rate_delta) DESC;

COMMENT ON VIEW trap_cards_report IS 'Cards that are popular but underperform - potential traps';

CREATE OR REPLACE VIEW spice_cards_report AS
SELECT
    card_name,
    deck_count,
    inclusion_rate,
    avg_win_rate,
    baseline_win_rate,
    win_rate_delta,
    top_16_rate,
    commander_count
FROM card_performance_global
WHERE is_spice = TRUE
ORDER BY win_rate_delta DESC;

COMMENT ON VIEW spice_cards_report IS 'Low-popularity cards that overperform - hidden gems';

GRANT SELECT ON card_performance_by_commander TO anon, authenticated, service_role;
GRANT SELECT ON card_performance_global TO anon, authenticated, service_role;
GRANT SELECT ON trap_cards_report TO anon, authenticated, service_role;
GRANT SELECT ON spice_cards_report TO anon, authenticated, service_role;

-- ============================================================================
-- SECTION 5: Read-model SQL functions
-- ============================================================================
-- CREATE OR REPLACE FUNCTION resets proconfig, so the search_path hardening
-- from 20260328000000 is re-declared inline on each function.

-- get_commander_round_stats (latest definition: 20260110000001).
CREATE OR REPLACE FUNCTION get_commander_round_stats(commander_uuid UUID)
RETURNS TABLE (
    round_number INTEGER,
    games_played BIGINT,
    wins BIGINT,
    losses BIGINT,
    draws BIGINT,
    win_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        g.round_number,
        COUNT(*)::BIGINT AS games_played,
        COUNT(*) FILTER (WHERE gp.result = 'win')::BIGINT AS wins,
        COUNT(*) FILTER (WHERE gp.result = 'loss')::BIGINT AS losses,
        COUNT(*) FILTER (WHERE gp.result = 'draw')::BIGINT AS draws,
        ROUND(
            COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0),
            4
        ) AS win_rate
    FROM game_participants gp
    JOIN games g ON gp.game_id = g.id
    JOIN tournament_entries te ON gp.entry_id = te.id
    JOIN tournaments t ON g.tournament_id = t.id
    WHERE te.commander_id = commander_uuid
      AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
      AND g.status = 'Completed'
      AND NOT g.is_bracket
    GROUP BY g.round_number
    ORDER BY g.round_number;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = public, extensions;

GRANT EXECUTE ON FUNCTION get_commander_round_stats(UUID) TO anon, authenticated, service_role;

-- get_notable_players_for_commander (latest definition: 20260121200000).
CREATE OR REPLACE FUNCTION get_notable_players_for_commander(
    p_commander_id UUID,
    p_limit INT DEFAULT 20,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    player_id UUID,
    player_name TEXT,
    topdeck_handle TEXT,
    topdeck_id TEXT,
    entries BIGINT,
    total_wins BIGINT,
    total_losses BIGINT,
    total_draws BIGINT,
    total_games BIGINT,
    win_rate NUMERIC,
    top_16_count BIGINT,
    avg_standing NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS player_id,
        p.name AS player_name,
        p.topdeck_handle,
        p.topdeck_id,
        COUNT(te.id) AS entries,
        SUM(te.wins)::BIGINT AS total_wins,
        SUM(te.losses)::BIGINT AS total_losses,
        SUM(te.draws)::BIGINT AS total_draws,
        SUM(te.wins + te.losses + te.draws)::BIGINT AS total_games,
        ROUND(SUM(te.wins)::NUMERIC / NULLIF(SUM(te.wins + te.losses + te.draws), 0), 4) AS win_rate,
        SUM(CASE WHEN te.made_top_16 THEN 1 ELSE 0 END)::BIGINT AS top_16_count,
        ROUND(AVG(te.final_standing), 1) AS avg_standing
    FROM tournament_entries te
    JOIN players p ON te.player_id = p.id
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE te.commander_id = p_commander_id
      AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
    GROUP BY p.id, p.name, p.topdeck_handle, p.topdeck_id
    HAVING COUNT(te.id) >= 2
    ORDER BY COUNT(te.id) DESC, SUM(te.wins) DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = public, extensions;

GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID, INT, INT) TO anon, authenticated, service_role;

-- get_commander_matchups (latest definition: 20260121200000).
CREATE OR REPLACE FUNCTION get_commander_matchups(
    p_commander_id UUID,
    p_limit INT DEFAULT 50,
    p_offset INT DEFAULT 0,
    p_min_games INT DEFAULT 5
)
RETURNS TABLE (
    opponent_commander_id UUID,
    opponent_commander_name TEXT,
    games_played BIGINT,
    wins BIGINT,
    losses BIGINT,
    draws BIGINT,
    win_rate NUMERIC,
    loss_rate NUMERIC,
    draw_rate NUMERIC,
    -- Statistical significance indicators
    expected_win_rate NUMERIC,
    win_rate_vs_expected NUMERIC,
    is_statistically_significant BOOLEAN,
    confidence_level TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH matchup_data AS (
        SELECT
            opp_c.id AS opp_commander_id,
            opp_c.name AS opp_commander_name,
            COUNT(*) AS total_games,
            COUNT(*) FILTER (WHERE gp.result = 'win') AS total_wins,
            COUNT(*) FILTER (WHERE gp.result = 'loss') AS total_losses,
            COUNT(*) FILTER (WHERE gp.result = 'draw') AS total_draws
        FROM game_participants gp
        JOIN tournament_entries te ON gp.entry_id = te.id
        JOIN games g ON gp.game_id = g.id
        JOIN tournaments t ON g.tournament_id = t.id
        JOIN game_participants opp_gp ON g.id = opp_gp.game_id AND opp_gp.id != gp.id
        JOIN tournament_entries opp_te ON opp_gp.entry_id = opp_te.id
        JOIN commanders opp_c ON opp_te.commander_id = opp_c.id
        WHERE te.commander_id = p_commander_id
          AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
          AND gp.result != 'bye'
          AND opp_gp.result != 'bye'
        GROUP BY opp_c.id, opp_c.name
        HAVING COUNT(*) >= p_min_games
    )
    SELECT
        md.opp_commander_id,
        md.opp_commander_name,
        md.total_games,
        md.total_wins,
        md.total_losses,
        md.total_draws,
        ROUND(md.total_wins::NUMERIC / md.total_games, 4) AS win_rate,
        ROUND(md.total_losses::NUMERIC / md.total_games, 4) AS loss_rate,
        ROUND(md.total_draws::NUMERIC / md.total_games, 4) AS draw_rate,
        -- Expected win rate in 4-player pod (25%)
        0.25::NUMERIC AS expected_win_rate,
        -- Difference from expected
        ROUND((md.total_wins::NUMERIC / md.total_games) - 0.25, 4) AS win_rate_vs_expected,
        -- Tiered significance heuristic for 4-player cEDH (expected win rate = 0.25):
        --   >= 30 games : always significant (Law of Large Numbers)
        --   20-29 games : significant if win rate deviates > 10% from 0.25 (i.e. >35% or <15%)
        --   10-19 games : significant only for extreme outliers (deviation > 15%, i.e. >40% or <10%)
        --   < 10 games  : never significant (insufficient data)
        CASE
            WHEN md.total_games >= 30 THEN TRUE
            WHEN md.total_games >= 20 AND ABS((md.total_wins::NUMERIC / md.total_games) - 0.25) > 0.10 THEN TRUE
            WHEN md.total_games >= 10 AND ABS((md.total_wins::NUMERIC / md.total_games) - 0.25) > 0.15 THEN TRUE
            ELSE FALSE
        END AS is_statistically_significant,
        -- Confidence level based on sample size
        CASE
            WHEN md.total_games >= 50 THEN 'high'
            WHEN md.total_games >= 30 THEN 'medium'
            WHEN md.total_games >= 15 THEN 'low'
            ELSE 'very_low'
        END AS confidence_level
    FROM matchup_data md
    ORDER BY md.total_games DESC, md.total_wins DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = public, extensions;

GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID, INT, INT, INT) TO anon, authenticated, service_role;

-- get_commander_matchups_count (latest definition: 20260121200000).
CREATE OR REPLACE FUNCTION get_commander_matchups_count(
    p_commander_id UUID,
    p_min_games INT DEFAULT 5
)
RETURNS BIGINT AS $$
BEGIN
    RETURN (
        SELECT COUNT(DISTINCT opp_te.commander_id)
        FROM game_participants gp
        JOIN tournament_entries te ON gp.entry_id = te.id
        JOIN games g ON gp.game_id = g.id
        JOIN tournaments t ON g.tournament_id = t.id
        JOIN game_participants opp_gp ON g.id = opp_gp.game_id AND opp_gp.id != gp.id
        JOIN tournament_entries opp_te ON opp_gp.entry_id = opp_te.id
        WHERE te.commander_id = p_commander_id
          AND t.game = 'Magic: The Gathering' AND t.format = 'EDH'
          AND gp.result != 'bye'
          AND opp_gp.result != 'bye'
        GROUP BY opp_te.commander_id
        HAVING COUNT(*) >= p_min_games
    );
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = public, extensions;

GRANT EXECUTE ON FUNCTION get_commander_matchups_count(UUID, INT) TO anon, authenticated, service_role;

-- ============================================================================
-- SECTION 6: Restore view options and grants
-- ============================================================================
-- CREATE OR REPLACE VIEW resets view options; re-apply the security_invoker
-- convention from 20260328000000 / 20260508000000 to every plain view touched
-- above (materialized views do not support security_invoker).

ALTER VIEW commander_stats SET (security_invoker = true);
ALTER VIEW commander_head_to_head SET (security_invoker = true);
ALTER VIEW player_tournament_journey SET (security_invoker = true);
ALTER VIEW pod_composition SET (security_invoker = true);
ALTER VIEW player_seat_distribution SET (security_invoker = true);
ALTER VIEW commander_meta_monthly SET (security_invoker = true);
ALTER VIEW commander_momentum SET (security_invoker = true);
ALTER VIEW commander_first_appearances SET (security_invoker = true);
ALTER VIEW player_commander_entries SET (security_invoker = true);
ALTER VIEW commander_wow_mom SET (security_invoker = true);
ALTER VIEW commander_card_report SET (security_invoker = true);
ALTER VIEW trap_cards_report SET (security_invoker = true);
ALTER VIEW spice_cards_report SET (security_invoker = true);

-- Re-apply read grants per source-migration conventions.
GRANT SELECT ON commander_stats TO anon, authenticated;
GRANT SELECT ON commander_head_to_head TO anon, authenticated;
GRANT SELECT ON player_tournament_journey TO anon, authenticated;
GRANT SELECT ON pod_composition TO anon, authenticated;
GRANT SELECT ON player_seat_distribution TO anon, authenticated;
GRANT SELECT ON commander_meta_monthly TO anon, authenticated;
GRANT SELECT ON commander_momentum TO anon, authenticated;
GRANT SELECT ON commander_first_appearances TO anon, authenticated;
GRANT SELECT ON player_commander_entries TO anon, authenticated;
