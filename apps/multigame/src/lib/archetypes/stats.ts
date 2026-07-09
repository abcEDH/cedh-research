/**
 * Pure math over deck identity stat rows. No I/O.
 */

export interface EntriesLike {
  entries: number;
}

export function totalEntries(rows: EntriesLike[]): number {
  return rows.reduce((sum, row) => sum + row.entries, 0);
}

/**
 * Meta share of each row as a fraction of total entries (0..1).
 * Returns 0 for every row when there are no entries at all.
 */
export function computeMetaShare<T extends EntriesLike>(rows: T[]): (T & { metaShare: number })[] {
  const total = totalEntries(rows);
  return rows.map((row) => ({
    ...row,
    metaShare: total > 0 ? row.entries / total : 0,
  }));
}

/** Format a 0..1 rate as a percentage string, em dash when unknown. */
export function formatWinRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) {
    return "—";
  }
  return `${(rate * 100).toFixed(1)}%`;
}

/** Format a 0..1 share as a percentage string. */
export function formatPercent(fraction: number, digits = 1): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}
