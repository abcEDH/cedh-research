# Backfill Follow-ups

## Recommended Workflow

- Do not treat the old attempt cache alone as the source of truth for completion.
- The reliable source of truth is current database state:
  - rows still in the date range
  - rows still storing a Moxfield `decklist_url`

## Current Corrective Pass

- Current residual manifest:
  - `logs/moxfield_entry_ids_remaining_in_range_20260409.txt`
- Current corrective run cache:
  - `logs/backfill_moxfield_commanders_residual_in_range_20260409.csv`
- This residual manifest was generated directly from Supabase for rows where:
  - `decklist_url ilike '%moxfield.com%'`
  - `tournaments.start_date` is between `2023-12-08` and `2025-10-05`

## After The Current Residual Run Finishes

- Regenerate a fresh residual manifest from the database.
- Goal: identify rows that still have a Moxfield `decklist_url` after the current corrective run.

```bash
python3 - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, "packages/backend/src")
from backfill_moxfield_commanders import load_credentials
from ingest import SupabaseClient

supabase_url, supabase_key = load_credentials()
client = SupabaseClient(supabase_url, supabase_key)

ids = []
offset = 0
limit = 1000
while True:
    rows = client.select(
        "tournament_entries",
        {
            "select": "id,players(topdeck_id),tournaments(topdeck_tid,start_date)",
            "decklist_url": "ilike.*moxfield.com*",
            "tournaments.start_date": ["gte.2023-12-08", "lte.2025-10-05"],
            "limit": limit,
            "offset": offset,
            "order": "id.asc",
        },
    )
    if not rows:
        break
    ids.extend(row["id"] for row in rows if row.get("id"))
    offset += len(rows)
    if len(rows) < limit:
        break

out = Path("logs/moxfield_entry_ids_remaining_in_range_postrun.txt")
out.write_text("\n".join(ids) + ("\n" if ids else ""))
print(f"remaining_in_range_rows={len(ids)}")
print(f"output={out}")
PY
```

## If Residual Rows Remain

- Run one more cleanup pass against that fresh DB-derived residual manifest.
- Use a fresh attempt cache for that second pass.

```bash
python3 packages/backend/src/backfill_moxfield_commanders.py \
  --entry-ids-file logs/moxfield_entry_ids_remaining_in_range_postrun.txt \
  --process-all-moxfield-rows \
  --resolve-topdeck-deck-page \
  --start-date 2023-12-08 \
  --end-date 2025-10-05 \
  --order-direction desc \
  --page-size 25 \
  --topdeck-timeout 10 \
  --attempt-cache logs/backfill_moxfield_commanders_residual_in_range_postrun.csv
```

## After The Residual Follow-up Pass

- If the second residual pass completes and there are still Moxfield rows left, inspect the remainder directly.
- Common expected remainder classes:
  - `moxfield_redirect`
  - `bad_moxfield_url`
  - rows where TopDeck metadata exists but TopDeck still does not expose a standalone native deck page

## Optional Transient Retry

- If you want one final focused retry after the second residual pass, use the second pass's own cache.
- Retry statuses:
  - `topdeck_timeout`
  - `topdeck_connection_error`
  - `supabase_update_failed`
  - `topdeck_http_error`
- The real CLI uses repeated `--retry-status`.

```bash
python3 packages/backend/src/backfill_moxfield_commanders.py \
  --entry-ids-file logs/moxfield_entry_ids_remaining_in_range_postrun.txt \
  --process-all-moxfield-rows \
  --resolve-topdeck-deck-page \
  --start-date 2023-12-08 \
  --end-date 2025-10-05 \
  --order-direction desc \
  --page-size 25 \
  --topdeck-timeout 10 \
  --retry-status topdeck_timeout \
  --retry-status topdeck_connection_error \
  --retry-status supabase_update_failed \
  --retry-status topdeck_http_error \
  --attempt-cache logs/backfill_moxfield_commanders_residual_in_range_postrun.csv
```

## Final Success Check

- Final success should be measured by the database, not by old cache presence.
- Success condition:
  - the regenerated DB-derived residual manifest is empty
  - or only contains rows you have explicitly accepted as irreducible Moxfield holdouts

