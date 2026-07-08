"use client";

import Link from "next/link";

// Client-facing row shape. Deliberately excludes `rating` (internal Elo) — this component
// runs in the browser, so any field present here is serialized into the page payload. See
// issue #253 / the `toClientLeaderboardRow` helper in page.tsx.
type LeaderboardRow = {
  region_type: string;
  region_key: string;
  player_id: string;
  player_name: string;
  topdeck_id: string | null;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  rank: number;
  topdeck_elo?: number | null;
  topdeck_elo_rank?: number | null;
};

type LatestCommanderRow = {
  topdeck_id: string | null;
  active_commander: string | null;
  active_commander_decklist_url: string | null;
  latest_tournament_name: string | null;
  latest_tournament_date: string | null;
  latest_tournament_topdeck_tid: string | null;
};

function buildTopdeckTournamentUrl(tournamentSlug: string | null | undefined) {
  return tournamentSlug ? `https://topdeck.gg/bracket/${tournamentSlug}` : null;
}

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
  currentPage,
  totalCount,
  pageSize,
  selectedScope,
  selectedCountry,
  selectedRegion,
  playerSearch,
}: {
  latestByPlayer: Record<string, LatestCommanderRow>;
  leaderboard: LeaderboardRow[];
  currentPage: number;
  totalCount: number;
  pageSize: number;
  selectedScope: "global" | "country";
  selectedCountry?: string;
  selectedRegion?: string;
  playerSearch: string;
}) {
  const totalPages = Math.max(Math.ceil(totalCount / pageSize), 1);
  const start = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const end = Math.min(currentPage * pageSize, totalCount);

  function buildPageHref(nextPage: number) {
    const params = new URLSearchParams();
    params.set("scope", selectedScope);
    if (selectedScope === "country" && selectedCountry) {
      params.set("country", selectedCountry);
    }
    if (selectedScope === "country" && selectedRegion) {
      params.set("region", selectedRegion);
    }
    if (playerSearch) {
      params.set("q", playerSearch);
    }
    if (nextPage > 1) {
      params.set("page", String(nextPage));
    }
    return `/regional-elo?${params.toString()}`;
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
              <th className="px-2 py-3 hidden md:table-cell">Active Commander</th>
              <th className="px-2 py-3 hidden sm:table-cell">Games</th>
              <th className="px-2 py-3 hidden md:table-cell">W-L-D</th>
              <th className="px-2 py-3 hidden lg:table-cell">Latest Tournament</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((row, index) => {
              const latestCommander = row.topdeck_id ? latestByPlayer[row.topdeck_id] : undefined;
              const latestTournamentHref = buildTopdeckTournamentUrl(latestCommander?.latest_tournament_topdeck_tid);
              const displayRank =
                row.topdeck_elo_rank ?? (currentPage - 1) * pageSize + index + 1;
              const playerHref =
                row.topdeck_id && row.region_type === "state"
                  ? `/regional-elo/player/${row.topdeck_id}?region=${encodeURIComponent(row.region_key)}`
                  : row.topdeck_id
                    ? `/regional-elo/player/${row.topdeck_id}`
                    : "";
              return (
                <tr key={row.player_id} className="border-t border-border/60">
                  <td className="px-2 py-3 text-muted-foreground">#{displayRank}</td>
                  <td className="px-2 py-3">
                    {row.topdeck_id ? (
                      <div className="space-y-1">
                        <Link
                          className="font-medium text-foreground hover:text-primary truncate max-w-[120px] sm:max-w-none block"
                          href={playerHref}
                        >
                          {row.player_name}
                        </Link>
                      </div>
                    ) : (
                      <div className="font-medium text-foreground truncate max-w-[120px] sm:max-w-none block">{row.player_name}</div>
                    )}
                  </td>
                  <td className="px-2 py-3 font-semibold text-primary">
                    {row.topdeck_elo == null ? "-" : Math.round(row.topdeck_elo)}
                  </td>
                  <td className="px-2 py-3 text-xs text-muted-foreground hidden md:table-cell">
                    <div className="truncate">
                      {latestCommander?.active_commander_decklist_url && latestCommander?.active_commander ? (
                        <a
                          href={latestCommander.active_commander_decklist_url}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-primary"
                        >
                          {latestCommander.active_commander}
                        </a>
                      ) : (
                        latestCommander?.active_commander || "No commander data"
                      )}
                    </div>
                  </td>
                  <td className="px-2 py-3 text-muted-foreground hidden sm:table-cell">{row.games_played}</td>
                  <td className="px-2 py-3 text-muted-foreground hidden md:table-cell">
                    {row.wins}-{row.losses}-{row.draws}
                  </td>
                  <td className="px-2 py-3 text-xs text-muted-foreground hidden lg:table-cell">
                    <div>{formatDate(latestCommander?.latest_tournament_date ?? row.last_game_date)}</div>
                    <div className="truncate text-[11px]">
                      {latestTournamentHref && latestCommander?.latest_tournament_name ? (
                        <a
                          href={latestTournamentHref}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-primary"
                        >
                          {latestCommander.latest_tournament_name}
                        </a>
                      ) : (
                        latestCommander?.latest_tournament_name || "No tournament data"
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {leaderboard.length === 0 && (
              <tr>
                <td colSpan={7} className="py-6 text-center text-sm text-muted-foreground">
                  No TopDeck Elo data available for this view.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-col gap-3 border-t border-border/60 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div>
          Showing {start}-{end} of {totalCount}
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={buildPageHref(currentPage - 1)}
            className="knd-chip border border-border/70 px-3 py-2 text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
            aria-disabled={currentPage <= 1}
            tabIndex={currentPage <= 1 ? -1 : 0}
          >
            Previous
          </Link>
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <Link
            href={buildPageHref(currentPage + 1)}
            className="knd-chip border border-border/70 px-3 py-2 text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
            aria-disabled={currentPage >= totalPages}
            tabIndex={currentPage >= totalPages ? -1 : 0}
          >
            Next
          </Link>
        </div>
      </div>
    </>
  );
}
