# Backfill Follow-ups

## Targeted Moxfield Commander Backfill

- After `logs/backfill_moxfield_commanders_targeted_run_20260408.csv` finishes, run a gap pass first for in-range Moxfield rows whose `entry_id` does not appear in the attempt cache.
- Current recoverable gap count from the target list versus cache UUID scan: about `5,360` rows.
- Generate the gap ID list first:

```bash
python3 - <<'PY'
from pathlib import Path
import re

target_ids = [
    line.strip()
    for line in Path("logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt").read_text().splitlines()
    if line.strip()
]
cache_ids = set(
    re.findall(
        r"(?m)^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}),",
        Path("logs/backfill_moxfield_commanders_targeted_run_20260408.csv").read_text(errors="replace"),
    )
)
missing_ids = [entry_id for entry_id in target_ids if entry_id not in cache_ids]
Path("logs/moxfield_entry_ids_2023-12-08_to_2025-10-05_missing_from_cache.txt").write_text(
    "\n".join(missing_ids) + ("\n" if missing_ids else "")
)
print(len(missing_ids))
PY
```

- Then run the backfill against just that gap list:

```bash
python3 packages/backend/src/backfill_moxfield_commanders.py \
  --entry-ids-file logs/moxfield_entry_ids_2023-12-08_to_2025-10-05_missing_from_cache.txt \
  --process-all-moxfield-rows \
  --resolve-topdeck-deck-page \
  --start-date 2023-12-08 \
  --end-date 2025-10-05 \
  --order-direction desc \
  --page-size 25 \
  --topdeck-timeout 10 \
  --attempt-cache logs/backfill_moxfield_commanders_targeted_run_20260408.csv
```

- After the gap pass, run one focused retry pass for transient failures only.
- Retry statuses: `topdeck_timeout`, `topdeck_connection_error`, `supabase_update_failed`, `topdeck_http_error`.
- The script's real CLI uses repeated `--retry-status`, not `--retry-statuses`.
- Recommended command shape:

```bash
python3 packages/backend/src/backfill_moxfield_commanders.py \
  --entry-ids-file logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt \
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
  --attempt-cache logs/backfill_moxfield_commanders_targeted_run_20260408.csv
```

- After the gap pass and transient retry pass, run one final reconciliation check.
- Goal: confirm that every target `entry_id` in `logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt` appears in the attempt cache.
- Recommended reconciliation command:

```bash
python3 - <<'PY'
from pathlib import Path
import re

target_ids = [
    line.strip()
    for line in Path("logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt").read_text().splitlines()
    if line.strip()
]
cache_ids = set(
    re.findall(
        r"(?m)^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}),",
        Path("logs/backfill_moxfield_commanders_targeted_run_20260408.csv").read_text(errors="replace"),
    )
)
missing_ids = [entry_id for entry_id in target_ids if entry_id not in cache_ids]
print(f"target_ids={len(target_ids)}")
print(f"cache_ids={len(cache_ids)}")
print(f"missing_ids={len(missing_ids)}")
if missing_ids:
    Path("logs/moxfield_entry_ids_2023-12-08_to_2025-10-05_missing_after_followups.txt").write_text(
        "\n".join(missing_ids) + "\n"
    )
    print("wrote logs/moxfield_entry_ids_2023-12-08_to_2025-10-05_missing_after_followups.txt")
PY
```

- Success condition: `missing_ids=0`
