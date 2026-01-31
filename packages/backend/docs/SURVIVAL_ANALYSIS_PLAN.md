# Survival Analysis for cEDH Tournament Data

**Date:** 2026-01-21
**Status:** Research Complete, Ready for Implementation
**Domain:** Statistical Survival Analysis, PostgreSQL, React/Recharts Visualization

---

## Executive Summary

This document outlines the implementation plan for survival analysis features in the cEDH Analytics platform. The goal is to provide round-by-round survival curves showing how different commanders perform as tournaments progress, enabling players to understand:

1. **Survival Curves**: Probability of still being "alive" (having a chance at top cut) at each round
2. **Time to Elimination**: How long commanders typically survive before being mathematically eliminated
3. **Kaplan-Meier Comparisons**: Visual comparison of top commanders' tournament longevity
4. **Hazard Rates**: Risk of elimination at each specific round

### Key Insight: Adapting Medical Survival Analysis to Tournaments

Traditional Kaplan-Meier analysis tracks "time to death" with censored observations. In cEDH tournaments:
- **Event**: Elimination from top-cut contention (accumulating too many losses)
- **Survival**: Still mathematically able to make top cut
- **Censoring**: Tournament ends before elimination (player makes top cut or tournament concludes)
- **Time**: Round number (discrete, not continuous)

---

## Data Model Context

### Existing Tables

```sql
-- Core tables already in schema.sql
games (id, tournament_id, round_number, is_bracket, winner_id)
game_participants (id, game_id, entry_id, seat_position, result)
tournament_entries (id, tournament_id, player_id, commander_id, final_standing, wins, losses)
tournaments (id, swiss_rounds, top_cut, player_count)
commanders (id, name, archetype)
```

### Key Relationships

```
tournament_entries
    -> commander_id -> commanders
    -> tournament_id -> tournaments (swiss_rounds, top_cut)
    -> entry_id <- game_participants -> games (round_number, is_bracket)
```

---

## Proposed SQL Views

### View 1: Entry Round History (Foundation Table)

This view creates the base data structure showing each entry's cumulative record after each round.

```sql
-- Foundation: Track each entry's cumulative record by round
CREATE MATERIALIZED VIEW entry_round_history AS
WITH round_results AS (
    SELECT
        gp.entry_id,
        g.tournament_id,
        g.round_number,
        g.is_bracket,
        gp.result,
        te.commander_id,
        t.swiss_rounds,
        t.top_cut,
        t.player_count
    FROM game_participants gp
    JOIN games g ON gp.game_id = g.id
    JOIN tournament_entries te ON gp.entry_id = te.id
    JOIN tournaments t ON g.tournament_id = t.id
    WHERE g.status = 'Completed'
      AND NOT g.is_bracket  -- Swiss rounds only for survival analysis
),
cumulative_stats AS (
    SELECT
        entry_id,
        tournament_id,
        commander_id,
        round_number,
        swiss_rounds,
        top_cut,
        player_count,
        -- Current round result
        result,
        -- Cumulative wins up to and including this round
        SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END)
            OVER (PARTITION BY entry_id ORDER BY round_number
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_wins,
        -- Cumulative losses
        SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END)
            OVER (PARTITION BY entry_id ORDER BY round_number
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_losses,
        -- Cumulative draws
        SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END)
            OVER (PARTITION BY entry_id ORDER BY round_number
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_draws
    FROM round_results
)
SELECT
    entry_id,
    tournament_id,
    commander_id,
    round_number,
    swiss_rounds,
    top_cut,
    player_count,
    result,
    cum_wins,
    cum_losses,
    cum_draws,
    -- Calculate if still alive for top cut
    -- Simplified: eliminated if losses > (swiss_rounds - top_cut_threshold)
    -- More sophisticated: based on tiebreakers and standings
    CASE
        WHEN cum_losses > (swiss_rounds - CEIL(LOG(2, GREATEST(top_cut, 1)))) THEN FALSE
        ELSE TRUE
    END AS still_alive
FROM cumulative_stats;

CREATE INDEX idx_erh_commander ON entry_round_history(commander_id);
CREATE INDEX idx_erh_round ON entry_round_history(round_number);
CREATE INDEX idx_erh_tournament ON entry_round_history(tournament_id);
```

### View 2: Commander Survival by Round (Kaplan-Meier Data)

This view computes the survival statistics needed for Kaplan-Meier curves.

```sql
-- Kaplan-Meier survival data by commander
CREATE MATERIALIZED VIEW commander_survival_by_round AS
WITH survival_events AS (
    -- For each commander, at each round, count:
    -- - at_risk: entries that were still alive entering this round
    -- - events: entries that got eliminated this round
    -- - censored: entries that survived but tournament ended
    SELECT
        erh.commander_id,
        erh.round_number,
        -- At risk at START of round (alive entering this round)
        COUNT(DISTINCT erh.entry_id) FILTER (
            WHERE erh.still_alive OR erh.round_number = (
                SELECT MAX(round_number)
                FROM entry_round_history erh2
                WHERE erh2.entry_id = erh.entry_id
            )
        ) AS at_risk,
        -- Events: eliminated THIS round (was alive, now not)
        COUNT(DISTINCT erh.entry_id) FILTER (
            WHERE NOT erh.still_alive
              AND LAG(erh.still_alive, 1, TRUE) OVER (
                  PARTITION BY erh.entry_id ORDER BY erh.round_number
              ) = TRUE
        ) AS events,
        -- Total entries for this commander
        COUNT(DISTINCT erh.entry_id) AS total_entries
    FROM entry_round_history erh
    GROUP BY erh.commander_id, erh.round_number
),
-- Calculate at_risk more accurately
at_risk_calc AS (
    SELECT
        commander_id,
        round_number,
        -- Count entries still in contention at round start
        (SELECT COUNT(DISTINCT e2.entry_id)
         FROM entry_round_history e2
         WHERE e2.commander_id = se.commander_id
           AND e2.round_number = se.round_number - 1
           AND e2.still_alive = TRUE) AS at_risk_start,
        -- Count eliminations this round
        (SELECT COUNT(DISTINCT e3.entry_id)
         FROM entry_round_history e3
         WHERE e3.commander_id = se.commander_id
           AND e3.round_number = se.round_number
           AND e3.still_alive = FALSE
           AND EXISTS (
               SELECT 1 FROM entry_round_history e4
               WHERE e4.entry_id = e3.entry_id
                 AND e4.round_number = se.round_number - 1
                 AND e4.still_alive = TRUE
           )) AS events,
        total_entries
    FROM survival_events se
),
-- First round: all entries start "at risk"
round_one_entries AS (
    SELECT
        commander_id,
        COUNT(DISTINCT entry_id) AS total_at_round_1
    FROM entry_round_history
    WHERE round_number = 1
    GROUP BY commander_id
)
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    c.archetype,
    COALESCE(arc.round_number, 1) AS round_number,
    COALESCE(
        CASE WHEN arc.round_number = 1 THEN r1.total_at_round_1
             ELSE arc.at_risk_start
        END,
        r1.total_at_round_1
    ) AS at_risk,
    COALESCE(arc.events, 0) AS events,
    r1.total_at_round_1 AS total_entries,
    -- Conditional survival probability for this round
    CASE
        WHEN COALESCE(arc.at_risk_start, r1.total_at_round_1) > 0
        THEN ROUND(
            1 - (COALESCE(arc.events, 0)::NUMERIC /
                 COALESCE(arc.at_risk_start, r1.total_at_round_1)),
            4
        )
        ELSE 1.0
    END AS conditional_survival_prob
FROM commanders c
LEFT JOIN at_risk_calc arc ON c.id = arc.commander_id
LEFT JOIN round_one_entries r1 ON c.id = r1.commander_id
WHERE r1.total_at_round_1 >= 20  -- Minimum sample size
ORDER BY c.name, COALESCE(arc.round_number, 1);

CREATE INDEX idx_csb_commander ON commander_survival_by_round(commander_id);
CREATE INDEX idx_csb_round ON commander_survival_by_round(round_number);
```

### View 3: Kaplan-Meier Survival Curve (Cumulative)

Computes the actual Kaplan-Meier survival probability using the product-limit estimator.

```sql
-- Kaplan-Meier cumulative survival curve
CREATE MATERIALIZED VIEW commander_kaplan_meier AS
WITH km_base AS (
    SELECT
        commander_id,
        commander_name,
        archetype,
        round_number,
        at_risk,
        events,
        total_entries,
        conditional_survival_prob,
        -- Kaplan-Meier: S(t) = product of (1 - d_i/n_i) for all i <= t
        -- Implemented as exp(sum(log(...))) since Postgres lacks product()
        EXP(
            SUM(LN(NULLIF(conditional_survival_prob, 0)))
            OVER (
                PARTITION BY commander_id
                ORDER BY round_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS survival_probability
    FROM commander_survival_by_round
    WHERE conditional_survival_prob > 0
),
-- Greenwood variance for confidence intervals
greenwood AS (
    SELECT
        commander_id,
        round_number,
        survival_probability,
        -- Greenwood sum: sum of d_i / (n_i * (n_i - d_i))
        SUM(
            CASE
                WHEN at_risk > events AND at_risk > 0
                THEN events::NUMERIC / (at_risk * (at_risk - events))
                ELSE 0
            END
        ) OVER (
            PARTITION BY commander_id
            ORDER BY round_number
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS greenwood_sum
    FROM km_base
)
SELECT
    km.commander_id,
    km.commander_name,
    km.archetype,
    km.round_number,
    km.at_risk,
    km.events,
    km.total_entries,
    ROUND(km.survival_probability, 4) AS survival_probability,
    -- Standard error using Greenwood formula
    ROUND(
        km.survival_probability * SQRT(COALESCE(g.greenwood_sum, 0)),
        4
    ) AS std_error,
    -- 95% confidence interval (plain method)
    GREATEST(0, ROUND(
        km.survival_probability - 1.96 * km.survival_probability * SQRT(COALESCE(g.greenwood_sum, 0)),
        4
    )) AS ci_lower_95,
    LEAST(1, ROUND(
        km.survival_probability + 1.96 * km.survival_probability * SQRT(COALESCE(g.greenwood_sum, 0)),
        4
    )) AS ci_upper_95,
    -- Nelson-Aalen cumulative hazard
    ROUND(
        SUM(
            CASE WHEN km.at_risk > 0
                 THEN km.events::NUMERIC / km.at_risk
                 ELSE 0
            END
        ) OVER (
            PARTITION BY km.commander_id
            ORDER BY km.round_number
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        4
    ) AS cumulative_hazard
FROM km_base km
LEFT JOIN greenwood g ON km.commander_id = g.commander_id
                     AND km.round_number = g.round_number;

CREATE INDEX idx_ckm_commander ON commander_kaplan_meier(commander_id);
CREATE INDEX idx_ckm_round ON commander_kaplan_meier(round_number);
```

### View 4: Hazard Rate by Round

Shows the instantaneous risk of elimination at each round.

```sql
-- Hazard rate by round for each commander
CREATE MATERIALIZED VIEW commander_hazard_rates AS
SELECT
    commander_id,
    commander_name,
    archetype,
    round_number,
    at_risk,
    events,
    -- Hazard rate: h(t) = d_t / n_t (events at time t / at risk at time t)
    CASE
        WHEN at_risk > 0
        THEN ROUND(events::NUMERIC / at_risk, 4)
        ELSE 0
    END AS hazard_rate,
    -- Expressed as percentage for readability
    CASE
        WHEN at_risk > 0
        THEN ROUND(events::NUMERIC / at_risk * 100, 2)
        ELSE 0
    END AS hazard_rate_pct,
    survival_probability,
    cumulative_hazard
FROM commander_kaplan_meier
ORDER BY commander_name, round_number;

CREATE INDEX idx_chr_commander ON commander_hazard_rates(commander_id);
```

### View 5: Global Survival Comparison (All Commanders)

For comparing multiple commanders on the same chart.

```sql
-- Global survival comparison data
CREATE MATERIALIZED VIEW survival_comparison AS
SELECT
    ckm.commander_id,
    ckm.commander_name,
    ckm.archetype,
    ckm.round_number,
    ckm.survival_probability,
    ckm.ci_lower_95,
    ckm.ci_upper_95,
    ckm.total_entries,
    -- Rank commanders by median survival
    DENSE_RANK() OVER (
        ORDER BY
            AVG(ckm.survival_probability) FILTER (WHERE ckm.round_number <= 4) DESC
    ) AS early_survival_rank,
    -- Category based on archetype
    COALESCE(ckm.archetype, 'unknown') AS strategy_type
FROM commander_kaplan_meier ckm
WHERE ckm.total_entries >= 30  -- Higher threshold for comparison
ORDER BY ckm.commander_name, ckm.round_number;

CREATE INDEX idx_sc_round ON survival_comparison(round_number);
CREATE INDEX idx_sc_archetype ON survival_comparison(archetype);
```

---

## Simplified Alternative: Loss-Based Elimination

If the above views prove too complex, here's a simpler approach tracking elimination by loss count:

```sql
-- Simpler survival: probability of having X or fewer losses by round Y
CREATE MATERIALIZED VIEW commander_loss_survival AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    erh.round_number,
    COUNT(DISTINCT erh.entry_id) AS total_entries,
    -- Entries with 0 losses
    COUNT(DISTINCT erh.entry_id) FILTER (WHERE erh.cum_losses = 0) AS zero_loss_count,
    ROUND(
        COUNT(DISTINCT erh.entry_id) FILTER (WHERE erh.cum_losses = 0)::NUMERIC /
        NULLIF(COUNT(DISTINCT erh.entry_id), 0),
        4
    ) AS zero_loss_rate,
    -- Entries with 1 or fewer losses
    COUNT(DISTINCT erh.entry_id) FILTER (WHERE erh.cum_losses <= 1) AS one_or_fewer_losses,
    ROUND(
        COUNT(DISTINCT erh.entry_id) FILTER (WHERE erh.cum_losses <= 1)::NUMERIC /
        NULLIF(COUNT(DISTINCT erh.entry_id), 0),
        4
    ) AS one_loss_survival_rate,
    -- Entries with 2 or fewer losses
    COUNT(DISTINCT erh.entry_id) FILTER (WHERE erh.cum_losses <= 2) AS two_or_fewer_losses,
    ROUND(
        COUNT(DISTINCT erh.entry_id) FILTER (WHERE erh.cum_losses <= 2)::NUMERIC /
        NULLIF(COUNT(DISTINCT erh.entry_id), 0),
        4
    ) AS two_loss_survival_rate
FROM entry_round_history erh
JOIN commanders c ON erh.commander_id = c.id
GROUP BY c.id, c.name, erh.round_number
HAVING COUNT(DISTINCT erh.entry_id) >= 20
ORDER BY c.name, erh.round_number;
```

---

## Frontend Visualization

### Technology Stack

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Charts | Recharts | 3.6.0+ | Already in package.json |
| Step Lines | `type="stepAfter"` | - | Kaplan-Meier step function |
| Confidence Intervals | `Area` component | - | Shaded CI bands |
| Tooltips | `Tooltip` component | - | Interactive data display |

### Recharts Implementation Pattern

```tsx
// src/components/SurvivalCurve.tsx
import {
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

interface SurvivalDataPoint {
  round: number;
  survival: number;
  ci_lower: number;
  ci_upper: number;
  at_risk: number;
  events: number;
}

interface CommanderSurvival {
  commander_id: string;
  commander_name: string;
  archetype: string;
  data: SurvivalDataPoint[];
  color: string;
}

interface SurvivalCurveProps {
  commanders: CommanderSurvival[];
  showConfidenceIntervals?: boolean;
  yAxisMin?: number;
}

export function SurvivalCurve({
  commanders,
  showConfidenceIntervals = true,
  yAxisMin = 0
}: SurvivalCurveProps) {
  // Transform data for Recharts
  const chartData = useMemo(() => {
    const rounds = new Set<number>();
    commanders.forEach(cmd => cmd.data.forEach(d => rounds.add(d.round)));

    return Array.from(rounds).sort((a, b) => a - b).map(round => {
      const point: Record<string, number | string> = { round };
      commanders.forEach(cmd => {
        const dataPoint = cmd.data.find(d => d.round === round);
        if (dataPoint) {
          point[`${cmd.commander_id}_survival`] = dataPoint.survival;
          point[`${cmd.commander_id}_ci_lower`] = dataPoint.ci_lower;
          point[`${cmd.commander_id}_ci_upper`] = dataPoint.ci_upper;
          point[`${cmd.commander_id}_at_risk`] = dataPoint.at_risk;
        }
      });
      return point;
    });
  }, [commanders]);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis
          dataKey="round"
          label={{ value: 'Round', position: 'insideBottom', offset: -10 }}
          stroke="#888"
        />
        <YAxis
          domain={[yAxisMin, 1]}
          tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
          label={{ value: 'Survival Probability', angle: -90, position: 'insideLeft' }}
          stroke="#888"
        />
        <Tooltip
          content={<CustomSurvivalTooltip commanders={commanders} />}
        />
        <Legend />

        {/* Reference line at 50% survival */}
        <ReferenceLine
          y={0.5}
          stroke="#666"
          strokeDasharray="5 5"
          label="50%"
        />

        {commanders.map((cmd) => (
          <React.Fragment key={cmd.commander_id}>
            {/* Confidence interval area */}
            {showConfidenceIntervals && (
              <Area
                dataKey={`${cmd.commander_id}_ci_upper`}
                stroke="none"
                fill={cmd.color}
                fillOpacity={0.1}
                type="stepAfter"
                baseValue="dataMin"
                // Note: This is simplified; proper CI bands need custom rendering
              />
            )}

            {/* Main survival line */}
            <Line
              type="stepAfter"
              dataKey={`${cmd.commander_id}_survival`}
              name={cmd.commander_name}
              stroke={cmd.color}
              strokeWidth={2}
              dot={{ r: 3, fill: cmd.color }}
              activeDot={{ r: 5, strokeWidth: 2 }}
            />
          </React.Fragment>
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// Custom tooltip for survival data
function CustomSurvivalTooltip({
  active,
  payload,
  label,
  commanders
}: any) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
      <p className="font-semibold text-white mb-2">Round {label}</p>
      {commanders.map((cmd: CommanderSurvival) => {
        const data = payload.find((p: any) =>
          p.dataKey === `${cmd.commander_id}_survival`
        );
        if (!data) return null;

        const atRisk = payload.find((p: any) =>
          p.dataKey === `${cmd.commander_id}_at_risk`
        )?.value;

        return (
          <div key={cmd.commander_id} className="mb-1">
            <span
              className="inline-block w-3 h-3 rounded-full mr-2"
              style={{ backgroundColor: cmd.color }}
            />
            <span className="text-gray-300">{cmd.commander_name}: </span>
            <span className="text-white font-medium">
              {(data.value * 100).toFixed(1)}%
            </span>
            {atRisk && (
              <span className="text-gray-500 text-sm ml-2">
                (n={atRisk})
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

### Hazard Rate Visualization

```tsx
// src/components/HazardRateChart.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface HazardDataPoint {
  round: number;
  hazard_rate: number;
  at_risk: number;
  events: number;
}

interface HazardRateChartProps {
  data: HazardDataPoint[];
  commanderName: string;
}

export function HazardRateChart({ data, commanderName }: HazardRateChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis
          dataKey="round"
          label={{ value: 'Round', position: 'insideBottom', offset: -5 }}
        />
        <YAxis
          tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
          label={{ value: 'Hazard Rate', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip
          formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'Risk']}
          labelFormatter={(label) => `Round ${label}`}
        />
        <Bar
          dataKey="hazard_rate"
          fill="#ef4444"
          name={`${commanderName} Elimination Risk`}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

### Color Palette for Commander Comparison

```typescript
// src/lib/colors.ts
export const COMMANDER_COLORS = {
  // By archetype
  turbo: '#3b82f6',     // Blue
  midrange: '#22c55e',  // Green
  stax: '#ef4444',      // Red
  adaptive: '#a855f7',  // Purple
  combo: '#f97316',     // Orange
  control: '#06b6d4',   // Cyan

  // Fallback palette for multiple commanders
  palette: [
    '#3b82f6', '#22c55e', '#ef4444', '#f59e0b', '#a855f7',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
  ]
};

export function getCommanderColor(index: number, archetype?: string): string {
  if (archetype && COMMANDER_COLORS[archetype as keyof typeof COMMANDER_COLORS]) {
    return COMMANDER_COLORS[archetype as keyof typeof COMMANDER_COLORS] as string;
  }
  return COMMANDER_COLORS.palette[index % COMMANDER_COLORS.palette.length];
}
```

---

## API Endpoints

### Supabase RPC Functions

```sql
-- Get survival curve for a single commander
CREATE OR REPLACE FUNCTION get_commander_survival(commander_uuid UUID)
RETURNS TABLE (
    round_number INTEGER,
    at_risk BIGINT,
    events BIGINT,
    survival_probability NUMERIC,
    ci_lower_95 NUMERIC,
    ci_upper_95 NUMERIC,
    cumulative_hazard NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ckm.round_number,
        ckm.at_risk,
        ckm.events,
        ckm.survival_probability,
        ckm.ci_lower_95,
        ckm.ci_upper_95,
        ckm.cumulative_hazard
    FROM commander_kaplan_meier ckm
    WHERE ckm.commander_id = commander_uuid
    ORDER BY ckm.round_number;
END;
$$ LANGUAGE plpgsql STABLE;

-- Get hazard rates for a commander
CREATE OR REPLACE FUNCTION get_commander_hazard(commander_uuid UUID)
RETURNS TABLE (
    round_number INTEGER,
    hazard_rate NUMERIC,
    hazard_rate_pct NUMERIC,
    at_risk BIGINT,
    events BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        chr.round_number,
        chr.hazard_rate,
        chr.hazard_rate_pct,
        chr.at_risk,
        chr.events
    FROM commander_hazard_rates chr
    WHERE chr.commander_id = commander_uuid
    ORDER BY chr.round_number;
END;
$$ LANGUAGE plpgsql STABLE;

-- Compare multiple commanders
CREATE OR REPLACE FUNCTION compare_commander_survival(commander_uuids UUID[])
RETURNS TABLE (
    commander_id UUID,
    commander_name TEXT,
    archetype TEXT,
    round_number INTEGER,
    survival_probability NUMERIC,
    ci_lower_95 NUMERIC,
    ci_upper_95 NUMERIC,
    total_entries BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sc.commander_id,
        sc.commander_name,
        sc.archetype,
        sc.round_number,
        sc.survival_probability,
        sc.ci_lower_95,
        sc.ci_upper_95,
        sc.total_entries
    FROM survival_comparison sc
    WHERE sc.commander_id = ANY(commander_uuids)
    ORDER BY sc.commander_name, sc.round_number;
END;
$$ LANGUAGE plpgsql STABLE;
```

### Frontend API Layer

```typescript
// src/lib/api/survival.ts
import { supabase } from '@/lib/supabase';

export interface SurvivalPoint {
  round_number: number;
  at_risk: number;
  events: number;
  survival_probability: number;
  ci_lower_95: number;
  ci_upper_95: number;
  cumulative_hazard: number;
}

export interface HazardPoint {
  round_number: number;
  hazard_rate: number;
  hazard_rate_pct: number;
  at_risk: number;
  events: number;
}

export async function getCommanderSurvival(commanderId: string): Promise<SurvivalPoint[]> {
  const { data, error } = await supabase
    .rpc('get_commander_survival', { commander_uuid: commanderId });

  if (error) throw error;
  return data ?? [];
}

export async function getCommanderHazard(commanderId: string): Promise<HazardPoint[]> {
  const { data, error } = await supabase
    .rpc('get_commander_hazard', { commander_uuid: commanderId });

  if (error) throw error;
  return data ?? [];
}

export async function compareCommanderSurvival(commanderIds: string[]): Promise<any[]> {
  const { data, error } = await supabase
    .rpc('compare_commander_survival', { commander_uuids: commanderIds });

  if (error) throw error;
  return data ?? [];
}

// Direct view queries (alternative to RPC)
export async function getSurvivalComparison(minEntries: number = 30) {
  const { data, error } = await supabase
    .from('survival_comparison')
    .select('*')
    .gte('total_entries', minEntries)
    .order('commander_name')
    .order('round_number');

  if (error) throw error;
  return data ?? [];
}
```

---

## Migration Files

### Migration 1: Foundation Tables

**File:** `supabase/migrations/20260121000001_survival_foundation.sql`

```sql
-- Enable required extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Foundation view for survival analysis
CREATE MATERIALIZED VIEW IF NOT EXISTS entry_round_history AS
-- [Insert full SQL from View 1 above]
;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_erh_commander ON entry_round_history(commander_id);
CREATE INDEX IF NOT EXISTS idx_erh_round ON entry_round_history(round_number);
CREATE INDEX IF NOT EXISTS idx_erh_tournament ON entry_round_history(tournament_id);

-- Grant read access
GRANT SELECT ON entry_round_history TO anon, authenticated;
```

### Migration 2: Kaplan-Meier Views

**File:** `supabase/migrations/20260121000002_kaplan_meier_views.sql`

```sql
-- Commander survival by round
CREATE MATERIALIZED VIEW IF NOT EXISTS commander_survival_by_round AS
-- [Insert full SQL from View 2 above]
;

-- Kaplan-Meier cumulative survival
CREATE MATERIALIZED VIEW IF NOT EXISTS commander_kaplan_meier AS
-- [Insert full SQL from View 3 above]
;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_csb_commander ON commander_survival_by_round(commander_id);
CREATE INDEX IF NOT EXISTS idx_ckm_commander ON commander_kaplan_meier(commander_id);
CREATE INDEX IF NOT EXISTS idx_ckm_round ON commander_kaplan_meier(round_number);

-- Grant access
GRANT SELECT ON commander_survival_by_round TO anon, authenticated;
GRANT SELECT ON commander_kaplan_meier TO anon, authenticated;
```

### Migration 3: Hazard and Comparison Views

**File:** `supabase/migrations/20260121000003_survival_analysis_complete.sql`

```sql
-- Hazard rates
CREATE MATERIALIZED VIEW IF NOT EXISTS commander_hazard_rates AS
-- [Insert full SQL from View 4 above]
;

-- Comparison view
CREATE MATERIALIZED VIEW IF NOT EXISTS survival_comparison AS
-- [Insert full SQL from View 5 above]
;

-- RPC Functions
CREATE OR REPLACE FUNCTION get_commander_survival(commander_uuid UUID)
-- [Insert full SQL from RPC section above]
;

CREATE OR REPLACE FUNCTION get_commander_hazard(commander_uuid UUID)
-- [Insert full SQL from RPC section above]
;

CREATE OR REPLACE FUNCTION compare_commander_survival(commander_uuids UUID[])
-- [Insert full SQL from RPC section above]
;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chr_commander ON commander_hazard_rates(commander_id);
CREATE INDEX IF NOT EXISTS idx_sc_round ON survival_comparison(round_number);
CREATE INDEX IF NOT EXISTS idx_sc_archetype ON survival_comparison(archetype);

-- Grant access
GRANT SELECT ON commander_hazard_rates TO anon, authenticated;
GRANT SELECT ON survival_comparison TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_commander_survival TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_commander_hazard TO anon, authenticated;
GRANT EXECUTE ON FUNCTION compare_commander_survival TO anon, authenticated;
```

### Migration 4: Refresh Function

**File:** `supabase/migrations/20260121000004_survival_refresh.sql`

```sql
-- Function to refresh all survival views in correct order
CREATE OR REPLACE FUNCTION refresh_survival_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW entry_round_history;
    REFRESH MATERIALIZED VIEW commander_survival_by_round;
    REFRESH MATERIALIZED VIEW commander_kaplan_meier;
    REFRESH MATERIALIZED VIEW commander_hazard_rates;
    REFRESH MATERIALIZED VIEW survival_comparison;
END;
$$ LANGUAGE plpgsql;

-- Grant execute
GRANT EXECUTE ON FUNCTION refresh_survival_views TO service_role;
```

---

## Implementation Steps

### Phase 1: Database Setup (Backend)

1. **Create foundation view** (`entry_round_history`)
   - Test with sample data
   - Verify cumulative calculations
   - Validate `still_alive` logic

2. **Create Kaplan-Meier views**
   - Start with `commander_survival_by_round`
   - Add `commander_kaplan_meier`
   - Validate against expected values

3. **Add hazard and comparison views**
   - Create `commander_hazard_rates`
   - Create `survival_comparison`
   - Test RPC functions

4. **Performance optimization**
   - Index tuning based on query patterns
   - Refresh scheduling

### Phase 2: Frontend Components

1. **Create `SurvivalCurve` component**
   - Single commander view
   - Multi-commander comparison
   - Confidence intervals (optional)

2. **Create `HazardRateChart` component**
   - Bar chart for hazard by round
   - Tooltip with context

3. **Create `/survival` page**
   - Commander selector
   - Comparison mode (up to 5 commanders)
   - Archetype filter

4. **Integrate with commander detail page**
   - Add survival tab to `/commanders/[id]`
   - Show hazard rates

### Phase 3: Polish and Documentation

1. **Add loading states and error handling**
2. **Create tooltips explaining survival analysis**
3. **Add export functionality (CSV/PNG)**
4. **Document API endpoints**

---

## Statistical Notes

### Kaplan-Meier Assumptions

1. **Censoring is non-informative**: Players who don't get eliminated (make top cut) are censored, not "different"
2. **Survival probabilities are the same for early and late entrants**: All tournaments are comparable
3. **Events happen at specified times**: Round numbers are discrete and known

### Limitations

1. **Not true time-to-event**: Rounds are discrete, not continuous
2. **Competing risks**: Players can be eliminated by multiple mechanisms (losses, drops)
3. **Variable tournament sizes**: Different tournaments have different numbers of rounds
4. **Sample size**: Need 20+ entries per commander for reliable estimates

### Future Enhancements

1. **Log-rank test**: Statistically compare survival curves between commanders
2. **Cox proportional hazards**: Model factors affecting survival (seat position, archetype)
3. **Stratified analysis**: Survival by tournament size, time period, or region

---

## References

### Primary Sources (HIGH Confidence)

- [Crosstab.io - Computing Kaplan-Meier Survival Curves in SQL](https://www.crosstab.io/articles/sql-survival-curves/)
- [Recharts API Documentation](https://recharts.github.io/en-US/api/Line/)
- [Eureka Statistics - Kaplan Meier SQL Server Implementation](https://eurekastatistics.com/calculating-kaplan-meier-survival-curves-and-their-confidence-intervals-in-sql-server/)

### Statistical References (HIGH Confidence)

- [Greenwood's Formula - Stanford University](https://web.stanford.edu/~lutian/coursepdf/unit5.pdf)
- [Kaplan-Meier Estimator - Wikipedia](https://en.wikipedia.org/wiki/Kaplan%E2%80%93Meier_estimator)
- [Log-Rank Test - Penn State STAT 509](https://online.stat.psu.edu/stat509/lesson/11/11.7)

### Tournament Format References (MEDIUM Confidence)

- [Swiss-system tournament - Wikipedia](https://en.wikipedia.org/wiki/Swiss-system_tournament)
- [MTR Appendix E - Recommended Rounds](https://blogs.magicjudges.org/rules/mtr-appendix-e/)

### Visualization References (MEDIUM Confidence)

- [LogRocket - Best React Chart Libraries 2025](https://blog.logrocket.com/best-react-chart-libraries-2025/)
- [Recharts GitHub](https://github.com/recharts/recharts)

---

## Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| SQL View Design | HIGH | Based on official PostgreSQL documentation and verified SQL patterns |
| Kaplan-Meier Formula | HIGH | Standard statistical method with well-documented implementation |
| Greenwood CI | HIGH | Industry-standard variance estimation |
| Recharts `stepAfter` | HIGH | Verified in official API documentation |
| Tournament Elimination Logic | MEDIUM | Simplified model; real elimination depends on tiebreakers |
| Log-rank Test in SQL | LOW | Complex to implement correctly in pure SQL; may need Python |

---

## Appendix: Data Validation Queries

```sql
-- Check data quality for survival analysis
SELECT
    'Total Entries' as metric,
    COUNT(DISTINCT entry_id) as value
FROM entry_round_history
UNION ALL
SELECT
    'Commanders with 20+ entries',
    COUNT(DISTINCT commander_id)
FROM entry_round_history
GROUP BY commander_id
HAVING COUNT(DISTINCT entry_id) >= 20
UNION ALL
SELECT
    'Max rounds in any tournament',
    MAX(round_number)
FROM entry_round_history
UNION ALL
SELECT
    'Avg rounds per tournament',
    ROUND(AVG(swiss_rounds), 1)
FROM (SELECT DISTINCT tournament_id, swiss_rounds FROM entry_round_history) t;

-- Validate Kaplan-Meier calculation
-- Survival at round 1 should be high (few eliminations)
-- Survival should monotonically decrease
SELECT
    commander_name,
    round_number,
    survival_probability,
    LAG(survival_probability) OVER (PARTITION BY commander_id ORDER BY round_number) as prev_survival,
    CASE
        WHEN survival_probability > LAG(survival_probability) OVER (PARTITION BY commander_id ORDER BY round_number)
        THEN 'ERROR: Survival increased!'
        ELSE 'OK'
    END as validation
FROM commander_kaplan_meier
ORDER BY commander_name, round_number;
```
