# Backfill Follow-ups

## Targeted Moxfield Commander Backfill

- After `logs/backfill_moxfield_commanders_targeted_run_20260408.csv` finishes, run one focused retry pass for transient failures only.
- Retry statuses: `topdeck_timeout`, `topdeck_connection_error`, `supabase_update_failed`, `topdeck_http_error`.
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
  --retry-statuses topdeck_timeout,topdeck_connection_error,supabase_update_failed,topdeck_http_error \
  --attempt-cache logs/backfill_moxfield_commanders_targeted_run_20260408.csv
```
