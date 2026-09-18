"""Supabase clients: supabase-py REST wrapper and direct Postgres."""

from __future__ import annotations

# Optional: psycopg2 for direct connection
import importlib.util
import logging
import os
from datetime import date
from typing import Any

from supabase import Client, create_client
from supabase_query import UPSERT_BATCH_SIZE, fetch_all, upsert_batched

PSYCOPG2_AVAILABLE = importlib.util.find_spec("psycopg2") is not None
if PSYCOPG2_AVAILABLE:
    import psycopg2
    import psycopg2.extras

logger = logging.getLogger(__name__)

SUPABASE_REST_BASE = "https://msjjihqbxtgjdtapywrj.supabase.co"

# Maps PostgREST-style filter prefixes to (SQL operator, prefix length).
# Used only by DirectPostgresClient.select() to translate shared filter dicts.
_FILTER_OPS: dict[str, tuple[str, int]] = {
    "eq.": ("=", 3),
    "neq.": ("!=", 4),
    "gte.": (">=", 4),
    "lte.": ("<=", 4),
    "ilike.": ("ILIKE", 6),
}

# Params that control query structure, not row filtering.
_STRUCTURAL_PARAMS = frozenset({"select", "limit", "offset", "order"})
ELO_TIER_FILTERS = {
    "ranking": "ranking_eligible",
    "local": "local_eligible",
    "all": "all_eligible",
}


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


def eligible_game_ids(rows: list[dict[str, Any]], tier: str) -> set[str]:
    if tier not in ELO_TIER_FILTERS:
        raise ValueError(f"Unknown Elo tier: {tier}")
    flag = ELO_TIER_FILTERS[tier]
    return {str(row["game_id"]) for row in rows if row.get("game_id") and row.get(flag) is True}


def fetch_tier_results_for_window(
    client: Client,
    window_start: date,
    window_end: date,
    tier: str,
    select: str,
) -> list[dict[str, Any]]:
    if tier not in ELO_TIER_FILTERS:
        raise ValueError(f"Unknown Elo tier: {tier}")

    eligible_rows = fetch_all(
        client,
        "global_elo_game_results",
        columns=select,
        filters=[
            ("start_date", "gte", window_start.isoformat()),
            ("start_date", "lt", window_end.isoformat()),
            (ELO_TIER_FILTERS[tier], "eq", "true"),
        ],
        label=f"global_elo_game_results {window_start:%Y-%m}",
    )
    if tier == "all":
        return eligible_rows

    game_ids = eligible_game_ids(eligible_rows, tier)
    complete_rows: list[dict[str, Any]] = []
    ordered_ids = sorted(game_ids)
    for start in range(0, len(ordered_ids), 200):
        chunk = ordered_ids[start : start + 200]
        complete_rows.extend(
            fetch_all(
                client,
                "global_elo_game_results",
                columns=select,
                filters=[("game_id", "in", chunk)],
                label=f"global_elo_game_results {window_start:%Y-%m} complete pods",
            )
        )
    return complete_rows


def fetch_existing_tids(
    client: Client,
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
            rows = client.table("tournaments").select("topdeck_tid").in_("topdeck_tid", chunk).execute().data
            existing.update(r["topdeck_tid"] for r in rows if r.get("topdeck_tid"))
        return existing

    rows = fetch_all(
        client,
        "tournaments",
        columns="topdeck_tid",
        filters=[("topdeck_tid", "not_is", "null")],
        order=[("start_date", True), ("topdeck_tid", False)],
        label="tournaments",
    )
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

        # A dict is a single row; lists are batched so one upsert never becomes
        # an oversized SQL statement that trips the Postgres statement_timeout.
        if not isinstance(data, list):
            batches: list[list[dict[str, Any]]] = [[data]]
        else:
            batches = [data[i : i + UPSERT_BATCH_SIZE] for i in range(0, len(data), UPSERT_BATCH_SIZE)] or [[]]

        collected: list[dict[str, Any]] = []
        try:
            for batch in batches:
                if not batch:
                    continue
                result = self._client.table(table).upsert(batch, **kwargs).execute()
                if result.data:
                    collected.extend(result.data)
            return collected
        except Exception as e:
            logger.error("upsert failed on %s: %s", table, e)
            raise

    def select(
        self,
        table: str,
        filters: dict[str, Any] | list[tuple[str, Any]] | None = None,
        max_retries: int = 8,
    ) -> list[dict[str, Any]]:
        params = filters or {}
        filter_items = params.items() if isinstance(params, dict) else params
        structural_params = params if isinstance(params, dict) else dict(params)
        columns = str(structural_params.get("select", "*"))
        limit_raw = structural_params.get("limit")
        offset_raw = structural_params.get("offset")
        order_raw = structural_params.get("order")

        q = self._client.table(table).select(columns)

        for col, val in filter_items:
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

    def call_function(self, function_name: str) -> None:
        """Invoke a no-arg void SQL function (e.g. a materialized-view refresh).

        Runs over the direct Postgres connection, bypassing the REST gateway —
        which returns a 504 on refreshes that run longer than its request limit.
        The function's own statement_timeout still applies.
        """
        if not function_name.isidentifier():
            raise ValueError(f"unsafe function name: {function_name!r}")
        self.connect()
        try:
            with self._conn.cursor() as cursor:
                cursor.execute(f"SELECT public.{function_name}()")
            self._conn.commit()
        except Exception:
            # Leave the connection usable for the next call; otherwise psycopg2
            # keeps it in an aborted transaction and every later refresh fails.
            self._conn.rollback()
            raise

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
            psycopg2.extras.execute_values(cursor, sql, [tuple(d.values()) for d in data], page_size=1000)
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


# fetch_all/upsert_batched/UPSERT_BATCH_SIZE now live in supabase_query.py (see
# AGENTS.md's module-extraction rule); re-exported here for the many existing
# `from supabase_client import fetch_all` call sites.
__all__ = [
    "SUPABASE_REST_BASE",
    "UPSERT_BATCH_SIZE",
    "ELO_TIER_FILTERS",
    "DirectPostgresClient",
    "SupabaseClient",
    "get_supabase_client",
    "fetch_all",
    "upsert_batched",
    "eligible_game_ids",
    "fetch_tier_results_for_window",
    "fetch_existing_tids",
    "_describe_request_failure",
]
