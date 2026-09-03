"""Generic supabase-py fluent-builder helpers: paginated fetch and batched upsert.

Split out of `supabase_client.py` (see AGENTS.md's module-extraction rule) so
that file stays focused on client construction, the legacy `SupabaseClient`
wrapper, and `DirectPostgresClient`. Both `fetch_all` and `upsert_batched`
are re-exported from `supabase_client` for the many existing
`from supabase_client import fetch_all` call sites.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

# Max rows per PostgREST upsert request. A single upsert is one SQL statement,
# so very large payloads (e.g. ~88k global Elo ratings) exceed the Postgres
# statement_timeout (error 57014). Splitting into batches keeps each statement
# well under the limit. Mirrors the chunking in rebuild_player_commander_profiles.py.
UPSERT_BATCH_SIZE = 500

# Maps a `fetch_all()` filter operator to the supabase-py query-builder method
# it dispatches to. "is" and "not_is" are handled separately since they hang
# off `.is_()` / `.not_.is_()` rather than a same-named method.
_OPERATOR_METHODS: dict[str, str] = {
    "eq": "eq",
    "neq": "neq",
    "gt": "gt",
    "gte": "gte",
    "lt": "lt",
    "lte": "lte",
    "like": "like",
    "ilike": "ilike",
    "in": "in_",
}


def _apply_operator(query: Any, column: str, operator: str, value: Any) -> Any:
    """Apply one (column, operator, value) filter to a supabase-py query builder."""
    if operator == "is":
        return query.is_(column, value)
    if operator == "not_is":
        return query.not_.is_(column, value)
    method = _OPERATOR_METHODS.get(operator)
    if method is None:
        raise ValueError(f"Unsupported filter operator: {operator!r}")
    return getattr(query, method)(column, value)


def fetch_all(
    client: Client,
    table: str,
    columns: str = "*",
    filters: list[tuple[str, str, Any]] | None = None,
    order: tuple[str, bool] | list[tuple[str, bool]] | None = None,
    page_size: int = 1000,
    label: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch every row of `table` via the supabase-py fluent builder, paginating by offset.

    `filters` is a list of (column, operator, value) triples, e.g.
    `[("start_date", "gte", cutoff)]`. Supported operators: eq, neq, gt, gte,
    lt, lte, like, ilike, in, is, not_is (see `_apply_operator`).
    `order` is `(column, desc)`, or a list of them for a multi-column sort;
    pass it for tables without a natural insertion order to keep offset
    pagination stable across pages.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    started = time.time()
    order_clauses = [order] if isinstance(order, tuple) else (order or [])
    while True:
        query = client.table(table).select(columns)
        for column, operator, value in filters or []:
            query = _apply_operator(query, column, operator, value)
        for order_column, desc in order_clauses:
            query = query.order(order_column, desc=desc)
        page = query.limit(page_size).offset(offset).execute().data
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
        if offset % 25000 == 0:
            elapsed = time.time() - started
            source = label or table
            print(f"Fetched {offset:,} rows from {source} in {elapsed:.1f}s", flush=True)
    return rows


def upsert_batched(
    client: Client,
    table: str,
    data: dict[str, Any] | list[dict[str, Any]],
    on_conflict: str | None = None,
    batch_size: int = UPSERT_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Upsert `data` via the fluent builder, chunked to `batch_size` rows per call.

    A single upsert is one SQL statement, so an oversized payload (e.g. the
    ~88k global Elo ratings) trips the Postgres statement_timeout (57014).
    Mirrors the batching that used to live in `SupabaseClient.upsert()` for
    callers now using `client.table(...)` directly.
    """
    kwargs: dict[str, Any] = {}
    if on_conflict:
        kwargs["on_conflict"] = on_conflict

    if not isinstance(data, list):
        batches: list[list[dict[str, Any]]] = [[data]]
    else:
        batches = [data[i : i + batch_size] for i in range(0, len(data), batch_size)] or [[]]

    collected: list[dict[str, Any]] = []
    try:
        for batch in batches:
            if not batch:
                continue
            result = client.table(table).upsert(batch, **kwargs).execute()
            if result.data:
                collected.extend(result.data)
        return collected
    except Exception as e:
        logger.error("upsert failed on %s: %s", table, e)
        raise


__all__ = ["UPSERT_BATCH_SIZE", "fetch_all", "upsert_batched"]
