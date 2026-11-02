"""Exact region aliases shared with the database migration seed.

Unknown or country-ambiguous values are preserved; never use substring matching.
"""

import json
from pathlib import Path

REGIONS = json.loads((Path(__file__).resolve().parents[1] / "data" / "region_aliases.json").read_text())
COUNTRY_ALIASES = {
    "US": "UNITED STATES",
    "USA": "UNITED STATES",
    "U.S.": "UNITED STATES",
    "UNITED STATES OF AMERICA": "UNITED STATES",
    "CA": "CANADA",
    "CAN": "CANADA",
    "AU": "AUSTRALIA",
    "AUS": "AUSTRALIA",
    "GB": "UNITED KINGDOM",
    "GBR": "UNITED KINGDOM",
    "UK": "UNITED KINGDOM",
}


def canonical_region_name(state: str | None, country: str | None = None) -> str | None:
    value = (state or "").strip()
    if not value or value.upper() in {"UNDEFINED", "UNKNOWN"}:
        return None
    country_key = (country or "").strip().upper()
    country_key = COUNTRY_ALIASES.get(country_key, country_key)
    matches = {
        row["name"]
        for row in REGIONS
        if (not country_key or row["country"] == country_key)
        and value.upper() in {alias.upper() for alias in [row["name"], *row["aliases"]]}
    }
    return next(iter(matches)) if len(matches) == 1 else value
