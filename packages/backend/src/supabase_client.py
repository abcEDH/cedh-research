"""Supabase REST API and direct Postgres clients."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

# Optional: psycopg2 for direct connection
try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)

SUPABASE_REST_BASE = "https://msjjihqbxtgjdtapywrj.supabase.co"


def _describe_request_failure(exc: BaseException, *, table: str, body_chars: int = 200) -> str:
    """Build a one-line diagnostic for a failed HTTP attempt: class, status, body excerpt."""
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
    # Avoid duplicating "{status} Server Error" when we already have status separately.
    if msg and not (status is not None and msg.startswith(f"{status} ")):
        parts.append(f"err={msg}")
    return " ".join(parts)


def fetch_existing_tids(
    client: SupabaseClient,
    tids: list[str] | None = None,
) -> set[str]:
    """Return existing TopDeck tournament IDs from Supabase.

    When tids are provided, query only those IDs in chunks instead of scanning the
    whole tournaments table.
    """
    if tids is not None:
        existing_tids: set[str] = set()
        chunk_size = 200
        for start in range(0, len(tids), chunk_size):
            chunk = [tid for tid in tids[start : start + chunk_size] if tid]
            if not chunk:
                continue
            page = client.select(
                "tournaments",
                {
                    "select": "topdeck_tid",
                    "topdeck_tid": f"in.({','.join(chunk)})",
                },
            )
            existing_tids.update(row["topdeck_tid"] for row in page if row.get("topdeck_tid"))
        return existing_tids

    rows: list[dict[str, Any]] = []
    offset = 0
    limit = 1000
    while True:
        page = client.select(
            "tournaments",
            {
                "select": "topdeck_tid",
                "topdeck_tid": "not.is.null",
                "order": "start_date.desc,topdeck_tid.asc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return {row["topdeck_tid"] for row in rows if row.get("topdeck_tid")}


class SupabaseClient:
    """Client for Supabase REST API."""

    def __init__(self, url: str, service_key: str):
        self.url = url
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any] | None:
        """Upsert data into a table with retry logic."""
        if max_retries <= 0:
            return None
        endpoint = f"{self.url}/rest/v1/{table}"

        headers = self.headers.copy()
        if on_conflict:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        params: dict[str, str] = {}
        if on_conflict:
            params["on_conflict"] = on_conflict

        for attempt in range(max_retries):
            try:
                response = requests.post(endpoint, json=data, headers=headers, params=params, timeout=90)
                if response.status_code >= 400:
                    logger.error(f"Supabase error: {response.text}")
                    response.raise_for_status()
                return response.json()
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
            ) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Connection error, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    raise

        return None

    def select(self, table: str, filters: dict[str, str] | None = None, max_retries: int = 8) -> list[dict[str, Any]]:
        """Select data from a table with retry logic."""
        if max_retries <= 0:
            return []
        endpoint = f"{self.url}/rest/v1/{table}"
        params = filters or {}

        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, headers=self.headers, params=params, timeout=90)
                if response.status_code >= 500:
                    raise requests.exceptions.HTTPError(f"{response.status_code} Server Error", response=response)
                response.raise_for_status()
                return response.json()
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.HTTPError,
            ) as e:
                diag = _describe_request_failure(e, table=table)
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Query failed: {diag}; retrying in {wait_time}s ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Query failed after {max_retries} retries: {diag}")
                    raise
        # This is a safety net; the loop above either returns or raises
        return []

    def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, str] | None = None,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """Update rows in a table matching filters. Uses PATCH (PostgREST convention)."""
        if max_retries <= 0:
            return []
        endpoint = f"{self.url}/rest/v1/{table}"
        params = filters or {}

        for attempt in range(max_retries):
            try:
                response = requests.patch(endpoint, json=data, headers=self.headers, params=params, timeout=90)
                if response.status_code >= 400:
                    logger.error(f"Supabase update error: {response.text}")
                    response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code is None:
                    status_code = getattr(response, "status_code", None)

                if status_code is not None and status_code >= 500 and attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Update HTTP {status_code}, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(f"Update failed after HTTP error: {e}")
                raise
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
            ) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Update connection error, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Update failed after {max_retries} retries: {e}")
                    raise
        return []

    def rpc(
        self,
        function_name: str,
        payload: dict[str, Any] | None = None,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> Any:
        """Call a Supabase stored procedure via POST /rest/v1/rpc/{function_name}."""
        if max_retries <= 0:
            return None
        endpoint = f"{self.url}/rest/v1/rpc/{function_name}"

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    endpoint,
                    json=payload or {},
                    headers=self.headers,
                    timeout=timeout,
                )
                if response.status_code >= 400:
                    logger.error(f"Supabase RPC error ({function_name}): {response.text}")
                    response.raise_for_status()
                if response.status_code == 204:
                    return None
                return response.json()
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
            ) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"RPC {function_name} failed, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"RPC {function_name} failed after {max_retries} retries: {e}")
                    raise
        return None


class DirectPostgresClient:
    """Client for direct Postgres connection using psycopg2 (faster for large batches)."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self._conn = None

    def connect(self):
        """Establish database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
    ) -> list[dict[str, Any]]:
        """Upsert data using execute_values for high performance."""
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
        """Select data from a table."""
        self.connect()

        where_clauses: list[str] = []
        params: list[Any] = []

        if filters:
            for col, val in filters.items():
                if val.startswith("eq."):
                    where_clauses.append(f"{col} = %s")
                    params.append(val[3:])
                elif val.startswith("ilike."):
                    where_clauses.append(f"{col} ILIKE %s")
                    params.append(val[6:])

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
