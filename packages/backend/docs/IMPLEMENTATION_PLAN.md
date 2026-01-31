# cEDH Analytics Implementation Plan

**Date:** 2026-01-20
**Based on:** ANALYTICS_RESEARCH_REPORT.md
**Estimated Phases:** 4 major features, 12 total tasks

---

## Overview

This plan implements four analytics features in order of complexity and data requirements:

1. **Card Inclusion Frequency** (Phase 1) - Foundation
2. **Turn Order Fairness** (Phase 2) - Statistical rigor
3. **Win-Rate Correlation** (Phase 3) - Builds on Phase 1
4. **Commander Clustering** (Phase 4) - Most complex

---

## Phase 1: Card Inclusion Frequency Analysis

**Goal:** Parse decklists and calculate card frequency per commander.
**Dependencies:** Existing `tournament_entries.decklist_text` data
**Estimated tasks:** 4

### Task 1.1: Create Decklist Parsing Function (SQL)

**File:** `supabase/migrations/XXXX_add_parse_decklist_function.sql`

```sql
CREATE OR REPLACE FUNCTION parse_decklist(decklist TEXT)
RETURNS TEXT[] AS $$
DECLARE
    lines TEXT[];
    result TEXT[];
    line TEXT;
    card_name TEXT;
BEGIN
    IF decklist IS NULL THEN RETURN '{}'; END IF;
    lines := string_to_array(decklist, E'\\n');
    result := '{}';
    FOREACH line IN ARRAY lines LOOP
        line := trim(line);
        IF line LIKE '~~%~~' THEN CONTINUE; END IF;
        IF line = '' THEN CONTINUE; END IF;
        IF line ~ '^\d+\s+' THEN
            card_name := regexp_replace(line, '^\d+\s+', '');
            IF card_name != '' THEN
                result := array_append(result, card_name);
            END IF;
        END IF;
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

**Acceptance criteria:**
- Function parses TopDeck decklist format correctly
- Handles NULL input gracefully
- Extracts card names without quantities

### Task 1.2: Create Card Frequencies View

**File:** `supabase/migrations/XXXX_add_card_frequencies_view.sql`

```sql
CREATE MATERIALIZED VIEW card_frequencies_by_commander AS
SELECT
    c.id AS commander_id,
    c.name AS commander,
    card_name,
    COUNT(DISTINCT te.id) AS deck_count,
    ROUND(
        COUNT(DISTINCT te.id)::NUMERIC /
        NULLIF((SELECT COUNT(*) FROM tournament_entries te2 WHERE te2.commander_id = c.id), 0),
        4
    ) AS inclusion_rate,
    CASE
        WHEN COUNT(DISTINCT te.id)::NUMERIC / NULLIF((SELECT COUNT(*) FROM tournament_entries te2 WHERE te2.commander_id = c.id), 0) >= 0.80 THEN 'core'
        WHEN COUNT(DISTINCT te.id)::NUMERIC / NULLIF((SELECT COUNT(*) FROM tournament_entries te2 WHERE te2.commander_id = c.id), 0) >= 0.60 THEN 'essential'
        WHEN COUNT(DISTINCT te.id)::NUMERIC / NULLIF((SELECT COUNT(*) FROM tournament_entries te2 WHERE te2.commander_id = c.id), 0) >= 0.30 THEN 'common'
        WHEN COUNT(DISTINCT te.id)::NUMERIC / NULLIF((SELECT COUNT(*) FROM tournament_entries te2 WHERE te2.commander_id = c.id), 0) >= 0.10 THEN 'flex'
        ELSE 'spice'
    END AS tier
FROM tournament_entries te
JOIN commanders c ON te.commander_id = c.id
CROSS JOIN LATERAL unnest(parse_decklist(te.decklist_text)) AS card_name
WHERE te.decklist_text IS NOT NULL
GROUP BY c.id, c.name, card_name;

CREATE INDEX idx_card_freq_commander ON card_frequencies_by_commander(commander_id);
CREATE INDEX idx_card_freq_card ON card_frequencies_by_commander(card_name);
CREATE INDEX idx_card_freq_tier ON card_frequencies_by_commander(tier);
```

**Acceptance criteria:**
- Materialized view computes correctly
- Tier classification matches thresholds (80/60/30/10)
- Indexes enable efficient queries

### Task 1.3: Create Python Card Frequency Module

**File:** `src/card_frequency.py`

```python
"""Card frequency analysis for cEDH decklist data."""
from dataclasses import dataclass
from typing import Optional
from collections import Counter

@dataclass
class CardFrequencyResult:
    card_name: str
    total_appearances: int
    total_eligible_decks: int
    inclusion_rate: float
    tier: str
    synergy_score: Optional[float] = None

@dataclass
class CommanderCardPool:
    commander: str
    total_decks_analyzed: int
    cards: dict[str, CardFrequencyResult]

    def get_core_cards(self, threshold: float = 0.80) -> list[CardFrequencyResult]:
        return [c for c in self.cards.values() if c.inclusion_rate >= threshold]

    def get_flex_slots(self, min_rate: float = 0.10, max_rate: float = 0.50) -> list[CardFrequencyResult]:
        return [c for c in self.cards.values() if min_rate <= c.inclusion_rate < max_rate]

def classify_tier(inclusion_rate: float) -> str:
    if inclusion_rate >= 0.80: return 'core'
    if inclusion_rate >= 0.60: return 'essential'
    if inclusion_rate >= 0.30: return 'common'
    if inclusion_rate >= 0.10: return 'flex'
    return 'spice'

def calculate_inclusion_rates(
    decks: list[list[str]],
    min_appearances: int = 5
) -> dict[str, CardFrequencyResult]:
    """Calculate card inclusion rates across a collection of decks."""
    total_decks = len(decks)
    card_counts = Counter()

    for deck in decks:
        unique_cards = set(deck)
        card_counts.update(unique_cards)

    results = {}
    for card, count in card_counts.items():
        if count >= min_appearances:
            rate = count / total_decks
            results[card] = CardFrequencyResult(
                card_name=card,
                total_appearances=count,
                total_eligible_decks=total_decks,
                inclusion_rate=rate,
                tier=classify_tier(rate)
            )
    return results
```

**Acceptance criteria:**
- Module computes inclusion rates correctly
- Tier classification matches SQL view
- Handles edge cases (empty decks, min appearances)

### Task 1.4: Add CLI Commands for Card Frequency

**File:** `src/ingest.py` (extend existing)

Add new CLI commands:
- `python src/ingest.py --refresh-card-frequencies` - Refresh materialized view
- `python src/ingest.py --card-report <commander>` - Generate frequency report for commander

**Acceptance criteria:**
- CLI commands work correctly
- Output is human-readable
- Integrates with existing ingestion workflow

---

## Phase 2: Turn Order Fairness Analysis

**Goal:** Chi-square analysis of seat position win rates.
**Dependencies:** Existing `game_participants.seat_position` data
**Estimated tasks:** 3

### Task 2.1: Create Turn Order Analysis Module

**File:** `src/turn_order_analysis.py`

Implement:
- `analyze_turn_order()` - Chi-square goodness-of-fit test
- `PositionStats` dataclass with Wilson score confidence intervals
- `TurnOrderAnalysis` dataclass with effect size interpretation
- `required_sample_size()` - Power analysis function
- `generate_report()` - Human-readable output

**Key formulas:**
```python
# Expected win rate with draw adjustment
expected_rate = (1 - draw_rate) / 4

# Chi-square statistic
chi2, p_value = stats.chisquare(f_obs=wins_by_position, f_exp=expected)

# Cohen's w effect size
cohens_w = np.sqrt(chi2 / total_wins)
```

**Acceptance criteria:**
- Chi-square test produces correct results
- Wilson score intervals calculated correctly
- Effect size interpretation follows Cohen's conventions

### Task 2.2: Create Turn Order SQL View

**File:** `supabase/migrations/XXXX_add_turn_order_stats_view.sql`

```sql
CREATE VIEW turn_order_stats AS
SELECT
    seat_position,
    COUNT(*) FILTER (WHERE is_winner) AS wins,
    COUNT(*) AS total_games,
    ROUND(COUNT(*) FILTER (WHERE is_winner)::NUMERIC / COUNT(*), 4) AS win_rate
FROM game_participants
WHERE seat_position IS NOT NULL
GROUP BY seat_position
ORDER BY seat_position;
```

**Acceptance criteria:**
- View aggregates correctly
- Handles NULL seat positions
- Win rate calculation is accurate

### Task 2.3: Add Turn Order CLI Commands

**File:** `src/turn_order_analysis.py` (CLI section)

Add:
- `python src/turn_order_analysis.py --analyze` - Run full analysis
- `python src/turn_order_analysis.py --report` - Generate report
- `python src/turn_order_analysis.py --power-analysis` - Show required sample sizes

**Acceptance criteria:**
- CLI produces readable output
- Statistical results are correct
- Power analysis provides actionable guidance

---

## Phase 3: Win-Rate Correlation Analysis

**Goal:** Correlate card presence with tournament performance.
**Dependencies:** Phase 1 (card parsing), tournament standings
**Estimated tasks:** 3

### Task 3.1: Create Win Rate Calculation Module

**File:** `src/win_rate_correlation.py`

Implement:
- `calculate_card_performance()` - Basic frequency-weighted analysis
- `power_law_weight()` - Power-law transform (center at 25%)
- `identify_trap_cards()` - High popularity, low performance
- `commander_controlled_performance()` - Relative win rate within commander

**Key formulas:**
```python
# Draw adjustment (quarter-win model)
win_rate = (wins + 0.25 * draws) / total_games

# Power-law weight
power_weight = sign(win_rate - 0.25) * |win_rate - 0.25|^2

# Trap score
trap_score = appearance_rate * max(0, median_wr - card_avg_wr)
```

**Acceptance criteria:**
- Win rate calculated with draw adjustment
- Trap cards identified correctly
- Commander-relative analysis working

### Task 3.2: Create Performance SQL Views

**File:** `supabase/migrations/XXXX_add_card_performance_views.sql`

Create views:
- `card_win_rates` - Card presence vs tournament placement
- `trap_cards` - Cards with high appearance, low performance
- `spice_cards` - Cards with low appearance, high performance

**Acceptance criteria:**
- Views compute correctly
- Sample size minimums enforced (10+ appearances)
- Performance data accurate

### Task 3.3: Add Win Rate CLI Commands

**File:** `src/win_rate_correlation.py` (CLI section)

Add:
- `python src/win_rate_correlation.py --trap-cards` - List potential trap cards
- `python src/win_rate_correlation.py --spice-report` - High-performing rare cards
- `python src/win_rate_correlation.py --commander <name>` - Commander-specific analysis

**Acceptance criteria:**
- Reports are human-readable
- Minimum sample sizes enforced
- Trap card criteria documented

---

## Phase 4: Commander/Decklist Clustering

**Goal:** Cluster decklists to identify archetypes.
**Dependencies:** Phase 1 (card parsing), sufficient data (100+ decks)
**Estimated tasks:** 2

### Task 4.1: Create Clustering Module

**File:** `src/deck_clustering.py`

Implement:
- `NOISE_CARDS` - 80+ card exclusion set (lands, rocks, signets)
- `vectorize_decks()` - DictVectorizer binary encoding
- `cluster_decks()` - AgglomerativeClustering with L1 distance
- `visualize_clusters()` - Dendrogram and UMAP projection

**Key implementation:**
```python
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction import DictVectorizer

# Filter noise cards
cards = set(deck_cards)
cards.difference_update(NOISE_CARDS)

# Vectorize
vectorizer = DictVectorizer(sparse=True)
X = vectorizer.fit_transform(deck_dicts)

# Cluster
clustering = AgglomerativeClustering(
    n_clusters=10,
    metric="l1",
    linkage="average",
    compute_distances=True
)
```

**Acceptance criteria:**
- Noise filtering removes 80+ ubiquitous cards
- Clustering produces meaningful groups
- Dendrogram renders correctly

### Task 4.2: Add Clustering CLI Commands

**File:** `src/deck_clustering.py` (CLI section)

Add:
- `python src/deck_clustering.py --cluster` - Run clustering analysis
- `python src/deck_clustering.py --dendrogram <output.png>` - Generate dendrogram
- `python src/deck_clustering.py --umap <output.html>` - Interactive UMAP visualization

**Acceptance criteria:**
- Visualizations are publication-quality
- UMAP handles >1000 decks
- Cluster labels are meaningful

---

## Dependencies to Add

**File:** `requirements.txt` additions

```
# Phase 2: Turn Order Analysis
scipy>=1.11.0
statsmodels>=0.14.0
openskill>=5.0.0

# Phase 4: Clustering
scikit-learn>=1.5.0
umap-learn>=0.5.0
plotly>=5.18.0
```

---

## Testing Strategy

### Unit Tests

| Module | Test Focus |
|--------|------------|
| `card_frequency.py` | Tier classification, inclusion rates |
| `turn_order_analysis.py` | Chi-square calculation, Wilson intervals |
| `win_rate_correlation.py` | Draw adjustment, trap identification |
| `deck_clustering.py` | Noise filtering, vectorization |

### Integration Tests

- Parse real decklists from database
- Verify materialized view refresh
- End-to-end CLI command execution

### Validation Tests

- Compare turn order results with cEDH League Season 1 data
- Verify clustering produces known archetypes (e.g., Turbo Naus, Stax)

---

## Success Criteria

### Phase 1 Complete When:
- [ ] `parse_decklist()` function deployed to Supabase
- [ ] `card_frequencies_by_commander` materialized view populated
- [ ] CLI can generate card frequency reports

### Phase 2 Complete When:
- [ ] Chi-square analysis runs on existing data
- [ ] Statistical report with confidence intervals generated
- [ ] Power analysis shows required sample sizes

### Phase 3 Complete When:
- [ ] Win-rate correlation calculated with draw adjustment
- [ ] Trap cards identified and flagged
- [ ] Commander-relative performance computed

### Phase 4 Complete When:
- [ ] Decklist clustering identifies distinct archetypes
- [ ] Dendrogram visualization generated
- [ ] UMAP projection available for large datasets

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Insufficient data | Start with commanders with 50+ entries |
| Moxfield URL decklists | Defer to Phase 5, work with inline text only |
| Memory issues at scale | Use sparse matrices, sample if needed |
| Statistical validity | Enforce minimum sample sizes |

---

## Estimated Timeline

| Phase | Complexity | Est. Effort |
|-------|------------|-------------|
| Phase 1: Card Frequency | Low | 4-6 hours |
| Phase 2: Turn Order | Medium | 6-8 hours |
| Phase 3: Win Rate | Medium | 6-8 hours |
| Phase 4: Clustering | High | 8-12 hours |

**Total:** ~24-34 hours of development

---

## Next Actions

1. Start with Phase 1, Task 1.1 (decklist parsing function)
2. Validate on sample data before full deployment
3. Review statistical methodology with domain experts if possible
