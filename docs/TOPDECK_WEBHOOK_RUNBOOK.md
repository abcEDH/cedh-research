# TopDeck Webhook Runbook

Operational guide for the TopDeck developer-webhook integration (ADR 0015).
Components: edge function `topdeck-webhook`, table `webhook_events`, RPC
`enqueue_targeted_ingestion`, DB trigger `process_webhook_event`.

## How it works

```
TopDeck ──POST──> topdeck-webhook (HMAC verify → insert webhook_events → 200)
                      │ AFTER INSERT trigger, tournament.finished only
                      ▼
        enqueue_targeted_ingestion(tid) → ingestion_jobs (target_tid)
                      │ net.http_post (vault project_url/anon_key)
                      ▼
        trigger-ingestion-refresh → ci-backend-ingestion.yml
        (tournament_id input) → ingest.py --tournament-id → chain-elo
```

Webhooks only fire for tournaments where the registered TopDeck account is
**on staff**. The daily 06:00 UTC sweep remains the primary pipeline; the
webhook path makes staffed events land minutes after they finish.

## Registration

1. Deploy the function (see below) and register the endpoint at
   https://topdeck.gg/developers:
   `https://msjjihqbxtgjdtapywrj.supabase.co/functions/v1/topdeck-webhook`
2. Copy the signing secret from the portal and set it:
   ```bash
   supabase secrets set TOPDECK_WEBHOOK_SECRET=<secret> --project-ref msjjihqbxtgjdtapywrj
   ```

## Deploy

```bash
# Receiver — MUST skip JWT verification (TopDeck can't send Supabase auth
# headers; the HMAC signature is the auth). config.toml pins this too.
supabase functions deploy topdeck-webhook --no-verify-jwt --project-ref msjjihqbxtgjdtapywrj

# Redeploy the dispatcher whenever its index.ts changes (it passes
# target_tid through to the workflow).
supabase functions deploy trigger-ingestion-refresh --project-ref msjjihqbxtgjdtapywrj
```

The migration (`20260704000000_topdeck_webhook_events.sql`) is applied via
MCP or the Supabase dashboard like every other migration.

## Signature-scheme discovery

TopDeck's exact signing format was unconfirmed when this was built.
`verify.ts` tries HMAC-SHA256 over the raw body (hex and base64, common
header names, `sha256=`/`v1=` prefixes, and a Stripe-style
`timestamp.body` variant). If real deliveries fail verification:

1. Switch to log mode — deliveries are accepted but flagged:
   ```bash
   supabase secrets set TOPDECK_WEBHOOK_SIGNATURE_MODE=log --project-ref msjjihqbxtgjdtapywrj
   ```
2. Fire a **test ping** from the portal, then inspect what TopDeck sent
   (service-role access required — the table has no public read):
   ```sql
   SELECT delivery_id, event_type, signature_valid, headers
   FROM webhook_events ORDER BY received_at DESC LIMIT 5;
   ```
3. Adjust `verify.ts` (it is the only file that encodes the scheme), or if
   only the header name differs, set `TOPDECK_WEBHOOK_SIGNATURE_HEADER`.
4. Flip back to enforcement:
   ```bash
   supabase secrets unset TOPDECK_WEBHOOK_SIGNATURE_MODE --project-ref msjjihqbxtgjdtapywrj
   ```

## Secret rotation

Rotate in the portal, then `supabase secrets set TOPDECK_WEBHOOK_SECRET=...`
immediately after. Deliveries signed with the old secret during the gap are
rejected with 401; TopDeck retries with backoff, and the portal's replay
button covers anything that exhausted its retries.

## Local testing

```bash
# Unit tests for the verifier (self-contained, no registry access needed)
deno test --allow-env packages/backend/supabase/functions/topdeck-webhook/

# Serve locally and POST a correctly signed fake payload
supabase functions serve topdeck-webhook --env-file <(echo TOPDECK_WEBHOOK_SECRET=testsecret)

BODY='{"event":"tournament.finished","TID":"faketid123"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac testsecret -hex | awk '{print $2}')
curl -i -X POST http://127.0.0.1:54321/functions/v1/topdeck-webhook \
  -H "Content-Type: application/json" \
  -H "x-topdeck-signature: sha256=$SIG" \
  -H "x-topdeck-delivery: local-test-001" \
  -d "$BODY"
```

Expected: first POST returns `200 {"ok":true,...}`; repeating the same
`x-topdeck-delivery` returns `duplicate: true`; tampering with the body
returns 401. Source-text assertions for the function and migration live in
`packages/backend/tests/test_topdeck_webhook_function.py` and
`test_topdeck_webhook_migration.py` (run with the normal pytest suite).

## Troubleshooting

`webhook_events.processing_status` values:

| Status | Meaning |
|--------|---------|
| `received` | Inserted; trigger hasn't stamped an outcome (should be transient). |
| `skipped` | Not `tournament.finished`, no TID, or a test ping — logged only. |
| `enqueued` | Targeted ingestion job created; see `ingestion_job_id`. |
| `deferred` | Another job was active; the daily sweep covers it within 24h. |
| `error` | Trigger raised; see `processing_note`. The delivery itself was still stored and acked. |

- **Portal shows 401s** → wrong/rotated secret, or an unrecognized signing
  scheme — run the discovery procedure above.
- **Event `enqueued` but no GitHub run** → check `net._http_response` for
  the pg_net call, then the `trigger-ingestion-refresh` function logs.
- **Targeted job stuck** → the stale-job cron (`cleanup_stale_ingestion_jobs`,
  every 15 min) marks it `stale` after 45 min without a heartbeat.
- **Test ping fabricated a `tournament.finished` with a bogus TID** → the
  targeted job fails on a TopDeck 404 and is marked `failed`; harmless.
