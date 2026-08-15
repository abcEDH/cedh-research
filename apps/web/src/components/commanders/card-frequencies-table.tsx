"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { normalizeDisplayString } from "@/lib/utils";
import { computePValue, formatPValue } from "@/lib/commanders/stats";
import { TierBadge } from "@/components/commanders/tier-badge";
import { CommanderArtThumb } from "@/components/commanders/commander-art-thumb";
import { CardPreviewSheet } from "@/components/commanders/card-preview-sheet";
import type { CardReport, CardPerformance } from "@/lib/commanders/fetchers";

export function CardFrequenciesTable({
  commanderName,
  cardReport,
  cardPerformanceMap,
}: {
  commanderName: string;
  cardReport: CardReport[];
  cardPerformanceMap: Map<string, CardPerformance>;
}) {
  const [openCardName, setOpenCardName] = useState<string | null>(null);
  const openReport = cardReport.find((card) => card.card_name === openCardName) ?? null;

  return (
    <Card>
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">
          Card Frequencies for {normalizeDisplayString(commanderName)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <TableHead>Card Name</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead className="text-right">Inc.</TableHead>
              <TableHead className="text-right hidden md:table-cell">Global</TableHead>
              <TableHead className="text-right">Win Δ</TableHead>
              <TableHead className="text-right hidden sm:table-cell">Decks</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {cardReport.map((card) => {
              const perf = cardPerformanceMap.get(card.card_name);
              const winRateDelta = perf ? parseFloat(perf.win_rate_delta) * 100 : null;
              return (
                <TableRow
                  key={card.card_name}
                  onClick={() => setOpenCardName(card.card_name)}
                  className="cursor-pointer border-border/60 hover:bg-accent/20"
                >
                  <TableCell className="font-medium">
                    <span className="flex items-center gap-2.5 text-foreground">
                      <CommanderArtThumb name={card.card_name} size={26} />
                      <span className="min-w-0 truncate">{normalizeDisplayString(card.card_name)}</span>
                    </span>
                  </TableCell>
                  <TableCell>
                    <TierBadge tier={card.tier} />
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {(parseFloat(card.inclusion_rate) * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground hidden md:table-cell">
                    {(parseFloat(card.global_rate) * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {winRateDelta !== null && perf ? (
                      <WinDeltaCell delta={winRateDelta} perf={perf} />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground hidden sm:table-cell">
                    {card.deck_count}/{card.total_decks}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        <p className="mt-3 text-xs text-muted-foreground">
          P-values are two-sided (normal approximation). Highlighted when p &lt; 0.05.
        </p>
        <p className="text-muted-foreground text-sm mt-4 text-center">
          Showing all {cardReport.length} cards · {cardPerformanceMap.size} have win rate data (min 3 decks)
        </p>
        {openReport && (
          <CardPreviewSheet
            key={openReport.card_name}
            report={openReport}
            perf={cardPerformanceMap.get(openReport.card_name)}
            onOpenChange={(open) => {
              if (!open) setOpenCardName(null);
            }}
          />
        )}
      </CardContent>
    </Card>
  );
}

function WinDeltaCell({ delta, perf }: { delta: number; perf: CardPerformance }) {
  const stdDev = parseFloat(perf.std_win_rate) * 100;
  const pValue = computePValue(delta, stdDev, perf.deck_count);
  const pClass =
    pValue < 0.05
      ? "border-primary/40 text-primary"
      : "border-border/60 text-muted-foreground";
  const deltaClass =
    delta > 0 ? "text-primary" : delta < 0 ? "text-[hsl(var(--knd-amber))]" : "text-muted-foreground";

  return (
    <span className="inline-flex items-center gap-2">
      <span className={deltaClass}>
        {delta > 0 ? "+" : ""}
        {delta.toFixed(1)}%
      </span>
      <span
        title="Two-sided p-value (normal approximation). Highlighted when p < 0.05."
        className={`rounded-full border px-2 py-0.5 text-[10px] ${pClass}`}
      >
        p={formatPValue(pValue)}
      </span>
    </span>
  );
}
