import { NextResponse } from "next/server";
import { getCachedTrapSpiceData } from "@/lib/public-data";

export async function GET() {
  return NextResponse.json(await getCachedTrapSpiceData(), {
    headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=86400" },
  });
}
