"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { CommanderArtBanner, CommanderArtThumb } from "@/components/commanders/commander-art-thumb";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPercent } from "@/lib/commander-stats";
import type { ScryfallArtByName } from "@/lib/commanders/fetchers";
import { normalizeDisplayString } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type CommanderStat = {
  commander_id: string;
  commander_name: string;
  archetype: string | null;
  color_identity: string[] | null;
  total_entries: number;
  tournaments_played: number;
  total_wins: number;
  total_losses: number;
  total_draws: number;
  avg_win_rate: string;
  top_16_count: number;
  conversion_rate_top_16: string;
  top_cut_count: number;
  conversion_rate_top_cut: string;
};

type SortKey =
  | "commander"
  | "entries"
  | "tournaments"
  | "winRate"
  | "pointsPerGame"
  | "top16"
  | "topCut";

type SortDirection = "asc" | "desc";
type View = "grid" | "table";
type Preset = "all" | "popular" | "established" | "winRate" | "topCut";

const MANA_COLORS = ["W", "U", "B", "R", "G", "C"] as const;
type ManaColor = (typeof MANA_COLORS)[number];

const MANA_LABELS: Record<ManaColor, string> = {
  W: "White",
  U: "Blue",
  B: "Black",
  R: "Red",
  G: "Green",
  C: "Colorless",
};

const MANA_SYMBOL_PATHS: Record<ManaColor, string> = {
  W: "/assets/mana/white.svg",
  U: "/assets/mana/blue.svg",
  B: "/assets/mana/black.svg",
  R: "/assets/mana/red.svg",
  G: "/assets/mana/green.svg",
  C: "/assets/mana/colorless.svg",
};

function getArchetypeIcon(archetype: string | null) {
  if (!archetype) return null;
  const normalized = archetype.toLowerCase();
  if (normalized.includes("turbo")) return "/assets/icons/archetype-turbo.svg";
  if (normalized.includes("mid")) return "/assets/icons/archetype-midrange.svg";
  if (normalized.includes("stax")) return "/assets/icons/archetype-stax.svg";
  if (normalized.includes("control")) return "/assets/icons/archetype-control.svg";
  return null;
}

function safeNumber(value: string): number {
  // parseFloat(null) is NaN, which sorts unpredictably. Treat missing values
  // as -Infinity so they consistently land at the bottom of asc/top of desc.
  const number = parseFloat(value);
  return Number.isFinite(number) ? number : -Infinity;
}

function pointsPerGame(commander: CommanderStat) {
  const games = commander.total_wins + commander.total_losses + commander.total_draws;
  return games ? (commander.total_wins * 5 + commander.total_draws) / games : 0;
}

function compareValues(a: CommanderStat, b: CommanderStat, key: SortKey) {
  switch (key) {
    case "commander":
      return a.commander_name.localeCompare(b.commander_name);
    case "entries":
      return a.total_entries - b.total_entries;
    case "tournaments":
      return a.tournaments_played - b.tournaments_played;
    case "winRate":
      return safeNumber(a.avg_win_rate) - safeNumber(b.avg_win_rate);
    case "pointsPerGame":
      return pointsPerGame(a) - pointsPerGame(b);
    case "top16":
      return safeNumber(a.conversion_rate_top_16) - safeNumber(b.conversion_rate_top_16);
    case "topCut":
      return safeNumber(a.conversion_rate_top_cut) - safeNumber(b.conversion_rate_top_cut);
    default:
      return 0;
  }
}

function ManaSymbol({ color, size = "sm" }: { color: ManaColor; size?: "sm" | "md" }) {
  const dimension = size === "md" ? 28 : 16;
  return (
    <Image
      src={MANA_SYMBOL_PATHS[color]}
      alt={`${MANA_LABELS[color]} mana symbol`}
      width={dimension}
      height={dimension}
      className="shrink-0"
    />
  );
}

function ManaSymbols({
  colors,
  size,
}: {
  colors: string[] | null;
  size?: "sm" | "md";
}) {
  const identity = (colors ?? []).filter((color): color is ManaColor =>
    MANA_COLORS.includes(color as ManaColor)
  );
  if (!identity.length) {
    return <ManaSymbol color="C" size={size} />;
  }
  return (
    <span className="flex items-center -space-x-0.5">
      {identity.map((color) => (
        <ManaSymbol key={color} color={color} size={size} />
      ))}
    </span>
  );
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
      className={`flex w-full items-center gap-1.5 text-xs uppercase tracking-[0.2em] ${
        align === "right" ? "justify-end" : "justify-start"
      }`}
    >
      <span>{label}</span>
      <span className={active ? "text-foreground" : "text-muted-foreground"} aria-hidden>
        {active && direction === "asc" ? "▴" : "▾"}
      </span>
    </button>
  );
}

function ViewToggle({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  return (
    <div
      className="inline-flex rounded-[10px] border border-border bg-muted/30 p-1"
      aria-label="Commander display mode"
    >
      {(["grid", "table"] as const).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          aria-pressed={view === option}
          className={`min-h-9 rounded-lg px-3 text-sm font-medium capitalize transition-colors ${
            view === option
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function CommanderGrid({
  commanders,
  ranks,
  artByName,
}: {
  commanders: CommanderStat[];
  ranks: Map<string, number>;
  artByName?: ScryfallArtByName;
}) {
  return (
    <div
      data-testid="commanders-grid"
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 md:gap-4"
    >
      {commanders.map((commander) => (
        <Link
          key={commander.commander_id}
          href={`/commanders/${commander.commander_id}`}
          className="group overflow-hidden rounded-xl border border-border bg-card/70 shadow-[0_20px_50px_rgba(2,10,26,0.35)] transition-colors hover:border-primary/45 hover:bg-card/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <div className="relative h-[88px] overflow-hidden sm:h-[104px]">
            <CommanderArtBanner name={commander.commander_name} artByName={artByName} />
            <div className="absolute inset-0 bg-gradient-to-b from-background/10 to-background/95" />
            <span className="absolute left-2 top-2 rounded-md bg-background/75 px-1.5 py-0.5 font-mono text-[10px] font-semibold">
              #{ranks.get(commander.commander_id)}
            </span>
            <div className="absolute bottom-2 left-2">
              <ManaSymbols colors={commander.color_identity} />
            </div>
          </div>
          <div className="p-2.5 sm:p-3">
            <p className="min-h-8 line-clamp-2 text-[12.5px] font-semibold leading-4 sm:min-h-9 sm:text-sm sm:leading-[1.15rem]">
              {normalizeDisplayString(commander.commander_name)}
            </p>
            <div className="mt-2 flex items-end justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Win Rate
                </p>
                <p className="font-mono text-base font-semibold leading-tight text-primary sm:text-xl">
                  {formatPercent(parseFloat(commander.avg_win_rate))}
                </p>
              </div>
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Top Cut
                </p>
                <p className="font-mono text-xs text-muted-foreground sm:text-sm">
                  {formatPercent(parseFloat(commander.conversion_rate_top_cut))}
                </p>
              </div>
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-muted-foreground sm:mt-2">
              {commander.total_entries.toLocaleString()} entries
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}

function CommanderTable({
  commanders,
  ranks,
  artByName,
  sortKey,
  sortDirection,
  onSort,
}: {
  commanders: CommanderStat[];
  ranks: Map<string, number>;
  artByName?: ScryfallArtByName;
  sortKey: SortKey;
  sortDirection: SortDirection;
  onSort: (key: SortKey) => void;
}) {
  return (
    <Card data-testid="all-commanders-card">
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">All Commanders</CardTitle>
      </CardHeader>
      <CardContent className="px-3 pb-3 sm:px-6 sm:pb-6">
        <Table data-testid="all-commanders-table">
          <TableHeader>
            <TableRow className="border-border/60 text-muted-foreground">
              <TableHead className="py-3">Rank</TableHead>
              <TableHead className="py-3">
                <SortButton
                  label="Commander"
                  active={sortKey === "commander"}
                  direction={sortDirection}
                  onClick={() => onSort("commander")}
                />
              </TableHead>
              <TableHead className="hidden py-3 sm:table-cell">Colors</TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Entries"
                  active={sortKey === "entries"}
                  direction={sortDirection}
                  onClick={() => onSort("entries")}
                  align="right"
                />
              </TableHead>
              <TableHead className="hidden py-3 text-right sm:table-cell">
                <SortButton
                  label="Tournaments"
                  active={sortKey === "tournaments"}
                  direction={sortDirection}
                  onClick={() => onSort("tournaments")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Win Rate"
                  active={sortKey === "winRate"}
                  direction={sortDirection}
                  onClick={() => onSort("winRate")}
                  align="right"
                />
              </TableHead>
              <TableHead className="hidden py-3 text-right md:table-cell">
                <SortButton
                  label="Pts/Game"
                  active={sortKey === "pointsPerGame"}
                  direction={sortDirection}
                  onClick={() => onSort("pointsPerGame")}
                  align="right"
                />
              </TableHead>
              <TableHead className="hidden py-3 text-right lg:table-cell">
                <SortButton
                  label="Top 16/10"
                  active={sortKey === "top16"}
                  direction={sortDirection}
                  onClick={() => onSort("top16")}
                  align="right"
                />
              </TableHead>
              <TableHead className="py-3 text-right">
                <SortButton
                  label="Top Cut"
                  active={sortKey === "topCut"}
                  direction={sortDirection}
                  onClick={() => onSort("topCut")}
                  align="right"
                />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {commanders.map((commander) => {
              const archetypeIcon = getArchetypeIcon(commander.archetype);
              return (
                <TableRow key={commander.commander_id} className="border-border/60">
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    #{ranks.get(commander.commander_id)}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/commanders/${commander.commander_id}`}
                      className="flex items-center gap-3 text-foreground hover:text-primary"
                    >
                      <CommanderArtThumb
                        name={commander.commander_name}
                        size={36}
                        artByName={artByName}
                      />
                      <span className="min-w-0">
                        <span className="font-medium line-clamp-1 max-w-[120px] sm:max-w-none sm:line-clamp-none">
                          {normalizeDisplayString(commander.commander_name)}
                        </span>
                        {commander.archetype && (
                          <span className="ml-2 hidden sm:inline-flex items-center gap-2 text-sm text-muted-foreground">
                            {archetypeIcon && (
                              <Image src={archetypeIcon} alt="" width={16} height={16} />
                            )}
                            {normalizeDisplayString(commander.archetype)}
                          </span>
                        )}
                      </span>
                    </Link>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <ManaSymbols colors={commander.color_identity} />
                  </TableCell>
                  <TableCell className="text-right font-mono text-foreground">
                    {commander.total_entries.toLocaleString()}
                  </TableCell>
                  <TableCell className="hidden text-right font-mono text-muted-foreground sm:table-cell">
                    {commander.tournaments_played}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    <span className="text-primary">
                      {formatPercent(parseFloat(commander.avg_win_rate))}
                    </span>
                  </TableCell>
                  <TableCell className="hidden text-right font-mono text-muted-foreground md:table-cell">
                    {pointsPerGame(commander).toFixed(2)}
                  </TableCell>
                  <TableCell className="hidden text-right font-mono text-muted-foreground lg:table-cell">
                    {formatPercent(parseFloat(commander.conversion_rate_top_16))}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatPercent(parseFloat(commander.conversion_rate_top_cut))}
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

export default function CommandersTable({
  commanders,
  artByName,
}: {
  commanders: CommanderStat[];
  artByName?: ScryfallArtByName;
}) {
  const [view, setView] = useState<View>("grid");
  const [query, setQuery] = useState("");
  const [colors, setColors] = useState<ManaColor[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("entries");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [minimumEntries, setMinimumEntries] = useState(5);
  const [preset, setPreset] = useState<Preset>("all");

  const ranks = useMemo(() => {
    const map = new Map<string, number>();
    commanders.forEach((commander, index) => {
      map.set(commander.commander_id, index + 1);
    });
    return map;
  }, [commanders]);

  const filteredCommanders = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return commanders.filter((commander) => {
      const nameMatch = normalizeDisplayString(commander.commander_name)
        .toLowerCase()
        .includes(normalizedQuery);
      const colorMatch = colors.every((color) =>
        color === "C"
          ? !commander.color_identity?.length
          : commander.color_identity?.includes(color)
      );
      return nameMatch && colorMatch && commander.total_entries >= minimumEntries;
    });
  }, [commanders, colors, minimumEntries, query]);

  const sortedCommanders = useMemo(() => {
    const sorted = [...filteredCommanders].sort((a, b) =>
      compareValues(a, b, sortKey)
    );
    return sortDirection === "asc" ? sorted : sorted.reverse();
  }, [filteredCommanders, sortDirection, sortKey]);

  const filteredEntries = useMemo(
    () => filteredCommanders.reduce((total, commander) => total + commander.total_entries, 0),
    [filteredCommanders]
  );

  function setMetric(key: SortKey) {
    setSortDirection((current) =>
      key === sortKey ? (current === "desc" ? "asc" : "desc") : "desc"
    );
    setSortKey(key);
  }

  function applyPreset(nextPreset: Preset) {
    setPreset(nextPreset);
    setQuery("");
    setColors([]);

    switch (nextPreset) {
      case "popular":
        setMinimumEntries(5);
        setSortKey("entries");
        break;
      case "established":
        setMinimumEntries(50);
        setSortKey("entries");
        break;
      case "winRate":
        setMinimumEntries(50);
        setSortKey("winRate");
        break;
      case "topCut":
        setMinimumEntries(50);
        setSortKey("topCut");
        break;
      default:
        setMinimumEntries(5);
        setSortKey("entries");
    }
    setSortDirection("desc");
  }

  function handleSort(key: SortKey) {
    setSortDirection((current) =>
      key === sortKey ? (current === "desc" ? "asc" : "desc") : "desc"
    );
    setSortKey(key);
  }

  const toggleColor = (color: ManaColor) => {
    setColors((selected) =>
      selected.includes(color)
        ? selected.filter((item) => item !== color)
        : [...selected, color]
    );
  };

  return (
    <section aria-labelledby="all-commanders-heading">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center">
        <div className="min-w-0 flex-1">
          <h2 id="all-commanders-heading" className="text-lg font-semibold">
            All Commanders
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse the competitive field by usage and performance.
          </p>
        </div>
        <ViewToggle view={view} onChange={setView} />
      </div>

      <div className="mb-3 flex max-w-full gap-2 overflow-x-auto pb-1" aria-label="Commander presets">
        {(
          [
            ["all", "All commanders"],
            ["popular", "Most played"],
            ["established", "Established"],
            ["winRate", "Win rate leaders"],
            ["topCut", "Top cut leaders"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => applyPreset(key)}
            aria-pressed={preset === key}
            className={`knd-chip min-h-9 shrink-0 whitespace-nowrap transition-colors ${
              preset === key ? "border-primary/50 text-foreground" : "hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-card/55 p-3.5 backdrop-blur-sm sm:px-4">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="knd-input min-h-11 w-full sm:w-56"
          placeholder="Search a commander"
          aria-label="Search commanders"
        />
        <div className="hidden h-6 w-px bg-border sm:block" />
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Colors
        </span>
        <div className="flex gap-1.5">
          {MANA_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              onClick={() => toggleColor(color)}
              aria-pressed={colors.includes(color)}
              aria-label={`Filter by ${MANA_LABELS[color]}`}
              className={`rounded-full p-0.5 transition-opacity focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 ${
                colors.length && !colors.includes(color) ? "opacity-35" : "opacity-100"
              }`}
            >
              <ManaSymbol color={color} size="md" />
            </button>
          ))}
        </div>
        <div className="hidden h-6 w-px bg-border lg:block" />
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Sort by
            <Select value={sortKey} onValueChange={(value) => { setMetric(value as SortKey); setPreset("all"); }}>
              <SelectTrigger className="w-36 rounded-full bg-input/50"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="entries">Popularity</SelectItem>
                <SelectItem value="winRate">Win rate</SelectItem>
                <SelectItem value="topCut">Top cut</SelectItem>
                <SelectItem value="pointsPerGame">Points / game</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Min. entries
            <Select value={String(minimumEntries)} onValueChange={(value) => { setMinimumEntries(Number(value)); setPreset("all"); }}>
              <SelectTrigger className="w-32 rounded-full bg-input/50"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5+ entries</SelectItem>
                <SelectItem value="20">20+ entries</SelectItem>
                <SelectItem value="50">50+ entries</SelectItem>
                <SelectItem value="100">100+ entries</SelectItem>
              </SelectContent>
            </Select>
          </label>
        </div>
        <span className="ml-auto font-mono text-xs text-muted-foreground">
          {filteredEntries.toLocaleString()} entries
        </span>
      </div>

      {sortedCommanders.length ? (
        view === "grid" ? (
          <CommanderGrid
            commanders={sortedCommanders}
            ranks={ranks}
            artByName={artByName}
          />
        ) : (
          <CommanderTable
            commanders={sortedCommanders}
            ranks={ranks}
            artByName={artByName}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onSort={handleSort}
          />
        )
      ) : (
        <div className="rounded-2xl border border-border/60 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
          No commanders match your filters.
        </div>
      )}
    </section>
  );
}
