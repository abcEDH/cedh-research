"use client";

import { startTransition, useState } from "react";
import { normalizeDisplayString } from "@/lib/utils";
import type { PlayerGameLog } from "./player-stats";

const PAGE_SIZE = 12;

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatResult(result: string) {
  return result.charAt(0).toUpperCase() + result.slice(1);
}

export function PlayerGamesTable({ logs }: { logs: PlayerGameLog[] }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(Math.ceil(logs.length / PAGE_SIZE), 1);
  const start = logs.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, logs.length);
  const visibleLogs = logs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function setBoundedPage(nextPage: number) {
    startTransition(() => {
      setPage(Math.min(Math.max(nextPage, 1), totalPages));
    });
  }

  return (
    <>
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
            <tr>
              <th className="px-2 py-3">Date</th>
              <th className="px-2 py-3">Tournament</th>
              <th className="px-2 py-3">Round</th>
              <th className="px-2 py-3">Seat</th>
              <th className="px-2 py-3">Result</th>
              <th className="px-2 py-3">Commander</th>
              <th className="px-2 py-3">Opponents</th>
            </tr>
          </thead>
          <tbody>
            {visibleLogs.map((log) => (
              <tr key={log.gameId} className="border-t border-border/60 align-top">
                <td className="px-2 py-3 text-muted-foreground">{formatDate(log.startDate)}</td>
                <td className="px-2 py-3">
                  <div className="font-medium text-foreground">{log.tournamentName}</div>
                  <div className="text-xs text-muted-foreground">{log.state || "-"}</div>
                </td>
                <td className="px-2 py-3 text-muted-foreground">
                  {log.roundLabel}
                  <div className="text-xs">{log.tableLabel}</div>
                </td>
                <td className="px-2 py-3 text-muted-foreground">Seat {log.seat}</td>
                <td className="px-2 py-3 font-medium text-foreground">{formatResult(log.result)}</td>
                <td className="px-2 py-3 text-muted-foreground">
                  {log.commanderName ? normalizeDisplayString(log.commanderName) : "Unknown commander"}
                </td>
                <td className="px-2 py-3 text-xs text-muted-foreground">
                  <div className="space-y-1">
                    {log.opponents.map((opponent) => (
                      <div key={`${log.gameId}:${opponent.seat}`}>
                        Seat {opponent.seat}: {opponent.playerName}
                        {opponent.commanderName ? ` · ${normalizeDisplayString(opponent.commanderName)}` : ""}
                        {` · ${formatResult(opponent.result)}`}
                      </div>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {visibleLogs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-2 py-6 text-center text-sm text-muted-foreground">
                  No games found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-col gap-3 border-t border-border/60 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div>
          Showing {start}-{end} of {logs.length}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="knd-chip border border-border/70 px-3 py-2 text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
            disabled={page <= 1}
            onClick={() => setBoundedPage(page - 1)}
            type="button"
          >
            Previous
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            className="knd-chip border border-border/70 px-3 py-2 text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
            disabled={page >= totalPages}
            onClick={() => setBoundedPage(page + 1)}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
    </>
  );
}
