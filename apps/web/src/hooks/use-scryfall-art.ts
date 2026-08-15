"use client";

import { useEffect, useRef, useState } from "react";
import { fetchScryfallArt, type ScryfallCardArt } from "@/lib/scryfall/client";

// Bounded backoff for the *current* mounted consumer. fetchScryfallArt only
// caches a `null` result for a confirmed 404 (permanent miss) — a 429/5xx/
// network failure is left uncached specifically so a retry re-hits the
// network instead of being short-circuited, so these retries are "free" for
// an actual miss (fast cache hit) and a real second chance for a transient one.
const RETRY_DELAYS_MS = [500, 1500];

async function fetchWithRetry(
  name: string | null | undefined,
  isCancelled: () => boolean
): Promise<ScryfallCardArt | null> {
  if (!name) return null;
  let result = await fetchScryfallArt(name);
  for (const delay of RETRY_DELAYS_MS) {
    if (result || isCancelled()) break;
    await new Promise((resolve) => setTimeout(resolve, delay));
    // Re-check after the sleep — the consumer may have unmounted while this
    // retry was waiting. Without this, an obsolete retry still hits
    // fetchScryfallArt's shared request queue after unmount, consuming rate
    // limit budget and delaying lookups the destination page actually needs.
    if (isCancelled()) break;
    result = await fetchScryfallArt(name);
  }
  return result;
}

/**
 * Fetches Scryfall art for one or more card names, deferred until the returned
 * `ref` scrolls near the viewport. Attach `ref` to the element that should gate
 * the fetch (a list row, a thumbnail wrapper, etc).
 */
export function useScryfallArts(names: Array<string | null | undefined>) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [arts, setArts] = useState<Array<ScryfallCardArt | null>>([]);
  const key = names.join("|");

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let cancelled = false;

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting) return;
        observer.disconnect();
        Promise.all(names.map((name) => fetchWithRetry(name, () => cancelled))).then((results) => {
          if (!cancelled) setArts(results);
        });
      },
      { rootMargin: "200px" }
    );
    observer.observe(el);
    return () => {
      cancelled = true;
      observer.disconnect();
    };
    // `names` is intentionally reduced to `key` so identical name sets don't re-trigger the observer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return { ref, arts };
}
