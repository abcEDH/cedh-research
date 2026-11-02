import { NextResponse } from "next/server";
import {
  getCachedTournamentPage,
  type TournamentListPeriod,
  type TournamentListSort,
  type TournamentListTier,
} from "@/lib/public-data";
import { TIER_MIN } from "@/lib/tournaments";

function enumValue<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return value && allowed.includes(value as T) ? (value as T) : fallback;
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const requestedPage = Number.parseInt(params.get("page") ?? "1", 10);
  const page = Number.isFinite(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const sort = enumValue(params.get("sort"), ["Date", "Players"] as const, "Date") as TournamentListSort;
  const tier = enumValue(params.get("tier"), Object.keys(TIER_MIN) as TournamentListTier[], "All Tiers");
  const period = enumValue(params.get("period"), ["3 Months", "6 Months", "1 Year", "All"] as const, "3 Months") as TournamentListPeriod;
  const result = await getCachedTournamentPage(page, sort, tier, period);

  return NextResponse.json(
    { ...result, page, pageSize: 20 },
    { headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" } }
  );
}
