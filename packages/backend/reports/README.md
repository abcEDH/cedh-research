# cEDH Analytics Reports

This directory contains periodic analysis snapshots and meta reports.

## Report Types

### Meta Reports (`YYYY-MM-meta-report.md`)
Monthly snapshots of the cEDH competitive meta including:
- Commander rankings by volume and performance
- Seat position win rates (turn order analysis)
- Rising/falling commanders
- Top player statistics

### Methodology
- **Win Rate**: Games won / (Games won + Games lost)
- **Top 16 Rate**: Entries finishing in top 16 (Top 4 for 34-player events) / Total entries
- **Seat Spread**: Seat 0 win rate minus Seat 3 win rate (measures turn order dependency)
- **Variance**: Based on distribution of entry win rates
  - High: >40% of entries below 15% win rate
  - Medium: 25-40% below 15%
  - Low: <25% below 15%

## Generating Reports

```bash
# Generate all snapshots for current month
python src/snapshot_analysis.py

# Generate with markdown export
python src/snapshot_analysis.py --export-md

# Specific period
python src/snapshot_analysis.py --period 2025-01 --export-md

# Single commander deep dive
python src/snapshot_analysis.py --commander "Kinnan, Bonder Prodigy"
```

## Data Sources

Reports are generated from tournament data ingested from [TopDeck.gg](https://topdeck.gg).

**Criteria:**
- Tournaments with 32+ players
- cEDH format (competitive Commander)
- Complete standings and round data

## Historical Data

Snapshots are stored in Supabase (`analysis_snapshots` table) for temporal queries:

```sql
-- Compare a commander across periods
SELECT meta_period, metrics->>'win_rate' as win_rate
FROM analysis_snapshots
WHERE entity_name ILIKE '%Kinnan%'
ORDER BY meta_period;

-- Find improving commanders
SELECT entity_name,
       metrics->>'win_rate' as current_wr
FROM latest_analysis
WHERE report_type = 'commander_survival'
ORDER BY (metrics->>'win_rate')::numeric DESC;
```

## License

Data is provided for educational and community analysis purposes.
