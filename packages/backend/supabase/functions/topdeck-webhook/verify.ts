// Signature verification for TopDeck developer webhooks.
//
// TopDeck's exact signing scheme is not yet confirmed against a live
// delivery, so this module is deliberately defensive: it tries several
// common header names and encodings, and it is the ONLY file that needs
// to change once the real scheme is observed (see
// docs/TOPDECK_WEBHOOK_RUNBOOK.md for the discovery procedure).

const DEFAULT_SIGNATURE_HEADERS = [
  "x-topdeck-signature",
  "x-webhook-signature",
  "x-signature",
  "webhook-signature",
];

const TIMESTAMP_HEADERS = [
  "x-topdeck-timestamp",
  "x-webhook-timestamp",
  "webhook-timestamp",
];

export type VerifyResult = {
  valid: boolean;
  reason?: string;
};

const encoder = new TextEncoder();

async function hmacSha256(secret: string, message: string): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return new Uint8Array(signature);
}

export function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function toBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export async function sha256Hex(message: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(message));
  return toHex(new Uint8Array(digest));
}

// Constant-time string comparison. Comparing SHA-256 digests of both
// sides makes timing independent of where the strings differ without
// hand-rolling an XOR loop over attacker-controlled lengths.
async function timingSafeEqual(a: string, b: string): Promise<boolean> {
  const [digestA, digestB] = await Promise.all([sha256Hex(a), sha256Hex(b)]);
  return digestA === digestB && a.length === b.length;
}

function stripKnownPrefixes(value: string): string {
  return value.replace(/^(sha256=|v1=|v1,)/i, "").trim();
}

function candidateSignatureValues(headers: Headers): string[] {
  const configured = Deno.env.get("TOPDECK_WEBHOOK_SIGNATURE_HEADER");
  const headerNames = configured ? [configured] : DEFAULT_SIGNATURE_HEADERS;

  const values: string[] = [];
  for (const name of headerNames) {
    const raw = headers.get(name);
    if (!raw) continue;
    // Svix-style headers can carry several space-separated signatures.
    for (const part of raw.split(/\s+/)) {
      const stripped = stripKnownPrefixes(part);
      if (stripped) values.push(stripped);
    }
  }
  return values;
}

export async function verifyTopdeckSignature(
  rawBody: string,
  headers: Headers,
  secret: string,
): Promise<VerifyResult> {
  if (!secret) {
    return { valid: false, reason: "TOPDECK_WEBHOOK_SECRET is not configured" };
  }

  const provided = candidateSignatureValues(headers);
  if (provided.length === 0) {
    return { valid: false, reason: "No signature header present" };
  }

  const messages = [rawBody];
  for (const name of TIMESTAMP_HEADERS) {
    const ts = headers.get(name);
    // Stripe-style: HMAC over "<timestamp>.<body>".
    if (ts) messages.push(`${ts}.${rawBody}`);
  }

  for (const message of messages) {
    const mac = await hmacSha256(secret, message);
    const expectedHex = toHex(mac);
    const expectedBase64 = toBase64(mac);
    for (const candidate of provided) {
      if (await timingSafeEqual(candidate.toLowerCase(), expectedHex)) {
        return { valid: true };
      }
      if (await timingSafeEqual(candidate, expectedBase64)) {
        return { valid: true };
      }
    }
  }

  return { valid: false, reason: "Signature mismatch" };
}
