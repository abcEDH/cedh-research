"use client";

import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";
import { ArtCropStack } from "./art-crop-stack";
import type { ScryfallArtByName } from "@/lib/commanders/fetchers";

/**
 * Server-cache-first Scryfall art resolution (#321).
 *
 * `artByName` is a map of already-resolved art keyed by *individual*
 * commander/card name -- partner pairs are split the same way
 * `splitCardName()` does -- sourced from the `scryfall_cards` table via
 * `getScryfallArtByNames()` in `@/lib/commanders/fetchers`, itself populated
 * by the `ingest_scryfall_cards.py` backend job from Scryfall's bulk-data
 * dump. Names missing from that map (cache misses -- not yet present in the
 * bulk dump) fall back to the existing live client-side lookup
 * (`useScryfallArts`), exactly as `CommanderArtThumb` does on its own, so a
 * cold cache degrades to today's behavior rather than rendering nothing.
 */
export function CommanderArt({
  name,
  size,
  artByName,
}: {
  name: string;
  size: number;
  artByName?: ScryfallArtByName;
}) {
  const names = splitCardName(name).slice(0, 2);
  const missingNames = names.filter((n) => !artByName?.[n]?.artCrop);
  const { ref, arts: fetchedArts } = useScryfallArts(missingNames);

  const urls = names.map((faceName) => {
    const resolved = artByName?.[faceName]?.artCrop;
    if (resolved) return resolved;
    const missingIndex = missingNames.indexOf(faceName);
    return missingIndex === -1 ? null : (fetchedArts[missingIndex]?.artCrop ?? null);
  });

  return (
    <div ref={ref} className="inline-flex shrink-0">
      {/* Decorative: every caller renders this beside the same visible name text,
          so a real alt would duplicate it in the enclosing link/button's accessible name. */}
      <ArtCropStack urls={urls} size={size} alt="" />
    </div>
  );
}
