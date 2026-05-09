"""PostHog analytics utilities for the cEDH Analytics pipeline."""

from __future__ import annotations

import atexit
import os
from typing import Any

try:
    from posthog import Posthog

    _POSTHOG_AVAILABLE = True
except ImportError:
    _POSTHOG_AVAILABLE = False

PIPELINE_DISTINCT_ID = "cedh-analytics-pipeline"

_client: Any = None


def get_posthog_client() -> Any:
    """Return a singleton PostHog client, initializing it on first call."""
    global _client
    if _client is not None:
        return _client

    if not _POSTHOG_AVAILABLE:
        return None

    token = os.environ.get("POSTHOG_PROJECT_TOKEN")
    if not token:
        return None

    host = os.environ.get("POSTHOG_HOST")
    if not host:
        return None
    _client = Posthog(
        token,
        host=host,
        enable_exception_autocapture=True,
    )
    atexit.register(_client.shutdown)
    return _client


def capture(event: str, properties: dict[str, Any] | None = None) -> None:
    """Capture a pipeline event. No-op if PostHog is not configured."""
    client = get_posthog_client()
    if client is None:
        return
    client.capture(
        distinct_id=PIPELINE_DISTINCT_ID,
        event=event,
        properties=properties or {},
    )
