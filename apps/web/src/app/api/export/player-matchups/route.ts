import { NextRequest, NextResponse } from "next/server";

/**
 * API route to export player matchup data as CSV.
 * Query params:
 *   - player_name: Name or part of name to search for
 *   - format: 'csv' or 'json' (default: csv)
 *   - summary_only: true for aggregated stats only
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const playerName = searchParams.get("player_name");
  const format = searchParams.get("format") || "csv";
  const summaryOnly = searchParams.get("summary_only") === "true";

  if (!playerName) {
    return NextResponse.json(
      { error: "player_name query parameter is required" },
      { status: 400 }
    );
  }

  try {
    // Import the export function from backend
    const { exportPlayerMatchups, exportMatchupSummary } = await import(
      "@/../../packages/backend/src/export_player_matchups"
    );

    let result;

    if (summaryOnly) {
      result = await exportMatchupSummary(playerName, format);
    } else {
      result = await exportPlayerMatchups(playerName, format);
    }

    if (!result) {
      return NextResponse.json(
        { error: `Player "${playerName}" not found` },
        { status: 404 }
      );
    }

    // Return as attachment
    const fileName =
      format === "csv"
        ? `${playerName.replace(/\s+/g, "_")}_matchups.csv`
        : `${playerName.replace(/\s+/g, "_")}_matchups.json`;

    return new NextResponse(result, {
      status: 200,
      headers: {
        "Content-Type": format === "csv" ? "text/csv" : "application/json",
        "Content-Disposition": `attachment; filename="${fileName}"`,
      },
    });
  } catch (error) {
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
