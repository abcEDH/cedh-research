import { NextRequest, NextResponse } from "next/server";
import {
  AmbiguousPlayerMatchError,
  exportPlayerMatchups,
  exportMatchupSummary,
} from "@/lib/exports/player-matchups";
import { ELO_TIER_INFO, parseEloTier } from "@/lib/elo-tiers";

/**
 * API route to export player matchup data as JSON.
 * Query params:
 *   - player_name: Name or part of name to search for
 *   - format: 'json' (optional; JSON is the only supported format)
 *   - summary_only: true for aggregated stats only
 *   - tier: 'ranking', 'local', or 'all' (default: ranking)
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const playerName = searchParams.get("player_name");
  const requestedFormat = searchParams.get("format");
  if (requestedFormat && requestedFormat !== "json") {
    return NextResponse.json({ error: "format must be json" }, { status: 400 });
  }
  const summaryOnly = searchParams.get("summary_only") === "true";
  const tier = parseEloTier(searchParams.get("tier"));

  if (!playerName) {
    return NextResponse.json(
      { error: "player_name query parameter is required" },
      { status: 400 }
    );
  }

  try {
    let result;

    if (summaryOnly) {
      result = await exportMatchupSummary(playerName, tier);
    } else {
      result = await exportPlayerMatchups(playerName, tier);
    }

    if (!result) {
      return NextResponse.json(
        { error: `Player "${playerName}" not found` },
        { status: 404 }
      );
    }

    // Return as attachment
    const fileName = `${playerName.replace(/\s+/g, "_")}_${tier}_matchups.json`;
    const asciiFileName = fileName
      .replace(/[^\x20-\x7e]/g, "_")
      .replace(/[\\"/]/g, "_");
    const encodedFileName = encodeURIComponent(fileName).replace(/['()]/g, (character) =>
      `%${character.charCodeAt(0).toString(16).toUpperCase()}`
    );

    return new NextResponse(result, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": `attachment; filename="${asciiFileName}"; filename*=UTF-8''${encodedFileName}`,
        "X-Elo-Tier": tier,
        "X-Elo-Tier-Label": ELO_TIER_INFO[tier].label,
      },
    });
  } catch (error) {
    if (error instanceof AmbiguousPlayerMatchError) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    console.error("Error exporting player matchups:", error);
    return NextResponse.json(
      { error: "Failed to export player data" },
      { status: 500 }
    );
  }
}

/**
 * List available players for export
 */
export async function HEAD(request: NextRequest) {
  return NextResponse.json({ status: "ok" });
}

// Keep the existing GET contract while accepting POST for clients that treat
// exports as a command rather than a cacheable read.
export async function POST(request: NextRequest) {
  return GET(request);
}
