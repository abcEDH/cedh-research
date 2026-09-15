"""Shared UTC cutoff for Elo inputs, including cached and direct-SQL inputs."""

from datetime import UTC, date, datetime
from typing import Any, Iterable


def utc_datetime(value: str | date | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time())
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def exclude_future_games(
    rows: Iterable[dict[str, Any]],
    *,
    date_key: str = "start_date",
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    """Reject whole pods when any dated participant is after the run cutoff.

    Undated legacy inputs retain their existing behavior. Malformed dates fail
    closed rather than being silently treated as historical games.
    """
    cutoff = utc_datetime(as_of or datetime.now(UTC))
    rows = list(rows)
    future_ids = {
        row["game_id"]
        for row in rows
        if row.get("game_id") and row.get(date_key)
        and utc_datetime(row[date_key]) > cutoff
    }
    return [
        row for row in rows
        if row.get("game_id") not in future_ids
        and (not row.get(date_key) or utc_datetime(row[date_key]) <= cutoff)
    ]
