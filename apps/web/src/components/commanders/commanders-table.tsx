"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { normalizeDisplayString } from "@/lib/utils";
import { formatPercent } from "@/lib/commander-stats";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type CommanderStat = {
  commander_id: string;
  commander_name: string;
  archetype: string | null;
  color_identity: string[] | null;
  total_entries: number;
  tournaments_played: number;
  total_wins: number;
  total_losses: number;
  total_draws: number;
  avg_win_rate: string;
  top_16_count: number;
  conversion_rate_top_16: string;
  top_cut_count: number;
  conversion_rate_top_cut: string;
};

type SortKey =
  | "commander"
  | "entries"
  | "tournaments"
  | "winRate"
  | "pointsPerGame"
  | "top16"
  | "topCut";

type SortDirection = "asc" | "desc";

function getArchetypeIcon(archetype: string | null) {
  if (!archetype) return null;
  const normalized = archetype.toLowerCase();

  if (normalized.includes("turbo")) return "/assets/icons/archetype-turbo.svg";
  if (normalized.includes("mid")) return "/assets/icons/archetype-midrange.svg";
  if (normalized.includes("stax")) return "/assets/icons/archetype-stax.svg";
  if (normalized.includes("control")) return "/assets/icons/archetype-control.svg";
  return null;
}

function safeNumber(value: string): number {
  // parseFloat(null) is NaN, which sorts unpredictably. Treat missing values
  // as -Infinity so they consistently land at the bottom of asc/top of desc.
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : -Infinity;
}

function compareValues(a: CommanderStat, b: CommanderStat, key: SortKey) {
  switch (key) {
    case "commander":
      return a.commander_name.localeCompare(b.commander_name);
    case "entries":
      return a.total_entries - b.total_entries;
    case "tournaments":
      return a.tournaments_played - b.tournaments_played;
    case "winRate":
      return safeNumber(a.avg_win_rate) - safeNumber(b.avg_win_rate);
    case "pointsPerGame": {
      const aGames = a.total_wins + a.total_losses + a.total_draws;
      const bGames = b.total_wins + b.total_losses + b.total_draws;
      const aPpg = aGames ? (a.total_wins * 5 + a.total_draws) / aGames : 0;
      const bPpg = bGames ? (b.total_wins * 5 + b.total_draws) / bGames : 0;
      return aPpg - bPpg;
    }
    case "top16":
      return (
        safeNumber(a.conversion_rate_top_16) -
        safeNumber(b.conversion_rate_top_16)
      );
    case "topCut":
      return (
        safeNumber(a.conversion_rate_top_cut) -
        safeNumber(b.conversion_rate_top_cut)
      );
    default:
      return 0;
  }
}

function SortButton({
  label,
  active,
  onClick,
  align = "left",
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  align?: "left" | "right";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 text-xs uppercase tracking-[0.2em] ${
        align === "right" ? "justify-end" : "justify-start"
      }`}
    >
      <span>{label}</span>
      <span className={`text-[10px] ${active ? "text-foreground" : "text-muted-foreground"}`}>
        ▾
      </span>
    </button>
  );
}

export default function CommandersTable({
  commanders,
}: {
  commanders: CommanderStat[];
}) {
  const [sortKey, setSortKey] = useState<SortKey>("entries");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const baseRank = useMemo(() => {
    const map = new Map<string, number>();
    commanders.forEach((commander, index) => {
      map.set(commander.commander_id, index + 1);
    });
    return map;
  }, [commanders]);

  const sortedCommanders = useMemo(() => {
    const sorted = [...commanders].sort((a, b) =>
      compareValues(a, b, sortKey)
    );
    return sortDirection === "asc" ? sorted : sorted.reverse();
  }, [commanders, sortDirection, sortKey]);

  function handleSort(nextKey: SortKey) {
    setSortDirection("desc");
    setSortKey(nextKey);
  }

  return (
    <Card data-testid="all-commanders-card">
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">All Commanders</CardTitle>
      </CardHeader>
      <CardContent>
        <Table data-testid="all-commanders-table">
          <TableHeader>
            <TableRow className="border-border/60 text-muted-foreground">
              <TableHead className="py-3">Rank</TableHead>
              <TableHead className="py-3">
                <SortButton
                  label="Commander"
                  active={sortKey === "commander"}
                  onClick={() => handleSort("commander")}
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Ent."
                  active={sortKey === "entries"}
                  onClick={() => handleSort("entries")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right hidden sm:table-cell">
                <SortButton
                  label="Tourn."
                  active={sortKey === "tournaments"}
                  onClick={() => handleSort("tournaments")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="WR"
                  active={sortKey === "winRate"}
                  onClick={() => handleSort("winRate")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right hidden md:table-cell">
                <SortButton
                  label="PPG"
                  active={sortKey === "pointsPerGame"}
                  onClick={() => handleSort("pointsPerGame")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right hidden lg:table-cell">
                <SortButton
                  label="Top 16"
                  active={sortKey === "top16"}
                  onClick={() => handleSort("top16")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Cut"
                  active={sortKey === "topCut"}
                  onClick={() => handleSort("topCut")}
                  align="right"
                />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedCommanders.map((commander, index) => {
              const archetypeIcon = getArchetypeIcon(commander.archetype);
              const winRate = parseFloat(commander.avg_win_rate);
              const totalGames = commander.total_wins + commander.total_losses + commander.total_draws;
              const pointsPerGame = totalGames ? (commander.total_wins * 5 + commander.total_draws) / totalGames : 0;
              const rank = baseRank.get(commander.commander_id) ?? index + 1;

              return (
                <TableRow key={commander.commander_id} className="border-border/60">
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    #{rank}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/commanders/${commander.commander_id}`}
                      className="text-foreground hover:text-primary"
                    >
                      <span className="font-medium line-clamp-1 max-w-[120px] sm:max-w-none sm:line-clamp-none">
                        {normalizeDisplayString(commander.commander_name)}
                      </span>
                      {commander.archetype && (
                        <span className="ml-2 hidden sm:inline-flex items-center gap-2 text-sm text-muted-foreground">
                          {archetypeIcon && (
                            <Image src={archetypeIcon} alt="" width={16} height={16} />
                          )}
                          {normalizeDisplayString(commander.archetype)}
                        </span>
                      )}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right font-mono text-foreground">
                    {commander.total_entries.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground hidden sm:table-cell">
                    {commander.tournaments_played}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    <span className="text-muted-foreground">
                      {formatPercent(winRate)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground hidden md:table-cell">
                    {pointsPerGame.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground hidden lg:table-cell">
                    {formatPercent(parseFloat(commander.conversion_rate_top_16))}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatPercent(parseFloat(commander.conversion_rate_top_cut))}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
