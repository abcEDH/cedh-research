import { NextRequest, NextResponse } from "next/server";
import { getCachedPublicSearch } from "@/lib/public-data";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim().slice(0, 80) ?? "";
  if (query.length < 2) return NextResponse.json({ results: [] });

  const results = await getCachedPublicSearch(query);
  return NextResponse.json(
    { results },
    { headers: { "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600" } }
  );
}
