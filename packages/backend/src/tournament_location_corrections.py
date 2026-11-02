"""Reviewed event-specific repairs, guarded against later venue/source changes."""

import json
from pathlib import Path

CORRECTIONS = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "tournament_location_corrections.json").read_text()
)
BY_TOPDECK_ID = {row["topdeck_tid"]: row for row in CORRECTIONS}


def corrected_location(topdeck_tid, location):
    correction = BY_TOPDECK_ID.get(topdeck_tid)
    if not correction:
        return dict(location)
    if any(location.get(key) != correction[key] for key in ("city", "venue")):
        return dict(location)
    if location.get("state") not in (correction["original_state"], correction["state"]):
        return dict(location)
    if location.get("country") not in (correction["original_country"], correction["country"]):
        return dict(location)
    return {**location, "state": correction["state"], "country": correction["country"]}


def apply_reviewed_corrections(cursor):
    """Caller owns transaction and must refresh regional read models before commit."""
    updated = 0
    for row in CORRECTIONS:
        cursor.execute(
            """UPDATE tournaments SET state=%s,country=%s
            WHERE topdeck_tid=%s AND state IS NOT DISTINCT FROM %s
            AND country IS NOT DISTINCT FROM %s AND city IS NOT DISTINCT FROM %s
            AND venue IS NOT DISTINCT FROM %s""",
            (
                row["state"],
                row["country"],
                row["topdeck_tid"],
                row["original_state"],
                row["original_country"],
                row["city"],
                row["venue"],
            ),
        )
        updated += cursor.rowcount
    return updated
