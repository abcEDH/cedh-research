export type PlayerStateHistoryRow = {
  state: string;
  city?: string | null;
  start_date: string;
  player_count: number | null;
};

export type PredictedState = {
  state: string;
  confidence: number;
  entries: number;
  source: "small-events" | "all-events" | "all-prior";
};

const LOCAL_EVENT_PLAYER_LIMIT = 64;

function normalizeState(value: string | null | undefined) {
  return (value ?? "").trim().toUpperCase();
}

function normalizeCity(value: string | null | undefined) {
  return normalizeState(value).replace(/[^A-Z0-9]+/g, " ").trim();
}

function addMonths(value: Date, months: number) {
  const date = new Date(value);
  date.setMonth(date.getMonth() + months);
  return date;
}

function calculateLocationRecencyWeight(eventDate: string, referenceDate: Date) {
  const eventTimestamp = Date.parse(eventDate);
  if (!Number.isFinite(eventTimestamp)) return 0;
  const ageInDays = Math.max(0, (referenceDate.getTime() - eventTimestamp) / (1000 * 60 * 60 * 24));
  return Math.max(0.25, 0.5 ** (ageInDays / 15));
}

function calculateSmallTournamentWeight(playerCount: number | null) {
  if (!playerCount || playerCount <= 0) return 1;
  return Math.max(0.5, Math.min(2, LOCAL_EVENT_PLAYER_LIMIT / playerCount));
}

function hasSimilarLocation(left: PlayerStateHistoryRow, right: PlayerStateHistoryRow) {
  if (left.state !== right.state) return false;
  const leftCity = normalizeCity(left.city);
  const rightCity = normalizeCity(right.city);
  if (leftCity && rightCity) return leftCity === rightCity;
  return true;
}

function isCleanSmallEvent(row: PlayerStateHistoryRow, rows: PlayerStateHistoryRow[]) {
  if (!row.player_count || row.player_count > LOCAL_EVENT_PLAYER_LIMIT) return false;
  const eventTimestamp = Date.parse(row.start_date);
  if (!Number.isFinite(eventTimestamp)) return false;

  return !rows.some((other) => {
    if (!other.player_count || other.player_count <= LOCAL_EVENT_PLAYER_LIMIT) return false;
    const otherTimestamp = Date.parse(other.start_date);
    if (!Number.isFinite(otherTimestamp)) return false;
    const ageDeltaDays = Math.abs(otherTimestamp - eventTimestamp) / (1000 * 60 * 60 * 24);
    return ageDeltaDays <= 2 && hasSimilarLocation(row, other);
  });
}

function selectStateHistoryWindow(rows: PlayerStateHistoryRow[], referenceDate: Date) {
  const sixMonthStart = addMonths(referenceDate, -6).getTime();
  const sixMonthRows = rows.filter((row) => Date.parse(row.start_date) >= sixMonthStart);
  if (sixMonthRows.length >= 2) return sixMonthRows;

  const twelveMonthStart = addMonths(referenceDate, -12).getTime();
  return rows.filter((row) => Date.parse(row.start_date) >= twelveMonthStart);
}

export function predictNextState(
  rows: PlayerStateHistoryRow[],
  referenceDate = new Date()
): PredictedState | null {
  const normalizedRows = rows
    .map((row) => ({
      ...row,
      state: normalizeState(row.state),
      city: normalizeCity(row.city),
    }))
    .filter((row) => row.state && Number.isFinite(Date.parse(row.start_date)))
    .sort((a, b) => Date.parse(a.start_date) - Date.parse(b.start_date));
  if (normalizedRows.length === 0) return null;

  const cleanSmallEventRows = normalizedRows.filter((row) => isCleanSmallEvent(row, normalizedRows));
  const smallEventRows = cleanSmallEventRows.length >= 2
    ? cleanSmallEventRows
    : normalizedRows.filter((row) => !row.player_count || row.player_count <= LOCAL_EVENT_PLAYER_LIMIT);
  let source: PredictedState["source"] = "small-events";
  let selectedRows = selectStateHistoryWindow(smallEventRows, referenceDate);

  if (selectedRows.length === 0) {
    source = "all-events";
    selectedRows = selectStateHistoryWindow(normalizedRows, referenceDate);
  }
  if (selectedRows.length === 0) {
    source = "all-prior";
    selectedRows = normalizedRows;
  }

  const stateScores = new Map<string, { state: string; score: number; entries: number; latestDate: string }>();
  for (const row of selectedRows) {
    const current = stateScores.get(row.state) ?? {
      state: row.state,
      score: 0,
      entries: 0,
      latestDate: "",
    };
    current.score += calculateLocationRecencyWeight(row.start_date, referenceDate) *
      calculateSmallTournamentWeight(row.player_count);
    current.entries += 1;
    if (row.start_date > current.latestDate) {
      current.latestDate = row.start_date;
    }
    stateScores.set(row.state, current);
  }

  const totalScore = Array.from(stateScores.values()).reduce((sum, row) => sum + row.score, 0);
  const prediction = Array.from(stateScores.values()).sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (b.entries !== a.entries) return b.entries - a.entries;
    if (b.latestDate !== a.latestDate) return b.latestDate.localeCompare(a.latestDate);
    return a.state.localeCompare(b.state);
  })[0];

  return prediction
    ? {
        state: prediction.state,
        confidence: totalScore ? prediction.score / totalScore : 0,
        entries: selectedRows.length,
        source,
      }
    : null;
}
