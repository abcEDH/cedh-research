import { StatCard } from "@/components/commanders/stat-card";
import type { CommanderStat } from "@/lib/commanders/fetchers";

const BASELINE_POINTS_PER_GAME = 1.25;

export function CommanderStatGrid({
  commander,
  winRateValue,
  pointsPerGame,
  resiliencyRate,
  firstPlaceFinishes,
}: {
  commander: CommanderStat;
  winRateValue: number;
  pointsPerGame: number;
  resiliencyRate: number;
  firstPlaceFinishes: number;
}) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6 mb-8">
      <StatCard label="Total Entries" value={commander.total_entries.toLocaleString()} tone="neutral" tooltip="Number of tournament entries for this commander." />
      <StatCard label="Tournaments" value={commander.tournaments_played.toString()} tone="neutral" tooltip="Unique tournaments where this commander was played." />
      <StatCard label="Win Rate" value={`${(winRateValue * 100).toFixed(1)}%`} tone={winRateValue > 0.25 ? "primary" : "neutral"} tooltip="Wins divided by total games. Baseline in 4-player pods is 25%." />
      <StatCard label="Points / Game" value={pointsPerGame.toFixed(2)} tone={pointsPerGame > BASELINE_POINTS_PER_GAME ? "primary" : "neutral"} tooltip="Weighted average points per game: win=5, draw=1, loss=0." />
      <StatCard label="Top 16 / Top 10 / Top 4 Rate" value={`${(parseFloat(commander.conversion_rate_top_16) * 100).toFixed(1)}%`} tone="neutral" tooltip="Share of entries reaching the top bracket. Under 64 players, events may have a Top 10, and for 34 players or fewer we only count Top 4 finishes." />
      <StatCard label="Top Cut Conversion" value={`${(parseFloat(commander.conversion_rate_top_cut) * 100).toFixed(1)}%`} tone="neutral" tooltip="Share of entries reaching the event's top cut bracket." />
      <StatCard label="1st Place Finishes" value={firstPlaceFinishes.toLocaleString()} tone="neutral" tooltip="Count of tournament entries finishing in 1st place." />
      <StatCard label="Resiliency" value={`${(resiliencyRate * 100).toFixed(1)}%`} tone={resiliencyRate > 0.25 ? "primary" : "neutral"} tooltip="Win + draw rate. Higher means fewer losses." />
      <StatCard label="Total Wins" value={commander.total_wins.toLocaleString()} tone="neutral" tooltip="Total wins across all recorded games." />
      <StatCard label="W/L/D" value={`${commander.total_wins}/${commander.total_losses}/${commander.total_draws}`} tone="neutral" tooltip="Wins, losses, and draws recorded for this commander." />
    </div>
  );
}
