#!/usr/bin/env python3
import argparse
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests

CACHE_PATH = Path('.cache/scryfall_cards.json')
LABELS_PATH = Path('data/card_labels.json')
SCRYFALL_NAMED = 'https://api.scryfall.com/cards/named'
USER_AGENT = 'KefkaHandEval/0.1'
ACCEPT = 'application/json'

DEFAULT_DECK_COLORS = set(['U', 'B', 'R'])

# --- parsing helpers ---

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


def load_deck(path: Path) -> List[str]:
    names = []
    for line in path.read_text().splitlines():
        name = parse_name(line)
        if name:
            names.append(name)
    return names


def load_cache() -> Dict[str, dict]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}

def load_labels(path: Path | None = None) -> dict:
    labels_path = path or LABELS_PATH
    base = {}
    if labels_path.exists():
        base = json.loads(labels_path.read_text())
    override_path = labels_path.with_name(labels_path.stem + '_override.json')
    if override_path.exists():
        override = json.loads(override_path.read_text())
        for k, v in override.items():
            if isinstance(v, list):
                base[k] = sorted(set((base.get(k) or []) + v))
            else:
                base[k] = v
    if base:
        return base
    return {
        'fast_rocks': [],
        'rituals': [],
        'engines': [],
        'ramp_rocks': [],
        'tutors': [],
        'threats': [],
        'wins': [],
        'commander_names': [],
        'commander_cost': None,
        'commander_colors': [],
    }


def parse_mana_cost(mana_cost: str | None) -> tuple[int, set]:
    if not mana_cost:
        return 0, set()
    generic = 0
    colors = set()
    for sym in re.findall(r"\{([^}]+)\}", mana_cost):
        if sym.isdigit():
            generic += int(sym)
        elif sym in ['X', 'Y', 'Z']:
            continue
        elif '/' in sym:
            # hybrid: count as 1 and add colors involved
            parts = sym.split('/')
            for p in parts:
                if p in ['W', 'U', 'B', 'R', 'G']:
                    colors.add(p)
            generic += 0
        else:
            if sym in ['W', 'U', 'B', 'R', 'G']:
                colors.add(sym)
            generic += 0
    return generic + len(colors), colors


def infer_commander_cost(labels: dict, cache: dict) -> tuple[int, set]:
    names = labels.get('commander_names', [])
    if not names:
        return 5, set(DEFAULT_DECK_COLORS)
    best_total = None
    deck_colors = set()
    for name in names:
        data = get_card_data(name, cache)
        total, colors = parse_mana_cost(data.get('mana_cost'))
        identity = set(data.get('color_identity') or colors)
        deck_colors |= identity
        if best_total is None or total < best_total:
            best_total = total
    return best_total or 0, deck_colors


def save_cache(cache: Dict[str, dict]):
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def scryfall_fetch(name: str) -> dict:
    headers = {'User-Agent': USER_AGENT, 'Accept': ACCEPT}
    params = {'fuzzy': name}
    r = requests.get(SCRYFALL_NAMED, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_card_data(name: str, cache: Dict[str, dict]) -> dict:
    key = name.lower()
    if key in cache:
        return cache[key]
    data = scryfall_fetch(name)
    cache[key] = data
    time.sleep(0.08)
    return data


def mana_cost_to_req(mana_cost: str) -> Tuple[int, Dict[str, int]]:
    # returns (generic, colored)
    generic = 0
    colored: Dict[str, int] = {}
    for sym in re.findall(r"\{([^}]+)\}", mana_cost or ''):
        if sym.isdigit():
            generic += int(sym)
        elif sym in ['X', 'Y', 'Z']:
            generic += 0
        elif '/' in sym:
            # hybrid: count as any of the colors involved
            parts = sym.split('/')
            # choose one; for requirements, treat as flexible -> min 1 of any color
            # represent as generic 0 and add a special marker
            colored.setdefault('HYB', 0)
            colored['HYB'] += 1
        else:
            colored[sym] = colored.get(sym, 0) + 1
    return generic, colored


def land_colors(oracle: str) -> set:
    colors = set()
    for line in (oracle or '').split('\n'):
        if 'Add' in line and '{' in line:
            for sym in re.findall(r"\{([WUBRG])\}", line):
                colors.add(sym)
    return colors


def is_land(card: dict) -> bool:
    return 'Land' in (card.get('type_line') or '')


def is_artifact(card: dict) -> bool:
    return 'Artifact' in (card.get('type_line') or '')


def is_legendary(card: dict) -> bool:
    return 'Legendary' in (card.get('type_line') or '')


def is_creature(card: dict) -> bool:
    return 'Creature' in (card.get('type_line') or '')


def parse_sources(hand_cards: List[dict]) -> dict:
    # Identify mana sources and conditions
    sources = {
        'lands': [],
        'rocks': [],
        'rituals': [],
        'dorks': [],
        'petal': False,
        'led': False,
        'spirit_guides': [],
        'mox_diamond': False,
        'chrome_mox': False,
        'mox_opal': False,
        'mox_amber': False,
        'sol_ring': False,
        'mana_vault': False,
    }

    for c in hand_cards:
        name = c['name']
        oracle = c.get('oracle_text') or ''
        if is_land(c):
            sources['lands'].append(c)
        if name in ['Lotus Petal']:
            sources['petal'] = True
        # LED ignored for mana contributions per user request
        if name in ["Lion's Eye Diamond"]:
            sources['led'] = True
        if name in ['Simian Spirit Guide', 'Elvish Spirit Guide']:
            sources['spirit_guides'].append(c)
        if name == 'Mox Diamond':
            sources['mox_diamond'] = True
        if name == 'Chrome Mox':
            sources['chrome_mox'] = True
        if name == 'Mox Opal':
            sources['mox_opal'] = True
        if name == 'Mox Amber':
            sources['mox_amber'] = True
        if name == 'Sol Ring':
            sources['sol_ring'] = True
        if name == 'Mana Vault':
            sources['mana_vault'] = True

        # Cheap rocks that tap for colors
        if name in ['Arcane Signet', 'Fellwar Stone', 'Talisman of Creativity', 'Talisman of Dominance', 'Talisman of Indulgence']:
            sources['rocks'].append(c)
        if name in ['Grim Monolith']:
            sources['rocks'].append(c)

        # Rituals
        if name in ['Dark Ritual', 'Cabal Ritual', 'Rite of Flame', 'Culling the Weak', 'Jeska\'s Will', 'Rain of Filth', 'Strike It Rich']:
            sources['rituals'].append(c)

        # Mana dorks
        if name in ['Birds of Paradise', 'Llanowar Elves', 'Elvish Mystic', 'Fyndhorn Elves', 'Delighted Halfling', 'Bloom Tender']:
            sources['dorks'].append(c)

    return sources


def mana_sources_colors(sources: dict, hand_cards: List[dict], deck_colors: set) -> Tuple[set, int]:
    colors = set()
    colorless = 0

    # Lands
    for land in sources['lands']:
        colors |= land_colors(land.get('oracle_text') or '')
    # Always treat City of Brass / Mana Confluence / Command Tower as all deck colors
    for land in sources['lands']:
        if land['name'] in ['City of Brass', 'Mana Confluence', 'Command Tower', 'Exotic Orchard', 'Forbidden Orchard']:
            colors |= deck_colors
    # Cavern of Souls can name Kefka or Thassa's Oracle; treat as flexible color for creatures only

    # Rocks
    for rock in sources['rocks']:
        if rock['name'] in ['Arcane Signet']:
            colors |= deck_colors
        elif rock['name'] in ['Fellwar Stone']:
            colors |= deck_colors
        elif 'Talisman' in rock['name']:
            colors |= deck_colors
        elif rock['name'] == 'Grim Monolith':
            colorless += 3

    # Moxen (conditional)
    if sources['mox_diamond'] and len(sources['lands']) >= 1:
        colors |= deck_colors
    if sources['chrome_mox']:
        # imprint any nonartifact nonland
        imprintable = any(not is_land(c) and not is_artifact(c) for c in hand_cards)
        if imprintable:
            colors |= deck_colors
    if sources['mox_opal']:
        # metalcraft: count artifacts in hand (incl. itself)
        artifacts = sum(1 for c in hand_cards if is_artifact(c))
        if artifacts >= 3:
            colors |= deck_colors
    if sources['mox_amber']:
        # needs legendary in play; if Rograkh or Kefka in hand we can cast Rograkh (0)
        if any(c['name'] == 'Rograkh, Son of Rohgahh' for c in hand_cards) or any(is_legendary(c) for c in hand_cards):
            colors |= deck_colors

    # Lotus Petal / LED are one-shot; treat as flexible
    if sources['petal']:
        colors |= deck_colors
    # LED ignored for mana contributions per user request

    # Spirit guides give one mana in their color
    for c in sources['spirit_guides']:
        if c['name'] == 'Simian Spirit Guide':
            colors.add('R')
        if c['name'] == 'Elvish Spirit Guide':
            colors.add('G')

    # Sol Ring / Mana Vault colorless
    if sources['sol_ring']:
        colorless += 2
    if sources['mana_vault']:
        colorless += 3

    return colors, colorless


def castable(card: dict, colors: set, colorless: int, available_mana: int, deck_colors: set) -> bool:
    mana_cost = card.get('mana_cost') or ''
    if mana_cost == '':
        return True
    generic, colored = mana_cost_to_req(mana_cost)

    # Hybrid requirement: treat as 1 colored pip of any deck color
    if 'HYB' in colored:
        for _ in range(colored['HYB']):
            if not (colors & deck_colors):
                return False

    for sym, count in colored.items():
        if sym == 'HYB':
            continue
        if sym not in colors:
            return False

    needed = generic + sum(v for k, v in colored.items() if k != 'HYB')
    return available_mana >= needed


def get_commander_profile(labels: dict, cache: dict) -> dict:
    names = labels.get('commander_names', [])
    commander_total_cost = labels.get('commander_cost')
    commander_colors = set(labels.get('commander_colors', []))

    if isinstance(commander_total_cost, str) and commander_total_cost != '':
        numeric = 0
        colors_from_str = set()
        for ch in commander_total_cost:
            if ch.isdigit():
                numeric = numeric * 10 + int(ch)
            elif ch in ['W', 'U', 'B', 'R', 'G']:
                colors_from_str.add(ch)
        if not commander_colors:
            commander_colors = colors_from_str
        commander_total_cost = numeric + len(colors_from_str)

    if commander_total_cost is None or commander_total_cost == '' or not commander_colors:
        commander_total_cost, commander_colors = infer_commander_cost(labels, cache)

    deck_colors = set(commander_colors) if commander_colors else set(DEFAULT_DECK_COLORS)
    return {
        'names': names,
        'cost': commander_total_cost,
        'colors': deck_colors,
        'is_kinnan': 'Kinnan, Bonder Prodigy' in names,
    }


def land_mana_value(land: dict) -> int:
    name = land['name']
    if name in ['Ancient Tomb', 'City of Traitors']:
        return 2
    return 1


def land_colors_set(land: dict, deck_colors: set) -> set:
    name = land['name']
    if name in ['City of Brass', 'Mana Confluence', 'Command Tower', 'Exotic Orchard', 'Forbidden Orchard']:
        return set(deck_colors)
    if name in [
        'Arid Mesa', 'Bloodstained Mire', 'Flooded Strand', 'Marsh Flats', 'Misty Rainforest',
        'Polluted Delta', 'Scalding Tarn', 'Verdant Catacombs', 'Wooded Foothills'
    ]:
        return set(deck_colors)
    return land_colors(land.get('oracle_text') or '')


def evaluate_hand(hand: List[dict], labels: dict, cache: dict, seat: int) -> dict:
    sources = parse_sources(hand)
    hand_names = [c['name'] for c in hand]
    commander = get_commander_profile(labels, cache)
    deck_colors = commander['colors']

    lands = sources['lands'][:]
    lands_sorted = sorted(lands, key=lambda l: (land_mana_value(l), len(land_colors_set(l, deck_colors))), reverse=True)
    artifacts_in_hand = sum(1 for c in hand if is_artifact(c))
    has_birds = any(c['name'] == 'Birds of Paradise' for c in sources['dorks'])
    dork_colors = set(deck_colors) if has_birds else set(['G'])

    ritual_net = {
        'Dark Ritual': 2,
        'Cabal Ritual': 2,
        'Rite of Flame': 1,
        "Jeska's Will": 2,
        'Culling the Weak': 3,
    }

    deferred_rocks = set([
        'Arcane Signet', 'Fellwar Stone',
        'Talisman of Creativity', 'Talisman of Dominance', 'Talisman of Indulgence', 'Talisman of Curiosity'
    ])

    def sequencing(turns: int):
        carry = 0
        dork_carry = 0
        kinnan_active = False
        last_colors = set()
        last_total = 0

        for turn in range(1, turns + 1):
            played_lands = lands_sorted[:turn]
            colors = set()
            mana = carry + dork_carry

            for land in played_lands:
                colors |= land_colors_set(land, deck_colors)
                mana += land_mana_value(land)

            if dork_carry:
                colors |= dork_colors

            if seat > 1 and any(l['name'] == 'Gemstone Caverns' for l in lands):
                colors |= deck_colors
                mana += 1

            nonland_producers = dork_carry + carry
            in_play = {
                'sol_ring': False,
                'mana_vault': False,
                'grim_monolith': False,
            }

            if sources['mox_diamond'] and len(lands) >= 2:
                colors |= deck_colors
                mana += 1
                nonland_producers += 1
            if sources['chrome_mox']:
                imprintable = any(not is_land(c) and not is_artifact(c) for c in hand)
                if imprintable:
                    colors |= deck_colors
                    mana += 1
                    nonland_producers += 1
            if sources['mox_opal'] and artifacts_in_hand >= 3:
                colors |= deck_colors
                mana += 1
                nonland_producers += 1
            if sources['mox_amber'] and (commander['cost'] == 0 or any(is_legendary(c) for c in hand)):
                colors |= deck_colors
                mana += 1
                nonland_producers += 1
            if sources['petal']:
                colors |= deck_colors
                mana += 1
                nonland_producers += 1
            if any(c['name'] == 'Simian Spirit Guide' for c in hand):
                colors.add('R')
                mana += 1

            if sources['sol_ring'] and mana >= 1:
                mana += 1
                in_play['sol_ring'] = True
            if sources['mana_vault'] and mana >= 1:
                mana += 2
                in_play['mana_vault'] = True
            if any(r['name'] == 'Grim Monolith' for r in sources['rocks']) and mana >= 2:
                mana += 1
                in_play['grim_monolith'] = True

            carry_next = 0
            rocks_2 = [r for r in sources['rocks'] if r['name'] in labels.get('ramp_rocks', [])]
            if mana >= 2 and rocks_2:
                if any(r['name'] in deferred_rocks for r in rocks_2):
                    colors |= deck_colors
                    mana -= 1
                    carry_next += 1
                    nonland_producers += 1
                else:
                    colors |= deck_colors

            dork_next = dork_carry
            if dork_carry == 0 and sources['dorks']:
                if 'G' in colors and mana >= 1:
                    mana -= 1
                    dork_next = 1
                    nonland_producers += 1

            if commander['is_kinnan'] and not kinnan_active and 'G' in colors and 'U' in colors and mana >= 2:
                mana -= 2
                kinnan_active = True
            if kinnan_active:
                bonus = nonland_producers
                if in_play['sol_ring']:
                    bonus += 1
                if in_play['mana_vault']:
                    bonus += 1
                if in_play['grim_monolith']:
                    bonus += 1
                mana += bonus

            for name, net in ritual_net.items():
                if name in hand_names:
                    if name in ['Dark Ritual', 'Cabal Ritual', 'Culling the Weak'] and 'B' not in colors:
                        continue
                    if name in ['Rite of Flame', "Jeska's Will"] and 'R' not in colors:
                        continue
                    if name == "Jeska's Will" and mana < 3:
                        continue
                    mana += net

            carry = carry_next
            dork_carry = dork_next
            last_colors = colors
            last_total = mana

        return last_colors, last_total

    colors_t1, t1_total = sequencing(1)
    colors_t2, t2_total = sequencing(2)
    colors_t3, t3_total = sequencing(3)

    castable_t1 = []
    castable_t2 = []
    castable_t3 = []

    for c in hand:
        if is_land(c):
            continue
        if castable(c, colors_t1, 0, t1_total, deck_colors):
            castable_t1.append(c['name'])
        if castable(c, colors_t2, 0, t2_total, deck_colors):
            castable_t2.append(c['name'])
        if castable(c, colors_t3, 0, t3_total, deck_colors):
            castable_t3.append(c['name'])

    def can_cast_commander(total, cols):
        if commander['cost'] == 0:
            return True
        return all(c in cols for c in commander['colors']) and total >= commander['cost']

    if can_cast_commander(t1_total, colors_t1):
        commander_turn = 'T1'
    elif can_cast_commander(t2_total, colors_t2):
        commander_turn = 'T2'
    elif can_cast_commander(t3_total, colors_t3):
        commander_turn = 'T3'
    else:
        commander_turn = 'T4+'

    return {
        'colors': ''.join(sorted(colors_t2)) or 'none',
        't1_total': t1_total,
        't2_total': t2_total,
        't3_total': t3_total,
        'castable_t1': sorted(set(castable_t1)),
        'castable_t2': sorted(set(castable_t2)),
        'castable_t3': sorted(set(castable_t3)),
        'commander_turn': commander_turn,
    }


def keep_or_mull(hand_eval: dict, pod: str, seat: int, labels: dict) -> Tuple[str, str]:
    castable_t1 = set(hand_eval['castable_t1'])
    castable_t2 = set(hand_eval['castable_t2'])
    castable_t3 = set(hand_eval.get('castable_t3', []))

    interaction = {
        'Force of Will', 'Force of Negation', 'Fierce Guardianship', 'Pact of Negation',
        'Flusterstorm', 'Swan Song', 'Mental Misstep', 'Mindbreak Trap',
        'Pyroblast', 'Red Elemental Blast', "An Offer You Can't Refuse"
    }
    engines = set(labels.get('engines', [])) or {'Mystic Remora', 'Rhystic Study'}
    tutors = set(labels.get('tutors', [])) or {'Demonic Tutor', 'Vampiric Tutor', 'Imperial Seal', 'Gamble', 'Mystical Tutor', 'Wishclaw Talisman', 'Tainted Pact', 'Demonic Consultation'}
    wins = set(labels.get('wins', [])) or {"Thassa's Oracle", 'Underworld Breach', 'Brain Freeze'}

    has_interaction = bool(interaction & (castable_t1 | castable_t2))
    has_engine = bool(engines & (castable_t1 | castable_t2))
    has_tutor = bool(tutors & (castable_t1 | castable_t2))
    has_win = bool(wins & (castable_t1 | castable_t2))

    has_engine_t3 = bool(engines & castable_t3)
    has_tutor_t3 = bool(tutors & castable_t3)
    has_win_t3 = bool(wins & castable_t3)

    commander_fast = hand_eval['commander_turn'] in ['T1', 'T2']
    t3_or_better = hand_eval['commander_turn'] in ['T1', 'T2', 'T3']

    strict = seat == 4
    middle = seat in [2, 3]

    is_kinnan = 'Kinnan, Bonder Prodigy' in labels.get('commander_names', [])
    early_7 = hand_eval.get('t1_total', 0) >= 7 or hand_eval.get('t2_total', 0) >= 7
    is_sisay = 'Sisay, Weatherlight Captain' in labels.get('commander_names', [])
    sisay_rainbow = {
        'Bloom Tender', 'Faeburrow Elder', 'Selvala, Heart of the Wilds',
        'Relic of Legends', 'The Cabbage Merchant', 'Lotho, Corrupt Shirriff',
        'Kinnan, Bonder Prodigy'
    }
    has_rainbow_line = bool(sisay_rainbow & (castable_t1 | castable_t2))
    wubrg_ready = hand_eval.get('colors', '') == 'BGRUW'

    if pod == 'fast':
        if is_kinnan and early_7:
            return 'keep', 'fast: kinnan early 7-mana line'
        if is_sisay and (wubrg_ready or has_rainbow_line) and not strict:
            return 'keep', 'fast: sisay wubrg/rainbow line'
        if has_interaction and (has_tutor or has_win or commander_fast):
            return 'keep', 'fast: interaction + line'
        if middle and has_interaction and (has_engine or has_tutor):
            return 'keep', 'fast: interaction + engine/tutor (seat 2-3)'
        if not strict and has_interaction and has_engine:
            return 'keep', 'fast: interaction + engine (seat 1 leniency)'
        return 'mull', 'fast: missing early interaction or line'

    if pod == 'mixed':
        if is_kinnan and early_7:
            return 'keep', 'mixed: kinnan early 7-mana line'
        if is_sisay and (wubrg_ready or has_rainbow_line):
            return 'keep', 'mixed: sisay wubrg/rainbow line'
        if has_interaction and (has_tutor or has_engine):
            return 'keep', 'mixed: interaction + engine/tutor'
        if middle and (has_engine or has_tutor) and t3_or_better:
            return 'keep', 'mixed: engine/tutor + commander timing (seat 2-3)'
        if not strict and (has_engine_t3 or has_tutor_t3 or has_win_t3) and t3_or_better:
            return 'keep', 'mixed: T3 line present'
        if not strict and has_engine and t3_or_better:
            return 'keep', 'mixed: engine + reasonable commander timing'
        return 'mull', 'mixed: low action density'

    if is_kinnan and early_7:
        return 'keep', 'midrange: kinnan early 7-mana line'
    if is_sisay and (wubrg_ready or has_rainbow_line):
        return 'keep', 'midrange: sisay wubrg/rainbow line'
    if has_engine and (has_interaction or has_tutor):
        return 'keep', 'midrange: engine + protection/tutor'
    if middle and (has_tutor or has_engine) and t3_or_better:
        return 'keep', 'midrange: engine/tutor + commander timing (seat 2-3)'
    if not strict and (has_engine_t3 or has_tutor_t3 or has_win_t3) and t3_or_better:
        return 'keep', 'midrange: T3 line present'
    if not strict and has_tutor and t3_or_better:
        return 'keep', 'midrange: tutor + commander timing'
    return 'mull', 'midrange: no engine/tutor'


def main():
    parser = argparse.ArgumentParser(description='Random hand evaluator for Kefka deck.')
    parser.add_argument('--deck', default='data/kefka_list.txt')
    parser.add_argument('--draw', type=int, default=7)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--hands', type=int, default=5)
    parser.add_argument('--pod', choices=['fast', 'mixed', 'midrange'], default='mixed')
    parser.add_argument('--seat', default='random', choices=['random', '1', '2', '3', '4'])
    parser.add_argument('--labels', default='data/card_labels.json')
    parser.add_argument('--mull', action='store_true')
    parser.add_argument('--mull_min', type=int, default=5)
    parser.add_argument('--explain', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    deck = load_deck(Path(args.deck))
    labels = load_labels(Path(args.labels))
    commander_names = set(labels.get('commander_names', []))
    if commander_names:
        deck = [c for c in deck if c not in commander_names]
    if args.seed is not None:
        random.seed(args.seed)

    seat = int(args.seat) if args.seat != 'random' else random.choice([1, 2, 3, 4])

    cache = load_cache()

    # preload card data for deck (cached)
    card_data = {}
    for name in deck:
        data = get_card_data(name, cache)
        card_data[name] = data

    save_cache(cache)

    def score_card(card, land_count):
        name = card['name']
        score = 0
        if name in labels.get('wins', []): score += 6
        if name in labels.get('tutors', []): score += 5
        if name in labels.get('engines', []): score += 4
        if name in labels.get('fast_rocks', []): score += 4
        if name in labels.get('rituals', []): score += 3
        if name in labels.get('ramp_rocks', []): score += 2
        if is_land(card):
            score += 4 if land_count <= 2 else 1
        return score

    def explain_hits(evals):
        cast = set(evals['castable_t1']) | set(evals['castable_t2']) | set(evals.get('castable_t3', []))
        return {
            'interaction': sorted(cast & {
                'Force of Will', 'Force of Negation', 'Fierce Guardianship', 'Pact of Negation',
                'Flusterstorm', 'Swan Song', 'Mental Misstep', 'Mindbreak Trap',
                'Pyroblast', 'Red Elemental Blast', "An Offer You Can't Refuse"
            }),
            'engines': sorted(cast & set(labels.get('engines', []))),
            'tutors': sorted(cast & set(labels.get('tutors', []))),
            'wins': sorted(cast & set(labels.get('wins', []))),
        }

    outputs = []
    for i in range(args.hands):
        if args.mull:
            steps = []
            for keep_n in range(7, args.mull_min - 1, -1):
                hand_names = random.sample(deck, args.draw)
                hand_cards = [card_data[n] for n in hand_names]
                land_count = sum(1 for c in hand_cards if is_land(c))
                scored = sorted(hand_cards, key=lambda c: score_card(c, land_count), reverse=True)
                kept = scored[:keep_n]
                kept_names = [c['name'] for c in kept]
                evals = evaluate_hand(kept, labels, cache, seat)
                decision, reason = keep_or_mull(evals, args.pod, seat, labels)
                step_obj = {
                    'keep_n': keep_n,
                    'hand': hand_names,
                    'kept': kept_names,
                    'decision': decision,
                    'reason': reason,
                    'commander_turn': evals['commander_turn'],
                    'castable_t1': evals['castable_t1'],
                    'castable_t2': evals['castable_t2'],
                    'castable_t3': evals['castable_t3'],
                }
                if args.explain:
                    step_obj['explain'] = explain_hits(evals)
                steps.append(step_obj)
            outputs.append({
                'hand_index': i + 1,
                'pod': args.pod,
                'seat': seat,
                'mulligan_steps': steps
            })
        else:
            hand_names = random.sample(deck, args.draw)
            hand_cards = [card_data[n] for n in hand_names]
            evals = evaluate_hand(hand_cards, labels, cache, seat)
            decision, reason = keep_or_mull(evals, args.pod, seat, labels)

            obj = {
                'hand_index': i + 1,
                'hand': hand_names,
                'colors': evals['colors'] or 'none',
                't1_total': evals['t1_total'],
                't2_total': evals['t2_total'],
                't3_total': evals['t3_total'],
                'commander_turn': evals['commander_turn'],
                'castable_t1': evals['castable_t1'],
                'castable_t2': evals['castable_t2'],
                'castable_t3': evals['castable_t3'],
                'pod': args.pod,
                'seat': seat,
                'decision': decision,
                'reason': reason,
            }
            if args.explain:
                obj['explain'] = explain_hits(evals)
            outputs.append(obj)

    if args.json:
        print(json.dumps(outputs, indent=2))
        return

    for o in outputs:
        print(f"\nHand {o['hand_index']}:")
        if 'mulligan_steps' in o:
            for step in o['mulligan_steps']:
                print(f"\n  Mull to {step['keep_n']} (keep {step['keep_n']}, bottom {7 - step['keep_n']}):")
                for n in step['hand']:
                    print(f"    - {n}")
                print(f"    Kept: {', '.join(step['kept'])}")
                print(f"    Commander by: {step['commander_turn']}")
                print(f"    Castable T1: {', '.join(step['castable_t1'])}")
                print(f"    Castable T2: {', '.join(step['castable_t2'])}")
                print(f"    Castable T3: {', '.join(step['castable_t3'])}")
                print(f"    Decision ({o['pod']} pod, seat {o['seat']}): {step['decision']} — {step['reason']}")
                if args.explain and 'explain' in step:
                    ex = step['explain']
                    print(f"    Explain: interaction={ex['interaction']}, engines={ex['engines']}, tutors={ex['tutors']}, wins={ex['wins']}")
        else:
            for n in o['hand']:
                print(f"  - {n}")
            print(f"\nColors available: {o['colors']}")
            print(f"T1 total mana (optimistic): {o['t1_total']}")
            print(f"T2 total mana (optimistic): {o['t2_total']}")
            print(f"T3 total mana (optimistic): {o['t3_total']}")
            print(f"Commander castable by (optimistic): {o['commander_turn']}")
            print(f"Castable T1 (optimistic): {', '.join(o['castable_t1'])}")
            print(f"Castable T2 (optimistic): {', '.join(o['castable_t2'])}")
            print(f"Castable T3 (optimistic): {', '.join(o['castable_t3'])}")
            print(f"Decision ({o['pod']} pod, seat {o['seat']}): {o['decision']} — {o['reason']}")
            if args.explain and 'explain' in o:
                ex = o['explain']
                print(f"Explain: interaction={ex['interaction']}, engines={ex['engines']}, tutors={ex['tutors']}, wins={ex['wins']}")


if __name__ == '__main__':
    main()
