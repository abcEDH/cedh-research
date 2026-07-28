export const DEFAULT_MISSING_TOPDECK_ELO = 1500;

export type TopdeckEloSummary = {
  average: number | null;
  defaultElo: number;
  missingCount: number;
  publishedCount: number;
  totalPlayers: number;
};

export function buildTopdeckEloSummary(
  topdeckIds: string[],
  eloByTopdeckId: Map<string, number>,
  defaultElo = DEFAULT_MISSING_TOPDECK_ELO
): TopdeckEloSummary {
  if (topdeckIds.length === 0) {
    return {
      average: null,
      defaultElo,
      missingCount: 0,
      publishedCount: 0,
      totalPlayers: 0,
    };
  }

  let totalElo = 0;
  let publishedCount = 0;

  for (const topdeckId of topdeckIds) {
    const publishedElo = topdeckId ? eloByTopdeckId.get(topdeckId) : undefined;
    if (typeof publishedElo === "number" && Number.isFinite(publishedElo)) {
      totalElo += publishedElo;
      publishedCount += 1;
    } else {
      totalElo += defaultElo;
    }
  }

  return {
    average: totalElo / topdeckIds.length,
    defaultElo,
    missingCount: topdeckIds.length - publishedCount,
    publishedCount,
    totalPlayers: topdeckIds.length,
  };
}
