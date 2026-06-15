These migrations were kept out of the active `supabase/migrations` directory
because the remote Supabase project's migration ledger is the source of truth
for the `20260202000000`-`20260202000002` timestamps.

The active branch keeps the matching `*_remote_placeholder.sql` files so
`supabase migration list` and `supabase db push` can reconcile cleanly with
the remote database.

June 10, 2026 ledger-version repair:

The linked production project records the June 10 Elo/profile schema changes
under the Supabase-generated versions:

- 20260610210415
- 20260610213012
- 20260610230303

Earlier local migration files used these versions instead:

- 20260610000000
- 20260610010000
- 20260610020000

If a non-production database applied those earlier local versions before the
active migration filenames were aligned to production, first verify that the
columns from those migrations already exist. Then repair the old local versions
out of that database's migration ledger and run the active migrations:

```bash
supabase migration repair --status reverted 20260610000000 20260610010000 20260610020000
supabase db push
```

Do not add no-op placeholder migrations for these old versions to the active
chain. Supabase Preview applies new migration files only, so adding older
timestamp placeholders after the production-ledger versions creates noisy
out-of-order migration warnings.
