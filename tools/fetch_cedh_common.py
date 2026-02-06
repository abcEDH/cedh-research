#!/usr/bin/env python3
import json
import time
from pathlib import Path
import requests

INPUT = Path('data/cedh_common_cards.txt')
OUT = Path('data/cedh_common_cards.json')
CACHE_PATH = Path('.cache/scryfall_cards.json')
SCRYFALL_NAMED = 'https://api.scryfall.com/cards/named'
USER_AGENT = 'CEDHCommon/0.1'
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
    names = [line.strip() for line in INPUT.read_text().splitlines() if line.strip()]
    cache = load_cache()
    out = {}

    for name in names:
        data = get_card_data(name, cache)
        out[name] = {
            'name': data.get('name'),
            'mana_cost': data.get('mana_cost'),
            'type_line': data.get('type_line'),
            'oracle_text': data.get('oracle_text'),
            'colors': data.get('colors'),
            'color_identity': data.get('color_identity'),
        }

    OUT.write_text(json.dumps(out, indent=2, sort_keys=True))
    save_cache(cache)
    print(f"Wrote {len(out)} cards to {OUT}")


if __name__ == '__main__':
    main()
