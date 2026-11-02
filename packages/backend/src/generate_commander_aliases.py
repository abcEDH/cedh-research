#!/usr/bin/env python3
"""Generate verified name aliases from Scryfall printings (never fuzzy matching).

Canonical names come from Scryfall's name field. English printed_name and
flavor_name identify alternate names for that same oracle_id. Fetch all pages.
"""

import argparse
import json
import time
from pathlib import Path

import requests


def aliases_from_cards(cards):
    aliases = {}
    for card in cards:
        if card.get("lang") != "en" or not card.get("oracle_id"):
            continue
        faces = card.get("card_faces") or [card]
        # Front faces only: backs are not interchangeable commander identities.
        face = faces[0]
        canonical = face.get("name", card["name"]).split(" // ", 1)[0]
        for field in ("flavor_name", "printed_name"):
            alias = face.get(field) or card.get(field)
            if not alias:
                continue
            alias = alias.split(" // ", 1)[0]
            if alias == canonical:
                continue
            if alias in aliases and aliases[alias]["canonical_name"] != canonical:
                raise ValueError(f"Ambiguous Scryfall alias: {alias}")
            aliases[alias] = {
                "alias": alias,
                "canonical_name": canonical,
                "oracle_id": card["oracle_id"],
                "source": card["scryfall_uri"],
            }
    return sorted(aliases.values(), key=lambda r: r["alias"])


def fetch_cards(session, query):
    url = "https://api.scryfall.com/cards/search"
    params = {"q": query, "unique": "prints", "include_extras": "true"}
    cards = []
    while url:
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        if data.get("warnings"):
            raise RuntimeError(data["warnings"])
        cards.extend(data["data"])
        url = data.get("next_page") if data.get("has_more") else None
        params = None
        time.sleep(0.12)
    print(f"{query}: {len(cards)} printings", flush=True)
    return cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/commander_name_aliases.json"
    )
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": "tedh.gg commander alias audit", "Accept": "application/json"})
    response = session.get("https://api.scryfall.com/sets", timeout=60)
    response.raise_for_status()
    omenpaths = [s["code"] for s in response.json()["data"] if "omenpaths" in s["name"].lower()]
    cards = []
    for query in ["has:flavorname lang:en", "set:sld lang:en", *[f"set:{code} lang:en" for code in omenpaths]]:
        cards.extend(fetch_cards(session, query))
    aliases = aliases_from_cards(cards)
    args.output.write_text(json.dumps(aliases, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(aliases)} verified aliases to {args.output}", flush=True)


if __name__ == "__main__":
    main()
