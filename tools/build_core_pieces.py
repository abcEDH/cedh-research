#!/usr/bin/env python3
import json
from pathlib import Path
import time
import requests

CACHE_PATH = Path('.cache/scryfall_cards.json')
LABELS_PATH = Path('data/card_labels.json')
OUT_PATH = Path('data/core_pieces.json')
SCRYFALL_NAMED = 'https://api.scryfall.com/cards/named'
USER_AGENT = 'KefkaCorePieces/0.1'
ACCEPT = 'application/json'


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


def main():
    labels = json.loads(LABELS_PATH.read_text())
    cache = load_cache()

    all_cards = set()
    for k, v in labels.items():
        all_cards.update(v)

    core = {}
    for name in sorted(all_cards):
        data = get_card_data(name, cache)
        core[name] = {
            'name': data.get('name'),
            'mana_cost': data.get('mana_cost'),
            'type_line': data.get('type_line'),
            'oracle_text': data.get('oracle_text'),
            'colors': data.get('colors'),
            'color_identity': data.get('color_identity'),
        }

    save_cache(cache)
    OUT_PATH.write_text(json.dumps(core, indent=2, sort_keys=True))
    print(f"Wrote {len(core)} core cards to {OUT_PATH}")


if __name__ == '__main__':
    main()
