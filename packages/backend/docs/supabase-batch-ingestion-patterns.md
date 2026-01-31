# Supabase Batch Ingestion Patterns

**Research Date:** 2026-01-11
**Source:** Gemini CLI research + web search
**Project:** cedh-analytics

## Summary

Efficiently ingesting batch data into Supabase requires balancing ease of use with raw performance. The best approach depends on dataset size.

## Decision Matrix

| Dataset Size | Recommended Method | Batch Size | Speed |
|--------------|-------------------|------------|-------|
| Small (<1k rows) | `supabase-py` REST API | All at once | ~100 rows/sec |
| Medium (1k-10k) | `supabase-py` REST API batched | 500-1000 | ~500 rows/sec |
| Large (10k-100k) | `psycopg2.execute_values` | 2,000-10,000 | ~5,000 rows/sec |
| Very Large (100k+) | PostgreSQL `COPY` command | Stream | ~50,000+ rows/sec |

## Method 1: REST API (supabase-py)

Best for: Convenience, small-medium datasets, serverless environments

```python
from supabase import create_client, Client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Insert batch of records
data = [{"name": "value1"}, {"name": "value2"}, ...]
response = supabase.table("table_name").insert(data).execute()

# Upsert with conflict resolution
response = supabase.table("table_name").upsert(data).execute()
```

**Pros:**
- Simple API, no connection management
- Works in serverless (Edge Functions, Vercel)
- Automatic retries possible

**Cons:**
- HTTP overhead per request
- ~500 row practical limit per call
- Slower than direct connection

## Method 2: Direct Postgres with psycopg2

Best for: Medium-large datasets, scheduled batch jobs

### Pattern A: execute_values (Recommended)

```python
import psycopg2
from psycopg2.extras import execute_values

def batch_insert_direct(conn_string: str, table: str, columns: list, data: list, batch_size: int = 5000):
    """
    High-performance batch insert using psycopg2.

    Args:
        conn_string: PostgreSQL connection string from Supabase dashboard
        table: Target table name
        columns: List of column names
        data: List of tuples matching column order
        batch_size: Rows per batch (2000-10000 recommended)
    """
    cols = ", ".join(columns)
    sql = f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"

    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            execute_values(cursor, sql, data, page_size=batch_size)
        conn.commit()
```

### Pattern B: COPY Command (Fastest)

```python
import psycopg2
import io

def batch_copy(conn_string: str, table: str, columns: list, data: list):
    """
    Maximum performance using PostgreSQL COPY command.
    Best for 100k+ rows or loading from files.
    """
    cols = ", ".join(columns)
    sql = f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT CSV)"

    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cursor:
            # Create in-memory CSV
            buffer = io.StringIO()
            for row in data:
                buffer.write(",".join(map(str, row)) + "\n")
            buffer.seek(0)

            cursor.copy_expert(sql, buffer)
        conn.commit()
```

## Connection String

Find in Supabase Dashboard: **Project Settings > Database > Connection string > URI**

Format: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`

For connection pooling (recommended for concurrent access):
`postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres?pgbouncer=true`

## Best Practices

1. **Always batch** - Never insert one row at a time
2. **Use transactions** - Wrap batches in single transaction
3. **Tune batch size** - Start with 5000, adjust based on row size
4. **Add indexes after** - For large loads, add indexes post-insert
5. **Use UPSERT** - `ON CONFLICT` for idempotent operations
6. **Monitor connections** - Don't exceed Supabase connection limits

## Supabase-Specific Notes

- **Connection Pooler**: Use port 6543 for PgBouncer (better for many short connections)
- **Direct Connection**: Use port 5432 for long-running batch jobs
- **Row Level Security**: Service role key bypasses RLS for ingestion
- **Realtime**: Disable realtime on tables during bulk loads for performance

## References

- [Supabase Discussion #11349 - Best Practices for Large Inserts](https://github.com/orgs/supabase/discussions/11349)
- [Supabase Python Upsert Docs](https://supabase.com/docs/reference/python/upsert)
- [psycopg2 execute_values](https://www.psycopg.org/docs/extras.html#fast-exec)
- [PostgreSQL COPY](https://www.postgresql.org/docs/current/sql-copy.html)
