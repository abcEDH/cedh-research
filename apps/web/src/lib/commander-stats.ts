export function mean(values: number[]): number | null {
  const finite = values.filter((v) => Number.isFinite(v));
  if (finite.length === 0) return null;
  return finite.reduce((sum, v) => sum + v, 0) / finite.length;
}

export function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export type TrendAggregateInput = {
  entries: number;
  wins: number;
  losses: number;
  draws: number;
};

export type TrendAggregateOutput = {
  entries: number;
  winRate: number | null;
  pointsPerGame: number | null;
};

// Periods can have entries logged before per-round games are ingested, leaving
// wins/losses/draws all zero. Returning null for those metrics tells charts to
// break the line at the gap rather than plotting a misleading 0%.
export function aggregateTrendPoint(values: TrendAggregateInput): TrendAggregateOutput {
  const games = values.wins + values.losses + values.draws;
  if (games <= 0) {
    return { entries: values.entries, winRate: null, pointsPerGame: null };
  }
  return {
    entries: values.entries,
    winRate: (values.wins / games) * 100,
    pointsPerGame: (values.wins * 5 + values.draws) / games,
  };
}
