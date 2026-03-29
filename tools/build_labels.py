#!/usr/bin/env python3
import json
import re
import time
from pathlib import Path
import requests

CACHE_PATH = Path('.cache/scryfall_cards.json')
SCRYFALL_NAMED = 'https://api.scryfall.com/cards/named'
USER_AGENT = 'DeckLabels/0.1'
ACCEPT = 'application/json'

# Known win pieces to force-include
KNOWN_WINS = {
    "Thassa's Oracle",
    'Underworld Breach',
    'Brain Freeze',
    'Demonic Consultation',
    'Tainted Pact',
    'Ad Nauseam',
    'Necropotence',
    'Necrodominance',
}

# Known engines even if heuristics miss
KNOWN_ENGINES = {
    'Mystic Remora',
    'Rhystic Study',
    'Wheel of Fortune',
    'Windfall',
    'Wheel of Misfortune',
    'Timetwister',
}

# Known tutors
KNOWN_TUTORS = {
    'Demonic Tutor', 'Vampiric Tutor', 'Imperial Seal', 'Gamble', 'Mystical Tutor',
    'Wishclaw Talisman', 'Demonic Consultation', 'Tainted Pact', 'Beseech the Mirror',
    'Diabolic Intent', 'Enlightened Tutor', 'Intuition', 'Grim Tutor', 'Praetor\'s Grasp'
}

# Known fast rocks
KNOWN_FAST_ROCKS = {
    'Chrome Mox', 'Mox Diamond', 'Mox Opal', 'Mox Amber', 'Lotus Petal',
    'Jeweled Lotus', 'Mana Crypt'
}

# Parse decklist lines

def parse_name(line: str) -> str | None:
    line = line.strip()
    if not line or not line[0].isdigit():
        return None
    name = line.split(' ', 1)[1]
    name = re.sub(r"\s*\([^)]*\)", "", name).strip()
    name = re.sub(r"\s\*.*\*\s*$", "", name).strip()
    name = re.sub(r"\s+[A-Z0-9-]+$", "", name).strip()
    name = re.sub(r"\s+[0-9]+[a-z]?$", "", name).strip()
    return name


def load_deck(path: Path):
    names = []
    for line in path.read_text().splitlines():
        name = parse_name(line)
        if name and not name.startswith('Kefka, Court Mage'):
            names.append(name)
    return names


def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def scryfall_fetch(name: str) -> dict:
    headers = {'User-Agent': USER_AGENT, 'Accept': ACCEPT}
    params = {'fuzzy': name}
    r = requests.get(SCRYFALL_NAMED, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_card_data(name: str, cache: dict) -> dict:
    key = name.lower()
    if key in cache:
        return cache[key]
    data = scryfall_fetch(name)
    cache[key] = data
    time.sleep(0.08)
    return data


def is_mana_rock(card: dict) -> bool:
    if 'Artifact' not in (card.get('type_line') or ''):
        return False
    text = card.get('oracle_text') or ''
    return 'Add' in text


def is_ritual(card: dict) -> bool:
    if 'Instant' not in (card.get('type_line') or '') and 'Sorcery' not in (card.get('type_line') or ''):
        return False
    text = card.get('oracle_text') or ''
    return 'Add' in text


def is_engine(card: dict) -> bool:
    text = (card.get('oracle_text') or '').lower()
    if 'draw' in text and 'discard' in text and 'each player' in text:
        return True  # wheels
    if 'draw a card' in text and 'whenever' in text:
        return True
    if card.get('name') in KNOWN_ENGINES:
        return True
    return False


def is_tutor(card: dict) -> bool:
    name = card.get('name')
    if name in KNOWN_TUTORS:
        return True
    text = (card.get('oracle_text') or '').lower()
    return 'search your library' in text


def is_win(card: dict) -> bool:
    name = card.get('name')
    if name in KNOWN_WINS:
        return True
    text = (card.get('oracle_text') or '').lower()
    return 'you win the game' in text


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deck', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    deck = load_deck(Path(args.deck))
    cache = load_cache()

    labels = {
        'fast_rocks': [],
        'rituals': [],
        'ramp_rocks': [],
        'engines': [],
        'tutors': [],
        'threats': [],
        'wins': [],
    }

    for name in deck:
        data = get_card_data(name, cache)
        if name in KNOWN_FAST_ROCKS:
            labels['fast_rocks'].append(name)
        if is_mana_rock(data) and name not in KNOWN_FAST_ROCKS:
            labels['ramp_rocks'].append(name)
        if is_ritual(data):
            labels['rituals'].append(name)
        if is_engine(data):
            labels['engines'].append(name)
        if is_tutor(data):
            labels['tutors'].append(name)
        if is_win(data):
            labels['wins'].append(name)
            labels['threats'].append(name)

    # Deduplicate and sort
    for k in labels:
        labels[k] = sorted(set(labels[k]))

    Path(args.out).write_text(json.dumps(labels, indent=2))
    save_cache(cache)
    print(f"Wrote labels to {args.out}")


if __name__ == '__main__':
    main()
