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
};

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

  return {
    totalGames,
    totalWins,
    totalDraws,
    totalLosses,
    seatRows,
    opponentRecords: buildOpponentRecords(logs),
  };
}
