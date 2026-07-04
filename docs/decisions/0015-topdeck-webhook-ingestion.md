# 0015 - TopDeck Webhook Receiver with Raw Event Log

## Status
Accepted

## Context
TopDeck.gg launched developer webhooks (July 2026): a registered endpoint receives signed, retried events (`round.published`, `round.started`, `match.result_reported`, `round.ended`, `tournament.finished`, `player.registered`, `player.dropped`, `tournament.checkin_started`) for every tournament where the account is on staff. Until now the only path from TopDeck to Supabase was the daily 06:00 UTC batch (ADR 0007), so results landed up to ~24h after an event ended.

Webhooks cannot replace polling — they only fire for staffed events, and this project aggregates the whole ≥32-player cEDH ecosystem. At adoption time we have no staffed events; the integration is exploratory, and the exact signing scheme/payload shapes were not yet observable.

## Decision
- **Raw-event-log-first.** The receiver persists *every* delivery verbatim (`webhook_events` table: payload, headers, delivery id) regardless of type, so future consumers (`match.result_reported` for authoritative W/L/D, live coverage, roster events) are designed against real payloads rather than guessed schemas.
- **One consumer at launch.** `tournament.finished` enqueues a targeted single-TID ingestion through the *existing* job machinery: `enqueue_targeted_ingestion` (shares the daily enqueue's advisory lock) → `trigger-ingestion-refresh` edge function → `ci-backend-ingestion.yml` with a new `tournament_id` input → `ingest.py --tournament-id`. No ingestion logic is reimplemented in Deno.
- **Receiver lives in Supabase Edge Functions** (`topdeck-webhook`), not `apps/web` — the frontend stays a pure read model (ADR 0005). Deployed with `verify_jwt = false`; the HMAC signature is the authentication.
- **Consumer work happens in a DB trigger, not the receiver.** `process_webhook_event` is exception-safe (failures are recorded on the event row), so a consumer bug can never surface as a webhook 5xx and trip TopDeck's retry backoff.
- **The webhook signing secret (`TOPDECK_WEBHOOK_SECRET`) is backend-only**, extending ADR 0013's posture for `TOPDECK_API_KEY`.
- **Signature verification is isolated in `verify.ts`** with a `log`-mode escape hatch (`TOPDECK_WEBHOOK_SIGNATURE_MODE`), because the upstream scheme was unconfirmed at build time. Discovery procedure lives in `docs/TOPDECK_WEBHOOK_RUNBOOK.md`.

## Consequences

**Easier**
- Staffed events land minutes after they finish (ingest + chained Elo refresh) instead of the next morning.
- Future webhook consumers start from accumulated real payloads in `webhook_events`.
- Replay/redelivery is safe end-to-end: unique `delivery_id` + `ON CONFLICT DO NOTHING` means the trigger fires at most once per delivery.

**Harder**
- Two ingestion entry points (daily sweep + targeted) must serialize; this is handled by the shared advisory lock and a per-TID workflow concurrency group, and both must be preserved by future changes.
- `webhook_events` is service-role-only (payloads may carry player PII), so debugging requires service-role access.
- If a targeted enqueue is blocked by an active job the event is only `deferred` — freshness falls back to the daily sweep rather than retrying.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- TopDeck developer announcement ("Developer webhooks are live", July 2026) — https://topdeck.gg/docs/webhooks
- `packages/backend/supabase/migrations/20260704000000_topdeck_webhook_events.sql`
- `packages/backend/supabase/functions/topdeck-webhook/`
- `docs/TOPDECK_WEBHOOK_RUNBOOK.md`
- ADR 0007 (split cron pipelines), ADR 0013 (TopDeck compliance)
