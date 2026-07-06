"""Per-game ingestion configuration (ADR 0015).

Single source of truth for how each supported game/format vertical maps onto the
TopDeck.gg API and the shared Supabase schema. The registry is pure data: identity
extraction behavior lives in the deck-identity module and is dispatched by
``GameConfig.key`` so this module never imports ingestion code.

TopDeck game strings are case-sensitive and come from the documented Game enum in
``packages/backend/openapi.yaml``. Format strings for non-MTG games are not enumerated
by the API docs; configs for those games search game-wide (``topdeck_format=None``) and
persist each tournament payload's own ``format`` string, so real format names surface
from the data itself (see ADR 0015 appendix).
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

    topdeck_format: str | None
    """Format string for the search payload; None searches the game across formats."""

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
    """Case-insensitive payload ``format`` values accepted when searching game-wide.
    Empty means every format returned for the game is ingested."""


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
}

DEFAULT_GAME_KEY = "cedh"


def get_game_config(key: str) -> GameConfig:
    """Return the config for a registry key, raising a helpful error otherwise."""
    try:
        return GAME_REGISTRY[key]
    except KeyError:
        known = ", ".join(sorted(GAME_REGISTRY))
        raise KeyError(f"Unknown game key {key!r}; known keys: {known}") from None


def payload_format_matches(config: GameConfig, payload_format: str | None) -> bool:
    """Return True when a tournament payload's format is ingestible for this config.

    Used to filter game-wide searches down to the formats a vertical actually wants
    (e.g. only Edison events out of all Yu-Gi-Oh results). Configs with an explicit
    ``topdeck_format`` already filter server-side, and empty ``format_aliases`` accepts
    everything.
    """
    if config.topdeck_format is not None or not config.format_aliases:
        return True
    if not payload_format:
        return False
    normalized = str(payload_format).strip().lower()
    return any(normalized == alias.strip().lower() for alias in config.format_aliases)
