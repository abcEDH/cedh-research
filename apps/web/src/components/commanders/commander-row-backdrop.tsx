"use client";

import Image from "next/image";
import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";

/**
 * Subtle art backdrop for a leaderboard/table row, keyed off a commander
 * name (a player's active commander, or a played-commander row). Must be
 * rendered inside one of the row's own <td>/<TableCell> children (a <div>
 * can't be a direct child of <tr>), but positions itself against the row
 * itself: pair with `relative` on the parent <tr>/TableRow and leave every
 * cell in between position-static, so this absolutely positioned box's
 * containing block resolves to the row, not the cell it's nested in — it
 * bleeds across the row's full height/width rather than being boxed into
 * one column. `inset-0` (not `contents`) also keeps a real layout box for
 * useScryfallArts' IntersectionObserver to measure.
 */
export function CommanderRowBackdrop({ name }: { name: string | null | undefined }) {
  const frontFace = name ? splitCardName(name)[0] ?? name : null;
  const { ref, arts } = useScryfallArts([frontFace]);
  const artCrop = arts[0]?.artCrop;

  if (!frontFace) return null;

  return (
    <div ref={ref} className="pointer-events-none absolute inset-0">
      {artCrop && (
        <div className="pointer-events-none absolute inset-y-0 right-0 w-1/2 overflow-hidden opacity-20 [mask-image:linear-gradient(to_right,transparent,black_78%)] [-webkit-mask-image:linear-gradient(to_right,transparent,black_78%)]">
          <Image src={artCrop} alt="" fill unoptimized loading="lazy" className="object-cover" />
        </div>
      )}
    </div>
  );
}
