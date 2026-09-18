"""HTTP client for Scryfall's bulk-data API.

See https://scryfall.com/docs/api/bulk-data. Scryfall's own guidance is to
use the bulk-data dump for lookups and hotlink its CDN for the actual image
bytes -- never re-host images, never call the per-name API in a loop. This
module is the one place that talks to that API for
``ingest_scryfall_cards.py`` (#321).
"""

from __future__ import annotations

import requests

SCRYFALL_BULK_DATA_ENDPOINT = "https://api.scryfall.com/bulk-data"
DEFAULT_CARDS_BULK_TYPE = "default_cards"

# The index response is tiny; the dump itself is not (tens of thousands of
# card objects), so it gets a much longer timeout.
INDEX_TIMEOUT_SECONDS = 30
DOWNLOAD_TIMEOUT_SECONDS = 300


def fetch_bulk_data_index(session: requests.Session) -> list[dict]:
    """Return the list of bulk-data descriptor objects Scryfall currently publishes."""
    response = session.get(SCRYFALL_BULK_DATA_ENDPOINT, timeout=INDEX_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", [])


def find_bulk_data_download_uri(index: list[dict], bulk_type: str = DEFAULT_CARDS_BULK_TYPE) -> str:
    """Pick the download URI for a given bulk-data type (default: ``default_cards``)."""
    for entry in index:
        if entry.get("type") == bulk_type:
            uri = entry.get("download_uri")
            if uri:
                return uri
    raise ValueError(f"No bulk-data entry found for type={bulk_type!r}")


def fetch_bulk_data_cards(download_uri: str, session: requests.Session) -> list[dict]:
    """Download and parse a bulk-data JSON array (e.g. ``default_cards``).

    One request for the whole dump instead of one request per card name --
    this is the entire point of #321.
    """
    response = session.get(download_uri, timeout=DOWNLOAD_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
