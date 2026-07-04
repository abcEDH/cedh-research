// deno test --allow-env packages/backend/supabase/functions/topdeck-webhook/
//
// Not wired into CI (no Deno step exists yet) — run manually after any
// change to verify.ts. See docs/TOPDECK_WEBHOOK_RUNBOOK.md.
import { sha256Hex, verifyTopdeckSignature } from "./verify.ts";

// Local assert keeps the test dependency-free — no Deno toolchain or
// registry access is set up in this repo's CI.
function assertEquals<T>(actual: T, expected: T): void {
  if (actual !== expected) {
    throw new Error(`Expected ${expected}, got ${actual}`);
  }
}

const SECRET = "testsecret";
const BODY = '{"event":"tournament.finished","TID":"faketid123"}';

// printf '%s' "$BODY" | openssl dgst -sha256 -hmac testsecret
const BODY_HMAC_HEX =
  "177c00783250fa3d51b18307c619f1abb44341389e676cef1dbbd5debdff10fa";
// echo -n <hex> | xxd -r -p | base64
const BODY_HMAC_B64 = "F3wAeDJQ+j1RsYMHxhnxq7RDQTieZ2zvHbvV3r3/EPo=";

function headers(init: Record<string, string>): Headers {
  return new Headers(init);
}

Deno.test("valid hex signature", async () => {
  const result = await verifyTopdeckSignature(
    BODY,
    headers({ "x-topdeck-signature": BODY_HMAC_HEX }),
    SECRET,
  );
  assertEquals(result.valid, true);
});

Deno.test("valid hex signature with sha256= prefix", async () => {
  const result = await verifyTopdeckSignature(
    BODY,
    headers({ "x-topdeck-signature": `sha256=${BODY_HMAC_HEX}` }),
    SECRET,
  );
  assertEquals(result.valid, true);
});

Deno.test("valid uppercase hex signature", async () => {
  const result = await verifyTopdeckSignature(
    BODY,
    headers({ "x-topdeck-signature": BODY_HMAC_HEX.toUpperCase() }),
    SECRET,
  );
  assertEquals(result.valid, true);
});

Deno.test("valid base64 signature on alternate header", async () => {
  const result = await verifyTopdeckSignature(
    BODY,
    headers({ "x-webhook-signature": `v1=${BODY_HMAC_B64}` }),
    SECRET,
  );
  assertEquals(result.valid, true);
});

Deno.test("timestamped Stripe-style signature", async () => {
  const ts = "1751600000";
  // HMAC over `${ts}.${BODY}` computed with WebCrypto itself — this
  // asserts the timestamped path is attempted, not a fixed vector.
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = new Uint8Array(
    await crypto.subtle.sign(
      "HMAC",
      key,
      new TextEncoder().encode(`${ts}.${BODY}`),
    ),
  );
  const macHex = Array.from(mac).map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  const result = await verifyTopdeckSignature(
    BODY,
    headers({
      "x-topdeck-signature": macHex,
      "x-topdeck-timestamp": ts,
    }),
    SECRET,
  );
  assertEquals(result.valid, true);
});

Deno.test("tampered body is rejected", async () => {
  const result = await verifyTopdeckSignature(
    BODY.replace("faketid123", "evil"),
    headers({ "x-topdeck-signature": BODY_HMAC_HEX }),
    SECRET,
  );
  assertEquals(result.valid, false);
});

Deno.test("wrong secret is rejected", async () => {
  const result = await verifyTopdeckSignature(
    BODY,
    headers({ "x-topdeck-signature": BODY_HMAC_HEX }),
    "wrongsecret",
  );
  assertEquals(result.valid, false);
});

Deno.test("missing signature header is rejected", async () => {
  const result = await verifyTopdeckSignature(BODY, headers({}), SECRET);
  assertEquals(result.valid, false);
  assertEquals(result.reason, "No signature header present");
});

Deno.test("empty secret is rejected", async () => {
  const result = await verifyTopdeckSignature(
    BODY,
    headers({ "x-topdeck-signature": BODY_HMAC_HEX }),
    "",
  );
  assertEquals(result.valid, false);
});

Deno.test("sha256Hex matches a known vector", async () => {
  // printf '%s' abc | sha256sum
  assertEquals(
    await sha256Hex("abc"),
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  );
});
