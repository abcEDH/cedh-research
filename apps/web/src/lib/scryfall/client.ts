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

/** Commander/card names use MTG's " // " partner and split-card separator; Scryfall lookups need the front face. */
export function splitCardName(name: string): string[] {
  return name
    .split(" // ")
    .map((part) => part.trim())
    .filter(Boolean);
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
        cache.set(name, null);
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
      cache.set(name, null);
      return null;
    } finally {
      inflight.delete(name);
    }
  })();

  inflight.set(name, promise);
  return promise;
}
