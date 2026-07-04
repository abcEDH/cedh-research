// TopDeck developer-webhook receiver (ADR 0015).
//
// Responsibilities are deliberately minimal: verify the signature over
// the RAW body, persist the delivery into webhook_events, and ack fast.
// All consumer work (tournament.finished -> targeted ingestion) happens
// in the process_webhook_event database trigger, so a consumer failure
// can never surface as a 5xx and trigger TopDeck's retry backoff.
//
// Deployed with JWT verification disabled (see supabase/config.toml):
// TopDeck cannot send Supabase auth headers, the HMAC is the auth.
import { sha256Hex, verifyTopdeckSignature } from "./verify.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL");
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
const TOPDECK_WEBHOOK_SECRET = Deno.env.get("TOPDECK_WEBHOOK_SECRET") ?? "";
// "enforce" (default) rejects bad signatures with 401. "log" accepts
// them but records signature_valid=false — used only during scheme
// discovery, before the real TopDeck signing format is confirmed.
const SIGNATURE_MODE = Deno.env.get("TOPDECK_WEBHOOK_SIGNATURE_MODE") ?? "enforce";

const DELIVERY_ID_HEADERS = [
  "x-topdeck-delivery",
  "x-topdeck-delivery-id",
  "x-webhook-id",
  "webhook-id",
];

const EVENT_TYPE_HEADERS = ["x-topdeck-event", "x-webhook-event"];

function json(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requireEnv(name: string, value: string | undefined): string {
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function firstHeader(headers: Headers, names: string[]): string | null {
  for (const name of names) {
    const value = headers.get(name);
    if (value) return value;
  }
  return null;
}

// deno-lint-ignore no-explicit-any
function extractEventType(payload: any, headers: Headers): string {
  return (
    payload?.event ??
    payload?.type ??
    payload?.event_type ??
    firstHeader(headers, EVENT_TYPE_HEADERS) ??
    "unknown"
  );
}

// deno-lint-ignore no-explicit-any
function extractTid(payload: any): string | null {
  const tid = payload?.TID ??
    payload?.tid ??
    payload?.tournament?.TID ??
    payload?.tournament?.tid ??
    payload?.tournament?.id ??
    payload?.data?.TID ??
    payload?.data?.tid ??
    null;
  return typeof tid === "string" && tid.trim() ? tid.trim() : null;
}

// deno-lint-ignore no-explicit-any
function isTestDelivery(payload: any, eventType: string): boolean {
  if (payload?.test === true || payload?.is_test === true) return true;
  const normalized = eventType.toLowerCase();
  return normalized === "ping" || normalized === "test" ||
    normalized.endsWith(".ping") || normalized.endsWith(".test");
}

function headersToJson(headers: Headers): Record<string, string> {
  const result: Record<string, string> = {};
  headers.forEach((value, key) => {
    // Never persist inbound auth material.
    if (key === "authorization" || key === "apikey") return;
    result[key] = value;
  });
  return result;
}

type InsertResult = { inserted: boolean; eventId: string | null };

async function insertWebhookEvent(
  row: Record<string, unknown>,
): Promise<InsertResult> {
  const baseUrl = requireEnv("SUPABASE_URL", SUPABASE_URL);
  const serviceRoleKey = requireEnv(
    "SUPABASE_SERVICE_ROLE_KEY",
    SUPABASE_SERVICE_ROLE_KEY,
  );

  const response = await fetch(`${baseUrl}/rest/v1/webhook_events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      // ON CONFLICT DO NOTHING on the delivery_id unique index: a
      // redelivered/replayed event returns an empty representation and
      // the processing trigger does not fire again.
      Prefer: "resolution=ignore-duplicates,return=representation",
    },
    body: JSON.stringify(row),
  });

  if (!response.ok) {
    throw new Error(
      `webhook_events insert failed: ${response.status} ${await response.text()}`,
    );
  }

  const rows = response.status === 201 ? await response.json() : [];
  if (Array.isArray(rows) && rows.length > 0) {
    return { inserted: true, eventId: rows[0].id ?? null };
  }
  return { inserted: false, eventId: null };
}

Deno.serve(async (request) => {
  if (request.method !== "POST") {
    return json(405, { error: "Method not allowed" });
  }

  // Raw body first — the signature is over the exact bytes TopDeck
  // sent, never a re-serialized parse.
  const rawBody = await request.text();

  const verification = await verifyTopdeckSignature(
    rawBody,
    request.headers,
    TOPDECK_WEBHOOK_SECRET,
  );
  if (!verification.valid && SIGNATURE_MODE !== "log") {
    return json(401, { error: "Invalid signature", reason: verification.reason });
  }

  // deno-lint-ignore no-explicit-any
  let payload: any;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return json(400, { error: "Invalid JSON body" });
  }

  const eventType = extractEventType(payload, request.headers);
  const deliveryId = firstHeader(request.headers, DELIVERY_ID_HEADERS) ??
    `sha256:${await sha256Hex(rawBody)}`;

  try {
    const result = await insertWebhookEvent({
      delivery_id: deliveryId,
      event_type: eventType,
      tid: extractTid(payload),
      payload,
      headers: headersToJson(request.headers),
      signature_valid: verification.valid,
      is_test: isTestDelivery(payload, eventType),
    });

    if (!result.inserted) {
      return json(200, { ok: true, duplicate: true, delivery_id: deliveryId });
    }
    return json(200, { ok: true, event_id: result.eventId });
  } catch (error) {
    // Storage failure is the one case where TopDeck SHOULD retry.
    const message = error instanceof Error ? error.message : String(error);
    console.error("topdeck-webhook storage failure:", message);
    return json(500, { error: "Failed to persist event" });
  }
});
