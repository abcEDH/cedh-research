import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

function escapeLikePattern(value: string) {
  return value.replace(/\\/g, "\\\\").replace(/%/g, "\\%").replace(/_/g, "\\_");
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (query.length < 2) return NextResponse.json({ players: [] });

  const { data, error } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .not("topdeck_id", "is", null)
    .ilike("name", `%${escapeLikePattern(query)}%`)
    .order("name", { ascending: true })
    .limit(20);

  if (error) {
    console.error("Error searching players:", error);
    return NextResponse.json({ error: "Failed to search players" }, { status: 500 });
  }

  return NextResponse.json({ players: data ?? [] });
}
