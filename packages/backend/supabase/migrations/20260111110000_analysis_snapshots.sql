-- Analysis Snapshots: Store versioned analytical insights
-- Enables temporal queries like "How did Kraum perform in Q4 vs Q3?"

CREATE TABLE analysis_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Classification
    report_type TEXT NOT NULL,              -- 'commander_survival', 'seat_position', 'meta_momentum'
    entity_type TEXT,                       -- 'commander', 'player', 'global'
    entity_id UUID,                         -- Reference to commander/player if applicable
    entity_name TEXT,                       -- Denormalized for easy querying

    -- Temporal context
    meta_period TEXT NOT NULL,              -- '2025-01', '2025-Q1', '2025-W02'
    data_start_date TIMESTAMPTZ,            -- First tournament included
    data_end_date TIMESTAMPTZ,              -- Last tournament included
    tournaments_included INTEGER,
    games_analyzed INTEGER,

    -- The analysis
    metrics JSONB NOT NULL,                 -- Key metrics (win_rate, conversion_rate, etc.)
    insights JSONB,                         -- Derived insights (trends, comparisons)
    summary TEXT,                           -- Human-readable summary

    -- Versioning
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    generator_version TEXT DEFAULT '1.0',   -- Code version that produced this
    is_latest BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(report_type, entity_type, entity_id, meta_period)
);

-- Indexes for common queries
CREATE INDEX idx_snapshots_type ON analysis_snapshots(report_type);
CREATE INDEX idx_snapshots_entity ON analysis_snapshots(entity_type, entity_name);
CREATE INDEX idx_snapshots_period ON analysis_snapshots(meta_period DESC);
CREATE INDEX idx_snapshots_latest ON analysis_snapshots(report_type, entity_type) WHERE is_latest;
CREATE INDEX idx_snapshots_metrics ON analysis_snapshots USING GIN(metrics);

-- RLS
ALTER TABLE analysis_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON analysis_snapshots FOR SELECT USING (true);

-- Helper view: Latest snapshots only
CREATE OR REPLACE VIEW latest_analysis AS
SELECT * FROM analysis_snapshots WHERE is_latest = true;

-- Example queries this enables:
--
-- Get latest commander survival stats:
--   SELECT * FROM latest_analysis
--   WHERE report_type = 'commander_survival' AND entity_name ILIKE '%Kinnan%';
--
-- Compare commander across periods:
--   SELECT meta_period, metrics->>'win_rate', metrics->>'top_16_rate'
--   FROM analysis_snapshots
--   WHERE entity_name = 'Kinnan, Bonder Prodigy'
--   ORDER BY meta_period;
--
-- Find commanders with improving win rates:
--   WITH current AS (
--     SELECT entity_name, (metrics->>'win_rate')::numeric as wr
--     FROM analysis_snapshots WHERE meta_period = '2025-01' AND report_type = 'commander_survival'
--   ),
--   previous AS (
--     SELECT entity_name, (metrics->>'win_rate')::numeric as wr
--     FROM analysis_snapshots WHERE meta_period = '2024-12' AND report_type = 'commander_survival'
--   )
--   SELECT c.entity_name, c.wr - p.wr as improvement
--   FROM current c JOIN previous p ON c.entity_name = p.entity_name
--   WHERE c.wr > p.wr ORDER BY improvement DESC;
