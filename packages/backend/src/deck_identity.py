"""Deck-identity extraction and commander-name normalization (ADR 0015).

Everything that turns a raw TopDeck standing (decklist text and/or structured
``deckObj``) into a canonical per-game deck identity lives here: the cEDH commander
domain that historically lived in ``ingest.py`` plus the per-game extractor dispatch
used by the multi-game pipeline. ``ingest.py`` re-exports the public names so existing
``from ingest import X`` call sites keep working.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from game_registry import GameConfig

UNKNOWN_IDENTITY = "Unknown Commander"


COMMANDER_NAME_ALIASES: dict[str, str] = {
    "Chief Jim Hopper": "Sophina, Spearsage Deserter",
    "Dustin, Gadget Genius": "Hargilde, Kindly Runechanter",
    "Eleven, the Mage": "Cecily, Haunted Mage",
    "Lucas, the Sharpshooter": "Bjorna, Nightfall Alchemist",
    "Max, the Daredevil": "Elmar, Ulvenwald Informant",
    "Mike, the Dungeon Master": "Othelm, Sigardian Outcast",
    "Mind Flayer, the Shadow": "Arvinox, the Mind Flail",
    "Will the Wise": "Wernog, Rider's Chaplain",
}


def clean_commander_card_name(name: str) -> str:
    """Normalize an individual commander card name.

    This removes escaped quotes, strips DFC/MDFC back faces, and drops any
    trailing set-indicator suffix.
    """
    if not name:
        return ""
    cleaned = name.replace("\\'", "'").replace('\\"', '"')
    front_face = cleaned.split(" // ", 1)[0]
    normalized = front_face.split("[", 1)[0].strip()
    return COMMANDER_NAME_ALIASES.get(normalized, normalized)


@lru_cache(maxsize=1)
def load_legal_commander_pair_names() -> set[str]:
    """Load canonical legal two-card commander pair names."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "legal_commander_pairings.json"
    payload = json.loads(data_path.read_text())
    names = payload.get("legal_pair_names") or []
    return {str(name) for name in names}


@lru_cache(maxsize=1)
def load_legal_commander_pair_order_map() -> dict[tuple[str, str], tuple[str, str]]:
    """Load canonical ordering for all legal two-card commander pairings."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "legal_commander_pairings.json"
    payload = json.loads(data_path.read_text())
    pairs = payload.get("legal_pairs") or []
    order_map: dict[tuple[str, str], tuple[str, str]] = {}
    for pair in pairs:
        canonical_name = str(pair.get("project_name") or "").strip()
        canonical_parts = [clean_commander_card_name(part) for part in canonical_name.split(" / ") if part.strip()]
        if len(canonical_parts) != 2:
            continue
        names = pair.get("commander_names") or []
        if not isinstance(names, list) or len(names) != 2:
            continue
        cleaned = [clean_commander_card_name(str(name)) for name in names]
        if len(cleaned) != 2 or not all(cleaned):
            continue
        order_map[tuple(sorted(cleaned))] = (canonical_parts[0], canonical_parts[1])
    return order_map


PARTNER_ORDER_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    tuple(sorted(["Kraum, Ludevic's Opus", "Tymna the Weaver"])): ("Tymna the Weaver", "Kraum, Ludevic's Opus"),
    tuple(sorted(["Thrasios, Triton Hero", "Tymna the Weaver"])): ("Tymna the Weaver", "Thrasios, Triton Hero"),
    tuple(sorted(["Rograkh, Son of Rohgahh", "Thrasios, Triton Hero"])): (
        "Rograkh, Son of Rohgahh",
        "Thrasios, Triton Hero",
    ),
    tuple(sorted(["Rograkh, Son of Rohgahh", "Silas Renn, Seeker Adept"])): (
        "Rograkh, Son of Rohgahh",
        "Silas Renn, Seeker Adept",
    ),
    tuple(sorted(["Malcolm, Keen-Eyed Navigator", "Tymna the Weaver"])): (
        "Malcolm, Keen-Eyed Navigator",
        "Tymna the Weaver",
    ),
    tuple(sorted(["Kraum, Ludevic's Opus", "Tevesh Szat, Doom of Fools"])): (
        "Tevesh Szat, Doom of Fools",
        "Kraum, Ludevic's Opus",
    ),
    tuple(sorted(["Dargo, the Shipwrecker", "Tymna the Weaver"])): ("Dargo, the Shipwrecker", "Tymna the Weaver"),
    tuple(sorted(["Krark, the Thumbless", "Sakashima of a Thousand Faces"])): (
        "Krark, the Thumbless",
        "Sakashima of a Thousand Faces",
    ),
    tuple(sorted(["Tevesh Szat, Doom of Fools", "Thrasios, Triton Hero"])): (
        "Tevesh Szat, Doom of Fools",
        "Thrasios, Triton Hero",
    ),
    tuple(sorted(["Pako, Arcane Retriever", "Haldan, Avid Arcanist"])): (
        "Pako, Arcane Retriever",
        "Haldan, Avid Arcanist",
    ),
    tuple(sorted(["Tana, the Bloodsower", "Tymna the Weaver"])): ("Tymna the Weaver", "Tana, the Bloodsower"),
    tuple(sorted(["Vial Smasher the Fierce", "Malcolm, Keen-Eyed Navigator"])): (
        "Malcolm, Keen-Eyed Navigator",
        "Vial Smasher the Fierce",
    ),
    tuple(sorted(["Kediss, Emberclaw Familiar", "Malcolm, Keen-Eyed Navigator"])): (
        "Malcolm, Keen-Eyed Navigator",
        "Kediss, Emberclaw Familiar",
    ),
    tuple(sorted(["Bruse Tarl, Boorish Herder", "Thrasios, Triton Hero"])): (
        "Bruse Tarl, Boorish Herder",
        "Thrasios, Triton Hero",
    ),
    tuple(sorted(["Ikra Shidiqi, the Usurper", "Kraum, Ludevic's Opus"])): (
        "Ikra Shidiqi, the Usurper",
        "Kraum, Ludevic's Opus",
    ),
    tuple(sorted(["Francisco, Fowl Marauder", "Thrasios, Triton Hero"])): (
        "Francisco, Fowl Marauder",
        "Thrasios, Triton Hero",
    ),
    tuple(sorted(["Malcolm, Keen-Eyed Navigator", "Tana, the Bloodsower"])): (
        "Malcolm, Keen-Eyed Navigator",
        "Tana, the Bloodsower",
    ),
    tuple(sorted(["Malcolm, Keen-Eyed Navigator", "Francisco, Fowl Marauder"])): (
        "Malcolm, Keen-Eyed Navigator",
        "Francisco, Fowl Marauder",
    ),
    tuple(sorted(["Jeska, Thrice Reborn", "Tymna the Weaver"])): ("Jeska, Thrice Reborn", "Tymna the Weaver"),
    tuple(sorted(["Kodama of the East Tree", "Tymna the Weaver"])): ("Kodama of the East Tree", "Tymna the Weaver"),
    tuple(sorted(["Rograkh, Son of Rohgahh", "Tymna the Weaver"])): (
        "Rograkh, Son of Rohgahh",
        "Tymna the Weaver",
    ),
    tuple(sorted(["Rograkh, Son of Rohgahh", "Tevesh Szat, Doom of Fools"])): (
        "Rograkh, Son of Rohgahh",
        "Tevesh Szat, Doom of Fools",
    ),
    tuple(sorted(["Ardenn, Intrepid Archaeologist", "Tana, the Bloodsower"])): (
        "Ardenn, Intrepid Archaeologist",
        "Tana, the Bloodsower",
    ),
    tuple(sorted(["Jeska, Thrice Reborn", "Ishai, Ojutai Dragonspeaker"])): (
        "Jeska, Thrice Reborn",
        "Ishai, Ojutai Dragonspeaker",
    ),
    tuple(sorted(["Rograkh, Son of Rohgahh", "Ishai, Ojutai Dragonspeaker"])): (
        "Rograkh, Son of Rohgahh",
        "Ishai, Ojutai Dragonspeaker",
    ),
    tuple(sorted(["Rograkh, Son of Rohgahh", "Reyhan, Last of the Abzan"])): (
        "Rograkh, Son of Rohgahh",
        "Reyhan, Last of the Abzan",
    ),
    tuple(sorted(["Ukkima, Stalking Shadow", "Cazur, Ruthless Stalker"])): (
        "Ukkima, Stalking Shadow",
        "Cazur, Ruthless Stalker",
    ),
}


def normalize_partner_order(names: list[str]) -> list[str]:
    """Return canonical partner ordering for a list of commander names."""
    clean_names = [clean_commander_card_name(value) for value in names if clean_commander_card_name(value)]
    if len(clean_names) != 2:
        return clean_names
    pair_key = tuple(sorted(clean_names))
    legal_pair_order = load_legal_commander_pair_order_map().get(pair_key)
    if legal_pair_order:
        return list(legal_pair_order)
    return list(PARTNER_ORDER_OVERRIDES.get(pair_key, pair_key))


def extract_commanders(decklist: str) -> list[str]:
    """Extract commander names from a decklist.

    Parses the ~Commanders~~ section to extract partner commanders.
    Returns a list of commander names (usually 1, or 2 for partner pairs).
    """
    if not decklist:
        return []

    # TopDeck sometimes returns decklists with literal escaped newlines instead of
    # actual line breaks. Normalize those first so the section parser can work.
    normalized_decklist = decklist.replace("\\r\\n", "\n").replace("\\n", "\n")

    commanders: list[str] = []
    in_commanders = False

    for line in normalized_decklist.split("\n"):
        line = line.strip()

        # Detect commander section
        if "~~Commanders~~" in line or "~~COMMANDERS~~" in line or "Commanders" in line:
            in_commanders = True
            continue

        # Stop at next section
        if in_commanders and line.startswith("~"):
            break

        if in_commanders and line:
            # Remove quantity prefix (e.g., "1 Commander Name" -> "Commander Name")
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                commanders.append(parts[1].strip())
            elif len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                # Partner pair like "1 Tymna the Weaver"
                commanders.append(parts[1] + " " + parts[2])
            else:
                commanders.append(line)

    return [clean_commander_card_name(c) for c in commanders if c]


def normalize_commander_name(commanders: list[str]) -> str:
    """Normalize commander pair name for consistent matching.

    Applies the project's canonical partner ordering for partner pairs.
    Single commanders are returned as-is.
    """
    clean_names = normalize_partner_order(commanders)
    if not clean_names:
        return UNKNOWN_IDENTITY
    return " / ".join(clean_names)


def sanitize_commander_payload(
    name: str | None,
    commander_names: list[str] | None,
) -> tuple[str, list[str]]:
    """Build a canonical commander row payload before persistence."""
    raw_names = commander_names or []
    clean_names: list[str] = []
    for value in raw_names:
        cleaned = clean_commander_card_name(value)
        if cleaned:
            clean_names.append(cleaned)
    if not clean_names and name:
        normalized = normalize_commander_name(name.split(" / "))
        clean_names = [part.strip() for part in normalized.split(" / ") if part.strip()]

    canonical_name = normalize_commander_name(clean_names)
    if len(clean_names) == 2 and canonical_name not in load_legal_commander_pair_names():
        return UNKNOWN_IDENTITY, [UNKNOWN_IDENTITY]
    if canonical_name == UNKNOWN_IDENTITY:
        return canonical_name, [UNKNOWN_IDENTITY]
    return canonical_name, [part.strip() for part in canonical_name.split(" / ") if part.strip()]


# ---------------------------------------------------------------------------
# Per-game identity extraction (multi-game pipeline)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeckSource:
    """Everything an identity extractor may look at for one standing."""

    decklist_text: str = ""
    deck_obj: dict[str, Any] | None = None
    standing: dict[str, Any] = field(default_factory=dict)


IdentityExtractor = Callable[[DeckSource], tuple[str, list[str]]]
"""Returns (canonical identity name, component card names)."""


def deck_obj_section_names(deck_obj: dict[str, Any] | None, section: str) -> list[str]:
    """Return the card names of one deckObj section ({<name>: {id, count}})."""
    if not isinstance(deck_obj, dict):
        return []
    bucket = deck_obj.get(section)
    if not isinstance(bucket, dict):
        return []
    return [str(name) for name in bucket if str(name).strip()]


def extract_identity_cedh(source: DeckSource) -> tuple[str, list[str]]:
    """Commander pair from decklist text, falling back to deckObj Commanders.

    The text path is byte-for-byte the legacy pipeline; the deckObj fallback only
    engages when the text yields nothing (e.g. bare Moxfield URLs).
    """
    commanders = extract_commanders(source.decklist_text)
    if not commanders:
        commanders = [clean_commander_card_name(name) for name in deck_obj_section_names(source.deck_obj, "Commanders")]
        commanders = [name for name in commanders if name]
    return normalize_commander_name(commanders), commanders


def extract_identity_riftbound(source: DeckSource) -> tuple[str, list[str]]:
    """Riftbound Legend from the deckObj Commanders-equivalent bucket."""
    legends = [name.strip() for name in deck_obj_section_names(source.deck_obj, "Commanders") if name.strip()]
    if not legends:
        return "Unknown Legend", []
    return " / ".join(sorted(legends)), sorted(legends)


def extract_identity_gundam(source: DeckSource) -> tuple[str, list[str]]:
    """Gundam deck identity — placeholder until leader extraction is defined.

    decklist_obj is persisted, so identities can be re-derived by a backfill once
    real Gundam deckObj payloads have been inspected (ADR 0015 appendix).
    """
    return "Unknown Deck", []


@cache
def load_ygo_archetype_rules(format_key: str) -> tuple[dict[str, Any], ...]:
    """Load ordered archetype classification rules for one YGO retro format.

    Rules file: packages/backend/data/ygo_archetypes/<format_key>.json with shape
    {"archetypes": [{"name": str, "signature_cards": [str, ...], "min_matches": int}]}.
    First rule whose signature-card matches reach min_matches (default 1) wins.
    """
    data_path = Path(__file__).resolve().parents[1] / "data" / "ygo_archetypes" / f"{format_key}.json"
    if not data_path.exists():
        return ()
    payload = json.loads(data_path.read_text())
    rules = payload.get("archetypes") or []
    return tuple(rule for rule in rules if isinstance(rule, dict) and rule.get("name"))


def classify_ygo_archetype(format_key: str, mainboard_names: list[str]) -> tuple[str, list[str]]:
    """Classify a YGO deck into an archetype from its mainboard card names."""
    normalized = {name.strip().lower() for name in mainboard_names if name.strip()}
    for rule in load_ygo_archetype_rules(format_key):
        signature = [str(card) for card in rule.get("signature_cards") or []]
        matches = [card for card in signature if card.strip().lower() in normalized]
        min_matches = int(rule.get("min_matches") or 1)
        if signature and len(matches) >= min_matches:
            return str(rule["name"]), matches
    return "Unknown Archetype", []


def make_ygo_extractor(format_key: str) -> IdentityExtractor:
    """Build a data-driven archetype extractor for one YGO retro format."""

    def extract(source: DeckSource) -> tuple[str, list[str]]:
        mainboard = deck_obj_section_names(source.deck_obj, "Mainboard")
        return classify_ygo_archetype(format_key, mainboard)

    return extract


IDENTITY_EXTRACTORS: dict[str, IdentityExtractor] = {
    "cedh": extract_identity_cedh,
    "riftbound": extract_identity_riftbound,
    "gundam": extract_identity_gundam,
    "ygo-edison": make_ygo_extractor("edison"),
    "ygo-goat": make_ygo_extractor("goat"),
}


def get_identity_extractor(config: GameConfig) -> IdentityExtractor:
    """Return the extractor for a game config, defaulting to the cEDH extractor."""
    return IDENTITY_EXTRACTORS.get(config.key, extract_identity_cedh)
