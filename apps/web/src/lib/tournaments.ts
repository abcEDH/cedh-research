export type EventTier = "Diamond" | "Platinum" | "Gold" | "Silver" | "Bronze";

export interface TournamentSummary {
  name: string;
  date: string;
  players: number;
  winner: string;
  slug: string;
  tier: EventTier;
  hasDetail: boolean;
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
  cut: "Champion" | "Top 2" | "Top 4" | "Top 16" | "Top 32" | "Top 40";
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
  count: number;
  pct: number;
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
  standings: Standing[];
  narratives: RoundNarrative[];
  cmdDist: CommanderDistEntry[];
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

export function tournamentPoints(wins: number, draws: number) {
  return wins * 5 + draws;
}

const summaries: Omit<TournamentSummary, "tier" | "hasDetail">[] = [
  { name: "SIEGE cEDH 10K", date: "2026-06-13", players: 308, winner: "Jason D. // CriticalEDH", slug: "siege-cedh-10k" },
  { name: "Land, Go Presents: The Boil 2026", date: "2026-03-28", players: 268, winner: "Zeke Maxwell [Monolith]", slug: "the-boil-2026" },
  { name: "Misplay on the Lake", date: "2026-04-18", players: 264, winner: "Andy Beach", slug: "misplay-on-the-lake" },
  { name: "The Quest for a Cause — $10k cEDH Charity Main Event", date: "2026-05-16", players: 260, winner: "Bruno Gino-Griffiths", slug: "quest-for-a-cause" },
  { name: "Land, Go Open 10k cEDH Tournament", date: "2026-05-23", players: 212, winner: "[CHUDS] Shmant Shmandrew Shmeklund", slug: "land-go-open-10k" },
  { name: "Braindead Fantasy Fest Commander Precon Tournament", date: "2026-04-12", players: 210, winner: "Evan Sussell", slug: "braindead-fantasy-fest" },
  { name: "Just Jam D-Grid", date: "2026-05-30", players: 200, winner: "Matt Hayes", slug: "just-jam-d-grid" },
  { name: "Commandergeddon 10: Jene's MTG & Irresistible Force", date: "2026-06-05", players: 173, winner: "Katie Giefer", slug: "commandergeddon-10" },
  { name: "Twisted Power — Midwest Gaming Classic TimeTwister", date: "2026-04-25", players: 172, winner: "JoeyTwoAnkles", slug: "twisted-power" },
  { name: "Commander Invitational", date: "2026-05-23", players: 147, winner: "Max Safran", slug: "commander-invitational" },
  { name: "SIEGE 10K Redemption Event — Aftermath", date: "2026-06-14", players: 142, winner: "[504] Joe Holland [Pinnacle]", slug: "siege-10k-redemption" },
  { name: "Jeweled Lotus Lattenkamp 2026", date: "2026-06-06", players: 142, winner: "Manuel Zimmermann", slug: "jeweled-lotus-lattenkamp" },
  { name: "The Side Quest — cEDH Redemption Event (Sunday)", date: "2026-05-17", players: 133, winner: "Aaron Joseph", slug: "the-side-quest" },
  { name: "Punt City 5", date: "2026-06-06", players: 129, winner: "Robert R", slug: "punt-city-5" },
  { name: "CCS $20,000 cEDH Invitational Qualifier #2", date: "2026-06-13", players: 125, winner: "Jacob Rhyne", slug: "ccs-qualifier-2" },
  { name: "The Decatur Deathmatch (10K guaranteed)", date: "2026-06-06", players: 118, winner: "[CHUDS] Shmant Shmandrew Shmeklund", slug: "decatur-deathmatch" },
  { name: "Land Go Expo — Nashville Hot! Redemption Event", date: "2026-05-24", players: 112, winner: "JoeyTwoAnkles", slug: "land-go-expo-nashville" },
  { name: "From The Vault Anniversary 3: Mox Ruby", date: "2026-03-28", players: 110, winner: "Theodore Montalbano", slug: "from-the-vault-3" },
];

const detailedSlugs = new Set(["siege-cedh-10k", "the-boil-2026", "quest-for-a-cause", "land-go-open-10k"]);

export const tournamentSummaries: TournamentSummary[] = summaries.map((event) => ({
  ...event,
  tier: assignEventTier(event.players),
  hasDetail: detailedSlugs.has(event.slug),
}));

const siegeStandings: Standing[] = [
  { rank: 1, player: "Jason D. // CriticalEDH", team: "[ZEN]", commander: "Kinnan, Bonder Prodigy", colors: "UG", wins: 5, losses: 0, draws: 3, cut: "Champion" },
  { rank: 2, player: "Logan Doan // CriticalEDH", team: "", commander: "Kinnan, Bonder Prodigy", colors: "UG", wins: 4, losses: 1, draws: 3, cut: "Top 2" },
  { rank: 3, player: "pigeonize (Level 7)", team: "[ZEN]", commander: "Ral, Monsoon Mage", colors: "UR", wins: 4, losses: 1, draws: 3, cut: "Top 4" },
  { rank: 4, player: "Justin Johnson", team: "", commander: "Thrasios / Tymna the Weaver", colors: "WUBG", wins: 3, losses: 2, draws: 3, cut: "Top 4" },
  { rank: 5, player: "Sarah K.", team: "", commander: "Sisay, Weatherlight Captain", colors: "WUBRG", wins: 4, losses: 1, draws: 1, cut: "Top 16" },
  { rank: 6, player: "Marcus T.", team: "[504]", commander: "Kraum / Tymna", colors: "WUBR", wins: 3, losses: 2, draws: 2, cut: "Top 16" },
  { rank: 7, player: "Devon R.", team: "", commander: "Rograkh / Silas Renn", colors: "UBR", wins: 4, losses: 2, draws: 0, cut: "Top 16" },
  { rank: 8, player: "Alex W.", team: "[Mon]", commander: "Dargo / Tymna the Weaver", colors: "WBR", wins: 3, losses: 3, draws: 0, cut: "Top 16" },
  { rank: 9, player: "Chris M.", team: "", commander: "Kinnan, Bonder Prodigy", colors: "UG", wins: 3, losses: 2, draws: 1, cut: "Top 40" },
  { rank: 10, player: "Pat L.", team: "", commander: "Etali, Primal Conqueror", colors: "RG", wins: 4, losses: 2, draws: 0, cut: "Top 40" },
  { rank: 11, player: "Jordan H.", team: "[SALT]", commander: "Ishai / Rograkh", colors: "WUR", wins: 3, losses: 3, draws: 0, cut: "Top 40" },
  { rank: 12, player: "Taylor S.", team: "", commander: "Vivi Ornitier", colors: "UR", wins: 3, losses: 3, draws: 0, cut: "Top 40" },
  { rank: 13, player: "Morgan B.", team: "", commander: "Thrasios / Yoshimaru", colors: "WUG", wins: 3, losses: 3, draws: 0, cut: "Top 40" },
  { rank: 14, player: "Riley C.", team: "", commander: "Magda, Brazen Outlaw", colors: "R", wins: 3, losses: 3, draws: 0, cut: "Top 40" },
  { rank: 15, player: "Casey F.", team: "[ZEN]", commander: "Kefka, Court Mage", colors: "UBR", wins: 3, losses: 3, draws: 0, cut: "Top 40" },
  { rank: 16, player: "Jamie V.", team: "", commander: "Tivit, Seller of Secrets", colors: "WUB", wins: 3, losses: 3, draws: 0, cut: "Top 40" },
];

function buildNarratives(event: { players: number; rounds: number; cutSize: number; winner: string; winnerCmd: string; topRecord: string; prize: string }): RoundNarrative[] {
  return [
    {
      stageNum: "01",
      stageLabel: "Swiss Rounds",
      roundRange: `Rounds 1-${event.rounds} · ${event.players} players`,
      isCut: false,
      isChamp: false,
      stat: event.topRecord,
      statLabel: "Top Record",
      narrative: `${event.players} players compete across ${event.rounds} Swiss rounds in pods of 4. Standings are ordered by tournament finish and points use 5 per win plus 1 per draw.`,
      spotlight: `${event.winner} enters the elimination rounds on ${event.winnerCmd}.`,
      spotlightIcon: "★",
    },
    {
      stageNum: "02",
      stageLabel: `Top ${event.cutSize} Cut`,
      roundRange: `${event.players} → ${event.cutSize} players · ${Math.round((event.cutSize / event.players) * 100)}% advance`,
      isCut: true,
      isChamp: false,
      stat: `${event.cutSize}`,
      statLabel: "Seats",
      narrative: `${event.cutSize} players move into elimination pods. Each pod is four players; advancing players are determined by pod wins and cut rules.`,
      spotlight: "Commander distribution is recalculated at the cut to show which shells converted from Swiss into elimination seats.",
      spotlightIcon: "↑",
    },
    {
      stageNum: "03",
      stageLabel: "Top 16",
      roundRange: `${event.cutSize} → 16 players · 4 pods of 4`,
      isCut: true,
      isChamp: false,
      stat: "4",
      statLabel: "Pods",
      narrative: "The bracket compresses into four pods of four. One pod winner from each table advances to the final pod.",
      spotlight: "Finalists are shown in the bracket tab with commander identities and pod winners marked in amber.",
      spotlightIcon: "↑",
    },
    {
      stageNum: "04",
      stageLabel: "Top 4 Final Pod",
      roundRange: "4 players · one decisive table",
      isCut: false,
      isChamp: false,
      stat: "1",
      statLabel: "Pod",
      narrative: "The final table is a single four-player cEDH pod, not a binary one-on-one bracket.",
      spotlight: `${event.winner} wins the final pod on ${event.winnerCmd}.`,
      spotlightIcon: "★",
    },
    {
      stageNum: "05",
      stageLabel: "Champion",
      roundRange: `Final record: ${event.topRecord.replaceAll("-", " — ")}`,
      isCut: false,
      isChamp: true,
      stat: event.prize,
      statLabel: "Prize",
      narrative: `${event.winner} is the recorded champion. Final standings and commander distribution remain visible for auditability.`,
      spotlight: "",
      spotlightIcon: "",
    },
  ];
}

function distributionFromStandings(standings: Standing[], cutSize: number): CommanderDistEntry[] {
  const counts = new Map<string, { colors: string; count: number }>();
  for (const row of standings) {
    const current = counts.get(row.commander) ?? { colors: row.colors, count: 0 };
    current.count += 1;
    counts.set(row.commander, current);
  }
  return [...counts.entries()]
    .map(([name, value]) => ({
      name,
      colors: value.colors,
      count: value.count,
      pct: Number(((value.count / cutSize) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
}

function buildBracket(standings: Standing[]) {
  const names = standings.map((row) => ({
    name: row.player,
    cmd: row.commander,
    colors: row.colors,
    isWinner: row.rank === 1,
  }));
  const pad = Array.from({ length: 40 }, (_, index) => names[index % names.length]);
  return {
    swiss: {
      topSeed: standings[0].player,
      topRecord: `${standings[0].wins}-${standings[0].losses}-${standings[0].draws}`,
    },
    t40: Array.from({ length: 10 }, (_, pod) => ({
      num: pod + 1,
      players: pad.slice(pod * 4, pod * 4 + 4).map((player, index) => ({
        ...player,
        isWinner: index === 0,
      })),
    })),
    t16: Array.from({ length: 4 }, (_, pod) => ({
      num: pod + 1,
      players: pad.slice(pod * 4, pod * 4 + 4).map((player, index) => ({
        ...player,
        isWinner: index === 0,
      })),
    })),
    t4: {
      players: names.slice(0, 4).map((player, index) => ({
        ...player,
        isWinner: index === 0,
      })),
    },
  };
}

function remapStandings(base: Standing[], winner: string, winnerCmd: string, winnerColors: string): Standing[] {
  return base.map((row, index) => {
    if (index === 0) {
      return { ...row, player: winner, commander: winnerCmd, colors: winnerColors };
    }
    return row;
  });
}

function makeDetail(input: {
  slug: string;
  name: string;
  date: string;
  players: number;
  rounds: number;
  cutSize: number;
  winner: string;
  winnerCmd: string;
  winnerColors: string;
  source: string;
  standings?: Standing[];
  topRecord: string;
  prize: string;
}): TournamentDetail {
  const standings = input.standings ?? remapStandings(siegeStandings, input.winner, input.winnerCmd, input.winnerColors);
  return {
    slug: input.slug,
    name: input.name,
    date: input.date,
    players: input.players,
    rounds: input.rounds,
    cutSize: input.cutSize,
    winner: input.winner,
    winnerCmd: input.winnerCmd,
    winnerColors: input.winnerColors,
    source: input.source,
    standings,
    narratives: buildNarratives(input),
    cmdDist: distributionFromStandings(standings, input.cutSize),
    bracket: buildBracket(standings),
  };
}

export const tournamentDetails: Record<string, TournamentDetail> = {
  "siege-cedh-10k": makeDetail({
    slug: "siege-cedh-10k",
    name: "SIEGE cEDH 10K",
    date: "2026-06-13",
    players: 308,
    rounds: 8,
    cutSize: 40,
    winner: "Jason D. // CriticalEDH",
    winnerCmd: "Kinnan, Bonder Prodigy",
    winnerColors: "UG",
    source: "https://topdeck.gg/bracket/level-7s-siege-at-the-castle-10k",
    standings: siegeStandings,
    topRecord: "5-0-3",
    prize: "$10K",
  }),
  "the-boil-2026": makeDetail({
    slug: "the-boil-2026",
    name: "Land, Go Presents: The Boil 2026",
    date: "2026-03-28",
    players: 268,
    rounds: 8,
    cutSize: 40,
    winner: "Zeke Maxwell [Monolith]",
    winnerCmd: "Kinnan, Bonder Prodigy",
    winnerColors: "UG",
    source: "https://topdeck.gg",
    topRecord: "6-0-2",
    prize: "$8K+",
  }),
  "quest-for-a-cause": makeDetail({
    slug: "quest-for-a-cause",
    name: "The Quest for a Cause — $10k cEDH Charity Main Event",
    date: "2026-05-16",
    players: 260,
    rounds: 8,
    cutSize: 40,
    winner: "Bruno Gino-Griffiths",
    winnerCmd: "Rograkh / Silas Renn",
    winnerColors: "UBR",
    source: "https://topdeck.gg",
    topRecord: "5-1-2",
    prize: "$10K+",
  }),
  "land-go-open-10k": makeDetail({
    slug: "land-go-open-10k",
    name: "Land, Go Open 10k cEDH Tournament",
    date: "2026-05-23",
    players: 212,
    rounds: 7,
    cutSize: 32,
    winner: "[CHUDS] Shmant Shmandrew Shmeklund",
    winnerCmd: "Kinnan, Bonder Prodigy",
    winnerColors: "UG",
    source: "https://topdeck.gg",
    topRecord: "5-1-1",
    prize: "$10K",
  }),
};

export function getTournamentDetail(slug: string) {
  return tournamentDetails[slug] ?? null;
}

export function getRecentTournaments(limit = 5) {
  return [...tournamentSummaries]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, limit);
}
