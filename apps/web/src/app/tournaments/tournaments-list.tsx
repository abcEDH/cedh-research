"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TIER_MIN, type EventTier, type TournamentSummary } from "@/lib/tournaments";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

function relTime(days: number): string {
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 14) return "last week";
  if (days < 31) return `${Math.round(days / 7)} weeks ago`;
  if (days < 365) return `${Math.round(days / 30)} months ago`;
  return "over a year ago";
}

// ---- FilterSelect ----
interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}

function FilterSelect({ label, value, onChange, options }: FilterSelectProps) {
  return (
    <div className="flex min-w-[132px] flex-1 flex-col gap-1.5 sm:flex-none">
      <span className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
        {label}
      </span>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="min-h-11 w-full border-border bg-muted/55 hover:border-primary/50 sm:min-h-0 sm:w-fit sm:min-w-[132px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

// ---- Page ----
export function TournamentsList({ initialSort, initialTier, initialPeriod }: TournamentsListProps) {
  const [sortBy, setSortBy] = useState<SortOption>(initialSort);
  const [tierFilter, setTierFilter] = useState<TierOption>(initialTier);
  const [period, setPeriod] = useState<PeriodOption>(initialPeriod);
  const [events, setEvents] = useState<TournamentSummary[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      const response = await fetch("/api/tournaments");
      const payload = (await response.json()) as { tournaments?: TournamentSummary[] };
      const loadedEvents = response.ok ? payload.tournaments ?? [] : [];

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

  // ---- Select option builders ----
  const sortOptions = (["Date", "Players"] as SortOption[]).map((o) => ({
    value: o,
    label: o,
  }));

  const tierOptions = (["All Tiers", "Diamond", "Platinum", "Gold", "Silver", "Bronze"] as TierOption[]).map((o) => ({
    value: o,
    label: o === "All Tiers" ? "All Tiers" : `${o} · ${TIER_MIN[o]}+`,
  }));

  const periodOptions = (["3 Months", "6 Months", "1 Year", "All"] as PeriodOption[]).map((o) => ({
    value: o,
    label: o,
  }));

  return (
    <>
      <main className="mx-auto max-w-5xl px-4 py-8 pb-16 sm:px-6 sm:py-10 sm:pb-20">
        {/* Page header */}
        <div className="mb-7">
          <div
            className="mb-2.5 text-xs font-medium uppercase tracking-[0.2em] font-mono"
            style={{ color: "hsl(var(--knd-cyan))" }}
          >
            TOURNAMENTS
          </div>
          <h1 className="m-0 text-3xl font-semibold tracking-tight sm:text-4xl">
            Latest Tournaments
          </h1>
          <p className="mt-2.5 text-[15px] leading-relaxed text-muted-foreground max-w-xl">
            Recent competitive events, newest first. Filter by recency and event tier. Click any event for full standings, round story, and bracket.
          </p>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-end gap-3 px-4 py-4 mb-4 knd-panel sm:gap-5 sm:px-5">
          <FilterSelect
            label="Sort By"
            value={sortBy}
            onChange={(v) => {
              setSortBy(v as SortOption);
              setFilter("sort", v);
            }}
            options={sortOptions}
          />
          <FilterSelect
            label="Event Tier"
            value={tierFilter}
            onChange={(v) => {
              setTierFilter(v as TierOption);
              setFilter("tier", v);
            }}
            options={tierOptions}
          />
          <FilterSelect
            label="Time Period"
            value={period}
            onChange={(v) => {
              setPeriod(v as PeriodOption);
              setFilter("period", v);
            }}
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

              return (
                <div
                  key={t.slug}
                  className="group flex items-center gap-3 px-4 py-4 transition-colors hover:bg-accent/25 sm:gap-4 sm:px-5"
                  style={{
                    borderBottom: i < items.length - 1 ? "1px solid var(--border)" : "none",
                    cursor: "pointer",
                  }}
                >
                  <Link
                    href={href}
                    className="flex-1 min-w-0 flex items-center gap-3 no-underline sm:gap-4"
                  >
                    {/* Date column */}
                    <div className="flex flex-col items-center justify-center w-12 flex-shrink-0 border-r border-border pr-3 sm:w-14 sm:pr-4">
                      <span className="text-[11px] tracking-[0.16em] uppercase text-muted-foreground font-medium">
                        {MONTHS[t.d.getMonth()]}
                      </span>
                      <span className="font-mono text-[22px] font-semibold leading-none">
                        {t.d.getDate()}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {t.d.getFullYear()}
                      </span>
                    </div>

                    {/* Name + winner */}
                    <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                      <div className="flex items-center gap-3">
                        <span className="text-[15px] font-semibold leading-snug text-foreground truncate sm:text-[17px]">
                          {t.name}
                        </span>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {relTime(t.days)}
                        </span>
                      </div>

                      {/* Player count moves into a sub-line below sm: */}
                      <span className="font-mono text-[11px] text-muted-foreground sm:hidden">
                        {t.players.toLocaleString("en-US")} players
                      </span>

                      {/* Top 4 Display — winner only below sm:, full top cut above */}
                      {t.topCut && t.topCut.length > 0 ? (
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                          {t.topCut.map((cut, ci) => (
                            <div key={`${cut.standing}-${cut.name}-${ci}`} className={`items-center gap-1.5 min-w-0 max-w-[200px] ${ci === 0 ? "flex" : "hidden sm:flex"}`}>
                              <span className={`text-[10px] font-mono font-bold flex-shrink-0 ${cut.standing === 1 ? 'text-[hsl(var(--knd-amber))]' : 'text-muted-foreground'}`}>
                                {cut.standing === 1 ? '★' : `${cut.standing}`}
                              </span>
                              <div className="flex flex-col min-w-0">
                                <span className={`text-xs truncate ${cut.standing === 1 ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                                  {cut.name}
                                </span>
                                <span className="text-[10px] text-muted-foreground/70 truncate" title={cut.commander}>
                                  {cut.commander}
                                </span>
                              </div>
                            </div>
                          ))}
                          {t.topCut.length > 1 && (
                            <span className="text-[10px] font-mono text-muted-foreground/70 sm:hidden">
                              +{t.topCut.length - 1} top cut
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                          <span className="inline-flex items-center gap-1.5">
                            <svg
                              width="13"
                              height="13"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              style={{ color: "hsl(var(--knd-cyan))", flexShrink: 0 }}
                            >
                              <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                              <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                              <path d="M4 22h16" />
                              <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
                              <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
                              <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
                            </svg>
                            <span className="text-foreground">{t.winner}</span>
                          </span>
                        </span>
                      )}
                    </div>

                    {/* Tier badge */}
                    {ts && (
                      <span
                        className="flex-shrink-0 whitespace-nowrap"
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

                    {/* Player count (column above sm:, sub-line below) */}
                    <div className="hidden flex-col items-end flex-shrink-0 gap-0 sm:flex">
                      <span className="font-mono text-xl font-semibold text-primary leading-none">
                        {t.players.toLocaleString("en-US")}
                      </span>
                      <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-medium">
                        Players
                      </span>
                    </div>

                    {/* Chevron */}
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="hidden flex-shrink-0 sm:block"
                      style={{
                        color: "hsl(var(--knd-cyan) / 0.6)",
                      }}
                    >
                      <path d="m9 18 6-6-6-6" />
                    </svg>
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
