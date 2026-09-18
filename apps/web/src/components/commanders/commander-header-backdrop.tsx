"use client";

import Image from "next/image";
import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";

/**
 * Full-bleed faded backdrop for the commander detail header. Resolves art by
 * name via the live Scryfall lookup (same mechanism as `CommanderArtThumb`)
 * rather than synthesizing a CDN URL from a scryfall_id — Scryfall's actual
 * object paths include face/shard segments a bare `{id}.jpg` doesn't match.
 */
export function CommanderHeaderBackdrop({ name }: { name: string }) {
  const frontFace = splitCardName(name)[0] ?? name;
  const { ref, arts } = useScryfallArts([frontFace]);
  const artCrop = arts[0]?.artCrop;

  return (
    <div ref={ref} className="absolute inset-0">
      {artCrop && (
        <Image
          src={artCrop}
          alt=""
          fill
          className="object-cover opacity-50 [mask-image:linear-gradient(to_bottom,black_10%,transparent)] [-webkit-mask-image:linear-gradient(to_bottom,black_10%,transparent)]"
          loading="lazy"
          unoptimized
        />
      )}
    </div>
  );
}
