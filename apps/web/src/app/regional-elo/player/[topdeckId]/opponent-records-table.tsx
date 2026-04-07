"use client";

import Link from "next/link";
import { startTransition, useState } from "react";
import type { OpponentRecord } from "./player-stats";

const PAGE_SIZE = 12;

export function OpponentRecordsTable({ records }: { records: OpponentRecord[] }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(Math.ceil(records.length / PAGE_SIZE), 1);
  const start = records.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, records.length);
  const visibleRecords = records.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

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
              <th className="px-2 py-3">Opponent</th>
              <th className="px-2 py-3 text-right">Games</th>
              <th className="px-2 py-3 text-right">W-L-D</th>
            </tr>
          </thead>
          <tbody>
            {visibleRecords.map((record) => (
              <tr key={`${record.opponentTopdeckId ?? record.opponentName}`} className="border-t border-border/60">
                <td className="px-2 py-3">
                  {record.opponentTopdeckId ? (
                    <Link
                      href={`/regional-elo/player/${record.opponentTopdeckId}`}
                      className="font-medium text-foreground hover:text-primary"
                    >
                      {record.opponentName}
                    </Link>
                  ) : (
                    <span className="font-medium text-foreground">{record.opponentName}</span>
                  )}
                </td>
                <td className="px-2 py-3 text-right font-mono text-muted-foreground">{record.games}</td>
                <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                  {record.wins}-{record.losses}-{record.draws}
                </td>
              </tr>
            ))}
            {visibleRecords.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-2 py-6 text-center text-sm text-muted-foreground">
                  No opponent records found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-col gap-3 border-t border-border/60 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div>
          Showing {start}-{end} of {records.length}
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
