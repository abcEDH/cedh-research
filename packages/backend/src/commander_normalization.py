"""Commander name/pair canonicalization used at ingestion write time.

Extracted from ``ingest.py`` (see ``AGENTS.md``'s module-extraction rule): this
module owns every pure function that decides what a commander row's ``name``
and ``commander_names`` should be, independent of any Supabase I/O. It is the
single source of truth both ``ingest.py`` (write path) and
``sweep_partner_commander_order.py`` (one-off backfill) use to decide partner
order, so the two can never disagree about which of "A, B" / "B, A" is
canonical -- see issue #260.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


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
    if normalized in COMMANDER_NAME_ALIASES:
        return COMMANDER_NAME_ALIASES[normalized]
    return load_commander_oracle_aliases().get(normalized, normalized)


COMMANDER_NAME_ALIASES: dict[str, str] = {
    # "Secret Lair x Stranger Things" character-name -> Innistrad-commander
    # mappings. An earlier pass on PR #265's Codex review incorrectly
    # concluded these were fabricated, having checked only the Scryfall
    # `flavor_name` field. Re-verified: this Secret Lair drop actually
    # records its rebrand via `printed_name` (normally a foreign-language
    # localization field, but reused here for an English-language rebrand
    # while keeping `lang: "en"`) -- e.g. Sophina, Spearsage Deserter's
    # `sld` printing has `printed_name: "Chief Jim Hopper"`, no
    # `flavor_name` at all. All 8 confirmed real via oracle_id printing
    # lookups. `commander_oracle_identity.py`'s `alternate_display_names()`
    # now checks both fields, so the generated
    # `commander_oracle_aliases.json` also covers these -- this hardcoded
    # dict is kept anyway as a guaranteed, generation-independent fallback.
    "Chief Jim Hopper": "Sophina, Spearsage Deserter",
    "Dustin, Gadget Genius": "Hargilde, Kindly Runechanter",
    "Eleven, the Mage": "Cecily, Haunted Mage",
    "Lucas, the Sharpshooter": "Bjorna, Nightfall Alchemist",
    "Max, the Daredevil": "Elmar, Ulvenwald Informant",
    "Mike, the Dungeon Master": "Othelm, Sigardian Outcast",
    "Mind Flayer, the Shadow": "Arvinox, the Mind Flail",
    "Will the Wise": "Wernog, Rider's Chaplain",
}


@lru_cache(maxsize=1)
def load_commander_oracle_aliases() -> dict[str, str]:
    """Load the generated Universes Beyond flavor-name -> true-name alias map.

    This is the ingestion-time half of issue #261's oracle_id dedup: names are
    pre-resolved into this artifact by ``generate_commander_oracle_aliases.py``
    (keyed off Scryfall ``oracle_id``) so new UB alternate-name commanders are
    normalized automatically, without requiring a manual
    ``COMMANDER_NAME_ALIASES`` entry for every new printing. Falls back to an
    empty map if the artifact hasn't been generated yet.
    """
    data_path = Path(__file__).resolve().parents[1] / "data" / "commander_oracle_aliases.json"
    if not data_path.exists():
        return {}
    payload = json.loads(data_path.read_text())
    aliases = payload.get("aliases") or {}
    return {str(key): str(value) for key, value in aliases.items()}


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


def normalize_commander_name(commanders: list[str]) -> str:
    """Normalize commander pair name for consistent matching.

    Applies the project's canonical partner ordering for partner pairs.
    Single commanders are returned as-is.
    """
    clean_names = normalize_partner_order(commanders)
    if not clean_names:
        return "Unknown Commander"
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
        return "Unknown Commander", ["Unknown Commander"]
    if canonical_name == "Unknown Commander":
        return canonical_name, ["Unknown Commander"]
    return canonical_name, [part.strip() for part in canonical_name.split(" / ") if part.strip()]
