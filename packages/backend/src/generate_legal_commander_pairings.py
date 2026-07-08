#!/usr/bin/env python3
"""Generate a canonical list of legal two-card commander pairings."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from ingest import normalize_commander_name

SCRYFALL_BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
ORACLE_BULK_TYPE = "oracle_cards"

PARTNER_WITH_PREFIX = "partner with "
PARTNER_DESIGNATOR_PATTERN = re.compile(r"^partner(?:\s*[—-]\s*|\s+)(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class CommanderCard:
    name: str
    display_name: str
    oracle_id: str
    scryfall_id: str
    type_line: str
    oracle_text: str
    color_identity: tuple[str, ...]
    is_commander_legal: bool
    is_legendary_background: bool
    has_partner: bool
    partner_designator: str | None
    partner_with_name: str | None
    has_friends_forever: bool
    has_choose_a_background: bool
    has_doctors_companion: bool
    is_time_lord_doctor: bool


def front_face_name(raw_name: str) -> str:
    return raw_name.split(" // ", 1)[0].strip()


def strip_reminder_text(raw_text: str) -> str:
    return raw_text.split(" (", 1)[0].strip()


def front_face_value(card: dict[str, Any], key: str) -> str:
    faces = card.get("card_faces")
    if isinstance(faces, list) and faces:
        value = faces[0].get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = card.get(key)
    return value.strip() if isinstance(value, str) else ""


def extract_partner_traits(oracle_text: str) -> dict[str, Any]:
    traits = {
        "has_partner": False,
        "partner_designator": None,
        "partner_with_name": None,
        "has_friends_forever": False,
        "has_choose_a_background": False,
        "has_doctors_companion": False,
    }
    for raw_line in oracle_text.splitlines():
        line = raw_line.strip()
        lower = line.casefold()
        if lower == "partner" or lower.startswith("partner ("):
            traits["has_partner"] = True
            continue
        if lower.startswith(PARTNER_WITH_PREFIX):
            partner_name = strip_reminder_text(line[len("Partner with ") :].strip())
            if partner_name:
                traits["partner_with_name"] = front_face_name(partner_name)
            continue
        designator_match = PARTNER_DESIGNATOR_PATTERN.match(line)
        if designator_match and not lower.startswith("partner with "):
            designator = strip_reminder_text(designator_match.group(1).strip())
            if designator:
                normalized_designator = designator.casefold()
                if normalized_designator == "friends forever":
                    traits["has_friends_forever"] = True
                else:
                    traits["partner_designator"] = normalized_designator
            continue
        if lower == "friends forever" or lower.startswith("friends forever ("):
            traits["has_friends_forever"] = True
            continue
        if lower == "choose a background" or lower.startswith("choose a background ("):
            traits["has_choose_a_background"] = True
            continue
        if lower in {"doctor's companion", "doctor’s companion"} or lower.startswith("doctor's companion (") or lower.startswith("doctor’s companion ("):
            traits["has_doctors_companion"] = True
            continue
    return traits


def build_commander_card(card: dict[str, Any]) -> CommanderCard:
    name = front_face_name(card.get("name", ""))
    type_line = front_face_value(card, "type_line")
    oracle_text = front_face_value(card, "oracle_text")
    traits = extract_partner_traits(oracle_text)
    legalities = card.get("legalities") or {}
    is_commander_legal = legalities.get("commander") == "legal"
    is_legendary_background = (
        is_commander_legal and "Legendary" in type_line and "Background" in type_line
    )
    is_time_lord_doctor = is_commander_legal and "Time Lord" in type_line and "Doctor" in type_line
    color_identity = tuple(sorted(card.get("color_identity") or ()))
    return CommanderCard(
        name=name,
        display_name=name,
        oracle_id=str(card.get("oracle_id") or ""),
        scryfall_id=str(card.get("id") or ""),
        type_line=type_line,
        oracle_text=oracle_text,
        color_identity=color_identity,
        is_commander_legal=is_commander_legal,
        is_legendary_background=is_legendary_background,
        has_partner=bool(traits["has_partner"]),
        partner_designator=traits["partner_designator"],
        partner_with_name=traits["partner_with_name"],
        has_friends_forever=bool(traits["has_friends_forever"]),
        has_choose_a_background=bool(traits["has_choose_a_background"]),
        has_doctors_companion=bool(traits["has_doctors_companion"]),
        is_time_lord_doctor=is_time_lord_doctor,
    )


def fetch_bulk_cards(bulk_type: str, timeout: float) -> list[dict[str, Any]]:
    """Fetch a Scryfall bulk-data card list of the given ``bulk_type``.

    Shared by any script that needs raw Scryfall card payloads — e.g.
    ``oracle_cards`` (one row per oracle_id, used here for legal pairing rules)
    or ``default_cards`` (one row per printing, used by
    ``commander_oracle_identity.py`` for Universes Beyond alternate-name/
    oracle_id identity resolution).
    """
    bulk_response = requests.get(SCRYFALL_BULK_DATA_URL, timeout=timeout)
    bulk_response.raise_for_status()
    bulk_payload = bulk_response.json()
    bulk_items = bulk_payload.get("data") or []
    bulk_item = next((item for item in bulk_items if item.get("type") == bulk_type), None)
    if not bulk_item or not bulk_item.get("download_uri"):
        raise RuntimeError(f"Unable to locate Scryfall {bulk_type} bulk download")
    cards_response = requests.get(bulk_item["download_uri"], timeout=timeout)
    cards_response.raise_for_status()
    return cards_response.json()


def fetch_oracle_cards(timeout: float) -> list[dict[str, Any]]:
    return fetch_bulk_cards(ORACLE_BULK_TYPE, timeout)


def add_pair(
    pair_map: dict[tuple[str, str], dict[str, Any]],
    left: CommanderCard,
    right: CommanderCard,
    *,
    rule: str,
    detail: str | None = None,
) -> None:
    if left.name == right.name:
        return
    sorted_names = tuple(sorted((left.name, right.name)))
    entry = pair_map.get(sorted_names)
    candidate = {
        "project_name": normalize_commander_name(list(sorted_names)),
        "sorted_name": " / ".join(sorted_names),
        "commander_names": list(sorted_names),
        "rule": rule,
        "detail": detail,
        "color_identity": "".join(sorted(set(left.color_identity) | set(right.color_identity))),
        "scryfall_ids": [left.scryfall_id, right.scryfall_id],
    }
    if entry is None:
        pair_map[sorted_names] = candidate
        return
    if candidate["rule"] < entry["rule"]:
        pair_map[sorted_names] = candidate


def build_pairings(cards: list[CommanderCard]) -> dict[tuple[str, str], dict[str, Any]]:
    pair_map: dict[tuple[str, str], dict[str, Any]] = {}
    legal_cards = [card for card in cards if card.is_commander_legal]
    by_name = {card.name: card for card in legal_cards}

    plain_partner_cards = [card for card in legal_cards if card.has_partner]
    for left, right in itertools.combinations(plain_partner_cards, 2):
        add_pair(pair_map, left, right, rule="partner")

    by_designator: dict[str, list[CommanderCard]] = defaultdict(list)
    for card in legal_cards:
        if card.partner_designator:
            by_designator[card.partner_designator].append(card)
    for designator, group in by_designator.items():
        for left, right in itertools.combinations(group, 2):
            add_pair(pair_map, left, right, rule="partner_designator", detail=designator)

    for card in legal_cards:
        if not card.partner_with_name:
            continue
        partner = by_name.get(card.partner_with_name)
        if not partner or partner.partner_with_name != card.name:
            continue
        add_pair(pair_map, card, partner, rule="partner_with", detail=card.name)

    friends_forever_cards = [card for card in legal_cards if card.has_friends_forever]
    for left, right in itertools.combinations(friends_forever_cards, 2):
        add_pair(pair_map, left, right, rule="friends_forever")

    background_cards = [card for card in legal_cards if card.is_legendary_background]
    choose_background_cards = [card for card in legal_cards if card.has_choose_a_background]
    for commander, background in itertools.product(choose_background_cards, background_cards):
        add_pair(pair_map, commander, background, rule="choose_a_background")

    doctors_companion_cards = [card for card in legal_cards if card.has_doctors_companion]
    time_lord_doctors = [card for card in legal_cards if card.is_time_lord_doctor]
    for companion, doctor in itertools.product(doctors_companion_cards, time_lord_doctors):
        add_pair(pair_map, companion, doctor, rule="doctors_companion")

    return pair_map


def write_output(
    pair_map: dict[tuple[str, str], dict[str, Any]],
    *,
    output_path: Path,
    timeout: float,
) -> None:
    pairs = sorted(pair_map.values(), key=lambda row: (row["project_name"], row["rule"]))
    counts_by_rule = Counter(pair["rule"] for pair in pairs)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "Scryfall",
            "dataset": ORACLE_BULK_TYPE,
            "bulk_data_url": SCRYFALL_BULK_DATA_URL,
            "timeout_seconds": timeout,
        },
        "pair_count": len(pairs),
        "counts_by_rule": dict(sorted(counts_by_rule.items())),
        "legal_pair_names": [pair["project_name"] for pair in pairs],
        "legal_pairs": pairs,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate legal commander pairing reference data.")
    parser.add_argument(
        "--output",
        default="packages/backend/data/legal_commander_pairings.json",
        help="Path to the generated JSON file",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    raw_cards = fetch_oracle_cards(args.timeout)
    cards = [build_commander_card(card) for card in raw_cards]
    pair_map = build_pairings(cards)
    write_output(pair_map, output_path=Path(args.output), timeout=args.timeout)

    counts_by_rule = Counter(pair["rule"] for pair in pair_map.values())
    print(f"pair_count={len(pair_map)}")
    for rule, count in sorted(counts_by_rule.items()):
        print(f"{rule}={count}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
