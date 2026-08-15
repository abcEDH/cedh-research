"use client";

import Image from "next/image";
import { normalizeDisplayString } from "@/lib/utils";
import { computePValue, formatPValue } from "@/lib/commanders/stats";
import { useScryfallArts } from "@/hooks/use-scryfall-art";
import type { CardPerformance } from "@/lib/commanders/fetchers";

export function PerformanceCardRow({
  card,
  isNegative = false,
}: {
  card: CardPerformance;
  isNegative?: boolean;
}) {
  const delta = parseFloat(card.win_rate_delta) * 100;
  const stdDev = parseFloat(card.std_win_rate) * 100;
  const winRate = parseFloat(card.avg_win_rate) * 100;
  const inclusionRate = parseFloat(card.inclusion_rate) * 100;
  const pValue = computePValue(delta, stdDev, card.deck_count);
  const { ref, arts } = useScryfallArts([card.card_name]);
  const artCrop = arts[0]?.artCrop;

  const deltaClass = isNegative ? "text-[hsl(var(--knd-amber))]" : "text-primary";
  const pClass =
    pValue < 0.05
      ? "border-primary/40 text-primary"
      : "border-border/60 text-muted-foreground";

  return (
    <div
      ref={ref}
      className="relative flex items-center justify-between overflow-hidden rounded-lg border border-border/60 bg-muted/30 p-2"
    >
      {artCrop && (
        <div className="pointer-events-none absolute inset-y-0 right-0 w-1/2 overflow-hidden opacity-20 [mask-image:linear-gradient(to_right,transparent,black_78%)] [-webkit-mask-image:linear-gradient(to_right,transparent,black_78%)]">
          <Image src={artCrop} alt="" fill unoptimized loading="lazy" className="object-cover" />
        </div>
      )}
      <div className="relative flex-1 min-w-0">
        <a
          href={`https://scryfall.com/search?q=${encodeURIComponent(normalizeDisplayString(card.card_name))}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground hover:text-primary truncate block"
        >
          {normalizeDisplayString(card.card_name)}
        </a>
        <p className="text-xs text-muted-foreground">
          {card.deck_count} decks · {inclusionRate.toFixed(0)}% inclusion
        </p>
      </div>
      <div className="relative text-right ml-4">
        <div className="flex items-center gap-2 justify-end">
          <span className={`font-mono font-semibold ${deltaClass}`}>
            {delta > 0 ? "+" : ""}
            {delta.toFixed(1)}%
          </span>
          <span
            title="Two-sided p-value (normal approximation). Highlighted when p < 0.05."
            className={`rounded-full border px-2 py-0.5 text-[10px] ${pClass}`}
          >
            p={formatPValue(pValue)}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          {winRate.toFixed(1)}% WR · ±{stdDev.toFixed(1)}%
        </p>
      </div>
    </div>
  );
}
