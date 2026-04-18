"use client";

import { useState } from "react";

export type FieldShareRow = {
  commander: string;
  fieldShare: number;
  expectedPlayers: number;
};

type FieldShareListProps = {
  rows: FieldShareRow[];
  hasTournamentResults: boolean;
};

const INITIAL_EXPECTED_ROWS = 4;
const SHOW_MORE_INCREMENT = 4;

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function FieldShareList({ rows, hasTournamentResults }: FieldShareListProps) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_EXPECTED_ROWS);
  const visibleRows = rows.slice(0, visibleCount);
  const hasMore = visibleCount < rows.length;

  return (
    <>
      <div className="grid gap-3 md:grid-cols-2">
        {visibleRows.map((row) => (
          <div key={row.commander} className="flex items-center justify-between text-sm">
            <span className="text-foreground">{row.commander}</span>
            <span className="text-primary">
              {formatPercent(row.fieldShare)} ·{" "}
              {hasTournamentResults ? row.expectedPlayers : row.expectedPlayers.toFixed(1)} players
            </span>
          </div>
        ))}
        {!rows.length && (
          <div className="text-sm text-muted-foreground">
            {hasTournamentResults
              ? "No submitted decklists found for the players in this event."
              : "No known commander history for the players in this event."}
          </div>
        )}
      </div>
      {hasMore ? (
        <button
          type="button"
          className="mt-4 rounded-md border border-border/70 px-3 py-2 text-sm text-foreground hover:border-primary/40 hover:text-primary"
          onClick={() => setVisibleCount((current) => Math.min(current + SHOW_MORE_INCREMENT, rows.length))}
        >
          Show more
        </button>
      ) : null}
    </>
  );
}
