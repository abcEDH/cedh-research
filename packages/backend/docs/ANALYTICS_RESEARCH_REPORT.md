# cEDH Analytics Research Report

**Date:** 2026-01-20
**Scope:** Card frequency, win-rate correlation, turn order fairness, commander clustering
**Status:** Research complete, ready for implementation

---

## Executive Summary

This report synthesizes research from multiple open-source cEDH analytics projects and establishes the statistical methodology and implementation patterns for four key analytics features. The research drew from:

- **EDH-Top-16/edhtop16** - Official TopDeck.gg partnership, Next.js/GraphQL
- **j-chan-hkust/cedh-deck-analytics** - Python, card tier analysis, trap card identification
- **KonradHoeffner/cedh** - Python, clustering, monthly staples tracking
- **isleep2late/cEDHLeague-Season1** - Chi-square turn order analysis, OpenSkill ratings
- **Warlord1986pl/mtg-metagame-tool** - Importance scoring, hypergeometric probability

---

## Current Database Status

| Metric | Count |
|--------|-------|
| Tournaments | 52 |
| Tournament Entries | 4,083 |
| Games | 5,749 |
| Game Participants | 22,427 |
| Commanders | 290 |
| Players | 3,099 |

**Top Commanders by Entries:**
| Commander | Entries | Win Rate |
|-----------|---------|----------|
| Unknown Commander | 1,209 | 16% |
| Kraum / Tymna the Weaver | 392 | 19% |
| Kinnan, Bonder Prodigy | 218 | 17% |
| Sisay, Weatherlight Captain | 123 | 22% |
| Inalla, Archmage Ritualist | 107 | 22% |

---

## 1. Card Inclusion Frequency Analysis

### Core Methodology

**Inclusion Rate Formula:**
```
Inclusion Rate = (Number of decks containing the card / Total eligible decks) × 100%
```

**Tier Classification (recommended thresholds):**

| Tier | Threshold | Description |
|------|-----------|-------------|
| **Core** | ≥80% | Auto-include, exclusion must be justified |
| **Essential** | 60-79% | Strong consensus |
| **Common** | 30-59% | Majority include |
| **Flex** | 10-29% | Meta-dependent choice |
| **Spice** | <10% | Personal tech, innovation |

### EDHREC Synergy Score

```
Synergy = (% in commander decks) - (% in color identity decks overall)
```

This reveals cards specifically good for a commander vs generally good cards.

**Example:** Eldrazi Displacer in Rasputin decks
- 86% in Rasputin decks
- 11% in UW decks generally
- **Synergy = +75%**

### Implementation Pattern

```python
from collections import Counter

def calculate_inclusion_rates(decks: list[list[str]], min_decks: int = 5) -> dict[str, float]:
    total_decks = len(decks)
    card_counts = Counter()
    for deck in decks:
        unique_cards = set(deck)
        card_counts.update(unique_cards)
    return {
        card: count / total_decks
        for card, count in card_counts.items()
        if count >= min_decks
    }
```

### SQL Implementation

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

---

## 2. Win-Rate Correlation Analysis

### Core Methodology

**Draw Adjustment (quarter-win model):**
```python
win_rate = (wins + 0.25 * draws) / total_games
```

**Center at 25%:** In 4-player pods, expected win rate = 25%. Cards performing above this threshold provide signal.

### Power-Law Weight Transform

```python
def power_law_weight(win_rate: float, power: float = 2.0, center: float = 0.25) -> float:
    """Emphasize differences at higher performance."""
    return (win_rate - center) ** power if win_rate > center else -abs(win_rate - center) ** power
```

### Trap Card Identification

**Definition:** Cards that are popular but underperform.

```python
is_trap = (
    card_appearance_rate > 0.20 and  # Appears in >20% of decks
    card_avg_power < percentile_20   # Bottom 20% of ranked cards
)

trap_score = appearance_rate * (percentile_20 - card_avg_power)
```

### 17lands GIH WR Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| GP WR | wins / games_with_card_in_deck | Win rate when card in deck |
| **GIH WR** | wins / games_where_card_drawn | Win rate when card was drawn |
| OH WR | wins / games_in_opening_hand | Opening hand win rate |
| IWD | GIH WR - GND WR | Improvement when drawn |

**GIH WR is preferred** because it filters noise from games where the card was never seen.

### Sample Size Requirements

| Analysis Type | Minimum | Ideal |
|---------------|---------|-------|
| Card frequency | 3 decks | 20+ |
| Card win rate | 30 games | 200+ |
| Commander comparison | 50 entries | 200+ |
| Regression model | 1000 games | 5000+ |

---

## 3. Turn Order Fairness Analysis

### Statistical Test

**Chi-Square Goodness-of-Fit Test**
- **Null hypothesis:** H₀: p₁ = p₂ = p₃ = p₄ = 0.25 (each seat has equal win probability)
- **Alternative:** At least one position differs significantly
- **Degrees of freedom:** 3 (for 4 categories)
- **Standard α:** 0.05 (95% confidence)

### Draw Rate Adjustment

```python
expected_rate = (1 - draw_rate) / 4
expected_wins = [total_games_at_position * expected_rate for each position]
```

### Cohen's w Effect Size

```
w = sqrt(chi² / n)
```

| Effect Size | Cohen's w | Sample Needed (80% power) |
|-------------|-----------|---------------------------|
| Small | 0.10 | ~785 games |
| Medium-small | 0.20 | ~196 games |
| Medium | 0.30 | ~87 games |
| Large | 0.50 | ~31 games |

### Wilson Score Confidence Intervals

Use `statsmodels.stats.proportion.proportion_confint(method='wilson')` for:
- Small samples
- Extreme proportions (close to 0 or 1)
- Asymmetric intervals

### OpenSkill Integration

For skill-adjusted analysis, use **OpenSkill Plackett-Luce model** (MIT licensed, 3x faster than TrueSkill).

**Elo Conversion Formula:**
```
Elo = 1000 + (mu - 25) × 12 - (sigma - 8.333) × 4
```

### Reference Data: cEDH League Season 1

| Seat | Wins | Total | Win Rate |
|------|------|-------|----------|
| 1 | 26 | 94 | 27.7% |
| 2 | 22 | 91 | 24.2% |
| 3 | 17 | 87 | 19.5% |
| 4 | 16 | 96 | 16.7% |

**Results:** χ² = 3.20, p = 0.362 (not significant with ~90 games)

---

## 4. Commander/Decklist Clustering

### Core Methodology

**Binary Vectorization:** Each deck becomes a sparse vector where each unique card is a dimension (1 = present, 0 = absent).

```python
from sklearn.feature_extraction import DictVectorizer

deck_dicts = [{card: 1 for card in deck.cards} for deck in decks]
vectorizer = DictVectorizer(sparse=True)
X = vectorizer.fit_transform(deck_dicts)
```

### Distance Metric

**L1 (Manhattan) distance** - For binary data, equals Hamming distance (count of differing positions).

```python
from sklearn.cluster import AgglomerativeClustering

clustering = AgglomerativeClustering(
    n_clusters=10,
    metric="l1",
    linkage="average",
    compute_distances=True
)
```

### Critical: Noise Card Filtering

**Must filter ~80+ ubiquitous cards before vectorization:**

```python
IGNORE_CARDS = {
    # Basic Lands
    "Island", "Swamp", "Plains", "Mountain", "Forest",
    "Snow-Covered Island", "Snow-Covered Swamp", ...

    # Fetchlands
    "Misty Rainforest", "Polluted Delta", "Scalding Tarn", ...

    # Original Duals
    "Underground Sea", "Volcanic Island", "Tropical Island", ...

    # Shocklands
    "Watery Grave", "Steam Vents", "Breeding Pool", ...

    # Mana Rocks
    "Sol Ring", "Mana Crypt", "Chrome Mox", "Arcane Signet",

    # Signets (all 10)
    "Azorius Signet", "Boros Signet", "Dimir Signet", ...

    # Talismans (all 10)
    "Talisman of Conviction", "Talisman of Creativity", ...
}
```

**Why:** Without filtering, all decks appear highly similar (60+ shared cards), producing meaningless clusters.

### Visualization

- **<1000 decks:** scipy dendrogram
- **>1000 decks:** UMAP 2D projection (faster, preserves global structure)

---

## 5. Data Sources Identified

| Source | Type | Confidence |
|--------|------|------------|
| [j-chan-hkust/cedh-deck-analytics](https://github.com/j-chan-hkust/cedh-deck-analytics) | GitHub | MEDIUM |
| [KonradHoeffner/cedh](https://github.com/KonradHoeffner/cedh) | GitHub | HIGH |
| [isleep2late/cEDHLeague-Season1](https://github.com/isleep2late/cEDHLeague-Season1) | GitHub | HIGH |
| [EDHREC Synergy Explanation](https://edhrec.com/articles/from-synergy-to-lift-the-math-behind-edhrecs-new-era) | Blog | HIGH |
| [17lands Metrics](https://www.17lands.com/metrics_definitions) | Docs | HIGH |
| [OpenSkill Library](https://github.com/vivekjoshy/openskill.py) | GitHub | HIGH |
| [cedh.io](https://www.cedh.io/) | Website | MEDIUM |

---

## 6. Key Dependencies

```
# Core Analysis
scipy>=1.11.0
statsmodels>=0.14.0
numpy>=1.24.0
pandas>=2.1.0

# Machine Learning
scikit-learn>=1.5.0

# Ratings
openskill>=5.0.0

# Visualization
matplotlib>=3.8.0
umap-learn>=0.5.0
plotly>=5.18.0
```

---

## 7. Open Questions

1. **Moxfield API access** - Required for URL-only decklists (TOS may restrict)
2. **Minimum sample sizes** - Need 200+ games for reliable card-level win-rate statistics
3. **Cluster count determination** - Use silhouette analysis vs fixed N=10?
4. **GIH WR tracking** - Requires game-level card draw logging (not currently captured)

---

## Recommendations

1. **Start with card inclusion frequency** - Most straightforward, requires only decklist parsing
2. **Add turn order analysis** - Good statistical grounding, clear methodology
3. **Defer win-rate correlation** - Requires more data and careful confounder handling
4. **Defer clustering** - Most complex, requires significant preprocessing

---

## Next Steps

See `IMPLEMENTATION_PLAN.md` for detailed phased implementation approach.
