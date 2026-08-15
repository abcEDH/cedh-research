"use client";

import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";
import { ArtCropStack } from "./art-crop-stack";

/** Client-side Scryfall art lookup by card/commander name (for rows that only have a name, not a cached scryfall_id). */
export function CommanderArtThumb({
  name,
  size,
}: {
  name: string;
  size: number;
}) {
  const names = splitCardName(name).slice(0, 2);
  const { ref, arts } = useScryfallArts(names);
  const urls = names.map((_, index) => arts[index]?.artCrop ?? null);

  return (
    <div ref={ref} className="inline-flex shrink-0">
      {/* Decorative: every caller renders this beside the same visible name text,
          so a real alt would duplicate it in the enclosing link/button's accessible name. */}
      <ArtCropStack urls={urls} size={size} alt="" />
    </div>
  );
}
