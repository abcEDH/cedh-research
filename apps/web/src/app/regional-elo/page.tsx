import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const dynamic = "force-dynamic";

type RegionRow = {
  region_type: string;
  region_key: string;
  player_count: number;
  updated_at: string | null;
};

type LeaderboardRow = {
  region_type: string;
  region_key: string;
  player_id: string;
  player_name: string;
  topdeck_id: string | null;
  rating: number;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  rank: number;
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default async function RegionalEloPage({
  searchParams,
}: {
  searchParams?: { region?: string };
}) {
  const { data: regionsData } = await supabase
    .from("regional_elo_regions")
    .select("region_type, region_key, player_count, updated_at")
    .eq("region_type", "state")
    .order("region_key", { ascending: true });

  const regions = (regionsData ?? []) as RegionRow[];
  const selectedRegion = searchParams?.region || regions[0]?.region_key;

  const { data: leaderboardData } = await supabase
    .from("regional_elo_leaderboard")
    .select(
      "region_type, region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank"
    )
    .eq("region_type", "state")
    .eq("region_key", selectedRegion ?? "")
    .order("rating", { ascending: false })
    .limit(100);

  const leaderboard = (leaderboardData ?? []) as LeaderboardRow[];

  const updatedAt = regions.find((r) => r.region_key === selectedRegion)?.updated_at ?? null;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="space-y-4">
          <p className="text-xs uppercase tracking-[0.4em] text-[#c9a227]">Regional Elo</p>
          <h1 className="text-4xl font-semibold">State Leaderboards</h1>
          <p className="text-base text-zinc-300">
            Elo ratings recalculated within each state using only local games. Players can rank
            differently across regions based on localized metas.
          </p>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[280px_1fr]">
          <Card className="border border-[#2a2a2a] bg-[#111111]">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">Region</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <form className="space-y-3">
                <label className="text-sm text-zinc-300">Select a state</label>
                <select
                  name="region"
                  defaultValue={selectedRegion}
                  className="w-full rounded-md border border-[#2a2a2a] bg-[#0f0f0f] px-3 py-2 text-sm text-white"
                  onChange={(event) => event.currentTarget.form?.submit()}
                >
                  {regions.map((region) => (
                    <option key={region.region_key} value={region.region_key}>
                      {region.region_key} ({region.player_count})
                    </option>
                  ))}
                </select>
              </form>
              <div className="text-xs text-zinc-500">
                Updated {updatedAt ? formatDate(updatedAt) : "—"}
              </div>
            </CardContent>
          </Card>

          <Card className="border border-[#2a2a2a] bg-[#111111]">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
                Top Players
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.3em] text-zinc-500">
                    <tr>
                      <th className="py-2">Rank</th>
                      <th>Player</th>
                      <th>Elo</th>
                      <th>Games</th>
                      <th>W-D-L</th>
                      <th>Last Game</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((row) => (
                      <tr key={row.player_id} className="border-t border-[#222222]">
                        <td className="py-3 text-zinc-400">#{row.rank}</td>
                        <td className="py-3">
                          <div className="font-medium text-white">{row.player_name}</div>
                          <div className="text-xs text-zinc-500">{row.topdeck_id || "Unknown ID"}</div>
                        </td>
                        <td className="py-3 font-semibold text-[#c9a227]">
                          {Math.round(row.rating)}
                        </td>
                        <td className="py-3 text-zinc-300">{row.games_played}</td>
                        <td className="py-3 text-zinc-300">
                          {row.wins}-{row.draws}-{row.losses}
                        </td>
                        <td className="py-3 text-zinc-500">{formatDate(row.last_game_date)}</td>
                      </tr>
                    ))}
                    {leaderboard.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-sm text-zinc-500">
                          No regional Elo data yet. Run the regional Elo job to populate this leaderboard.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
