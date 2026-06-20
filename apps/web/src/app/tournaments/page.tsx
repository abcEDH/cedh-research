import { TIER_MIN, type EventTier } from "@/lib/tournaments";
import { TournamentsList } from "./tournaments-list";

type SearchParams = Record<string, string | string[] | undefined>;
type SortOption = "Date" | "Players";
type TierOption = "All Tiers" | EventTier;
type PeriodOption = "3 Months" | "6 Months" | "1 Year" | "All";

const PERIOD_DAYS: Record<PeriodOption, number> = {
  "3 Months": 92,
  "6 Months": 183,
  "1 Year": 365,
  All: 1e9,
};

type PageProps = {
  searchParams: Promise<SearchParams>;
};

function paramValue(params: SearchParams, key: string) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}

function parseSort(params: SearchParams): SortOption {
  return paramValue(params, "sort") === "Players" ? "Players" : "Date";
}

function parseTier(params: SearchParams): TierOption {
  const value = paramValue(params, "tier");
  return value && value in TIER_MIN ? (value as TierOption) : "Gold";
}

function parsePeriod(params: SearchParams): PeriodOption {
  const value = paramValue(params, "period");
  return value && value in PERIOD_DAYS ? (value as PeriodOption) : "3 Months";
}

export default async function TournamentsPage({ searchParams }: PageProps) {
  const params = await searchParams;

  return (
    <TournamentsList
      initialSort={parseSort(params)}
      initialTier={parseTier(params)}
      initialPeriod={parsePeriod(params)}
    />
  );
}
