"use client";

import { startTransition, useDeferredValue, useMemo, useState } from "react";
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
  | "decklist"
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
  wins: number;
  draws: number;
  losses: number;
  actualDeckCommander: string | null;
  actualDecklistUrl: string | null;
};

type EloAttendee = {
  topdeck_id: string | null;
  player_name: string;
  rating: number | null;
  hidden_rating?: number;
  topdeck_elo?: number | null;
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

function displayedCommanderPercents(commanders: CommanderPrediction[]) {
  const percents = commanders.map((commander) => ({
    commander,
    percent: Math.round(commander.predictionShare * 100),
  }));

  for (const row of percents) {
    if (row.commander.predictionShare > 0 && row.percent === 0) {
      row.percent = 1;
    }
  }

  while (percents.reduce((sum, row) => sum + row.percent, 0) > 100) {
    const reducer = percents
      .map((row, index) => ({ ...row, index }))
      .filter((row) => row.percent > 1)
      .sort((a, b) => b.percent - a.percent)[0];

    if (!reducer) break;
    percents[reducer.index].percent -= 1;
  }

  return percents.map((row) => row.percent);
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

function compareRecord(a: TournamentStanding, b: TournamentStanding, direction: SortDirection) {
  const result = b.wins - a.wins || b.draws - a.draws || a.losses - b.losses;
  return direction === "desc" ? result : -result;
}

function formatTournamentRecord(standing: TournamentStanding) {
  const hasRecord = standing.wins > 0 || standing.losses > 0 || standing.draws > 0;
  if (!hasRecord) return String(standing.points);
  return `${standing.points} | ${standing.wins}-${standing.losses}-${standing.draws}`;
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
    if (key === "decklist") {
      return compareText(a.standing.actualDeckCommander, b.standing.actualDeckCommander, direction);
    }

    return compareRecord(a.standing, b.standing, direction);
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
  showActualDecks,
  showTournamentRecord,
  standings,
}: {
  eloAttendees: EloAttendee[];
  profiles: PlayerCommanderProfile[];
  showActualDecks: boolean;
  showTournamentRecord: boolean;
  standings: TournamentStanding[];
}) {
  const defaultSortKey: SortKey = showTournamentRecord ? "standing" : "elo";
  const visibleColumnCount = 3 + (showActualDecks ? 1 : 2) + (showTournamentRecord ? 2 : 0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>(defaultSortKey);
  const [sortDirection, setSortDirection] = useState<SortDirection>(
    defaultDirectionForSort(defaultSortKey)
  );
  const deferredSearch = useDeferredValue(search);
  const profileByPlayer = useMemo(
    () => new Map(profiles.map((profile) => [profile.topdeckId, profile])),
    [profiles]
  );
  const eloByPlayer = useMemo(
    () =>
      new Map(
        eloAttendees
          .filter((attendee) => attendee.topdeck_id)
          .map((attendee) => [attendee.topdeck_id as string, attendee])
      ),
    [eloAttendees]
  );
  const rows = useMemo(
    () =>
      standings.map((standing) => {
        const elo = eloByPlayer.get(standing.id);
        return {
          standing,
          profile: profileByPlayer.get(standing.id),
          rating: elo?.rating ?? null,
          regionKey: elo?.region_key ?? null,
        };
      }),
    [eloByPlayer, profileByPlayer, standings]
  );
  const query = normalizeSearch(deferredSearch);
  const filteredRows = useMemo(
    () =>
      query
        ? rows.filter((row) => {
            const commanders = row.profile?.commanders.map((commander) => commander.commander).join(" ");
            return (
              includesSearch(row.standing.standing, query) ||
              includesSearch(row.standing.name, query) ||
              includesSearch(row.standing.username, query) ||
              includesSearch(row.standing.id, query) ||
              includesSearch(row.rating, query) ||
              includesSearch(row.regionKey, query) ||
              includesSearch(row.standing.actualDeckCommander, query) ||
              includesSearch(row.standing.points, query) ||
              includesSearch(formatTournamentRecord(row.standing), query) ||
              includesSearch(commanders, query)
            );
          })
        : rows,
    [query, rows]
  );
  const sortedRows = useMemo(
    () => sortRows(filteredRows, sortKey, sortDirection),
    [filteredRows, sortDirection, sortKey]
  );
  const visibleRows = useMemo(
    () => sortedRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [page, sortedRows]
  );

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
          {showActualDecks ? "Attendees" : "Attendee Forecast"}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 text-sm text-muted-foreground">
          {showActualDecks
            ? "Players in the field with tournament standing, TopDeck Elo, and commander data."
            : "Players in the field with TopDeck Elo and recent commander forecast."}
        </div>
        <label className="mb-4 flex flex-col gap-2 text-sm text-muted-foreground">
          Search attendees
          <input
            className="knd-input"
            onChange={(event) => {
              const value = event.target.value;
              setSearch(value);
              startTransition(() => {
                setPage(1);
              });
            }}
            placeholder={
              showActualDecks
                ? "Standing, player, TopDeck Elo, region, record, profile ID, or commander"
                : showTournamentRecord
                  ? "Player, TopDeck Elo, region, record, profile ID, or commander"
                  : "Player, TopDeck Elo, region, profile ID, or commander"
            }
            type="search"
            value={search}
          />
        </label>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                {showTournamentRecord && (
                  <SortHeader column="standing" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                    Pos
                  </SortHeader>
                )}
                <SortHeader column="player" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Player
                </SortHeader>
                {showTournamentRecord && (
                  <th className="px-2 py-3 hidden md:table-cell">
                    <button
                      className={`text-left uppercase tracking-[0.3em] transition hover:text-foreground ${
                        sortKey === "record" ? "text-foreground" : ""
                      }`}
                      onClick={() => handleSort("record")}
                      type="button"
                    >
                      Record
                      {sortKey === "record" && <span className="ml-1 text-[10px]">{sortDirection === "asc" ? "^" : "v"}</span>}
                    </button>
                  </th>
                )}
                <SortHeader column="elo" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                  Elo
                </SortHeader>
                <th className="px-2 py-3 hidden lg:table-cell">
                  <button
                    className={`text-left uppercase tracking-[0.3em] transition hover:text-foreground ${
                      sortKey === "homeRegion" ? "text-foreground" : ""
                    }`}
                    onClick={() => handleSort("homeRegion")}
                    type="button"
                  >
                    Region
                    {sortKey === "homeRegion" && <span className="ml-1 text-[10px]">{sortDirection === "asc" ? "^" : "v"}</span>}
                  </button>
                </th>
                {showActualDecks ? (
                  <SortHeader column="decklist" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                    Decklist
                  </SortHeader>
                ) : (
                  <>
                    <SortHeader column="mostLikely" direction={sortDirection} onSort={handleSort} sortKey={sortKey}>
                      Most Likely
                    </SortHeader>
                    <th className="px-2 py-3 hidden md:table-cell">
                      <button
                        className={`text-left uppercase tracking-[0.3em] transition hover:text-foreground ${
                          sortKey === "alternatives" ? "text-foreground" : ""
                        }`}
                        onClick={() => handleSort("alternatives")}
                        type="button"
                      >
                        Alternatives
                        {sortKey === "alternatives" && <span className="ml-1 text-[10px]">{sortDirection === "asc" ? "^" : "v"}</span>}
                      </button>
                    </th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => {
                const regionalProfileHref = `/regional-elo/player/${row.standing.id}`;
                const primary = row.profile?.commanders[0];
                const alternatives = row.profile?.commanders.slice(1, 3) ?? [];
                const displayedPercents = displayedCommanderPercents(row.profile?.commanders.slice(0, 3) ?? []);
                const primaryDecklistHref = primary?.latestTopdeckDecklistUrl || primary?.latestDecklistUrl;
                return (
                  <tr key={`${row.standing.id}-${row.standing.standing}`} className="border-t border-border/60">
                    {showTournamentRecord && (
                      <td className="px-2 py-4 text-muted-foreground text-xs">#{row.standing.standing}</td>
                    )}
                    <td className="px-2 py-4">
                      <div className="space-y-1">
                        <Link
                          className="block font-medium text-foreground hover:text-primary truncate max-w-[120px] sm:max-w-none"
                          href={regionalProfileHref}
                          target="_blank"
                        >
                          {row.standing.name}
                        </Link>
                      </div>
                    </td>
                    {showTournamentRecord && (
                      <td className="px-2 py-4 text-muted-foreground hidden md:table-cell">{formatTournamentRecord(row.standing)}</td>
                    )}
                    <td className="px-2 py-4 font-semibold text-primary">
                      {row.rating === null ? "-" : Math.round(row.rating)}
                    </td>
                    <td className="px-2 py-4 text-muted-foreground hidden lg:table-cell">{row.regionKey ?? "-"}</td>
                    {showActualDecks ? (
                      <td className="px-2 py-4">
                        {row.standing.actualDeckCommander && row.standing.actualDecklistUrl ? (
                          <a
                            className="font-medium text-foreground hover:text-primary line-clamp-1 sm:line-clamp-none"
                            href={row.standing.actualDecklistUrl}
                            rel="noreferrer"
                            target="_blank"
                          >
                            {row.standing.actualDeckCommander}
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground">No decklist</span>
                        )}
                      </td>
                    ) : (
                      <>
                        <td className="px-2 py-4">
                          {primary ? (
                            <div>
                              {primaryDecklistHref ? (
                                <a
                                  className="font-medium text-foreground hover:text-primary line-clamp-1 sm:line-clamp-none"
                                  href={primaryDecklistHref}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  {primary.commander}
                                </a>
                              ) : (
                                <div className="font-medium text-foreground">{primary.commander}</div>
                              )}
                              <div className="text-[10px] text-muted-foreground sm:text-xs">
                                {displayedPercents[0] ?? 0}%
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">No data</span>
                          )}
                        </td>
                        <td className="px-2 py-4 hidden md:table-cell">
                          <div className="flex flex-wrap gap-2">
                            {alternatives.length ? (
                              alternatives.map((commander, index) => (
                                commander.latestTopdeckDecklistUrl || commander.latestDecklistUrl ? (
                                  <a
                                    key={`${row.standing.id}-${commander.commander}`}
                                    className="knd-chip hover:text-primary"
                                    href={commander.latestTopdeckDecklistUrl || commander.latestDecklistUrl || "#"}
                                    rel="noreferrer"
                                    target="_blank"
                                  >
                                    {commander.commander} | {displayedPercents[index + 1] ?? 0}%
                                  </a>
                                ) : (
                                  <span key={`${row.standing.id}-${commander.commander}`} className="knd-chip">
                                    {commander.commander} | {displayedPercents[index + 1] ?? 0}%
                                  </span>
                                )
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">None</span>
                            )}
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}
              {visibleRows.length === 0 && (
                <tr>
                  <td colSpan={visibleColumnCount} className="py-6 text-center text-sm text-muted-foreground">
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
