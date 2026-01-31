-- cEDH Analytics Database Schema
-- Designed for: win rate by round, seat position analysis, matchup tracking, conversion rates
-- Data source: TopDeck.gg API
-- Card enrichment: Scryfall API

-- Enable UUID extension
-- Supabase uses gen_random_uuid() natively

-- ============================================================================
-- CORE REFERENCE TABLES
-- ============================================================================

-- Commanders (unique commander/partner combinations)
-- Links to Scryfall for card data enrichment
CREATE TABLE commanders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                    -- Display name (e.g., "Kraum, Ludevic's Opus / Tymna the Weaver")
    commander_names TEXT[] NOT NULL,       -- Array of individual commander names
    scryfall_ids TEXT[],                   -- Array of Scryfall card IDs for API enrichment
    color_identity TEXT[],                 -- e.g., ['W', 'U', 'B', 'R']
    archetype TEXT,                        -- User-categorized: 'turbo', 'midrange', 'stax', 'adaptive', etc.
    win_condition TEXT,                    -- Primary win condition description
    notes TEXT,                            -- Additional categorization notes
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name)
);

-- Index for commander name lookups
CREATE INDEX idx_commanders_name ON commanders(name);
CREATE INDEX idx_commanders_archetype ON commanders(archetype);

-- Players (unique TopDeck.gg users)
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topdeck_id TEXT UNIQUE NOT NULL,       -- TopDeck.gg player UID
    name TEXT NOT NULL,                    -- Display name (can change)
    discord_username TEXT,
    discord_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_players_topdeck_id ON players(topdeck_id);

-- ============================================================================
-- TOURNAMENT TABLES
-- ============================================================================

-- Tournaments (events from TopDeck.gg)
CREATE TABLE tournaments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topdeck_tid TEXT UNIQUE NOT NULL,      -- TopDeck.gg tournament ID (slug)
    name TEXT NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    game TEXT NOT NULL DEFAULT 'Magic: The Gathering',
    format TEXT NOT NULL DEFAULT 'EDH',

    -- Tournament structure
    player_count INTEGER NOT NULL,
    swiss_rounds INTEGER NOT NULL,
    top_cut INTEGER DEFAULT 0,             -- Size of top cut (0 = no bracket)

    -- Elo statistics
    average_elo INTEGER,
    median_elo INTEGER,
    top_elo INTEGER,

    -- Location data
    city TEXT,
    state TEXT,
    country TEXT,
    venue TEXT,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),

    -- Metadata
    header_image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only index tournaments meeting our criteria (32+ players)
CREATE INDEX idx_tournaments_date ON tournaments(start_date DESC);
CREATE INDEX idx_tournaments_player_count ON tournaments(player_count);
CREATE INDEX idx_tournaments_format ON tournaments(format);
CREATE INDEX idx_tournaments_large ON tournaments(start_date DESC) WHERE player_count >= 32;

-- ============================================================================
-- TOURNAMENT ENTRY & RESULTS
-- ============================================================================

-- Tournament entries (a player's participation in a tournament)
CREATE TABLE tournament_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    commander_id UUID NOT NULL REFERENCES commanders(id),

    -- Final standings
    final_standing INTEGER,                -- Final position (1 = winner)
    points INTEGER NOT NULL DEFAULT 0,     -- Total points (W=5, D=1, L=0)

    -- Win/Loss/Draw breakdown
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    byes INTEGER NOT NULL DEFAULT 0,

    -- Swiss vs Bracket breakdown
    wins_swiss INTEGER DEFAULT 0,
    losses_swiss INTEGER DEFAULT 0,
    wins_bracket INTEGER DEFAULT 0,
    losses_bracket INTEGER DEFAULT 0,

    -- Rate calculations (stored for query efficiency)
    win_rate NUMERIC(5, 4),                -- 0.0000 to 1.0000
    opponent_win_rate NUMERIC(5, 4),       -- Tiebreaker

    -- Decklist info
    decklist_url TEXT,
    decklist_text TEXT,
    decklist_obj JSONB,                    -- Structured deck data from TopDeck

    -- Conversion tracking
    made_top_cut BOOLEAN DEFAULT FALSE,    -- Did they make the top cut?
    made_top_16 BOOLEAN DEFAULT FALSE,     -- Specifically top 16

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tournament_id, player_id)
);

CREATE INDEX idx_entries_tournament ON tournament_entries(tournament_id);
CREATE INDEX idx_entries_player ON tournament_entries(player_id);
CREATE INDEX idx_entries_commander ON tournament_entries(commander_id);
CREATE INDEX idx_entries_standing ON tournament_entries(final_standing);
CREATE INDEX idx_entries_top_cut ON tournament_entries(made_top_cut) WHERE made_top_cut = TRUE;
CREATE INDEX idx_entries_top_16 ON tournament_entries(made_top_16) WHERE made_top_16 = TRUE;

-- ============================================================================
-- GAME-LEVEL TRACKING (POD RESULTS)
-- ============================================================================

-- Games (individual pod games within a round)
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,

    -- Round info
    round_number INTEGER,                  -- Swiss round number (1, 2, 3...)
    round_name TEXT,                       -- For bracket: "Top 8", "Top 4", "Finals"
    is_bracket BOOLEAN DEFAULT FALSE,      -- Is this a top cut round?
    table_number INTEGER,

    -- Game outcome
    status TEXT NOT NULL DEFAULT 'Completed', -- 'Completed', 'Active', 'Pending', 'Bye'
    is_draw BOOLEAN DEFAULT FALSE,         -- Did all 4 players draw?
    winner_id UUID REFERENCES players(id), -- NULL if draw

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_games_tournament ON games(tournament_id);
CREATE INDEX idx_games_round ON games(tournament_id, round_number);
CREATE INDEX idx_games_winner ON games(winner_id);

-- Game participants (each player in a pod with their seat position)
CREATE TABLE game_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    entry_id UUID NOT NULL REFERENCES tournament_entries(id) ON DELETE CASCADE,

    -- CRITICAL: Seat position (0-3, representing turn order)
    seat_position INTEGER NOT NULL CHECK (seat_position >= 0 AND seat_position <= 3),

    -- Outcome for this player
    result TEXT NOT NULL CHECK (result IN ('win', 'loss', 'draw', 'bye')),

    -- Points earned this game
    points_earned INTEGER NOT NULL DEFAULT 0, -- 5 for win, 1 for draw, 0 for loss

    UNIQUE(game_id, entry_id),
    UNIQUE(game_id, seat_position)
);

CREATE INDEX idx_participants_game ON game_participants(game_id);
CREATE INDEX idx_participants_entry ON game_participants(entry_id);
CREATE INDEX idx_participants_seat ON game_participants(seat_position);
CREATE INDEX idx_participants_result ON game_participants(result);

-- ============================================================================
-- COMMANDER MATCHUP TRACKING
-- ============================================================================

-- Matchups (commander vs commander results within same game)
-- Derived/materialized view for efficient matchup queries
CREATE TABLE commander_matchups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    commander_id UUID NOT NULL REFERENCES commanders(id),
    opponent_commander_id UUID NOT NULL REFERENCES commanders(id),

    -- Relative outcome
    won_against BOOLEAN NOT NULL,          -- Did this commander beat the opponent?

    -- Context
    commander_seat INTEGER NOT NULL,       -- Seat position of this commander
    opponent_seat INTEGER NOT NULL,        -- Seat position of opponent

    -- Denormalized for query efficiency
    tournament_id UUID NOT NULL REFERENCES tournaments(id),
    round_number INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_matchups_commander ON commander_matchups(commander_id);
CREATE INDEX idx_matchups_opponent ON commander_matchups(opponent_commander_id);
CREATE INDEX idx_matchups_pair ON commander_matchups(commander_id, opponent_commander_id);

-- ============================================================================
-- ANALYTICAL VIEWS
-- ============================================================================

-- View: Commander performance summary
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
GROUP BY c.id, c.name, c.archetype, c.color_identity;

-- View: Seat position win rates
CREATE OR REPLACE VIEW seat_position_stats AS
SELECT
    gp.seat_position,
    COUNT(*) AS total_games,
    COUNT(*) FILTER (WHERE gp.result = 'win') AS wins,
    COUNT(*) FILTER (WHERE gp.result = 'loss') AS losses,
    COUNT(*) FILTER (WHERE gp.result = 'draw') AS draws,
    ROUND(
        COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0),
        4
    ) AS win_rate
FROM game_participants gp
JOIN games g ON gp.game_id = g.id
WHERE g.status = 'Completed' AND gp.result != 'bye'
GROUP BY gp.seat_position
ORDER BY gp.seat_position;

-- View: Win rate by round (survival analysis proxy)
CREATE OR REPLACE VIEW round_win_rates AS
SELECT
    g.round_number,
    g.is_bracket,
    COUNT(*) AS total_games,
    COUNT(*) FILTER (WHERE gp.result = 'win') AS wins,
    ROUND(
        COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0) / 4, -- Divide by 4 for 4-player pods
        4
    ) AS expected_win_rate,
    ROUND(
        COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0),
        4
    ) AS actual_participation_win_rate
FROM games g
JOIN game_participants gp ON g.id = gp.game_id
WHERE g.status = 'Completed'
GROUP BY g.round_number, g.is_bracket
ORDER BY g.is_bracket, g.round_number;

-- View: Commander head-to-head matchups
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
GROUP BY c1.name, c2.name
HAVING COUNT(*) >= 5  -- Minimum sample size
ORDER BY games_together DESC;

-- ============================================================================
-- SCRYFALL CARD CACHE (for future card-level analysis)
-- ============================================================================

CREATE TABLE scryfall_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scryfall_id TEXT UNIQUE NOT NULL,      -- Scryfall's oracle_id or id
    name TEXT NOT NULL,
    oracle_text TEXT,
    mana_cost TEXT,
    cmc NUMERIC(4, 1),
    type_line TEXT,
    colors TEXT[],
    color_identity TEXT[],
    keywords TEXT[],
    legalities JSONB,
    image_uris JSONB,
    prices JSONB,
    released_at DATE,
    set_code TEXT,
    rarity TEXT,

    -- Timestamps
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scryfall_name ON scryfall_cards(name);
CREATE INDEX idx_scryfall_colors ON scryfall_cards USING GIN(color_identity);

-- ============================================================================
-- ROW-LEVEL SECURITY (for Supabase)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE commanders ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE tournaments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tournament_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE games ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE commander_matchups ENABLE ROW LEVEL SECURITY;
ALTER TABLE scryfall_cards ENABLE ROW LEVEL SECURITY;

-- Public read access policies (data is public, writes are restricted)
CREATE POLICY "Public read access" ON commanders FOR SELECT USING (true);
CREATE POLICY "Public read access" ON players FOR SELECT USING (true);
CREATE POLICY "Public read access" ON tournaments FOR SELECT USING (true);
CREATE POLICY "Public read access" ON tournament_entries FOR SELECT USING (true);
CREATE POLICY "Public read access" ON games FOR SELECT USING (true);
CREATE POLICY "Public read access" ON game_participants FOR SELECT USING (true);
CREATE POLICY "Public read access" ON commander_matchups FOR SELECT USING (true);
CREATE POLICY "Public read access" ON scryfall_cards FOR SELECT USING (true);

-- ============================================================================
-- FUNCTIONS FOR ANALYTICS
-- ============================================================================

-- Function: Calculate conversion score (similar to cedh.io)
-- Score of 100 = expected performance, >100 = outperforming, <100 = underperforming
CREATE OR REPLACE FUNCTION calculate_conversion_score(
    entries INTEGER,
    top_cuts INTEGER,
    expected_probability NUMERIC
) RETURNS NUMERIC AS $$
BEGIN
    IF entries = 0 OR expected_probability = 0 THEN
        RETURN NULL;
    END IF;

    RETURN ROUND(
        (top_cuts::NUMERIC / (entries * expected_probability)) * 100,
        1
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function: Get commander win rate by round
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
    WHERE te.commander_id = commander_uuid
      AND g.status = 'Completed'
      AND NOT g.is_bracket
    GROUP BY g.round_number
    ORDER BY g.round_number;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Trigger function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER update_commanders_timestamp
    BEFORE UPDATE ON commanders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_players_timestamp
    BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_tournaments_timestamp
    BEFORE UPDATE ON tournaments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
