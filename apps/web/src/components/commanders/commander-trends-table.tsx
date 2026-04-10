"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { normalizeDisplayString } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type CommanderPeriodSnapshot = {
  weekStart: string | null;
  weekEntries: number | null;
  weekWinRate: number | null;
  weekPointsPerGame: number | null;
  weekPlayers: number | null;
  monthKey: string | null;
  monthEntries: number | null;
  monthWinRate: number | null;
  monthPointsPerGame: number | null;
  monthPlayers: number | null;
};

type CommanderStat = {
  commander_id: string;
  commander_name: string;
  total_entries: number;
  avg_win_rate: string;
};

function formatPercent(value: number | null) {
  if (value === null || Number.isNaN(value)) return "—";
  return `${value.toFixed(1)}%`;
}

function formatPoints(value: number | null) {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

function formatDateLabel(value: string | null) {
  if (!value) return "—";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [, month, day] = value.split("-").map(Number);
    if (!month || !day) return value;
    return `${month}/${day}`;
  }
  return value;
}

type SortKey =
  | "commander"
  | "entries"
  | "winRate"
  | "weekEntries"
  | "weekWin"
  | "weekPts"
  | "monthEntries"
  | "monthWin"
  | "monthPts";

type SortDirection = "asc" | "desc";

function compareValues(
  a: CommanderStat,
  b: CommanderStat,
  snapshots: Record<string, CommanderPeriodSnapshot>,
  key: SortKey
) {
  const aSnap = snapshots[a.commander_id];
  const bSnap = snapshots[b.commander_id];
  switch (key) {
    case "commander":
      return a.commander_name.localeCompare(b.commander_name);
    case "entries":
      return a.total_entries - b.total_entries;
    case "winRate":
      return parseFloat(a.avg_win_rate) - parseFloat(b.avg_win_rate);
    case "weekEntries":
      return (aSnap?.weekEntries ?? 0) - (bSnap?.weekEntries ?? 0);
    case "weekWin":
      return (aSnap?.weekWinRate ?? 0) - (bSnap?.weekWinRate ?? 0);
    case "weekPts":
      return (aSnap?.weekPointsPerGame ?? 0) - (bSnap?.weekPointsPerGame ?? 0);
    case "monthEntries":
      return (aSnap?.monthEntries ?? 0) - (bSnap?.monthEntries ?? 0);
    case "monthWin":
      return (aSnap?.monthWinRate ?? 0) - (bSnap?.monthWinRate ?? 0);
    case "monthPts":
      return (aSnap?.monthPointsPerGame ?? 0) - (bSnap?.monthPointsPerGame ?? 0);
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

export default function CommanderTrendsTable({
  commanders,
  snapshotsByCommanderId,
  weeklyEntriesByCommanderId,
  limit = 30,
  title = "Commander Performance Trends",
}: {
  commanders: CommanderStat[];
  snapshotsByCommanderId: Record<string, CommanderPeriodSnapshot>;
  weeklyEntriesByCommanderId?: Record<string, number[]>;
  limit?: number;
  title?: string;
}) {
  const [viewMode, setViewMode] = useState<"monthly" | "weekly">("monthly");
  const [sortKey, setSortKey] = useState<SortKey>("entries");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const sorted = useMemo(() => {
    const items = [...commanders].sort((a, b) =>
      compareValues(a, b, snapshotsByCommanderId, sortKey)
    );
    const ordered = sortDirection === "asc" ? items : items.reverse();
    return ordered.slice(0, limit);
  }, [commanders, limit, snapshotsByCommanderId, sortDirection, sortKey]);

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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-lg">{title}</CardTitle>
          <div className="flex gap-2 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("monthly")}
              className={`rounded-full border px-3 py-1 ${
                viewMode === "monthly"
                  ? "border-primary/50 text-foreground"
                  : "border-border/60 text-muted-foreground"
              }`}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setViewMode("weekly")}
              className={`rounded-full border px-3 py-1 ${
                viewMode === "weekly"
                  ? "border-primary/50 text-foreground"
                  : "border-border/60 text-muted-foreground"
              }`}
            >
              Weekly
            </button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Sorted by total entries. Shows latest monthly or weekly snapshot.
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 text-muted-foreground">
              <TableHead className="py-3">Rank</TableHead>
              <TableHead className="py-3">Commander</TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Entries"
                  active={sortKey === "entries"}
                  direction={sortDirection}
                  onClick={() => handleSort("entries")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Win Rate"
                  active={sortKey === "winRate"}
                  direction={sortDirection}
                  onClick={() => handleSort("winRate")}
                  align="right"
                />
              </TableHead>
              {viewMode === "weekly" ? (
                <>
                  <TableHead className="py-3 text-right">Week</TableHead>
                  <TableHead className="py-3 text-right">
                    <SortButton
                      label="Week Entries"
                      active={sortKey === "weekEntries"}
                      direction={sortDirection}
                      onClick={() => handleSort("weekEntries")}
                      align="right"
                    />
                  </TableHead>
                  <TableHead className="py-3 text-right">
                    <SortButton
                      label="Week Win"
                      active={sortKey === "weekWin"}
                      direction={sortDirection}
                      onClick={() => handleSort("weekWin")}
                      align="right"
                    />
                  </TableHead>
                  <TableHead className="py-3 text-right">
                    <SortButton
                      label="Week Pts"
                      active={sortKey === "weekPts"}
                      direction={sortDirection}
                      onClick={() => handleSort("weekPts")}
                      align="right"
                    />
                  </TableHead>
                </>
              ) : (
                <>
                  <TableHead className="py-3 text-right">Month</TableHead>
                  <TableHead className="py-3 text-right">
                    <SortButton
                      label="Month Entries"
                      active={sortKey === "monthEntries"}
                      direction={sortDirection}
                      onClick={() => handleSort("monthEntries")}
                      align="right"
                    />
                  </TableHead>
                  <TableHead className="py-3 text-right">
                    <SortButton
                      label="Month Win"
                      active={sortKey === "monthWin"}
                      direction={sortDirection}
                      onClick={() => handleSort("monthWin")}
                      align="right"
                    />
                  </TableHead>
                  <TableHead className="py-3 text-right">
                    <SortButton
                      label="Month Pts"
                      active={sortKey === "monthPts"}
                      direction={sortDirection}
                      onClick={() => handleSort("monthPts")}
                      align="right"
                    />
                  </TableHead>
                </>
              )}
              <TableHead className="py-3 text-right">Trend</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((commander, index) => {
              const snapshot = snapshotsByCommanderId[commander.commander_id];
              const winRate = parseFloat(commander.avg_win_rate) * 100;
              const weeklyEntries = weeklyEntriesByCommanderId?.[commander.commander_id] ?? [];

              return (
                <TableRow key={commander.commander_id} className="border-border/60">
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    #{index + 1}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/commanders/${commander.commander_id}`}
                      className="text-foreground hover:text-primary"
                    >
                      <span className="font-medium">
                        {normalizeDisplayString(commander.commander_name)}
                      </span>
                    </Link>
                  </TableCell>
                  <TableCell className="text-right font-mono text-foreground">
                    {commander.total_entries.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {winRate.toFixed(1)}%
                  </TableCell>
                  {viewMode === "weekly" ? (
                    <>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {formatDateLabel(snapshot?.weekStart ?? null)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {snapshot?.weekEntries ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {formatPercent(snapshot?.weekWinRate ?? null)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {formatPoints(snapshot?.weekPointsPerGame ?? null)}
                      </TableCell>
                    </>
                  ) : (
                    <>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {snapshot?.monthKey ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {snapshot?.monthEntries ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {formatPercent(snapshot?.monthWinRate ?? null)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {formatPoints(snapshot?.monthPointsPerGame ?? null)}
                      </TableCell>
                    </>
                  )}
                  <TableCell className="text-right">
                    <Sparkline values={weeklyEntries} />
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

function Sparkline({ values }: { values: number[] }) {
  if (!values || values.length < 2) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  const width = 80;
  const height = 24;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = width / (values.length - 1);
  const points = values
    .map((value, index) => {
      const x = index * step;
      const y = height - ((value - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="flex items-center justify-end gap-2">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="inline-block"
        aria-hidden="true"
      >
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          points={points}
          className="text-muted-foreground"
        />
      </svg>
      <span className="text-[10px] text-muted-foreground">
        {values[0]}→{values[values.length - 1]}
      </span>
    </div>
  );
}
