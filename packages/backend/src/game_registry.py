"""Per-game ingestion configuration (ADR 0015).

Single source of truth for how each supported game/format vertical maps onto the
TopDeck.gg API and the shared Supabase schema. The registry is pure data: identity
extraction behavior lives in the deck-identity module and is dispatched by
``GameConfig.key`` so this module never imports ingestion code.

TopDeck game strings are case-sensitive and come from the documented Game enum in
``packages/backend/openapi.yaml``. The search endpoint requires both ``game`` and
``format`` on every request (a 400 documents "Both game and format fields are
required") — there is no way to search a game across all of its formats in one
call. Format strings for non-MTG games are not enumerated by the API docs, so
configs for those games carry a best-guess ``topdeck_format`` plus optional
``format_aliases``; ingestion queries each candidate and merges the results (see
ADR 0015 appendix). Pin the real strings once live data confirms them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MTG_GAME = "Magic: The Gathering"


@dataclass(frozen=True)
class GameConfig:
    """How one game/format vertical is searched, scored, and persisted."""

    key: str
    """CLI slug, e.g. ``cedh`` or ``ygo-edison``. One slug encodes game + format."""

    topdeck_game: str
    """Exact case-sensitive game string sent to the TopDeck search API."""

    topdeck_format: str
    """Primary format string sent in every search request (TopDeck requires it)."""

    db_game: str
    """Value written to tournaments.game (and commanders.game)."""

    db_format: str
    """Fallback for tournaments.format when the payload carries no format string."""

    pod_size: int
    """Players per game: 4 for cEDH pods, 2 for 1v1 games."""

    win_points: int
    """game_participants.points_earned for a win."""

    draw_points: int
    """game_participants.points_earned for a draw."""

    derive_wld_from_points: bool
    """Derive wins/draws from standings points (cEDH 5/1/0 only). Losses are NEVER
    derived from points — they grant 0 points and cannot be inferred without the
    round count (see backend AGENTS.md known issue #4)."""

    small_event_top_cut_override: int | None
    """Effective top cut forced for events with <= 34 players (cEDH convention)."""

    identity_kind: str
    """Value written to commanders.identity_kind for this game's deck identities."""

    format_aliases: tuple[str, ...] = field(default=())
    """Additional format strings to also search for (besides ``topdeck_format``) when
    the exact label TopDeck uses is uncertain. Each alias triggers its own search
    call; results are merged and deduped by tournament id."""


GAME_REGISTRY: dict[str, GameConfig] = {
    "cedh": GameConfig(
        key="cedh",
        topdeck_game=MTG_GAME,
        topdeck_format="EDH",
        db_game=MTG_GAME,
        db_format="EDH",
        pod_size=4,
        win_points=5,
        draw_points=1,
        derive_wld_from_points=True,
        small_event_top_cut_override=4,
        identity_kind="commander",
    ),
    # Riftbound and Gundam: TopDeck's format taxonomy for these games is not
    # documented. "Standard" is a best guess (matches db_format); win/draw points
    # follow standard 1v1 Swiss match points and are only informational (no
    # points-based W/D derivation). Pin the real string once live search results
    # confirm it (ADR 0015 appendix).
    "riftbound": GameConfig(
        key="riftbound",
        topdeck_game="Riftbound",
        topdeck_format="Standard",
        db_game="Riftbound",
        db_format="Standard",
        pod_size=2,
        win_points=3,
        draw_points=1,
        derive_wld_from_points=False,
        small_event_top_cut_override=None,
        identity_kind="legend",
    ),
    "gundam": GameConfig(
        key="gundam",
        topdeck_game="Gundam TCG",
        topdeck_format="Standard",
        db_game="Gundam TCG",
        db_format="Standard",
        pod_size=2,
        win_points=3,
        draw_points=1,
        derive_wld_from_points=False,
        small_event_top_cut_override=None,
        identity_kind="leader",
    ),
    # Yu-Gi-Oh retro formats: exact TopDeck format strings are unverified until
    # the first live runs (ADR 0015 appendix) — format_aliases lists plausible
    # alternate spellings/casings; each is searched and results are merged.
    "ygo-edison": GameConfig(
        key="ygo-edison",
        topdeck_game="Yu-Gi-Oh",
        topdeck_format="Edison",
        db_game="Yu-Gi-Oh",
        db_format="Edison",
        pod_size=2,
        win_points=3,
        draw_points=1,
        derive_wld_from_points=False,
        small_event_top_cut_override=None,
        identity_kind="archetype",
        format_aliases=("Edison Format",),
    ),
    "ygo-goat": GameConfig(
        key="ygo-goat",
        topdeck_game="Yu-Gi-Oh",
        topdeck_format="Goat",
        db_game="Yu-Gi-Oh",
        db_format="Goat",
        pod_size=2,
        win_points=3,
        draw_points=1,
        derive_wld_from_points=False,
        small_event_top_cut_override=None,
        identity_kind="archetype",
        format_aliases=("GOAT", "Goat Format"),
    ),
}

DEFAULT_GAME_KEY = "cedh"


def get_game_config(key: str) -> GameConfig:
    """Return the config for a registry key, raising a helpful error otherwise."""
    try:
        return GAME_REGISTRY[key]
    except KeyError:
        known = ", ".join(sorted(GAME_REGISTRY))
        raise KeyError(f"Unknown game key {key!r}; known keys: {known}") from None


def accepted_topdeck_formats(config: GameConfig) -> tuple[str, ...]:
    """Every format string a config's searches may return (primary + aliases)."""
    return (config.topdeck_format, *config.format_aliases)


def payload_format_matches(config: GameConfig, payload_format: str | None) -> bool:
    """Return True when a tournament payload's format matches one this config
    searched for. Used as a defensive post-filter after multi-alias searches, in
    case the API's format matching is looser than the documented exact match.
    """
    if not payload_format:
        return False
    normalized = str(payload_format).strip().lower()
    return any(normalized == alias.strip().lower() for alias in accepted_topdeck_formats(config))
