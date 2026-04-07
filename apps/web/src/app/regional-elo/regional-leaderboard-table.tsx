"use client";

import Link from "next/link";
import { startTransition, useState } from "react";

const PAGE_SIZE = 50;

type LeaderboardRow = {
  region_type: string;
  region_key: string;
  player_id: string;
  player_name: string;
  topdeck_id: string | null;
  rating: number;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  rank: number;
};

type LatestCommanderRow = {
  topdeck_id: string | null;
  active_commander: string | null;
  latest_commander: string | null;
  latest_commander_date: string | null;
};

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function RegionalLeaderboardTable({
  latestByPlayer,
  leaderboard,
}: {
  latestByPlayer: Record<string, LatestCommanderRow>;
  leaderboard: LeaderboardRow[];
}) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(Math.ceil(leaderboard.length / PAGE_SIZE), 1);
  const start = leaderboard.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, leaderboard.length);
  const visibleRows = leaderboard.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function setBoundedPage(nextPage: number) {
    startTransition(() => {
      setPage(Math.min(Math.max(nextPage, 1), totalPages));
    });
  }

  return (
    <>
      <div className="max-h-[70vh] overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
            <tr>
              <th className="px-2 py-3">Rank</th>
              <th className="px-2 py-3">Player</th>
              <th className="px-2 py-3">Elo</th>
              <th className="px-2 py-3">Games</th>
              <th className="px-2 py-3">W-L-D</th>
              <th className="px-2 py-3">Latest</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const latestCommander = row.topdeck_id ? latestByPlayer[row.topdeck_id] : undefined;
              const playerHref =
                row.topdeck_id && row.region_type === "state"
                  ? `/regional-elo/player/${row.topdeck_id}?region=${encodeURIComponent(row.region_key)}`
                  : row.topdeck_id
                    ? `/regional-elo/player/${row.topdeck_id}`
                    : "";
              return (
                <tr key={row.player_id} className="border-t border-border/60">
                  <td className="px-2 py-3 text-muted-foreground">#{row.rank}</td>
                  <td className="px-2 py-3">
                    {row.topdeck_id ? (
                      <div className="space-y-1">
                        <Link
                          className="font-medium text-foreground hover:text-primary"
                          href={playerHref}
                        >
                          {row.player_name}
                        </Link>
                      </div>
                    ) : (
                      <div className="font-medium text-foreground">{row.player_name}</div>
                    )}
                  </td>
                  <td className="px-2 py-3 font-semibold text-primary">{Math.round(row.rating)}</td>
                  <td className="px-2 py-3 text-muted-foreground">{row.games_played}</td>
                  <td className="px-2 py-3 text-muted-foreground">
                    {row.wins}-{row.losses}-{row.draws}
                  </td>
                  <td className="px-2 py-3 text-xs text-muted-foreground">
                    <div>{formatDate(row.last_game_date)}</div>
                    <div className="truncate text-[11px]">
                      {latestCommander?.active_commander || latestCommander?.latest_commander || "No commander data"}
                    </div>
                  </td>
                </tr>
              );
            })}
            {visibleRows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-sm text-muted-foreground">
                  No regional Elo data yet. Run the regional Elo job to populate this leaderboard.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-col gap-3 border-t border-border/60 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div>
          Showing {start}-{end} of {leaderboard.length}
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
