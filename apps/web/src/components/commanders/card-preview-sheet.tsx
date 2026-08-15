"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
} from "@/components/ui/sheet";
import { normalizeDisplayString } from "@/lib/utils";
import { computePValue, formatPValue } from "@/lib/commanders/stats";
import { fetchScryfallArt, type ScryfallCardArt } from "@/lib/scryfall/client";
import type { CardReport, CardPerformance } from "@/lib/commanders/fetchers";

export function CardPreviewSheet({
  report,
  perf,
  onOpenChange,
}: {
  report: CardReport | null;
  perf: CardPerformance | null | undefined;
  onOpenChange: (open: boolean) => void;
}) {
  const [art, setArt] = useState<ScryfallCardArt | null>(null);
  const cardName = report?.card_name ?? null;

  useEffect(() => {
    if (!cardName) return;
    let cancelled = false;
    fetchScryfallArt(cardName).then((result) => {
      if (!cancelled) setArt(result);
    });
    return () => {
      cancelled = true;
    };
  }, [cardName]);

  if (!report) return null;

  const displayName = normalizeDisplayString(report.card_name);
  const inclusionPct = (parseFloat(report.inclusion_rate) * 100).toFixed(1);
  const winDelta = perf ? parseFloat(perf.win_rate_delta) * 100 : null;
  const stdDev = perf ? parseFloat(perf.std_win_rate) * 100 : 0;
  const pValue = perf ? computePValue(winDelta ?? 0, stdDev, perf.deck_count) : null;
  const deltaClass =
    winDelta === null
      ? "text-muted-foreground"
      : winDelta > 0
        ? "text-primary"
        : winDelta < 0
          ? "text-[hsl(var(--knd-amber))]"
          : "text-muted-foreground";

  return (
    <Sheet open onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto rounded-t-2xl border-border/70 p-0">
        <SheetHeader className="sr-only">
          <SheetTitle>{displayName}</SheetTitle>
          <SheetDescription>Card preview and stats for {displayName}</SheetDescription>
        </SheetHeader>
        <div className="flex gap-4 p-4">
          <div className="h-[209px] w-[150px] shrink-0 overflow-hidden rounded-xl border border-border/60 bg-muted shadow-[0_24px_48px_rgba(2,10,26,0.85),0_0_34px_hsl(var(--knd-cyan)/0.2)]">
            {art?.normal && (
              <Image
                src={art.normal}
                alt={displayName}
                width={150}
                height={209}
                className="h-full w-full object-cover"
                unoptimized
              />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold leading-snug text-foreground">{displayName}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {art?.typeLine ?? "Loading from Scryfall…"}
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <StatRow label="Inclusion" value={`${inclusionPct}%`} />
              <StatRow
                label="Win Δ"
                value={winDelta === null ? "—" : `${winDelta > 0 ? "+" : ""}${winDelta.toFixed(1)}%`}
                valueClassName={deltaClass}
              />
              <StatRow label="Decks" value={`${report.deck_count}/${report.total_decks}`} />
              {pValue !== null && <StatRow label="p-value" value={formatPValue(pValue)} />}
            </div>
          </div>
        </div>
        <SheetFooter className="flex-row gap-2 border-t border-border/60 p-4">
          <a
            href={`https://scryfall.com/search?q=${encodeURIComponent(displayName)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-11 flex-1 items-center justify-center rounded-lg border border-border/70 px-3 text-sm font-medium text-foreground hover:bg-accent/40"
          >
            View on Scryfall
          </a>
          <SheetClose className="flex min-h-11 flex-1 items-center justify-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            Close
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function StatRow({
  label,
  value,
  valueClassName = "text-foreground",
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2.5">
      <span className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <span className={`font-mono text-xs font-semibold ${valueClassName}`}>{value}</span>
    </div>
  );
}
