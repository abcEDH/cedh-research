"use client";

import Image from "next/image";
import Link from "next/link";
import { normalizeDisplayString } from "@/lib/utils";
import { formatPercent } from "@/lib/commander-stats";
import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { splitCardName } from "@/lib/scryfall/client";
import { ColorBadge } from "@/components/commanders/stat-card";

type CommanderListRowMobileProps = {
  commanderId: string;
  commanderName: string;
  colorIdentity: string[] | null;
  rank: number;
  entries: number;
  winRate: number;
};

/**
 * Mobile-only commanders list row: full-height card art bleeds behind the
 * row (from the tedh.gg mobile card-art design, option 1a) rather than the
 * small icon-sized thumb the desktop table uses. `sm:hidden` — the desktop
 * `<Table>` in `commanders-table.tsx` covers `sm:` and up per this repo's
 * "wide tables" convention (drop to a denser view, don't rebuild it twice).
 */
export function CommanderListRowMobile({
  commanderId,
  commanderName,
  colorIdentity,
  rank,
  entries,
  winRate,
}: CommanderListRowMobileProps) {
  const frontFace = splitCardName(commanderName)[0] ?? commanderName;
  const { ref, arts } = useScryfallArts([frontFace]);
  const artCrop = arts[0]?.artCrop;

  return (
    // A plain block div (not `display: contents`) — IntersectionObserver needs
    // a real layout box to measure, and `contents` collapses this element out
    // of the box tree entirely, so it never intersects and art never loads.
    // As a flex item of the parent's `flex flex-col`, it still stretches to
    // full width via the default `align-items: stretch`, same as the bare
    // <Link> did before this wrapper existed.
    <div ref={ref}>
      <Link
        href={`/commanders/${commanderId}`}
        className="relative flex min-h-[78px] items-center gap-3 overflow-hidden rounded-2xl border border-border/60 bg-card/70 px-3.5 py-3"
      >
        {artCrop && (
          <div className="pointer-events-none absolute inset-y-0 right-0 w-3/4 overflow-hidden opacity-35 [mask-image:linear-gradient(to_right,transparent,black_62%)] [-webkit-mask-image:linear-gradient(to_right,transparent,black_62%)]">
            <Image
              src={artCrop}
              alt=""
              fill
              unoptimized
              loading="lazy"
              className="object-cover object-[center_32%]"
            />
          </div>
        )}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-card/95 via-card/70 to-transparent" />

        <span className="relative z-10 w-6 shrink-0 font-mono text-xs text-muted-foreground">
          #{rank}
        </span>
        <div className="relative z-10 min-w-0 flex-1">
          <p className="truncate text-[13.5px] font-semibold leading-tight text-foreground">
            {normalizeDisplayString(commanderName)}
          </p>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="flex items-center gap-0.5">
              {colorIdentity?.filter(Boolean).map((color) => (
                <ColorBadge key={color} color={color} />
              ))}
            </span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {entries.toLocaleString()} entries
            </span>
          </div>
        </div>
        <span className="relative z-10 shrink-0 font-mono text-sm font-semibold text-primary">
          {formatPercent(winRate)}
        </span>
      </Link>
    </div>
  );
}
