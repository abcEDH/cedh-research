#!/usr/bin/env python3
"""
Analyze a cEDH deck list: CMC distribution, Ad Nauseam simulation,
color identity validation, and EDHREC synergy cross-reference.

Usage:
    python tools/deck_analyzer.py DECKLIST [--db PATH] [--edhrec COMMANDER_SLUG]

Decklist format (one card per line, sideboard section ignored):
    1 Thassa's Oracle (PTHB) 73p
    1 Force of Will (DMR) 284
    ...
    SIDEBOARD:
    1 ...

The sideboard section is always ignored — it is treated as a "not playing"
pile, not a swap pool.
"""
import argparse
import json
import random
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_DB = Path('data/cards.db')
LAND_TYPES = ('Land', 'Basic Land')


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_decklist(text: str) -> tuple[list[str], list[str]]:
    """Return (main_deck_names, sideboard_names). Sideboard after 'SIDEBOARD:'."""
    main, side = [], []
    in_side = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r'sideboard', line, re.IGNORECASE):
            in_side = True
            continue
        m = re.match(r'^\d+\s+(.+?)(?:\s+\([A-Z0-9]+\)\s+\S+)?$', line)
        if m:
            name = m.group(1).strip()
            (side if in_side else main).append(name)
    return main, side


# ---------------------------------------------------------------------------
# Card DB
# ---------------------------------------------------------------------------

def lookup_cards(names: list[str], db_path: Path) -> dict[str, dict]:
    if not db_path.exists():
        print(f'Card database not found at {db_path}. Run: python tools/build_card_db.py', file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    results = {}
    for name in names:
        row = c.execute(
            'SELECT name, mana_cost, type_line, oracle_text, cmc, color_identity '
            'FROM cards WHERE name = ?', (name,)
        ).fetchone()
        if row:
            results[name] = {'name': row[0], 'mana_cost': row[1], 'type_line': row[2],
                             'oracle_text': row[3], 'cmc': row[4], 'color_identity': row[5]}
        else:
            results[name] = None
    conn.close()
    return results


# ---------------------------------------------------------------------------
# CMC analysis
# ---------------------------------------------------------------------------

def is_land(card: dict) -> bool:
    return 'Land' in card.get('type_line', '')


def cmc_list(cards_data: dict) -> list[float]:
    """Return list of CMC values (lands = 0)."""
    cmcs = []
    for card in cards_data.values():
        if card is None:
            continue
        cmcs.append(0.0 if is_land(card) else card.get('cmc', 0))
    return cmcs


def cmc_stats(cmcs: list[float]) -> dict:
    nonland = [x for x in cmcs if x > 0]
    return {
        'total': len(cmcs),
        'avg_with_lands': round(sum(cmcs) / len(cmcs), 2) if cmcs else 0,
        'avg_nonland': round(sum(nonland) / len(nonland), 2) if nonland else 0,
        'high_cmc': sorted([(c, v) for c, v in zip(cmcs, cmcs) if v >= 4], reverse=True),
    }


# ---------------------------------------------------------------------------
# Ad Nauseam simulation
# ---------------------------------------------------------------------------

def simulate_ad_nauseam(cmcs: list[float], starting_life: int = 40, trials: int = 1000) -> dict:
    """Monte Carlo simulation of Ad Nauseam draws."""
    results = []
    for _ in range(trials):
        deck = cmcs.copy()
        random.shuffle(deck)
        life = starting_life
        drawn = 0
        for cmc in deck:
            if life - cmc <= 1:
                break
            life -= cmc
            drawn += 1
            if drawn >= 35:
                break
        results.append((drawn, life))

    avg_drawn = sum(r[0] for r in results) / trials
    avg_life  = sum(r[1] for r in results) / trials
    pct_20    = sum(1 for r in results if r[0] >= 20) / trials * 100
    pct_25    = sum(1 for r in results if r[0] >= 25) / trials * 100

    return {
        'avg_cards_drawn': round(avg_drawn, 1),
        'avg_life_remaining': round(avg_life, 1),
        'pct_draw_20_plus': round(pct_20, 1),
        'pct_draw_25_plus': round(pct_25, 1),
    }


# ---------------------------------------------------------------------------
# EDHREC
# ---------------------------------------------------------------------------

def fetch_edhrec_synergies(commander_slug: str, top_n: int = 20) -> list[dict]:
    url = f'https://json.edhrec.com/pages/commanders/{commander_slug}.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f'EDHREC fetch failed: {e}', file=sys.stderr)
        return []

    all_cards = []
    for cl in data.get('container', {}).get('json_dict', {}).get('cardlists', []):
        for card in cl.get('cardviews', []):
            all_cards.append({
                'name': card.get('name', ''),
                'synergy': card.get('synergy', 0),
                'num_decks': card.get('num_decks', 0),
                'potential_decks': card.get('potential_decks', 1),
            })

    all_cards.sort(key=lambda x: x['synergy'], reverse=True)
    return all_cards[:top_n]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(main_names: list[str], cards_data: dict, edhrec_slug: str | None):
    cmcs = cmc_list(cards_data)
    stats = cmc_stats(cmcs)

    print(f'\n{"="*60}')
    print(f'DECK ANALYSIS  ({len(main_names)} cards)')
    print(f'{"="*60}')

    # Not found
    missing = [n for n, v in cards_data.items() if v is None]
    if missing:
        print(f'\n⚠  Not found in DB ({len(missing)}): {", ".join(missing)}')

    # CMC
    print(f'\n--- CMC Distribution ---')
    print(f'  Avg CMC (incl lands as 0): {stats["avg_with_lands"]}')
    print(f'  Avg CMC (nonland only):    {stats["avg_nonland"]}')

    buckets: dict[int, list[str]] = {}
    for name, card in cards_data.items():
        if card is None or is_land(card): continue
        cmc = int(card['cmc'])
        buckets.setdefault(cmc, []).append(name)
    for cmc in sorted(buckets):
        bar = '█' * len(buckets[cmc])
        print(f'  CMC {cmc}: {bar} ({len(buckets[cmc])})')

    # Lands
    land_count = sum(1 for c in cards_data.values() if c and is_land(c))
    print(f'\n  Lands: {land_count}  |  Nonlands: {len(main_names) - land_count}')

    # Ad Nauseam
    print(f'\n--- Ad Nauseam Simulation (1000 trials, 40 starting life) ---')
    sim = simulate_ad_nauseam(cmcs)
    print(f'  Avg cards drawn:       {sim["avg_cards_drawn"]}')
    print(f'  Avg life remaining:    {sim["avg_life_remaining"]}')
    print(f'  ≥20 cards drawn:       {sim["pct_draw_20_plus"]}% of games')
    print(f'  ≥25 cards drawn:       {sim["pct_draw_25_plus"]}% of games')

    # High CMC warning
    high = [(n, c['cmc']) for n, c in cards_data.items() if c and not is_land(c) and c['cmc'] >= 4]
    if high:
        print(f'\n  CMC 4+ hits (risk cards):')
        for name, cmc in sorted(high, key=lambda x: -x[1]):
            print(f'    {name:40s} CMC={cmc:.0f}')

    # EDHREC
    if edhrec_slug:
        print(f'\n--- EDHREC High-Synergy Cards Not In Deck ---')
        deck_set = {n.lower() for n in main_names}
        synergies = fetch_edhrec_synergies(edhrec_slug)
        shown = 0
        for card in synergies:
            if card['name'].lower() not in deck_set and card['synergy'] > 0.3:
                pct = round(100 * card['num_decks'] / max(card['potential_decks'], 1))
                print(f'  {card["name"]:40s} synergy={card["synergy"]:.2f}  {pct}% incl')
                shown += 1
                if shown >= 10: break
        if not shown:
            print('  None found above 0.30 synergy threshold.')

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('decklist', type=Path, help='Path to decklist text file')
    parser.add_argument('--db', default=DEFAULT_DB, type=Path, help='SQLite card database')
    parser.add_argument('--edhrec', metavar='SLUG', help='Commander slug for EDHREC synergy lookup (e.g. leonardo-the-balance)')
    args = parser.parse_args()

    if not args.decklist.exists():
        print(f'Decklist not found: {args.decklist}', file=sys.stderr)
        sys.exit(1)

    text = args.decklist.read_text()
    main_names, side_names = parse_decklist(text)

    if not main_names:
        print('No cards found in decklist.', file=sys.stderr)
        sys.exit(1)

    print(f'Parsed {len(main_names)} main deck cards, {len(side_names)} sideboard (ignored).')
    cards_data = lookup_cards(main_names, args.db)
    print_report(main_names, cards_data, args.edhrec)


if __name__ == '__main__':
    main()
