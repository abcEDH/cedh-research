# Backfill Follow-ups

## Recommended Workflow

- Do not treat the old attempt cache alone as the source of truth for completion.
- The reliable source of truth is current database state:
  - rows still in the date range
  - rows still storing a Moxfield `decklist_url`
- Treat DB-derived residual manifests as candidate sets, not guaranteed in-range truth.
- Because the relation date filter can leak out-of-range rows, any residual manifest used for `--entry-ids-file` follow-up work should be validated again with the script's local date-window logic.
- Residual reruns should preload prior non-retry statuses so accepted permanent outcomes are skipped instead of rediscovered.
- For `--entry-ids-file` runs, do not pre-filter rows missing TopDeck IDs out of the Supabase fetch. Let the script record them as `missing_topdeck_ids`.

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
- The raw DB-derived manifest is only a candidate residual set. Validate the date window locally before treating it as the true in-range remainder.

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

## Validate The Residual Manifest Locally

- Re-check the date window against the fetched rows themselves before using the manifest as the true in-range residual set.

```bash
python3 - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, "packages/backend/src")
from backfill_moxfield_commanders import fetch_entries_by_ids, load_credentials, row_within_date_window
from ingest import SupabaseClient

supabase_url, supabase_key = load_credentials()
client = SupabaseClient(supabase_url, supabase_key)

candidate_ids = [
    line.strip()
    for line in Path("logs/moxfield_entry_ids_remaining_in_range_postrun.txt").read_text().splitlines()
    if line.strip()
]

validated_ids = []
chunk_size = 100
for index in range(0, len(candidate_ids), chunk_size):
    chunk_ids = candidate_ids[index : index + chunk_size]
    rows = fetch_entries_by_ids(
        client,
        entry_ids=chunk_ids,
        include_known=True,
        require_topdeck_ids=False,
    )
    rows_by_id = {row["id"]: row for row in rows if row.get("id")}
    for entry_id in chunk_ids:
        row = rows_by_id.get(entry_id)
        if row and row_within_date_window(
            row,
            start_date="2023-12-08",
            end_date="2025-10-05",
        ):
            validated_ids.append(entry_id)

out = Path("logs/moxfield_entry_ids_remaining_in_range_postrun_validated.txt")
out.write_text("\n".join(validated_ids) + ("\n" if validated_ids else ""))
print(f"validated_in_range_rows={len(validated_ids)}")
print(f"output={out}")
PY
```

## Seed Non-Retry Statuses Before Residual Reruns

- Do not use a fresh empty cache for the residual rerun.
- Build a seeded attempt cache from prior runs using statuses that should not be retried:
  - `resolved`
  - `bad_moxfield_url`
  - `missing_topdeck_ids`
  - `moxfield_redirect`
  - `no_commander_found`

```bash
python3 - <<'PY'
import csv
from pathlib import Path

NON_RETRY = {
    "resolved",
    "bad_moxfield_url",
    "missing_topdeck_ids",
    "moxfield_redirect",
    "no_commander_found",
}

inputs = [
    Path("logs/backfill_moxfield_commanders_targeted_run_20260408.csv"),
    Path("logs/backfill_moxfield_commanders_residual_in_range_20260409.csv"),
    Path("logs/backfill_moxfield_commanders_residual_in_range_postrun.csv"),
]
output = Path("logs/backfill_moxfield_commanders_residual_in_range_postrun_seeded.csv")

merged = {}
for path in inputs:
    if not path.exists():
        continue
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            entry_id = (row.get("entry_id") or "").strip()
            status = (row.get("status") or "").strip()
            if not entry_id or status not in NON_RETRY:
                continue
            merged[entry_id] = {
                "entry_id": entry_id,
                "status": status,
                "detail": (row.get("detail") or "")[:500],
                "decklist_url": row.get("decklist_url") or "",
                "topdeck_tid": row.get("topdeck_tid") or "",
                "player_topdeck_id": row.get("player_topdeck_id") or "",
                "last_attempted_at": row.get("last_attempted_at") or "",
            }

with output.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "entry_id",
            "status",
            "detail",
            "decklist_url",
            "topdeck_tid",
            "player_topdeck_id",
            "last_attempted_at",
        ],
    )
    writer.writeheader()
    for entry_id in sorted(merged):
        writer.writerow(merged[entry_id])

print(f"seeded_rows={len(merged)}")
print(f"output={output}")
PY
```

## If Residual Rows Remain

- Run one more cleanup pass against the validated residual manifest.
- Use the seeded non-retry cache for that second pass.

```bash
python3 packages/backend/src/backfill_moxfield_commanders.py \
  --entry-ids-file logs/moxfield_entry_ids_remaining_in_range_postrun_validated.txt \
  --process-all-moxfield-rows \
  --resolve-topdeck-deck-page \
  --start-date 2023-12-08 \
  --end-date 2025-10-05 \
  --order-direction desc \
  --page-size 25 \
  --topdeck-timeout 10 \
  --attempt-cache logs/backfill_moxfield_commanders_residual_in_range_postrun_seeded.csv
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
  --entry-ids-file logs/moxfield_entry_ids_remaining_in_range_postrun_validated.txt \
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
  --attempt-cache logs/backfill_moxfield_commanders_residual_in_range_postrun_seeded.csv
```

## Final Success Check

- Final success should be measured by the database, not by old cache presence.
- Success condition:
  - the regenerated DB-derived residual manifest is empty
  - or only contains rows you have explicitly accepted as irreducible Moxfield holdouts
