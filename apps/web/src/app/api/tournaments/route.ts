import { NextResponse } from "next/server";
import { getCachedTournamentSummaries } from "@/lib/public-data";

export async function GET() {
  return NextResponse.json(
    { tournaments: await getCachedTournamentSummaries() },
    { headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" } }
  );
}
