"use client";

import Image from "next/image";
import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";

/**
 * Decorative commander art contained by a `relative overflow-hidden` table
 * cell. Do not anchor it to a positioned <tr>: WebKit can resolve that
 * containing block to the surrounding panel and stretch art over other rows.
 * Keep a real layout box so the lazy-loading observer can measure it.
 */
export function CommanderRowBackdrop({ name }: { name: string | null | undefined }) {
  const frontFace = name ? splitCardName(name)[0] ?? name : null;
  const { ref, arts } = useScryfallArts([frontFace]);
  const artCrop = arts[0]?.artCrop;

  if (!frontFace) return null;

  return (
    <div ref={ref} aria-hidden="true" data-testid="commander-row-backdrop" className="pointer-events-none absolute inset-0 overflow-hidden">
      {artCrop && (
        <div className="pointer-events-none absolute inset-y-0 right-0 w-1/2 overflow-hidden opacity-20 [mask-image:linear-gradient(to_right,transparent,black_78%)] [-webkit-mask-image:linear-gradient(to_right,transparent,black_78%)]">
          <Image src={artCrop} alt="" fill unoptimized loading="lazy" className="object-cover" />
        </div>
      )}
    </div>
  );
}
