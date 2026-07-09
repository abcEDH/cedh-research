/**
 * Pure helpers for tournament display. No I/O.
 */

/** Format an ISO timestamp as a human date (UTC), em dash when unknown. */
export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) {
    return "—";
  }
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }
  return parsed.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** Win rate from a W/L/D record (0..1), or null when no games are recorded. */
export function winRateFromWLD(
  wins: number | null,
  losses: number | null,
  draws: number | null
): number | null {
  const w = wins ?? 0;
  const games = w + (losses ?? 0) + (draws ?? 0);
  if (games === 0) {
    return null;
  }
  return w / games;
}

/** Render a W/L/D record, tolerating nulls. */
export function formatRecord(
  wins: number | null,
  losses: number | null,
  draws: number | null
): string {
  return `${wins ?? 0}-${losses ?? 0}-${draws ?? 0}`;
}
