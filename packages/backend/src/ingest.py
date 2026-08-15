#!/usr/bin/env python3
"""
cEDH Analytics Data Ingestion Pipeline

Fetches tournament data from TopDeck.gg API and loads into Supabase.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser

from supabase_client import (
    SUPABASE_REST_BASE,
    DirectPostgresClient,
    SupabaseClient,
    _describe_request_failure,
    fetch_existing_tids,
)
from topdeck_client import (
    TOPDECK_FIRESTORE_PROJECT,
    TopDeckClient,
    decode_firestore_value,
    is_placeholder_player_name,
)

# Explicit re-exports — these names are imported from sub-modules so that
# existing scripts which do `from ingest import X` continue to work unchanged.
__all__ = [
    "SUPABASE_REST_BASE",
    "DirectPostgresClient",
    "SupabaseClient",
    "_describe_request_failure",
    "TOPDECK_FIRESTORE_PROJECT",
    "TopDeckClient",
    "decode_firestore_value",
]

TOPDECK_STANDING_RATE_FIELDS = [
    ("primaryWinRate", "opponentWinRate"),
    ("primaryWinRateElo", "opponentWinRateElo"),
    ("primaryWinRateO", "opponentWinRateO"),
    ("winRate", "opponentWinRate"),
    ("successRate", "opponentSuccessRate"),
]

# Reject tournaments whose start_date is further in the future than this grace
# period. A tournament with completed games/standings should already have
# happened (or be underway) by ingestion time — a start_date far in the future
# indicates test/placeholder data (e.g. TopDeck practice events) rather than a
# real, played event. The grace period tolerates timezone skew and same-day
# multi-region event scheduling without needing to be precise.
FUTURE_START_DATE_GRACE = timedelta(days=2)


# Ensure logs directory exists
_log_dir = Path(__file__).parent.parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_dir / "ingest.log"),
    ],
)
logger = logging.getLogger(__name__)


def load_local_env() -> None:
    """Load local env files without overriding already-exported variables."""
    for env_path in (Path("packages/backend/.env"), Path(".env"), Path(__file__).resolve().parents[1] / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def normalize_rate_value(value: Any) -> float | None:
    """Normalize TopDeck rate fields to a 0-1 float."""
    if value is None or value == "":
        return None

    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None

    if normalized < 0:
        return None
    if normalized > 1:
        normalized = normalized / 100
    if normalized > 1:
        return None

    return normalized


def extract_standing_rates(standing: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract normalized win rates from a standing record.

    Scans TOPDECK_STANDING_RATE_FIELDS for non-empty primary and opponent rates,
    returning them as floats in [0, 1]. If no rate is found for a category, returns
    None for that slot.
    """
    primary_rate: float | None = None
    for primary_rate_key, _ in TOPDECK_STANDING_RATE_FIELDS:
        primary_rate = normalize_rate_value(standing.get(primary_rate_key))
        if primary_rate is not None:
            break

    opponent_rate: float | None = None
    for _, opponent_rate_key in TOPDECK_STANDING_RATE_FIELDS:
        opponent_rate = normalize_rate_value(standing.get(opponent_rate_key))
        if opponent_rate is not None:
            break

    return primary_rate, opponent_rate


def resolve_record_fields(info: dict[str, Any]) -> dict[str, int]:
    """Resolve wins/losses/draws for a standing entry.

    Only returns fields TopDeck reports explicitly. Point totals are not
    derived into wins/draws: scoring formulas vary per tournament/organizer
    (flat 5-per-win, league/ladder scoring, etc.), so points is not a
    reliable stand-in for an explicit record. Deriving from it can fabricate
    impossible win counts (e.g. points=1866 on a 5-round event).
    """
    fields: dict[str, int] = {}
    if info.get("wins") is not None:
        fields["wins"] = info["wins"]
    if info.get("losses") is not None:
        fields["losses"] = info["losses"]
    if info.get("draws") is not None:
        fields["draws"] = info["draws"]
    return fields


def clean_commander_card_name(name: str) -> str:
    """Normalize an individual commander card name.

    This removes escaped quotes, normalizes Unicode curly quotes to their
    straight ASCII equivalents, strips DFC/MDFC back faces, and drops any
    trailing set-indicator suffix.
    """
    if not name:
        return ""
    cleaned = name.replace("\\'", "'").replace('\\"', '"')
    # TopDeck/Moxfield decklist sources are inconsistent about curly vs.
    # straight quotes for apostrophes in card names (e.g. "Ludevic's Opus"
    # vs "Ludevic's Opus" with U+2019). Left uncorrected, this makes the same
    # commander pair hash to two different canonical_pair_key()/pair_key
    # tuples in normalize_partner_order() and sweep_partner_commander_order.py,
    # which is how partner pairs keep re-splitting into duplicate rows despite
    # PARTNER_ORDER_OVERRIDES already covering the pair.
    cleaned = cleaned.replace("’", "'").replace("‘", "'")
    cleaned = cleaned.replace("“", '"').replace("”", '"')
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


def normalize_region_name(
    state: str | None,
    city: str | None = None,
    country: str | None = None,
    venue: str | None = None,
) -> str | None:
    """Normalize state/region name for consistent regional Elo grouping.

    Args:
        state: Raw state/province name from TopDeck
        city: City name
        country: Country name
        venue: Venue name

    Returns:
        Normalized state name or None
    """
    if not state:
        return None

    normalized = state.upper().strip()

    # Known state abbreviations and alternate spellings
    state_normalizations = {
        "ALBERTA": "AB",
        "ANDALUCÍA": "ANDALUSIA",
        "ANDALUCIA": "ANDALUSIA",
        "ARAGÓN": "ARAGON",
        "ARAGON": "ARAGON",
        "AUCKLAND": "AUCKLAND",
        "BADA WURTTEMBERG": "BADEN-WURTTEMBERG",
        "BADA-WURTTEMBERG": "BADEN-WURTTEMBERG",
        "BADEN-WURTTEMBERG": "BADEN-WURTTEMBERG",
        "BADEN-WÜRTTEMBERG": "BADEN-WURTTEMBERG",
        "BAVARIA": "BAYERN",
        "BAYERN": "BAYERN",
        "BERLIN": "BERLIN",
        "BOGOTA": "BOGOTA",
        "BOGOTÁ": "BOGOTA",
        "BRITISH COLUMBIA": "BC",
        "BRITISH COLUMBIA, CANADA": "BC",
        "CITY OF": "",
        "CONNECTICUT": "CT",
        "D.C.": "DC",
        "D.C": "DC",
        "D.C., US": "DC",
        "DISTRICT OF COLUMBIA": "DC",
        "ENGLAND": "ENGLAND",
        "FLEVOLAND": "FLEVOLAND",
        "FLORIDA": "FL",
        "GELDERLAND": "GELDERLAND",
        "GEORGIA": "GA",
        "GIRALTAR": "GIBRALTAR",
        "GÜELL": "GIRONA",
        "HAUTE GARONNE": "HAUTE-GARONNE",
        "HAUTE-GARONNE": "HAUTE-GARONNE",
        "ILLINOIS": "IL",
        "INDIANA": "IN",
        "KANSAS": "KS",
        "KENTUCKY": "KY",
        "LIMBURG": "LIMBURG",
        "LOUISIANA": "LA",
        "MARYLAND": "MD",
        "MASSACHUSETTS": "MA",
        "MICHIGAN": "MI",
        "MINNESOTA": "MN",
        "MISSOURI": "MO",
        "MORAVIAN-SILESIAN REGION": "MORAVIAN-SILESIAN",
        "NEBRASKA": "NE",
        "NEVADA": "NV",
        "NEW BRUNSWICK": "NB",
        "NEW JERSEY": "NJ",
        "NEW SOUTH WALES": "NSW",
        "NEW YORK": "NY",
        "NEW ZEALAND": "NZ",
        "NORTH CAROLINA": "NC",
        "NORTH RHINE-WESTPHALIA": "NORTH RHINE-WESTPHALIA",
        "NORTH RHINE-WESTPHALIA, GERMANY": "NORTH RHINE-WESTPHALIA",
        "NORTHERN TERRITORY": "NT",
        "NORTHWEST TERRITORIES": "NT",
        "NOTthing": "NOTTINGHAM",
        "NOTTINGHAMSHIRE": "NOTTINGHAM",
        "NOTTM": "NOTTINGHAM",
        "NOUVEAU BRUNSWICK": "NB",
        "ONTARIO": "ON",
        "OREGON": "OR",
        "PENNSYLVANIA": "PA",
        "PÉRDUES": "PORDIMON",
        "PRAGUE": "PRAGUE",
        "PRAGUE CITY": "PRAGUE",
        "PROVINCE OF": "",
        "QUEBEC": "QC",
        "QUEENSLAND": "QLD",
        "RÉPUBLIQUE TCHÈQUE": "CZ",
        "REGION OF": "",
        "RHONE": "RHONE",
        "SAARLAND": "SAARLAND",
        "SASKATCHEWAN": "SK",
        "SCOTLAND": "SCT",
        "SHIKOKU": "SHIKOKU",
        "SICILY": "SICILY",
        "SICH": "SICILY",
        "SINGAPORE": "SG",
        "SOUTH AUSTRALIA": "SA",
        "SOUTH CAROLINA": "SC",
        "SOUTH ENGLAND": "SOUTH ENGLAND",
        "SPAIN": "SPAIN",
        "STATE OF": "",
        "SWEDEN": "SWEDEN",
        "TERritory OF": "",
        "TEXAS": "TX",
        "THE NETHERLANDS": "NETHERLANDS",
        "THE NETHERLANDS, NL": "NETHERLANDS",
        "THURINGIA": "THURINGIA",
        "TOkyo": "TOKYO",
        "Tasmania": "TAS",
        "UNDEFINED": None,
        "UNIFIED TERRITORIES": "NT",
        "UNITED KINGDOM": "UK",
        "UTRECHT": "UTRECHT",
        "UTRECHT, NETHERLANDS": "UTRECHT",
        "UTTAR PRADESH": "UP",
        "VALENCIANA": "VALENCIA",
        "VICTORIA": "VIC",
        "VIRGINIA": "VA",
        "WASHINGTON": "WA",
        "WEST AUSTRALIA": "WA",
        "WEST MIDLANDS": "WEST MIDLANDS",
        "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI",
        "WYOMING": "WY",
        "YUKON": "YT",
    }

    # Direct match
    if normalized in state_normalizations:
        result = state_normalizations[normalized]
        if result is None or result == "":
            return None
        return result

    # Partial match for composite names
    for key, value in state_normalizations.items():
        if key in normalized or normalized in key:
            if value is None or value == "":
                return None
            return value

    # Return as-is if no normalization needed
    return normalized


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


def fetch_existing_partner_order_map(client: SupabaseClient) -> dict[tuple[str, str], tuple[str, str]]:
    """Map each known 2-commander pair (order-insensitive) to its already-established order.

    ``normalize_partner_order()`` picks a canonical order for a partner pair purely
    from static rules: ``legal_commander_pairings.json``, then
    ``PARTNER_ORDER_OVERRIDES``, then an alphabetical fallback for pairs neither
    source knows about. That rule-based order can drift from whatever order a
    pair's row was actually given in the ``commanders`` table -- e.g. a legacy row
    created before an override/legal-pairing entry existed, or a row renamed by
    ``sweep_partner_commander_order.py`` based on observed decklists without a
    matching ``PARTNER_ORDER_OVERRIDES`` entry ever being added.

    Without reconciling against the row that already exists, re-ingesting the
    same pair (in either name order) recomputes the rule-based name, which may no
    longer match the existing row's ``name`` -- so the ``on_conflict="name"``
    upsert can't find it and inserts a brand-new duplicate row instead (issue
    #260). Consulting this map before writing makes the *existing* row win, so a
    pair only ever gets one canonical row after its first ingestion -- no manual
    sweep required to keep new tournament data from re-splitting it.

    Ties (if a pair somehow already has more than one row) resolve to whichever
    row was created first, since rows are fetched oldest-first.
    """
    rows = client.select(
        "commanders",
        {"select": "commander_names,created_at", "limit": 20000, "order": "created_at.asc"},
    )
    order_map: dict[tuple[str, str], tuple[str, str]] = {}
    for row in rows:
        names = row.get("commander_names") or []
        if not isinstance(names, list) or len(names) != 2:
            continue
        cleaned = [clean_commander_card_name(str(value)) for value in names]
        if len(cleaned) != 2 or not all(cleaned):
            continue
        pair_key = tuple(sorted(cleaned))
        order_map.setdefault(pair_key, (cleaned[0], cleaned[1]))
    return order_map


class DataIngester:
    """Main ingestion orchestrator."""

    def __init__(
        self,
        topdeck: TopDeckClient,
        supabase: SupabaseClient,
    ):
        self.topdeck = topdeck
        self.supabase = supabase
        self.commander_cache: dict[str, str] = {}  # name -> id
        self.player_cache: dict[str, str] = {}  # topdeck_id -> id
        self._existing_partner_order_map: dict[tuple[str, str], tuple[str, str]] | None = None

    def _get_existing_partner_order_map(self) -> dict[tuple[str, str], tuple[str, str]]:
        """Lazily fetch and cache the DB's established partner-pair orderings."""
        if self._existing_partner_order_map is None:
            self._existing_partner_order_map = fetch_existing_partner_order_map(self.supabase)
        return self._existing_partner_order_map

    def _reconcile_partner_order(self, canonical_name: str, canonical_names: list[str]) -> tuple[str, list[str]]:
        """Prefer a pair's already-established DB order over a freshly computed one.

        See ``fetch_existing_partner_order_map`` for why this prevents partner
        pairs from splitting into "A, B" vs "B, A" rows across ingestion runs.
        """
        if len(canonical_names) != 2:
            return canonical_name, canonical_names
        pair_key = tuple(sorted(canonical_names))
        existing_order = self._get_existing_partner_order_map().get(pair_key)
        if existing_order and list(existing_order) != canonical_names:
            return " / ".join(existing_order), list(existing_order)
        return canonical_name, canonical_names

    def get_or_create_commander(self, name: str, commander_names: list[str]) -> str | None:
        """Get or create a commander entry, return UUID. (Legacy - use batch method)"""
        canonical_name, canonical_names = sanitize_commander_payload(name, commander_names)
        canonical_name, canonical_names = self._reconcile_partner_order(canonical_name, canonical_names)
        name = canonical_name
        if name in self.commander_cache:
            return self.commander_cache[name]

        # Try to find existing
        existing = self.supabase.select("commanders", {"name": f"eq.{name}"})
        if existing:
            self.commander_cache[name] = existing[0]["id"]
            return existing[0]["id"]

        # Create new
        data = {
            "name": name,
            "commander_names": canonical_names,
        }
        result = self.supabase.upsert("commanders", data, on_conflict="name")
        if result:
            self.commander_cache[name] = result[0]["id"]
            return result[0]["id"]
        return None

    def get_or_create_player(self, topdeck_id: str, name: str) -> str | None:
        """Get or create a player entry, return UUID. (Legacy - use batch method)"""
        if not topdeck_id:
            return None

        if topdeck_id in self.player_cache:
            return self.player_cache[topdeck_id]

        # Try to find existing
        existing = self.supabase.select("players", {"topdeck_id": f"eq.{topdeck_id}"})
        if existing:
            self.player_cache[topdeck_id] = existing[0]["id"]
            return existing[0]["id"]

        # Create new
        data = {"topdeck_id": topdeck_id, "name": name}
        result = self.supabase.upsert("players", data, on_conflict="topdeck_id")
        if result:
            self.player_cache[topdeck_id] = result[0]["id"]
            return result[0]["id"]
        return None

    def batch_upsert_commanders(self, commander_data: dict[str, list[str]]) -> dict[str, str]:
        """Batch upsert commanders and return original-key -> id mapping.

        Each entry's canonical name/order is reconciled against any
        already-established DB row for that pair (see
        ``_reconcile_partner_order``) before writing, so the returned mapping is
        keyed by ``commander_data``'s original keys rather than the possibly
        reconciled ``name`` -- callers (e.g. ``ingest_tournament``) look up
        commander ids by the pre-reconciliation name they already computed.
        """
        if not commander_data:
            return {}

        payload_by_original_key: dict[str, tuple[str, list[str]]] = {}
        for name, names in commander_data.items():
            canonical_name, canonical_names = sanitize_commander_payload(name, names)
            canonical_name, canonical_names = self._reconcile_partner_order(canonical_name, canonical_names)
            payload_by_original_key[name] = (canonical_name, canonical_names)

        # Dedupe by canonical name: reconciliation can make two distinct original
        # keys resolve to the same existing row, and a single upsert call can't
        # target the same on_conflict row twice.
        rows_by_canonical_name: dict[str, list[str]] = {}
        for canonical_name, canonical_names in payload_by_original_key.values():
            rows_by_canonical_name[canonical_name] = canonical_names
        data = [
            {"name": canonical_name, "commander_names": canonical_names}
            for canonical_name, canonical_names in rows_by_canonical_name.items()
        ]

        result = self.supabase.upsert("commanders", data, on_conflict="name")
        if not result:
            logger.error("Failed to batch upsert commanders")
            return {}

        name_to_id = {r["name"]: r["id"] for r in result}
        return {
            original_key: name_to_id[canonical_name]
            for original_key, (canonical_name, _canonical_names) in payload_by_original_key.items()
            if canonical_name in name_to_id
        }

    def batch_upsert_players(self, player_data: dict[str, str]) -> dict[str, str]:
        """Batch upsert players and return topdeck_id -> id mapping."""
        if not player_data:
            return {}

        unknown_topdeck_ids = [
            topdeck_id for topdeck_id, name in player_data.items() if is_placeholder_player_name(name)
        ]
        for start in range(0, len(unknown_topdeck_ids), 100):
            chunk = unknown_topdeck_ids[start : start + 100]
            existing_players = self.supabase.select(
                "players",
                {
                    "topdeck_id": f"in.({','.join(chunk)})",
                    "select": "topdeck_id,name",
                },
            )
            for existing_player in existing_players:
                topdeck_id = existing_player.get("topdeck_id")
                existing_name = existing_player.get("name")
                if topdeck_id and not is_placeholder_player_name(existing_name):
                    player_data[topdeck_id] = existing_name

        data = [{"topdeck_id": tid, "name": name} for tid, name in player_data.items()]

        result = self.supabase.upsert("players", data, on_conflict="topdeck_id")
        if not result:
            logger.error("Failed to batch upsert players")
            return {}

        return {r["topdeck_id"]: r["id"] for r in result}

    def batch_upsert_entries(self, entries: list[dict[str, Any]]) -> dict[str, str]:
        """Batch upsert tournament entries and return topdeck entry id -> db id mapping."""
        if not entries:
            return {}

        entry_keys_by_player_id = {
            entry["player_id"]: entry.get("topdeck_entry_id")
            for entry in entries
            if entry.get("player_id") and entry.get("topdeck_entry_id")
        }
        entries_by_keys: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for entry in entries:
            db_entry = {k: v for k, v in entry.items() if k != "topdeck_entry_id"}
            entries_by_keys[tuple(sorted(db_entry.keys()))].append(db_entry)

        result: list[dict[str, Any]] = []
        for db_entries in entries_by_keys.values():
            upserted = self.supabase.upsert("tournament_entries", db_entries, on_conflict="tournament_id,player_id")
            if upserted:
                result.extend(upserted)

        if not result:
            logger.error("Failed to batch upsert tournament entries")
            return {}

        entry_id_map: dict[str, str] = {}
        for row in result:
            topdeck_entry_id = entry_keys_by_player_id.get(row.get("player_id"))
            if topdeck_entry_id:
                entry_id_map[topdeck_entry_id] = row["id"]
        return entry_id_map

    def process_tournament(self, tournament: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single tournament and ingest all data.

        Args:
            tournament: Tournament data from TopDeck API

        Returns:
            Result summary or None on failure
        """
        tid = tournament.get("id")
        name = tournament.get("name", "Unknown Tournament")
        rounds = tournament.get("rounds", [])
        standings = tournament.get("standings", [])
        start_date = tournament.get("startDate")
        player_count = len(standings)
        swiss_rounds = tournament.get("swissNum", 0)
        reported_top_cut = tournament.get("topCut", 0)
        effective_top_cut = reported_top_cut
        if player_count <= 34:
            effective_top_cut = 4

        parsed_start = parse_tournament_start_date(tournament)
        if isinstance(parsed_start, datetime):
            naive_start = (
                parsed_start.astimezone(timezone.utc).replace(tzinfo=None)
                if parsed_start.tzinfo is not None
                else parsed_start
            )
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            if naive_start > now_utc + FUTURE_START_DATE_GRACE:
                logger.warning(
                    f"Skipping tournament '{name}' ({tid}): start_date {naive_start.isoformat()} "
                    f"is more than {FUTURE_START_DATE_GRACE} in the future. Refusing to ingest "
                    "test/placeholder events with implausible future dates."
                )
                return None

        logger.info(f"Processing: {name} ({player_count} players, {len(rounds)} rounds)")

        # Convert timestamp to ISO format
        if isinstance(start_date, (int, float)):
            start_date = datetime.fromtimestamp(start_date).isoformat()

        # Get location and tier data
        event_data = tournament.get("eventData", {})
        tier = self.topdeck.get_tournament_tier(tid)

        # Upsert tournament
        tournament_data: dict[str, Any] = {
            "topdeck_tid": tid,
            "name": name,
            "start_date": start_date,
            "player_count": player_count,
            "swiss_rounds": swiss_rounds,
            "top_cut": effective_top_cut,
            "average_elo": (int(tournament.get("averageElo")) if tournament.get("averageElo") else None),
            "median_elo": (int(tournament.get("medianElo")) if tournament.get("medianElo") else None),
            "top_elo": (int(tournament.get("topElo")) if tournament.get("topElo") else None),
            "city": event_data.get("city"),
            "state": normalize_region_name(
                event_data.get("state"),
                city=event_data.get("city"),
                country=event_data.get("country"),
                venue=event_data.get("location"),
            ),
            "venue": event_data.get("location"),
            "latitude": event_data.get("lat"),
            "longitude": event_data.get("lng"),
            "header_image_url": event_data.get("headerImage"),
            "tier": tier,
        }

        result = self.supabase.upsert("tournaments", tournament_data, on_conflict="topdeck_tid")
        if not result:
            logger.error(f"Failed to upsert tournament: {tid}")
            return None

        tournament_id = result[0]["id"]
        logger.info(f"Tournament ID: {tournament_id}")

        # === BATCH PROCESSING: Pre-process all data first ===
        total_players = len(standings)
        logger.info(f"Pre-processing {total_players} players...")

        # Step 1: Extract all unique commanders and players (local processing)
        commander_data: dict[str, list[str]] = {}  # name -> [individual_commander_names]
        player_data: dict[str, str] = {}  # topdeck_id -> name
        standing_info: list[dict[str, Any]] = []  # [{idx, topdeck_id, commander_name, decklist, ...}]

        for idx, standing in enumerate(standings):
            player_topdeck_id = standing.get("id")
            player_name = standing.get("name", "Unknown")
            decklist = standing.get("decklist") or ""

            # Extract and normalize commander
            commanders = extract_commanders(decklist)
            commander_name = normalize_commander_name(commanders)

            # Collect unique commanders
            if commander_name not in commander_data:
                commander_data[commander_name] = commanders

            # Collect unique players
            if player_topdeck_id and player_topdeck_id not in player_data:
                player_data[player_topdeck_id] = player_name

            standing_info.append(
                {
                    "idx": idx,
                    "topdeck_id": player_topdeck_id,
                    "name": player_name,
                    "commander_name": commander_name,
                    "decklist": decklist,
                    "rank": standing.get("rank") or standing.get("standing"),
                    "points": standing.get("points") or 0,
                    "wins": standing.get("wins"),
                    "losses": standing.get("losses"),
                    "draws": standing.get("draws"),
                    "omw": standing.get("omw"),
                    "gw": standing.get("gw"),
                    "pgw": standing.get("pgw"),
                    "primaryWinRate": standing.get("primaryWinRate"),
                    "primaryWinRateElo": standing.get("primaryWinRateElo"),
                    "primaryWinRateO": standing.get("primaryWinRateO"),
                    "winRate": standing.get("winRate"),
                    "successRate": standing.get("successRate"),
                    "opponentWinRate": standing.get("opponentWinRate"),
                    "opponentWinRateElo": standing.get("opponentWinRateElo"),
                    "opponentWinRateO": standing.get("opponentWinRateO"),
                    "opponentSuccessRate": standing.get("opponentSuccessRate"),
                }
            )

        # Some league / Firestore-backed events include players in round tables
        # who are absent from standings. If we only build tournament_entries from
        # standings, later game ingest drops those players and leaves partial
        # game rows with only losses recorded.
        known_standing_topdeck_ids = {str(info["topdeck_id"]) for info in standing_info if info.get("topdeck_id")}
        next_idx = len(standing_info)
        for round_data in rounds:
            for table in round_data.get("tables", []) or []:
                for player in table.get("players", []) or []:
                    player_topdeck_id = player.get("id")
                    if not player_topdeck_id:
                        continue
                    normalized_topdeck_id = str(player_topdeck_id)
                    if normalized_topdeck_id in known_standing_topdeck_ids:
                        continue
                    player_name = player.get("name") or "Unknown"
                    if normalized_topdeck_id not in player_data:
                        player_data[normalized_topdeck_id] = player_name
                    # Unknown / missing decklists are acceptable here; the
                    # important part is creating the player entry so games can
                    # attach all participants.
                    commander_name = normalize_commander_name([])
                    if commander_name not in commander_data:
                        commander_data[commander_name] = []
                    standing_info.append(
                        {
                            "idx": next_idx,
                            "topdeck_id": normalized_topdeck_id,
                            "name": player_name,
                            "commander_name": commander_name,
                            "decklist": "",
                            "rank": None,
                            "points": 0,
                            "wins": None,
                            "losses": None,
                            "draws": None,
                            "omw": None,
                            "gw": None,
                            "pgw": None,
                            "primaryWinRate": None,
                            "primaryWinRateElo": None,
                            "primaryWinRateO": None,
                            "winRate": None,
                            "successRate": None,
                            "opponentWinRate": None,
                            "opponentWinRateElo": None,
                            "opponentWinRateO": None,
                            "opponentSuccessRate": None,
                        }
                    )
                    known_standing_topdeck_ids.add(normalized_topdeck_id)
                    next_idx += 1

        # Step 2: Batch upsert commanders
        logger.info(f"Upserting {len(commander_data)} unique commanders...")
        commander_id_map = self.batch_upsert_commanders(commander_data)
        self.commander_cache.update(commander_id_map)

        # Step 3: Batch upsert players
        logger.info(f"Upserting {len(player_data)} unique players...")
        player_id_map = self.batch_upsert_players(player_data)
        self.player_cache.update(player_id_map)

        # Step 4: Build entry records
        entries: list[dict[str, Any]] = []
        seen_entry_player_ids: set[str] = set()
        for info in standing_info:
            commander_id = commander_id_map.get(info["commander_name"])
            player_id = player_id_map.get(info["topdeck_id"])

            if not commander_id or not player_id:
                logger.warning(
                    f"Missing commander or player for standing {info['idx']}: "
                    f"commander={commander_id}, player={player_id}"
                )
                continue

            if player_id in seen_entry_player_ids:
                logger.warning(f"Skipping duplicate standing for player {info['topdeck_id']} in tournament {tid}")
                continue
            seen_entry_player_ids.add(player_id)

            primary_rate, opponent_rate = extract_standing_rates(info)

            entry = {
                "tournament_id": tournament_id,
                "player_id": player_id,
                "commander_id": commander_id,
                "final_standing": info["rank"],
                "points": info["points"],
                "win_rate": primary_rate,
                "opponent_win_rate": opponent_rate,
                "decklist_text": info["decklist"],
                "topdeck_entry_id": f"{tid}_{info['topdeck_id']}",
            }

            # Only add W/L/D if they are explicitly present in the data, to avoid
            # overwriting existing values with zeros during re-ingestion.
            entry.update(resolve_record_fields(info))

            entries.append(entry)

        # Step 5: Batch upsert entries
        logger.info(f"Upserting {len(entries)} tournament entries...")
        entry_id_map = self.batch_upsert_entries(entries)

        # Step 6: Process game results
        games_processed = 0
        entries_by_topdeck_id = {
            e.get("topdeck_entry_id", "").removeprefix(f"{tid}_"): (e, db_id)
            for e, db_id in ((entry, entry_id_map.get(entry.get("topdeck_entry_id"))) for entry in entries)
            if e.get("topdeck_entry_id") and db_id
        }
        entries_by_rank = sorted(
            [
                (
                    e,
                    entry_id_map.get(e.get("topdeck_entry_id")),
                    e.get("rank", 999),
                )
                for e in entries
            ],
            key=lambda x: x[2],
        )

        # Process each round
        for round_data in rounds:
            round_value = round_data.get("round")
            round_num = round_value if isinstance(round_value, int) else None
            round_name = None if isinstance(round_value, int) else str(round_value) if round_value else None
            is_bracket = round_num is None
            tables = round_data.get("tables", [])

            for table in tables:
                table_num = table.get("table") or table.get("table_number") or table.get("tableNumber")
                seats = table.get("seats", [])
                players = table.get("players", [])

                # Build game participants map
                participant_map: dict[int, dict[str, Any]] = {}
                if players:
                    for seat_num, player in enumerate(players):
                        player_topdeck_id = player.get("id")
                        entry_pair = entries_by_topdeck_id.get(player_topdeck_id)
                        if entry_pair:
                            standing, db_id = entry_pair
                            participant_map[seat_num] = {
                                "entry_id": db_id,
                                "standing": standing,
                                "topdeck_id": player_topdeck_id,
                            }
                else:
                    for seat in seats:
                        seat_num = seat.get("seat", 0)
                        entry_id = seat.get("entryId")
                        # Find the entry by topdeck_entry_id
                        for e, db_id, _ in entries_by_rank:
                            if e.get("topdeck_entry_id") == entry_id:
                                participant_map[seat_num] = {
                                    "entry_id": db_id,
                                    "standing": e,
                                    "topdeck_id": e.get("topdeck_id"),
                                }
                                break

                if not participant_map:
                    continue

                game_key = build_game_key(tournament_id, round_num, round_name, table_num, is_bracket)
                winner_topdeck_id = table.get("winner_id") or table.get("winnerId")
                uses_topdeck_winner_id = "winner_id" in table or "winnerId" in table

                # Process current TopDeck v2 results.
                if uses_topdeck_winner_id:
                    is_draw = is_draw_winner_id(winner_topdeck_id)
                    winner_player_id = None if is_draw else player_id_map.get(str(winner_topdeck_id))

                    game_record = {
                        "tournament_id": tournament_id,
                        "round_number": round_num,
                        "round_name": round_name,
                        "is_bracket": is_bracket,
                        "table_number": table_num,
                        "status": table.get("status") or "Completed",
                        "is_draw": is_draw,
                        "winner_id": winner_player_id,
                        "game_key": game_key,
                    }

                    try:
                        game_result = self.supabase.upsert("games", game_record, on_conflict="game_key")
                        if game_result:
                            games_processed += 1
                            participant_records: list[dict[str, Any]] = []

                            for seat_num, participant in participant_map.items():
                                entry_id = participant.get("entry_id")
                                if not entry_id:
                                    continue

                                is_winner = not is_draw and participant.get("topdeck_id") == winner_topdeck_id
                                result_text = "draw" if is_draw else "win" if is_winner else "loss"

                                participant_record = {
                                    "game_id": game_result[0]["id"],
                                    "entry_id": entry_id,
                                    "seat_position": seat_num,
                                    "result": result_text,
                                    "points_earned": 1 if is_draw else 5 if is_winner else 0,
                                }
                                participant_records.append(participant_record)
                            if participant_records:
                                self.supabase.upsert(
                                    "game_participants",
                                    participant_records,
                                    on_conflict="game_id,entry_id",
                                )
                    except Exception as e:
                        logger.warning(f"Failed to upsert game {game_key}: {e}")
                    continue

                # Process legacy TopDeck results.
                results = table.get("results", [])
                for result in results:
                    winner_seats = result.get("winners", [])
                    draws = result.get("draws", [])

                    # Get winner/loser IDs
                    winner_entry_ids = [
                        participant_map[s]["entry_id"]
                        for s in winner_seats
                        if s in participant_map and participant_map[s].get("entry_id")
                    ]
                    if not winner_entry_ids and not draws:
                        continue
                    winner_player_id = None
                    if len(winner_seats) == 1 and winner_seats[0] in participant_map:
                        winner_topdeck_id = participant_map[winner_seats[0]].get("topdeck_id")
                        winner_player_id = player_id_map.get(winner_topdeck_id)

                    # Create game record
                    game_record = {
                        "tournament_id": tournament_id,
                        "round_number": round_num,
                        "round_name": round_name,
                        "is_bracket": is_bracket,
                        "table_number": table_num,
                        "status": table.get("status") or "Completed",
                        "is_draw": bool(draws) and not winner_entry_ids,
                        "winner_id": winner_player_id,
                        "game_key": game_key,
                    }

                    # Upsert game
                    try:
                        game_result = self.supabase.upsert("games", game_record, on_conflict="game_key")
                        if game_result:
                            games_processed += 1
                            participant_records: list[dict[str, Any]] = []

                            # Create participant records
                            for seat_num, participant in participant_map.items():
                                entry_id = participant.get("entry_id")
                                if not entry_id:
                                    continue

                                is_winner = seat_num in winner_seats
                                is_draw = seat_num in draws
                                result_text = "draw" if is_draw else "win" if is_winner else "loss"

                                participant_record = {
                                    "game_id": game_result[0]["id"],
                                    "entry_id": entry_id,
                                    "seat_position": seat_num,
                                    "result": result_text,
                                    "points_earned": 1 if is_draw else 5 if is_winner else 0,
                                }
                                participant_records.append(participant_record)
                            if participant_records:
                                self.supabase.upsert(
                                    "game_participants",
                                    participant_records,
                                    on_conflict="game_id,entry_id",
                                )
                    except Exception as e:
                        logger.warning(f"Failed to upsert game {game_key}: {e}")

        logger.info(f"Completed {name}: {len(entries)} entries, {games_processed} games")
        return {
            "tournament_id": tournament_id,
            "name": name,
            "topdeck_tid": tid,
            "entries": len(entries),
            "games": games_processed,
        }


def parse_tournament_start_date(tournament: dict[str, Any]) -> datetime | None:
    """Parse tournament start date from various formats."""
    start_date = tournament.get("startDate")
    if not start_date:
        return None

    try:
        if isinstance(start_date, (int, float)):
            return datetime.fromtimestamp(start_date)
        return date_parser.parse(str(start_date))
    except Exception:
        return None


def normalize_tournament_name(name: str) -> str:
    """Normalize tournament name for matching."""
    return name.lower().strip()


def build_game_key(
    tournament_id: str,
    round_num: int | None,
    round_name: str | None,
    table_num: int | None,
    is_bracket: bool,
) -> str:
    """Build the canonical game key used by the database trigger."""
    return "|".join(
        [
            tournament_id,
            str(round_num) if round_num is not None else "RNULL",
            round_name if round_name is not None else "RNNULL",
            str(table_num) if table_num is not None else "TNULL",
            str(is_bracket).lower(),
        ]
    )


def is_draw_winner_id(winner_id: Any) -> bool:
    """TopDeck v2 represents drawn pods as winner_id='Draw'."""
    return winner_id is None or str(winner_id).strip().lower() == "draw"


def extract_name_and_tid(tournament: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract normalized name and tid from a tournament dict."""
    name = tournament.get("name")
    tid = tournament.get("id")
    return (normalize_tournament_name(name) if name else None, tid)


INGESTION_JOBS_TABLE = "ingestion_jobs"
INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE = 20


def claim_ingestion_job(client: SupabaseClient, job_id: str, github_run_id: int) -> bool:
    """Atomically claim an ingestion job by transitioning it to 'running'.

    Returns True if the job was claimed, False if it was already claimed by
    another runner (empty update result).  Raises on operational errors so the
    caller can distinguish conflicts from failures.
    """
    now = datetime.now().astimezone().isoformat()
    updated = client.update(
        INGESTION_JOBS_TABLE,
        {
            "status": "running",
            "github_run_id": github_run_id,
            "started_at": now,
            "heartbeat_at": now,
        },
        {"id": f"eq.{job_id}", "status": "in.(pending,dispatched)"},
    )
    return bool(updated)


def update_ingestion_heartbeat(client: SupabaseClient, job_id: str) -> None:
    """Best-effort heartbeat for ingestion job."""
    if not job_id:
        return
    try:
        client.update(
            INGESTION_JOBS_TABLE,
            {"heartbeat_at": datetime.now().astimezone().isoformat()},
            {"id": f"eq.{job_id}", "status": "eq.running"},
        )
    except Exception as exc:
        logger.warning(f"Ingestion heartbeat failed for {job_id} (safe to continue): {exc}")


def complete_ingestion_job(client: SupabaseClient, job_id: str, metrics: dict) -> None:
    """Mark ingestion job as completed with metrics."""
    now = datetime.now().astimezone().isoformat()
    client.update(
        INGESTION_JOBS_TABLE,
        {"status": "completed", "completed_at": now, "heartbeat_at": now, **metrics},
        {"id": f"eq.{job_id}", "status": "eq.running"},
    )


def fail_ingestion_job(client: SupabaseClient, job_id: str, error: str) -> None:
    """Mark ingestion job as failed."""
    try:
        client.update(
            INGESTION_JOBS_TABLE,
            {
                "status": "failed",
                "completed_at": datetime.now().astimezone().isoformat(),
                "error_text": error[:2000],
            },
            {"id": f"eq.{job_id}", "status": "in.(pending,dispatched,running)"},
        )
    except Exception as exc:
        logger.error(f"Failed to record ingestion failure for {job_id}: {exc}")


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def load_tids(path: Path) -> list[str]:
    """Load unique tournament IDs from a file, skipping blanks and comments."""
    seen: set[str] = set()
    result: list[str] = []
    for line in path.read_text().splitlines():
        tid = line.strip()
        if not tid or tid.startswith("#"):
            continue
        if tid not in seen:
            seen.add(tid)
            result.append(tid)
    return result


def write_tids(path: Path, tids: list[str], header_lines: list[str] | None = None) -> None:
    """Write tournament IDs to a file, one per line, with optional comment header."""
    lines = [f"# {h}" for h in (header_lines or [])] + tids
    path.write_text("\n".join(lines) + "\n")


def chunk_items(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into chunks of at most *size* items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def default_backfill_run_key(path: Path, batch_size: int) -> str:
    """Generate a default run key from the manifest path and current timestamp."""
    stem = path.stem
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"{stem}-bs{batch_size}-{ts}"


def fetch_failed_tids_for_run(client: SupabaseClient, run_key: str) -> list[str]:
    """Return TIDs marked as failed for a given backfill run key."""
    runs = client.select(
        "ingestion_backfill_runs",
        {"select": "id", "run_key": f"eq.{run_key}"},
    )
    if not runs:
        return []
    run_id = runs[0]["id"]
    events = client.select(
        "ingestion_backfill_events",
        {
            "select": "tid",
            "run_id": f"eq.{run_id}",
            "event_type": "eq.process_failed",
            "tid": "not.is.null",
        },
    )
    seen: set[str] = set()
    result: list[str] = []
    for row in events:
        tid = row.get("tid")
        if tid and tid not in seen:
            seen.add(tid)
            result.append(tid)
    return result


def upsert_backfill_run(
    client: SupabaseClient,
    run_key: str,
    tids_path: Path,
    batch_size: int,
    total_tournaments: int,
    total_batches: int,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str = "running",
) -> dict[str, Any] | None:
    """Upsert a row in ingestion_backfill_runs and return it."""
    import hashlib

    manifest_sha256 = hashlib.sha256(tids_path.read_bytes()).hexdigest()
    rows = client.upsert(
        "ingestion_backfill_runs",
        {
            "run_key": run_key,
            "manifest_path": str(tids_path),
            "manifest_sha256": manifest_sha256,
            "batch_size": batch_size,
            "discovered_tournament_count": total_tournaments,
            "total_batches": total_batches,
            "requested_start_date": start_date,
            "requested_end_date": end_date,
            "status": status,
            "updated_at": utc_now_iso(),
        },
        on_conflict="run_key",
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    if isinstance(rows, dict):
        return rows
    return None


def upsert_backfill_batch(
    client: SupabaseClient,
    run_id: str,
    batch_index: int,
    batch_start: int,
    batch_end: int,
    tournament_count: int,
    status: str = "running",
    error_text: str | None = None,
) -> dict[str, Any] | None:
    """Upsert a row in ingestion_backfill_batches and return it."""
    payload: dict[str, Any] = {
        "run_id": run_id,
        "batch_index": batch_index,
        "batch_start": batch_start,
        "batch_end": batch_end,
        "tournament_count": tournament_count,
        "status": status,
        "updated_at": utc_now_iso(),
    }
    if status == "running":
        payload["started_at"] = utc_now_iso()
    if status in ("completed", "failed"):
        payload["finished_at"] = utc_now_iso()
    if error_text is not None:
        payload["error_text"] = error_text
    rows = client.upsert(
        "ingestion_backfill_batches",
        payload,
        on_conflict="run_id,batch_index",
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    if isinstance(rows, dict):
        return rows
    return None


def append_backfill_event(
    client: SupabaseClient,
    run_id: str,
    batch_index: int,
    event_type: str,
    tid: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Insert a row into ingestion_backfill_events."""
    client.upsert(
        "ingestion_backfill_events",
        {
            "run_id": run_id,
            "batch_index": batch_index,
            "tid": tid,
            "event_type": event_type,
            "payload": payload or {},
        },
    )


def update_backfill_run_progress(
    client: SupabaseClient,
    run_row: dict[str, Any],
    processed_count: int,
    succeeded_count: int,
    failed_count: int,
    status: str = "running",
    current_batch_index: int | None = None,
    current_tid: str | None = None,
    last_completed_tid: str | None = None,
    current_batch_processed_count: int = 0,
    current_batch_succeeded_count: int = 0,
    current_batch_failed_count: int = 0,
    last_success_at: str | None = None,
) -> None:
    """Update progress columns on an ingestion_backfill_runs row."""
    data: dict[str, Any] = {
        "processed_tournament_count": processed_count,
        "succeeded_tournament_count": succeeded_count,
        "failed_tournament_count": failed_count,
        "status": status,
        "current_batch_processed_count": current_batch_processed_count,
        "current_batch_succeeded_count": current_batch_succeeded_count,
        "current_batch_failed_count": current_batch_failed_count,
        "updated_at": utc_now_iso(),
        "heartbeat_at": utc_now_iso(),
    }
    if current_batch_index is not None:
        data["current_batch_index"] = current_batch_index
    if current_tid is not None:
        data["current_tid"] = current_tid
    if last_completed_tid is not None:
        data["last_completed_tid"] = last_completed_tid
    if last_success_at is not None:
        data["last_success_at"] = last_success_at
    client.update(
        "ingestion_backfill_runs",
        data,
        {"id": f"eq.{run_row['id']}"},
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ingestion CLI."""
    parser = argparse.ArgumentParser(description="cEDH Analytics Data Ingestion")
    parser.add_argument("--tournament-id", type=str, help="TopDeck tournament ID (slug) to ingest")
    parser.add_argument("--days", type=int, default=7, help="Number of recent days to search for tournaments")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Fail fast instead of continuing to later tournaments after an error in --tids-file mode",
    )
    parser.add_argument("--tids-file", type=str, help="Path to file with one TopDeck tournament ID per line")
    parser.add_argument("--names-file", type=str, help="Path to file with one tournament name per line")
    parser.add_argument("--resolve-days", type=int, default=120, help="Days back to search when resolving names to IDs")
    parser.add_argument("--tids-out", type=str, help="Write resolved tournament IDs to this file")
    parser.add_argument("--selected-tids-out", type=str, help="Write filtered manifest TIDs to this file")
    parser.add_argument(
        "--skip-existing-tids",
        action="store_true",
        help="Skip manifest TIDs already present in Supabase",
    )
    parser.add_argument(
        "--only-failed-from-run-key",
        type=str,
        help="Restrict manifest TIDs to those marked failed for a recorded backfill run",
    )
    parser.add_argument("--batch-size", type=int, default=250, help="Batch size for --tids-file mode")
    parser.add_argument(
        "--batch-index", type=int, help="Only run the selected zero-based batch index from --tids-file mode"
    )
    parser.add_argument("--run-key", type=str, help="Logical run key for recorded --tids-file backfills")
    parser.add_argument(
        "--record-backfill",
        action="store_true",
        help="Record backfill run/batch progress in Supabase metadata tables",
    )
    parser.add_argument(
        "--start-date", type=str, help="Optional lower bound used when recording --tids-file backfill metadata"
    )
    parser.add_argument(
        "--end-date", type=str, help="Optional upper bound used when recording --tids-file backfill metadata"
    )
    parser.add_argument(
        "--resolve-include-ambiguous",
        action="store_true",
        help="Include all candidate IDs for ambiguous name matches",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of tournaments to process")
    parser.add_argument(
        "--leagues",
        "--league",
        dest="leagues",
        action="store_true",
        help="Include leagues=true in the TopDeck tournament search payload",
    )
    parser.add_argument("--direct", action="store_true", help="Use direct Postgres connection for faster ingestion")
    parser.add_argument(
        "--skip-existing-tournaments",
        action="store_true",
        help="Skip tournaments whose topdeck_tid already exists in Supabase",
    )
    parser.add_argument("--job-id", type=str, default="", help="ingestion_jobs UUID for cron-dispatched runs")
    parser.add_argument(
        "--min-players", type=int, default=0, help="Minimum number of players required to process a tournament"
    )
    return parser


def main():
    """Main entry point for ingestion."""
    args = build_arg_parser().parse_args()

    # Load environment variables
    load_local_env()
    topdeck_api_key = os.environ.get("TOPDECK_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not topdeck_api_key or not supabase_key:
        raise SystemExit("TOPDECK_API_KEY and SUPABASE_SERVICE_KEY are required")

    # Initialize clients
    topdeck = TopDeckClient(topdeck_api_key)
    supabase = SupabaseClient(supabase_url, supabase_key)
    db_client = None

    # Initialize ingester
    ingester = DataIngester(topdeck, supabase)

    # Job lifecycle management
    job_id = getattr(args, "job_id", "") or ""
    github_run_id = int(os.environ.get("GITHUB_RUN_ID", 0))
    start_time = time.time()

    if job_id:
        try:
            claimed = claim_ingestion_job(supabase, job_id, github_run_id)
        except Exception as exc:
            logger.error(f"Operational error claiming ingestion job {job_id}: {exc}")
            sys.exit(1)
        if not claimed:
            logger.info(f"No active ingestion job found for ID {job_id} - may already be claimed")
            sys.exit(INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE)
        update_ingestion_heartbeat(supabase, job_id)

    try:
        _run_ingestion(args, topdeck, supabase, ingester, job_id)
    except Exception as exc:
        if job_id:
            fail_ingestion_job(supabase, job_id, str(exc))
        raise

    duration = round(time.time() - start_time, 2)
    if job_id:
        complete_ingestion_job(
            supabase,
            job_id,
            {
                "duration_seconds": duration,
            },
        )

    # Cleanup direct Postgres connection
    db_client = None
    if args.direct and db_client:
        db_client.close()
        logger.info("Closed direct Postgres connection")

    logger.info("Ingestion complete")


def _run_ingestion(args, topdeck, supabase, ingester, job_id):
    """Core ingestion logic, extracted for job lifecycle wrapping."""
    min_players = getattr(args, "min_players", 0) or 0

    if args.tournament_id:
        # Ingest single tournament
        if args.skip_existing_tournaments:
            existing_tids = fetch_existing_tids(supabase, [args.tournament_id])
            if args.tournament_id in existing_tids:
                logger.info(
                    "Skipping existing tournament %s because --skip-existing-tournaments was set",
                    args.tournament_id,
                )
                return
        logger.info(f"Fetching tournament: {args.tournament_id}")
        tournament = topdeck.get_tournament(args.tournament_id)
        tournament["TID"] = args.tournament_id
        if ingester:
            result = ingester.process_tournament(tournament)
            logger.info(f"Result: {result}")
            update_ingestion_heartbeat(supabase, job_id)
    elif getattr(args, "tids_file", None):
        tids_path = Path(args.tids_file)
        if not tids_path.exists():
            logger.error(f"TIDs file not found: {tids_path}")
            sys.exit(1)
        tids = load_tids(tids_path)
        logger.info(f"Loaded {len(tids)} unique tournament IDs from {tids_path}")

        if args.only_failed_from_run_key:
            if not ingester:
                logger.error("--only-failed-from-run-key requires a readable database client")
                sys.exit(1)
            failed_tids = set(fetch_failed_tids_for_run(ingester.supabase, args.only_failed_from_run_key))
            original_count = len(tids)
            tids = [tid for tid in tids if tid in failed_tids]
            logger.info(
                f"Filtered manifest to {len(tids)} failed tids from run_key={args.only_failed_from_run_key} "
                f"(from {original_count})"
            )

        if args.skip_existing_tids:
            if not ingester:
                logger.error("--skip-existing-tids requires a readable database client")
                sys.exit(1)
            existing_tids = fetch_existing_tids(ingester.supabase, tids)
            original_count = len(tids)
            tids = [tid for tid in tids if tid not in existing_tids]
            logger.info(
                f"Skipped {original_count - len(tids)} tids already present in tournaments.topdeck_tid; "
                f"{len(tids)} remaining"
            )

        if args.skip_existing_tournaments:
            existing_tids = fetch_existing_tids(ingester.supabase, tids)
            original_count = len(tids)
            tids = [tid for tid in tids if tid not in existing_tids]
            logger.info(
                f"Skipped {original_count - len(tids)} tids already present because "
                f"--skip-existing-tournaments was set; {len(tids)} remaining"
            )

        if args.selected_tids_out:
            selected_path = Path(args.selected_tids_out)
            header_lines = [
                "# Selected tournament IDs after ingest.py pre-batch filtering",
                f"# Source manifest: {tids_path}",
                f"# only_failed_from_run_key: {args.only_failed_from_run_key or ''}",
                f"# skip_existing_tids: {args.skip_existing_tids}",
            ]
            write_tids(selected_path, tids, header_lines=header_lines)
            logger.info(f"Wrote {len(tids)} selected tids to {selected_path}")

        if args.batch_size <= 0:
            logger.error("--batch-size must be positive")
            sys.exit(1)

        start_dt = date_parser.parse(args.start_date) if args.start_date else None
        end_dt = date_parser.parse(args.end_date) if args.end_date else None
        if start_dt and end_dt and end_dt < start_dt:
            logger.error("--end-date must be on or after --start-date")
            sys.exit(1)

        if args.limit > 0 and len(tids) > args.limit:
            logger.info(f"Limiting to {args.limit} tournaments (from {len(tids)})")
            tids = tids[: args.limit]

        batches = chunk_items(tids, args.batch_size)
        logger.info(f"Prepared {len(batches)} batches from {len(tids)} tournaments (batch_size={args.batch_size})")

        if args.batch_index is not None and (args.batch_index < 0 or args.batch_index >= len(batches)):
            logger.error(f"--batch-index must be between 0 and {max(len(batches) - 1, 0)}")
            sys.exit(1)

        selected_batches = (
            [(args.batch_index, batches[args.batch_index])]
            if args.batch_index is not None
            else list(enumerate(batches))
        )

        run_key = args.run_key or default_backfill_run_key(tids_path, args.batch_size)
        processed_count = 0
        succeeded_count = 0
        failed_count = 0
        run_row = None
        if args.record_backfill:
            if not ingester:
                logger.error("--record-backfill requires a writable database client")
                sys.exit(1)
            run_row = upsert_backfill_run(
                ingester.supabase,
                run_key=run_key,
                tids_path=tids_path,
                batch_size=args.batch_size,
                total_tournaments=len(tids),
                total_batches=len(batches),
                start_date=start_dt.date().isoformat() if start_dt else None,
                end_date=end_dt.date().isoformat() if end_dt else None,
                status="running",
            )
            if not run_row:
                logger.error("Failed to initialize ingestion_backfill_runs row")
                sys.exit(1)

        for batch_index, batch_tids in selected_batches:
            batch_start = batch_index * args.batch_size
            batch_end = batch_start + len(batch_tids) - 1
            logger.info(
                f"Processing batch {batch_index + 1}/{len(batches)} "
                f"(batch_index={batch_index}, tids={batch_start}-{batch_end})"
            )
            if args.record_backfill and run_row:
                upsert_backfill_batch(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    tournament_count=len(batch_tids),
                    status="running",
                )
                append_backfill_event(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    event_type="batch_started",
                    payload={
                        "batch_start": batch_start,
                        "batch_end": batch_end,
                        "tournament_count": len(batch_tids),
                    },
                )
                update_backfill_run_progress(
                    ingester.supabase,
                    run_row=run_row,
                    processed_count=processed_count,
                    succeeded_count=succeeded_count,
                    failed_count=failed_count,
                    status="running",
                    current_batch_index=batch_index,
                    current_batch_processed_count=0,
                    current_batch_succeeded_count=0,
                    current_batch_failed_count=0,
                )

            batch_failed = False
            batch_error_text = None
            batch_processed_count = 0
            batch_succeeded_count = 0
            batch_failed_count = 0
            for tid in batch_tids:
                processed_count += 1
                batch_processed_count += 1
                if args.record_backfill and run_row:
                    append_backfill_event(
                        ingester.supabase,
                        run_id=run_row["id"],
                        batch_index=batch_index,
                        tid=tid,
                        event_type="fetch_started",
                    )
                    update_backfill_run_progress(
                        ingester.supabase,
                        run_row=run_row,
                        processed_count=processed_count,
                        succeeded_count=succeeded_count,
                        failed_count=failed_count,
                        status="running",
                        current_batch_index=batch_index,
                        current_tid=tid,
                        current_batch_processed_count=batch_processed_count,
                        current_batch_succeeded_count=batch_succeeded_count,
                        current_batch_failed_count=batch_failed_count,
                    )
                try:
                    tournament = topdeck.get_tournament(tid)
                except Exception as e:
                    failed_count += 1
                    batch_failed_count += 1
                    batch_failed = True
                    batch_error_text = f"fetch {tid}: {e}"
                    logger.error(f"Failed to fetch {tid}: {e}")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="fetch_failed",
                            payload={"error": str(e)},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    if args.stop_on_error:
                        break
                    continue

                tournament["TID"] = tid
                ts = parse_tournament_start_date(tournament)
                if ts is None:
                    logger.warning(f"Skipping {tid}: missing start date")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="tournament_skipped",
                            payload={"reason": "missing start date"},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    continue

                if start_dt and ts.date() < start_dt.date():
                    logger.info(f"Skipping {tid}: before start-date filter")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="tournament_skipped",
                            payload={"reason": "before start-date filter"},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    continue
                if end_dt and ts.date() > end_dt.date():
                    logger.info(f"Skipping {tid}: after end-date filter")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="tournament_skipped",
                            payload={"reason": "after end-date filter"},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    continue

                if ingester:
                    try:
                        if args.record_backfill and run_row:
                            append_backfill_event(
                                ingester.supabase,
                                run_id=run_row["id"],
                                batch_index=batch_index,
                                tid=tid,
                                event_type="process_started",
                            )
                        result = ingester.process_tournament(tournament)
                        if result:
                            succeeded_count += 1
                            batch_succeeded_count += 1
                            logger.info(f"Processed: {result['name']}")
                            if args.record_backfill and run_row:
                                last_success_at = utc_now_iso()
                                append_backfill_event(
                                    ingester.supabase,
                                    run_id=run_row["id"],
                                    batch_index=batch_index,
                                    tid=tid,
                                    event_type="process_succeeded",
                                    payload=result,
                                )
                                update_backfill_run_progress(
                                    ingester.supabase,
                                    run_row=run_row,
                                    processed_count=processed_count,
                                    succeeded_count=succeeded_count,
                                    failed_count=failed_count,
                                    status="running",
                                    current_batch_index=batch_index,
                                    current_tid=tid,
                                    last_completed_tid=tid,
                                    current_batch_processed_count=batch_processed_count,
                                    current_batch_succeeded_count=batch_succeeded_count,
                                    current_batch_failed_count=batch_failed_count,
                                    last_success_at=last_success_at,
                                    heartbeat_at=last_success_at,
                                )
                    except Exception as e:
                        failed_count += 1
                        batch_failed_count += 1
                        batch_failed = True
                        batch_error_text = f"process {tid}: {e}"
                        logger.error(f"Failed to process {tid}: {e}")
                        if args.record_backfill and run_row:
                            append_backfill_event(
                                ingester.supabase,
                                run_id=run_row["id"],
                                batch_index=batch_index,
                                tid=tid,
                                event_type="process_failed",
                                payload={"error": str(e)},
                            )
                            update_backfill_run_progress(
                                ingester.supabase,
                                run_row=run_row,
                                processed_count=processed_count,
                                succeeded_count=succeeded_count,
                                failed_count=failed_count,
                                status="running",
                                current_batch_index=batch_index,
                                current_tid=tid,
                                last_completed_tid=tid,
                                current_batch_processed_count=batch_processed_count,
                                current_batch_succeeded_count=batch_succeeded_count,
                                current_batch_failed_count=batch_failed_count,
                            )
                        if args.stop_on_error:
                            break
                else:
                    t_name = tournament.get("tournamentName")
                    t_players = len(tournament.get("standings", []))
                    logger.info(f"Would process: {t_name} ({t_players} players)")
                update_ingestion_heartbeat(supabase, job_id)

            if args.record_backfill and run_row:
                append_backfill_event(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    event_type="batch_failed" if batch_failed else "batch_completed",
                    payload={
                        "processed_count": batch_processed_count,
                        "succeeded_count": batch_succeeded_count,
                        "failed_count": batch_failed_count,
                        "error_text": batch_error_text,
                    },
                )
                upsert_backfill_batch(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    tournament_count=len(batch_tids),
                    status="failed" if batch_failed else "completed",
                    error_text=batch_error_text,
                )
                update_backfill_run_progress(
                    ingester.supabase,
                    run_row=run_row,
                    processed_count=processed_count,
                    succeeded_count=succeeded_count,
                    failed_count=failed_count,
                    status="running",
                    current_batch_index=batch_index,
                    current_tid=None,
                    current_batch_processed_count=batch_processed_count,
                    current_batch_succeeded_count=batch_succeeded_count,
                    current_batch_failed_count=batch_failed_count,
                )

            if batch_failed and args.stop_on_error:
                break

        if args.record_backfill and run_row:
            final_status = "completed_with_errors" if failed_count else "completed"
            update_backfill_run_progress(
                ingester.supabase,
                run_row=run_row,
                processed_count=processed_count,
                succeeded_count=succeeded_count,
                failed_count=failed_count,
                status=final_status,
                current_batch_index=None,
                current_tid=None,
                current_batch_processed_count=0,
                current_batch_succeeded_count=0,
                current_batch_failed_count=0,
            )
    else:
        # Search and ingest recent tournaments
        start_date = (datetime.now() - timedelta(days=args.days)).date().isoformat()
        end_date = datetime.now().date().isoformat()
        logger.info(f"Searching for tournaments from {start_date} through {end_date} ({args.days} days)")
        tournaments = topdeck.search_tournaments(start_date=start_date, end_date=end_date, leagues=args.leagues)
        logger.info(f"Found {len(tournaments)} tournaments to process")

        if min_players > 0:
            original_count = len(tournaments)
            tournaments = [t for t in tournaments if len(t.get("standings", [])) >= min_players]
            logger.info(
                f"Filtered to {len(tournaments)} tournaments with >= {min_players} players (from {original_count})"
            )

        if args.skip_existing_tournaments:
            search_tids = [tid for t in tournaments if (tid := t.get("id") or t.get("TID"))]
            existing_tids = fetch_existing_tids(ingester.supabase, search_tids)
            original_count = len(tournaments)
            tournaments = [t for t in tournaments if (t.get("id") or t.get("TID")) not in existing_tids]
            logger.info(
                f"Skipped {original_count - len(tournaments)} existing tournaments because "
                f"--skip-existing-tournaments was set; {len(tournaments)} remaining"
            )

        if args.limit > 0 and len(tournaments) > args.limit:
            logger.info(f"Limiting to {args.limit} tournaments (from {len(tournaments)})")
            tournaments = tournaments[: args.limit]

        for t in tournaments:
            tid = t.get("id") or t.get("TID")
            tournament = t
            if tid:
                tournament = topdeck.get_tournament(tid)
                for key in (
                    "swissNum",
                    "topCut",
                    "averageElo",
                    "medianElo",
                    "topElo",
                    "eventData",
                ):
                    if key not in tournament and key in t:
                        tournament[key] = t[key]
            if ingester:
                try:
                    result = ingester.process_tournament(tournament)
                    if result:
                        logger.info(f"Processed: {result['name']}")
                except Exception as e:
                    logger.error(f"Failed to process {tournament.get('name') or t.get('tournamentName')}: {e}")
            else:
                logger.info(f"Would process: {tournament.get('name')} ({len(tournament.get('standings', []))} players)")
            update_ingestion_heartbeat(supabase, job_id)


if __name__ == "__main__":
    main()
