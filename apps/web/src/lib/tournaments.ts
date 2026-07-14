export type EventTier = "Diamond" | "Platinum" | "Gold" | "Silver" | "Bronze";

export interface TopCutPlayer {
  name: string;
  commander: string;
  colors: string[];
  standing: number;
}

export interface TournamentSummary {
  name: string;
  date: string;
  players: number;
  winner: string;
  slug: string;
  topdeckTid: string;
  tier: EventTier;
  hasDetail: boolean;
  topCut?: TopCutPlayer[];
}

export interface Standing {
  rank: number;
  player: string;
  team: string;
  commander: string;
  colors: string;
  wins: number;
  losses: number;
  draws: number;
  points: number;
  cut: "Champion" | "Top 2" | "Top 4" | "Top 10" | "Top 16" | "Top 32" | "Top 40" | "—";
  decklistUrl?: string | null;
  topdeckId?: string | null;
}

export interface RoundNarrative {
  stageNum: string;
  stageLabel: string;
  roundRange: string;
  isCut: boolean;
  isChamp: boolean;
  stat: string;
  statLabel: string;
  narrative: string;
  spotlight: string;
  spotlightIcon: string;
}

export interface CommanderDistEntry {
  name: string;
  colors: string;
  cutCount: number;
  missCount: number;
  totalCount: number;
  conversion: number;
}

export interface PodPlayer {
  name: string;
  cmd: string;
  colors: string;
  isWinner: boolean;
}

export interface PodData {
  num: number;
  players: PodPlayer[];
}

export interface TournamentDetail extends Omit<TournamentSummary, "hasDetail" | "tier"> {
  rounds: number;
  cutSize: number;
  winnerCmd: string;
  winnerColors: string;
  source: string;
  bracketAvailable?: boolean;
  standings: Standing[];
  narratives: RoundNarrative[];
  topCutDist: CommanderDistEntry[];
  overallDist: CommanderDistEntry[];
  bracket: {
    swiss: { topSeed: string; topRecord: string };
    t40: PodData[];
    t16: PodData[];
    t4: { players: PodPlayer[] };
  };
}

export const TIER_MIN: Record<"All Tiers" | EventTier, number> = {
  "All Tiers": 0,
  Diamond: 250,
  Platinum: 100,
  Gold: 50,
  Silver: 30,
  Bronze: 16,
};

export function assignEventTier(players: number): EventTier {
  if (players >= 250) return "Diamond";
  if (players >= 100) return "Platinum";
  if (players >= 50) return "Gold";
  if (players >= 30) return "Silver";
  return "Bronze";
}

export function colorLetters(colors: string): string[] {
  return colors.split("").filter(Boolean);
}

export function distributionFromStandings(standings: Standing[]): { topCutDist: CommanderDistEntry[]; overallDist: CommanderDistEntry[] } {
  const counts = new Map<string, { colors: string; cutCount: number; missCount: number }>();

  for (const row of standings) {
    const current = counts.get(row.commander) ?? { colors: row.colors, cutCount: 0, missCount: 0 };
    if (row.cut !== "—") {
      current.cutCount += 1;
    } else {
      current.missCount += 1;
    }
    counts.set(row.commander, current);
  }

  const entries: CommanderDistEntry[] = [...counts.entries()].map(([name, value]) => {
    const totalCount = value.cutCount + value.missCount;
    return {
      name,
      colors: value.colors,
      cutCount: value.cutCount,
      missCount: value.missCount,
      totalCount,
      conversion: Number(((value.cutCount / totalCount) * 100).toFixed(1)),
    };
  });

  const topCutDist = [...entries]
    .sort((a, b) => {
      if (b.cutCount !== a.cutCount) return b.cutCount - a.cutCount;
      if (a.cutCount > 0) return a.totalCount - b.totalCount; // High conversion: 1/1 before 1/15
      return b.totalCount - a.totalCount; // Missed cuts: 0/15 before 0/1
    })
    .slice(0, 30);

  const overallDist = [...entries]
    .sort((a, b) => b.totalCount - a.totalCount || b.cutCount - a.cutCount)
    .slice(0, 10);

  return { topCutDist, overallDist };
}

