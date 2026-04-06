These migrations were kept out of the active `supabase/migrations` directory
because the remote Supabase project's migration ledger is the source of truth
for the `20260202000000`-`20260202000002` timestamps.

The active branch keeps the matching `*_remote_placeholder.sql` files so
`supabase migration list` and `supabase db push` can reconcile cleanly with
the remote database.
