"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { normalizeDisplayString } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type CommanderMatchup = {
  opponent_commander_id: string;
  opponent_commander_name: string;
  games_played: number;
  wins: number;
  losses: number;
  draws: number;
  win_rate: number | string;
  loss_rate: number | string;
  draw_rate: number | string;
  expected_win_rate: number | string;
  win_rate_vs_expected: number | string;
  is_statistically_significant: boolean;
  confidence_level: string;
};

type SortKey =
  | "opponent"
  | "games"
  | "metaShare"
  | "winRate"
  | "drawRate"
  | "lossRate"
  | "points"
  | "resiliency"
  | "vsExpected";

type SortDirection = "asc" | "desc";

function toNumber(val: number | string | null | undefined): number {
  if (val === null || val === undefined) return 0;
  return typeof val === "string" ? parseFloat(val) : val;
}

function pointsPerGame(matchup: CommanderMatchup): number {
  const games = matchup.games_played;
  if (!games) return 0;
  return (matchup.wins * 5 + matchup.draws) / games;
}

function resiliencyRate(matchup: CommanderMatchup): number {
  const games = matchup.games_played;
  if (!games) return 0;
  return (matchup.wins + matchup.draws) / games;
}

function compareValues(a: CommanderMatchup, b: CommanderMatchup, key: SortKey) {
  switch (key) {
    case "opponent":
      return a.opponent_commander_name.localeCompare(b.opponent_commander_name);
    case "games":
      return a.games_played - b.games_played;
    case "metaShare":
      return a.games_played - b.games_played;
    case "winRate":
      return toNumber(a.win_rate) - toNumber(b.win_rate);
    case "drawRate":
      return toNumber(a.draw_rate) - toNumber(b.draw_rate);
    case "lossRate":
      return toNumber(a.loss_rate) - toNumber(b.loss_rate);
    case "points":
      return pointsPerGame(a) - pointsPerGame(b);
    case "resiliency":
      return resiliencyRate(a) - resiliencyRate(b);
    case "vsExpected":
      return toNumber(a.win_rate_vs_expected) - toNumber(b.win_rate_vs_expected);
    default:
      return 0;
  }
}

function SortButton({
  label,
  active,
  direction,
  onClick,
  align = "left",
}: {
  label: string;
  active: boolean;
  direction: SortDirection;
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
        {active ? (direction === "asc" ? "▴" : "▾") : "▾"}
      </span>
    </button>
  );
}

export default function CommanderMatchupsTable({
  matchups,
}: {
  matchups: CommanderMatchup[];
}) {
  const [sortKey, setSortKey] = useState<SortKey>("games");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const totalGames = useMemo(
    () => matchups.reduce((sum, matchup) => sum + matchup.games_played, 0),
    [matchups]
  );
  const metaWeightedWinRate = useMemo(() => {
    if (!totalGames) return 0;
    const weighted = matchups.reduce((sum, matchup) => {
      return sum + matchup.games_played * toNumber(matchup.win_rate);
    }, 0);
    return weighted / totalGames;
  }, [matchups, totalGames]);
  const metaWeightedDrawRate = useMemo(() => {
    if (!totalGames) return 0;
    const weighted = matchups.reduce((sum, matchup) => {
      return sum + matchup.games_played * toNumber(matchup.draw_rate);
    }, 0);
    return weighted / totalGames;
  }, [matchups, totalGames]);
  const metaWeightedResiliency = useMemo(() => {
    if (!totalGames) return 0;
    const weighted = matchups.reduce((sum, matchup) => {
      const resiliency = (matchup.wins + matchup.draws) / matchup.games_played;
      return sum + matchup.games_played * resiliency;
    }, 0);
    return weighted / totalGames;
  }, [matchups, totalGames]);

  const sortedMatchups = useMemo(() => {
    const sorted = [...matchups].sort((a, b) => compareValues(a, b, sortKey));
    return sortDirection === "asc" ? sorted : sorted.reverse();
  }, [matchups, sortDirection, sortKey]);

  function handleSort(nextKey: SortKey) {
    if (nextKey === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection("desc");
  }

  return (
    <Card>
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">Commander Matchups</CardTitle>
        <p className="text-sm text-muted-foreground">
          All matchups, sortable by performance and sample size. Default order is most matches played.
        </p>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted-foreground uppercase tracking-[0.2em]">Quick sort</span>
          <button
            type="button"
            onClick={() => handleSort("games")}
            className={`rounded-full border px-3 py-1 ${
              sortKey === "games" ? "border-primary/50 text-foreground" : "border-border/60 text-muted-foreground"
            }`}
          >
            Matches
          </button>
          <button
            type="button"
            onClick={() => handleSort("winRate")}
            className={`rounded-full border px-3 py-1 ${
              sortKey === "winRate" ? "border-primary/50 text-foreground" : "border-border/60 text-muted-foreground"
            }`}
          >
            Win %
          </button>
          <button
            type="button"
            onClick={() => handleSort("drawRate")}
            className={`rounded-full border px-3 py-1 ${
              sortKey === "drawRate" ? "border-primary/50 text-foreground" : "border-border/60 text-muted-foreground"
            }`}
          >
            Draw %
          </button>
          <button
            type="button"
            onClick={() => handleSort("resiliency")}
            className={`rounded-full border px-3 py-1 ${
              sortKey === "resiliency" ? "border-primary/50 text-foreground" : "border-border/60 text-muted-foreground"
            }`}
          >
            Win+Draw %
          </button>
        </div>
        <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Meta-Weighted Win</p>
            <p className="text-xl font-semibold text-foreground">
              {(metaWeightedWinRate * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-muted-foreground">Weighted by matchup frequency.</p>
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Meta-Weighted Draw</p>
            <p className="text-xl font-semibold text-foreground">
              {(metaWeightedDrawRate * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-muted-foreground">Weighted by matchup frequency.</p>
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Meta-Weighted Win + Draw</p>
            <p className="text-xl font-semibold text-foreground">
              {(metaWeightedResiliency * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-muted-foreground">Win + draw rate weighted by matchup frequency.</p>
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Total Matchups</p>
            <p className="text-xl font-semibold text-foreground">{totalGames.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">Across all opponents.</p>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 text-muted-foreground">
              <TableHead className="py-3">Rank</TableHead>
              <TableHead className="py-3">
                <SortButton
                  label="Opponent"
                  active={sortKey === "opponent"}
                  direction={sortDirection}
                  onClick={() => handleSort("opponent")}
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Matches"
                  active={sortKey === "games"}
                  direction={sortDirection}
                  onClick={() => handleSort("games")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Meta Share"
                  active={sortKey === "metaShare"}
                  direction={sortDirection}
                  onClick={() => handleSort("metaShare")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Win %"
                  active={sortKey === "winRate"}
                  direction={sortDirection}
                  onClick={() => handleSort("winRate")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Draw %"
                  active={sortKey === "drawRate"}
                  direction={sortDirection}
                  onClick={() => handleSort("drawRate")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Pts/Game"
                  active={sortKey === "points"}
                  direction={sortDirection}
                  onClick={() => handleSort("points")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Win+Draw %"
                  active={sortKey === "resiliency"}
                  direction={sortDirection}
                  onClick={() => handleSort("resiliency")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Δ vs Exp"
                  active={sortKey === "vsExpected"}
                  direction={sortDirection}
                  onClick={() => handleSort("vsExpected")}
                  align="right"
                />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedMatchups.map((matchup, index) => {
              const winRate = toNumber(matchup.win_rate) * 100;
              const drawRate = toNumber(matchup.draw_rate) * 100;
              const vsExpected = toNumber(matchup.win_rate_vs_expected) * 100;
              const points = pointsPerGame(matchup);
              const resiliency = resiliencyRate(matchup) * 100;
              const metaShare = totalGames ? (matchup.games_played / totalGames) * 100 : 0;

              return (
                <TableRow key={matchup.opponent_commander_id} className="border-border/60">
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    #{index + 1}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/commanders/${matchup.opponent_commander_id}`}
                      className="text-foreground hover:text-primary"
                    >
                      <span className="font-medium">
                        {normalizeDisplayString(matchup.opponent_commander_name)}
                      </span>
                    </Link>
                    <p className="text-xs text-muted-foreground">
                      {matchup.games_played} games · {matchup.wins}W/{matchup.losses}L/{matchup.draws}D
                      {matchup.is_statistically_significant && (
                        <span className="ml-1 text-[hsl(var(--knd-amber))]">★</span>
                      )}
                    </p>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {matchup.games_played.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {metaShare.toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {winRate.toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {drawRate.toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {points.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {resiliency.toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {vsExpected > 0 ? "+" : ""}{vsExpected.toFixed(1)}%
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        <p className="mt-3 text-xs text-muted-foreground">
          Points per game uses 5 points for a win, 1 point for a draw, and 0 for a loss. Resiliency is win + draw rate.
        </p>
        <p className="text-xs text-muted-foreground">
          ★ indicates matchup data meeting the statistical threshold.
        </p>
      </CardContent>
    </Card>
  );
}
