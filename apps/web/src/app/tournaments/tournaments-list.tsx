"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { assignEventTier, TIER_MIN, type EventTier, type TournamentSummary, type TopCutPlayer } from "@/lib/tournaments";

// ---- Types ----
type SortOption = "Date" | "Players";
type TierOption = "All Tiers" | EventTier;
type PeriodOption = "3 Months" | "6 Months" | "1 Year" | "All";

// ---- Constants ----
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

const TIER_STYLE: Record<Exclude<TierOption, "All Tiers">, { color: string; bg: string; border: string }> = {
  Diamond: { color: "hsl(305 85% 65%)", bg: "hsl(305 85% 65% / 0.13)", border: "hsl(305 85% 65% / 0.32)" },
  Platinum: { color: "#8fd3fb", bg: "rgba(125,211,252,.12)", border: "rgba(125,211,252,.30)" },
  Gold: { color: "hsl(38 80% 60%)", bg: "hsl(38 80% 60% / 0.13)", border: "hsl(38 80% 60% / 0.32)" },
  Silver: { color: "#cbd5e1", bg: "rgba(203,213,225,.10)", border: "rgba(203,213,225,.26)" },
  Bronze: { color: "#d8995a", bg: "rgba(205,127,50,.14)", border: "rgba(205,127,50,.32)" },
};

const PERIOD_DAYS: Record<PeriodOption, number> = {
  "3 Months": 92,
  "6 Months": 183,
  "1 Year": 365,
  All: 1e9,
};

const TODAY = new Date();

// ---- Helpers ----
type TournamentsListProps = {
  initialSort: SortOption;
  initialTier: TierOption;
  initialPeriod: PeriodOption;
};

type TournamentRow = {
  id: string;
  topdeck_tid: string | null;
  name: string | null;
  start_date: string | null;
  player_count: number | null;
  tier: EventTier | null;
};

type TopCutRow = {
  tournament_id: string;
  final_standing: number;
  players: { name: string | null } | Array<{ name: string | null }> | null;
  commanders: { name: string | null; color_identity: string[] | null } | Array<{ name: string | null; color_identity: string[] | null }> | null;
};

function relTime(days: number): string {
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 14) return "last week";
  if (days < 31) return `${Math.round(days / 7)} weeks ago`;
  if (days < 365) return `${Math.round(days / 30)} months ago`;
  return "over a year ago";
}

function firstRelation<T>(value: T | T[] | null | undefined): T | null {
  if (!value) return null;
  return Array.isArray(value) ? value[0] ?? null : value;
}

// ---- FilterDropdown ----
interface FilterDropdownProps {
  label: string;
  display: string;
  isOpen: boolean;
  onToggle: () => void;
  options: { label: string; active: boolean; onSelect: () => void }[];
}

function FilterDropdown({ label, display, isOpen, onToggle, options }: FilterDropdownProps) {
  return (
    <div className="relative flex flex-col gap-1.5">
      <span className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
        {label}
      </span>
      <button
        onClick={onToggle}
        className="inline-flex items-center justify-between gap-2.5 min-w-[132px] px-3 py-2 border border-border rounded-[10px] bg-muted/55 text-foreground text-sm cursor-pointer transition-colors hover:border-primary/50"
      >
        <span>{display}</span>
        <span className="text-muted-foreground text-[10px]">▾</span>
      </button>
      {isOpen && (
        <div className="absolute top-full left-0 mt-1.5 min-w-[150px] z-50 p-1.5 bg-card border border-border rounded-xl shadow-[0_20px_50px_rgba(2,10,26,.55)] backdrop-blur-md flex flex-col gap-0.5">
          {options.map((opt) => (
            <button
              key={opt.label}
              onClick={opt.onSelect}
              className="flex justify-between items-center w-full text-left px-2.5 py-2 border-none rounded-lg text-sm cursor-pointer whitespace-nowrap gap-3 transition-colors"
              style={{
                background: opt.active ? "oklch(0.32 0.04 260 / 0.5)" : "transparent",
                color: opt.active ? "var(--foreground)" : "var(--muted-foreground)",
                fontWeight: opt.active ? 600 : 400,
              }}
            >
              <span>{opt.label}</span>
              {opt.active && (
                <span style={{ color: "hsl(var(--knd-cyan))" }}>★</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Page ----
export function TournamentsList({ initialSort, initialTier, initialPeriod }: TournamentsListProps) {
  const [sortBy, setSortBy] = useState<SortOption>(initialSort);
  const [tierFilter, setTierFilter] = useState<TierOption>(initialTier);
  const [period, setPeriod] = useState<PeriodOption>(initialPeriod);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [events, setEvents] = useState<TournamentSummary[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      const { data: tournamentRows, error } = await supabase
        .from("tournaments")
        .select("id, topdeck_tid, name, start_date, player_count, tier")
        .not("topdeck_tid", "is", null)
        .gte("player_count", 16)
        .order("start_date", { ascending: false })
        .limit(100);

      if (error || !tournamentRows?.length || cancelled) return;

      const rows = tournamentRows as TournamentRow[];
      const ids = rows.map((row) => row.id);
      const { data: topRows } = await supabase
        .from("tournament_entries")
        .select("tournament_id, final_standing, players(name), commanders(name, color_identity)")
        .in("tournament_id", ids)
        .lte("final_standing", 4)
        .order("final_standing", { ascending: true });

      const topCutByTournamentId = new Map<string, TopCutPlayer[]>();
      for (const row of ((topRows ?? []) as unknown as TopCutRow[])) {
        const tId = row.tournament_id;
        const entries = topCutByTournamentId.get(tId) ?? [];
        entries.push({
          standing: row.final_standing,
          name: firstRelation(row.players)?.name ?? "Unknown",
          commander: firstRelation(row.commanders)?.name ?? "Unknown Commander",
          colors: firstRelation(row.commanders)?.color_identity ?? [],
        });
        topCutByTournamentId.set(tId, entries);
      }

      const loadedEvents = rows
        .filter((row) => row.topdeck_tid && row.name && row.start_date && row.player_count)
        .map((row) => {
          const topCut = topCutByTournamentId.get(row.id) ?? [];
          const winner = topCut.find((c) => c.standing === 1)?.name ?? "—";
          return {
            name: (row.name ?? "").trim(),
            date: (row.start_date ?? "").slice(0, 10),
            players: row.player_count ?? 0,
            winner,
            topCut,
            slug: row.topdeck_tid as string,
            topdeckTid: row.topdeck_tid as string,
            tier: row.tier ?? assignEventTier(row.player_count ?? 0),
            hasDetail: true,
          };
        });

      if (!cancelled && loadedEvents.length > 0) {
        setEvents(loadedEvents);
      }
    }

    void loadEvents();

    return () => {
      cancelled = true;
    };
  }, []);

  function setFilter(key: string, value: string) {
    const p = new URLSearchParams(window.location.search);
    p.set(key, value);
    window.history.replaceState(null, "", window.location.pathname + "?" + p.toString());
  }

  function toggleMenu(name: string) {
    setOpenMenu((prev) => (prev === name ? null : name));
  }

  // ---- Compute rows ----
  const periodDays = PERIOD_DAYS[period];

  const items = events.map((t) => {
    const d = new Date(t.date + "T00:00:00");
    const days = Math.round((TODAY.getTime() - d.getTime()) / 86400000);
    return { ...t, d, days };
  })
    .filter((t) => (tierFilter === "All Tiers" || t.tier === tierFilter) && t.days <= periodDays)
    .sort((a, b) => (sortBy === "Players" ? b.players - a.players : a.days - b.days));

  const tierLabel =
    tierFilter === "All Tiers" ? "all tiers" : tierFilter.toLowerCase();
  const countText = `${items.length} events · ${period.toLowerCase()} · ${tierLabel}`;

  // ---- Dropdown option builders ----
  const sortOptions = (["Date", "Players"] as SortOption[]).map((o) => ({
    label: o,
    active: o === sortBy,
    onSelect: () => {
      setSortBy(o);
      setFilter("sort", o);
      setOpenMenu(null);
    },
  }));

  const tierOptions = (["All Tiers", "Diamond", "Platinum", "Gold", "Silver", "Bronze"] as TierOption[]).map((o) => ({
    label: o === "All Tiers" ? "All Tiers" : `${o} · ${TIER_MIN[o]}+`,
    active: o === tierFilter,
    onSelect: () => {
      setTierFilter(o);
      setFilter("tier", o);
      setOpenMenu(null);
    },
  }));

  const periodOptions = (["3 Months", "6 Months", "1 Year", "All"] as PeriodOption[]).map((o) => ({
    label: o,
    active: o === period,
    onSelect: () => {
      setPeriod(o);
      setFilter("period", o);
      setOpenMenu(null);
    },
  }));

  return (
    <>
      {/* Click-outside overlay when any menu is open */}
      {openMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setOpenMenu(null)}
        />
      )}

      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-10 pb-20">
        {/* Page header */}
        <div className="mb-7">
          <div
            className="mb-2.5 text-xs font-medium uppercase tracking-[0.2em] font-mono"
            style={{ color: "hsl(var(--knd-cyan))" }}
          >
            TOURNAMENTS
          </div>
          <h1 className="m-0 text-4xl font-semibold tracking-tight">
            Latest Tournaments
          </h1>
          <p className="mt-2.5 text-[15px] leading-relaxed text-muted-foreground max-w-xl">
            Recent competitive events, newest first. Filter by recency and event tier. Click any event for full standings, round story, and bracket.
          </p>
        </div>

        {/* Filter bar */}
        <div className="relative z-41 flex items-end gap-5 flex-wrap px-4 sm:px-5 py-4 mb-4 knd-panel">
          <FilterDropdown
            label="Sort By"
            display={sortBy}
            isOpen={openMenu === "sort"}
            onToggle={() => toggleMenu("sort")}
            options={sortOptions}
          />
          <FilterDropdown
            label="Event Tier"
            display={tierFilter === "All Tiers" ? "All Tiers" : `${tierFilter} · ${TIER_MIN[tierFilter]}+`}
            isOpen={openMenu === "tier"}
            onToggle={() => toggleMenu("tier")}
            options={tierOptions}
          />
          <FilterDropdown
            label="Time Period"
            display={period}
            isOpen={openMenu === "period"}
            onToggle={() => toggleMenu("period")}
            options={periodOptions}
          />
          <div className="flex-1" />
          <span
            className="pb-2 text-xs font-mono text-muted-foreground"
          >
            {countText}
          </span>
        </div>

        {/* Tournament list */}
        <div className="relative knd-panel overflow-hidden">
          {items.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-muted-foreground font-mono">
              No events match the current filters.
            </div>
          ) : (
            items.map((t, i) => {
              const tier = t.tier;
              const ts = TIER_STYLE[tier];
              const href = `/tournaments/${t.slug}`;
              const winnerEntry = t.topCut?.find((c) => c.standing === 1) ?? null;

              return (
                <div
                  key={t.slug}
                  className="group"
                  style={{
                    borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <Link
                    href={href}
                    className="flex items-start gap-3 px-4 sm:px-5 py-3.5 sm:py-4 no-underline transition-colors hover:bg-accent/25"
                  >
                    {/* Date column */}
                    <div className="flex flex-col items-center justify-center w-11 sm:w-14 flex-shrink-0 border-r border-border pr-3 sm:pr-4 self-center">
                      <span className="text-[10px] sm:text-[11px] tracking-[0.16em] uppercase text-muted-foreground font-medium">
                        {MONTHS[t.d.getMonth()]}
                      </span>
                      <span className="font-mono text-[19px] sm:text-[22px] font-semibold leading-none">
                        {t.d.getDate()}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {t.d.getFullYear()}
                      </span>
                    </div>

                    {/* Content column */}
                    <div className="flex-1 min-w-0 flex flex-col gap-1">

                      {/* Name row */}
                      <div className="flex items-start sm:items-center gap-2">
                        <div className="flex-1 min-w-0">
                          <span className="block text-[15px] sm:text-[17px] font-semibold leading-snug text-foreground truncate">
                            {t.name}
                          </span>
                          {/* Rel time below name on mobile */}
                          <span className="block sm:hidden text-[11px] text-muted-foreground mt-0.5">
                            {relTime(t.days)}
                          </span>
                        </div>

                        {/* Rel time inline on desktop */}
                        <span className="hidden sm:inline text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                          {relTime(t.days)}
                        </span>

                        {/* Tier badge — always visible */}
                        {ts && (
                          <span
                            className="flex-shrink-0 whitespace-nowrap self-start sm:self-auto"
                            style={{
                              padding: "3px 9px",
                              borderRadius: 999,
                              fontSize: 10,
                              fontWeight: 600,
                              fontFamily: "var(--font-mono)",
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                              color: ts.color,
                              background: ts.bg,
                              border: `1px solid ${ts.border}`,
                            }}
                          >
                            {tier}
                          </span>
                        )}

                        {/* Desktop-only: player count + chevron */}
                        <div className="hidden sm:flex items-center gap-3 flex-shrink-0">
                          <div className="flex flex-col items-end">
                            <span className="font-mono text-xl font-semibold text-primary leading-none">
                              {t.players.toLocaleString("en-US")}
                            </span>
                            <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-medium">
                              Players
                            </span>
                          </div>
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className="flex-shrink-0"
                            style={{ color: "hsl(var(--knd-cyan) / 0.6)" }}
                          >
                            <path d="m9 18 6-6-6-6" />
                          </svg>
                        </div>
                      </div>

                      {/* Desktop-only: top-4 entries */}
                      {t.topCut && t.topCut.length > 0 && (
                        <div className="hidden sm:flex flex-wrap items-center gap-x-4 gap-y-1">
                          {t.topCut.map((cut, ci) => (
                            <div key={`${cut.standing}-${cut.name}-${ci}`} className="flex items-center gap-1.5 min-w-0 max-w-[200px]">
                              <span className={`text-[10px] font-mono font-bold flex-shrink-0 ${cut.standing === 1 ? "text-[hsl(var(--knd-amber))]" : "text-muted-foreground"}`}>
                                {cut.standing === 1 ? "★" : `${cut.standing}`}
                              </span>
                              <div className="flex flex-col min-w-0">
                                <span className={`text-xs truncate ${cut.standing === 1 ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                                  {cut.name}
                                </span>
                                <span className="text-[10px] text-muted-foreground/70 truncate" title={cut.commander}>
                                  {cut.commander}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Mobile-only: winner summary + player count + chevron */}
                      <div className="sm:hidden flex items-center gap-1.5 mt-0.5">
                        {winnerEntry ? (
                          <>
                            <span className="text-[hsl(var(--knd-amber))] text-[11px] flex-shrink-0">★</span>
                            <span className="text-xs font-medium text-foreground truncate flex-1 min-w-0">
                              {winnerEntry.name}
                            </span>
                            <span className="text-[10px] text-muted-foreground/70 truncate max-w-[90px]">
                              {winnerEntry.commander}
                            </span>
                          </>
                        ) : t.winner && t.winner !== "—" ? (
                          <>
                            <span className="text-[hsl(var(--knd-amber))] text-[11px] flex-shrink-0">★</span>
                            <span className="text-xs font-medium text-foreground truncate flex-1 min-w-0">
                              {t.winner}
                            </span>
                          </>
                        ) : (
                          <div className="flex-1" />
                        )}
                        <div className="ml-auto flex-shrink-0 flex items-baseline gap-1 pl-2">
                          <span className="font-mono text-sm font-semibold text-primary">
                            {t.players.toLocaleString("en-US")}
                          </span>
                          <span className="text-[10px] text-muted-foreground">ppl</span>
                        </div>
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="flex-shrink-0"
                          style={{ color: "hsl(var(--knd-cyan) / 0.6)" }}
                        >
                          <path d="m9 18 6-6-6-6" />
                        </svg>
                      </div>
                    </div>
                  </Link>
                </div>
              );
            })
          )}
        </div>

        {/* Footer note */}
        <p className="mt-5 mx-0.5 text-xs text-muted-foreground font-mono">
          Source: TopDeck.gg · sample sizes ≥ 16 players · standings updated nightly.
        </p>
      </main>
    </>
  );
}
