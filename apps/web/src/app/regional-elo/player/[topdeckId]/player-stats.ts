export type PlayerGameLog = {
  gameId: string;
  startDate: string;
  tournamentName: string;
  state: string | null;
  roundLabel: string;
  tableLabel: string;
  seat: number;
  result: string;
  commanderName: string | null;
  opponents: Array<{
    topdeckId: string | null;
    playerName: string;
    commanderName: string | null;
    seat: number;
    result: string;
  }>;
};

export type OpponentRecord = {
  opponentTopdeckId: string | null;
  opponentName: string;
  wins: number;
  draws: number;
  losses: number;
  games: number;
};

export type CommanderRecord = {
  commanderName: string;
  wins: number;
  draws: number;
  losses: number;
  games: number;
};

export type MatchupInsight = {
  label: string;
  subtitle: string;
  wins: number;
  draws: number;
  losses: number;
  games: number;
  baselineScore: number;
  posteriorScore: number;
  delta: number;
  href?: string;
};

export type SeatSummaryRow = {
  seat: number;
  games: number;
  wins: number;
  draws: number;
  losses: number;
};

export type PlayerLogSummary = {
  totalGames: number;
  totalWins: number;
  totalDraws: number;
  totalLosses: number;
  seatRows: SeatSummaryRow[];
  opponentRecords: OpponentRecord[];
  commanderRecords: CommanderRecord[];
  bestOpponentMatchup: MatchupInsight | null;
  worstOpponentMatchup: MatchupInsight | null;
  bestCommanderMatchup: MatchupInsight | null;
  worstCommanderMatchup: MatchupInsight | null;
};

const MATCHUP_PRIOR_GAMES = 20;
const MATCHUP_DELTA_THRESHOLD = 0.08;
const DRAW_SCORE = 0.2;

function scoreRate(wins: number, draws: number, games: number) {
  if (games <= 0) return 0;
  return (wins + draws * DRAW_SCORE) / games;
}

function posteriorScore(
  wins: number,
  draws: number,
  games: number,
  baselineScore: number,
  priorGames = MATCHUP_PRIOR_GAMES
) {
  return (wins + draws * DRAW_SCORE + baselineScore * priorGames) / (games + priorGames);
}

function buildMatchupInsight(
  record: OpponentRecord | CommanderRecord,
  baselineScore: number,
  label: string,
  subtitle: string,
  href?: string
): MatchupInsight {
  const posterior = posteriorScore(record.wins, record.draws, record.games, baselineScore);
  return {
    label,
    subtitle,
    wins: record.wins,
    draws: record.draws,
    losses: record.losses,
    games: record.games,
    baselineScore,
    posteriorScore: posterior,
    delta: posterior - baselineScore,
    href,
  };
}

function selectBestAndWorstMatchups(
  insights: MatchupInsight[]
): { best: MatchupInsight | null; worst: MatchupInsight | null } {
  const nonEmpty = insights.filter((insight) => insight.games > 0);
  if (nonEmpty.length === 0) {
    return { best: null, worst: null };
  }
  const pool = nonEmpty;

  const best =
    [...pool]
      .filter((insight) => insight.delta >= MATCHUP_DELTA_THRESHOLD)
      .sort((a, b) => {
        if (b.delta !== a.delta) return b.delta - a.delta;
        return b.games - a.games;
      })[0] ??
    [...pool]
      .sort((a, b) => {
        if (b.delta !== a.delta) return b.delta - a.delta;
        return b.games - a.games;
      })[0] ??
    null;

  const worst =
    [...pool]
      .filter((insight) => insight.delta <= -MATCHUP_DELTA_THRESHOLD)
      .sort((a, b) => {
        if (a.delta !== b.delta) return a.delta - b.delta;
        return b.games - a.games;
      })[0] ??
    [...pool]
      .sort((a, b) => {
        if (a.delta !== b.delta) return a.delta - b.delta;
        return b.games - a.games;
      })[0] ??
    null;

  return { best, worst };
}

export function buildOpponentRecords(logs: PlayerGameLog[]): OpponentRecord[] {
  const records = new Map<string, OpponentRecord>();

  for (const log of logs) {
    for (const opponent of log.opponents) {
      const key = opponent.topdeckId ?? `${log.gameId}:${opponent.playerName}:${opponent.seat}`;
      const existing =
        records.get(key) ??
        {
          opponentTopdeckId: opponent.topdeckId,
          opponentName: opponent.playerName,
          wins: 0,
          draws: 0,
          losses: 0,
          games: 0,
        };

      existing.games += 1;

      if (log.result === "win") {
        existing.wins += 1;
      } else if (log.result === "loss") {
        existing.losses += 1;
      } else if (log.result === "draw") {
        existing.draws += 1;
      }

      records.set(key, existing);
    }
  }

  return Array.from(records.values()).sort((a, b) => {
    if (b.games !== a.games) return b.games - a.games;
    return a.opponentName.localeCompare(b.opponentName);
  });
}

export function summarizePlayerLogs(logs: PlayerGameLog[]): PlayerLogSummary {
  const totalGames = logs.length;
  const totalWins = logs.filter((row) => row.result === "win").length;
  const totalDraws = logs.filter((row) => row.result === "draw").length;
  const totalLosses = logs.filter((row) => row.result === "loss").length;
  const baselineScore = scoreRate(totalWins, totalDraws, totalGames);

  const seatRows = [1, 2, 3, 4].map((seat) => {
    const seatGames = logs.filter((row) => row.seat === seat);
    return {
      seat,
      games: seatGames.length,
      wins: seatGames.filter((row) => row.result === "win").length,
      draws: seatGames.filter((row) => row.result === "draw").length,
      losses: seatGames.filter((row) => row.result === "loss").length,
    };
  });

  const opponentRecords = buildOpponentRecords(logs);
  const commanderRecords = buildCommanderRecords(logs);
  const opponentMatchups = opponentRecords.map((record) =>
    buildMatchupInsight(
      record,
      baselineScore,
      record.opponentName,
      "Opponent",
      record.opponentTopdeckId ? `/regional-elo/player/${record.opponentTopdeckId}` : undefined
    )
  );
  const commanderMatchups = commanderRecords.map((record) =>
    buildMatchupInsight(
      record,
      baselineScore,
      record.commanderName,
      "Commander"
    )
  );
  const { best: bestOpponentMatchup, worst: worstOpponentMatchup } =
    selectBestAndWorstMatchups(opponentMatchups);
  const { best: bestCommanderMatchup, worst: worstCommanderMatchup } =
    selectBestAndWorstMatchups(commanderMatchups);

  return {
    totalGames,
    totalWins,
    totalDraws,
    totalLosses,
    seatRows,
    opponentRecords,
    commanderRecords,
    bestOpponentMatchup,
    worstOpponentMatchup,
    bestCommanderMatchup,
    worstCommanderMatchup,
  };
}

export function buildCommanderRecords(logs: PlayerGameLog[]): CommanderRecord[] {
  const records = new Map<string, CommanderRecord>();
  const unknownCommanderLabel = "Unknown";

  function normalizeCommanderName(value: string | null | undefined) {
    const trimmed = value?.trim() ?? "";
    if (!trimmed || trimmed.toLowerCase() === "unknown commander") {
      return unknownCommanderLabel;
    }
    return trimmed;
  }

  for (const log of logs) {
    const commandersInGame = new Set<string>();

    for (const opponent of log.opponents) {
      const commanderName = normalizeCommanderName(opponent.commanderName);
      commandersInGame.add(commanderName);
    }

    for (const commanderName of commandersInGame) {
      const existing =
        records.get(commanderName) ??
        {
          commanderName,
          wins: 0,
          draws: 0,
          losses: 0,
          games: 0,
        };

      existing.games += 1;

      if (log.result === "win") {
        existing.wins += 1;
      } else if (log.result === "loss") {
        existing.losses += 1;
      } else if (log.result === "draw") {
        existing.draws += 1;
      }

      records.set(commanderName, existing);
    }
  }

  return Array.from(records.values()).sort((a, b) => {
    if (a.commanderName === unknownCommanderLabel && b.commanderName !== unknownCommanderLabel) {
      return 1;
    }
    if (b.commanderName === unknownCommanderLabel && a.commanderName !== unknownCommanderLabel) {
      return -1;
    }
    if (b.games !== a.games) return b.games - a.games;
    return a.commanderName.localeCompare(b.commanderName);
  });
}
