"""Supabase clients: supabase-py REST wrapper and direct Postgres."""

from __future__ import annotations

import logging
import os
from typing import Any

from supabase import Client, create_client

# Optional: psycopg2 for direct connection
import importlib.util

PSYCOPG2_AVAILABLE = importlib.util.find_spec("psycopg2") is not None
if PSYCOPG2_AVAILABLE:
    import psycopg2
    import psycopg2.extras

logger = logging.getLogger(__name__)

SUPABASE_REST_BASE = "https://msjjihqbxtgjdtapywrj.supabase.co"

# Maps PostgREST-style filter prefixes to (SQL operator, prefix length).
# Used only by DirectPostgresClient.select() to translate shared filter dicts.
_FILTER_OPS: dict[str, tuple[str, int]] = {
    "eq.":    ("=",     3),
    "neq.":   ("!=",    4),
    "gte.":   (">=",    4),
    "lte.":   ("<=",    4),
    "ilike.": ("ILIKE", 6),
}

# Params that control query structure, not row filtering.
_STRUCTURAL_PARAMS = frozenset({"select", "limit", "offset", "order"})


def get_supabase_client(
    url: str | None = None,
    key: str | None = None,
) -> Client:
    """Return a supabase-py Client. Falls back to env vars when args are omitted."""
    return create_client(
        url or os.environ["SUPABASE_URL"],
        key or os.environ["SUPABASE_SERVICE_KEY"],
    )


def _describe_request_failure(exc: BaseException, *, table: str, body_chars: int = 200) -> str:
    """Build a one-line diagnostic string for a failed request."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    body = getattr(response, "text", "") or ""
    body_excerpt = body[:body_chars].replace("\n", " ").strip()
    parts = [f"table={table}", type(exc).__name__]
    if status is not None:
        parts.append(f"status={status}")
    if body_excerpt:
        parts.append(f"body={body_excerpt!r}")
    msg = str(exc).strip()
    if msg and not (status is not None and msg.startswith(f"{status} ")):
        parts.append(f"err={msg}")
    return " ".join(parts)


def _apply_filter(q: Any, col: str, val: str) -> Any:
    """Apply one PostgREST-style predicate to a supabase-py query builder."""
    if val.startswith("eq."):
        return q.eq(col, val[3:])
    if val.startswith("neq."):
        return q.neq(col, val[4:])
    if val.startswith("gte."):
        return q.gte(col, val[4:])
    if val.startswith("lte."):
        return q.lte(col, val[4:])
    if val.startswith("gt."):
        return q.gt(col, val[3:])
    if val.startswith("lt."):
        return q.lt(col, val[3:])
    if val.startswith("ilike."):
        return q.ilike(col, val[6:])
    if val.startswith("in.(") and val.endswith(")"):
        items = [v.strip() for v in val[4:-1].split(",") if v.strip()]
        return q.in_(col, items)
    if val == "not.is.null":
        return q.not_.is_(col, "null")
    logger.warning("Unknown PostgREST filter for column %s: %r — skipped", col, val)
    return q


def fetch_existing_tids(
    client: SupabaseClient,
    tids: list[str] | None = None,
) -> set[str]:
    """Return existing TopDeck tournament IDs from Supabase.

    When tids are provided, query only those IDs in chunks instead of scanning
    the whole tournaments table.
    """
    if tids is not None:
        existing: set[str] = set()
        chunk_size = 200
        for start in range(0, len(tids), chunk_size):
            chunk = [t for t in tids[start : start + chunk_size] if t]
            if not chunk:
                continue
            rows = client._client.table("tournaments").select("topdeck_tid").in_("topdeck_tid", chunk).execute().data
            existing.update(r["topdeck_tid"] for r in rows if r.get("topdeck_tid"))
        return existing

    rows: list[dict[str, Any]] = []
    offset = 0
    limit = 1000
    while True:
        page = (
            client._client.table("tournaments")
            .select("topdeck_tid")
            .not_.is_("topdeck_tid", "null")
            .order("start_date", desc=True)
            .order("topdeck_tid", desc=False)
            .limit(limit)
            .offset(offset)
            .execute()
            .data
        )
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return {r["topdeck_tid"] for r in rows if r.get("topdeck_tid")}


class SupabaseClient:
    """Supabase REST client backed by supabase-py.

    Maintains the same select/upsert/update/rpc interface as the former
    hand-rolled requests client so all existing call sites remain unchanged.
    """

    def __init__(self, url: str, service_key: str):
        self._client: Client = create_client(url, service_key)
        self.url = url
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public interface (unchanged signatures)
    # ------------------------------------------------------------------

    def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
        max_retries: int = 3,
    ) -> list[dict[str, Any]] | None:
        kwargs: dict[str, Any] = {}
        if on_conflict:
            kwargs["on_conflict"] = on_conflict
        try:
            result = self._client.table(table).upsert(data, **kwargs).execute()
            return result.data
        except Exception as e:
            logger.error("upsert failed on %s: %s", table, e)
            raise

    def select(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        max_retries: int = 8,
    ) -> list[dict[str, Any]]:
        params = filters or {}
        columns = str(params.get("select", "*"))
        limit_raw = params.get("limit")
        offset_raw = params.get("offset")
        order_raw = params.get("order")

        q = self._client.table(table).select(columns)

        for col, val in params.items():
            if col in _STRUCTURAL_PARAMS:
                continue
            q = _apply_filter(q, col, str(val))

        if order_raw:
            for part in str(order_raw).split(","):
                segments = part.strip().split(".")
                col_name = segments[0]
                desc = len(segments) > 1 and segments[-1] == "desc"
                q = q.order(col_name, desc=desc)

        if limit_raw is not None:
            q = q.limit(int(limit_raw))
        if offset_raw is not None:
            q = q.offset(int(offset_raw))

        try:
            return q.execute().data
        except Exception as e:
            logger.error("select failed on %s: %s", table, e)
            raise

    def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, str] | None = None,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        q = self._client.table(table).update(data)
        for col, val in (filters or {}).items():
            q = _apply_filter(q, col, str(val))
        try:
            return q.execute().data
        except Exception as e:
            logger.error("update failed on %s: %s", table, e)
            raise

    def rpc(
        self,
        function_name: str,
        payload: dict[str, Any] | None = None,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> Any:
        try:
            result = self._client.rpc(function_name, payload or {}).execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error("rpc %s failed: %s", function_name, e)
            raise


class DirectPostgresClient:
    """Direct Postgres connection via psycopg2 — ~50× faster than REST for bulk ops."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self._conn = None

    def connect(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url, connect_timeout=15)

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()

    def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
    ) -> list[dict[str, Any]]:
        if not data:
            return []
        if isinstance(data, dict):
            data = [data]
        if not data:
            return []

        columns = list(data[0].keys())
        cols_str = ", ".join(columns)

        if on_conflict:
            conflict_cols = on_conflict.replace(" ", "").split(",")
            update_cols = [c for c in columns if c not in conflict_cols]
            update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
            conflict_clause = f"ON CONFLICT ({on_conflict}) DO UPDATE SET {update_str}"
        else:
            conflict_clause = ""

        sql = f"""
            INSERT INTO {table} ({cols_str})
            VALUES %s
            {conflict_clause}
            RETURNING *
        """

        self.connect()
        with self._conn.cursor() as cursor:
            psycopg2.extras.execute_values(cursor, sql, [(tuple(d.values()) for d in data)], page_size=1000)
            self._conn.commit()
            results = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row, strict=False)) for row in results]

    def select(self, table: str, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        self.connect()

        where_clauses: list[str] = []
        params: list[Any] = []

        if filters:
            for col, val in filters.items():
                for prefix, (op, length) in _FILTER_OPS.items():
                    if val.startswith(prefix):
                        where_clauses.append(f"{col} {op} %s")
                        params.append(val[length:])
                        break

        sql = f"SELECT * FROM {table}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            if not results:
                return []
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row, strict=False)) for row in results]
