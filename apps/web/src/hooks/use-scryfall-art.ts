"use client";

import { useEffect, useRef, useState } from "react";
import { fetchScryfallArt, type ScryfallCardArt } from "@/lib/scryfall/client";

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

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting) return;
        observer.disconnect();
        Promise.all(names.map((name) => (name ? fetchScryfallArt(name) : Promise.resolve(null)))).then(
          setArts
        );
      },
      { rootMargin: "200px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
    // `names` is intentionally reduced to `key` so identical name sets don't re-trigger the observer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return { ref, arts };
}
