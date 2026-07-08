#!/usr/bin/env python3
"""Scryfall oracle_id identity resolution for commander rows.

Universes Beyond alternate-art/alternate-name printings (e.g. the Stranger
Things Secret Lair versions of Innistrad cards) are the *same* Magic card as
far as Scryfall's ``oracle_id`` is concerned — only the flavor-facing
``flavor_name`` differs. TopDeck decklists are transcribed from what's
printed on the card, so they capture the flavor name, which historically
caused the same commander to be ingested as two distinct ``commanders`` rows
(one per printed name) instead of merging into a single canonical row.

This module builds a name -> oracle_id map from Scryfall's ``default_cards``
bulk dataset (one entry per printing, including flavor names) and uses it to:

- resolve the oracle_id "signature" of an existing commander row so
  duplicate rows can be detected and merged (see
  ``sweep_ub_alt_name_commander_dedup.py``), and
- build a flavor-name -> true-oracle-name alias map that can be consulted at
  ingestion time to prevent new splits going forward (see
  ``generate_commander_oracle_aliases.py`` and ``ingest.py``).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from generate_legal_commander_pairings import build_commander_card, front_face_name, front_face_value
from ingest import clean_commander_card_name, normalize_partner_order

DEFAULT_CARDS_BULK_TYPE = "default_cards"


def build_name_to_oracle_id_map(cards: list[dict[str, Any]]) -> dict[str, str]:
    """Index every known printed name (true name and flavor name) to oracle_id.

    True (Oracle) names are indexed first so that, in the extremely unlikely
    event of a collision, a flavor name never shadows a real card name.
    """
    mapping: dict[str, str] = {}

    for card in cards:
        oracle_id = str(card.get("oracle_id") or "").strip()
        if not oracle_id:
            continue
        true_name = front_face_name(str(card.get("name") or ""))
        if true_name:
            mapping.setdefault(true_name, oracle_id)

    for card in cards:
        oracle_id = str(card.get("oracle_id") or "").strip()
        if not oracle_id:
            continue
        flavor_name = front_face_value(card, "flavor_name")
        if not flavor_name:
            continue
        flavor_name = front_face_name(flavor_name)
        if flavor_name:
            mapping.setdefault(flavor_name, oracle_id)

    return mapping


def collect_true_oracle_names(cards: list[dict[str, Any]]) -> set[str]:
    """Return the set of "real" (non-flavor) card names seen in ``cards``."""
    names: set[str] = set()
    for card in cards:
        true_name = front_face_name(str(card.get("name") or ""))
        if true_name:
            names.add(true_name)
    return names


def is_commander_eligible(card: dict[str, Any]) -> bool:
    """Return whether ``card`` can actually occupy the command zone.

    ``legalities.commander == "legal"`` only means the card is legal to
    *include in the 99* of a Commander deck -- true for the overwhelming
    majority of Magic cards -- and says nothing about whether the card can
    itself *be* a commander. Reuses the trait extraction that
    ``generate_legal_commander_pairings.py`` already built to solve this
    exact problem for legal-pairing generation (``build_commander_card``),
    rather than re-deriving type-line/oracle-text heuristics here.

    A card can be a (possibly partial, e.g. partner/background) commander
    if it is format-legal in Commander *and* one of:

    - a Legendary Creature, the overwhelmingly common case;
    - a Legendary Background, which occupies the second command-zone slot
      alongside a "Choose a Background" creature; or
    - any other card whose oracle text explicitly grants commander
      eligibility (the wording Wizards uses on eligible planeswalkers,
      e.g. "Tevesh Szat, Doom of Fools can be your commander.").
    """
    commander_card = build_commander_card(card)
    if not commander_card.is_commander_legal:
        return False
    if "Legendary" in commander_card.type_line and "Creature" in commander_card.type_line:
        return True
    if commander_card.is_legendary_background:
        return True
    if "can be your commander" in commander_card.oracle_text.casefold():
        return True
    return False


def build_alias_map(cards: list[dict[str, Any]]) -> dict[str, str]:
    """Build a flavor_name -> true_name alias map for commander-eligible cards.

    Only cards that can actually occupy the command zone (see
    ``is_commander_eligible``) are considered, keeping the generated
    artifact scoped to names that can plausibly appear as a ``commanders``
    row rather than every commander-format-legal, flavor-named card ever
    printed -- most of which are ordinary 99-deck cards, not commanders.

    Flavor names that are themselves a real Oracle name of some *other*
    card are also skipped: aliasing such a string would be ambiguous, and
    could silently rewrite a distinct real card's name via
    ``clean_commander_card_name()``.
    """
    true_oracle_names = collect_true_oracle_names(cards)
    alias_map: dict[str, str] = {}
    for card in cards:
        if not is_commander_eligible(card):
            continue
        true_name = front_face_name(str(card.get("name") or ""))
        flavor_name = front_face_value(card, "flavor_name")
        flavor_name = front_face_name(flavor_name) if flavor_name else ""
        if not true_name or not flavor_name or flavor_name == true_name:
            continue
        if flavor_name in true_oracle_names:
            continue
        alias_map.setdefault(flavor_name, true_name)
    return alias_map


def commander_names_from_row(row: dict[str, Any]) -> list[str]:
    """Extract the individual card names represented by a ``commanders`` row."""
    names = row.get("commander_names")
    if isinstance(names, list) and names:
        return [str(name).strip() for name in names if str(name).strip()]

    raw_name = str(row.get("name") or "")
    return [part.strip() for part in raw_name.split(" / ") if part.strip()]


def oracle_signature_for_names(
    names: list[str],
    name_to_oracle_id: dict[str, str],
) -> tuple[str, ...] | None:
    """Resolve a sorted oracle_id signature for a list of card names.

    Returns ``None`` if any name can't be resolved to an oracle_id, since an
    unresolved name can't be safely compared against other rows.
    """
    if not names:
        return None
    oracle_ids: list[str] = []
    for name in names:
        oracle_id = name_to_oracle_id.get(name)
        if not oracle_id:
            return None
        oracle_ids.append(oracle_id)
    return tuple(sorted(oracle_ids))


def group_duplicate_commander_rows(
    rows: list[dict[str, Any]],
    name_to_oracle_id: dict[str, str],
) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    """Group commander rows that share an oracle_id signature.

    Only signatures with more than one row are returned — those are the
    duplicate groups that need merging.
    """
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        names = commander_names_from_row(row)
        signature = oracle_signature_for_names(names, name_to_oracle_id)
        if signature is None:
            continue
        groups[signature].append(row)
    return {signature: group for signature, group in groups.items() if len(group) > 1}


def choose_canonical_row(
    rows: list[dict[str, Any]],
    true_oracle_names: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Pick the canonical row out of a duplicate group.

    Preference order:
    1. A row whose ``name`` is a real Oracle name (not a UB flavor name).
    2. For two-card partner rows, the row whose commander order already
       matches the canonical partner order (see ``normalize_partner_order``),
       so a sweep never merges into the non-canonical "B, A" ordering just
       because it sorts alphabetically first.
    3. Alphabetically first name, for determinism.
    4. Lowest ``id``, as a final tiebreaker.
    """

    def sort_key(row: dict[str, Any]) -> tuple[int, int, str, str]:
        name = str(row.get("name") or "")
        # For partner/two-card commander rows, `name` is a composite display
        # string (e.g. "Sophina, Spearsage Deserter / Hargilde, Kindly
        # Runechanter") that never matches an individual entry in
        # `true_oracle_names`. Score each component name from
        # `commander_names` instead so a row only counts as flavor-named when
        # at least one of its actual cards is a UB alt name.
        component_names = commander_names_from_row(row)
        is_true_named = bool(component_names) and all(
            component in true_oracle_names for component in component_names
        )
        is_flavor_name = 0 if is_true_named else 1

        # When the database already has the same two-card partner pair in
        # both orders (e.g. "Kraum, Ludevic's Opus / Tymna the Weaver" and
        # "Tymna the Weaver / Kraum, Ludevic's Opus"), both rows are equally
        # "true named" and would otherwise tie-break alphabetically — which
        # ignores the canonical order enforced elsewhere via
        # `PARTNER_ORDER_OVERRIDES`/`normalize_partner_order`. Prefer the row
        # that already matches that canonical order.
        is_non_canonical_order = 0
        if len(component_names) == 2:
            cleaned_components = [clean_commander_card_name(component) for component in component_names]
            canonical_order = normalize_partner_order(component_names)
            if len(canonical_order) == 2 and cleaned_components != canonical_order:
                is_non_canonical_order = 1

        return (is_flavor_name, is_non_canonical_order, name, str(row.get("id") or ""))

    ordered = sorted(rows, key=sort_key)
    return ordered[0], ordered[1:]
