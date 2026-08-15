"use client";

import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";
import type { ScryfallArtByName } from "@/lib/commanders/fetchers";
import { ArtCropStack } from "./art-crop-stack";

function useCommanderArts(name: string, artByName?: ScryfallArtByName) {
  const names = splitCardName(name).slice(0, 2);
  const missingNames = artByName
    ? names.filter((cardName) => !artByName[cardName]?.artCrop)
    : names;
  const { ref, arts } = useScryfallArts(missingNames);
  const artCrops = names.map((cardName) => {
    const cachedArt = artByName?.[cardName]?.artCrop;
    if (cachedArt) return cachedArt;
    const missingIndex = missingNames.indexOf(cardName);
    return missingIndex === -1 ? null : (arts[missingIndex]?.artCrop ?? null);
  });

  return { artCrops, ref };
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
  const { artCrops, ref } = useCommanderArts(name, artByName);

  return (
    <div ref={ref} className="inline-flex shrink-0">
      {/* Decorative: every caller renders this beside the same visible name text,
          so a real alt would duplicate it in the enclosing link/button's accessible name. */}
      <ArtCropStack urls={artCrops} size={size} alt="" />
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
  const { artCrops, ref } = useCommanderArts(name, artByName);

  return (
    <div
      ref={ref}
      aria-hidden
      className={`absolute inset-0 grid ${artCrops.length > 1 ? "grid-cols-2" : "grid-cols-1"}`}
    >
      {artCrops.map((artCrop, index) => (
        <div
          key={index}
          className="bg-[linear-gradient(135deg,oklch(0.28_0.06_258),oklch(0.22_0.05_300))] bg-cover"
          style={
            artCrop
              ? { backgroundImage: `url("${artCrop}")`, backgroundPosition: "50% 32%" }
              : undefined
          }
        />
      ))}
    </div>
  );
}
