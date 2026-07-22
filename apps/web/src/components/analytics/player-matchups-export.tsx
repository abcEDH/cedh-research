"use client";

import { useState } from "react";

export function PlayerMatchupsExport() {
  const [playerName, setPlayerName] = useState("");
  const [format, setFormat] = useState<"csv" | "json">("csv");
  const [dataType, setDataType] = useState<"detailed" | "summary">("detailed");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      if (!playerName.trim()) {
        setError("Please enter a player name");
        setIsLoading(false);
        return;
      }

      const params = new URLSearchParams({
        player_name: playerName,
        format,
        summary_only: dataType === "summary" ? "true" : "false",
      });

      const response = await fetch(`/api/export/player-matchups?${params}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Export failed");
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get("content-disposition");
      const fileName = contentDisposition
        ? contentDisposition.split("filename=")[1].replaceAll('"', "")
        : `${playerName.replace(/\s+/g, "_")}_matchups.${format}`;

      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-950 text-white">
      <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="space-y-8">
          {/* Header */}
          <div className="space-y-4">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Player Matchup Analysis
            </h1>
            <p className="text-lg text-slate-300">
              Export and analyze head-to-head matchup data for any player in the database.
            </p>
          </div>

          {/* Export Tool */}
          <div className="rounded-lg border border-slate-700 bg-slate-800 p-8">
            <h2 className="mb-6 text-2xl font-semibold">Export Data</h2>

            <form onSubmit={handleExport} className="space-y-6">
              {/* Player Search */}
              <div>
                <label htmlFor="player" className="mb-2 block text-sm font-medium">
                  Player Name
                </label>
                <input
                  id="player"
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  placeholder="e.g., Jason Doan, Dexter Idzikowski, Jordan Callister"
                  className="w-full rounded-lg border border-slate-600 bg-slate-700 px-4 py-2 text-white placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                  disabled={isLoading}
                />
              </div>

              {/* Format Selection */}
              <div>
                <label className="mb-3 block text-sm font-medium">Format</label>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
                  <label className="flex items-center space-x-3">
                    <input
                      type="radio"
                      name="format"
                      value="csv"
                      checked={format === "csv"}
                      onChange={(e) => setFormat(e.target.value as "csv")}
                      disabled={isLoading}
                      className="h-4 w-4"
                    />
                    <span>CSV (Spreadsheet)</span>
                  </label>
                  <label className="flex items-center space-x-3">
                    <input
                      type="radio"
                      name="format"
                      value="json"
                      checked={format === "json"}
                      onChange={(e) => setFormat(e.target.value as "json")}
                      disabled={isLoading}
                      className="h-4 w-4"
                    />
                    <span>JSON (Raw Data)</span>
                  </label>
                </div>
              </div>

              {/* Data Type Selection */}
              <div>
                <label className="mb-3 block text-sm font-medium">Data Type</label>
                <div className="space-y-3">
                  <label className="flex items-center space-x-3">
                    <input
                      type="radio"
                      name="data_type"
                      value="detailed"
                      checked={dataType === "detailed"}
                      onChange={(e) => setDataType(e.target.value as "detailed")}
                      disabled={isLoading}
                      className="h-4 w-4"
                    />
                    <div className="flex-1">
                      <span>Detailed (Game-by-Game)</span>
                      <p className="text-xs text-slate-400">
                        Every game result with date, tournament, opponent
                      </p>
                    </div>
                  </label>
                  <label className="flex items-center space-x-3">
                    <input
                      type="radio"
                      name="data_type"
                      value="summary"
                      checked={dataType === "summary"}
                      onChange={(e) => setDataType(e.target.value as "summary")}
                      disabled={isLoading}
                      className="h-4 w-4"
                    />
                    <div className="flex-1">
                      <span>Summary (Aggregated)</span>
                      <p className="text-xs text-slate-400">
                        Win/loss/draw counts and win% by opponent
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="rounded-lg border border-red-500 bg-red-900/20 p-4">
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}

              {/* Export Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full rounded-lg bg-cyan-600 px-6 py-3 font-semibold text-white hover:bg-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Exporting..." : "Export Data"}
              </button>
            </form>
          </div>

          {/* Info Section */}
          <div className="space-y-6 rounded-lg border border-slate-700 bg-slate-800 p-8">
            <div>
              <h3 className="mb-3 text-lg font-semibold">About This Tool</h3>
              <p className="text-slate-300">
                Export comprehensive head-to-head matchup statistics for competitive analysis.
                Data includes all games from tournaments tracked in our database.
              </p>
            </div>

            <div>
              <h3 className="mb-3 text-lg font-semibold">CSV Format</h3>
              <div className="space-y-2 text-sm text-slate-300">
                <p>
                  <strong>Detailed:</strong> date, tournament, player, player_result, opponent,
                  opponent_topdeck_id
                </p>
                <p>
                  <strong>Summary:</strong> opponent, opponent_topdeck_id, games, wins, losses,
                  draws, win_pct
                </p>
              </div>
            </div>

            <div>
              <h3 className="mb-3 text-lg font-semibold">Examples</h3>
              <ul className="space-y-2 text-sm text-slate-300">
                <li>
                  Download all games for{" "}
                  <code className="rounded bg-slate-700 px-2 py-1">Jason Doan</code>
                </li>
                <li>
                  Export summary stats for{" "}
                  <code className="rounded bg-slate-700 px-2 py-1">CriticalEDH</code>
                </li>
                <li>
                  Analyze matchups with{" "}
                  <code className="rounded bg-slate-700 px-2 py-1">Dexter Idzikowski</code>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
