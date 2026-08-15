export type ScryfallCardArt = {
  artCrop: string | null;
  normal: string | null;
  typeLine: string | null;
  setName: string | null;
};

const SCRYFALL_THROTTLE_MS = 100;

const cache = new Map<string, ScryfallCardArt | null>();
const inflight = new Map<string, Promise<ScryfallCardArt | null>>();

let requestChain: Promise<unknown> = Promise.resolve();
let lastRequestAt = 0;

function throttledFetch(url: string): Promise<Response> {
  const run = requestChain.then(async () => {
    const wait = Math.max(0, lastRequestAt + SCRYFALL_THROTTLE_MS - Date.now());
    if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
    lastRequestAt = Date.now();
    return fetch(url);
  });
  // Keep the chain alive even if this request fails, so later callers aren't stuck.
  requestChain = run.then(
    () => undefined,
    () => undefined
  );
  return run;
}

/**
 * Split a commander/card name into individual Scryfall-lookup names.
 *
 * This project's `commander_name` values use `" / "` (single slash) for
 * partner pairs — see `normalize_commander_name()` in
 * `packages/backend/src/ingest.py` — while actual Magic split/MDFC cards use
 * Scryfall's own `" // "` (double slash) convention (e.g. "Fire // Ice").
 * `" // "` never contains `" / "` as a substring, so checking it first is
 * unambiguous.
 */
export function splitCardName(name: string): string[] {
  const separator = name.includes(" // ") ? " // " : name.includes(" / ") ? " / " : null;
  const parts = separator ? name.split(separator) : [name];
  return parts.map((part) => part.trim()).filter(Boolean);
}

export async function fetchScryfallArt(rawName: string): Promise<ScryfallCardArt | null> {
  const name = splitCardName(rawName)[0] ?? rawName;
  if (cache.has(name)) return cache.get(name) ?? null;

  const existing = inflight.get(name);
  if (existing) return existing;

  const promise = (async (): Promise<ScryfallCardArt | null> => {
    try {
      const res = await throttledFetch(
        `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}`
      );
      if (!res.ok) {
        // Only cache a permanent miss (404 — Scryfall found no such card).
        // Transient failures (429 rate-limit, 5xx) must not be cached as "no
        // art", or a temporary hiccup blacklists that card for the rest of
        // the session; leave the cache empty so a later call retries.
        if (res.status === 404) cache.set(name, null);
        return null;
      }
      const data = await res.json();
      const face = data.image_uris ? data : (data.card_faces ?? [])[0] ?? {};
      const images = face.image_uris ?? data.image_uris ?? {};
      const result: ScryfallCardArt = {
        artCrop: images.art_crop ?? null,
        normal: images.normal ?? null,
        typeLine: data.type_line ?? face.type_line ?? null,
        setName: data.set_name ?? null,
      };
      cache.set(name, result);
      return result;
    } catch {
      // Network failure — also transient, don't cache.
      return null;
    } finally {
      inflight.delete(name);
    }
  })();

  inflight.set(name, promise);
  return promise;
}
