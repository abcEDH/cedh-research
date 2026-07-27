export const ELO_TIERS = ["ranking", "local", "all"] as const;

export type EloTier = (typeof ELO_TIERS)[number];

export type EloTierInfo = {
  key: EloTier;
  label: string;
  description: string;
};

export const ELO_TIER_INFO: Record<EloTier, EloTierInfo> = {
  ranking: {
    key: "ranking",
    label: "Tier 1: Ranking ELO",
    description: "30+ player tournaments; leagues and casual events excluded.",
  },
  local: {
    key: "local",
    label: "Tier 2: Local / Regional ELO",
    description: "10+ player finalized tournaments, including leagues; obvious casual events excluded.",
  },
  all: {
    key: "all",
    label: "Tier 3: All Games",
    description: "Every dated game currently available in the research dataset.",
  },
};

export function parseEloTier(value: string | null | undefined, fallback: EloTier = "ranking"): EloTier {
  return value && ELO_TIERS.includes(value as EloTier) ? (value as EloTier) : fallback;
}

export type TierTournament = {
  name: string;
  topdeck_tid?: string | null;
  player_count?: number | null;
  start_date?: string | null;
};

function isObviousCasualEvent(name: string) {
  return /casual|exhibition|\bfun\b/i.test(name);
}

function isLeagueEvent(tournament: TierTournament) {
  return /league/i.test(`${tournament.topdeck_tid ?? ""} ${tournament.name}`);
}

function isFinalized(tournament: TierTournament) {
  return Boolean(tournament.start_date);
}

export function isEloTierEligible(
  tier: EloTier,
  tournament: TierTournament | null | undefined,
  gameStatus?: string | null
) {
  if (!tournament || !isFinalized(tournament)) return false;
  if (tier === "all") return true;
  if (new Date(tournament.start_date as string).getTime() > Date.now()) return false;
  if (gameStatus && !["completed", "complete", "done"].includes(gameStatus.toLowerCase())) {
    return false;
  }
  if (isObviousCasualEvent(tournament.name)) return false;
  if (tier === "local") return (tournament.player_count ?? 0) >= 10;
  return (
    (tournament.player_count ?? 0) >= 30 &&
    !isLeagueEvent(tournament)
  );
}
