"use client";

import { startTransition, useState } from "react";
import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

const PAGE_SIZE = 25;

type SortDirection = "asc" | "desc";
type SortKey =
  | "standing"
  | "player"
  | "elo"
  | "homeRegion"
  | "mostLikely"
  | "alternatives"
  | "record";

type CommanderPrediction = {
  commander: string;
  entries: number;
  latestDecklistUrl: string | null;
  latestTopdeckDecklistUrl: string | null;
  predictionShare: number;
};

type PlayerCommanderProfile = {
  topdeckId: string;
  commanders: CommanderPrediction[];
};

type TournamentStanding = {
  name: string;
  id: string;
  username?: string | null;
  standing: number;
  points: number;
  winRate: number;
};

type EloAttendee = {
  topdeck_id: string | null;
  player_name: string;
  rating: number;
  region_key: string;
  standing?: TournamentStanding;
  profile?: PlayerCommanderProfile;
};

type AttendeeRow = {
  standing: TournamentStanding;
  profile?: PlayerCommanderProfile;
  rating: number | null;
  regionKey: string | null;
};

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function normalizeSearch(value: string) {
  return value.trim().toLowerCase();
}

function includesSearch(value: string | number | null | undefined, query: string) {
  return String(value ?? "").toLowerCase().includes(query);
}

function compareNullableNumber(a: number | null, b: number | null, direction: SortDirection) {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return direction === "asc" ? a - b : b - a;
}

function compareText(a: string | null | undefined, b: string | null | undefined, direction: SortDirection) {
  const result = (a ?? "").localeCompare(b ?? "");
  return direction === "asc" ? result : -result;
}

function defaultDirectionForSort(key: SortKey): SortDirection {
  return key === "elo" || key === "record" ? "desc" : "asc";
}

function sortRows(rows: AttendeeRow[], key: SortKey, direction: SortDirection) {
  return [...rows].sort((a, b) => {
    if (key === "standing") {
      return direction === "asc"
        ? a.standing.standing - b.standing.standing
        : b.standing.standing - a.standing.standing;
    }
    if (key === "player") {
      return compareText(a.standing.name, b.standing.name, direction);
    }
    if (key === "elo") {
      return compareNullableNumber(a.rating, b.rating, direction);
    }
    if (key === "homeRegion") {
      return compareText(a.regionKey, b.regionKey, direction);
    }
    if (key === "mostLikely") {
      return compareText(a.profile?.commanders[0]?.commander, b.profile?.commanders[0]?.commander, direction);
    }
    if (key === "alternatives") {
      const aAlternatives = a.profile?.commanders.slice(1, 3).map((commander) => commander.commander).join(" ") ?? "";
      const bAlternatives = b.profile?.commanders.slice(1, 3).map((commander) => commander.commander).join(" ") ?? "";
      return compareText(aAlternatives, bAlternatives, direction);
    }

    const pointSort = direction === "asc"
      ? a.standing.points - b.standing.points
      : b.standing.points - a.standing.points;
    if (pointSort !== 0) return pointSort;
    return direction === "asc"
      ? a.standing.winRate - b.standing.winRate
      : b.standing.winRate - a.standing.winRate;
  });
}

function PaginationControls({
  currentPage,
  totalItems,
  onPageChange,
}: {
  currentPage: number;
  totalItems: number;
  onPageChange: (page: number) => void;
}) {
  const totalPages = Math.max(Math.ceil(totalItems / PAGE_SIZE), 1);
  const start = totalItems === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
  const end = Math.min(currentPage * PAGE_SIZE, totalItems);

  function setPage(page: number) {
    startTransition(() => {
      onPageChange(Math.min(Math.max(page, 1), totalPages));
    });
  }

  return (
    <div className="mt-4 flex flex-col gap-3 border-t border-border/60 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
      <div>
        Showing {start}-{end} of {totalItems}
      </div>
      <div className="flex items-center gap-2">
        <button
          className="knd-chip border border-border/70 px-3 py-2 text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
          disabled={currentPage <= 1}
          onClick={() => setPage(currentPage - 1)}
          type="button"
        >
          Previous
        </button>
        <span>
          Page {currentPage} of {totalPages}
        </span>
        <button
          className="knd-chip border border-border/70 px-3 py-2 text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
          disabled={currentPage >= totalPages}
          onClick={() => setPage(currentPage + 1)}
          type="button"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function SortHeader({
  children,
  column,
  direction,
  sortKey,
  onSort,
}: {
  children: ReactNode;
  column: SortKey;
  direction: SortDirection;
  sortKey: SortKey;
  onSort: (column: SortKey) => void;
}) {
  const isActive = sortKey === column;
  return (
    <th className="px-2 py-3">
      <button
        className={`text-left uppercase tracking-[0.3em] transition hover:text-foreground ${
          isActive ? "text-foreground" : ""
        }`}
        onClick={() => onSort(column)}
        type="button"
      >
        {children}
        {isActive && <span className="ml-1 text-[10px]">{direction === "asc" ? "^" : "v"}</span>}
      </button>
    </th>
  );
}

export function TournamentAnalysisTables({
  eloAttendees,
  profiles,
  standings,
}: {
  eloAttendees: EloAttendee[];
  profiles: PlayerCommanderProfile[];
  standings: TournamentStanding[];
}) {
  const hasScoredPlayers = standings.some((standing) => standing.points > 0);
  const defaultSortKey: SortKey = hasScoredPlayers ? "standing" : "elo";
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>(defaultSortKey);
  const [sortDirection, setSortDirection] = useState<SortDirection>(
    defaultDirectionForSort(defaultSortKey)
  );
  const profileByPlayer = new Map(profiles.map((profile) => [profile.topdeckId, profile]));
  const eloByPlayer = new Map(
    eloAttendees
      .filter((attendee) => attendee.topdeck_id)
      .map((attendee) => [attendee.topdeck_id as string, attendee])
  );
  const query = normalizeSearch(search);
  const rows = standings.map((standing) => {
    const elo = eloByPlayer.get(standing.id);
    return {
      standing,
      profile: profileByPlayer.get(standing.id),
      rating: elo?.rating ?? null,
      regionKey: elo?.region_key ?? null,
    };
  });
  const filteredRows = query
    ? rows.filter((row) => {
        const commanders = row.profile?.commanders.map((commander) => commander.commander).join(" ");
        return (
          includesSearch(row.standing.standing, query) ||
          includesSearch(row.standing.name, query) ||
          includesSearch(row.standing.username, query) ||
          includesSearch(row.standing.id, query) ||
          includesSearch(row.rating, query) ||
          includesSearch(row.regionKey, query) ||
          includesSearch(row.standing.points, query) ||
          includesSearch(Math.round((row.standing.winRate || 0) * 100), query) ||
          includesSearch(commanders, query)
        );
      })
    : rows;
  const sortedRows = sortRows(filteredRows, sortKey, sortDirection);
  const visibleRows = sortedRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function handleSort(column: SortKey) {
    startTransition(() => {
      setPage(1);
      if (column === sortKey) {
        setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
        return;
      }
      setSortKey(column);
      setSortDirection(defaultDirectionForSort(column));
    });
  }

  return (
    <Card className="knd-panel mt-6">
      <CardHeader>
        <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
          Attendee Forecast
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 text-sm text-muted-foreground">
          Players in the field with tournament standing, best regional Elo, and recent commander forecast.
        </div>
        <label className="mb-4 flex flex-col gap-2 text-sm text-muted-foreground">
          Search attendees
          <input
            className="knd-input"
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Standing, player, Elo, region, record, profile ID, or commander"
            type="search"
            value={search}
          />
        </label>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <SortHeader column="standing" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Standing
                </SortHeader>
                <SortHeader column="player" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Player
                </SortHeader>
                <SortHeader column="elo" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Elo
                </SortHeader>
                <SortHeader column="homeRegion" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Home Region
                </SortHeader>
                <SortHeader column="mostLikely" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Most Likely To Bring
                </SortHeader>
                <SortHeader column="alternatives" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Alternatives
                </SortHeader>
                <SortHeader column="record" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Tournament Record
                </SortHeader>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => {
                const regionalProfileHref = `/regional-elo/player/${row.standing.id}${
                  row.regionKey && row.regionKey !== "ALL"
                    ? `?region=${encodeURIComponent(row.regionKey)}`
                    : ""
                }`;
                const primary = row.profile?.commanders[0];
                const alternatives = row.profile?.commanders.slice(1, 3) ?? [];
                const primaryDecklistHref = primary?.latestTopdeckDecklistUrl || primary?.latestDecklistUrl;
                return (
                  <tr key={`${row.standing.id}-${row.standing.standing}`} className="border-t border-border/60">
                    <td className="px-2 py-4 text-muted-foreground">#{row.standing.standing}</td>
                    <td className="px-2 py-4">
                      <div className="space-y-1">
                        <Link
                          className="block font-medium text-foreground hover:text-primary"
                          href={regionalProfileHref}
                          target="_blank"
                        >
                          {row.standing.name}
                        </Link>
                      </div>
                    </td>
                    <td className="px-2 py-4 font-semibold text-primary">
                      {row.rating === null ? "-" : Math.round(row.rating)}
                    </td>
                    <td className="px-2 py-4 text-muted-foreground">{row.regionKey ?? "-"}</td>
                    <td className="px-2 py-4">
                      {primary ? (
                        <div>
                            {primaryDecklistHref ? (
                              <a
                                className="font-medium text-foreground hover:text-primary"
                                href={primaryDecklistHref}
                                rel="noreferrer"
                                target="_blank"
                              >
                                {primary.commander}
                              </a>
                            ) : (
                              <div className="font-medium text-foreground">{primary.commander}</div>
                            )}
                          <div className="text-xs text-muted-foreground">
                            Forecast confidence {formatPercent(primary.predictionShare)} | {primary.entries} recent entries
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">No recent deck data</span>
                      )}
                    </td>
                    <td className="px-2 py-4">
                      <div className="flex flex-wrap gap-2">
                        {alternatives.length ? (
                          alternatives.map((commander) => (
                            commander.latestTopdeckDecklistUrl || commander.latestDecklistUrl ? (
                              <a
                                key={`${row.standing.id}-${commander.commander}`}
                                className="knd-chip hover:text-primary"
                                href={commander.latestTopdeckDecklistUrl || commander.latestDecklistUrl || "#"}
                                rel="noreferrer"
                                target="_blank"
                              >
                                {commander.commander} | {formatPercent(commander.predictionShare)}
                              </a>
                            ) : (
                              <span key={`${row.standing.id}-${commander.commander}`} className="knd-chip">
                                {commander.commander} | {formatPercent(commander.predictionShare)}
                              </span>
                            )
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">No strong alternatives</span>
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-4 text-muted-foreground">
                      {row.standing.points} pts | {Math.round((row.standing.winRate || 0) * 100)}% WR
                    </td>
                  </tr>
                );
              })}
              {visibleRows.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-sm text-muted-foreground">
                    {query ? "No attendees matched that search." : "No attendees found."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationControls currentPage={page} onPageChange={setPage} totalItems={filteredRows.length} />
      </CardContent>
    </Card>
  );
}
