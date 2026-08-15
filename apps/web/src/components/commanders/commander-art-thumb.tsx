"use client";

import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";
import type { ScryfallArtByName } from "@/lib/commanders/fetchers";
import { ArtCropStack } from "./art-crop-stack";

function useCommanderArt(name: string, artByName?: ScryfallArtByName) {
  const cardName = splitCardName(name)[0] ?? name;
  const needsFallback = !artByName || !artByName[cardName]?.artCrop;
  const { ref, arts } = useScryfallArts(needsFallback ? [cardName] : []);
  const artCrop = artByName?.[cardName]?.artCrop ?? arts[0]?.artCrop ?? null;

  return { artCrop, ref };
}

/**
 * Client-side Scryfall art lookup by card/commander name (for rows that only
 * have a name, not a cached scryfall_id). Names present in `artByName` (the
 * server-cached `scryfall_cards` lookup) render immediately with no network
 * request; any name missing from it falls back to a live client-side Scryfall
 * fetch, gated by viewport visibility.
 */
export function CommanderArtThumb({
  name,
  size,
  artByName,
}: {
  name: string;
  size: number;
  artByName?: ScryfallArtByName;
}) {
  const names = splitCardName(name).slice(0, 2);
  const missingNames = artByName
    ? names.filter((n) => !artByName[n]?.artCrop)
    : names;
  const { ref, arts } = useScryfallArts(missingNames);

  const urls = names.map((n) => {
    if (artByName && artByName[n]?.artCrop) return artByName[n].artCrop;
    const missingIndex = missingNames.indexOf(n);
    return missingIndex === -1 ? null : (arts[missingIndex]?.artCrop ?? null);
  });

  return (
    <div ref={ref} className="inline-flex shrink-0">
      {/* Decorative: every caller renders this beside the same visible name text,
          so a real alt would duplicate it in the enclosing link/button's accessible name. */}
      <ArtCropStack urls={urls} size={size} alt="" />
    </div>
  );
}

/** A full-width art crop for commander-ranking cards. */
export function CommanderArtBanner({
  name,
  artByName,
}: {
  name: string;
  artByName?: ScryfallArtByName;
}) {
  const { artCrop, ref } = useCommanderArt(name, artByName);

  return (
    <div
      ref={ref}
      aria-hidden
      className="absolute inset-0 bg-[linear-gradient(135deg,oklch(0.28_0.06_258),oklch(0.22_0.05_300))] bg-cover bg-center"
      style={artCrop ? { backgroundImage: `url("${artCrop}")` } : undefined}
    />
  );
}
