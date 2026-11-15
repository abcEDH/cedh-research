"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { normalizeDisplayString } from "@/lib/utils";
import type { WinrateMatrixRow, CommanderMetaEv } from "@/lib/schemas/api-contracts";
import type { CommanderLabel } from "@/lib/winrates/fetchers";
import {
  buildRowBundles,
  sortRowBundles,
  classifyWinrateHeat,
  HEAT_BG_CLASS,
  HEAT_LEGEND,
  HEADER_REPEAT_INTERVAL,
  DEFAULT_SORT_KEY,
  formatPercent,
  formatCiRange,
  formatSampleSize,
  type MatrixSortKey,
  type SortDirection,
  type MatrixRowBundle,
} from "@/lib/winrates/stats";

const SORT_OPTIONS: { key: MatrixSortKey; label: string }[] = [
  { key: "matches", label: "Number of Matches" },
  { key: "winrate", label: "Winrate" },
  { key: "ev", label: "EV" },
  { key: "alphabetical", label: "Alphabetical" },
];

function MatrixCell({
  row,
  emptyLabel = "—",
}: {
  row: WinrateMatrixRow | null | undefined;
  emptyLabel?: string;
}) {
  if (!row) {
    return (
      <td className="min-w-[88px] px-2 py-1.5 text-center align-middle text-xs text-muted-foreground">
        {emptyLabel}
      </td>
    );
  }
  const heat = classifyWinrateHeat(row.point_winrate);
  return (
    <td
      className={`min-w-[88px] px-2 py-1.5 text-center align-middle ${HEAT_BG_CLASS[heat]}`}
      title={`${row.wins}W / ${row.losses}L / ${row.draws}D`}
    >
      <div className="text-[10px] leading-tight text-foreground/70">{formatCiRange(row.ci_low, row.ci_high)}</div>
      <div className="text-base leading-tight font-bold text-foreground">{formatPercent(row.point_winrate)}</div>
      <div className="text-[10px] leading-tight text-foreground/70">{formatSampleSize(row.games_played)}</div>
    </td>
  );
}

function EvCell({ ev }: { ev: CommanderMetaEv | null }) {
  if (!ev) {
    return (
      <td className="min-w-[88px] px-2 py-1.5 text-center align-middle text-xs text-muted-foreground">—</td>
    );
  }
  const heat = classifyWinrateHeat(ev.meta_ev);
  return (
    <td
      className={`min-w-[88px] px-2 py-1.5 text-center align-middle ${HEAT_BG_CLASS[heat]}`}
      title="Expected pod winrate weighted by realistic pod compositions."
    >
      <div className="text-[10px] leading-tight text-foreground/70">
        {formatCiRange(ev.meta_ev_ci_low, ev.meta_ev_ci_high)}
      </div>
      <div className="text-base leading-tight font-bold text-foreground">{formatPercent(ev.meta_ev)}</div>
      <div className="text-[10px] leading-tight text-foreground/70">
        {formatPercent(ev.composition_coverage)} coverage
      </div>
    </td>
  );
}

function HeaderRow({ commanderOrder }: { commanderOrder: CommanderLabel[] }) {
  return (
    <tr className="border-border/60 bg-card text-muted-foreground">
      <th className="sticky left-0 z-20 min-w-[160px] bg-card px-2 py-2 text-left text-xs uppercase tracking-[0.15em]">
        Commander
      </th>
      <th className="min-w-[88px] px-2 py-2 text-center text-xs uppercase tracking-[0.15em]">Overall</th>
      <th className="min-w-[88px] px-2 py-2 text-center text-xs uppercase tracking-[0.15em]">EV</th>
      {commanderOrder.map((commander) => (
        <th
          key={commander.id}
          className="min-w-[88px] max-w-[110px] truncate px-2 py-2 text-center text-xs font-medium"
          title={normalizeDisplayString(commander.name)}
        >
          {normalizeDisplayString(commander.name)}
        </th>
      ))}
    </tr>
  );
}

export default function MatchupMatrixTable({
  commanderOrder,
  rows,
  evRows,
}: {
  commanderOrder: CommanderLabel[];
  rows: WinrateMatrixRow[];
  evRows: CommanderMetaEv[];
}) {
  const [sortKey, setSortKey] = useState<MatrixSortKey>(DEFAULT_SORT_KEY);
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const bundles = useMemo(
    () => buildRowBundles(commanderOrder, rows, evRows),
    [commanderOrder, rows, evRows]
  );

  const sortedBundles = useMemo(
    () => sortRowBundles(bundles, sortKey, sortDirection),
    [bundles, sortKey, sortDirection]
  );

  function handleSortChange(nextKey: MatrixSortKey) {
    if (nextKey === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection("desc");
  }

  if (commanderOrder.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No matchup data is available for this date range yet.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted-foreground uppercase tracking-[0.2em]">Sort rows by</span>
        {SORT_OPTIONS.map((option) => (
          <button
            key={option.key}
            type="button"
            onClick={() => handleSortChange(option.key)}
            className={`min-h-11 rounded-full border px-3 py-1 sm:min-h-0 ${
              sortKey === option.key
                ? "border-primary/50 text-foreground"
                : "border-border/60 text-muted-foreground"
            }`}
          >
            {option.label}
            {sortKey === option.key ? (sortDirection === "asc" ? " ▴" : " ▾") : ""}
          </button>
        ))}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="uppercase tracking-[0.2em]">Winrate heat</span>
        {HEAT_LEGEND.map(({ bucket, label }) => (
          <span key={bucket} className="flex items-center gap-1">
            <span className={`inline-block h-3 w-3 rounded-sm ${HEAT_BG_CLASS[bucket]} border border-border/50`} />
            {label}
          </span>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/60">
        <table className="w-full border-collapse text-sm">
          <thead>
            <HeaderRow commanderOrder={commanderOrder} />
          </thead>
          <tbody>
            {sortedBundles.map((bundle, index) => (
              <RowWithRepeatingHeader
                key={bundle.commander.id}
                bundle={bundle}
                index={index}
                commanderOrder={commanderOrder}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RowWithRepeatingHeader({
  bundle,
  index,
  commanderOrder,
}: {
  bundle: MatrixRowBundle;
  index: number;
  commanderOrder: CommanderLabel[];
}) {
  const showRepeatedHeader = index > 0 && index % HEADER_REPEAT_INTERVAL === 0;
  return (
    <>
      {showRepeatedHeader && <HeaderRow commanderOrder={commanderOrder} />}
      <tr className="border-border/60">
        <td className="sticky left-0 z-10 min-w-[160px] bg-background px-2 py-1.5 text-left align-middle">
          <Link
            href={`/commanders/${bundle.commander.id}`}
            className="font-medium text-foreground hover:text-primary"
          >
            {normalizeDisplayString(bundle.commander.name)}
          </Link>
        </td>
        <MatrixCell row={bundle.overall} />
        <EvCell ev={bundle.ev} />
        {commanderOrder.map((opponent) => (
          <MatrixCell key={opponent.id} row={bundle.cellsByOpponent.get(opponent.id) ?? null} />
        ))}
      </tr>
    </>
  );
}
